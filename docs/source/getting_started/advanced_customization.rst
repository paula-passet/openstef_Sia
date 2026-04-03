Advanced Customization
======================

OpenSTEF provides several extension points for customizing forecasting workflows beyond the standard configuration options. This guide shows how to implement custom data preparation logic, build custom feature transforms, and create tailored pipeline workflows for specialized forecasting scenarios.

This page assumes you've completed the :doc:`first_forecast` tutorial and are familiar with basic OpenSTEF concepts.

Custom Feature Engineering
---------------------------

OpenSTEF's feature engineering system is built around the ``TimeSeriesTransform`` interface. You can create custom transforms to add domain-specific features or implement specialized preprocessing logic.

Creating a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To implement a custom transform, subclass ``TimeSeriesTransform`` and implement the required methods:

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class TemperatureHumidityIndex(TimeSeriesTransform):
       """Adds a heat index feature combining temperature and humidity."""
       
       def __init__(self, temp_column: str = "temp", humidity_column: str = "humidity"):
           self.temp_column = temp_column
           self.humidity_column = humidity_column
       
       @property
       def is_fitted(self) -> bool:
           # This transform is stateless, so always fitted
           return True
       
       def fit(self, data: TimeSeriesDataset) -> None:
           # No fitting required for this transform
           pass
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Calculate heat index from temperature and humidity."""
           df = data.data.copy()
           
           if self.temp_column in df.columns and self.humidity_column in df.columns:
               # Simplified heat index calculation
               T = df[self.temp_column]
               RH = df[self.humidity_column]
               df["heat_index"] = T + 0.5 * (T - 58.0) * (RH / 100.0)
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           """Return list of features added by this transform."""
           return ["heat_index"]

Stateful Transforms
^^^^^^^^^^^^^^^^^^^

For transforms that need to learn parameters from training data, implement the ``fit`` method and track fitted state:

.. code-block:: python

   class AdaptiveClipper(TimeSeriesTransform):
       """Clips features to percentile-based ranges learned from training data."""
       
       def __init__(self, features: list[str], lower_percentile: float = 1.0, 
                    upper_percentile: float = 99.0):
           self.features = features
           self.lower_percentile = lower_percentile
           self.upper_percentile = upper_percentile
           self.clip_ranges_ = None
       
       @property
       def is_fitted(self) -> bool:
           return self.clip_ranges_ is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn clipping ranges from training data."""
           self.clip_ranges_ = {}
           for feature in self.features:
               if feature in data.data.columns:
                   lower = data.data[feature].quantile(self.lower_percentile / 100.0)
                   upper = data.data[feature].quantile(self.upper_percentile / 100.0)
                   self.clip_ranges_[feature] = (lower, upper)
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply learned clipping ranges."""
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           df = data.data.copy()
           for feature, (lower, upper) in self.clip_ranges_.items():
               if feature in df.columns:
                   df[feature] = df[feature].clip(lower=lower, upper=upper)
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return []  # This transform modifies existing features

Integrating Custom Transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add custom transforms to a preprocessing pipeline:

.. code-block:: python

   from openstef_models.preprocessing import PreprocessingPipeline
   from openstef_models.transforms.general import AddMissingValuesIndicator
   
   # Create pipeline with custom transforms
   pipeline = PreprocessingPipeline(
       transforms=[
           AddMissingValuesIndicator(),
           TemperatureHumidityIndex(temp_column="temp", humidity_column="humidity"),
           AdaptiveClipper(features=["wind_speed", "radiation"]),
       ]
   )
   
   # Fit on training data
   pipeline.fit(data=train_dataset)
   
   # Transform both training and prediction data
   train_transformed = pipeline.transform(data=train_dataset)
   predict_transformed = pipeline.transform(data=predict_dataset)

Custom Data Preparation
------------------------

For advanced data preparation needs, you can customize how input data is processed before model training and prediction.

Customizing Model Preprocessing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Models in OpenSTEF use preprocessing pipelines that can be customized:

.. code-block:: python

   from openstef_models.models import XGBQuantileModel
   from openstef_models.preprocessing import PreprocessingPipeline
   from openstef_models.transforms.general import Clipper, AddMissingValuesIndicator
   
   # Create model with custom preprocessing
   model = XGBQuantileModel(
       target_column="load",
       quantiles=[0.1, 0.5, 0.9],
       preprocessing=PreprocessingPipeline(
           transforms=[
               AddMissingValuesIndicator(),
               Clipper(features=["wind_speed"], min_value=0.0, max_value=50.0),
               TemperatureHumidityIndex(),
           ]
       )
   )
   
   # Preprocessing is applied automatically during fit and predict
   model.fit(data=train_dataset)
   forecasts = model.predict(data=predict_dataset)

Model-Specific Preprocessing in Ensembles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ensemble models support both common preprocessing (applied to all base models) and model-specific preprocessing:

.. code-block:: python

   from openstef_models.models import EnsembleModel
   from openstef_models.preprocessing import PreprocessingPipeline
   
   # Common preprocessing for all models
   common_pipeline = PreprocessingPipeline(
       transforms=[
           AddMissingValuesIndicator(),
       ]
   )
   
   # Model-specific preprocessing
   xgb_pipeline = PreprocessingPipeline(
       transforms=[
           Clipper(features=["wind_speed"], min_value=0.0, max_value=50.0),
       ]
   )
   
   ensemble = EnsembleModel(
       target_column="load",
       base_models={"xgb": xgb_model, "lgb": lgb_model},
       preprocessing=common_pipeline,
       model_specific_preprocessing={"xgb": xgb_pipeline}
   )

Custom Pipeline Workflows
--------------------------

For production systems requiring custom orchestration, lifecycle hooks, or integration with external systems, you can build custom workflows using OpenSTEF's workflow components.

Using Callbacks for Lifecycle Hooks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks provide hooks into key workflow stages for logging, monitoring, or custom validation:

.. code-block:: python

   from openstef_models.workflows import CustomComponentSplitWorkflow, ComponentSplitCallback
   from openstef_core.datasets import TimeSeriesDataset, EnergyComponentDataset
   import logging
   
   class MonitoringCallback(ComponentSplitCallback):
       """Custom callback for monitoring component splitting workflow."""
       
       def __init__(self):
           self.logger = logging.getLogger(__name__)
       
       def on_fit_start(self, pipeline: CustomComponentSplitWorkflow, 
                       dataset: TimeSeriesDataset) -> None:
           """Called before model training begins."""
           self.logger.info(f"Starting training with {len(dataset.data)} samples")
           self.logger.info(f"Date range: {dataset.data.index.min()} to {dataset.data.index.max()}")
       
       def on_fit_end(self, pipeline: CustomComponentSplitWorkflow, 
                     dataset: TimeSeriesDataset) -> None:
           """Called after model training completes."""
           self.logger.info("Training completed successfully")
       
       def on_predict_start(self, pipeline: CustomComponentSplitWorkflow,
                           dataset: TimeSeriesDataset) -> None:
           """Called before prediction begins."""
           self.logger.info(f"Starting prediction for {len(dataset.data)} time points")
       
       def on_predict_end(self, pipeline: CustomComponentSplitWorkflow,
                         dataset: TimeSeriesDataset,
                         forecasts: EnergyComponentDataset) -> None:
           """Called after prediction completes."""
           components = forecasts.data.columns.tolist()
           self.logger.info(f"Generated forecasts for components: {components}")
   
   # Use callback in workflow
   workflow = CustomComponentSplitWorkflow(
       model=component_model,
       callbacks=MonitoringCallback()
   )

Building Custom Workflows
^^^^^^^^^^^^^^^^^^^^^^^^^^

For specialized orchestration needs, you can create custom workflow classes:

.. code-block:: python

   from openstef_core.base_model import BaseModel
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   from openstef_models.models import BaseForecastingModel
   from pydantic import Field
   
   class ValidationWorkflow(BaseModel):
       """Custom workflow with data validation and fallback logic."""
       
       primary_model: BaseForecastingModel
       fallback_model: BaseForecastingModel
       min_data_points: int = Field(default=100)
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Train both primary and fallback models."""
           # Validate input data
           if len(data.data) < self.min_data_points:
               raise ValueError(f"Insufficient data: {len(data.data)} < {self.min_data_points}")
           
           # Train both models
           self.primary_model.fit(data=data)
           self.fallback_model.fit(data=data)
       
       def predict(self, data: TimeSeriesDataset) -> ForecastDataset:
           """Generate forecasts with fallback on failure."""
           try:
               # Try primary model
               forecasts = self.primary_model.predict(data=data)
               
               # Validate output quality
               if self._validate_forecasts(forecasts):
                   return forecasts
               else:
                   print("Primary model forecasts failed validation, using fallback")
                   return self.fallback_model.predict(data=data)
           
           except Exception as e:
               print(f"Primary model failed: {e}, using fallback")
               return self.fallback_model.predict(data=data)
       
       def _validate_forecasts(self, forecasts: ForecastDataset) -> bool:
           """Check forecast quality."""
           # Check for NaN values
           if forecasts.data.isna().any().any():
               return False
           
           # Check for unrealistic values
           if (forecasts.data < 0).any().any():
               return False
           
           return True

Advanced Preprocessing Patterns
--------------------------------

Conditional Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create transforms that adapt based on data characteristics:

.. code-block:: python

   class ConditionalTransform(TimeSeriesTransform):
       """Applies different transforms based on data properties."""
       
       def __init__(self, threshold: float = 100.0):
           self.threshold = threshold
           self.use_log_transform_ = None
       
       @property
       def is_fitted(self) -> bool:
           return self.use_log_transform_ is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Decide transformation strategy based on data range."""
           target_range = data.data["load"].max() - data.data["load"].min()
           self.use_log_transform_ = target_range > self.threshold
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply chosen transformation."""
           df = data.data.copy()
           
           if self.use_log_transform_:
               df["load_transformed"] = np.log1p(df["load"])
           else:
               df["load_transformed"] = df["load"]
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return ["load_transformed"]

Next Steps
----------

- See :doc:`backtesting` for evaluating custom models and pipelines
- Explore the API reference for detailed documentation on transform interfaces
- Check the examples repository for more advanced customization patterns

.. note::

   When implementing custom components, ensure they follow OpenSTEF's fit/transform pattern and properly handle missing data and edge cases. Always validate custom transforms on held-out data before production deployment.