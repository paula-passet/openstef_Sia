Data Integration
================

OpenSTEF is designed to integrate seamlessly with your existing data infrastructure. This page covers practical patterns for reading input data from various sources, writing forecasts back to storage systems, and handling common data quality challenges in production forecasting pipelines.

Reading Input Data
------------------

OpenSTEF works with pandas DataFrames wrapped in typed dataset classes. The library doesn't prescribe specific data sources—you're free to load data from any system that can produce a DataFrame.

Basic Pattern
^^^^^^^^^^^^^

The fundamental pattern involves loading data into a DataFrame, then wrapping it in the appropriate dataset class:

.. code-block:: python

    import pandas as pd
    from datetime import datetime, timedelta
    from openstef.datasets import ForecastInputDataset
    
    # Load from any source (CSV, database, API, etc.)
    df = pd.read_csv("load_data.csv", index_col="timestamp", parse_dates=True)
    
    # Wrap in OpenSTEF dataset
    input_data = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
        forecast_start=datetime(2024, 1, 1)
    )

The dataset classes validate column requirements and handle temporal metadata. For training data, use ``VersionedTimeSeriesDataset`` to preserve data versioning:

.. code-block:: python

    from openstef.datasets import VersionedTimeSeriesDataset
    
    # For training: preserve when each data point became available
    training_data = VersionedTimeSeriesDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load"
    )

Reading from Databases
^^^^^^^^^^^^^^^^^^^^^^

PostgreSQL and other SQL databases are common sources for time series data:

.. code-block:: python

    import psycopg2
    import pandas as pd
    from openstef.datasets import ForecastInputDataset
    
    def load_forecast_input(connection_string, target_id, start_date, end_date):
        """Load forecast input from PostgreSQL."""
        query = """
            SELECT timestamp, load, temperature, wind_speed, solar_radiation
            FROM measurements
            WHERE target_id = %s
              AND timestamp BETWEEN %s AND %s
            ORDER BY timestamp
        """
        
        with psycopg2.connect(connection_string) as conn:
            df = pd.read_sql_query(
                query,
                conn,
                params=(target_id, start_date, end_date),
                index_col="timestamp",
                parse_dates=["timestamp"]
            )
        
        return ForecastInputDataset(
            data=df,
            sample_interval=timedelta(minutes=15),
            target_column="load",
            forecast_start=end_date
        )

For InfluxDB, adapt the query syntax:

.. code-block:: python

    from influxdb_client import InfluxDBClient
    
    def load_from_influxdb(url, token, org, bucket, target_id, start, end):
        """Load forecast input from InfluxDB."""
        client = InfluxDBClient(url=url, token=token, org=org)
        query_api = client.query_api()
        
        query = f'''
            from(bucket: "{bucket}")
              |> range(start: {start.isoformat()}, stop: {end.isoformat()})
              |> filter(fn: (r) => r["target_id"] == "{target_id}")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        result = query_api.query_data_frame(query)
        result.set_index("_time", inplace=True)
        
        return ForecastInputDataset(
            data=result,
            sample_interval=timedelta(minutes=15),
            target_column="load"
        )

Reading from Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^

For S3, Databricks, or other cloud storage, use parquet files for efficient time series storage:

.. code-block:: python

    import boto3
    import pandas as pd
    from io import BytesIO
    
    def load_from_s3(bucket, key, forecast_start):
        """Load forecast input from S3 parquet file."""
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket, Key=key)
        
        df = pd.read_parquet(BytesIO(obj['Body'].read()))
        
        return ForecastInputDataset(
            data=df,
            sample_interval=timedelta(minutes=15),
            target_column="load",
            forecast_start=forecast_start
        )

For Databricks, leverage the native integration:

.. code-block:: python

    from pyspark.sql import SparkSession
    
    def load_from_databricks(table_name, target_id, start_date, end_date):
        """Load forecast input from Databricks Delta table."""
        spark = SparkSession.builder.getOrCreate()
        
        df_spark = spark.sql(f"""
            SELECT * FROM {table_name}
            WHERE target_id = '{target_id}'
              AND timestamp BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY timestamp
        """)
        
        # Convert to pandas for OpenSTEF
        df = df_spark.toPandas()
        df.set_index("timestamp", inplace=True)
        
        return ForecastInputDataset(
            data=df,
            sample_interval=timedelta(minutes=15),
            target_column="load",
            forecast_start=end_date
        )

Combining Multiple Data Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Real forecasting pipelines often combine data from multiple sources. Use OpenSTEF's built-in utilities:

.. code-block:: python

    from openstef.datasets.utils import combine_forecast_input_datasets
    
    # Load base measurements from database
    measurements = load_from_postgres(conn_string, target_id, start, end)
    
    # Load weather forecasts from S3
    weather = load_weather_from_s3(bucket, target_id, start, end)
    
    # Combine datasets
    combined = combine_forecast_input_datasets(
        input_data=measurements,
        additional_features=weather
    )

This function handles column alignment, index matching, and preserves metadata from the primary dataset.

Writing Forecast Output
------------------------

After generating forecasts, write results back to your storage systems for downstream consumption.

Writing to Databases
^^^^^^^^^^^^^^^^^^^^

Store forecasts with metadata for traceability:

.. code-block:: python

    def save_forecast_to_postgres(forecast, connection_string, target_id, model_id):
        """Save forecast results to PostgreSQL."""
        df = forecast.data.reset_index()
        df['target_id'] = target_id
        df['model_id'] = model_id
        df['forecast_start'] = forecast.forecast_start
        df['created_at'] = datetime.now()
        
        with psycopg2.connect(connection_string) as conn:
            # Use copy for better performance
            with conn.cursor() as cur:
                # Create temporary table
                cur.execute("""
                    CREATE TEMP TABLE forecast_staging (LIKE forecasts INCLUDING ALL)
                """)
                
                # Bulk insert
                from io import StringIO
                buffer = StringIO()
                df.to_csv(buffer, index=False, header=False)
                buffer.seek(0)
                
                cur.copy_from(buffer, 'forecast_staging', sep=',')
                
                # Upsert into main table
                cur.execute("""
                    INSERT INTO forecasts
                    SELECT * FROM forecast_staging
                    ON CONFLICT (target_id, timestamp, forecast_start)
                    DO UPDATE SET
                        load = EXCLUDED.load,
                        updated_at = EXCLUDED.created_at
                """)
                
                conn.commit()

Writing to Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^

For cloud storage, use parquet format with partitioning for efficient queries:

.. code-block:: python

    def save_forecast_to_s3(forecast, bucket, target_id, model_id):
        """Save forecast to S3 with date partitioning."""
        df = forecast.data.reset_index()
        df['target_id'] = target_id
        df['model_id'] = model_id
        df['forecast_start'] = forecast.forecast_start
        
        # Add partition columns
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month
        df['day'] = df['timestamp'].dt.day
        
        # Write partitioned parquet
        key = f"forecasts/target={target_id}/year={df['year'].iloc[0]}/month={df['month'].iloc[0]}/forecast_{forecast.forecast_start.isoformat()}.parquet"
        
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        
        s3 = boto3.client('s3')
        s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())

Using Storage Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^

For automated storage during workflows, use callbacks. OpenSTEF includes a ``DataSaveCallback`` for debugging:

.. code-block:: python

    from openstef.callbacks import DataSaveCallback
    from pathlib import Path
    
    # Save intermediate data during workflow execution
    callback = DataSaveCallback(
        cache_dir=Path("./debug_output"),
        save_predict_data=True,
        save_forecast=True,
        save_contributions=True
    )
    
    # Attach to workflow
    workflow.add_callback(callback)

This automatically saves prediction inputs, forecasts, and feature contributions to parquet files for inspection.

Handling Missing Data
---------------------

Real-world data pipelines inevitably encounter missing values. OpenSTEF provides several strategies for handling gaps.

Detection and Validation
^^^^^^^^^^^^^^^^^^^^^^^^^

Dataset classes validate data quality on construction. Add custom validation for your requirements:

.. code-block:: python

    def validate_data_completeness(df, max_gap_hours=2):
        """Validate that data has no large gaps."""
        time_diff = df.index.to_series().diff()
        max_gap = time_diff.max()
        
        if max_gap > timedelta(hours=max_gap_hours):
            raise ValueError(f"Data contains gap of {max_gap}, exceeding {max_gap_hours} hour limit")
        
        # Check for missing values in critical columns
        critical_columns = ['load', 'temperature']
        missing = df[critical_columns].isnull().sum()
        
        if missing.any():
            raise ValueError(f"Missing values in critical columns: {missing[missing > 0].to_dict()}")

Imputation Strategies
^^^^^^^^^^^^^^^^^^^^^

For training data, use preprocessing transforms to handle missing values:

.. code-block:: python

    from openstef.preprocessing import TransformPipeline
    
    # Define preprocessing with imputation
    preprocessing = TransformPipeline()
    # Add transforms for handling missing data
    # (specific transforms depend on your OpenSTEF version)
    
    # Apply to data before training
    cleaned_data = preprocessing.fit_transform(training_data)

For prediction data, ensure completeness before forecasting:

.. code-block:: python

    def prepare_prediction_data(df, forecast_start):
        """Prepare prediction data with forward-fill for small gaps."""
        # Forward-fill small gaps (up to 2 hours)
        df_filled = df.fillna(method='ffill', limit=8)  # 8 * 15min = 2 hours
        
        # Check if any gaps remain
        if df_filled.isnull().any().any():
            raise ValueError("Data contains gaps that cannot be safely filled")
        
        return ForecastInputDataset(
            data=df_filled,
            sample_interval=timedelta(minutes=15),
            forecast_start=forecast_start
        )

Data Quality Monitoring
^^^^^^^^^^^^^^^^^^^^^^^

Implement monitoring to catch data quality issues early:

.. code-block:: python

    def monitor_data_quality(df, target_id):
        """Log data quality metrics for monitoring."""
        metrics = {
            'target_id': target_id,
            'timestamp': datetime.now(),
            'row_count': len(df),
            'missing_load': df['load'].isnull().sum(),
            'missing_temperature': df['temperature'].isnull().sum(),
            'load_mean': df['load'].mean(),
            'load_std': df['load'].std(),
            'time_span_hours': (df.index.max() - df.index.min()).total_seconds() / 3600
        }
        
        # Log to your monitoring system
        # logger.info("Data quality metrics", extra=metrics)
        
        return metrics

Complete Pipeline Example
--------------------------

Here's a realistic end-to-end data integration pipeline:

.. code-block:: python

    from datetime import datetime, timedelta
    from openstef.datasets import ForecastInputDataset
    from openstef.workflows import ForecastingWorkflow
    
    def run_forecast_pipeline(target_id, forecast_start):
        """Complete pipeline: load data, forecast, save results."""
        
        # 1. Load historical data for context
        lookback_days = 60
        start_date = forecast_start - timedelta(days=lookback_days)
        
        try:
            # Load measurements from database
            measurements = load_from_postgres(
                conn_string=DB_CONNECTION,
                target_id=target_id,
                start_date=start_date,
                end_date=forecast_start
            )
            
            # Load weather forecasts from S3
            weather = load_weather_from_s3(
                bucket=WEATHER_BUCKET,
                target_id=target_id,
                start=start_date,
                end=forecast_start + timedelta(hours=48)
            )
            
            # Combine data sources
            input_data = combine_forecast_input_datasets(
                input_data=measurements,
                additional_features=weather
            )
            
            # Validate data quality
            validate_data_completeness(input_data.data)
            quality_metrics = monitor_data_quality(input_data.data, target_id)
            
        except Exception as e:
            # Log error and alert
            logger.error(f"Data loading failed for {target_id}: {e}")
            raise
        
        # 2. Generate forecast
        workflow = ForecastingWorkflow(model_id=f"{target_id}_model")
        forecast = workflow.predict(input_data)
        
        # 3. Save results to multiple destinations
        try:
            # Primary storage: database
            save_forecast_to_postgres(
                forecast=forecast,
                connection_string=DB_CONNECTION,
                target_id=target_id,
                model_id=workflow.model_id
            )
            
            # Backup storage: S3
            save_forecast_to_s3(
                forecast=forecast,
                bucket=FORECAST_BUCKET,
                target_id=target_id,
                model_id=workflow.model_id
            )
            
            logger.info(f"Successfully saved forecast for {target_id}")
            
        except Exception as e:
            logger.error(f"Forecast storage failed for {target_id}: {e}")
            raise
        
        return forecast

This pattern separates concerns, handles errors gracefully, and provides observability through logging and monitoring.

Custom Storage Backends
------------------------

For enterprise deployments, implement custom storage backends by extending OpenSTEF's storage interfaces. The benchmark storage interface provides a template:

.. code-block:: python

    from openstef.benchmarking.storage import BenchmarkStorage
    from openstef.datasets import TimeSeriesDataset
    
    class CustomEnterpriseStorage(BenchmarkStorage):
        """Custom storage backend for enterprise data lake."""
        
        def __init__(self, connection_config):
            self.config = connection_config
            # Initialize your storage client
        
        def save_backtest_output(self, target, output):
            """Save backtest results to enterprise storage."""
            # Implement your storage logic
            pass
        
        def load_backtest_output(self, target):
            """Load backtest results from enterprise storage."""
            # Implement your retrieval logic
            pass
        
        def has_backtest_output(self, target):
            """Check if backtest output exists."""
            # Implement your existence check
            pass

This approach allows seamless integration with proprietary storage systems while maintaining compatibility with OpenSTEF workflows.

See Also
--------

- :doc:`use_cases` - Common forecasting scenarios and patterns
- :doc:`deployment` - Production deployment architectures
- :doc:`logging` - Logging configuration for data pipeline monitoring