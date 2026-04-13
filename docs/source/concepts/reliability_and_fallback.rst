Reliability and Fallback Strategies
====================================

Production energy forecasting systems must keep running even when things go wrong — models age, sensors fail, and data arrives late or not at all. This page explains how OpenSTEF addresses these challenges through built-in data validation, fallback forecasting, and model staleness controls. These mechanisms are part of the library itself, not bolt-on additions, so you can rely on them as first-class building blocks.

.. note::

   This page focuses on reliability patterns. For an introduction to how forecasting works in OpenSTEF, see :doc:`forecasting_basics`. For probabilistic output and confidence intervals, see :doc:`quantiles_and_confidence`.

Data Quality Validation Before Forecasting
-------------------------------------------

Bad input data is the most common source of silent forecast failures. OpenSTEF provides three validation transforms in ``openstef_models.transforms.validation`` that can be applied before training or inference to catch problems early.

**Completeness checking**

The ``CompletenessChecker`` measures what fraction of expected values are actually present and raises ``InsufficientlyCompleteError`` if the data falls below a configurable threshold. By default, a dataset must be at least 50% complete.

.. code-block:: python

   from datetime import timedelta
   import numpy as np
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker

   data = pd.DataFrame(
       {
           "load": [1.2, np.nan, np.nan, 1.5],
           "temperature": [20.0, np.nan, 22.0, np.nan],
           "wind_speed": [np.nan, np.nan, np.nan, np.nan],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min"),
   )
   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   # Default threshold: 50% completeness required
   checker = CompletenessChecker()
   try:
       checker.transform(dataset)
   except Exception as e:
       print(f"Data rejected: {e}")
       # Fall back to a simpler forecasting strategy

You can tune the threshold and focus on specific columns. Weighting lets you treat some features as more critical than others:

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker

   # Require 80% completeness, but weight load data as twice as important
   checker = CompletenessChecker(
       columns=["load", "temperature"],
       weights={"load": 2.0, "temperature": 1.0},
       completeness_threshold=0.8,
   )

**Flatline detection**

A sensor that stops updating will produce a stream of identical values — a "flatliner" pattern that looks like valid data but is actually a fault. The ``FlatlineChecker`` detects this condition:

.. code-block:: python

   from openstef_models.transforms.validation import FlatlineChecker

   flatline_checker = FlatlineChecker(
       load_column="load",
       flatliner_threshold=6,       # flag after 6 consecutive identical values
       detect_non_zero_flatliner=True,
       error_on_flatliner=False,    # warn rather than raise, so the pipeline continues
   )

Setting ``error_on_flatliner=False`` is the recommended production posture: the checker logs the anomaly but allows the pipeline to proceed, letting downstream logic decide whether to use a fallback forecast.

**Input consistency checking**

``InputConsistencyChecker`` validates that the structure of incoming data matches what the model was trained on — same columns, compatible time intervals, and no unexpected schema drift. This is especially useful when models are retrained infrequently and the upstream data pipeline evolves independently.

.. code-block:: python

   from openstef_models.transforms.validation import InputConsistencyChecker

   consistency_checker = InputConsistencyChecker()
   consistency_checker.fit(training_dataset)   # learn the expected schema at train time
   consistency_checker.transform(live_dataset) # validate at inference time

These three validators compose naturally. In the ``EnsembleForecastingWorkflowConfig``, they are wired in automatically as part of the preprocessing pipeline, so you get them for free when using the high-level workflow API.

The BaseCaseForecaster: A Built-In Fallback
--------------------------------------------

When a primary model cannot produce a forecast — because data is too sparse, the model has not yet been trained, or validation has failed — you need something to fill the gap. OpenSTEF ships ``BaseCaseForecaster`` for exactly this purpose.

The forecaster implements a simple but robust strategy: it repeats the most recent weekly pattern of historical load data over the forecast horizon. If the most recent week is unavailable, it falls back to the week before that. This mirrors how human operators have historically handled outages, and it performs surprisingly well for load data that has strong weekly periodicity.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   fallback_model = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),   # use last week first
           fallback_lag=timedelta(days=14), # fall back to two weeks ago
       ),
   )

The ``BaseCaseForecaster`` also produces confidence intervals by computing hourly standard deviations from the repeated base-case data, so it integrates cleanly with probabilistic forecasting pipelines. See :doc:`quantiles_and_confidence` for more on how OpenSTEF represents forecast uncertainty.

.. note::

   ``BaseCaseForecaster`` is a naive baseline, not a replacement for a well-trained ML model. Use it as a safety net, not as a primary forecaster. It is most appropriate when you have strong weekly seasonality and need a forecast that is always available.

Graceful Degradation in Practice
----------------------------------

A robust production system layers these tools into a degradation hierarchy. The idea is to always produce *some* forecast, with quality decreasing gracefully as conditions worsen:

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

In code, this looks like catching specific OpenSTEF exceptions and routing to the next level:

.. code-block:: python

   from openstef_core.exceptions import InsufficientlyCompleteError

   def produce_forecast(live_dataset, primary_workflow, fallback_model):
       """Attempt primary forecast, degrade gracefully on failure."""
       try:
           # Attempt full ML forecast
           return primary_workflow.predict(live_dataset)

       except InsufficientlyCompleteError as e:
           # Data is too sparse for the primary model; use the base case
           print(f"Primary forecast failed due to data quality: {e}")
           print("Falling back to BaseCaseForecaster.")
           return fallback_model.predict(live_dataset)

       except Exception as e:
           # Unexpected failure — log and re-raise so the caller can decide
           print(f"Unexpected forecasting error: {e}")
           raise

The key principle is that ``InsufficientlyCompleteError`` is a *recoverable* condition — the library raises it precisely so you can catch it and act. Unexpected exceptions should propagate so they are visible in monitoring.

Model Staleness and Reuse Controls
------------------------------------

A model trained weeks ago on different weather conditions or load patterns may produce poor forecasts even when the data pipeline is healthy. OpenSTEF's ``EnsembleForecastingWorkflowConfig`` exposes controls for managing model age and reuse decisions.

.. code-block:: python

   from openstef_models.workflows.ensemble_forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
   )
   from datetime import timedelta

   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42",
       # Prevent reuse of models older than 30 days
       model_max_age=timedelta(days=30),
       # Enable automatic model selection based on performance
       model_reuse_enable=True,
       # Metric used to compare old vs. new model
       model_selection_enable=True,
       model_selection_metric=("Q0.5", "R2", "higher_is_better"),
       # Apply a 20% penalty to the old model's score to bias towards retraining
       model_selection_old_model_penalty=1.2,
   )

The ``model_selection_old_model_penalty`` parameter is worth understanding: it biases the comparison so that a newly trained model only needs to be *roughly as good* as the incumbent to be adopted, rather than strictly better. This prevents the system from clinging to an old model that happens to score marginally higher on a stale evaluation set.

When ``model_reuse_enable=False``, the workflow always retrains from scratch. This is appropriate for backtesting (where you want reproducible results) but is usually too expensive for production. Setting ``model_max_age`` gives you a middle ground: reuse the model when it is fresh, retrain when it has aged past the threshold.

.. note::

   Model staleness is distinct from data staleness. A model can be recent but trained on data that did not include the current season or a recent grid change. Monitoring forecast residuals over time is the most reliable signal that a model needs retraining, regardless of its age.

Handling Missing Features at Inference Time
--------------------------------------------

Even when the target load signal is available, weather features or market price data may arrive late or be missing entirely. OpenSTEF's feature engineering pipeline is designed to handle this gracefully. See :doc:`feature_engineering` for a full discussion of which features are used and how they are constructed.

For inference specifically, the key practice is to distinguish between features that are *required* and those that are *optional enrichments*. The ``CompletenessChecker`` supports column-level weights for this reason: you can configure it to tolerate missing weather data while still rejecting forecasts when the load signal itself is absent.

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker

   # Load is critical; weather features are helpful but not essential
   checker = CompletenessChecker(
       columns=["load", "temperature", "wind_speed", "radiation"],
       weights={
           "load": 4.0,        # heavily penalise missing load data
           "temperature": 1.0,
           "wind_speed": 0.5,
           "radiation": 0.5,
       },
       completeness_threshold=0.7,
   )

With this configuration, a forecast run with missing weather data will still pass validation as long as the load signal is present, because the weighted completeness score remains above 0.7.

Summary
--------

OpenSTEF provides a layered set of reliability tools that work together:

- **``CompletenessChecker``** — rejects data that is too sparse before it can corrupt a forecast.
- **``FlatlineChecker``** — detects stuck sensors that produce deceptively valid-looking data.
- **``InputConsistencyChecker``** — guards against schema drift between training and inference.
- **``BaseCaseForecaster``** — provides a always-available fallback that repeats weekly patterns.
- **``model_max_age`` and ``model_selection_old_model_penalty``** — prevent stale models from persisting in production.

These are library primitives. How you combine them — which exceptions you catch, what your degradation hierarchy looks like, how you alert on failures — is the responsibility of the application built on top of OpenSTEF. The library's job is to make the failure modes explicit and recoverable.