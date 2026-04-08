Advanced Customization
======================

This guide shows how to customize OpenSTEF for advanced use cases. You'll learn how to extend the library's core components: creating custom feature transforms, building custom preprocessing pipelines, and implementing workflow callbacks for production systems.

If you're new to OpenSTEF, start with :doc:`quickstart` or :doc:`first_forecast` instead.

Custom Feature Engineering
---------------------------

OpenSTEF provides a flexible transform system based on the ``TimeSeriesTransform`` interface. You can create custom transforms to add domain-specific features or implement specialized preprocessing logic.

Creating a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All custom transforms inherit from ``TimeSeriesTransform`` and implement two key methods:

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class TemperatureDifferenceTransform(TimeSeriesTransform):
       """Adds temperature difference features for heating/cooling analysis."""
       
       def __init__(self, base_temp: float = 18.0):
           self.base_temp = base_temp
           self._fitted = False
       
       @property
       def is_fitted(self) -> bool:
           return self._fitted
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Fit is called during training to learn parameters."""
           # For stateless transforms, just mark as fitted
           self._fitted = True
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply the transformation to the dataset."""
           df = data.data.copy()
           
           # Add heating degree days (HDD) and cooling degree days (CDD)
           if 'temperature' in df.columns:
               df['hdd'] = (self.base_temp - df['temperature']).clip(lower=0)
               df['cdd'] = (df['temperature'] - self.base_temp).clip(lower=0)
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           """Return names of features added by this transform."""
           return ['hdd', 'cdd']

The ``features_added()`` method helps OpenSTEF track which features are created by each transform, useful for debugging and feature importance analysis.

Stateful Transforms
^^^^^^^^^^^^^^^^^^^

For transforms that need to learn parameters from training data (like scalers or encoders), use the ``fit()`` method:

.. code-block:: python

   class AdaptiveScalerTransform(TimeSeriesTransform):
       """Scales features based on training data statistics."""
       
       def __init__(self, columns: list[str]):
           self.columns = columns
           self.scale_factors = None
       
       @property
       def is_fitted(self) -> bool:
           return self.scale_factors is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn scaling factors from training data."""
           df = data.data
           self.scale_factors = {
               col: df[col].std() for col in self.columns if col in df.columns
           }
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply learned scaling to data."""
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           df = data.data.copy()
           for col, scale in self.scale_factors.items():
               if col in df.columns and scale > 0:
                   df[f'{col}_scaled'] = df[col] / scale
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return [f'{col}_scaled' for col in self.columns]

Custom Preprocessing Pipelines
-------------------------------

OpenSTEF uses ``TransformPipeline`` to chain multiple transforms together. You can build custom pipelines by combining built-in transforms with your custom ones.

Building a Pipeline
^^^^^^^^^^^^^^^^^^^

The ``preprocessing`` field on forecasting models accepts a ``TransformPipeline``:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.general import Clipper
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.models import XGBForecastingModel
   
   # Create a custom preprocessing pipeline
   preprocessing = TransformPipeline()
   
   # Add your custom transform
   preprocessing.add_transform(TemperatureDifferenceTransform(base_temp=18.0))
   
   # Add built-in transforms
   preprocessing.add_transform(WindPowerFeatureAdder())
   preprocessing.add_transform(Clipper())
   
   # Create model with custom pipeline
   model = XGBForecastingModel(
       target_column='load',
       preprocessing=preprocessing
   )
   
   # The pipeline is automatically fitted and applied during training
   model.fit(train_data, data_val=val_data)

The pipeline executes transforms in order. Each transform's ``fit()`` is called during model training, and ``transform()`` is applied to both training and prediction data.

Model-Specific Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^

Ensemble models support both common preprocessing (applied to all base models) and model-specific preprocessing:

.. code-block:: python

   from openstef_models.models import EnsembleForecastingModel, XGBForecastingModel, LinearForecastingModel
   from openstef_core.transforms import TransformPipeline
   
   # Common preprocessing for all models
   common_preprocessing = TransformPipeline()
   common_preprocessing.add_transform(TemperatureDifferenceTransform())
   
   # Model-specific preprocessing
   xgb_preprocessing = TransformPipeline()
   xgb_preprocessing.add_transform(Clipper())  # XGBoost benefits from clipping
   
   linear_preprocessing = TransformPipeline()
   linear_preprocessing.add_transform(AdaptiveScalerTransform(['temperature', 'windspeed']))
   
   # Create ensemble with custom pipelines
   ensemble = EnsembleForecastingModel(
       forecasters={
           'xgb': XGBForecastingModel(target_column='load'),
           'linear': LinearForecastingModel(target_column='load')
       },
       preprocessing=common_preprocessing,
       model_specific_preprocessing={
           'xgb': xgb_preprocessing,
           'linear': linear_preprocessing
       }
   )

The common preprocessing runs first, then each model's specific preprocessing is applied to its input.

Custom Workflow Callbacks
--------------------------

For production systems, OpenSTEF provides workflow callbacks that hook into key lifecycle events. Use callbacks for logging, monitoring, data persistence, or validation.

Creating a Callback
^^^^^^^^^^^^^^^^^^^

Callbacks inherit from ``ForecastingCallback`` and override specific event methods:

.. code-block:: python

   from openstef_models.mixins.callbacks import ForecastingCallback, WorkflowContext
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   from openstef_models.models.forecasting_model import ModelFitResult
   import logging
   
   logger = logging.getLogger(__name__)
   
   class MetricsCallback(ForecastingCallback):
       """Collects and logs metrics during training and prediction."""
       
       def on_fit_start(
           self, 
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset
       ) -> None:
           """Called before model training begins."""
           logger.info(
               f"Starting training for {context.workflow.model.model_id}",
               extra={
                   "n_samples": len(data.data),
                   "date_range": f"{data.data.index.min()} to {data.data.index.max()}"
               }
           )
       
       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult
       ) -> None:
           """Called after model training completes."""
           logger.info(
               f"Training completed for {context.workflow.model.model_id}",
               extra={
                   "train_score": result.train_score,
                   "val_score": result.val_score,
                   "feature_importance": result.feature_importance
               }
           )
       
       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
           result: ForecastDataset
       ) -> None:
           """Called after predictions are generated."""
           logger.info(
               f"Generated {len(result.data)} predictions",
               extra={
                   "forecast_range": f"{result.data.index.min()} to {result.data.index.max()}",
                   "mean_forecast": result.data['forecast'].mean()
               }
           )

Using Callbacks in Workflows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attach callbacks to workflows to enable monitoring and debugging:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.workflows.callbacks import DataSaveCallback
   
   # Create multiple callbacks
   metrics_callback = MetricsCallback()
   data_save_callback = DataSaveCallback(output_dir="./workflow_data")
   
   # Create workflow with callbacks
   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[metrics_callback, data_save_callback]
   )
   
   # Callbacks are automatically invoked during workflow execution
   workflow.fit(train_data, data_val=val_data)
   forecasts = workflow.predict(test_data)

The ``DataSaveCallback`` is a built-in callback that saves intermediate datasets to parquet files, useful for debugging and auditing.

Component Splitting Workflows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Component splitting models have their own callback interface:

.. code-block:: python

   from openstef_models.workflows import CustomComponentSplitWorkflow, ComponentSplitCallback
   from openstef_core.datasets import EnergyComponentDataset
   
   class ComponentValidationCallback(ComponentSplitCallback):
       """Validates component splits sum to total load."""
       
       def on_predict_end(
           self,
           context: WorkflowContext[CustomComponentSplitWorkflow],
           data: TimeSeriesDataset,
           result: EnergyComponentDataset
       ) -> None:
           """Validate component predictions."""
           components_sum = result.data[result.components].sum(axis=1)
           original_load = data.data[context.workflow.model.source_column]
           
           max_error = (components_sum - original_load).abs().max()
           if max_error > 0.01:
               logger.warning(
                   f"Component split validation failed: max error {max_error}",
                   extra={"max_error": max_error}
               )

Extension Points Summary
------------------------

OpenSTEF provides three main extension points for customization:

- **Custom Transforms**: Implement ``TimeSeriesTransform`` to add domain-specific features or preprocessing logic. Use ``fit()`` for stateful transforms that learn from training data.

- **Custom Pipelines**: Chain transforms using ``TransformPipeline``. Assign pipelines to model ``preprocessing`` fields. Ensemble models support both common and model-specific pipelines.

- **Workflow Callbacks**: Implement ``ForecastingCallback`` or ``ComponentSplitCallback`` to hook into training and prediction lifecycle events. Use for logging, monitoring, validation, or data persistence.

These patterns enable you to adapt OpenSTEF to your specific forecasting requirements while maintaining compatibility with the library's core architecture.

Next Steps
----------

- See :doc:`backtesting` for evaluating custom models and pipelines
- Explore the API reference for complete details on transform interfaces
- Review built-in transforms in ``openstef_models.transforms`` for implementation examples