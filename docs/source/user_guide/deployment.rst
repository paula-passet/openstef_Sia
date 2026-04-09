Production Deployment
======================

This guide covers deployment patterns for running OpenSTEF in production environments, from simple scheduled jobs to full orchestration platforms. OpenSTEF is a Python library, so deployment involves integrating it into your infrastructure using standard Python deployment practices.

Deployment Approaches
---------------------

Simple Scheduled Jobs
^^^^^^^^^^^^^^^^^^^^^

For straightforward forecasting tasks, scheduled Python scripts are often sufficient. This approach works well when:

- You have a small number of forecast targets
- Updates happen at regular intervals (e.g., hourly)
- Your infrastructure already has job scheduling capabilities

**Example using cron:**

.. code-block:: python

   # forecast_job.py
   from datetime import timedelta
   from openstef_models.workflows import EnsembleForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset
   from my_app.data import load_training_data, save_forecasts
   from my_app.storage import ProductionModelStorage
   
   def run_forecast():
       # Load data from your data source
       dataset = load_training_data(
           start=pd.Timestamp.now() - timedelta(days=90),
           end=pd.Timestamp.now()
       )
       
       # Initialize workflow with production storage
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id="grid_segment_123",
           storage=ProductionModelStorage(),
           fallback_config=my_config
       )
       
       # Generate forecasts
       forecasts = workflow.predict(dataset)
       
       # Save to your data sink
       save_forecasts(forecasts)
   
   if __name__ == "__main__":
       run_forecast()

Schedule this script with cron:

.. code-block:: bash

   # Run forecast every hour at 15 minutes past
   15 * * * * /usr/bin/python3 /opt/forecasting/forecast_job.py >> /var/log/forecast.log 2>&1

Orchestration Platforms
^^^^^^^^^^^^^^^^^^^^^^^

For complex workflows with multiple dependencies, orchestration platforms like Apache Airflow, Prefect, or Dagster provide better control:

**Example Airflow DAG:**

.. code-block:: python

   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from datetime import datetime, timedelta
   from openstef_models.workflows import EnsembleForecastingWorkflow
   
   def train_model(target_id: str, **context):
       """Train model for a specific target."""
       dataset = load_data_for_target(target_id)
       
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id=target_id,
           storage=storage,
           fallback_config=config
       )
       
       workflow.fit(dataset)
       context['ti'].xcom_push(key='model_trained', value=True)
   
   def generate_forecast(target_id: str, **context):
       """Generate forecast using trained model."""
       dataset = load_recent_data(target_id)
       
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id=target_id,
           storage=storage
       )
       
       forecasts = workflow.predict(dataset)
       save_forecasts(target_id, forecasts)
   
   with DAG(
       'openstef_forecasting',
       default_args={
           'owner': 'data-team',
           'retries': 2,
           'retry_delay': timedelta(minutes=5),
       },
       schedule_interval='0 * * * *',  # Hourly
       start_date=datetime(2025, 1, 1),
       catchup=False,
   ) as dag:
       
       targets = ['grid_segment_123', 'grid_segment_456']
       
       for target in targets:
           train = PythonOperator(
               task_id=f'train_{target}',
               python_callable=train_model,
               op_kwargs={'target_id': target},
           )
           
           forecast = PythonOperator(
               task_id=f'forecast_{target}',
               python_callable=generate_forecast,
               op_kwargs={'target_id': target},
           )
           
           train >> forecast

Containerization
----------------

Containerizing OpenSTEF applications ensures consistent environments across development and production.

Docker Configuration
^^^^^^^^^^^^^^^^^^^^

**Example Dockerfile:**

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       && rm -rf /var/lib/apt/lists/*
   
   # Set working directory
   WORKDIR /app
   
   # Copy requirements
   COPY requirements.txt .
   
   # Install Python dependencies
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY . .
   
   # Set environment variables
   ENV PYTHONUNBUFFERED=1
   ENV OPENSTEF_LOG_LEVEL=INFO
   
   # Run the application
   CMD ["python", "forecast_job.py"]

**requirements.txt:**

.. code-block:: text

   openstef-models>=4.0.0
   openstef-beam>=4.0.0
   pandas>=2.0.0
   # Add your data connectors
   sqlalchemy>=2.0.0
   psycopg2-binary>=2.9.0

Build and run:

.. code-block:: bash

   docker build -t openstef-forecaster:latest .
   docker run -e DATABASE_URL=postgresql://user:pass@host/db openstef-forecaster:latest

Kubernetes Deployment
^^^^^^^^^^^^^^^^^^^^^

For scalable, resilient deployments:

**Example Kubernetes CronJob:**

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
     namespace: forecasting
   spec:
     schedule: "15 * * * *"  # Every hour at :15
     concurrencyPolicy: Forbid
     successfulJobsHistoryLimit: 3
     failedJobsHistoryLimit: 3
     jobTemplate:
       spec:
         template:
           spec:
             restartPolicy: OnFailure
             containers:
             - name: forecaster
               image: myregistry/openstef-forecaster:latest
               env:
               - name: DATABASE_URL
                 valueFrom:
                   secretKeyRef:
                     name: db-credentials
                     key: url
               - name: OPENSTEF_LOG_LEVEL
                 value: "INFO"
               resources:
                 requests:
                   memory: "2Gi"
                   cpu: "1000m"
                 limits:
                   memory: "4Gi"
                   cpu: "2000m"

Cloud Deployment
----------------

AWS Deployment
^^^^^^^^^^^^^^

**Using AWS Batch for scheduled forecasting:**

.. code-block:: python

   # Deploy as a container on AWS Batch
   # Job definition handles resource allocation
   # CloudWatch Events trigger on schedule
   
   import boto3
   from openstef_models.workflows import EnsembleForecastingWorkflow
   
   def lambda_trigger_forecast(event, context):
       """Lambda function to trigger Batch job."""
       batch = boto3.client('batch')
       
       response = batch.submit_job(
           jobName='openstef-forecast',
           jobQueue='forecasting-queue',
           jobDefinition='openstef-forecaster:1',
           containerOverrides={
               'environment': [
                   {'name': 'TARGET_ID', 'value': event['target_id']},
               ]
           }
       )
       
       return {'jobId': response['jobId']}

**Using S3 for model storage:**

See the :doc:`data_integration` guide for S3 integration patterns.

Azure Deployment
^^^^^^^^^^^^^^^^

**Using Azure Container Instances:**

.. code-block:: bash

   # Deploy container to Azure
   az container create \
     --resource-group forecasting-rg \
     --name openstef-forecaster \
     --image myregistry.azurecr.io/openstef-forecaster:latest \
     --cpu 2 \
     --memory 4 \
     --environment-variables \
       DATABASE_URL=$DB_URL \
       OPENSTEF_LOG_LEVEL=INFO \
     --restart-policy OnFailure

**Using Azure Functions for serverless:**

.. code-block:: python

   import azure.functions as func
   from openstef_models.workflows import EnsembleForecastingWorkflow
   
   def main(mytimer: func.TimerRequest) -> None:
       """Azure Function triggered by timer."""
       if mytimer.past_due:
           logging.info('Timer is past due')
       
       # Run forecasting workflow
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id="production_model",
           storage=azure_storage
       )
       
       forecasts = workflow.predict(dataset)
       save_to_azure_storage(forecasts)

Monitoring and Health Checks
-----------------------------

Production deployments require monitoring to ensure reliability and detect issues early.

Health Check Endpoint
^^^^^^^^^^^^^^^^^^^^^

If running as a service, implement health checks:

.. code-block:: python

   from flask import Flask, jsonify
   from datetime import datetime, timedelta
   
   app = Flask(__name__)
   
   @app.route('/health')
   def health_check():
       """Basic health check endpoint."""
       try:
           # Check model storage accessibility
           storage.has_model("test_model")
           
           # Check data source connectivity
           test_data = load_recent_data(limit=1)
           
           return jsonify({
               'status': 'healthy',
               'timestamp': datetime.now().isoformat()
           }), 200
       except Exception as e:
           return jsonify({
               'status': 'unhealthy',
               'error': str(e),
               'timestamp': datetime.now().isoformat()
           }), 503
   
   @app.route('/ready')
   def readiness_check():
       """Check if service is ready to handle requests."""
       try:
           # Verify model is loaded
           workflow = EnsembleForecastingWorkflow.from_storage(
               model_id="production_model",
               storage=storage
           )
           
           return jsonify({'status': 'ready'}), 200
       except Exception as e:
           return jsonify({'status': 'not_ready', 'error': str(e)}), 503

Logging Configuration
^^^^^^^^^^^^^^^^^^^^^

Configure structured logging for production monitoring. See the :doc:`logging` guide for detailed configuration options.

.. code-block:: python

   import logging
   import json
   
   class JSONFormatter(logging.Formatter):
       """Format logs as JSON for structured logging."""
       
       def format(self, record):
           log_data = {
               'timestamp': self.formatTime(record),
               'level': record.levelname,
               'message': record.getMessage(),
               'module': record.module,
           }
           
           if hasattr(record, 'target_id'):
               log_data['target_id'] = record.target_id
           
           if record.exc_info:
               log_data['exception'] = self.formatException(record.exc_info)
           
           return json.dumps(log_data)
   
   # Configure for production
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.getLogger('openstef').addHandler(handler)
   logging.getLogger('openstef').setLevel(logging.INFO)

Metrics Collection
^^^^^^^^^^^^^^^^^^

Track operational metrics for monitoring:

.. code-block:: python

   from prometheus_client import Counter, Histogram, Gauge
   import time
   
   # Define metrics
   forecast_requests = Counter(
       'openstef_forecast_requests_total',
       'Total forecast requests',
       ['target_id', 'status']
   )
   
   forecast_duration = Histogram(
       'openstef_forecast_duration_seconds',
       'Time spent generating forecasts',
       ['target_id']
   )
   
   model_age = Gauge(
       'openstef_model_age_hours',
       'Hours since model was last trained',
       ['target_id']
   )
   
   def monitored_forecast(target_id: str):
       """Generate forecast with monitoring."""
       start_time = time.time()
       
       try:
           workflow = EnsembleForecastingWorkflow.from_storage(
               model_id=target_id,
               storage=storage
           )
           
           forecasts = workflow.predict(dataset)
           
           forecast_requests.labels(target_id=target_id, status='success').inc()
           forecast_duration.labels(target_id=target_id).observe(
               time.time() - start_time
           )
           
           return forecasts
           
       except Exception as e:
           forecast_requests.labels(target_id=target_id, status='error').inc()
           raise

Configuration Management
------------------------

Separate configuration from code for different environments:

.. code-block:: python

   # config.py
   from pydantic import BaseSettings
   from datetime import timedelta
   
   class DeploymentConfig(BaseSettings):
       """Environment-specific configuration."""
       
       # Data sources
       database_url: str
       s3_bucket: str | None = None
       
       # Model storage
       model_storage_path: str = "/models"
       
       # Forecasting parameters
       training_history: timedelta = timedelta(days=90)
       prediction_horizon: timedelta = timedelta(hours=48)
       
       # Operational settings
       log_level: str = "INFO"
       max_retries: int = 3
       timeout_seconds: int = 300
       
       class Config:
           env_file = ".env"
           env_prefix = "OPENSTEF_"
   
   # Load configuration
   config = DeploymentConfig()

**Example .env file:**

.. code-block:: bash

   OPENSTEF_DATABASE_URL=postgresql://user:pass@localhost/forecasting
   OPENSTEF_S3_BUCKET=my-forecast-bucket
   OPENSTEF_LOG_LEVEL=INFO
   OPENSTEF_MAX_RETRIES=3

Performance Considerations
--------------------------

Resource Allocation
^^^^^^^^^^^^^^^^^^^

OpenSTEF workflows can be memory and CPU intensive:

- **Training**: Requires more memory (2-4 GB typical) and CPU for model fitting
- **Prediction**: Lighter weight (1-2 GB typical), faster execution
- **Ensemble models**: Higher resource usage than single models

Allocate resources based on your workload:

.. code-block:: yaml

   # Kubernetes resource allocation example
   resources:
     requests:
       memory: "2Gi"
       cpu: "1000m"
     limits:
       memory: "4Gi"
       cpu: "2000m"

Parallel Processing
^^^^^^^^^^^^^^^^^^^

For multiple forecast targets, parallelize execution:

.. code-block:: python

   from concurrent.futures import ThreadPoolExecutor, as_completed
   
   def forecast_target(target_id: str):
       """Generate forecast for single target."""
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id=target_id,
           storage=storage
       )
       return target_id, workflow.predict(dataset)
   
   def forecast_all_targets(target_ids: list[str], max_workers: int = 4):
       """Generate forecasts for multiple targets in parallel."""
       results = {}
       
       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           futures = {
               executor.submit(forecast_target, tid): tid 
               for tid in target_ids
           }
           
           for future in as_completed(futures):
               target_id, forecast = future.result()
               results[target_id] = forecast
       
       return results

.. note::

   Adjust ``max_workers`` based on available CPU and memory resources. Monitor resource usage to find optimal parallelism for your infrastructure.

See Also
--------

- :doc:`data_integration` - Connecting to data sources and sinks
- :doc:`logging` - Detailed logging configuration for production
- :doc:`use_cases` - Common forecasting patterns and workflows