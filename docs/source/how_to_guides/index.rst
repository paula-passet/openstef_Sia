How-to Guides
================

This page provides practical, step-by-step guides for common OpenSTEF integration scenarios. These guides focus on real-world deployment patterns and data integration approaches that teams typically need when building forecasting applications with OpenSTEF.

.. note::
   Remember that OpenSTEF is a Python library, not a deployable application. These guides show how to integrate OpenSTEF into your own applications and infrastructure.

Simple Deployment
=================

Cron Job for Scheduled Forecasting
-----------------------------------

The simplest way to deploy OpenSTEF is using a cron job that runs forecasting on a regular schedule. This approach works well for small to medium-scale deployments.

**Step 1: Create the forecasting script**

.. code-block:: python

    #!/usr/bin/env python3
    # forecast_job.py
    
    import pandas as pd
    from openstef.model.regressors import XGBQuantileOpenstfRegressor
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.pipeline.create_forecast import create_forecast_pipeline
    from openstef.data_classes.prediction_job import PredictionJobDataClass
    import logging
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def main():
        try:
            # Load your data (implement load_data function)
            data = load_data()
            
            # Configure prediction job
            pj = PredictionJobDataClass(
                id=1,
                name="my_forecast",
                model="xgb",
                quantiles=[0.1, 0.5, 0.9],
                horizon_minutes=2880,  # 48 hours
                resolution_minutes=15
            )
            
            # Train model (daily or as needed)
            model = train_model_pipeline(pj, data)
            
            # Create forecast
            forecast = create_forecast_pipeline(pj, model, data)
            
            # Save forecast (implement save_forecast function)
            save_forecast(forecast)
            
            logger.info(f"Forecast completed successfully: {len(forecast)} predictions")
            
        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            raise
    
    if __name__ == "__main__":
        main()

**Step 2: Set up the cron job**

.. code-block:: bash

    # Run forecast every 15 minutes
    */15 * * * * /usr/bin/python3 /path/to/forecast_job.py >> /var/log/openstef_forecast.log 2>&1
    
    # Or run hourly for less frequent updates
    0 * * * * /usr/bin/python3 /path/to/forecast_job.py >> /var/log/openstef_forecast.log 2>&1

**Step 3: Add error handling and monitoring**

.. code-block:: python

    import smtplib
    from email.mime.text import MIMEText
    
    def send_alert(message):
        """Send email alert on forecast failure"""
        msg = MIMEText(f"OpenSTEF forecast failed: {message}")
        msg['Subject'] = 'OpenSTEF Forecast Alert'
        msg['From'] = 'alerts@yourcompany.com'
        msg['To'] = 'ops@yourcompany.com'
        
        server = smtplib.SMTP('localhost')
        server.send_message(msg)
        server.quit()

Using Dagster for Orchestration
--------------------------------

For more complex deployments, use Dagster to orchestrate OpenSTEF forecasting workflows.

**Step 1: Install Dagster**

.. code-block:: bash

    pip install dagster dagster-webserver dagster-postgres

**Step 2: Create Dagster assets**

.. code-block:: python

    # dagster_assets.py
    
    from dagster import asset, get_dagster_logger
    import pandas as pd
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.pipeline.create_forecast import create_forecast_pipeline
    
    @asset(group_name="openstef")
    def training_data() -> pd.DataFrame:
        """Load and prepare training data"""
        logger = get_dagster_logger()
        logger.info("Loading training data")
        
        # Your data loading logic here
        data = load_training_data()
        return data
    
    @asset(group_name="openstef")
    def trained_model(training_data: pd.DataFrame):
        """Train OpenSTEF model"""
        logger = get_dagster_logger()
        logger.info("Training OpenSTEF model")
        
        pj = create_prediction_job_config()
        model = train_model_pipeline(pj, training_data)
        return model
    
    @asset(group_name="openstef")
    def forecast(trained_model, training_data: pd.DataFrame) -> pd.DataFrame:
        """Generate forecast"""
        logger = get_dagster_logger()
        logger.info("Creating forecast")
        
        pj = create_prediction_job_config()
        forecast_df = create_forecast_pipeline(pj, trained_model, training_data)
        
        # Save to your storage system
        save_forecast_to_storage(forecast_df)
        return forecast_df

**Step 3: Configure schedules**

.. code-block:: python

    # dagster_schedules.py
    
    from dagster import schedule, DefaultScheduleStatus
    from .dagster_assets import forecast
    
    @schedule(
        job_name="openstef_forecast_job",
        cron_schedule="*/15 * * * *",  # Every 15 minutes
        default_status=DefaultScheduleStatus.RUNNING
    )
    def forecast_schedule(context):
        return {}

Minimal Production Setup
-------------------------

A minimal production setup includes error handling, monitoring, and data persistence:

.. code-block:: python

    # production_forecast.py
    
    import os
    import sys
    import json
    import traceback
    from datetime import datetime, timedelta
    from pathlib import Path
    
    import pandas as pd
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.pipeline.create_forecast import create_forecast_pipeline
    
    class ProductionForecaster:
        def __init__(self, config_path: str):
            with open(config_path) as f:
                self.config = json.load(f)
            
            self.model_cache_path = Path(self.config["model_cache_dir"])
            self.model_cache_path.mkdir(exist_ok=True)
        
        def should_retrain_model(self, model_path: Path) -> bool:
            """Check if model needs retraining"""
            if not model_path.exists():
                return True
            
            # Retrain daily
            model_age = datetime.now() - datetime.fromtimestamp(model_path.stat().st_mtime)
            return model_age > timedelta(days=1)
        
        def run_forecast(self):
            """Run complete forecasting pipeline"""
            try:
                # Load data
                data = self.load_data()
                
                # Check if we need to retrain
                model_path = self.model_cache_path / "model.pkl"
                
                if self.should_retrain_model(model_path):
                    print("Training new model...")
                    model = train_model_pipeline(self.config["prediction_job"], data)
                    
                    # Cache model
                    import pickle
                    with open(model_path, 'wb') as f:
                        pickle.dump(model, f)
                else:
                    print("Using cached model...")
                    import pickle
                    with open(model_path, 'rb') as f:
                        model = pickle.load(f)
                
                # Create forecast
                forecast = create_forecast_pipeline(
                    self.config["prediction_job"], 
                    model, 
                    data
                )
                
                # Save results
                self.save_forecast(forecast)
                return True
                
            except Exception as e:
                print(f"Forecast failed: {e}")
                traceback.print_exc()
                return False
    
    if __name__ == "__main__":
        forecaster = ProductionForecaster("config.json")
        success = forecaster.run_forecast()
        sys.exit(0 if success else 1)

Data Integration
================

Connecting to S3
----------------

**Reading Input Data from S3**

.. code-block:: python

    import boto3
    import pandas as pd
    from io import StringIO
    
    def load_data_from_s3(bucket: str, key: str) -> pd.DataFrame:
        """Load training data from S3"""
        s3_client = boto3.client('s3')
        
        try:
            # Download file
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            # Parse CSV
            df = pd.read_csv(StringIO(content), parse_dates=['datetime'])
            df.set_index('datetime', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Failed to load data from S3: {e}")
            raise
    
    # Usage
    training_data = load_data_from_s3("my-energy-bucket", "data/training_data.csv")

**Writing Forecasts to S3**

.. code-block:: python

    import boto3
    from datetime import datetime
    from io import StringIO
    
    def save_forecast_to_s3(forecast: pd.DataFrame, bucket: str, base_key: str):
        """Save forecast results to S3 with timestamp"""
        s3_client = boto3.client('s3')
        
        # Create timestamped key
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"{base_key}/forecast_{timestamp}.csv"
        
        # Convert to CSV
        csv_buffer = StringIO()
        forecast.to_csv(csv_buffer)
        
        try:
            # Upload to S3
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=csv_buffer.getvalue(),
                ContentType='text/csv'
            )
            
            print(f"Forecast saved to s3://{bucket}/{key}")
            
            # Also save as "latest" for easy access
            latest_key = f"{base_key}/latest_forecast.csv"
            s3_client.put_object(
                Bucket=bucket,
                Key=latest_key,
                Body=csv_buffer.getvalue(),
                ContentType='text/csv'
            )
            
        except Exception as e:
            print(f"Failed to save forecast to S3: {e}")
            raise
    
    # Usage
    save_forecast_to_s3(forecast_df, "my-energy-bucket", "forecasts/congestion")

**S3 Configuration with Environment Variables**

.. code-block:: python

    import os
    import boto3
    from botocore.config import Config
    
    def create_s3_client():
        """Create configured S3 client"""
        config = Config(
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        
        return boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            config=config
        )

Databricks Integration
----------------------

**Setting up OpenSTEF in Databricks**

.. code-block:: python

    # Databricks notebook cell 1: Install OpenSTEF
    %pip install openstef
    
    # Databricks notebook cell 2: Load data from Delta Lake
    import pandas as pd
    
    # Read from Delta table
    spark_df = spark.table("energy_data.meter_readings")
    
    # Convert to pandas for OpenSTEF
    training_data = spark_df.toPandas()
    training_data['datetime'] = pd.to_datetime(training_data['datetime'])
    training_data.set_index('datetime', inplace=True)

**Running Forecasts in Databricks Jobs**

.. code-block:: python

    # databricks_forecast_job.py
    
    from pyspark.sql import SparkSession
    import pandas as pd
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.pipeline.create_forecast import create_forecast_pipeline
    from openstef.data_classes.prediction_job import PredictionJobDataClass
    
    def main():
        # Initialize Spark
        spark = SparkSession.builder.appName("OpenSTEF-Forecast").getOrCreate()
        
        try:
            # Load data from Delta Lake
            spark_df = spark.sql("""
                SELECT datetime, load, temperature, radiation, windspeed
                FROM energy_data.meter_readings 
                WHERE datetime >= current_date() - INTERVAL 30 DAYS
                ORDER BY datetime
            """)
            
            # Convert to pandas
            data = spark_df.toPandas()
            data['datetime'] = pd.to_datetime(data['datetime'])
            data.set_index('datetime', inplace=True)
            
            # Configure prediction job
            pj = PredictionJobDataClass(
                id=1,
                name="databricks_forecast",
                model="xgb",
                quantiles=[0.1, 0.5, 0.9],
                horizon_minutes=2880,
                resolution_minutes=15
            )
            
            # Train and forecast
            model = train_model_pipeline(pj, data)
            forecast = create_forecast_pipeline(pj, model, data)
            
            # Convert back to Spark DataFrame and save
            forecast_spark = spark.createDataFrame(forecast.reset_index())
            
            forecast_spark.write \
                .mode("overwrite") \
                .option("overwriteSchema", "true") \
                .saveAsTable("energy_data.forecasts")
            
            print(f"Forecast completed: {len(forecast)} predictions saved")
            
        finally:
            spark.stop()
    
    if __name__ == "__main__":
        main()

**Databricks Workflow Configuration**

.. code-block:: json

    {
      "name": "OpenSTEF Forecasting Pipeline",
      "tasks": [
        {
          "task_key": "train_and_forecast",
          "python_wheel_task": {
            "package_name": "openstef_databricks",
            "entry_point": "main"
          },
          "job_cluster_key": "forecast_cluster",
          "timeout_seconds": 3600
        }
      ],
      "job_clusters": [
        {
          "job_cluster_key": "forecast_cluster",
          "new_cluster": {
            "spark_version": "12.2.x-scala2.12",
            "node_type_id": "i3.xlarge",
            "num_workers": 2,
            "spark_conf": {
              "spark.sql.adaptive.enabled": "true"
            }
          }
        }
      ],
      "schedule": {
        "quartz_cron_expression": "0 */15 * * * ?",
        "timezone_id": "UTC"
      }
    }

InfluxDB Integration
--------------------

**Reading Time Series Data from InfluxDB**

.. code-block:: python

    from influxdb_client import InfluxDBClient
    import pandas as pd
    from datetime import datetime, timedelta
    
    def load_data_from_influxdb(bucket: str, measurement: str, days_back: int = 30) -> pd.DataFrame:
        """Load training data from InfluxDB"""
        
        client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL"),
            token=os.getenv("INFLUXDB_TOKEN"),
            org=os.getenv("INFLUXDB_ORG