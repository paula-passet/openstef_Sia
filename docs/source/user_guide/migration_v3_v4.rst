Migration from V3 to V4
=======================

OpenSTEF V4 represents a major architectural shift from V3, introducing breaking changes that require code updates. This guide walks through the key changes and provides step-by-step migration instructions with before/after examples.

.. warning::
   V3 and V4 are not compatible. You cannot mix V3 and V4 APIs in the same codebase.

Overview of breaking changes
-----------------------------

V4 introduces three fundamental changes:

**Data handling**: V3 used pandas DataFrames directly. V4 introduces ``TimeSeriesDataset``, a structured container that wraps DataFrames with metadata and validation.

**Configuration**: V3 used ``PredictionJobDataClass`` to configure models and pipelines. V4 removes this concept entirely, replacing it with simpler ``ModelConfiguration`` objects and direct function parameters.

**Package structure**: V3 integrated with ``openstef-dbc`` for database operations. V4 is a standalone library focused purely on forecasting logic. Database integration is now your responsibility.

Key API changes
---------------

DataFrame to TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most pervasive change is the introduction of ``TimeSeriesDataset``. All pipeline functions now expect this type instead of raw DataFrames.

**V3 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Load data as DataFrame
   data = pd.read_csv('data.csv', index_col='datetime', parse_dates=True)
   
   # Configure via PredictionJobDataClass
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=47*60,
       resolution_minutes=15,
   )
   
   # Train with DataFrame
   model = train_model_pipeline(pj, data)

**V4 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.pipeline.train import train_pipeline
   from openstef.model.model_configuration import ModelConfiguration
   
   # Load data as DataFrame
   df = pd.read_csv('data.csv', index_col='datetime', parse_dates=True)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset.from_dataframe(
       df,
       target_column='load',
       feature_columns=['temp', 'humidity', 'wind_speed']
   )
   
   # Configure via ModelConfiguration
   config = ModelConfiguration(
       model_type='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=47*60,
   )
   
   # Train with TimeSeriesDataset
   model = train_pipeline(dataset, config)

The ``TimeSeriesDataset`` enforces structure: it requires explicit target and feature columns, validates datetime indices, and provides metadata about your data.

Removal of PredictionJobDataClass
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3's ``PredictionJobDataClass`` mixed concerns: model configuration, job metadata, database IDs, and pipeline settings. V4 separates these:

- **Model settings**: Use ``ModelConfiguration``
- **Pipeline behavior**: Pass as function arguments
- **Job metadata**: Manage in your own application layer

**V3 configuration:**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   pj = PredictionJobDataClass(
       id=287,
       name="transformer_287",
       model='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=2820,
       resolution_minutes=15,
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       hyper_params={'max_depth': 5},
       feature_names=['temp', 'humidity'],
   )

**V4 configuration:**

.. code-block:: python

   from openstef.model.model_configuration import ModelConfiguration
   
   # Model configuration only
   config = ModelConfiguration(
       model_type='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=2820,
       hyperparameters={'max_depth': 5},
   )
   
   # Job metadata managed separately (in your app)
   job_metadata = {
       'id': 287,
       'name': 'transformer_287',
       'location': {'lat': 52.0, 'lon': 5.0},
       'forecast_type': 'demand',
   }

This separation makes OpenSTEF more flexible as a library—you control job management and persistence.

Pipeline function changes
^^^^^^^^^^^^^^^^^^^^^^^^^

Pipeline function names and signatures have changed:

**Training:**

.. code-block:: python

   # V3
   from openstef.pipeline.train_model import train_model_pipeline
   model = train_model_pipeline(prediction_job, data)
   
   # V4
   from openstef.pipeline.train import train_pipeline
   model = train_pipeline(dataset, config)

**Prediction:**

.. code-block:: python

   # V3
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   forecast = create_forecast_pipeline(prediction_job, data, model)
   
   # V4
   from openstef.pipeline.predict import predict_pipeline
   forecast = predict_pipeline(model, dataset)

Notice that V4 functions are simpler: they take only the data and configuration they need, without job metadata.

Import path changes
^^^^^^^^^^^^^^^^^^^

Some modules have been reorganized:

.. code-block:: python

   # V3
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   
   # V4
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.model.model_configuration import ModelConfiguration
   from openstef.pipeline.train import train_pipeline

Step-by-step migration workflow
--------------------------------

Follow these steps to migrate a V3 codebase to V4:

1. Update dependencies
^^^^^^^^^^^^^^^^^^^^^^

Update your ``requirements.txt`` or ``pyproject.toml``:

.. code-block:: text

   # Remove
   openstef==3.x.x
   
   # Add
   openstef==4.0.0

If you used ``openstef-dbc``, remove it. V4 does not integrate with database libraries—you'll handle data loading separately.

2. Wrap DataFrames in TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Find all places where you pass DataFrames to OpenSTEF functions. Wrap them:

.. code-block:: python

   # Before
   data = load_data_from_database()  # Returns DataFrame
   model = train_model_pipeline(pj, data)
   
   # After
   df = load_data_from_database()  # Returns DataFrame
   dataset = TimeSeriesDataset.from_dataframe(
       df,
       target_column='load',
       feature_columns=['temp', 'humidity', 'wind_speed']
   )
   model = train_pipeline(dataset, config)

Specify ``target_column`` explicitly—V4 doesn't assume column names.

3. Replace PredictionJobDataClass
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract model-related fields into ``ModelConfiguration``:

.. code-block:: python

   # V3
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=2820,
       hyper_params={'max_depth': 5},
   )
   
   # V4
   config = ModelConfiguration(
       model_type='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=2820,
       hyperparameters={'max_depth': 5},
   )

Store non-model fields (``id``, ``name``, ``lat``, ``lon``) in your application's data structures, not in OpenSTEF objects.

4. Update pipeline calls
^^^^^^^^^^^^^^^^^^^^^^^^

Replace old pipeline functions with new ones:

.. code-block:: python

   # V3 training
   from openstef.pipeline.train_model import train_model_pipeline
   model = train_model_pipeline(
       pj, 
       data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlruns"
   )
   
   # V4 training
   from openstef.pipeline.train import train_pipeline
   model = train_pipeline(
       dataset,
       config,
       mlflow_tracking_uri="./mlruns"
   )

Check function signatures—some parameters have been renamed or removed.

5. Handle database operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 integrated with ``openstef-dbc`` for data loading. V4 expects you to handle this:

.. code-block:: python

   # V3 (integrated database loading)
   from openstef.data.dbc import DataBase
   db = DataBase()
   data = db.get_model_input(pj)
   
   # V4 (you handle loading)
   import pandas as pd
   from your_app.database import load_forecast_data
   
   df = load_forecast_data(job_id=287)
   dataset = TimeSeriesDataset.from_dataframe(
       df,
       target_column='load',
       feature_columns=['temp', 'humidity']
   )

This gives you flexibility to use any data source: SQL databases, S3, Databricks, etc. See :doc:`data_integration` for patterns.

6. Update model persistence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Model serialization has changed slightly:

.. code-block:: python

   # V3
   from openstef.model.serializer import MLflowSerializer
   serializer = MLflowSerializer(tracking_uri="./mlruns")
   serializer.save_model(model, pj)
   
   # V4
   from openstef.model.serializer import ModelSerializer
   serializer = ModelSerializer(tracking_uri="./mlruns")
   serializer.save(model, config)

The API is similar but no longer requires ``PredictionJobDataClass``.

7. Test thoroughly
^^^^^^^^^^^^^^^^^^

After migration, verify:

- Models train successfully with ``TimeSeriesDataset`` inputs
- Predictions match V3 outputs (within numerical tolerance)
- Feature engineering produces expected columns
- Quantile forecasts cover the same ranges

Common migration pitfalls
--------------------------

**Forgetting to specify target_column**: V4 doesn't assume your target is named ``load``. Always specify it explicitly in ``TimeSeriesDataset.from_dataframe()``.

**Mixing V3 and V4 imports**: These versions are incompatible. Ensure all ``openstef`` imports come from V4 after migration.

**Expecting database integration**: V4 is a pure forecasting library. If you relied on ``openstef-dbc``, you'll need to implement data loading yourself.

**Reusing PredictionJobDataClass**: This class doesn't exist in V4. Extract model settings into ``ModelConfiguration`` and manage job metadata separately.

Benefits of V4
--------------

Despite the migration effort, V4 offers significant advantages:

- **Clearer separation of concerns**: Model configuration is distinct from job metadata
- **Better type safety**: ``TimeSeriesDataset`` validates data structure upfront
- **Library-first design**: V4 is easier to integrate into diverse applications
- **Simplified API**: Fewer parameters and clearer function signatures

Further reading
---------------

- :doc:`use_cases` - See V4 in action with practical examples
- :doc:`data_integration` - Patterns for loading data from various sources
- :doc:`deployment` - Production deployment strategies for V4

.. note::
   If you encounter migration issues not covered here, please open an issue on the OpenSTEF GitHub repository.