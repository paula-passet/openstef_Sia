Production Deployment
=====================

This guide covers deployment patterns for running OpenSTEF forecasting pipelines in production environments. OpenSTEF is a Python library that you integrate into your own applications, so deployment approaches range from simple scheduled scripts to sophisticated orchestration platforms.

Deployment Approaches
---------------------

Scheduled Jobs
^^^^^^^^^^^^^^

The simplest deployment pattern runs forecasting workflows as scheduled jobs using cron, systemd timers, or task schedulers. This works well for periodic forecasting tasks with predictable schedules.

A basic scheduled script might look like:

.. code-block:: python

   #!/usr/bin/env python3
   from datetime import timedelta
   from openstef_models.workflows import EnsembleForecastingWorkflow
   from openstef_core.data_classes import LeadTime, Quantile as Q
   from my_project.data import load_training_data
   from my_project.storage import get_model_storage, get_forecast_storage
   
   def run_daily_forecast():
       """Daily forecasting job for production predictions."""
       # Load data from your data source
       dataset = load_training_data(days=90)
       
       # Initialize workflow with storage
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id="production_forecast_v1",
           storage=get_model_storage(),
           horizons=[LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       )
       
       # Train if needed (workflow handles model reuse logic)
       workflow.fit(dataset)
       
       # Generate predictions
       forecasts = workflow.predict(dataset)
       
       # Save results to your storage system
       get_forecast_storage().save(forecasts)
   
   if __name__ == "__main__":
       run_daily_forecast()

Schedule this with cron:

.. code-block:: bash

   # Run daily at 6 AM
   0 6 * * * /opt/openstef/venv/bin/python /opt/openstef/scripts/daily_forecast.py

For systemd, create a timer unit:

.. code-block:: ini

   [Unit]
   Description=OpenSTEF Daily Forecast
   
   [Timer]
   OnCalendar=daily
   OnCalendar=06:00
   Persistent=true
   
   [Install]
   WantedBy=timers.target

Workflow Orchestration
^^^^^^^^^^^^^^^^^^^^^^

For complex forecasting pipelines with multiple dependencies, use orchestration platforms like Apache Airflow, Prefect, or Dagster. These provide dependency management, retry logic, monitoring, and scheduling.

Example Airflow DAG:

.. code-block:: python

   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from openstef_models.workflows import EnsembleForecastingWorkflow
   from openstef_core.data_classes import LeadTime, Quantile as Q
   
   def fetch_training_data(**context):
       """Fetch and validate training data."""
       from my_project.data import load_training_data
       dataset = load_training_data(days=90)
       # Push to XCom for downstream tasks
       context['ti'].xcom_push(key='dataset', value=dataset.to_dict())
   
   def train_model(**context):
       """Train forecasting model."""
       from my_project.storage import get_model_storage
       dataset_dict = context['ti'].xcom_pull(key='dataset')
       dataset = TimeSeriesDataset.from_dict(dataset_dict)
       
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id=f"forecast_{context['ds_nodash']}",
           storage=get_model_storage(),
           horizons=[LeadTime.from_string("PT24H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       )
       workflow.fit(dataset)
       context['ti'].xcom_push(key='model_id', value=workflow.model_id)
   
   def generate_forecasts(**context):
       """Generate and save forecasts."""
       from my_project.storage import get_model_storage, get_forecast_storage
       model_id = context['ti'].xcom_pull(key='model_id')
       dataset_dict = context['ti'].xcom_pull(key='dataset')
       dataset = TimeSeriesDataset.from_dict(dataset_dict)
       
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id=model_id,
           storage=get_model_storage(),
       )
       forecasts = workflow.predict(dataset)
       get_forecast_storage().save(forecasts)
   
   with DAG(
       'openstef_daily_forecast',
       default_args={
           'owner': 'data-team',
           'retries': 2,
           'retry_delay': timedelta(minutes=5),
       },
       description='Daily energy forecasting pipeline',
       schedule_interval='0 6 * * *',
       start_date=datetime(2025, 1, 1),
       catchup=False,
   ) as dag:
       
       fetch_data = PythonOperator(
           task_id='fetch_training_data',
           python_callable=fetch_training_data,
       )
       
       train = PythonOperator(
           task_id='train_model',
           python_callable=train_model,
       )
       
       predict = PythonOperator(
           task_id='generate_forecasts',
           python_callable=generate_forecasts,
       )
       
       fetch_data >> train >> predict

Containerization
----------------

Docker containers provide consistent environments across development and production. Here's a production-ready Dockerfile:

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       && rm -rf /var/lib/apt/lists/*
   
   # Create non-root user
   RUN useradd -m -u 1000 openstef
   WORKDIR /app
   
   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY --chown=openstef:openstef . .
   
   # Switch to non-root user
   USER openstef
   
   # Run forecasting job
   CMD ["python", "scripts/run_forecast.py"]

Example ``requirements.txt``:

.. code-block:: text

   openstef-models>=4.0.0
   openstef-beam>=4.0.0
   pandas>=2.0.0
   boto3>=1.28.0  # If using S3 storage
   psycopg2-binary>=2.9.0  # If using PostgreSQL

Build and run:

.. code-block:: bash

   docker build -t openstef-forecast:latest .
   docker run --env-file .env openstef-forecast:latest

For Kubernetes deployments, create a CronJob:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-daily-forecast
   spec:
     schedule: "0 6 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: forecast
               image: openstef-forecast:latest
               env:
               - name: MODEL_STORAGE_PATH
                 value: "s3://my-bucket/models"
               - name: FORECAST_OUTPUT_PATH
                 value: "s3://my-bucket/forecasts"
               envFrom:
               - secretRef:
                   name: openstef-secrets
               resources:
                 requests:
                   memory: "4Gi"
                   cpu: "2"
                 limits:
                   memory: "8Gi"
                   cpu: "4"
             restartPolicy: OnFailure

Cloud Deployment
----------------

AWS
^^^

Deploy on AWS using ECS Fargate for serverless container execution:

.. code-block:: python

   # Configuration using environment variables
   import os
   from openstef_models.workflows import EnsembleForecastingWorkflow
   from openstef_core.storage import S3Storage
   
   # Read configuration from environment
   MODEL_BUCKET = os.environ["MODEL_BUCKET"]
   FORECAST_BUCKET = os.environ["FORECAST_BUCKET"]
   AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")
   
   # Initialize S3-backed storage
   model_storage = S3Storage(
       bucket=MODEL_BUCKET,
       prefix="models/",
       region=AWS_REGION,
   )
   
   forecast_storage = S3Storage(
       bucket=FORECAST_BUCKET,
       prefix="forecasts/",
       region=AWS_REGION,
   )

Use AWS EventBridge to trigger ECS tasks on a schedule, or Lambda for lightweight forecasting jobs.

Azure
^^^^^

Deploy using Azure Container Instances or Azure Batch:

.. code-block:: python

   import os
   from azure.storage.blob import BlobServiceClient
   from openstef_core.storage import AzureBlobStorage
   
   # Azure Blob Storage for models and forecasts
   connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
   
   model_storage = AzureBlobStorage(
       connection_string=connection_string,
       container_name="openstef-models",
   )

Schedule with Azure Logic Apps or Azure Functions with timer triggers.

GCP
^^^

Deploy on Google Cloud Run or Cloud Functions:

.. code-block:: python

   import os
   from google.cloud import storage
   from openstef_core.storage import GCSStorage
   
   # Google Cloud Storage for artifacts
   PROJECT_ID = os.environ["GCP_PROJECT_ID"]
   MODEL_BUCKET = os.environ["MODEL_BUCKET"]
   
   model_storage = GCSStorage(
       project_id=PROJECT_ID,
       bucket_name=MODEL_BUCKET,
       prefix="models/",
   )

Use Cloud Scheduler to trigger Cloud Run jobs on a schedule.

Monitoring and Health Checks
-----------------------------

Production deployments need monitoring to detect failures and performance degradation.

Health Check Endpoint
^^^^^^^^^^^^^^^^^^^^^

If running as a service, implement health checks:

.. code-block:: python

   from datetime import datetime, timedelta
   from flask import Flask, jsonify
   from openstef_models.workflows import EnsembleForecastingWorkflow
   
   app = Flask(__name__)
   
   @app.route('/health')
   def health_check():
       """Basic health check endpoint."""
       return jsonify({
           "status": "healthy",
           "timestamp": datetime.utcnow().isoformat(),
       })
   
   @app.route('/health/model')
   def model_health():
       """Check if model is available and recent."""
       try:
           workflow = EnsembleForecastingWorkflow.from_storage(
               model_id="production_forecast_v1",
               storage=get_model_storage(),
           )
           # Check model age
           model_age = datetime.utcnow() - workflow.last_trained
           is_stale = model_age > timedelta(days=7)
           
           return jsonify({
               "status": "warning" if is_stale else "healthy",
               "model_age_hours": model_age.total_seconds() / 3600,
               "last_trained": workflow.last_trained.isoformat(),
           })
       except Exception as e:
           return jsonify({
               "status": "unhealthy",
               "error": str(e),
           }), 503

Logging and Metrics
^^^^^^^^^^^^^^^^^^^

Configure structured logging for production monitoring. See the :doc:`logging` page for detailed configuration.

Export metrics for monitoring systems:

.. code-block:: python

   from prometheus_client import Counter, Histogram, Gauge, start_http_server
   import time
   
   # Define metrics
   forecast_runs = Counter('openstef_forecast_runs_total', 'Total forecast runs')
   forecast_duration = Histogram('openstef_forecast_duration_seconds', 'Forecast duration')
   forecast_errors = Counter('openstef_forecast_errors_total', 'Total forecast errors')
   model_age = Gauge('openstef_model_age_hours', 'Age of current model in hours')
   
   def run_monitored_forecast():
       """Run forecast with metrics collection."""
       forecast_runs.inc()
       start_time = time.time()
       
       try:
           workflow = EnsembleForecastingWorkflow.from_storage(
               model_id="production_forecast_v1",
               storage=get_model_storage(),
           )
           
           # Update model age metric
           age_hours = (datetime.utcnow() - workflow.last_trained).total_seconds() / 3600
           model_age.set(age_hours)
           
           # Generate forecast
           dataset = load_training_data()
           forecasts = workflow.predict(dataset)
           
           # Record duration
           duration = time.time() - start_time
           forecast_duration.observe(duration)
           
           return forecasts
           
       except Exception as e:
           forecast_errors.inc()
           raise
   
   if __name__ == "__main__":
       # Start Prometheus metrics server
       start_http_server(8000)
       
       # Run forecast
       run_monitored_forecast()

Alerting
^^^^^^^^

Set up alerts for critical conditions:

- Forecast job failures
- Model staleness (not retrained in X days)
- Prediction latency exceeding thresholds
- Data quality issues detected by validation checks

Example alert configuration for Prometheus Alertmanager:

.. code-block:: yaml

   groups:
   - name: openstef_alerts
     interval: 5m
     rules:
     - alert: ForecastJobFailing
       expr: rate(openstef_forecast_errors_total[1h]) > 0.1
       for: 15m
       annotations:
         summary: "OpenSTEF forecast job failing"
         description: "Forecast error rate is {{ value }} errors/sec"
     
     - alert: ModelStale
       expr: openstef_model_age_hours > 168  # 7 days
       for: 1h
       annotations:
         summary: "OpenSTEF model is stale"
         description: "Model has not been retrained in {{ value }} hours"

Configuration Management
------------------------

Manage deployment configuration separately from code:

.. code-block:: python

   from pydantic import BaseModel, Field
   from openstef_core.data_classes import LeadTime, Quantile as Q
   import yaml
   
   class DeploymentConfig(BaseModel):
       """Production deployment configuration."""
       model_id: str = Field(..., description="Unique model identifier")
       horizons: list[str] = Field(default=["PT24H", "PT48H"])
       quantiles: list[float] = Field(default=[0.1, 0.5, 0.9])
       training_days: int = Field(default=90)
       model_storage_path: str = Field(...)
       forecast_output_path: str = Field(...)
       enable_monitoring: bool = Field(default=True)
       
       def get_horizons(self) -> list[LeadTime]:
           return [LeadTime.from_string(h) for h in self.horizons]
       
       def get_quantiles(self) -> list[Quantile]:
           return [Q(q) for q in self.quantiles]
   
   # Load from YAML
   with open("config/production.yaml") as f:
       config = DeploymentConfig(**yaml.safe_load(f))

Example ``production.yaml``:

.. code-block:: yaml

   model_id: "production_forecast_v1"
   horizons:
     - "PT24H"
     - "PT48H"
   quantiles: [0.1, 0.5, 0.9]
   training_days: 90
   model_storage_path: "s3://my-bucket/models"
   forecast_output_path: "s3://my-bucket/forecasts"
   enable_monitoring: true

See Also
--------

- :doc:`data_integration` - Connecting to data sources like S3, Databricks, and InfluxDB
- :doc:`logging` - Logging configuration and best practices for production
- :doc:`use_cases` - Common forecasting use cases and patterns
