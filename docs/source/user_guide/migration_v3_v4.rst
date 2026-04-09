Migrating from V3 to V4
=======================

OpenSTEF V4 represents a major architectural evolution of the library, introducing a modular package structure, improved APIs, and enhanced flexibility. This guide walks you through the breaking changes and provides practical migration steps with before/after code examples.

Overview of Changes
-------------------

V4 introduces several fundamental changes:

- **Modular package structure**: The monolithic ``openstef`` package is now split into ``openstef-core``, ``openstef-models``, and ``openstef-beam``
- **New prediction API**: The pipeline-based approach is replaced with a workflow-based system
- **Updated data classes**: ``PredictionJobDataClass`` evolves with new configuration options
- **Improved extensibility**: Callback hooks and versioned state management for custom workflows

Most V3 code will require updates to work with V4, but the core concepts remain similar. The migration typically involves updating imports, adapting to new APIs, and optionally leveraging new features.

Package Structure Changes
-------------------------

V3 used a single ``openstef`` package containing all functionality. V4 splits this into specialized packages:

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core

**After (V4):**

.. code-block:: python

   # Core data structures and utilities
   from openstef_core.data_classes.prediction_job import PredictionJobDataClass
   
   # Model training and prediction workflows
   from openstef_models.workflows.train import TrainWorkflow
   from openstef_models.workflows.predict import PredictWorkflow
   
   # Evaluation and metrics (optional)
   from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline

For convenience, you can install the ``openstef`` meta-package which includes ``openstef-core`` and ``openstef-models``:

.. code-block:: bash

   pip install openstef

This provides the essential components for most use cases. Install ``openstef-beam`` separately if you need backtesting, evaluation, or analysis features:

.. code-block:: bash

   pip install openstef-beam

Training Models
---------------

The training API shifts from pipeline functions to workflow classes with explicit configuration.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   import pandas as pd

   # Define prediction job
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       name="Example"
   )

   # Load training data
   train_data = pd.read_csv('training_data.csv', index_col=0, parse_dates=True)

   # Train model using pipeline
   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts"
   )

**After (V4):**

.. code-block:: python

   from openstef_core.data_classes.prediction_job import PredictionJobDataClass
   from openstef_models.workflows.train import TrainWorkflow
   from openstef_models.workflows.context import WorkflowContext
   import pandas as pd

   # Define prediction job (similar structure)
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       name="Example"
   )

   # Create workflow context
   context = WorkflowContext(prediction_job=pj)

   # Initialize and run training workflow
   workflow = TrainWorkflow()
   result = workflow.run(context, train_data)

   # Access trained model
   trained_model = result.model

The V4 approach provides better separation of concerns and makes it easier to customize training behavior through callbacks or workflow subclassing.

Making Predictions
------------------

Prediction workflows follow a similar pattern to training, replacing pipeline functions with workflow classes.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline_core
   from openstef.model.serializer import MLflowSerializer

   # Load trained model
   serializer = MLflowSerializer(mlflow_tracking_uri="./mlflow_trained_models")
   model = serializer.load_model(pj.id)

   # Create forecast
   forecast = create_forecast_pipeline_core(
       pj,
       input_data,
       model,
       modelspecs
   )

**After (V4):**

.. code-block:: python

   from openstef_models.workflows.predict import PredictWorkflow
   from openstef_models.workflows.context import WorkflowContext

   # Create context with trained model
   context = WorkflowContext(
       prediction_job=pj,
       model=trained_model  # From training workflow or loaded separately
   )

   # Initialize and run prediction workflow
   workflow = PredictWorkflow()
   result = workflow.run(context, input_data)

   # Access predictions
   forecast = result.forecast

State Management and Model Persistence
---------------------------------------

V4 introduces versioned state management for better backward compatibility when loading models trained with older versions.

Models now include version metadata and automatic migration logic. When you save a model in V4, it stores version information:

.. code-block:: python

   # Saving models (handled automatically by workflows)
   # Models now include __version__ metadata
   
   # Loading models with automatic migration
   # V4 automatically detects and migrates V3 models
   loaded_model = workflow.load_model(model_path)
   # Warning issued if loading legacy format without version metadata

This versioning system ensures that models trained with V3 can still be loaded in V4, with appropriate warnings about compatibility.

Evaluation and Metrics
----------------------

Evaluation capabilities are now in the separate ``openstef-beam`` package with enhanced functionality.

**Before (V3):**

.. code-block:: python

   from openstef.metrics.reporter import Report
   
   # Basic evaluation
   report = Report(forecast, actual_data)
   metrics = report.get_metrics()

**After (V4):**

.. code-block:: python

   from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline
   from openstef_beam.evaluation.config import EvaluationConfig
   from openstef_beam.metrics.providers import MetricProvider

   # Configure comprehensive evaluation
   config = EvaluationConfig(
       available_ats=["D-1T06:00"],
       lead_times=["PT36H"],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))]
   )

   # Run evaluation across multiple dimensions
   pipeline = EvaluationPipeline(
       config=config,
       quantiles=pj.quantiles,
       window_metric_providers=[...],
       global_metric_providers=[...]
   )
   
   evaluation_results = pipeline.evaluate(predictions, actuals)

The V4 evaluation framework provides more granular control over metrics, time windows, and lead time analysis.

Extending Workflows with Callbacks
-----------------------------------

V4 introduces a callback system for customizing workflow behavior without subclassing.

.. code-block:: python

   from openstef_models.workflows.callbacks import PredictorCallback
   from openstef_models.workflows.context import WorkflowContext

   class CustomCallback(PredictorCallback):
       """Custom callback for logging and validation."""
       
       def on_predict_complete(
           self,
           context: WorkflowContext,
           data: pd.DataFrame,
           result: PredictionResult
       ) -> None:
           """Called after prediction completes."""
           # Log predictions to database
           self.save_to_database(result.forecast)
           
           # Validate forecast quality
           if result.forecast.isna().any():
               logger.warning("Forecast contains NaN values")

   # Use callback in workflow
   workflow = PredictWorkflow(callbacks=[CustomCallback()])
   result = workflow.run(context, input_data)

This pattern enables clean separation of core prediction logic from auxiliary tasks like logging, validation, or downstream integrations.

Migration Workflow
------------------

Follow these steps to migrate your V3 codebase:

1. **Update dependencies**: Replace ``openstef`` with the V4 packages in your ``requirements.txt`` or ``pyproject.toml``:

   .. code-block:: text

      # Remove
      openstef==3.x.x
      
      # Add
      openstef>=4.0.0
      openstef-beam>=4.0.0  # If using evaluation features

2. **Update imports**: Search and replace import statements following the package structure changes shown above. Focus on:

   - ``openstef.pipeline.*`` → ``openstef_models.workflows.*``
   - ``openstef.data_classes.*`` → ``openstef_core.data_classes.*``
   - ``openstef.metrics.*`` → ``openstef_beam.metrics.*``

3. **Refactor pipeline calls**: Replace pipeline function calls with workflow instantiation and execution:

   - Identify all calls to ``train_model_pipeline``, ``create_forecast_pipeline_core``, etc.
   - Create ``WorkflowContext`` objects with appropriate configuration
   - Instantiate and run corresponding workflow classes

4. **Test incrementally**: Migrate and test one component at a time (training, then prediction, then evaluation) rather than attempting a full migration at once.

5. **Leverage compatibility warnings**: Run your migrated code and address any deprecation warnings or compatibility notices that V4 emits.

Common Pitfalls
---------------

**Return value changes**: V3 pipelines often returned tuples of DataFrames. V4 workflows return structured result objects. Update code that unpacks return values:

.. code-block:: python

   # V3
   train, val, test = train_model_pipeline(...)
   
   # V4
   result = workflow.run(...)
   train = result.train_data
   val = result.validation_data

**Configuration location**: Some configuration that was passed as function arguments in V3 is now part of ``WorkflowContext`` or workflow initialization in V4.

**Model serialization**: If you have custom model serialization code, review the new versioned state management system to ensure compatibility.

Next Steps
----------

- See :doc:`use_cases` for practical examples using V4 APIs
- Review :doc:`data_integration` for updated data loading patterns
- Consult :doc:`deployment` for production deployment strategies with V4

For questions or migration issues, consult the OpenSTEF community forums or GitHub issues.