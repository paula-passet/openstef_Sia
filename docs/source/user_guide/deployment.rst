Production Deployment
=====================

This page covers deployment patterns for running OpenSTEF in production environments. OpenSTEF is a Python library, so deployment involves integrating it into your infrastructure using scheduled jobs, orchestration platforms, or custom applications. We'll explore different approaches from simple cron-based scheduling to full cloud orchestration, along with containerization, monitoring, and configuration management.

Deployment Approaches
---------------------

Simple Scheduled Jobs
^^^^^^^^^^^^^^^^^^^^^

For small-scale deployments or getting started, scheduled jobs using cron or systemd timers work well. Create a Python script that imports OpenSTEF and runs your forecasting workflow:

.. code-block:: python

   # forecast_job.py
   from datetime import timedelta
   from openstef_models.workflows import ForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.forecasters import XGBoostForecaster
   from openstef_models.model import ForecastingModel
   from openstef_core.types import LeadTime, Quantile as Q
   import pandas as pd
   
   def run_forecast():
       # Load your data (see data_integration page for details)
       data = load_data_from_source()
       
       dataset = TimeSeriesDataset(
           data=data,
           sample_interval=timedelta(minutes=15)
       )
       
       # Configure and run workflow
       model = ForecastingModel(
           forecaster=XGBoostForecaster(
               horizons=[LeadTime.from_string("PT24H")],
               quantiles=[Q(0.5), Q(0.1), Q(0.9)]
           )
       )
       
       workflow = ForecastingWorkflow(
           model=model,
           model_id="production_forecast"
       )
       
       # Train if needed
       workflow.fit(dataset)
       
       # Generate forecasts
       forecasts = workflow.predict(dataset)
       
       # Save results
       save_forecasts(forecasts)
   
   if __name__ == "__main__":
       run_forecast()

Schedule this with cron:

.. code-block:: bash

   # Run every hour at 5 minutes past
   5 * * * * /usr/bin/python3 /opt/forecasting/forecast_job.py >> /var/log/forecast.log 2>&1

This approach works for single-server deployments with straightforward scheduling needs. For production robustness, add error handling, retry logic, and alerting.

Workflow Orchestration
^^^^^^^^^^^^^^^^^^^^^^

For complex pipelines with dependencies, orchestration platforms like Apache Airflow, Prefect, or Dagster provide better control. Here's an Airflow DAG example:

.. code-block:: python

   # forecast_dag.py
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from datetime import datetime, timedelta
   
   def fetch_training_data(**context):
       """Fetch historical data for model training."""
       # Implementation depends on your data source
       data = fetch_from_database(
           start=context['execution_date'] - timedelta(days=90),
           end=context['execution_date']
       )
       return data
   
   def train_model(**context):
       """Train forecasting model with latest data."""
       from openstef_models.workflows import ForecastingWorkflow
       
       ti = context['ti']
       data = ti.xcom_pull(task_ids='fetch_training_data')
       
       # Configure and train
       workflow = ForecastingWorkflow.from_storage(
           model_id="production_model",
           storage=get_storage_backend()
       )
       workflow.fit(data)
       
   def generate_forecasts(**context):
       """Generate forecasts using trained model."""
       workflow = ForecastingWorkflow.from_storage(
           model_id="production_model",
           storage=get_storage_backend()
       )
       
       recent_data = fetch_recent_data()
       forecasts = workflow.predict(recent_data)
       
       publish_forecasts(forecasts)
   
   with DAG(
       'openstef_forecasting',
       default_args={
           'owner': 'data-team',
           'retries': 2,
           'retry_delay': timedelta(minutes=5),
       },
       description='Energy forecasting with OpenSTEF',
       schedule_interval='0 * * * *',  # Hourly
       start_date=datetime(2025, 1, 1),
       catchup=False,
   ) as dag:
       
       fetch_task = PythonOperator(
           task_id='fetch_training_data',
           python_callable=fetch_training_data,
       )
       
       train_task = PythonOperator(
           task_id='train_model',
           python_callable=train_model,
       )
       
       forecast_task = PythonOperator(
           task_id='generate_forecasts',
           python_callable=generate_forecasts,
       )
       
       fetch_task >> train_task >> forecast_task

Orchestration platforms handle scheduling, dependency management, retries, and monitoring through their UI.

Containerization
----------------

Docker containers provide consistent environments across development and production. Here's a production-ready Dockerfile:

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       g++ \
       && rm -rf /var/lib/apt/lists/*
   
   # Create application user
   RUN useradd -m -u 1000 forecast && \
       mkdir -p /app /data && \
       chown -R forecast:forecast /app /data
   
   WORKDIR /app
   
   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY --chown=forecast:forecast . .
   
   # Switch to non-root user
   USER forecast
   
   # Run the forecasting job
   CMD ["python", "forecast_job.py"]

Build and run:

.. code-block:: bash

   docker build -t openstef-forecast:latest .
   docker run -v /path/to/data:/data \
              -e DATABASE_URL=postgresql://... \
              openstef-forecast:latest

For multi-container deployments, use Docker Compose:

.. code-block:: yaml

   # docker-compose.yml
   version: '3.8'
   
   services:
     forecast:
       build: .
       volumes:
         - ./data:/data
         - ./models:/models
       environment:
         - DATABASE_URL=${DATABASE_URL}
         - MODEL_STORAGE_PATH=/models
         - LOG_LEVEL=INFO
       restart: unless-stopped
     
     scheduler:
       image: apache/airflow:2.7.0
       depends_on:
         - postgres
       volumes:
         - ./dags:/opt/airflow/dags
         - ./models:/models
       environment:
         - AIRFLOW__CORE__EXECUTOR=LocalExecutor
         - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://airflow:airflow@postgres/airflow
     
     postgres:
       image: postgres:15
       environment:
         - POSTGRES_USER=airflow
         - POSTGRES_PASSWORD=airflow
         - POSTGRES_DB=airflow
       volumes:
         - postgres-data:/var/lib/postgresql/data
   
   volumes:
     postgres-data:

Kubernetes Deployment
^^^^^^^^^^^^^^^^^^^^^

For large-scale production deployments, Kubernetes provides orchestration, scaling, and resilience. Create a CronJob for scheduled forecasting:

.. code-block:: yaml

   # forecast-cronjob.yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
     namespace: forecasting
   spec:
     schedule: "5 * * * *"  # Every hour at 5 minutes past
     concurrencyPolicy: Forbid
     successfulJobsHistoryLimit: 3
     failedJobsHistoryLimit: 3
     jobTemplate:
       spec:
         template:
           spec:
             restartPolicy: OnFailure
             containers:
             - name: forecast
               image: your-registry/openstef-forecast:v1.0.0
               resources:
                 requests:
                   memory: "2Gi"
                   cpu: "1000m"
                 limits:
                   memory: "4Gi"
                   cpu: "2000m"
               env:
               - name: DATABASE_URL
                 valueFrom:
                   secretKeyRef:
                     name: forecast-secrets
                     key: database-url
               - name: MODEL_STORAGE_PATH
                 value: "/models"
               volumeMounts:
               - name: model-storage
                 mountPath: /models
             volumes:
             - name: model-storage
               persistentVolumeClaim:
                 claimName: model-storage-pvc

Deploy with:

.. code-block:: bash

   kubectl apply -f forecast-cronjob.yaml

Cloud Deployment Options
-------------------------

AWS
^^^

Deploy OpenSTEF on AWS using several service combinations:

**ECS with EventBridge**: Run containerized forecasting jobs on ECS Fargate triggered by EventBridge schedules. Store models in S3 and use RDS for metadata.

**Lambda for lightweight forecasts**: For small models and quick predictions, package OpenSTEF in a Lambda function. Note the 15-minute timeout and memory limits.

**Batch for long-running jobs**: AWS Batch handles compute-intensive training jobs with automatic scaling.

Example ECS task definition:

.. code-block:: json

   {
     "family": "openstef-forecast",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "2048",
     "memory": "4096",
     "containerDefinitions": [
       {
         "name": "forecast",
         "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/openstef:latest",
         "environment": [
           {"name": "MODEL_STORAGE_BUCKET", "value": "my-models-bucket"},
           {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"}
         ],
         "secrets": [
           {
             "name": "DATABASE_URL",
             "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:db-url"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/openstef",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "forecast"
           }
         }
       }
     ]
   }

Azure
^^^^^

**Azure Container Instances**: Run scheduled forecasting jobs using Container Instances triggered by Logic Apps or Azure Functions.

**Azure Batch**: For parallel processing of multiple forecasts across different locations.

**AKS (Azure Kubernetes Service)**: Full Kubernetes deployment for complex orchestration needs.

Store models in Azure Blob Storage and use Azure Database for PostgreSQL for metadata.

GCP
^^^

**Cloud Run Jobs**: Serverless container execution for forecasting workloads with automatic scaling.

**GKE (Google Kubernetes Engine)**: Managed Kubernetes for production deployments.

**Cloud Scheduler + Cloud Functions**: Trigger forecasting jobs on schedule.

Use Google Cloud Storage for model artifacts and Cloud SQL for metadata.

Configuration Management
-------------------------

Externalize configuration using environment variables and configuration files:

.. code-block:: python

   # config.py
   import os
   from datetime import timedelta
   from pydantic import BaseModel, Field
   
   class DeploymentConfig(BaseModel):
       """Production deployment configuration."""
       
       # Data sources
       database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL"))
       s3_bucket: str = Field(default_factory=lambda: os.getenv("MODEL_STORAGE_BUCKET"))
       
       # Model configuration
       model_id: str = Field(default="production_model")
       forecast_horizons: list[str] = Field(default=["PT24H", "PT48H"])
       sample_interval: timedelta = Field(default=timedelta(minutes=15))
       
       # Training schedule
       retrain_interval_hours: int = Field(default=24)
       min_training_samples: int = Field(default=2000)
       
       # Performance
       n_jobs: int = Field(default_factory=lambda: int(os.getenv("N_JOBS", "-1")))
       
       # Monitoring
       enable_metrics: bool = Field(default=True)
       metrics_endpoint: str = Field(default_factory=lambda: os.getenv("METRICS_ENDPOINT"))
   
   def load_config() -> DeploymentConfig:
       """Load configuration from environment."""
       return DeploymentConfig()

Use this in your application:

.. code-block:: python

   from config import load_config
   
   config = load_config()
   
   workflow = ForecastingWorkflow(
       model=model,
       model_id=config.model_id
   )

Monitoring and Health Checks
-----------------------------

Production deployments need monitoring to track performance and detect issues. Implement health checks and metrics collection:

.. code-block:: python

   # monitoring.py
   from datetime import datetime
   import logging
   from typing import Any
   
   logger = logging.getLogger(__name__)
   
   class ForecastMonitor:
       """Monitor forecasting job execution and performance."""
       
       def __init__(self, metrics_backend=None):
           self.metrics_backend = metrics_backend
       
       def record_job_start(self, job_id: str):
           """Record job execution start."""
           logger.info(f"Job {job_id} started at {datetime.now()}")
           if self.metrics_backend:
               self.metrics_backend.increment("forecast_jobs_started")
       
       def record_job_success(self, job_id: str, duration_seconds: float):
           """Record successful job completion."""
           logger.info(f"Job {job_id} completed in {duration_seconds:.2f}s")
           if self.metrics_backend:
               self.metrics_backend.increment("forecast_jobs_completed")
               self.metrics_backend.histogram("forecast_job_duration", duration_seconds)
       
       def record_job_failure(self, job_id: str, error: Exception):
           """Record job failure."""
           logger.error(f"Job {job_id} failed: {error}", exc_info=True)
           if self.metrics_backend:
               self.metrics_backend.increment("forecast_jobs_failed")
       
       def record_forecast_metrics(self, metrics: dict[str, float]):
           """Record forecast quality metrics."""
           for metric_name, value in metrics.items():
               logger.info(f"Metric {metric_name}: {value:.4f}")
               if self.metrics_backend:
                   self.metrics_backend.gauge(f"forecast_{metric_name}", value)
   
   def health_check() -> dict[str, Any]:
       """Health check endpoint for load balancers."""
       try:
           # Check database connectivity
           check_database()
           
           # Check model storage access
           check_model_storage()
           
           # Check last successful forecast time
           last_forecast = get_last_forecast_time()
           
           return {
               "status": "healthy",
               "timestamp": datetime.now().isoformat(),
               "last_forecast": last_forecast.isoformat() if last_forecast else None
           }
       except Exception as e:
           logger.error(f"Health check failed: {e}")
           return {
               "status": "unhealthy",
               "error": str(e),
               "timestamp": datetime.now().isoformat()
           }

Integrate monitoring into your forecasting job:

.. code-block:: python

   import time
   from monitoring import ForecastMonitor
   
   monitor = ForecastMonitor(metrics_backend=prometheus_client)
   
   def run_forecast_with_monitoring():
       job_id = f"forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
       monitor.record_job_start(job_id)
       
       start_time = time.time()
       try:
           # Run forecasting workflow
           forecasts = workflow.predict(dataset)
           
           # Calculate and record quality metrics
           metrics = calculate_forecast_metrics(forecasts)
           monitor.record_forecast_metrics(metrics)
           
           duration = time.time() - start_time
           monitor.record_job_success(job_id, duration)
           
       except Exception as e:
           monitor.record_job_failure(job_id, e)
           raise

For detailed logging configuration, see the :doc:`logging` page.

Best Practices
--------------

**Model versioning**: Store model artifacts with version identifiers and metadata. Use the storage backend's versioning capabilities to track model lineage.

**Graceful degradation**: When model training fails, fall back to the last known good model rather than stopping forecasts entirely.

**Resource limits**: Set appropriate memory and CPU limits based on your data volume and model complexity. XGBoost and LightGBM models can be memory-intensive during training.

**Secrets management**: Never hardcode credentials. Use environment variables, secret managers (AWS Secrets Manager, Azure Key Vault, etc.), or Kubernetes secrets.

**Testing in staging**: Deploy to a staging environment first. Run backtests to validate model performance before promoting to production.

**Alerting**: Set up alerts for job failures, forecast quality degradation, and infrastructure issues. Monitor metrics like forecast accuracy, job duration, and error rates.

**Data validation**: Validate input data before training or prediction. OpenSTEF includes validation checks, but add domain-specific validation for your use case.

See Also
--------

- :doc:`data_integration` - Loading data from various sources
- :doc:`logging` - Logging configuration for production
- :doc:`use_cases` - Common forecasting scenarios