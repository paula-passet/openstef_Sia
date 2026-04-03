Production Deployment
=====================

This page covers practical patterns for deploying OpenSTEF in production environments. OpenSTEF is a Python library, not a standalone application, so deployment involves integrating it into your infrastructure through scheduled jobs, containerized services, or orchestration platforms.

Deployment approaches range from simple cron-based scripts to sophisticated orchestration with Kubernetes or Apache Airflow. Choose based on your operational requirements, existing infrastructure, and scale.

Deployment Patterns
-------------------

Simple Scheduled Jobs
^^^^^^^^^^^^^^^^^^^^^

For small-scale deployments or proof-of-concept work, scheduled Python scripts provide the simplest approach. Use system schedulers like cron or Windows Task Scheduler to run forecasting workflows at regular intervals.

.. code-block:: python

   # forecast_job.py
   from datetime import timedelta
   from openstef_models.workflows import ForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Q, LeadTime
   import pandas as pd
   
   def run_forecast():
       # Load your data (see data_integration page for details)
       data = load_data_from_source()
       
       dataset = TimeSeriesDataset(
           data=data,
           sample_interval=timedelta(minutes=15),
       )
       
       # Load or create workflow
       workflow = ForecastingWorkflow.from_storage(
           model_id="production_model",
           storage=your_storage_backend,
           fallback_config=your_config,
       )
       
       # Generate forecasts
       forecasts = workflow.predict(dataset)
       
       # Save results
       save_forecasts(forecasts)
   
   if __name__ == "__main__":
       run_forecast()

Schedule with cron for Unix systems:

.. code-block:: bash

   # Run every 15 minutes
   */15 * * * * /usr/bin/python3 /path/to/forecast_job.py >> /var/log/forecast.log 2>&1

This pattern works well for:

- Single prediction targets
- Low-frequency forecasts (hourly or less frequent)
- Development and testing environments
- Small teams without dedicated infrastructure

Limitations include no built-in retry logic, limited observability, and manual dependency management.

Containerized Deployment
^^^^^^^^^^^^^^^^^^^^^^^^

Docker containers provide reproducible environments and simplify deployment across different infrastructure. Package OpenSTEF with your application code and dependencies into a container image.

Example Dockerfile:

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   WORKDIR /app
   
   # Install uv for fast dependency resolution
   RUN pip install uv
   
   # Copy dependency files
   COPY pyproject.toml uv.lock ./
   
   # Install dependencies
   RUN uv sync --frozen --no-dev
   
   # Copy application code
   COPY . .
   
   # Run the forecasting job
   CMD ["uv", "run", "python", "forecast_job.py"]

Build and run:

.. code-block:: bash

   docker build -t openstef-forecaster:latest .
   docker run --env-file .env openstef-forecaster:latest

For production, use environment variables to configure data sources, storage backends, and model parameters:

.. code-block:: python

   import os
   from openstef_models.storage import FileSystemStorage
   
   # Configuration from environment
   MODEL_ID = os.getenv("MODEL_ID", "default_model")
   STORAGE_PATH = os.getenv("STORAGE_PATH", "/data/models")
   DATA_SOURCE = os.getenv("DATA_SOURCE")
   
   storage = FileSystemStorage(base_path=STORAGE_PATH)

Container orchestration platforms like Kubernetes can schedule these containers as CronJobs:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
   spec:
     schedule: "*/15 * * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: forecaster
               image: openstef-forecaster:latest
               env:
               - name: MODEL_ID
                 value: "production_model"
               - name: STORAGE_PATH
                 value: "/mnt/models"
               volumeMounts:
               - name: model-storage
                 mountPath: /mnt/models
             volumes:
             - name: model-storage
               persistentVolumeClaim:
                 claimName: model-storage-pvc
             restartPolicy: OnFailure

Workflow Orchestration
^^^^^^^^^^^^^^^^^^^^^^^

For complex deployments with multiple models, dependencies between tasks, or sophisticated retry logic, use workflow orchestration platforms like Apache Airflow, Prefect, or Dagster.

Example Airflow DAG:

.. code-block:: python

   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from openstef_models.workflows import ForecastingWorkflow
   
   def train_model(**context):
       """Train or update forecasting model."""
       workflow = ForecastingWorkflow.from_storage(
           model_id=context["params"]["model_id"],
           storage=storage_backend,
           fallback_config=config,
       )
       
       training_data = load_training_data()
       result = workflow.fit(training_data)
       
       # Push metrics to XCom for monitoring
       context["ti"].xcom_push(key="r2_score", value=result.metrics[Q(0.5)]["R2"])
   
   def generate_forecast(**context):
       """Generate forecasts for multiple horizons."""
       workflow = ForecastingWorkflow.from_storage(
           model_id=context["params"]["model_id"],
           storage=storage_backend,
       )
       
       recent_data = load_recent_data()
       forecasts = workflow.predict(recent_data)
       save_forecasts(forecasts)
   
   default_args = {
       "owner": "data-team",
       "depends_on_past": False,
       "email_on_failure": True,
       "email_on_retry": False,
       "retries": 3,
       "retry_delay": timedelta(minutes=5),
   }
   
   with DAG(
       "openstef_forecasting",
       default_args=default_args,
       description="Energy load forecasting with OpenSTEF",
       schedule_interval="*/15 * * * *",
       start_date=datetime(2024, 1, 1),
       catchup=False,
       tags=["forecasting", "energy"],
   ) as dag:
       
       train_task = PythonOperator(
           task_id="train_model",
           python_callable=train_model,
           params={"model_id": "production_model"},
           # Run daily at 2 AM
           schedule_interval="0 2 * * *",
       )
       
       forecast_task = PythonOperator(
           task_id="generate_forecast",
           python_callable=generate_forecast,
           params={"model_id": "production_model"},
       )
       
       train_task >> forecast_task

Orchestration platforms provide:

- Dependency management between tasks
- Automatic retries with backoff
- Centralized logging and monitoring
- Task parallelization for multiple models
- Historical run tracking

Cloud Platform Deployment
--------------------------

AWS Deployment
^^^^^^^^^^^^^^

Deploy OpenSTEF on AWS using services like Lambda for serverless execution, ECS for containerized workloads, or EC2 for traditional compute.

For scheduled forecasts with AWS Lambda:

.. code-block:: python

   # lambda_handler.py
   import json
   from openstef_models.workflows import ForecastingWorkflow
   from openstef_models.storage import S3Storage
   
   def lambda_handler(event, context):
       """AWS Lambda handler for forecasting."""
       model_id = event.get("model_id", "default_model")
       
       # Use S3 for model storage
       storage = S3Storage(bucket="my-openstef-models")
       
       workflow = ForecastingWorkflow.from_storage(
           model_id=model_id,
           storage=storage,
           fallback_config=config,
       )
       
       # Load data from S3, RDS, or other AWS services
       data = load_data_from_aws()
       forecasts = workflow.predict(data)
       
       # Save results to S3 or database
       save_to_s3(forecasts)
       
       return {
           "statusCode": 200,
           "body": json.dumps({"message": "Forecast completed"}),
       }

Use EventBridge to trigger Lambda on a schedule. For data integration with AWS services, see the :doc:`data_integration` page.

Azure Deployment
^^^^^^^^^^^^^^^^

Azure Functions provides serverless execution similar to AWS Lambda. For containerized deployments, use Azure Container Instances or Azure Kubernetes Service.

Example Azure Function:

.. code-block:: python

   # __init__.py
   import azure.functions as func
   from openstef_models.workflows import ForecastingWorkflow
   
   def main(mytimer: func.TimerRequest) -> None:
       """Azure Function triggered by timer."""
       workflow = ForecastingWorkflow.from_storage(
           model_id="production_model",
           storage=azure_storage_backend,
           fallback_config=config,
       )
       
       data = load_from_azure_blob()
       forecasts = workflow.predict(data)
       save_to_azure(forecasts)

Configure in `function.json`:

.. code-block:: json

   {
     "scriptFile": "__init__.py",
     "bindings": [
       {
         "name": "mytimer",
         "type": "timerTrigger",
         "direction": "in",
         "schedule": "0 */15 * * * *"
       }
     ]
   }

Google Cloud Platform
^^^^^^^^^^^^^^^^^^^^^

Use Cloud Functions for serverless deployment or Cloud Run for containerized applications. Cloud Scheduler triggers functions on a schedule.

.. code-block:: python

   # main.py
   from flask import Request
   from openstef_models.workflows import ForecastingWorkflow
   
   def forecast_endpoint(request: Request):
       """Cloud Function HTTP endpoint."""
       workflow = ForecastingWorkflow.from_storage(
           model_id="production_model",
           storage=gcs_storage,
           fallback_config=config,
       )
       
       data = load_from_bigquery()
       forecasts = workflow.predict(data)
       save_to_bigquery(forecasts)
       
       return {"status": "success"}

Monitoring and Health Checks
-----------------------------

Production deployments require monitoring to detect failures, track performance, and alert on issues.

Health Check Endpoints
^^^^^^^^^^^^^^^^^^^^^^

For containerized deployments, implement health check endpoints:

.. code-block:: python

   from flask import Flask, jsonify
   from datetime import datetime
   
   app = Flask(__name__)
   
   last_successful_run = None
   
   @app.route("/health")
   def health_check():
       """Basic liveness check."""
       return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})
   
   @app.route("/ready")
   def readiness_check():
       """Check if service can handle requests."""
       try:
           # Verify storage connectivity
           storage.ping()
           # Verify model is loaded
           workflow = ForecastingWorkflow.from_storage(
               model_id="production_model",
               storage=storage,
           )
           return jsonify({"status": "ready"})
       except Exception as e:
           return jsonify({"status": "not_ready", "error": str(e)}), 503
   
   @app.route("/metrics")
   def metrics():
       """Expose metrics for monitoring."""
       return jsonify({
           "last_successful_run": last_successful_run,
           "models_loaded": len(loaded_models),
       })

Logging Configuration
^^^^^^^^^^^^^^^^^^^^^

Configure structured logging for production observability. See the :doc:`logging` page for detailed configuration options.

.. code-block:: python

   import logging
   import json
   from datetime import datetime
   
   class StructuredLogger:
       """Structured logging for production monitoring."""
       
       def __init__(self, service_name: str):
           self.service_name = service_name
           self.logger = logging.getLogger(service_name)
       
       def log_forecast_run(self, model_id: str, duration: float, success: bool):
           """Log forecast execution metrics."""
           self.logger.info(
               json.dumps({
                   "service": self.service_name,
                   "event": "forecast_completed",
                   "model_id": model_id,
                   "duration_seconds": duration,
                   "success": success,
                   "timestamp": datetime.utcnow().isoformat(),
               })
           )

Metrics and Alerting
^^^^^^^^^^^^^^^^^^^^

Track key metrics to monitor forecasting performance and system health:

- **Execution metrics**: Run duration, success rate, error rate
- **Model metrics**: Forecast accuracy (R², MAE), model age, retraining frequency
- **Data metrics**: Data completeness, missing values, data freshness
- **System metrics**: CPU usage, memory consumption, storage utilization

Export metrics to monitoring systems like Prometheus:

.. code-block:: python

   from prometheus_client import Counter, Histogram, Gauge, start_http_server
   
   # Define metrics
   forecast_runs = Counter("forecast_runs_total", "Total forecast runs", ["model_id", "status"])
   forecast_duration = Histogram("forecast_duration_seconds", "Forecast execution time", ["model_id"])
   model_age = Gauge("model_age_days", "Days since model was trained", ["model_id"])
   
   def run_forecast_with_metrics(model_id: str):
       """Run forecast with metric collection."""
       start_time = time.time()
       try:
           workflow = ForecastingWorkflow.from_storage(model_id=model_id, storage=storage)
           forecasts = workflow.predict(data)
           
           forecast_runs.labels(model_id=model_id, status="success").inc()
           return forecasts
       except Exception as e:
           forecast_runs.labels(model_id=model_id, status="error").inc()
           raise
       finally:
           duration = time.time() - start_time
           forecast_duration.labels(model_id=model_id).observe(duration)
   
   # Start metrics server
   start_http_server(8000)

Configure alerts for critical conditions:

- Forecast failures exceeding threshold
- Model age exceeding retraining schedule
- Data freshness issues
- Performance degradation

Configuration Management
-------------------------

Manage configuration separately from code using environment variables, configuration files, or secret management services.

.. code-block:: python

   from pydantic import BaseModel, Field
   from pydantic_settings import BaseSettings
   
   class DeploymentConfig(BaseSettings):
       """Production deployment configuration."""
       
       model_id: str = Field(..., description="Model identifier")
       storage_backend: str = Field(default="filesystem", description="Storage type")
       storage_path: str = Field(..., description="Storage location")
       
       data_source_url: str = Field(..., description="Data source connection")
       data_source_username: str | None = None
       data_source_password: str | None = None
       
       log_level: str = Field(default="INFO", description="Logging level")
       enable_metrics: bool = Field(default=True, description="Enable metrics export")
       
       class Config:
           env_file = ".env"
           env_file_encoding = "utf-8"
   
   # Load configuration from environment
   config = DeploymentConfig()

Store secrets securely using platform-specific services (AWS Secrets Manager, Azure Key Vault, Google Secret Manager) rather than environment variables for sensitive credentials.

Best Practices
--------------

- **Separate environments**: Use distinct configurations for development, staging, and production
- **Version models**: Tag model versions and track which version is deployed
- **Graceful degradation**: Implement fallback strategies when models fail to load
- **Resource limits**: Set appropriate CPU and memory limits for containers
- **Idempotency**: Design jobs to be safely retryable without side effects
- **Data validation**: Validate input data before forecasting to catch issues early
- **Monitoring first**: Deploy monitoring before deploying models
- **Gradual rollout**: Test new models in shadow mode before full deployment

Related Topics
--------------

- :doc:`data_integration` - Connecting to data sources in production
- :doc:`logging` - Configuring logging for production observability
- :doc:`use_cases` - Common deployment patterns for specific use cases