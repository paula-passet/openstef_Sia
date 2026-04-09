Production Deployment
======================

OpenSTEF is a Python library designed to integrate into your existing infrastructure. This page covers practical deployment patterns from simple scheduled jobs to full orchestration platforms, along with containerization, cloud deployment, and monitoring considerations.

Deployment Approaches
---------------------

OpenSTEF workflows can be deployed using several patterns depending on your infrastructure and operational requirements.

Simple Scheduled Jobs
^^^^^^^^^^^^^^^^^^^^^^

For straightforward use cases, a cron job or system scheduler can trigger forecasting workflows at regular intervals:

.. code-block:: python

   # forecast_job.py
   from datetime import timedelta
   from openstef_models.workflows import EnsembleForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from my_app.storage import get_model_storage, get_data_loader
   
   def run_forecast():
       """Execute forecasting workflow and save results."""
       # Load configuration and data
       data_loader = get_data_loader()
       dataset = data_loader.load_recent_data(days=90)
       
       # Initialize workflow with storage
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id="grid_node_123",
           storage=get_model_storage(),
           horizons=[LeadTime.from_string("PT48H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           sample_interval=timedelta(minutes=15),
       )
       
       # Train if needed, then predict
       if workflow.should_retrain(dataset):
           workflow.fit(dataset)
       
       forecasts = workflow.predict(dataset)
       
       # Save forecasts to your database
       data_loader.save_forecasts(forecasts)
   
   if __name__ == "__main__":
       run_forecast()

Schedule this script with cron:

.. code-block:: bash

   # Run every 15 minutes
   */15 * * * * /opt/venv/bin/python /opt/forecasting/forecast_job.py >> /var/log/forecast.log 2>&1

This approach works well for:

- Single prediction targets or small numbers of forecasts
- Environments where existing job schedulers are available
- Teams familiar with traditional operations patterns

Containerization
----------------

Docker containers provide reproducible environments and simplify deployment across different platforms.

Basic Dockerfile
^^^^^^^^^^^^^^^^

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       g++ \
       && rm -rf /var/lib/apt/lists/*
   
   # Create application directory
   WORKDIR /app
   
   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY forecast_job.py .
   COPY config/ ./config/
   
   # Run as non-root user
   RUN useradd -m forecaster
   USER forecaster
   
   CMD ["python", "forecast_job.py"]

Example ``requirements.txt``:

.. code-block:: text

   openstef-models>=4.0.0
   openstef-beam>=4.0.0
   pandas>=2.0.0
   # Add your data source connectors
   boto3  # For AWS S3
   # influxdb-client  # For InfluxDB
   # databricks-sql-connector  # For Databricks

Build and run:

.. code-block:: bash

   docker build -t my-forecast-service .
   docker run --env-file .env my-forecast-service

Multi-Stage Build for Production
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Optimize image size with multi-stage builds:

.. code-block:: dockerfile

   # Build stage
   FROM python:3.11-slim as builder
   
   WORKDIR /build
   COPY requirements.txt .
   
   RUN pip install --user --no-cache-dir -r requirements.txt
   
   # Runtime stage
   FROM python:3.11-slim
   
   RUN apt-get update && apt-get install -y \
       libgomp1 \
       && rm -rf /var/lib/apt/lists/*
   
   WORKDIR /app
   
   # Copy installed packages from builder
   COPY --from=builder /root/.local /root/.local
   ENV PATH=/root/.local/bin:$PATH
   
   COPY forecast_job.py .
   COPY config/ ./config/
   
   RUN useradd -m forecaster && chown -R forecaster:forecaster /app
   USER forecaster
   
   CMD ["python", "forecast_job.py"]

Orchestration Platforms
------------------------

For production systems managing multiple forecasts, orchestration platforms provide scheduling, monitoring, and dependency management.

Apache Airflow
^^^^^^^^^^^^^^

Airflow DAGs can orchestrate complex forecasting pipelines:

.. code-block:: python

   # dags/forecasting_dag.py
   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from openstef_models.workflows import EnsembleForecastingWorkflow
   from openstef_core.types import LeadTime, Q
   
   def forecast_task(model_id: str, **context):
       """Airflow task for single forecast."""
       from my_app.storage import get_model_storage, get_data_loader
       
       data_loader = get_data_loader()
       dataset = data_loader.load_recent_data(days=90)
       
       workflow = EnsembleForecastingWorkflow.from_storage(
           model_id=model_id,
           storage=get_model_storage(),
           horizons=[LeadTime.from_string("PT48H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           sample_interval=timedelta(minutes=15),
       )
       
       if workflow.should_retrain(dataset):
           workflow.fit(dataset)
       
       forecasts = workflow.predict(dataset)
       data_loader.save_forecasts(forecasts)
   
   default_args = {
       'owner': 'data-team',
       'depends_on_past': False,
       'start_date': datetime(2025, 1, 1),
       'retries': 2,
       'retry_delay': timedelta(minutes=5),
   }
   
   with DAG(
       'energy_forecasting',
       default_args=default_args,
       schedule_interval='*/15 * * * *',  # Every 15 minutes
       catchup=False,
   ) as dag:
       
       # Create tasks for multiple prediction targets
       for model_id in ['grid_node_123', 'grid_node_456', 'grid_node_789']:
           PythonOperator(
               task_id=f'forecast_{model_id}',
               python_callable=forecast_task,
               op_kwargs={'model_id': model_id},
           )

Kubernetes
^^^^^^^^^^

Deploy forecasting services on Kubernetes with CronJobs:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: energy-forecast
     namespace: forecasting
   spec:
     schedule: "*/15 * * * *"
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
               image: my-registry/forecast-service:v1.2.3
               env:
               - name: MODEL_ID
                 value: "grid_node_123"
               - name: LOG_LEVEL
                 value: "INFO"
               envFrom:
               - secretRef:
                   name: forecast-secrets
               resources:
                 requests:
                   memory: "2Gi"
                   cpu: "1000m"
                 limits:
                   memory: "4Gi"
                   cpu: "2000m"

For parallel processing of multiple forecasts, use a Job with multiple pods:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: Job
   metadata:
     name: batch-forecast
   spec:
     parallelism: 10
     completions: 100
     template:
       spec:
         restartPolicy: Never
         containers:
         - name: forecaster
           image: my-registry/forecast-service:v1.2.3
           env:
           - name: TASK_INDEX
             valueFrom:
               fieldRef:
                 fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']

Cloud Deployment
----------------

OpenSTEF integrates with major cloud platforms through standard Python interfaces.

AWS Deployment
^^^^^^^^^^^^^^

Deploy using AWS Batch for scalable job processing:

.. code-block:: python

   # Use AWS Secrets Manager for credentials
   import boto3
   from botocore.exceptions import ClientError
   
   def get_secret(secret_name: str) -> dict:
       """Retrieve secrets from AWS Secrets Manager."""
       client = boto3.client('secretsmanager')
       try:
           response = client.get_secret_value(SecretId=secret_name)
           return json.loads(response['SecretString'])
       except ClientError as e:
           raise RuntimeError(f"Failed to retrieve secret: {e}")
   
   # Store models in S3
   from openstef_models.storage import FileSystemModelStorage
   import s3fs
   
   s3 = s3fs.S3FileSystem()
   storage = FileSystemModelStorage(
       base_path="s3://my-bucket/models",
       filesystem=s3,
   )

Azure Deployment
^^^^^^^^^^^^^^^^

Use Azure Container Instances or Azure Batch:

.. code-block:: python

   # Azure Key Vault for secrets
   from azure.identity import DefaultAzureCredential
   from azure.keyvault.secrets import SecretClient
   
   credential = DefaultAzureCredential()
   vault_url = "https://my-vault.vault.azure.net"
   client = SecretClient(vault_url=vault_url, credential=credential)
   
   db_password = client.get_secret("db-password").value
   
   # Store models in Azure Blob Storage
   from openstef_models.storage import FileSystemModelStorage
   import adlfs
   
   fs = adlfs.AzureBlobFileSystem(account_name="mystorageaccount")
   storage = FileSystemModelStorage(
       base_path="az://models-container/forecasts",
       filesystem=fs,
   )

GCP Deployment
^^^^^^^^^^^^^^

Deploy with Cloud Run or Cloud Functions:

.. code-block:: python

   # GCP Secret Manager
   from google.cloud import secretmanager
   
   def get_secret(project_id: str, secret_id: str) -> str:
       """Access secret from GCP Secret Manager."""
       client = secretmanager.SecretManagerServiceClient()
       name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
       response = client.access_secret_version(request={"name": name})
       return response.payload.data.decode("UTF-8")
   
   # Store models in GCS
   from openstef_models.storage import FileSystemModelStorage
   import gcsfs
   
   fs = gcsfs.GCSFileSystem(project="my-project")
   storage = FileSystemModelStorage(
       base_path="gs://my-bucket/models",
       filesystem=fs,
   )

Monitoring and Health Checks
-----------------------------

Production deployments require monitoring to ensure forecasts are generated reliably and accurately.

Health Check Endpoint
^^^^^^^^^^^^^^^^^^^^^

If exposing forecasting as a service, implement health checks:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_models.workflows import EnsembleForecastingWorkflow
   
   class ForecastService:
       def __init__(self, workflow: EnsembleForecastingWorkflow):
           self.workflow = workflow
           self.last_prediction_time = None
           self.last_training_time = None
       
       def health_check(self) -> dict:
           """Return service health status."""
           now = datetime.now()
           
           # Check if predictions are recent
           prediction_healthy = (
               self.last_prediction_time is not None
               and (now - self.last_prediction_time) < timedelta(minutes=30)
           )
           
           # Check model age
           model_age_days = (
               (now - self.last_training_time).days
               if self.last_training_time
               else None
           )
           
           return {
               "status": "healthy" if prediction_healthy else "degraded",
               "last_prediction": self.last_prediction_time.isoformat() if self.last_prediction_time else None,
               "last_training": self.last_training_time.isoformat() if self.last_training_time else None,
               "model_age_days": model_age_days,
           }

Metrics Collection
^^^^^^^^^^^^^^^^^^

Track operational metrics for alerting and analysis:

.. code-block:: python

   import time
   import logging
   from prometheus_client import Counter, Histogram, Gauge
   
   # Define metrics
   predictions_total = Counter(
       'forecast_predictions_total',
       'Total number of predictions generated',
       ['model_id', 'status']
   )
   
   prediction_duration = Histogram(
       'forecast_prediction_duration_seconds',
       'Time spent generating predictions',
       ['model_id']
   )
   
   training_duration = Histogram(
       'forecast_training_duration_seconds',
       'Time spent training models',
       ['model_id']
   )
   
   model_age_days = Gauge(
       'forecast_model_age_days',
       'Age of the current model in days',
       ['model_id']
   )
   
   def run_monitored_forecast(model_id: str):
       """Execute forecast with metrics collection."""
       start_time = time.time()
       
       try:
           # Your forecasting logic here
           workflow = EnsembleForecastingWorkflow.from_storage(...)
           
           if workflow.should_retrain(dataset):
               train_start = time.time()
               workflow.fit(dataset)
               training_duration.labels(model_id=model_id).observe(
                   time.time() - train_start
               )
           
           forecasts = workflow.predict(dataset)
           
           prediction_duration.labels(model_id=model_id).observe(
               time.time() - start_time
           )
           predictions_total.labels(model_id=model_id, status='success').inc()
           
       except Exception as e:
           predictions_total.labels(model_id=model_id, status='failure').inc()
           logging.error(f"Forecast failed for {model_id}: {e}")
           raise

Logging Configuration
^^^^^^^^^^^^^^^^^^^^^

Configure structured logging for production environments. See :doc:`logging` for detailed logging configuration and best practices.

.. code-block:: python

   import logging
   import json
   
   class JSONFormatter(logging.Formatter):
       """Format logs as JSON for structured logging systems."""
       
       def format(self, record):
           log_data = {
               'timestamp': self.formatTime(record),
               'level': record.levelname,
               'message': record.getMessage(),
               'module': record.module,
           }
           
           if hasattr(record, 'model_id'):
               log_data['model_id'] = record.model_id
           
           if record.exc_info:
               log_data['exception'] = self.formatException(record.exc_info)
           
           return json.dumps(log_data)
   
   # Configure logging
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.getLogger('openstef').addHandler(handler)
   logging.getLogger('openstef').setLevel(logging.INFO)

Configuration Management
------------------------

Separate configuration from code for different environments:

.. code-block:: python

   # config.py
   from pydantic import BaseModel, Field
   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   
   class DeploymentConfig(BaseModel):
       """Configuration for production deployment."""
       
       model_id: str = Field(..., description="Unique model identifier")
       
       # Data configuration
       data_retention_days: int = Field(default=90)
       sample_interval: timedelta = Field(default=timedelta(minutes=15))
       
       # Forecast configuration
       horizons: list[LeadTime] = Field(
           default=[LeadTime.from_string("PT48H")]
       )
       quantiles: list[Q] = Field(default=[Q(0.1), Q(0.5), Q(0.9)])
       
       # Training configuration
       max_model_age_days: int = Field(default=7)
       min_training_samples: int = Field(default=1000)
       
       # Storage paths
       model_storage_path: str = Field(...)
       data_source_url: str = Field(...)
       
       @classmethod
       def from_env(cls):
           """Load configuration from environment variables."""
           import os
           return cls(
               model_id=os.getenv("MODEL_ID"),
               model_storage_path=os.getenv("MODEL_STORAGE_PATH"),
               data_source_url=os.getenv("DATA_SOURCE_URL"),
           )

Load configuration in your deployment:

.. code-block:: python

   # In your forecast job
   config = DeploymentConfig.from_env()
   
   workflow = EnsembleForecastingWorkflow.from_storage(
       model_id=config.model_id,
       storage=get_storage(config.model_storage_path),
       horizons=config.horizons,
       quantiles=config.quantiles,
       sample_interval=config.sample_interval,
   )

See Also
--------

- :doc:`data_integration` - Connect to data sources like S3, Databricks, and InfluxDB
- :doc:`logging` - Configure logging for production environments
- :doc:`use_cases` - Common OpenSTEF use cases and patterns