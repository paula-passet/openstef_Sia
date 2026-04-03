Migration Guide: V3 to V4
==========================

OpenSTEF V4 introduces significant architectural changes that improve the library's flexibility and modularity. This guide walks you through the breaking changes and provides step-by-step migration instructions with before/after code examples.

Overview of Changes
-------------------

V4 represents a major refactoring of OpenSTEF's core architecture. The key changes include:

- **Data handling**: Pandas DataFrames replaced with ``TimeSeriesDataset`` objects
- **Configuration**: ``PredictionJobDataClass`` removed in favor of direct function parameters
- **Database integration**: Standalone library with no built-in database coupling (openstef-dbc removed)
- **Pipeline API**: Simplified function signatures with explicit parameters
- **Feature engineering**: More modular and composable feature applicators

These changes make OpenSTEF more flexible as a library, allowing you to integrate it into your own systems without being tied to specific data structures or database schemas.

Breaking Changes
----------------

TimeSeriesDataset replaces DataFrames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most significant change is the introduction of ``TimeSeriesDataset`` as the primary data container. This object provides better structure and validation for time series data.

**V3 code:**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Load data as DataFrame
   input_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_data = input_data.iloc[:-200, :]
   
   # Pass DataFrame directly to pipeline
   models = train_model_pipeline(pj, train_data, ...)

**V4 code:**

.. code-block:: python

   import pandas as pd
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.pipeline.train import train_pipeline
   
   # Load data as DataFrame, then convert
   df = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_data = df.iloc[:-200, :]
   
   # Create TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=train_data,
       target_column='load',
       datetime_column=train_data.index
   )
   
   # Pass TimeSeriesDataset to pipeline
   model = train_pipeline(dataset, model_type='xgb', horizons=[0.25, 47.0], ...)

PredictionJobDataClass removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 used a ``PredictionJobDataClass`` to bundle all configuration parameters. V4 removes this in favor of explicit function parameters, giving you more control over each pipeline step.

**V3 code:**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Define prediction job with all parameters
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       name="backtest",
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       hyper_params={},
       feature_names=None
   )
   
   # Pass prediction job to pipeline
   models = train_model_pipeline(pj, train_data, ...)

**V4 code:**

.. code-block:: python

   # Pass parameters directly to pipeline functions
   model = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       horizons=[0.25, 47.0],  # in hours
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       lat=52.0,
       lon=5.0,
       hyperparameters={},
       feature_names=None
   )

Pipeline function signatures changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pipeline functions have been renamed and simplified. The core functionality remains the same, but the API is more explicit.

**V3 training pipeline:**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   
   train_data, validation_data, test_data = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts"
   )

**V4 training pipeline:**

.. code-block:: python

   from openstef.pipeline.train import train_pipeline
   from openstef.model.serializer import MLflowSerializer
   
   # Train model
   model, metrics = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       horizons=[0.25, 47.0]
   )
   
   # Serialize separately if needed
   serializer = MLflowSerializer(tracking_uri="./mlflow_trained_models")
   serializer.save_model(model, artifact_path="./mlflow_artifacts")

**V3 forecast pipeline:**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   forecast = create_forecast_pipeline(
       pj,
       input_data,
       mlflow_tracking_uri="./mlflow_trained_models"
   )

**V4 forecast pipeline:**

.. code-block:: python

   from openstef.pipeline.predict import predict_pipeline
   from openstef.model.serializer import MLflowSerializer
   
   # Load model
   serializer = MLflowSerializer(tracking_uri="./mlflow_trained_models")
   model = serializer.load_model(model_id="287")
   
   # Create forecast
   forecast = predict_pipeline(
       model=model,
       dataset=input_dataset,
       horizons=[0.25, 47.0]
   )

Database integration removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 included ``openstef-dbc`` for database connectivity. V4 is a standalone library—you handle data loading and storage in your own application.

**V3 approach:**

.. code-block:: python

   # V3 had built-in database queries
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   # Database connection was implicit through prediction job

**V4 approach:**

.. code-block:: python

   # You load data from your own sources
   import pandas as pd
   from openstef.data.dataset import TimeSeriesDataset
   
   # Load from your database, S3, Databricks, etc.
   df = load_from_your_database(query="SELECT * FROM timeseries WHERE id=287")
   
   # Convert to TimeSeriesDataset
   dataset = TimeSeriesDataset(data=df, target_column='load')

See the :doc:`data_integration` page for patterns on loading data from various sources.

Step-by-Step Migration Workflow
--------------------------------

Follow these steps to migrate your V3 code to V4:

1. Update imports
^^^^^^^^^^^^^^^^^

Replace V3 imports with their V4 equivalents:

.. code-block:: python

   # V3 imports
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # V4 imports
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.pipeline.train import train_pipeline
   from openstef.pipeline.predict import predict_pipeline
   from openstef.model.serializer import MLflowSerializer

2. Convert data to TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Wrap your pandas DataFrames in ``TimeSeriesDataset`` objects:

.. code-block:: python

   # Your existing DataFrame
   df = pd.read_csv('data.csv', index_col='datetime', parse_dates=True)
   
   # Create TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',  # or 'demand', 'generation', etc.
       datetime_column=df.index
   )

3. Replace PredictionJobDataClass with parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract parameters from your prediction job and pass them directly:

.. code-block:: python

   # V3: bundled in prediction job
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       horizon_minutes=47*60,
       quantiles=[0.05, 0.5, 0.95],
       lat=52.0,
       lon=5.0
   )
   
   # V4: explicit parameters
   model_type = 'xgb'
   horizons = [0.25, 47.0]  # converted from minutes to hours
   quantiles = [0.05, 0.5, 0.95]
   location = {'lat': 52.0, 'lon': 5.0}

4. Update pipeline calls
^^^^^^^^^^^^^^^^^^^^^^^^

Replace V3 pipeline calls with V4 equivalents:

.. code-block:: python

   # V3 training
   train_data, val_data, test_data = train_model_pipeline(
       pj, train_data, mlflow_tracking_uri="./mlflow"
   )
   
   # V4 training
   model, metrics = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       horizons=[0.25, 47.0],
       quantiles=[0.05, 0.5, 0.95]
   )
   
   # Save model separately
   serializer = MLflowSerializer(tracking_uri="./mlflow")
   serializer.save_model(model, artifact_path="./artifacts")

5. Handle model serialization explicitly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 separates training from serialization:

.. code-block:: python

   # Training
   model, metrics = train_pipeline(dataset, model_type='xgb', horizons=[0.25, 47.0])
   
   # Saving
   serializer = MLflowSerializer(tracking_uri="./mlflow")
   serializer.save_model(
       model,
       artifact_path="./artifacts",
       metadata={'model_id': '287', 'version': '1.0'}
   )
   
   # Loading
   loaded_model = serializer.load_model(model_id="287")

6. Implement your own data integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace database dependencies with your own data loading logic. See :doc:`data_integration` for detailed patterns.

Common Migration Patterns
--------------------------

Converting time horizons
^^^^^^^^^^^^^^^^^^^^^^^^

V3 used minutes, V4 uses hours:

.. code-block:: python

   # V3
   horizon_minutes = 47 * 60  # 47 hours in minutes
   
   # V4
   horizons = [0.25, 47.0]  # 15 minutes and 47 hours

Handling quantile forecasts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The quantile parameter works the same way, but is now passed directly:

.. code-block:: python

   # Both V3 and V4
   quantiles = [0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95]
   
   # V3: in prediction job
   pj = PredictionJobDataClass(quantiles=quantiles, ...)
   
   # V4: direct parameter
   model, metrics = train_pipeline(dataset, quantiles=quantiles, ...)

Feature engineering
^^^^^^^^^^^^^^^^^^^

Feature applicators are now more modular:

.. code-block:: python

   # V3: features applied implicitly in pipeline
   models = train_model_pipeline(pj, train_data, ...)
   
   # V4: explicit feature application
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   
   applicator = TrainFeatureApplicator(
       horizons=[0.25, 47.0],
       feature_names=['hour', 'dayofweek', 'month']
   )
   dataset_with_features = applicator.add_features(dataset)
   model, metrics = train_pipeline(dataset_with_features, ...)

Next Steps
----------

After migrating your code:

- Review the :doc:`use_cases` page for practical examples of common workflows
- Check :doc:`deployment` for production deployment patterns
- Consult :doc:`logging` for configuring logging in your application

If you encounter issues during migration, check the API reference documentation or open an issue on the OpenSTEF GitHub repository.