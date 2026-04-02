How-To Guides
=============

This page provides practical guides for specific implementation tasks when working with OpenSTEF as a library in your energy forecasting system. These guides focus on integration patterns, deployment strategies, and migration paths that go beyond basic tutorials.

.. note::
   Looking for your first forecast? Start with the :doc:`../getting_started/quickstart`. For comprehensive learning, see :doc:`../getting_started/tutorials`.


Deployment and Orchestration
-----------------------------

OpenSTEF is a Python library that you integrate into your own forecasting system. You need to orchestrate when models are trained and predictions are made. Here are common deployment patterns.


Simple Cron-Based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, use cron jobs to schedule training and prediction tasks. This approach works well for small to medium-scale operations with predictable schedules.

Create a Python script that runs your forecasting workflow:

.. code-block:: python

   # forecast_job.py
   from datetime import timedelta
   from openstef.workflow import ForecastingWorkflow
   from openstef.storage import LocalModelStorage
   from my_data_layer import load_forecast_data
   
   def run_forecast(model_id: str):
       """Execute a single forecast run."""
       # Load your data
       dataset = load_forecast_data(
           model_id=model_id,
           lookback=timedelta(days=7)
       )
       
       # Load workflow from storage (or create if first run)
       storage = LocalModelStorage(base_path="/var/openstef/models")
       try:
           workflow = ForecastingWorkflow.from_storage(
               model_id=model_id,
               storage=storage
           )
       except FileNotFoundError:
           # First run - create and train new workflow
           from openstef.workflow import create_forecasting_workflow
           from openstef.workflow.config import ForecastingWorkflowConfig
           
           config = ForecastingWorkflowConfig(
               model_id=model_id,
               horizons=["PT24H"],
               target_column="load"
           )
           workflow = create_forecasting_workflow(config)
           workflow.fit(dataset)
           workflow.to_storage(storage)
       
       # Generate predictions
       predictions = workflow.predict(dataset)
       
       # Store results (implement your own storage)
       from my_data_layer import save_predictions
       save_predictions(model_id, predictions)
   
   if __name__ == "__main__":
       import sys
       run_forecast(sys.argv[1])

Schedule this script with cron:

.. code-block:: bash

   # Run predictions every hour at 15 minutes past
   15 * * * * /usr/bin/python3 /opt/forecast_job.py "substation_001" >> /var/log/forecast.log 2>&1
   
   # Retrain models daily at 2 AM
   0 2 * * * /usr/bin/python3 /opt/retrain_job.py "substation_001" >> /var/log/retrain.log 2>&1

For the retraining script, follow a similar pattern but call ``workflow.fit()`` with fresh training data before saving back to storage.


Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^^

For production systems requiring dependency management, monitoring, and complex scheduling, Dagster provides a robust orchestration framework. OpenSTEF integrates naturally as Dagster assets or ops.

.. code-block:: python

   # dagster_forecast_pipeline.py
   from dagster import asset, AssetExecutionContext, DailyPartitionsDefinition
   from datetime import datetime, timedelta
   from openstef.workflow import ForecastingWorkflow
   from openstef.storage import LocalModelStorage
   
   # Define partitions for daily model retraining
   daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")
   
   @asset(partitions_def=daily_partitions)
   def training_data(context: AssetExecutionContext) -> dict:
       """Load and prepare training data for model."""
       partition_date = datetime.fromisoformat(context.partition_key)
       
       # Your data loading logic
       from my_data_layer import load_training_data
       dataset = load_training_data(
           start=partition_date - timedelta(days=365),
           end=partition_date
       )
       
       return {
           "dataset": dataset,
           "model_id": "substation_001",
           "partition_date": partition_date
       }
   
   @asset(deps=[training_data])
   def trained_model(context: AssetExecutionContext, training_data: dict):
       """Train forecasting model on prepared data."""
       from openstef.workflow import create_forecasting_workflow
       from openstef.workflow.config import ForecastingWorkflowConfig
       
       config = ForecastingWorkflowConfig(
           model_id=training_data["model_id"],
           horizons=["PT24H", "PT48H"],
           target_column="load"
       )
       
       workflow = create_forecasting_workflow(config)
       workflow.fit(training_data["dataset"])
       
       # Persist to storage
       storage = LocalModelStorage(base_path="/var/openstef/models")
       workflow.to_storage(storage)
       
       context.log.info(f"Model trained for {training_data['model_id']}")
   
   @asset
   def hourly_forecast(context: AssetExecutionContext, trained_model):
       """Generate hourly forecasts using latest trained model."""
       from my_data_layer import load_forecast_data, save_predictions
       
       model_id = "substation_001"
       dataset = load_forecast_data(model_id, lookback=timedelta(days=7))
       
       storage = LocalModelStorage(base_path="/var/openstef/models")
       workflow = ForecastingWorkflow.from_storage(model_id, storage)
       
       predictions = workflow.predict(dataset)
       save_predictions(model_id, predictions)
       
       context.log.info(f"Generated forecast with {len(predictions.data)} points")

Configure Dagster to run ``hourly_forecast`` every hour and ``trained_model`` daily. Dagster handles dependency resolution, retry logic, and monitoring dashboards automatically.


Data Integration Patterns
--------------------------

OpenSTEF requires time series data as input and produces forecast outputs. You need to integrate with your data infrastructure to load inputs and store results.


Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides built-in S3 storage for benchmark results. For general data integration, use standard Python libraries to load data from S3 into OpenSTEF's expected format.

.. code-block:: python

   # s3_data_integration.py
   import pandas as pd
   from datetime import timedelta
   import boto3
   from io import StringIO
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_data_from_s3(bucket: str, key: str) -> TimeSeriesDataset:
       """Load time series data from S3 CSV file."""
       s3_client = boto3.client('s3')
       
       # Download CSV from S3
       response = s3_client.get_object(Bucket=bucket, Key=key)
       csv_content = response['Body'].read().decode('utf-8')
       
       # Parse into DataFrame
       df = pd.read_csv(
           StringIO(csv_content),
           parse_dates=['timestamp'],
           index_col='timestamp'
       )
       
       # Convert to OpenSTEF dataset
       return TimeSeriesDataset(
           data=df,
           sample_interval=timedelta(hours=1)
       )
   
   def save_predictions_to_s3(
       predictions: TimeSeriesDataset,
       bucket: str,
       key: str
   ):
       """Save forecast results to S3 as CSV."""
       s3_client = boto3.client('s3')
       
       # Convert to CSV
       csv_buffer = StringIO()
       predictions.data.to_csv(csv_buffer)
       
       # Upload to S3
       s3_client.put_object(
           Bucket=bucket,
           Key=key,
           Body=csv_buffer.getvalue()
       )

For model storage on S3, use the provided ``S3BenchmarkStorage`` class:

.. code-block:: python

   from openstef_beam.benchmarking.storage import S3BenchmarkStorage, LocalBenchmarkStorage
   
   # Create hybrid storage (local + S3 sync)
   local_storage = LocalBenchmarkStorage(base_path="/tmp/models")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="my-openstef-models",
       s3_prefix="production/",
       s3fs_kwargs={"key": "ACCESS_KEY", "secret": "SECRET_KEY"}
   )
   
   # Use with workflows - writes go to both local and S3
   workflow.to_storage(s3_storage)

.. note::
   The ``S3BenchmarkStorage`` requires the ``s3fs`` package. Install with ``pip install openstef[s3]``.


Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^^

When running OpenSTEF in Databricks, leverage Spark DataFrames for data loading and Delta Lake for storage.

.. code-block:: python

   # databricks_integration.py
   from pyspark.sql import SparkSession
   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_delta_table(
       spark: SparkSession,
       table_name: str,
       start_date: str,
       end_date: str
   ) -> TimeSeriesDataset:
       """Load time series from Delta table."""
       # Query Delta table
       df_spark = spark.sql(f"""
           SELECT timestamp, load, temperature, radiation, windspeed
           FROM {table_name}
           WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
           ORDER BY timestamp
       """)
       
       # Convert to pandas (OpenSTEF uses pandas internally)
       df_pandas = df_spark.toPandas()
       df_pandas['timestamp'] = pd.to_datetime(df_pandas['timestamp'])
       df_pandas.set_index('timestamp', inplace=True)
       
       return TimeSeriesDataset(
           data=df_pandas,
           sample_interval=timedelta(hours=1)
       )
   
   def save_to_delta_table(
       spark: SparkSession,
       predictions: TimeSeriesDataset,
       table_name: str
   ):
       """Save predictions to Delta table."""
       # Convert to Spark DataFrame
       df_spark = spark.createDataFrame(predictions.data.reset_index())
       
       # Write to Delta (append mode for new predictions)
       df_spark.write.format("delta").mode("append").saveAsTable(table_name)

Run OpenSTEF forecasting jobs as Databricks notebooks or scheduled jobs, using the cluster's distributed computing for data preparation while OpenSTEF handles the ML forecasting.


InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

InfluxDB is common for storing time series energy data. Use the InfluxDB client to query data and write forecasts.

.. code-block:: python

   # influxdb_integration.py
   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_influxdb(
       url: str,
       token: str,
       org: str,
       bucket: str,
       measurement: str,
       start: str,
       stop: str
   ) -> TimeSeriesDataset:
       """Load time series data from InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       query_api = client.query_api()
       
       # Flux query to retrieve data
       query = f'''
       from(bucket: "{bucket}")
           |> range(start: {start}, stop: {stop})
           |> filter(fn: (r) => r["_measurement"] == "{measurement}")
           |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
       '''
       
       result = query_api.query_data_frame(query)
       
       # Transform to expected format
       result['_time'] = pd.to_datetime(result['_time'])
       result.set_index('_time', inplace=True)
       result.index.name = 'timestamp'
       
       # Select relevant columns
       data_columns = ['load', 'temperature', 'radiation', 'windspeed']
       df = result[data_columns]
       
       client.close()
       
       return TimeSeriesDataset(
           data=df,
           sample_interval=timedelta(hours=1)
       )
   
   def write_forecasts_to_influxdb(
       predictions: TimeSeriesDataset,
       url: str,
       token: str,
       org: str,
       bucket: str,
       measurement: str = "forecast"
   ):
       """Write forecast results to InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       write_api = client.write_api(write_options=SYNCHRONOUS)
       
       # Convert predictions to InfluxDB points
       for timestamp, row in predictions.data.iterrows():
           point = Point(measurement)
           point.time(timestamp)
           
           # Write each forecast column as a field
           for column in predictions.data.columns:
               point.field(column, float(row[column]))
           
           write_api.write(bucket=bucket, record=point)
       
       client.close()

This pattern works for both loading historical data for training and storing forecast outputs for downstream consumption.


Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 introduced significant architectural changes to improve modularity and maintainability. This guide helps you migrate existing V3 code to V4.


Key Breaking Changes
^^^^^^^^^^^^^^^^^^^^

**Package Structure**

V3 was a single package. V4 is a monorepo with multiple packages:

- ``openstef-core``: Core data structures and utilities
- ``openstef``: Main forecasting library (workflows, models)
- ``openstef-beam``: Backtesting and benchmarking framework
- ``openstef-reference``: Reference implementations and examples

Update your imports:

.. code-block:: python

   # V3
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   
   # V4
   from openstef.forecasters import XGBQuantileForecaster
   from openstef.workflow import ForecastingWorkflow, create_forecasting_workflow

**Workflow API**

V3 used pipeline functions. V4 uses object-oriented workflows:

.. code-block:: python

   # V3 approach
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   model = train_model_pipeline(pj, input_data)
   forecast = create_forecast_pipeline(pj, input_data, model)
   
   # V4 approach
   from openstef.workflow import create_forecasting_workflow
   from openstef.workflow.config import ForecastingWorkflowConfig
   
   config = ForecastingWorkflowConfig(
       model_id="my_model",
       horizons=["PT24H"],
       target_column="load"
   )
   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)
   predictions = workflow.predict(dataset)

**Data Structures**

V3 used ``PredictionJobDataClass`` for configuration. V4 uses Pydantic models:

.. code-block:: python

   # V3
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   pj = PredictionJobDataClass(
       id=1,
       model="xgb",
       horizon_minutes=1440,
       resolution_minutes=15
   )
   
   # V4
   from openstef.workflow.config import ForecastingWorkflowConfig
   from openstef_core.enums import LeadTime
   
   config = ForecastingWorkflowConfig(
       model_id="model_1",
       model="xgb",
       horizons=[LeadTime.from_string("PT24H")],
       sample_interval=timedelta(minutes=15)
   )

**Model Storage**

V3 used MLflow or custom storage. V4 has a standardized storage interface:

.. code-block:: python

   # V3
   # Custom implementation required
   
   # V4
   from openstef.storage import LocalModelStorage
   
   storage = LocalModelStorage(base_path="/var/models")
   workflow.to_storage(storage)
   
   # Later: reload from storage
   workflow = ForecastingWorkflow.from_storage(
       model_id="my_model",
       storage=storage
   )


Migration Strategy
^^^^^^^^^^^^^^^^^^

**Step 1: Update Dependencies**

Replace V3 package with V4 packages in your ``requirements.txt``:

.. code-block:: text

   # Old
   openstef==3.x.x
   
   # New
   openstef==4.x.x
   openstef-core==4.x.x
   openstef-beam==4.x.x  # If using backtesting

**Step 2: Refactor Configuration**

Convert ``PredictionJobDataClass`` instances to ``ForecastingWorkflowConfig``:

.. code-block:: python

   # Migration helper function
   def convert_pj_to_config(pj: PredictionJobDataClass) -> ForecastingWorkflowConfig:
       """Convert V3 PredictionJob to V4 config."""
       from openstef.workflow.config import ForecastingWorkflowConfig
       from openstef_core.enums import LeadTime
       
       return ForecastingWorkflowConfig(
           model_id=str(pj.id),
           model=pj.model,
           horizons=[LeadTime(minutes=pj.horizon_minutes)],
           target_column="load",  # V4 requires explicit target
           sample_interval=timedelta(minutes=pj.resolution_minutes)
       )

**Step 3: Replace Pipeline Calls**

Wrap V3 pipeline calls with V4 workflow equivalents:

.. code-block:: python

   # V3 training
   trained_model = train_model_pipeline(pj, input_data)
   
   # V4 equivalent
   config = convert_pj_to_config(pj)
   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)

**Step 4: Update Data Loading**

V4 uses ``TimeSeriesDataset`` instead of raw DataFrames:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta
   
   # Wrap your existing DataFrame
   dataset = TimeSeriesDataset(
       data=your_dataframe,  # Must have DatetimeIndex
       sample_interval=timedelta(minutes=15)
   )

**Step 5: Migrate Storage**

If you used MLflow in V3, create a storage adapter or use V4's built-in storage:

.. code-block:: python

   from openstef.storage import LocalModelStorage
   
   # Initialize storage
   storage = LocalModelStorage(base_path="/path/to/models")
   
   # Save after training
   workflow.to_storage(storage)
   
   # Load for prediction
   workflow = ForecastingWorkflow.from_storage(model_id, storage)


Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^

**Issue: Missing model files after upgrade**

V3 and V4 use different serialization formats. You need to retrain models in V4:

.. code-block:: python

   # Load V3 training data
   historical_data = load_historical_data()
   
   # Train fresh V4 model
   dataset = TimeSeriesDataset(data=historical_data, sample_interval=timedelta(hours=1))
   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)
   workflow.to_storage(storage)

**Issue: Import errors for specific models**

Some V3 model names changed in V4:

.. code-block:: python

   # V3: XGBQuantileOpenstfRegressor
   # V4: XGBQuantileForecaster
   
   # V3: LinearQuantileOpenstfRegressor  
   # V4: LinearQuantileForecaster

Update your model configuration strings accordingly.

**Issue: Different prediction output format**

V4 predictions return ``TimeSeriesDataset`` objects instead of raw DataFrames:

.. code-block:: python

   # V4 prediction
   predictions = workflow.predict(dataset)
   
   # Access underlying DataFrame
   forecast_df = predictions.data
   
   # Continue with your existing DataFrame processing
   process_forecast(forecast_df)


Further Resources
-----------------

- :doc:`../getting_started/tutorials` - Learn V4 patterns from scratch
- :doc:`use_cases` - Understand different forecasting scenarios
- :doc:`faq` - Common questions about OpenSTEF usage
- :doc:`../reference/concepts` - Deep dive into forecasting concepts

For migration questions, reach out to the OpenSTEF community on Slack or GitHub Discussions.