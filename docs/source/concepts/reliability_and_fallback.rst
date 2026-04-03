Reliability and Fallback Strategies
====================================

Production forecasting systems must handle failures gracefully. Models can fail to train, input data may be incomplete or corrupted, and external dependencies can become unavailable. This page covers strategies for building reliable forecasting systems that degrade gracefully rather than failing catastrophically.

Why Reliability Matters
-----------------------

In production environments, forecasting systems often feed critical business processes—energy trading, grid balancing, capacity planning. A missing forecast can be worse than a simple forecast, because downstream systems may not know how to handle the gap. OpenSTEF provides multiple layers of defense to ensure your system always produces a forecast, even when conditions are suboptimal.

Fallback Forecasters
--------------------

The most fundamental reliability strategy is to use a fallback forecaster when your primary model fails or cannot be trained. OpenSTEF provides baseline forecasters specifically designed for this purpose.

BaseCaseForecaster: Weekly Pattern Repetition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``BaseCaseForecaster`` implements a simple but effective fallback: it repeats the pattern from the previous week. This works well for energy forecasting because load patterns typically exhibit strong weekly periodicity.

.. code-block:: python

   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   # Create a fallback forecaster
   fallback = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),    # Use last week's pattern
           fallback_lag=timedelta(days=14),  # If unavailable, use 2 weeks ago
       )
   )

The ``BaseCaseForecaster`` has its own internal fallback logic: if data from 7 days ago is missing, it automatically falls back to 14 days ago. This two-tier approach handles common data gaps.

When to Use Fallback Forecasters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Consider using a fallback forecaster in these scenarios:

- **Initial deployment**: Before you have enough historical data to train a machine learning model
- **Model training failures**: When the primary model fails to train due to data quality issues
- **Cold start problems**: For new prediction locations with no historical model
- **Extreme data gaps**: When input features are unavailable for extended periods

The fallback forecaster should be simple and robust—it's your last line of defense.

Handling Missing and Bad Data
------------------------------

Data quality issues are inevitable in production systems. OpenSTEF provides validation transforms that detect problems early and handle them appropriately.

Validation Transforms
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes several validation transforms that check data quality before training or prediction:

.. code-block:: python

   from openstef_models.transforms.validation import (
       InputConsistencyChecker,
       FlatlineChecker,
       CompletenessChecker,
   )
   from openstef_models.workflows.forecasting_workflow import (
       ForecastingWorkflow,
       ForecastingWorkflowConfig,
   )

   # Configure validation checks
   config = ForecastingWorkflowConfig(
       target_column="load",
       flatliner_threshold=0.95,           # Detect if 95%+ of values are identical
       detect_non_zero_flatliner=True,     # Also check for constant non-zero values
       # ... other config
   )

   workflow = ForecastingWorkflow(model=my_model, config=config)

**InputConsistencyChecker** validates that the input data structure matches what the model expects—correct columns, proper index frequency, and consistent data types.

**FlatlineChecker** detects when recent measurements show suspiciously constant values, which often indicates sensor failures or data pipeline issues. By default, it logs warnings but doesn't block training or prediction (``error_on_flatliner=False``). You can configure it to raise errors if your system has alternative data sources.

**CompletenessChecker** ensures sufficient data is available for training. It raises an ``InsufficientlyCompleteError`` if too much data is missing.

Handling NaN Values
^^^^^^^^^^^^^^^^^^^

OpenSTEF workflows automatically handle NaN (missing) values in the target column during training:

.. code-block:: python

   # The workflow automatically drops rows where the target is NaN
   result = workflow.fit(data)  # Rows with NaN in target_column are dropped

   # If ALL target values are NaN, an InsufficientlyCompleteError is raised
   # This prevents training on empty data

For prediction, the behavior depends on the forecaster. The ``MedianForecaster`` and similar models return NaN predictions when required lag features are missing, rather than failing entirely. This allows partial predictions when some data is available.

Model Staleness Detection
--------------------------

Models degrade over time as the underlying patterns in your data shift. OpenSTEF provides mechanisms to detect stale models and trigger retraining.

Maximum Model Age
^^^^^^^^^^^^^^^^^

The simplest staleness detection is age-based. Configure a maximum age for models:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.workflows.ensemble_forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
   )

   config = EnsembleForecastingWorkflowConfig(
       target_column="load",
       max_age=timedelta(days=7),  # Retrain if model is older than 7 days
       # ... other config
   )

When loading a model from storage, the workflow checks its age. If the model exceeds ``max_age``, the workflow will retrain automatically on the next fit operation.

Performance-Based Model Selection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

More sophisticated than simple age checks, OpenSTEF can compare old and new models based on validation performance:

.. code-block:: python

   from openstef_core.types import Q

   config = EnsembleForecastingWorkflowConfig(
       target_column="load",
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,  # New model must be 20% better
       # ... other config
   )

With ``model_selection_enable=True``, the workflow trains a new model and compares its validation performance against the existing model. The ``model_selection_old_model_penalty`` parameter biases selection toward newer models—the new model must be significantly better (20% in this example) to replace the old one. This prevents unnecessary model churn from minor performance fluctuations.

The metric tuple specifies:

1. Which quantile to evaluate (or use a global metric)
2. Which metric to use (R2, MAE, RMSE, etc.)
3. Whether higher or lower values are better

Graceful Degradation Strategies
--------------------------------

A robust production system should degrade gracefully through multiple fallback layers.

Multi-Tier Fallback Architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Design your system with multiple fallback tiers:

1. **Primary model**: Your best-performing machine learning model (XGBoost, LightGBM, etc.)
2. **Secondary model**: A simpler but more robust model (linear regression, median forecaster)
3. **Tertiary fallback**: BaseCaseForecaster with weekly pattern repetition
4. **Ultimate fallback**: Return historical median or a constant value

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgb_quantile_forecaster import XGBQuantileForecaster
   from openstef_models.models.forecasting.median_forecaster import MedianForecaster
   from openstef_models.models.forecasting.base_case_forecaster import BaseCaseForecaster

   def create_robust_forecasting_system(horizons, quantiles):
       """Create a forecasting system with multiple fallback layers."""
       
       # Primary: XGBoost model
       primary = ForecastingModel(
           forecaster=XGBQuantileForecaster(horizons=horizons, quantiles=quantiles)
       )
       
       # Secondary: Simple median-based model
       secondary = ForecastingModel(
           forecaster=MedianForecaster(horizons=horizons, quantiles=quantiles)
       )
       
       # Tertiary: Pattern repetition
       tertiary = ForecastingModel(
           forecaster=BaseCaseForecaster(horizons=horizons, quantiles=quantiles)
       )
       
       return primary, secondary, tertiary

   def predict_with_fallback(data, primary, secondary, tertiary):
       """Attempt prediction with multiple fallback layers."""
       try:
           forecasts = primary.predict(data)
           if not forecasts.data.empty:
               return forecasts, "primary"
       except Exception as e:
           print(f"Primary model failed: {e}")
       
       try:
           forecasts = secondary.predict(data)
           if not forecasts.data.empty:
               return forecasts, "secondary"
       except Exception as e:
           print(f"Secondary model failed: {e}")
       
       try:
           forecasts = tertiary.predict(data)
           return forecasts, "tertiary"
       except Exception as e:
           print(f"All models failed: {e}")
           raise

Storage-Based Fallback
^^^^^^^^^^^^^^^^^^^^^^

When using model storage, the workflow automatically implements a fallback strategy:

.. code-block:: python

   from openstef_models.workflows.forecasting_workflow import ForecastingWorkflow

   # Try to load from storage, fall back to creating new model
   workflow = ForecastingWorkflow.from_storage(
       model_id="production_model_v1",
       storage=my_storage,
       # If model doesn't exist or is too old, workflow will create new one
   )

The ``from_storage`` method loads an existing model if available, but doesn't fail if the model is missing. Combined with age-based checks, this provides automatic fallback to retraining when needed.

Monitoring and Alerting
------------------------

Implement monitoring to detect when fallback strategies are being used frequently:

- **Fallback usage rate**: Track how often each fallback tier is used
- **Data quality metrics**: Monitor validation failure rates, NaN percentages, flatliner detection
- **Model age**: Alert when models approach their maximum age
- **Prediction quality**: Compare forecast accuracy across different model tiers

Frequent fallback usage indicates underlying problems that need investigation—data pipeline issues, concept drift, or insufficient training data.

Best Practices
--------------

1. **Always have a fallback**: Never deploy a system that can fail to produce a forecast
2. **Test failure modes**: Regularly test your fallback strategies with corrupted or missing data
3. **Log fallback usage**: Track when and why fallbacks are triggered for debugging
4. **Set appropriate thresholds**: Configure validation thresholds based on your data characteristics
5. **Monitor model age**: Implement automated retraining before models become stale
6. **Validate fallback quality**: Ensure your fallback forecasts are good enough for downstream systems

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding short-term energy forecasting fundamentals
- :doc:`model_selection` - Choosing the right primary forecasting model
- :doc:`architecture` - System architecture and component interactions