Migrating from V3 to V4
=======================

OpenSTEF V4 represents a major architectural redesign that splits the monolithic V3 package into three focused packages. This guide walks you through the breaking changes, updated APIs, and provides a step-by-step migration workflow with before/after code examples.

Overview of Changes
-------------------

V4 introduces a complete restructuring of OpenSTEF's architecture:

**Package Structure**: The single ``openstef`` package has been split into three specialized packages:

- ``openstef-core``: Core data structures, configuration, and utilities
- ``openstef-models``: Forecasting models, preprocessing transforms, and training pipelines
- ``openstef-beam``: Evaluation, backtesting, and benchmarking tools

**API Design**: V4 replaces procedural pipelines with object-oriented workflows centered around ``WorkflowContext`` and callback-based extensibility.

**Model Management**: The new ``ForecastingModel`` class provides a unified interface for preprocessing, training, and prediction, replacing the separate pipeline functions.

Breaking Changes
----------------

Import Paths
^^^^^^^^^^^^

All import paths have changed due to the package split. You must update imports throughout your codebase.

Before (V3)::

    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.pipeline.create_forecast import create_forecast_pipeline

After (V4)::

    from openstef_core.data_classes.prediction_job import PredictionJobDataClass
    from openstef_models.pipelines.workflows import WorkflowContext
    from openstef_models.models.forecasting import ForecastingModel

Pipeline Architecture
^^^^^^^^^^^^^^^^^^^^^

V3's functional pipelines (``train_model_pipeline``, ``create_forecast_pipeline``) have been replaced with the ``WorkflowContext`` pattern.

Before (V3)::

    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.data_classes.prediction_job import PredictionJobDataClass
    import pandas as pd

    # Define prediction job
    pj = PredictionJobDataClass(
        id=287,
        model='xgb',
        quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],
        forecast_type="demand",
        lat=52.0,
        lon=5.0,
        horizon_minutes=47*60,
        resolution_minutes=15,
        name="Example"
    )

    # Load data
    train_data = pd.read_csv('data/train.csv', index_col='index', parse_dates=True)

    # Train model
    model = train_model_pipeline(
        pj,
        train_data,
        check_old_model_age=False,
        mlflow_tracking_uri="./mlflow_trained_models",
        artifact_folder="./mlflow_artifacts"
    )

After (V4)::

    from openstef_core.data_classes.prediction_job import PredictionJobDataClass
    from openstef_models.pipelines.workflows import WorkflowContext
    from openstef_models.models.forecasting import ForecastingModel
    from openstef_models.transforms import StandardScaler
    import pandas as pd

    # Define prediction job (same structure)
    pj = PredictionJobDataClass(
        id=287,
        model='xgb',
        quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],
        forecast_type="demand",
        lat=52.0,
        lon=5.0,
        horizon_minutes=47*60,
        resolution_minutes=15,
        name="Example"
    )

    # Load data
    train_data = pd.read_csv('data/train.csv', index_col='index', parse_dates=True)

    # Create forecasting model
    model = ForecastingModel.from_config(
        forecaster_type="xgb",
        preprocessing=[StandardScaler()]
    )

    # Create workflow context
    context = WorkflowContext(model=model, prediction_job=pj)

    # Train model
    fit_result = context.fit(train_data)

The key differences:

- ``ForecastingModel`` encapsulates preprocessing, model, and postprocessing
- ``WorkflowContext`` manages the workflow state and callbacks
- Training is now ``context.fit()`` instead of calling a pipeline function
- Model storage is handled through context methods, not pipeline parameters

Prediction and Forecasting
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forecast generation follows a similar pattern change.

Before (V3)::

    from openstef.pipeline.create_forecast import create_forecast_pipeline

    # Generate forecast
    forecast = create_forecast_pipeline(
        pj,
        input_data=forecast_data,
        model=model
    )

After (V4)::

    # Using the same context from training
    forecast = context.predict(forecast_data)

    # Or create a new context with a loaded model
    loaded_context = WorkflowContext.load(model_path, prediction_job=pj)
    forecast = loaded_context.predict(forecast_data)

Callback System
^^^^^^^^^^^^^^^

V4 introduces a callback system for extensibility. Instead of modifying pipeline code, you implement callbacks.

Example - Custom Logging Callback::

    from openstef_models.pipelines.callbacks import PredictorCallback

    class LoggingCallback(PredictorCallback):
        def on_fit_start(self, context, data):
            print(f"Starting training with {len(data)} samples")

        def on_fit_end(self, context, result):
            print(f"Training completed. Model: {context.model}")

        def on_predict_end(self, context, data, result):
            print(f"Generated {len(result)} predictions")

    # Use callback in workflow
    context = WorkflowContext(
        model=model,
        prediction_job=pj,
        callbacks=[LoggingCallback()]
    )
    context.fit(train_data)

This replaces V3's approach of modifying pipeline functions or using hooks scattered throughout the codebase.

Step-by-Step Migration Workflow
--------------------------------

1. **Update Dependencies**

   Update your ``requirements.txt`` or ``pyproject.toml``::

       # Remove
       openstef==3.x.x

       # Add
       openstef-core==4.x.x
       openstef-models==4.x.x
       openstef-beam==4.x.x  # Only if using evaluation/backtesting

2. **Fix Import Statements**

   Use your IDE's find-and-replace to update imports:

   - ``from openstef.data_classes`` → ``from openstef_core.data_classes``
   - ``from openstef.pipeline`` → ``from openstef_models.pipelines``
   - ``from openstef.model`` → ``from openstef_models.models``

3. **Refactor Training Code**

   Replace pipeline function calls with ``WorkflowContext``:

   - Create ``ForecastingModel`` instance
   - Wrap in ``WorkflowContext`` with prediction job
   - Call ``context.fit()`` instead of ``train_model_pipeline()``

4. **Refactor Prediction Code**

   - Use ``context.predict()`` instead of ``create_forecast_pipeline()``
   - Load models using ``WorkflowContext.load()`` if needed

5. **Migrate Custom Extensions**

   If you modified pipeline behavior in V3:

   - Identify customization points
   - Implement ``PredictorCallback`` subclass
   - Register callbacks with ``WorkflowContext``

6. **Update Model Storage**

   V4 uses versioned state serialization:

   - Old V3 models can be loaded with automatic migration warnings
   - Save new models using ``context.save()``
   - Update any model loading code to use ``WorkflowContext.load()``

7. **Test Thoroughly**

   V4 includes automatic state migration, but verify:

   - Models train successfully
   - Predictions match expected format
   - Custom callbacks execute at correct lifecycle points

Common Migration Patterns
--------------------------

Hyperparameter Optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 provided ``optimize_hyperparameters_pipeline()``. In V4, you implement this using the workflow context and your preferred optimization library.

Before (V3)::

    from openstef.pipeline.optimize_hyperparameters import optimize_hyperparameters_pipeline

    model, modelspecs, report, params, trial_id, study = optimize_hyperparameters_pipeline(
        pj,
        input_data,
        n_trials=50
    )

After (V4)::

    import optuna
    from openstef_models.pipelines.workflows import WorkflowContext

    def objective(trial):
        # Define hyperparameters to optimize
        params = {
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3)
        }

        # Create model with trial parameters
        model = ForecastingModel.from_config(
            forecaster_type="xgb",
            forecaster_params=params
        )

        context = WorkflowContext(model=model, prediction_job=pj)
        result = context.fit(train_data)

        # Return metric to optimize
        return result.validation_score

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=50)

    # Train final model with best parameters
    best_model = ForecastingModel.from_config(
        forecaster_type="xgb",
        forecaster_params=study.best_params
    )
    context = WorkflowContext(model=best_model, prediction_job=pj)
    context.fit(train_data)

This approach gives you more control and flexibility over the optimization process.

Model Persistence
^^^^^^^^^^^^^^^^^

Model saving and loading use the new versioned state system.

Before (V3)::

    # Models saved automatically to mlflow_tracking_uri
    model = train_model_pipeline(
        pj,
        train_data,
        mlflow_tracking_uri="./models"
    )

    # Loading was implicit through MLflow

After (V4)::

    # Explicit save/load
    context = WorkflowContext(model=model, prediction_job=pj)
    context.fit(train_data)

    # Save model
    context.save("./models/my_model.pkl")

    # Load model
    loaded_context = WorkflowContext.load("./models/my_model.pkl", prediction_job=pj)

V4 automatically handles version migration when loading older models, issuing warnings if the saved version differs from the current version.

Backward Compatibility
----------------------

V4 includes automatic state migration for models trained in earlier versions. When loading a V3 model:

- A warning is issued indicating legacy format
- The model state is automatically migrated to V4 format
- Predictions should work identically

However, **we strongly recommend retraining models in V4** to take advantage of:

- Improved preprocessing pipeline
- Better feature engineering
- Enhanced model validation
- Versioned state tracking

Next Steps
----------

After completing your migration:

- Review the :doc:`deployment` guide for production patterns
- Explore :doc:`data_integration` for connecting to data sources
- Configure :doc:`logging` for production monitoring
- Check :doc:`use_cases` for advanced usage patterns

For detailed API documentation, see the :doc:`../api_reference/index` section.