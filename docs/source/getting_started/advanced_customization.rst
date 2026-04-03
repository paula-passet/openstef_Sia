Advanced Customization
======================

This guide shows how to extend OpenSTEF beyond the standard workflows. You'll learn how to customize data preparation, build custom feature engineering transforms, and modify pipeline behavior to match your specific forecasting needs.

OpenSTEF is designed with clear extension points that let you inject custom logic without modifying the library itself. The key patterns are:

- **Custom transforms** for feature engineering and data preprocessing
- **Custom workflows** with callbacks for lifecycle hooks
- **Custom pipelines** that compose transforms in specific ways

Understanding the Pipeline Architecture
----------------------------------------

OpenSTEF separates concerns into distinct pipeline stages:

1. **Preprocessing**: Feature engineering and data preparation
2. **Forecasting**: Model training and prediction
3. **Postprocessing**: Confidence intervals and result transformation

Each stage uses a ``TransformPipeline`` that chains transforms together. You can customize any stage by providing your own transforms or replacing entire pipelines.

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.transforms import TransformPipeline
   
   # Standard model with default preprocessing
   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=[
           # Your custom transforms here
       ]),
       forecaster=xgb_forecaster,
       postprocessing=TransformPipeline(transforms=[
           # Your custom postprocessing
       ]),
       target_column="load",
   )

Creating Custom Transforms
---------------------------

Custom transforms let you add domain-specific feature engineering. All transforms inherit from ``TimeSeriesTransform`` and implement two methods: ``transform()`` and ``features_added()``.

Here's a complete example that adds rolling statistics:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.base import TimeSeriesTransform
   from pydantic import BaseModel
   
   class RollingStatsTransform(TimeSeriesTransform, BaseModel):
       """Add rolling mean and std features."""
       
       window_hours: int = 24
       columns: list[str]
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply rolling statistics to specified columns."""
           df = data.data.copy()
           
           for col in self.columns:
               if col not in df.columns:
                   continue
                   
               # Add rolling mean
               df[f"{col}_rolling_mean_{self.window_hours}h"] = (
                   df[col].rolling(window=self.window_hours).mean()
               )
               
               # Add rolling std
               df[f"{col}_rolling_std_{self.window_hours}h"] = (
                   df[col].rolling(window=self.window_hours).std()
               )
           
           return data.copy_with(df)
       
       def features_added(self) -> list[str]:
           """Return names of features this transform adds."""
           features = []
           for col in self.columns:
               features.append(f"{col}_rolling_mean_{self.window_hours}h")
               features.append(f"{col}_rolling_std_{self.window_hours}h")
           return features

Use your custom transform in a preprocessing pipeline:

.. code-block:: python

   from openstef_models.transforms.general import AddMissingValuesFeature
   from openstef_models.transforms.temporal import AddTemporalFeatures
   
   preprocessing = TransformPipeline(transforms=[
       AddTemporalFeatures(),
       RollingStatsTransform(
           window_hours=24,
           columns=["load", "temperature"]
       ),
       AddMissingValuesFeature(),
   ])
   
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=your_forecaster,
       target_column="load",
   )

Stateful Transforms with Fit/Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For transforms that need to learn from training data (like scalers or clippers), implement the ``fit()`` method:

.. code-block:: python

   class CustomClipper(TimeSeriesTransform, BaseModel):
       """Clip features to observed ranges from training data."""
       
       columns: list[str]
       min_values_: dict[str, float] = {}
       max_values_: dict[str, float] = {}
       is_fitted: bool = False
       
       def fit(self, data: TimeSeriesDataset) -> "CustomClipper":
           """Learn min/max values from training data."""
           df = data.data
           
           for col in self.columns:
               if col in df.columns:
                   self.min_values_[col] = df[col].min()
                   self.max_values_[col] = df[col].max()
           
           self.is_fitted = True
           return self
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Clip values to learned ranges."""
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           df = data.data.copy()
           
           for col in self.columns:
               if col in df.columns and col in self.min_values_:
                   df[col] = df[col].clip(
                       lower=self.min_values_[col],
                       upper=self.max_values_[col]
                   )
           
           return data.copy_with(df)
       
       def features_added(self) -> list[str]:
           return []  # Modifies existing features, doesn't add new ones

Custom Workflows with Callbacks
--------------------------------

Workflows orchestrate the complete training and prediction lifecycle. Use callbacks to inject custom logic at specific points without modifying the workflow itself.

The ``CustomForecastingWorkflow`` provides hooks for:

- ``on_fit_start``: Before training begins
- ``on_fit_end``: After training completes
- ``on_predict_start``: Before prediction
- ``on_predict_end``: After prediction

Here's a callback that logs feature importance after training:

.. code-block:: python

   from openstef_models.workflows import (
       CustomForecastingWorkflow,
       ForecastingCallback,
       WorkflowContext,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.forecasting_model import ModelFitResult
   import logging
   
   logger = logging.getLogger(__name__)
   
   class FeatureImportanceLogger(ForecastingCallback):
       """Log feature importance after model training."""
       
       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult,
       ) -> None:
           """Extract and log feature importance."""
           model = context.workflow.model
           
           if hasattr(model.forecaster, "feature_importance_dataframe"):
               importance_df = model.forecaster.feature_importance_dataframe
               
               logger.info("Top 10 most important features:")
               top_features = importance_df.nlargest(10, "importance")
               for idx, row in top_features.iterrows():
                   logger.info(f"  {row['feature']}: {row['importance']:.4f}")

Use the callback in your workflow:

.. code-block:: python

   workflow = CustomForecastingWorkflow(
       model=your_model,
       model_id="custom_forecast",
       callbacks=[
           FeatureImportanceLogger(),
           # Add other callbacks here
       ],
   )
   
   # Callbacks fire automatically during fit/predict
   workflow.fit(data=train_data)
   predictions = workflow.predict(data=test_data)

Custom Data Preparation
-----------------------

For complex data preparation needs, create a custom preprocessing pipeline that handles your specific data format:

.. code-block:: python

   from openstef_models.transforms.temporal import AddTemporalFeatures
   from openstef_models.transforms.weather import AddWeatherFeatures
   from openstef_models.transforms.general import AddMissingValuesFeature
   
   def create_custom_preprocessing(
       weather_columns: list[str],
       lag_hours: list[int],
   ) -> TransformPipeline:
       """Build a custom preprocessing pipeline."""
       
       transforms = [
           # Temporal features first
           AddTemporalFeatures(),
           
           # Weather-specific features
           AddWeatherFeatures(columns=weather_columns),
           
           # Your custom domain logic
           RollingStatsTransform(
               window_hours=24,
               columns=["load"] + weather_columns
           ),
           
           # Lag features
           AddLagFeatures(lag_hours=lag_hours),
           
           # Handle missing values last
           AddMissingValuesFeature(),
       ]
       
       return TransformPipeline(transforms=transforms)
   
   # Use in model
   model = ForecastingModel(
       preprocessing=create_custom_preprocessing(
           weather_columns=["temperature", "wind_speed"],
           lag_hours=[1, 24, 168],
       ),
       forecaster=forecaster,
       target_column="load",
   )

Model-Specific Preprocessing for Ensembles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ensemble models support both common preprocessing (applied to all models) and model-specific preprocessing:

.. code-block:: python

   from openstef_models.models import EnsembleForecastingModel
   
   ensemble = EnsembleForecastingModel(
       # Common preprocessing for all models
       preprocessing=TransformPipeline(transforms=[
           AddTemporalFeatures(),
           AddMissingValuesFeature(),
       ]),
       
       # Model-specific preprocessing
       model_specific_preprocessing={
           "xgb": TransformPipeline(transforms=[
               CustomClipper(columns=["temperature"]),
           ]),
           "lgbm": TransformPipeline(transforms=[
               RollingStatsTransform(window_hours=48, columns=["load"]),
           ]),
       },
       
       forecasters={"xgb": xgb_model, "lgbm": lgbm_model},
       target_column="load",
   )

The common preprocessing runs first, then each model's specific preprocessing transforms the common output before training or prediction.

Integrating with Existing Pipelines
------------------------------------

When working with existing OpenSTEF pipelines, you can inject custom components at specific points. For example, to add custom preprocessing to a standard forecasting configuration:

.. code-block:: python

   from openstef_models.workflows.factories import create_forecasting_workflow
   from openstef_models.workflows.configs import ForecastingWorkflowConfig
   
   # Start with standard config
   config = ForecastingWorkflowConfig(
       model="xgb",
       location=your_location,
       target_column="load",
       # ... other config
   )
   
   # Create workflow
   workflow = create_forecasting_workflow(config)
   
   # Inject custom preprocessing
   custom_transforms = [
       RollingStatsTransform(window_hours=24, columns=["load"]),
   ]
   
   # Prepend to existing preprocessing
   existing_transforms = workflow.model.preprocessing.transforms
   workflow.model.preprocessing = TransformPipeline(
       transforms=custom_transforms + existing_transforms
   )

Best Practices
--------------

**Keep transforms focused**: Each transform should do one thing well. Compose multiple simple transforms rather than creating complex monolithic ones.

**Use Pydantic for configuration**: Inherit from ``BaseModel`` to get automatic validation and serialization of transform parameters.

**Handle missing data gracefully**: Check if columns exist before transforming them. Not all datasets will have all features.

**Document feature names**: The ``features_added()`` method is crucial for debugging and feature importance analysis.

**Test transforms independently**: Write unit tests for your transforms using sample ``TimeSeriesDataset`` objects before integrating into pipelines.

**Fit on training data only**: Stateful transforms should only learn from training data, never from validation or test sets.

Next Steps
----------

- See :doc:`first_forecast` for basic model training patterns
- See :doc:`backtesting` for evaluating custom models
- Explore the API reference for built-in transforms in ``openstef_models.transforms``