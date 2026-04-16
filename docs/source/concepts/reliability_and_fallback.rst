Production Reliability and Fallback Strategies
===============================================

In any production energy forecasting system, things go wrong: sensors fail, data
pipelines stall, models grow stale, and weather feeds arrive late. A robust deployment
does not simply crash or silently emit bad numbers — it degrades gracefully, substitutes
sensible fallback forecasts, and surfaces the right signals so operators can act.

This page explains how OpenSTEF's library components support each layer of that
reliability story, from detecting bad input data to substituting a baseline model when
the primary one cannot be trusted.

.. note::

   This page focuses on reliability mechanics. For background on what a forecast
   represents, see :doc:`forecasting_basics`. For how uncertainty is expressed in
   outputs, see :doc:`quantiles_and_confidence`.

----

Detecting Bad Input Data Early
-------------------------------

The first line of defence is refusing to produce a forecast from data that is
fundamentally broken. OpenSTEF provides two built-in validation transforms that you
compose into your preprocessing pipeline.

**Completeness checking**

:class:`~openstef_models.transforms.validation.CompletenessChecker` measures the ratio
of non-missing values across the dataset and raises
:class:`~openstef_core.exceptions.InsufficientlyCompleteError` when that ratio falls
below a configurable threshold. The default threshold is ``0.5`` — if more than half
the values are missing, the dataset is considered unusable.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker

   data = pd.DataFrame(
       {
           "load": [100.0, np.nan, np.nan, np.nan],
           "temperature": [20.0, np.nan, 24.0, np.nan],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min"),
   )
   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   checker = CompletenessChecker(completeness_threshold=0.5)
   try:
       checker.transform(dataset)
   except Exception as exc:
       print(f"Data rejected: {exc}")
   # Data rejected: The dataset is not sufficiently complete. Completeness: 0.25

You can tighten or relax the threshold, restrict checking to specific columns, and
assign per-column weights to reflect that some features matter more than others:

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker

   # Only check the load column; weight it heavily relative to weather features
   checker = CompletenessChecker(
       columns=["load"],
       weights={"load": 2.0, "temperature": 1.0},
       completeness_threshold=0.7,
   )

**Flatliner detection**

A sensor that is stuck at a constant value is just as dangerous as a missing one —
it looks complete but carries no information. The
:class:`~openstef_models.transforms.validation.FlatlineChecker` detects periods where
the load signal does not change, raising
:class:`~openstef_core.exceptions.FlatlinerDetectedError`. This catches common failure
modes such as a frozen SCADA reading or a broken data-transmission link.

.. code-block:: python

   from openstef_models.transforms.validation import FlatlineChecker

   flatline_checker = FlatlineChecker(
       load_column="load",
       flatliner_threshold=timedelta(hours=1),
       detect_non_zero_flatliner=True,
       error_on_flatliner=False,   # warn rather than raise, so the pipeline continues
   )

Setting ``error_on_flatliner=False`` is a deliberate choice for production: you want
the anomaly logged and flagged, but you may still want to attempt a forecast using
whatever valid data remains.

----

Handling Missing Values in Features
-------------------------------------

Even when the overall dataset passes completeness checks, individual feature columns
often have gaps — a weather station goes offline, a lag feature cannot be computed at
the start of a series, or a new sensor is added mid-deployment. OpenSTEF's
:class:`~openstef_models.transforms.imputation.Imputer` fills these gaps before they
reach the model.

The imputer supports several strategies. For most production use cases the iterative
strategy (based on ``IterativeImputer``) gives the best results because it uses the
relationships between features to infer missing values, rather than substituting a
global mean or median blindly:

.. code-block:: python

   from openstef_models.transforms.imputation import Imputer

   imputer = Imputer(
       strategy="iterative",
       initial_strategy="mean",
       max_iterations=40,
       tolerance=1e-3,
   )

.. note::

   By default the imputer does **not** fill future values — only historical gaps. This
   preserves time-series integrity and prevents look-ahead leakage. Set
   ``fill_future_values`` explicitly if your pipeline requires it.

----

The Baseline Fallback Model
----------------------------

When the primary model cannot produce a forecast — because training data was
insufficient, the model artefact is missing, or a validation step raised an exception —
you need something to fall back on. OpenSTEF ships
:class:`~openstef_models.models.forecasting.BaseCaseForecaster` precisely for this
role.

The baseline model exploits the strong weekly periodicity of energy load: it takes the
last seven days of historical data and repeats that pattern forward. If the seven-day
window is itself incomplete, it falls back automatically to a fourteen-day window:

.. code-block:: python

   from datetime import timedelta

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

The baseline also produces confidence intervals, derived from hourly standard
deviations of the repeated historical window. This means downstream consumers always
receive a probabilistic forecast in the same format, regardless of whether the primary
or fallback model answered the request.

.. note::

   The baseline is intentionally simple. Its purpose is to keep the system producing
   *reasonable* numbers, not *optimal* ones. Use it as a safety net, not as a
   long-term substitute for a well-trained model.

----

Model Staleness and Reuse Limits
----------------------------------

A model trained weeks ago on summer data should not be trusted to forecast a winter
peak. OpenSTEF's workflow layer enforces a maximum model age through the
``model_reuse_max_age`` parameter. When the stored model is older than this limit, the
workflow triggers a fresh training run rather than reusing the cached artefact.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),   # retrain if model is older than 7 days
       model_selection_enable=True,
       model_selection_metric=("Q0.5", "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,   # bias selection toward newer models
   )

The ``model_selection_old_model_penalty`` parameter is worth understanding: when
comparing a newly trained model against the stored one, the stored model's metric is
multiplied by this factor before comparison. A value of ``1.2`` means the old model
must be 20 % better than the new one to be retained. This deliberately biases the
system toward freshness, preventing a situation where a marginally better old model
blocks retraining indefinitely.

.. note:: [DIAGRAM: Decision flow — on each forecast cycle, check model age against
   ``model_reuse_max_age``; if stale, retrain; compare new vs old model with penalty
   factor; store winner; produce forecast.]

----

Catching Errors and Continuing
--------------------------------

Production pipelines must distinguish between errors that are recoverable (sparse data,
a single bad feature) and those that are not (no training data at all). OpenSTEF uses a
typed exception hierarchy so you can catch specific failure modes and respond
appropriately.

.. code-block:: python

   from openstef_core.exceptions import (
       FlatlinerDetectedError,
       InsufficientlyCompleteError,
   )
   from openstef_models.models.forecasting.base_case_forecaster import BaseCaseForecaster
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   def produce_forecast(workflow, dataset):
       """Attempt primary forecast; fall back to baseline on known failure modes."""
       try:
           return workflow.predict(dataset)
       except (InsufficientlyCompleteError, FlatlinerDetectedError) as exc:
           # Data quality issue — use the baseline model instead
           print(f"Primary forecast failed ({exc}); switching to baseline.")
           fallback = BaseCaseForecaster(
               quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
               horizons=[LeadTime(timedelta(hours=1))],
           )
           fallback.fit(dataset)
           return fallback.predict(dataset)

This pattern keeps the calling code clean: the fallback is invoked only for known,
recoverable conditions, while unexpected exceptions still propagate and alert on-call
engineers.

----

Monitoring Performance Over Time
----------------------------------

Fallback strategies are reactive. A proactive system also monitors how forecast quality
evolves over time so that degradation is caught before it becomes a crisis.
``openstef-beam`` provides ``WindowedMetricVisualization``, which plots a chosen metric
(such as MAE or R²) over a sliding evaluation window, making it straightforward to spot
the moment a model starts drifting:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window

   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_evolution",
               metric="MAE",
               window=Window(size=timedelta(days=7), step=timedelta(days=1)),
           )
       ]
   )

Typical patterns to watch for:

- A gradual upward drift in MAE after a seasonal transition (model needs retraining).
- A sudden spike coinciding with a sensor replacement or grid topology change.
- Periodic degradation at the same time each week, suggesting a missing calendar
  feature (see :doc:`feature_engineering`).

----

Summary
--------

Reliable production forecasting with OpenSTEF rests on four complementary mechanisms:

- **Input validation** — :class:`~openstef_models.transforms.validation.CompletenessChecker`
  and :class:`~openstef_models.transforms.validation.FlatlineChecker` reject data that
  cannot support a trustworthy forecast.
- **Imputation** — :class:`~openstef_models.transforms.imputation.Imputer` fills
  recoverable gaps in feature columns before they reach the model.
- **Baseline fallback** — :class:`~openstef_models.models.forecasting.BaseCaseForecaster`
  provides a weekly-repetition forecast whenever the primary model is unavailable.
- **Staleness control** — ``model_reuse_max_age`` and ``model_selection_old_model_penalty``
  ensure the workflow retrains before a model drifts too far from current conditions.

Together these components let you build a system that keeps producing useful forecasts
under adverse conditions, while giving you the observability to know when something
needs attention.