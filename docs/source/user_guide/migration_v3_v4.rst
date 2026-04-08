Migrating from V3 to V4
=======================

OpenSTEF V4 introduces a major architectural redesign focused on modularity, composability, and type safety. This guide helps you migrate existing V3 code to the new V4 API.

Overview of Changes
-------------------

V4 represents a fundamental shift in how OpenSTEF is structured:

**Architecture**: V3's monolithic pipeline functions have been replaced with composable workflow objects. Instead of calling ``train_model_pipeline()`` with many parameters, you now create predictor instances that encapsulate configuration and behavior.

**Package structure**: V3 had a single ``openstef`` package. V4 splits functionality across three packages:

- ``openstef-models``: Core forecasting workflows and predictors
- ``openstef-meta``: Meta-learning and ensemble methods
- ``openstef-core``: Shared utilities and base classes

**Type safety**: V4 uses modern Python type hints throughout, enabling better IDE support and catching errors at development time rather than runtime.

**Configuration**: V3 used dictionary-based ``PredictionJobDataClass`` objects. V4 uses strongly-typed configuration classes with validation.

Step-by-Step Migration Workflow
--------------------------------

Follow these steps to migrate your V3 code:

1. **Update dependencies**: Replace ``openstef`` with the appropriate V4 packages in your requirements:

   .. code-block:: text

      # V3
      openstef>=3.0.0

      # V4
      openstef-models>=4.0.0
      openstef-meta>=4.0.0  # If using ensemble methods

2. **Update imports**: Change import statements to reflect the new package structure.

3. **Replace pipeline functions with workflow objects**: Convert functional pipeline calls to object-oriented workflow instances.

4. **Update configuration**: Migrate from ``PredictionJobDataClass`` dictionaries to typed configuration classes.

5. **Adapt callbacks and hooks**: Replace custom logging/monitoring with V4's ``PredictorCallback`` system.

Training Models
---------------

The training workflow has changed from a pipeline function to a workflow object pattern.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   import pandas as pd

   # Define prediction job as dictionary
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
       save_train_forecasts=True,
   )

   # Load and prepare data
   input_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_data = input_data.iloc[:-200, :]

   # Train using pipeline function
   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.presets import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow
   )
   import pandas as pd

   # Define configuration with typed config class
   config = ForecastingWorkflowConfig(
       location=LocationConfig(
           id=287,
           name="Example",
           lat=52.0,
           lon=5.0,
       ),
       quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],
       horizon=timedelta(hours=47),
       resolution=timedelta(minutes=15),
       model_type="xgboost",
   )

   # Create workflow instance
   workflow = create_forecasting_workflow(config)

   # Load and prepare data
   input_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)

   # Train using workflow object
   fit_result = workflow.fit(input_data)

Key differences:

- Configuration is now strongly typed with validation
- No separate pipeline function - the workflow object encapsulates behavior
- Return values are structured result objects rather than tuples
- MLflow integration is handled through callbacks rather than function parameters

Making Predictions
------------------

Prediction generation follows the same pattern shift from functions to objects.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline_core

   # Assumes model was trained and saved earlier
   forecast = create_forecast_pipeline_core(
       pj,
       input_data,
       model,
       modelspecs,
   )

**After (V4):**

.. code-block:: python

   # Using the same workflow instance from training
   prediction = workflow.predict(input_data)

   # Or load a saved workflow
   from openstef_models.workflows import CustomForecastingWorkflow
   
   loaded_workflow = CustomForecastingWorkflow.load("path/to/saved/workflow")
   prediction = loaded_workflow.predict(input_data)

The workflow object maintains state between training and prediction, eliminating the need to pass models and specifications separately.

Package Structure Changes
-------------------------

V3's single-package structure has been split for better modularity:

**V3 structure:**

.. code-block:: text

   openstef/
   ├── pipeline/
   │   ├── train_model.py
   │   ├── create_forecast.py
   │   └── optimize_hyperparameters.py
   ├── data_classes/
   │   └── prediction_job.py
   ├── model/
   │   └── regressors/
   └── metrics/

**V4 structure:**

.. code-block:: text

   openstef-models/
   ├── workflows/
   │   └── forecasting_workflow.py
   ├── presets/
   │   └── forecasting_workflow.py
   └── transforms/

   openstef-meta/
   ├── workflows/
   │   └── ensemble_workflow.py
   └── presets/

   openstef-core/
   ├── base/
   └── utils/

Update your imports accordingly:

.. code-block:: python

   # V3
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # V4
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.presets import ForecastingWorkflowConfig

Callbacks and Monitoring
-------------------------

V3 had limited extension points. V4 introduces a comprehensive callback system.

**Before (V3):**

.. code-block:: python

   # Limited customization - mostly through function parameters
   train, val, test = train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./mlflow",
       # Custom behavior required modifying pipeline code
   )

**After (V4):**

.. code-block:: python

   from openstef_models.base import PredictorCallback, WorkflowContext

   class CustomMonitoring(PredictorCallback):
       def on_fit_start(self, context: WorkflowContext, data):
           print(f"Starting training with {len(data)} samples")
           
       def on_fit_end(self, context: WorkflowContext, result):
           print(f"Training complete: {result.metrics}")
           
       def on_predict_end(self, context: WorkflowContext, data, result):
           print(f"Generated {len(result.predictions)} predictions")

   # Attach callback to workflow
   workflow = create_forecasting_workflow(config)
   workflow.add_callback(CustomMonitoring())
   
   # Callbacks fire automatically during fit/predict
   fit_result = workflow.fit(input_data)
   predictions = workflow.predict(test_data)

This provides clean extension points for logging, metrics collection, validation, and integration with monitoring systems.

Configuration Migration
-----------------------

V3's flexible dictionary-based configuration has been replaced with typed configuration classes that provide validation and better IDE support.

**Before (V3):**

.. code-block:: python

   # Dictionary with optional validation
   pj = dict(
       id=287,
       model='xgb',
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
       default_modelspecs=None,
       save_train_forecasts=True,
   )
   pj = PredictionJobDataClass(**pj)

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets import ForecastingWorkflowConfig, LocationConfig

   # Strongly typed with automatic validation
   config = ForecastingWorkflowConfig(
       location=LocationConfig(
           id=287,
           name="Example",
           lat=52.0,
           lon=5.0,
       ),
       quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],  # Note: fractions not percentages
       horizon=timedelta(hours=47),  # timedelta instead of minutes
       resolution=timedelta(minutes=15),
       model_type="xgboost",
   )

Benefits of typed configuration:

- IDE autocomplete shows available fields
- Type checking catches errors before runtime
- Validation happens at construction time
- Better documentation through type hints

Common Migration Patterns
--------------------------

**Pattern 1: Repository pattern integration**

If you wrapped V3 pipelines in a repository class, update the wrapper methods:

.. code-block:: python

   # V3
   class OpenstefRepository:
       def forecast_pipeline(self, prediction_job, input_data, model, modelspecs):
           return create_forecast_pipeline_core(
               prediction_job, input_data, model, modelspecs
           )

   # V4
   class OpenstefRepository:
       def __init__(self):
           self.workflows = {}  # Cache workflow instances
           
       def forecast_pipeline(self, config, input_data):
           workflow_id = config.location.id
           if workflow_id not in self.workflows:
               self.workflows[workflow_id] = create_forecasting_workflow(config)
           return self.workflows[workflow_id].predict(input_data)

**Pattern 2: Batch processing**

V3 batch processing with loops:

.. code-block:: python

   # V3
   for pj in prediction_jobs:
       train_model_pipeline(pj, data[pj.id])

V4 with workflow reuse:

.. code-block:: python

   # V4
   workflows = {
       config.location.id: create_forecasting_workflow(config)
       for config in configs
   }
   
   for config_id, workflow in workflows.items():
       workflow.fit(data[config_id])

State Migration
---------------

V4 includes automatic state migration for models trained in V3. When loading a V3 model:

.. code-block:: python

   # V4 automatically detects and migrates V3 models
   workflow = CustomForecastingWorkflow.load("path/to/v3/model")
   # Warning: "Loading legacy CustomForecastingWorkflow without version metadata."

The migration is transparent, but you should retrain models in V4 format for production use to ensure full compatibility with new features.

Next Steps
----------

After migrating your code:

1. **Test thoroughly**: V4's architectural changes may expose edge cases in your data or configuration
2. **Update deployment**: See :doc:`deployment` for V4-specific deployment patterns
3. **Leverage new features**: Explore V4's callback system and typed configurations for better maintainability
4. **Retrain models**: While V3 models load in V4, retraining ensures optimal performance

For data integration patterns with V4, see :doc:`data_integration`. For logging configuration, see :doc:`logging`.