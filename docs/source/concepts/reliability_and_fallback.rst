Production Reliability and Fallback Strategies
===============================================

Energy forecasting systems operate continuously in production environments where data
pipelines break, sensors fail, and models can grow stale. This page covers the
reliability mechanisms built into OpenSTEF and the patterns you should adopt when
integrating the library into a production system. The goal is *graceful degradation*:
when something goes wrong, the system should produce the best possible forecast rather
than failing silently or crashing entirely.

For background on what forecasts contain and how uncertainty is represented, see
:doc:`quantiles_and_confidence`. For details on the features that feed into these
models, see :doc:`feature_engineering`.

.. mermaid:: diagrams/concepts/reliability_and_fallback_diagram_1.mmd


Data Quality Validation
-----------------------

The first line of defence is catching bad input before it reaches the model. OpenSTEF
provides three built-in validation transforms in ``openstef_models.transforms.validation``
that can be composed into any preprocessing pipeline.

**CompletenessChecker** computes the fraction of non-null values across the dataset and
raises ``InsufficientlyCompleteError`` if it falls below the configured threshold. This
prevents a model from training or predicting on a dataset that is mostly gaps:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker

   data = pd.DataFrame(
       {
           "load": [100.0, np.nan, np.nan, 105.0],
           "temperature": [20.0, np.nan, 24.0, np.nan],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min"),
   )
   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   checker = CompletenessChecker()
   try:
       checker.transform(dataset)
   except Exception as exc:
       print(f"Data rejected: {exc}")
   # Data rejected: The dataset is not sufficiently complete. Completeness: 0.50

You can restrict the check to specific columns and assign weights to reflect their
relative importance. Weather features that are missing can often be imputed; a missing
target column cannot.

**FlatlineChecker** detects *flatliner* patterns — sequences of identical consecutive
values that typically indicate a stuck sensor rather than a real physical signal. It
exposes a ``detect_ongoing_flatliner`` method for real-time monitoring as well as a
``transform`` method that integrates into the pipeline. The ``error_on_flatliner``
parameter controls whether detection raises an exception or merely logs a warning,
which is useful when you want to flag the issue without halting the forecast:

.. code-block:: python

   from openstef_models.transforms.validation import FlatlineChecker

   flatline_checker = FlatlineChecker(
       load_column="load",
       flatliner_threshold=6,      # consecutive identical values before flagging
       detect_non_zero_flatliner=True,
       error_on_flatliner=False,   # warn, don't raise
   )

**InputConsistencyChecker** ensures that the feature columns present at inference time
match those seen during training. It logs warnings and drops unexpected columns rather
than crashing, which is the correct behaviour when a data provider adds a new field
that the model was never trained on.

All three transforms are used together in the default
``EnsembleForecastingWorkflowConfig`` preprocessing pipeline, so you get this
protection automatically when using the high-level workflow API.


Handling Missing and Incomplete Input
--------------------------------------

Even when data passes the completeness threshold, individual time steps may contain
gaps. OpenSTEF's feature engineering layer handles forward-filling and lag-based
imputation internally, but there are limits. A few practical rules for production:

- **Short gaps (< 1 hour)** are generally safe to forward-fill. OpenSTEF's lag
  features will naturally bridge these.
- **Long gaps (hours to days)** in the target variable make lag features unreliable.
  Consider switching to the base-case forecaster (see below) until the feed is
  restored.
- **Missing weather features** are less critical than missing load data, but
  degraded weather input will reduce accuracy. Log a warning and monitor forecast
  error metrics when a weather feed is interrupted.

When training data contains NaN targets after preprocessing, OpenSTEF raises
``InsufficientlyCompleteError`` with a clear message rather than silently fitting a
model on an empty dataset:

.. code-block:: python

   from openstef_core.exceptions import InsufficientlyCompleteError

   try:
       workflow.fit(train_data)
   except InsufficientlyCompleteError as exc:
       # Log the failure and skip this training run; keep the existing model
       logger.error("Training skipped due to insufficient data: %s", exc)


The Base-Case Forecaster as a Fallback
---------------------------------------

When a trained model is unavailable — because training failed, the model file is
corrupt, or the model is too stale to trust — OpenSTEF provides ``BaseCaseForecaster``
as a principled fallback. Rather than returning zeros or raising an exception, it
repeats the most recent weekly pattern from historical data:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   fallback = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),   # use last week as the template
           fallback_lag=timedelta(days=14), # fall back to two weeks ago if needed
       ),
   )

The forecaster uses the 7-day lag as its primary template and automatically falls back
to the 14-day lag when the primary window contains gaps. Confidence intervals are
derived from the hourly standard deviation of the repeated pattern, so the output
remains a valid probabilistic forecast compatible with the rest of your pipeline.

``BaseCaseForecaster`` is intentionally naive — it makes no use of weather features or
recent load trends. Its value is *reliability*, not accuracy. A system that always
produces a reasonable forecast is more useful in production than one that produces
excellent forecasts most of the time but fails unpredictably.

A typical integration pattern wraps the primary forecast call and falls back on any
exception:

.. code-block:: python

   def get_forecast(workflow, fallback_forecaster, forecast_input):
       try:
           return workflow.predict(forecast_input)
       except Exception as exc:
           logger.warning(
               "Primary model failed (%s), using base-case fallback.", exc
           )
           return fallback_forecaster.predict(forecast_input)

.. note::

   Log every fallback activation with enough context (model ID, timestamp, exception
   type) to diagnose the root cause later. Silent fallbacks are a common source of
   hard-to-detect accuracy regressions in production.


Model Staleness Detection
--------------------------

A model trained months ago on last winter's data may be technically loadable but
produce poor forecasts on today's conditions. OpenSTEF's workflow configuration
exposes ``model_max_age`` to set an upper bound on how old a reused model can be:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.workflows.ensemble_forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
   )

   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42",
       model_reuse_enable=True,
       model_max_age=timedelta(days=30),   # reject models older than 30 days
       model_selection_enable=True,
       model_selection_metric=("Q0.5", "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,  # bias selection towards newer models
       # ... other config
   )

When ``model_reuse_enable=True``, the workflow checks the age of any stored model
before deciding whether to reuse it or retrain. The ``model_selection_old_model_penalty``
multiplier applies a discount to an older model's performance metric, so a newer model
that is only marginally worse on the validation set will be preferred. This prevents
the system from holding on to a high-performing model that was trained on data that no
longer reflects current conditions.

If the stored model exceeds ``model_max_age``, the workflow triggers a fresh training
run. If training fails (for example, because recent data is incomplete), the system
should fall back to the base-case forecaster rather than using the stale model — this
is a policy decision you implement in the calling code, as shown in the previous
section.


Graceful Degradation in Practice
----------------------------------

The following table summarises the failure modes and recommended responses:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Failure mode
     - Detection
     - Response
   * - Input data mostly missing
     - ``CompletenessChecker`` raises ``InsufficientlyCompleteError``
     - Skip training run; use existing model or base-case fallback
   * - Stuck sensor / flatliner
     - ``FlatlineChecker`` warning or error
     - Flag data quality issue; optionally exclude affected column
   * - Feature column mismatch at inference
     - ``InputConsistencyChecker`` warning
     - Drop unknown columns; continue with known features
   * - Model too old
     - ``model_max_age`` exceeded in workflow config
     - Trigger retraining; fall back to base-case if retraining fails
   * - Primary model prediction error
     - Exception in ``workflow.predict()``
     - Activate ``BaseCaseForecaster``; alert on-call

The key design principle is that each layer should handle what it can and propagate
failures upward with enough information for the next layer to make a sensible decision.
OpenSTEF's built-in validators and the ``BaseCaseForecaster`` give you the building
blocks; the orchestration logic that connects them belongs in your application code.

.. note::

   Monitor the *rate* of fallback activations as a production metric. A sudden
   increase in base-case usage is a strong signal that something has changed upstream
   — a sensor failure, a data pipeline outage, or a distribution shift in the load
   itself. Treat it as an alert condition, not just a safety net.


Further Reading
---------------

- :doc:`forecasting_basics` — how short-term forecasts are structured and what drives
  their accuracy
- :doc:`feature_engineering` — which input features matter most and how gaps in
  weather data affect forecast quality
- :doc:`quantiles_and_confidence` — understanding the probabilistic output that
  fallback forecasters still need to produce