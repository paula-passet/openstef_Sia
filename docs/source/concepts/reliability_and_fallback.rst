Production Reliability and Fallback Strategies
===============================================

When deploying forecasting models in production, failures are inevitable. Data sources go offline, models produce invalid predictions, or input quality degrades unexpectedly. This page covers practical strategies for building resilient forecasting systems that gracefully handle these failures.

Understanding Production Failure Modes
--------------------------------------

Production forecasting systems face several common failure scenarios:

**Missing or incomplete data**: Weather APIs fail, sensor data has gaps, or upstream systems experience outages. Without proper handling, these gaps propagate through your pipeline and prevent forecast generation.

**Invalid predictions**: Models occasionally produce NaN values, negative loads, or physically impossible forecasts. This happens when input data falls outside the training distribution or when feature engineering creates invalid combinations.

**Model staleness**: A model trained months ago may no longer reflect current patterns. Detecting when a model has degraded is critical for maintaining forecast quality.

**Storage failures**: Model artifacts may be corrupted or unavailable when needed for prediction.

OpenSTEF provides built-in mechanisms to handle each of these scenarios.

Fallback Forecasters for Baseline Predictions
----------------------------------------------

The simplest and most reliable fallback strategy is to use a naive baseline forecaster when sophisticated models fail. OpenSTEF includes ``BaseCaseForecaster``, which repeats weekly patterns from historical data:

.. code-block:: python

   from openstef_models.models.forecasting import BaseCaseForecaster
   from openstef_models.models.forecasting.forecaster import BaseCaseForecasterHyperParams
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta
   
   # Configure fallback forecaster with two-tier lag strategy
   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),   # Use last week
           fallback_lag=timedelta(days=14)  # Fall back to 2 weeks ago
       )
   )

The ``BaseCaseForecaster`` implements a two-tier fallback strategy internally. It first attempts to use data from 7 days ago (the primary lag). If that data is missing, it automatically falls back to 14 days ago. This ensures predictions are always available even when recent historical data has gaps.

In production, maintain both a sophisticated model (XGBoost, LightGBM) and a baseline forecaster. When the primary model fails, switch to the baseline:

.. code-block:: python

   from openstef_models.workflows import ForecastingWorkflow
   from openstef_core.exceptions import NotFittedError
   
   def generate_forecast(dataset, storage):
       """Generate forecast with automatic fallback to baseline."""
       try:
           # Try loading and using the production model
           workflow = ForecastingWorkflow.from_storage(
               model_id="production_xgb_model",
               storage=storage
           )
           return workflow.predict(dataset)
       except (NotFittedError, FileNotFoundError):
           # Fall back to baseline forecaster
           fallback_workflow = ForecastingWorkflow(
               model=ForecastingModel(forecaster=fallback_forecaster),
               model_id="baseline_fallback"
           )
           # Baseline doesn't need fitting, just predict
           return fallback_workflow.predict(dataset)

Handling Missing and Invalid Data
----------------------------------

OpenSTEF provides validation transforms that detect data quality issues before they cause prediction failures. Use these transforms in your preprocessing pipeline:

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker
   )
   from openstef_models.preprocessing import Preprocessing
   
   # Build preprocessing with validation checks
   preprocessing = Preprocessing(
       transforms=[
           CompletenessChecker(
               min_completeness=0.9,  # Require 90% complete data
               raise_on_incomplete=False  # Log warning instead of failing
           ),
           FlatlineChecker(
               check_ongoing=True,  # Detect if latest data is flat
               min_variance_threshold=0.01
           ),
           InputConsistencyChecker(),
           # ... other transforms
       ]
   )

The ``CompletenessChecker`` verifies that sufficient data is available. The ``FlatlineChecker`` detects when sensors are stuck or data feeds have frozen—a common production issue where data appears present but is actually stale repeated values.

When validation transforms detect issues, you have several options:

1. **Raise exceptions** to prevent bad forecasts from being generated
2. **Log warnings** and proceed with degraded data
3. **Trigger fallback** to baseline forecasters

For missing features, OpenSTEF's forecasters handle NaN values differently:

- **Tree-based models** (XGBoost, LightGBM) can handle missing values natively
- **Linear models** require imputation or will produce NaN predictions

Configure your workflow to handle insufficient data:

.. code-block:: python

   from openstef_core.exceptions import InsufficientlyCompleteError
   from openstef_models.workflows import ForecastingWorkflow
   
   def robust_training(dataset, storage):
       """Train model with graceful handling of insufficient data."""
       workflow = ForecastingWorkflow.from_storage(
           model_id="my_model",
           storage=storage
       )
       
       try:
           result = workflow.fit(dataset)
           return result
       except InsufficientlyCompleteError as e:
           # Not enough valid training data
           logging.warning(f"Skipping training: {e}")
           # Keep using existing model or schedule retry
           return None

The workflow automatically drops rows with NaN target values during training. If no valid training data remains after dropping NaNs, it raises ``InsufficientlyCompleteError``.

Detecting Model Staleness
--------------------------

Model performance degrades over time as patterns shift. Implement monitoring to detect when retraining is needed:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.evaluation.models import Window
   from datetime import timedelta
   
   # Configure evaluation to track recent performance
   eval_config = EvaluationConfig(
       windows=[
           Window(name="last_week", duration=timedelta(days=7)),
           Window(name="last_month", duration=timedelta(days=30))
       ],
       metrics=["rmse", "mae", "bias"]
   )
   
   pipeline = EvaluationPipeline(config=eval_config)
   report = pipeline.evaluate(predictions=forecasts, actuals=actuals)
   
   # Check if performance has degraded
   recent_rmse = report.get_metric("last_week", "rmse")
   baseline_rmse = report.get_metric("last_month", "rmse")
   
   if recent_rmse > baseline_rmse * 1.2:  # 20% degradation
       logging.warning("Model performance degraded, retraining recommended")
       trigger_retraining()

Compare recent performance against historical baselines. Significant degradation indicates the model has become stale and needs retraining with fresh data.

Also track model age explicitly:

.. code-block:: python

   from datetime import datetime, timedelta
   
   def check_model_age(workflow, max_age_days=30):
       """Check if model is too old and needs retraining."""
       if not workflow.model.is_fitted:
           return True  # Not fitted yet
       
       # Assuming you store training timestamp in model metadata
       training_date = workflow.model.metadata.get("training_date")
       if training_date is None:
           return True  # Unknown age, retrain to be safe
       
       age = datetime.now() - training_date
       if age > timedelta(days=max_age_days):
           logging.info(f"Model is {age.days} days old, triggering retrain")
           return True
       
       return False

Graceful Degradation Strategies
--------------------------------

When failures occur, degrade gracefully rather than failing completely. Implement a hierarchy of forecasting strategies:

.. code-block:: python

   from enum import IntEnum
   
   class ForecastQuality(IntEnum):
       """Quality levels for forecast degradation."""
       HIGH = 1      # Full ML model with all features
       MEDIUM = 2    # ML model with reduced features
       LOW = 3       # Baseline forecaster
       MINIMAL = 4   # Simple persistence (repeat last value)
   
   def generate_forecast_with_degradation(dataset, storage):
       """Generate best possible forecast given available data."""
       quality = ForecastQuality.HIGH
       
       # Try full-featured ML model
       try:
           workflow = ForecastingWorkflow.from_storage(
               model_id="production_model",
               storage=storage
           )
           forecasts = workflow.predict(dataset)
           return forecasts, quality
       except Exception as e:
           logging.warning(f"Primary model failed: {e}")
           quality = ForecastQuality.MEDIUM
       
       # Try baseline forecaster
       try:
           baseline = BaseCaseForecaster(
               horizons=dataset.horizons,
               quantiles=[Quantile(0.5)]
           )
           workflow = ForecastingWorkflow(
               model=ForecastingModel(forecaster=baseline),
               model_id="baseline"
           )
           forecasts = workflow.predict(dataset)
           return forecasts, quality
       except Exception as e:
           logging.error(f"Baseline forecaster failed: {e}")
           quality = ForecastQuality.LOW
       
       # Last resort: simple persistence
       last_value = dataset.data[dataset.target_column].iloc[-1]
       forecasts = create_persistence_forecast(last_value, dataset.horizons)
       return forecasts, ForecastQuality.MINIMAL

Tag forecasts with their quality level so downstream systems can make informed decisions. For example, don't trigger automated trading decisions on minimal-quality forecasts.

Production Checklist
--------------------

When deploying forecasting systems, ensure you have:

- **Fallback forecasters**: Always maintain a baseline forecaster (``BaseCaseForecaster``) as backup
- **Data validation**: Use ``CompletenessChecker`` and ``FlatlineChecker`` to detect bad input data
- **Error handling**: Catch ``InsufficientlyCompleteError``, ``NotFittedError``, and storage exceptions
- **Performance monitoring**: Track metrics over time to detect model degradation
- **Age tracking**: Monitor model training dates and trigger retraining on a schedule
- **Quality indicators**: Tag forecasts with quality levels for downstream decision-making
- **Alerting**: Set up alerts for fallback activation, validation failures, and performance degradation

These strategies ensure your forecasting system continues operating even when components fail, providing the best possible predictions given available data and models.

For more information on forecast evaluation and monitoring, see the evaluation documentation. For details on specific forecasting models and their failure modes, refer to :doc:`model_selection`.