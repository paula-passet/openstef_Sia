Advanced Customization
======================

OpenSTEF is designed for extensibility. This guide shows how to customize the library's core components: data preparation pipelines, feature engineering, and workflow orchestration. These techniques let you adapt OpenSTEF to your specific forecasting requirements while maintaining the benefits of the library's architecture.

This page assumes you've completed the :doc:`quickstart` and :doc:`first_forecast` tutorials.

Custom Feature Engineering
---------------------------

OpenSTEF's feature engineering is built on a transform pipeline system. You can add custom transforms by implementing the ``TimeSeriesTransform`` interface.

Creating a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Custom transforms follow the scikit-learn pattern with ``fit()`` and ``transform()`` methods:

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class TemperatureInteractionTransform(TimeSeriesTransform):
       """Add interaction features between temperature and time of day."""
       
       def __init__(self, temp_column: str = "temperature"):
           self.temp_column = temp_column
           self._fitted = False
       
       @property
       def is_fitted(self) -> bool:
           return self._fitted
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Fit is called during training to learn parameters."""
           # For stateless transforms, just mark as fitted
           self._fitted = True
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply the transformation to the data."""
           df = data.data.copy()
           
           # Add hour of day if not present
           if "hour" not in df.columns:
               df["hour"] = df.index.hour
           
           # Create interaction features
           df["temp_morning"] = df[self.temp_column] * (df["hour"] < 12).astype(int)
           df["temp_evening"] = df[self.temp_column] * (df["hour"] >= 18).astype(int)
           
           return data.copy_with(df)
       
       def features_added(self) -> list[str]:
           """List features added by this transform."""
           return ["temp_morning", "temp_evening"]

Stateful transforms can learn parameters during ``fit()``:

.. code-block:: python

   class AdaptiveScalerTransform(TimeSeriesTransform):
       """Scale features based on training data statistics."""
       
       def __init__(self, columns: list[str]):
           self.columns = columns
           self.means_ = None
           self.stds_ = None
       
       @property
       def is_fitted(self) -> bool:
           return self.means_ is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn scaling parameters from training data."""
           df = data.data
           self.means_ = df[self.columns].mean()
           self.stds_ = df[self.columns].std()
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply learned scaling."""
           if not self.is_fitted:
               raise NotFittedError("Transform must be fitted before transform")
           
           df = data.data.copy()
           df[self.columns] = (df[self.columns] - self.means_) / self.stds_
           
           return data.copy_with(df)
       
       def features_added(self) -> list[str]:
           return []  # Modifies existing features, doesn't add new ones

Integrating Custom Transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add custom transforms to a model's preprocessing pipeline:

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_models.models.xgboost import XGBForecastingModel, XGBForecastingModelConfig
   from openstef_models.transforms.general import Imputer, ImputerConfig
   
   # Create preprocessing pipeline with custom transform
   preprocessing = TransformPipeline(transforms=[
       Imputer(ImputerConfig(columns=["temperature", "wind_speed"])),
       TemperatureInteractionTransform(temp_column="temperature"),
       AdaptiveScalerTransform(columns=["temperature", "wind_speed"]),
   ])
   
   # Create model with custom preprocessing
   model = XGBForecastingModel(
       XGBForecastingModelConfig(
           target="load",
           horizons=[0.25, 24.0, 47.0],
       ),
       preprocessing=preprocessing,
   )
   
   # Fit and predict - preprocessing is applied automatically
   model.fit(training_data)
   forecast = model.predict(input_data)

The pipeline applies transforms sequentially. Each transform receives the output of the previous transform during both ``fit()`` and ``transform()``.

Custom Data Preparation
------------------------

Beyond feature engineering, you may need to customize how data flows through the forecasting process.

Custom Input Preparation
^^^^^^^^^^^^^^^^^^^^^^^^^

Override ``prepare_input()`` to customize data preparation before forecasting:

.. code-block:: python

   from openstef_models.models.xgboost import XGBForecastingModel
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import datetime
   
   class CustomInputModel(XGBForecastingModel):
       """Model with custom input preparation logic."""
       
       def prepare_input(
           self,
           data: TimeSeriesDataset,
           forecast_start: datetime | None = None,
       ) -> TimeSeriesDataset:
           """Add custom data validation and preparation."""
           # Apply base preprocessing
           prepared = super().prepare_input(data, forecast_start)
           
           # Add custom logic
           df = prepared.data.copy()
           
           # Example: Ensure minimum data quality
           required_columns = ["temperature", "wind_speed"]
           for col in required_columns:
               if col in df.columns:
                   missing_pct = df[col].isna().mean()
                   if missing_pct > 0.3:
                       raise ValueError(f"Column {col} has {missing_pct:.1%} missing values")
           
           # Example: Add derived features
           if "temperature" in df.columns:
               df["temp_squared"] = df["temperature"] ** 2
           
           return prepared.copy_with(df)

This approach gives you full control over data preparation while preserving the library's structure.

Custom Workflow Orchestration
------------------------------

For production systems, you may need custom workflow logic beyond basic training and prediction.

Using Workflow Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks let you hook into workflow lifecycle events without modifying core logic:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.workflows.callbacks import ForecastingCallback, WorkflowContext
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   import logging
   
   class DataQualityCallback(ForecastingCallback):
       """Monitor data quality during workflow execution."""
       
       def on_fit_start(
           self,
           context: WorkflowContext,
           data: TimeSeriesDataset,
       ) -> None:
           """Log data quality metrics before training."""
           df = data.data
           logger = logging.getLogger(__name__)
           
           logger.info(f"Training data shape: {df.shape}")
           logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
           
           # Check for missing values
           missing = df.isna().sum()
           if missing.any():
               logger.warning(f"Missing values detected:\n{missing[missing > 0]}")
       
       def on_predict_end(
           self,
           context: WorkflowContext,
           data: TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           """Validate forecast output."""
           logger = logging.getLogger(__name__)
           
           forecast_df = result.data
           if (forecast_df["forecast"] < 0).any():
               logger.error("Negative forecast values detected!")

Use callbacks in a workflow:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   
   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[DataQualityCallback()],
   )
   
   # Callbacks are invoked automatically
   workflow.fit(training_data)
   forecast = workflow.predict(input_data)

Custom Workflow Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For complete control, create a custom workflow class:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   
   class MultiStageWorkflow(CustomForecastingWorkflow):
       """Workflow with multi-stage forecasting logic."""
       
       def predict(
           self,
           data: TimeSeriesDataset,
           forecast_start: datetime | None = None,
       ) -> ForecastDataset:
           """Generate forecast with custom multi-stage logic."""
           # Stage 1: Generate base forecast
           base_forecast = super().predict(data, forecast_start)
           
           # Stage 2: Apply custom post-processing
           forecast_df = base_forecast.data.copy()
           
           # Example: Apply business rules
           forecast_df.loc[forecast_df["forecast"] < 0, "forecast"] = 0
           
           # Example: Adjust for known events
           weekend_mask = forecast_df.index.dayofweek >= 5
           forecast_df.loc[weekend_mask, "forecast"] *= 0.85
           
           return base_forecast.copy_with(forecast_df)

This pattern is useful for complex production requirements like ensemble forecasting, conditional logic, or integration with external systems.

Extension Points Summary
------------------------

OpenSTEF provides several key extension points:

- **TimeSeriesTransform**: Add custom feature engineering logic
- **TransformPipeline**: Chain multiple transforms with automatic fit/transform
- **Model.prepare_input()**: Customize data preparation before forecasting
- **Workflow callbacks**: Monitor and react to workflow events
- **Custom workflows**: Full control over orchestration logic

Each extension point is designed to work with the library's existing components, so you can customize specific parts without reimplementing everything.

Next Steps
----------

- See :doc:`backtesting` for evaluating custom models
- Explore the API documentation for available transforms and models
- Check the examples directory for more customization patterns