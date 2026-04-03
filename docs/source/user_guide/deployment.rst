Production Deployment
=====================

OpenSTEF is a Python library for short-term energy forecasting. Deploying it to production means integrating it into your operational infrastructure—whether that's a simple scheduled job, a containerized service, or a full orchestration platform. This page covers practical deployment patterns, containerization strategies, cloud deployment options, and monitoring setup.

Deployment Approaches
---------------------

The right deployment approach depends on your infrastructure, scale, and operational requirements. OpenSTEF workflows can be deployed in several ways:

**Scheduled Jobs**

The simplest deployment pattern runs forecasting workflows on a schedule using cron, systemd timers, or task schedulers. This works well for periodic forecasting tasks where you need predictions at regular intervals (e.g., hourly forecasts).

.. code-block:: python

   # forecast_job.py
   import logging
   from datetime import datetime, timedelta
   from pathlib import Path
   
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.model import ForecastingModel
   from openstef_models.forecasters import XGBQuantileForecaster
   from openstef_models.storage import LocalStorage
   from openstef_core.quantiles import Q
   from openstef_core.lead_time import LeadTime
   
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   def run_forecast():
       """Run a single forecasting iteration."""
       logger.info(f"Starting forecast run at {datetime.now()}")
       
       # Load your data (see data_integration page for details)
       dataset = load_data_from_source()
       
       # Load or create model
       storage = LocalStorage(base_path=Path("/var/openstef/models"))
       
       try:
           workflow = CustomForecastingWorkflow.from_storage(
               model_id="production_model_v1",
               storage=storage,
           )
           logger.info("Loaded existing model from storage")
       except FileNotFoundError:
           # Create new model if none exists
           model = ForecastingModel(
               forecaster=XGBQuantileForecaster(
                   horizons=[LeadTime.from_string("PT24H")],
                   quantiles=[Q(0.1), Q(0.5), Q(0.9)],
               )
           )
           workflow = CustomForecastingWorkflow(
               model=model,
               model_id="production_model_v1",
               storage=storage,
           )
           logger.info("Training new model")
           workflow.fit(data=dataset)
       
       # Generate forecast
       forecast = workflow.predict(data=dataset)
       
       # Store results
       save_forecast_to_destination(forecast)
       
       logger.info(f"Forecast completed at {datetime.now()}")
   
   if __name__ == "__main__":
       run_forecast()

Schedule this script with cron:

.. code-block:: bash

   # Run every hour at 5 minutes past
   5 * * * * /usr/bin/python3 /opt/openstef/forecast_job.py >> /var/log/openstef/forecast.log 2>&1

**Orchestration Platforms**

For more complex workflows with dependencies, retries, and monitoring, orchestration platforms like Apache Airflow, Prefect, or Dagster provide better control.

.. code-block:: python

   # airflow_dag.py
   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   
   def train_model(**context):
       """Train or update forecasting model."""
       from openstef_models.workflows import CustomForecastingWorkflow
       # Training logic here
       pass
   
   def generate_forecast(**context):
       """Generate forecast using trained model."""
       from openstef_models.workflows import CustomForecastingWorkflow
       # Forecasting logic here
       pass
   
   def validate_forecast(**context):
       """Validate forecast quality before publishing."""
       # Validation logic here
       pass
   
   default_args = {
       'owner': 'energy-team',
       'depends_on_past': False,
       'start_date': datetime(2025, 1, 1),
       'email_on_failure': True,
       'email_on_retry': False,
       'retries': 2,
       'retry_delay': timedelta(minutes=5),
   }
   
   with DAG(
       'openstef_forecasting',
       default_args=default_args,
       description='Hourly energy forecasting with OpenSTEF',
       schedule_interval='5 * * * *',  # Every hour at 5 minutes past
       catchup=False,
   ) as dag:
       
       train = PythonOperator(
           task_id='train_model',
           python_callable=train_model,
       )
       
       forecast = PythonOperator(
           task_id='generate_forecast',
           python_callable=generate_forecast,
       )
       
       validate = PythonOperator(
           task_id='validate_forecast',
           python_callable=validate_forecast,
       )
       
       train >> forecast >> validate

Containerization
----------------

Containerizing OpenSTEF workflows ensures consistent environments across development and production. Here's a production-ready Dockerfile:

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   # Set working directory
   WORKDIR /app
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       g++ \
       && rm -rf /var/lib/apt/lists/*
   
   # Copy requirements
   COPY requirements.txt .
   
   # Install Python dependencies
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY . .
   
   # Create non-root user
   RUN useradd -m -u 1000 openstef && \
       chown -R openstef:openstef /app
   USER openstef
   
   # Set environment variables
   ENV PYTHONUNBUFFERED=1
   ENV OPENSTEF_LOG_LEVEL=INFO
   
   # Run the forecasting job
   CMD ["python", "forecast_job.py"]

Build and run:

.. code-block:: bash

   docker build -t openstef-forecast:latest .
   docker run -v /var/openstef/models:/app/models \
              -v /var/openstef/config:/app/config \
              -e OPENSTEF_LOG_LEVEL=INFO \
              openstef-forecast:latest

For Kubernetes deployment:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
     namespace: energy-forecasting
   spec:
     schedule: "5 * * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: forecast
               image: openstef-forecast:latest
               env:
               - name: OPENSTEF_LOG_LEVEL
                 value: "INFO"
               - name: MODEL_STORAGE_PATH
                 value: "/models"
               volumeMounts:
               - name: model-storage
                 mountPath: /models
               resources:
                 requests:
                   memory: "2Gi"
                   cpu: "1"
                 limits:
                   memory: "4Gi"
                   cpu: "2"
             volumes:
             - name: model-storage
               persistentVolumeClaim:
                 claimName: openstef-models
             restartPolicy: OnFailure

Cloud Deployment
----------------

**AWS Deployment**

Deploy OpenSTEF on AWS using ECS Fargate for serverless container execution:

.. code-block:: json

   {
     "family": "openstef-forecast",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "containerDefinitions": [
       {
         "name": "forecast",
         "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/openstef-forecast:latest",
         "environment": [
           {"name": "OPENSTEF_LOG_LEVEL", "value": "INFO"},
           {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"}
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/openstef-forecast",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }

Use EventBridge to trigger on a schedule:

.. code-block:: bash

   aws events put-rule \
     --name openstef-hourly-forecast \
     --schedule-expression "cron(5 * * * ? *)"
   
   aws events put-targets \
     --rule openstef-hourly-forecast \
     --targets "Id"="1","Arn"="arn:aws:ecs:us-east-1:123456789:cluster/production","RoleArn"="arn:aws:iam::123456789:role/ecsEventsRole","EcsParameters"="{TaskDefinitionArn=arn:aws:ecs:us-east-1:123456789:task-definition/openstef-forecast:1,TaskCount=1,LaunchType=FARGATE}"

**Azure Deployment**

Use Azure Container Instances with Azure Functions for event-driven forecasting:

.. code-block:: python

   # Azure Function trigger
   import azure.functions as func
   from azure.mgmt.containerinstance import ContainerInstanceManagementClient
   
   def main(mytimer: func.TimerRequest) -> None:
       """Trigger OpenSTEF forecast container on schedule."""
       # Start container instance
       client = ContainerInstanceManagementClient(credential, subscription_id)
       client.container_groups.start(resource_group, container_group_name)

**GCP Deployment**

Use Cloud Run Jobs for scheduled forecasting:

.. code-block:: bash

   gcloud run jobs create openstef-forecast \
     --image gcr.io/project-id/openstef-forecast:latest \
     --region us-central1 \
     --memory 2Gi \
     --cpu 1 \
     --max-retries 2 \
     --task-timeout 1h
   
   gcloud scheduler jobs create http openstef-hourly \
     --schedule "5 * * * *" \
     --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/project-id/jobs/openstef-forecast:run" \
     --http-method POST

Monitoring and Health Checks
-----------------------------

Production deployments need monitoring to detect failures, track performance, and ensure forecast quality.

**Basic Health Check**

.. code-block:: python

   # health_check.py
   import logging
   from datetime import datetime, timedelta
   from pathlib import Path
   
   def check_model_health(model_path: Path) -> bool:
       """Verify model exists and is recent."""
       if not model_path.exists():
           logging.error("Model file not found")
           return False
       
       # Check model age
       model_age = datetime.now() - datetime.fromtimestamp(model_path.stat().st_mtime)
       if model_age > timedelta(days=7):
           logging.warning(f"Model is {model_age.days} days old")
           return False
       
       return True
   
   def check_forecast_freshness(forecast_path: Path, max_age_hours: int = 2) -> bool:
       """Verify latest forecast is recent."""
       if not forecast_path.exists():
           logging.error("No forecast found")
           return False
       
       forecast_age = datetime.now() - datetime.fromtimestamp(forecast_path.stat().st_mtime)
       if forecast_age > timedelta(hours=max_age_hours):
           logging.error(f"Forecast is {forecast_age.total_seconds() / 3600:.1f} hours old")
           return False
       
       return True

**Prometheus Metrics**

Export metrics for monitoring systems:

.. code-block:: python

   # metrics.py
   from prometheus_client import Counter, Histogram, Gauge, start_http_server
   import time
   
   # Define metrics
   forecast_runs_total = Counter(
       'openstef_forecast_runs_total',
       'Total number of forecast runs',
       ['status']
   )
   
   forecast_duration_seconds = Histogram(
       'openstef_forecast_duration_seconds',
       'Time spent generating forecast'
   )
   
   model_age_days = Gauge(
       'openstef_model_age_days',
       'Age of the current model in days'
   )
   
   forecast_error = Gauge(
       'openstef_forecast_error',
       'Recent forecast error metric',
       ['metric_type']
   )
   
   def run_forecast_with_metrics():
       """Run forecast and record metrics."""
       start_time = time.time()
       
       try:
           run_forecast()
           forecast_runs_total.labels(status='success').inc()
       except Exception as e:
           forecast_runs_total.labels(status='failure').inc()
           raise
       finally:
           duration = time.time() - start_time
           forecast_duration_seconds.observe(duration)
   
   if __name__ == "__main__":
       # Start metrics server
       start_http_server(8000)
       
       # Run forecast loop
       while True:
           run_forecast_with_metrics()
           time.sleep(3600)  # Run every hour

**Logging Configuration**

See the :doc:`logging` page for detailed logging setup. For production deployments, use structured logging:

.. code-block:: python

   import logging
   import json
   from datetime import datetime
   
   class StructuredFormatter(logging.Formatter):
       """Format logs as JSON for centralized logging systems."""
       
       def format(self, record):
           log_data = {
               'timestamp': datetime.utcnow().isoformat(),
               'level': record.levelname,
               'logger': record.name,
               'message': record.getMessage(),
               'module': record.module,
               'function': record.funcName,
           }
           
           if record.exc_info:
               log_data['exception'] = self.formatException(record.exc_info)
           
           return json.dumps(log_data)
   
   # Configure logging
   handler = logging.StreamHandler()
   handler.setFormatter(StructuredFormatter())
   logging.root.addHandler(handler)
   logging.root.setLevel(logging.INFO)

Configuration Management
------------------------

Separate configuration from code using environment variables and configuration files:

.. code-block:: python

   # config.py
   from pydantic import BaseModel
   from pathlib import Path
   import os
   
   class DeploymentConfig(BaseModel):
       """Production deployment configuration."""
       
       model_storage_path: Path = Path(os.getenv("MODEL_STORAGE_PATH", "/var/openstef/models"))
       forecast_output_path: Path = Path(os.getenv("FORECAST_OUTPUT_PATH", "/var/openstef/forecasts"))
       log_level: str = os.getenv("OPENSTEF_LOG_LEVEL", "INFO")
       
       # Data source configuration
       data_source_url: str = os.getenv("DATA_SOURCE_URL", "")
       data_source_api_key: str = os.getenv("DATA_SOURCE_API_KEY", "")
       
       # Model parameters
       retrain_interval_hours: int = int(os.getenv("RETRAIN_INTERVAL_HOURS", "168"))  # Weekly
       forecast_horizon_hours: int = int(os.getenv("FORECAST_HORIZON_HOURS", "48"))
       
       # Monitoring
       metrics_port: int = int(os.getenv("METRICS_PORT", "8000"))
       enable_metrics: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"

Best Practices
--------------

**Resource Management**

- Allocate sufficient memory for model training (2-4 GB typical)
- Use CPU limits to prevent resource contention
- Consider GPU acceleration for large-scale deployments

**Error Handling**

- Implement retries with exponential backoff for transient failures
- Log detailed error information for debugging
- Set up alerts for critical failures

**Model Updates**

- Version your models using the storage system
- Test new models before deploying to production
- Keep previous model versions for rollback

**Data Quality**

- Validate input data before forecasting
- Monitor for data gaps or anomalies
- Implement fallback strategies for missing data

.. note::
   For data integration patterns (reading from S3, Databricks, InfluxDB), see :doc:`data_integration`. For logging configuration details, see :doc:`logging`.

Related Topics
--------------

- :doc:`data_integration` - Reading data from various sources
- :doc:`logging` - Logging configuration and best practices
- :doc:`use_cases` - Common OpenSTEF use cases with examples