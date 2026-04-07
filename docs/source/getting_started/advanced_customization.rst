Advanced Customization
======================

This guide shows how to extend OpenSTEF for specialized forecasting needs. You'll learn how to customize data preparation, build custom feature engineering transforms, and create tailored workflow pipelines.

OpenSTEF is designed with clear extension points that let you modify behavior without forking the library. The three main customization areas are:

- **Data preparation**: Custom preprocessing transforms
- **Feature engineering**: Domain-specific feature transforms
- **Workflow pipelines**: Custom training and prediction logic

When to Customize
-----------------

Use the standard library components when possible—they're tested and optimized for common energy forecasting scenarios. Consider customization when you have:

- Domain-specific features (e.g., specialized weather transformations)
- Unique data quality requirements
- Custom model selection or storage logic
- Specific callback requirements for monitoring or logging

For basic forecasting workflows, see :doc:`first_forecast`. For model comparison, see :doc:`backtesting`.

Custom Data Preparation
-----------------------

Data preparation transforms implement the ``TimeSeriesTransform`` interface. They process ``TimeSeriesDataset`` objects and can be chained in a ``TransformPipeline``.

Creating a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a custom transform that adds a rolling average feature:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.base import TimeSeriesTransform
   from pydantic import BaseModel
   import pandas as pd

   class RollingAverageTransform(TimeSeriesTransform, BaseModel):
       """Add rolling average features to the dataset."""
       
       window_hours: int = 24
       columns: list[str] = ["load"]
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply rolling average to specified columns."""
           df = data.data.copy()
           
           for col in self.columns:
               if col in df.columns:
                   feature_name = f"{col}_rolling_{self.window_hours}h"
                   df[feature_name] = df[col].rolling(
                       window=self.window_hours,
                       min_periods=1
                   ).mean()
           
           return data.copy_with(df)
       
       def features_added(self) -> list[str]:
           """Return list of features added by this transform."""
           return [f"{col}_rolling_{self.window_hours}h" for col in self.columns]

Use it in a preprocessing pipeline:

.. code-block:: python

   from openstef_models.preprocessing import TransformPipeline
   from openstef_models.transforms.general import AddMissingValuesColumn

   preprocessing = TransformPipeline(transforms=[
       AddMissingValuesColumn(),
       RollingAverageTransform(window_hours=24, columns=["load", "temperature"]),
   ])
   
   # Fit and transform
   preprocessing.fit(data=training_data)
   transformed_data = preprocessing.transform(data=training_data)

Stateful Transforms
^^^^^^^^^^^^^^^^^^^

Some transforms need to learn from training data. Implement ``fit()`` for these cases:

.. code-block:: python

   class FeatureScaler(TimeSeriesTransform, BaseModel):
       """Scale features based on training data statistics."""
       
       columns: list[str]
       mean_: dict[str, float] = {}
       std_: dict[str, float] = {}
       
       def fit(self, data: TimeSeriesDataset) -> "FeatureScaler":
           """Learn scaling parameters from training data."""
           df = data.data
           for col in self.columns:
               if col in df.columns:
                   self.mean_[col] = df[col].mean()
                   self.std_[col] = df[col].std()
           return self
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply learned scaling."""
           df = data.data.copy()
           for col in self.columns:
               if col in self.mean_:
                   df[col] = (df[col] - self.mean_[col]) / self.std_[col]
           return data.copy_with(df)
       
       @property
       def is_fitted(self) -> bool:
           return len(self.mean_) > 0

The ``TransformPipeline`` automatically calls ``fit()`` on all transforms when you call ``pipeline.fit()``.

Custom Feature Engineering
---------------------------

OpenSTEF provides domain-specific transforms in ``openstef_models.transforms``. You can create similar transforms for your domain.

Energy Domain Example
^^^^^^^^^^^^^^^^^^^^^

Here's a custom transform for solar power features:

.. code-block:: python

   import numpy as np
   from openstef_models.transforms.base import TimeSeriesTransform
   from pydantic import BaseModel

   class SolarAngleFeatureAdder(TimeSeriesTransform, BaseModel):
       """Add solar angle features for PV forecasting."""
       
       latitude: float
       longitude: float
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Calculate solar elevation and azimuth angles."""
           df = data.data.copy()
           
           # Simplified solar angle calculation
           # In practice, use a library like pvlib
           hour_angle = (df.index.hour - 12) * 15  # degrees
           
           # Solar elevation (simplified)
           df["solar_elevation"] = np.clip(
               90 - abs(hour_angle),
               0,
               90
           )
           
           # Solar azimuth (simplified)
           df["solar_azimuth"] = hour_angle + 180
           
           return data.copy_with(df)
       
       def features_added(self) -> list[str]:
           return ["solar_elevation", "solar_azimuth"]

Combine with existing transforms:

.. code-block:: python

   from openstef_models.transforms.temporal import AddTemporalFeatures
   from openstef_models.transforms.weather import AddWeatherFeatures

   preprocessing = TransformPipeline(transforms=[
       AddTemporalFeatures(),
       AddWeatherFeatures(weather_columns=["radiation", "temperature"]),
       SolarAngleFeatureAdder(latitude=52.0, longitude=5.0),
   ])

Custom Workflow Pipelines
--------------------------

Workflows orchestrate the complete training and prediction process. They integrate models, preprocessing, and callbacks for monitoring and storage.

The ``CustomForecastingWorkflow`` class provides the foundation. You can extend it with custom callbacks for specialized behavior.

Creating Custom Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks hook into workflow lifecycle events. Here's a callback that logs feature importance:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       ForecastingCallback,
       CustomForecastingWorkflow,
       WorkflowContext,
   )
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
           """Log top features after training."""
           if hasattr(result, "feature_importance"):
               importance = result.feature_importance
               top_features = importance.nlargest(10)
               
               logger.info("Top 10 features:")
               for feature, score in top_features.items():
                   logger.info(f"  {feature}: {score:.4f}")

Use callbacks in a workflow:

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.forecasters.xgboost import XGBForecaster

   workflow = CustomForecastingWorkflow(
       model=ForecastingModel(
           preprocessing=preprocessing,
           forecaster=XGBForecaster(),
           target_column="load",
       ),
       callbacks=[
           FeatureImportanceLogger(),
       ],
   )
   
   # Train with callback execution
   workflow.fit(data=training_data)

Custom Model Selection
^^^^^^^^^^^^^^^^^^^^^^^

Implement custom model selection logic with callbacks:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   class CustomModelSelector(ForecastingCallback):
       """Select models based on custom criteria."""
       
       def __init__(self, metric_threshold: float = 0.1):
           self.metric_threshold = metric_threshold
           self.best_score = float("inf")
       
       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult,
       ) -> None:
           """Evaluate model and decide whether to keep it."""
           if result.metrics and "rmse" in result.metrics:
               current_score = result.metrics["rmse"]
               
               if current_score < self.best_score * (1 - self.metric_threshold):
                   logger.info(f"New best model: RMSE={current_score:.2f}")
                   self.best_score = current_score
                   # Store model (implementation depends on your storage)
               else:
                   logger.info(f"Model not improved: RMSE={current_score:.2f}")

Combining Custom Components
----------------------------

Here's a complete example combining custom transforms, features, and workflows:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.forecasters.xgboost import XGBForecaster
   from openstef_models.preprocessing import TransformPipeline
   from openstef_models.transforms.temporal import AddTemporalFeatures

   # Build custom preprocessing pipeline
   preprocessing = TransformPipeline(transforms=[
       AddTemporalFeatures(),
       RollingAverageTransform(window_hours=24, columns=["load"]),
       SolarAngleFeatureAdder(latitude=52.0, longitude=5.0),
       FeatureScaler(columns=["load", "temperature"]),
   ])

   # Create model with custom components
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=XGBForecaster(
           max_depth=6,
           n_estimators=100,
       ),
       target_column="load",
   )

   # Build workflow with custom callbacks
   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[
           FeatureImportanceLogger(),
           CustomModelSelector(metric_threshold=0.05),
       ],
   )

   # Train and predict
   workflow.fit(data=training_data, data_val=validation_data)
   predictions = workflow.predict(data=forecast_input)

Best Practices
--------------

**Keep transforms focused**: Each transform should do one thing well. Chain multiple transforms rather than creating complex single transforms.

**Test transforms independently**: Write unit tests for custom transforms before integrating them into pipelines.

**Document feature additions**: Use ``features_added()`` to clearly indicate what features your transforms create.

**Handle missing data gracefully**: Check for column existence and handle edge cases in your transforms.

**Use type hints**: Leverage Pydantic's validation for configuration parameters.

**Profile performance**: Custom transforms run on every training and prediction cycle. Profile them if you have performance concerns.

Next Steps
----------

- Explore the :doc:`/api/index` for detailed class documentation
- See :doc:`backtesting` for comparing custom models
- Review ``openstef_models.transforms`` source code for more transform examples