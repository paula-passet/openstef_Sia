Production Deployment
=====================

OpenSTEF is a Python library designed to integrate into your existing infrastructure. This page covers practical deployment patterns for running OpenSTEF forecasting workloads in production, from simple scheduled jobs to full orchestration platforms.

Deployment Approaches
---------------------

OpenSTEF forecasts are typically generated on a schedule—hourly, daily, or at custom intervals depending on your use case. The library itself doesn't include a scheduler; instead, you integrate it into your preferred orchestration system.

Common deployment patterns:

- **Scheduled scripts**: Cron jobs or systemd timers running Python scripts
- **Workflow orchestrators**: Airflow, Dagster, Prefect, or similar platforms
- **Kubernetes CronJobs**: Container-based scheduled workloads
- **Cloud-native schedulers**: AWS Lambda + EventBridge, Azure Functions, Google Cloud Scheduler

Choose based on your existing infrastructure, team expertise, and operational requirements. All approaches use the same OpenSTEF library code—only the scheduling mechanism differs.

Simple Scheduled Job
--------------------

The most straightforward deployment is a Python script executed on schedule. This works well for single-target forecasts or small-scale deployments.

.. code-block:: python

   #!/usr/bin/env python3
   """Production forecasting script for scheduled execution."""
   
   import logging
   from datetime import datetime, timedelta
   from pathlib import Path
   
   from openstef_core.data import VersionedTimeSeriesDataset
   from openstef_models.forecaster import ForecastingModel
   from openstef_models.storage import LocalModelStorage
   from openstef_models.workflows import CustomForecastingWorkflow
   
   # Configure logging (see logging.rst for details)
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   logger = logging.getLogger(__name__)
   
   def run_forecast():
       """Execute forecast and save results."""
       try:
           # Load data (see data_integration.rst for data loading patterns)
           dataset = load_data_from_source()
           
           # Load or create model
           storage = LocalModelStorage(base_path=Path("/var/openstef/models"))
           model = ForecastingModel.load(storage=storage, model_id="grid_123")
           
           # Generate forecast
           workflow = CustomForecastingWorkflow(model=model, storage=storage)
           forecast = workflow.predict(dataset)
           
           # Save forecast to database/API
           save_forecast_results(forecast)
           
           logger.info(f"Forecast completed successfully at {datetime.now()}")
           
       except Exception as e:
           logger.error(f"Forecast failed: {e}", exc_info=True)
           raise  # Re-raise for monitoring systems to catch
   
   if __name__ == "__main__":
       run_forecast()

Schedule this script with cron:

.. code-block:: bash

   # Run every hour at 5 minutes past
   5 * * * * /usr/bin/python3 /opt/openstef/forecast_job.py >> /var/log/openstef/forecast.log 2>&1

Or use systemd timers for better logging and dependency management:

.. code-block:: ini

   # /etc/systemd/system/openstef-forecast.service
   [Unit]
   Description=OpenSTEF Forecasting Job
   After=network.target
   
   [Service]
   Type=oneshot
   User=openstef
   WorkingDirectory=/opt/openstef
   ExecStart=/usr/bin/python3 /opt/openstef/forecast_job.py
   StandardOutput=journal
   StandardError=journal

.. code-block:: ini

   # /etc/systemd/system/openstef-forecast.timer
   [Unit]
   Description=Run OpenSTEF forecast hourly
   
   [Timer]
   OnCalendar=hourly
   Persistent=true
   
   [Install]
   WantedBy=timers.target

Containerization
----------------

Containerizing OpenSTEF forecasting workloads provides consistent environments across development and production. Here's a production-ready Dockerfile:

.. code-block:: dockerfile

   FROM python:3.12-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       g++ \
       && rm -rf /var/lib/apt/lists/*
   
   # Create non-root user
   RUN useradd -m -u 1000 openstef
   WORKDIR /app
   
   # Install OpenSTEF and dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY --chown=openstef:openstef . .
   
   USER openstef
   
   # Health check endpoint (if using web service)
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
       CMD python -c "import openstef_models; print('healthy')" || exit 1
   
   ENTRYPOINT ["python", "forecast_job.py"]

Example ``requirements.txt``:

.. code-block:: text

   openstef-models>=4.0.0
   openstef-beam>=4.0.0
   pandas>=2.0.0
   # Add data connectors as needed
   sqlalchemy>=2.0.0
   psycopg2-binary>=2.9.0

Build and run:

.. code-block:: bash

   docker build -t openstef-forecaster:latest .
   docker run --rm \
       -v /var/openstef/models:/models:ro \
       -v /var/openstef/config:/config:ro \
       -e OPENSTEF_MODEL_PATH=/models \
       openstef-forecaster:latest

Kubernetes Deployment
---------------------

For cloud-native deployments, Kubernetes CronJobs provide scalability and reliability:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
     namespace: forecasting
   spec:
     schedule: "5 * * * *"  # Every hour at 5 minutes past
     successfulJobsHistoryLimit: 3
     failedJobsHistoryLimit: 3
     concurrencyPolicy: Forbid  # Prevent overlapping runs
     jobTemplate:
       spec:
         backoffLimit: 2
         template:
           spec:
             restartPolicy: OnFailure
             containers:
             - name: forecaster
               image: your-registry/openstef-forecaster:v1.2.3
               imagePullPolicy: IfNotPresent
               env:
               - name: DATABASE_URL
                 valueFrom:
                   secretKeyRef:
                     name: openstef-secrets
                     key: database-url
               - name: MODEL_STORAGE_PATH
                 value: /models
               resources:
                 requests:
                   memory: "2Gi"
                   cpu: "1000m"
                 limits:
                   memory: "4Gi"
                   cpu: "2000m"
               volumeMounts:
               - name: model-storage
                 mountPath: /models
                 readOnly: true
             volumes:
             - name: model-storage
               persistentVolumeClaim:
                 claimName: openstef-models-pvc

For parallel processing of multiple targets, use a Kubernetes Job with multiple pods:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: Job
   metadata:
     name: openstef-batch-forecast
   spec:
     parallelism: 10  # Process 10 targets concurrently
     completions: 100  # Total targets to process
     template:
       spec:
         containers:
         - name: forecaster
           image: your-registry/openstef-forecaster:v1.2.3
           env:
           - name: TARGET_INDEX
             valueFrom:
               fieldRef:
                 fieldPath: metadata.labels['batch.kubernetes.io/job-completion-index']

Workflow Orchestration
----------------------

For complex forecasting pipelines with dependencies, use a workflow orchestrator. Here's an Airflow DAG example:

.. code-block:: python

   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   
   def train_models(**context):
       """Train models for all targets."""
       from openstef_models.workflows import CustomForecastingWorkflow
       # Training logic here
       pass
   
   def generate_forecasts(**context):
       """Generate forecasts using trained models."""
       # Forecasting logic here
       pass
   
   def validate_forecasts(**context):
       """Validate forecast quality."""
       # Validation logic here
       pass
   
   default_args = {
       'owner': 'energy-team',
       'depends_on_past': False,
       'email_on_failure': True,
       'email_on_retry': False,
       'retries': 2,
       'retry_delay': timedelta(minutes=5),
   }
   
   with DAG(
       'openstef_forecasting',
       default_args=default_args,
       description='OpenSTEF forecasting pipeline',
       schedule_interval='@hourly',
       start_date=datetime(2024, 1, 1),
       catchup=False,
       tags=['forecasting', 'openstef'],
   ) as dag:
       
       train = PythonOperator(
           task_id='train_models',
           python_callable=train_models,
       )
       
       forecast = PythonOperator(
           task_id='generate_forecasts',
           python_callable=generate_forecasts,
       )
       
       validate = PythonOperator(
           task_id='validate_forecasts',
           python_callable=validate_forecasts,
       )
       
       train >> forecast >> validate

Cloud Deployment Options
------------------------

**AWS Lambda**

For serverless deployments with infrequent execution:

.. code-block:: python

   import json
   import logging
   from openstef_models.workflows import CustomForecastingWorkflow
   
   logger = logging.getLogger()
   logger.setLevel(logging.INFO)
   
   def lambda_handler(event, context):
       """AWS Lambda handler for forecasting."""
       try:
           target_id = event.get('target_id')
           
           # Load data from S3, generate forecast
           # (see data_integration.rst for S3 patterns)
           
           return {
               'statusCode': 200,
               'body': json.dumps({'status': 'success', 'target': target_id})
           }
       except Exception as e:
           logger.error(f"Forecast failed: {e}", exc_info=True)
           return {
               'statusCode': 500,
               'body': json.dumps({'error': str(e)})
           }

Trigger with EventBridge on a schedule or use Step Functions for complex workflows.

**Azure Container Instances**

Deploy containerized forecasting jobs on-demand:

.. code-block:: bash

   az container create \
       --resource-group openstef-rg \
       --name openstef-forecast \
       --image yourregistry.azurecr.io/openstef-forecaster:latest \
       --cpu 2 --memory 4 \
       --restart-policy Never \
       --environment-variables \
           DATABASE_URL=$DATABASE_URL \
           MODEL_STORAGE_PATH=/models

**Google Cloud Run Jobs**

For scheduled container execution:

.. code-block:: bash

   gcloud run jobs create openstef-forecast \
       --image gcr.io/your-project/openstef-forecaster:latest \
       --region us-central1 \
       --memory 4Gi \
       --cpu 2 \
       --max-retries 2 \
       --task-timeout 30m

Monitoring and Health Checks
-----------------------------

Production deployments require monitoring to detect failures and performance issues.

**Basic Health Check**

.. code-block:: python

   def health_check():
       """Verify system components are operational."""
       checks = {
           'database': check_database_connection(),
           'model_storage': check_model_storage_accessible(),
           'data_source': check_data_source_available(),
       }
       
       all_healthy = all(checks.values())
       return {
           'status': 'healthy' if all_healthy else 'unhealthy',
           'checks': checks,
           'timestamp': datetime.now().isoformat()
       }

**Metrics Collection**

Track key operational metrics:

.. code-block:: python

   import time
   from dataclasses import dataclass
   
   @dataclass
   class ForecastMetrics:
       """Operational metrics for monitoring."""
       target_id: str
       execution_time_seconds: float
       forecast_horizon_hours: int
       data_points_processed: int
       model_version: str
       success: bool
       error_message: str | None = None
   
   def run_forecast_with_metrics(target_id: str) -> ForecastMetrics:
       """Execute forecast and collect metrics."""
       start_time = time.time()
       
       try:
           # Forecasting logic
           forecast = generate_forecast(target_id)
           
           return ForecastMetrics(
               target_id=target_id,
               execution_time_seconds=time.time() - start_time,
               forecast_horizon_hours=forecast.horizon_hours,
               data_points_processed=len(forecast.data),
               model_version=forecast.model_version,
               success=True
           )
       except Exception as e:
           return ForecastMetrics(
               target_id=target_id,
               execution_time_seconds=time.time() - start_time,
               forecast_horizon_hours=0,
               data_points_processed=0,
               model_version="unknown",
               success=False,
               error_message=str(e)
           )

Export metrics to your monitoring system (Prometheus, CloudWatch, Datadog, etc.). See :doc:`logging` for detailed logging configuration.

**Alerting**

Set up alerts for critical failures:

- Forecast execution failures
- Execution time exceeding threshold
- Model loading failures
- Data quality issues
- Forecast accuracy degradation

Configuration Management
------------------------

Separate configuration from code for different environments:

.. code-block:: python

   from pathlib import Path
   from pydantic import BaseModel, Field
   import yaml
   
   class ForecastConfig(BaseModel):
       """Production forecasting configuration."""
       target_id: str
       model_storage_path: Path
       database_url: str
       forecast_horizon_hours: int = Field(default=48)
       retrain_interval_days: int = Field(default=7)
       prediction_interval_minutes: int = Field(default=60)
   
   def load_config(env: str = "production") -> ForecastConfig:
       """Load environment-specific configuration."""
       config_path = Path(f"/etc/openstef/config.{env}.yaml")
       with open(config_path) as f:
           config_data = yaml.safe_load(f)
       return ForecastConfig(**config_data)

Example configuration file:

.. code-block:: yaml

   # config.production.yaml
   target_id: "grid_substation_123"
   model_storage_path: "/var/openstef/models"
   database_url: "postgresql://user:pass@db.example.com/forecasts"
   forecast_horizon_hours: 48
   retrain_interval_days: 7
   prediction_interval_minutes: 60

Store secrets separately using environment variables or secret management services (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault).

Best Practices
--------------

- **Idempotency**: Design jobs to produce the same output when run multiple times with the same input
- **Graceful degradation**: Handle missing data or model loading failures without crashing
- **Resource limits**: Set appropriate memory and CPU limits to prevent resource exhaustion
- **Logging**: Use structured logging with correlation IDs for debugging (see :doc:`logging`)
- **Model versioning**: Track which model version generated each forecast
- **Data validation**: Validate input data quality before forecasting
- **Timeout handling**: Set reasonable timeouts for long-running operations
- **Retry logic**: Implement exponential backoff for transient failures

Next Steps
----------

- :doc:`data_integration` - Patterns for loading data from various sources
- :doc:`logging` - Configure logging for production environments
- :doc:`use_cases` - Common forecasting use cases and patterns