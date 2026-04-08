Production Deployment
======================

This guide covers deployment patterns for running OpenSTEF forecasting models in production environments. OpenSTEF is a Python library that integrates into your existing infrastructure—whether that's simple scheduled jobs, containerized services, or full orchestration platforms.

Deployment Approaches
---------------------

Simple Scheduled Jobs
^^^^^^^^^^^^^^^^^^^^^

For many use cases, a straightforward cron job or task scheduler is sufficient. This approach works well when:

- You have a small number of forecasting targets (< 100)
- Predictions run at regular intervals (e.g., hourly, daily)
- Your infrastructure is simple and doesn't require complex orchestration

Here's a minimal production script that loads data, trains a model, and generates forecasts:

.. code-block:: python

   from pathlib import Path
   from datetime import timedelta
   import pandas as pd
   
   from openstef_core.data import TimeSeriesDataset
   from openstef_models.workflows import create_forecasting_workflow, ForecastingWorkflowConfig
   from openstef_models.storage import MLFlowStorage
   
   def run_forecast_job(model_id: str, storage_path: Path):
       """Production forecasting job."""
       
       # Load your data (see data_integration.rst for details)
       data = load_data_from_source()  # Your data loading logic
       
       # Configure storage for model persistence
       storage = MLFlowStorage(
           tracking_uri=str(storage_path / "mlflow_tracking"),
           local_artifacts_path=storage_path / "mlflow_artifacts",
       )
       
       # Create workflow with production configuration
       config = ForecastingWorkflowConfig(
           model_id=model_id,
           horizons=["PT1H", "PT6H", "PT24H"],
           quantiles=[0.1, 0.5, 0.9],
           train_horizon_limit=timedelta(days=90),
           tags={"environment": "production", "version": "v4"},
       )
       
       workflow = create_forecasting_workflow(config)
       
       # Train model (with automatic storage via callbacks)
       workflow.fit(data=data)
       
       # Generate forecasts
       forecast = workflow.predict(data=data)
       
       # Store predictions (implement your storage logic)
       store_predictions(forecast, model_id)
       
       return forecast

Schedule this script using cron:

.. code-block:: bash

   # Run hourly forecasts at 5 minutes past the hour
   5 * * * * /usr/bin/python /opt/forecasting/run_forecast.py --model-id grid_123

Containerized Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^

Containerization provides consistency across environments and simplifies dependency management. Here's a production-ready Dockerfile:

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       g++ \
       && rm -rf /var/lib/apt/lists/*
   
   # Create non-root user
   RUN useradd -m -u 1000 forecaster
   WORKDIR /app
   
   # Install OpenSTEF and dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY --chown=forecaster:forecaster . .
   
   USER forecaster
   
   # Run forecasting job
   CMD ["python", "run_forecast.py"]

Example ``requirements.txt``:

.. code-block:: text

   openstef-models>=4.0.0
   openstef-beam>=4.0.0
   pandas>=2.0.0
   influxdb-client>=1.36.0  # If using InfluxDB

Build and run:

.. code-block:: bash

   docker build -t openstef-forecaster:latest .
   docker run -e MODEL_ID=grid_123 \
              -v /data/models:/app/models \
              openstef-forecaster:latest

Orchestration Platforms
^^^^^^^^^^^^^^^^^^^^^^^^

For larger deployments with multiple forecasting targets, orchestration platforms like Apache Airflow, Prefect, or Kubernetes CronJobs provide better management, monitoring, and error handling.

**Apache Airflow Example:**

.. code-block:: python

   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from datetime import datetime, timedelta
   
   from openstef_models.workflows import ForecastingWorkflow
   
   def train_model(model_id: str, **context):
       """Train forecasting model."""
       data = load_training_data(model_id, lookback_days=90)
       
       workflow = ForecastingWorkflow.from_storage(
           model_id=model_id,
           storage=get_storage(),
           fallback_to_new=True,
       )
       
       result = workflow.fit(data=data)
       context['ti'].xcom_push(key='metrics', value=result.metrics_test)
   
   def generate_forecast(model_id: str, **context):
       """Generate predictions."""
       data = load_recent_data(model_id, lookback_hours=168)
       
       workflow = ForecastingWorkflow.from_storage(
           model_id=model_id,
           storage=get_storage(),
       )
       
       forecast = workflow.predict(data=data)
       store_forecast(model_id, forecast)
   
   with DAG(
       'openstef_forecasting',
       default_args={
           'owner': 'energy-team',
           'retries': 2,
           'retry_delay': timedelta(minutes=5),
       },
       schedule_interval='0 * * * *',  # Hourly
       start_date=datetime(2025, 1, 1),
       catchup=False,
   ) as dag:
       
       # Train weekly
       train = PythonOperator(
           task_id='train_model',
           python_callable=train_model,
           op_kwargs={'model_id': 'grid_123'},
       )
       
       # Predict hourly
       predict = PythonOperator(
           task_id='generate_forecast',
           python_callable=generate_forecast,
           op_kwargs={'model_id': 'grid_123'},
       )
       
       train >> predict

**Kubernetes CronJob Example:**

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
   spec:
     schedule: "5 * * * *"  # Every hour at :05
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: forecaster
               image: openstef-forecaster:latest
               env:
               - name: MODEL_ID
                 value: "grid_123"
               - name: STORAGE_PATH
                 value: "/mnt/models"
               volumeMounts:
               - name: model-storage
                 mountPath: /mnt/models
             volumes:
             - name: model-storage
               persistentVolumeClaim:
                 claimName: openstef-models-pvc
             restartPolicy: OnFailure

Cloud Deployment
----------------

AWS Example
^^^^^^^^^^^

Deploy on AWS using ECS with scheduled tasks:

.. code-block:: python

   # task_definition.json
   {
     "family": "openstef-forecaster",
     "networkMode": "awsvpc",
     "containerDefinitions": [{
       "name": "forecaster",
       "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/openstef:latest",
       "environment": [
         {"name": "MODEL_ID", "value": "grid_123"},
         {"name": "S3_BUCKET", "value": "my-forecasts"}
       ],
       "logConfiguration": {
         "logDriver": "awslogs",
         "options": {
           "awslogs-group": "/ecs/openstef",
           "awslogs-region": "us-east-1"
         }
       }
     }],
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048"
   }

Use EventBridge to schedule the task:

.. code-block:: bash

   aws events put-rule \
     --name openstef-hourly \
     --schedule-expression "cron(5 * * * ? *)"
   
   aws events put-targets \
     --rule openstef-hourly \
     --targets "Id=1,Arn=arn:aws:ecs:us-east-1:123456789:cluster/prod,RoleArn=arn:aws:iam::123456789:role/ecsEventsRole,EcsParameters={TaskDefinitionArn=arn:aws:ecs:us-east-1:123456789:task-definition/openstef-forecaster:1,LaunchType=FARGATE}"

Azure Example
^^^^^^^^^^^^^

Deploy using Azure Container Instances with Logic Apps for scheduling:

.. code-block:: bash

   # Create container group
   az container create \
     --resource-group openstef-rg \
     --name openstef-forecaster \
     --image myregistry.azurecr.io/openstef:latest \
     --cpu 2 --memory 4 \
     --environment-variables MODEL_ID=grid_123 \
     --restart-policy Never

Monitoring and Observability
-----------------------------

Production deployments require monitoring for model performance, system health, and operational issues.

Application Metrics
^^^^^^^^^^^^^^^^^^^

Track key metrics using OpenSTEF's built-in evaluation tools:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.metrics import R2Provider, MAEProvider
   
   def monitor_model_performance(predictions, actuals):
       """Evaluate and log model performance."""
       
       config = EvaluationConfig(
           available_ats=["D-1T06:00"],
           lead_times=["PT1H", "PT24H"],
       )
       
       pipeline = EvaluationPipeline(
           config=config,
           quantiles=[Q(0.5)],
           window_metric_providers=[MAEProvider()],
           global_metric_providers=[R2Provider()],
       )
       
       report = pipeline.evaluate(
           forecasts=predictions,
           observations=actuals,
       )
       
       # Log metrics to your monitoring system
       for metric_name, value in report.metrics_full.items():
           log_metric(f"forecast.{metric_name}", value)

System Monitoring
^^^^^^^^^^^^^^^^^

Monitor container health and resource usage:

.. code-block:: python

   import logging
   import time
   from functools import wraps
   
   logger = logging.getLogger(__name__)
   
   def monitor_execution(func):
       """Decorator to track execution time and errors."""
       @wraps(func)
       def wrapper(*args, **kwargs):
           start_time = time.time()
           try:
               result = func(*args, **kwargs)
               duration = time.time() - start_time
               logger.info(f"{func.__name__} completed", extra={
                   "duration_seconds": duration,
                   "status": "success"
               })
               return result
           except Exception as e:
               duration = time.time() - start_time
               logger.error(f"{func.__name__} failed", extra={
                   "duration_seconds": duration,
                   "status": "error",
                   "error": str(e)
               })
               raise
       return wrapper
   
   @monitor_execution
   def run_forecast_job(model_id: str):
       # Your forecasting logic
       pass

For detailed logging configuration, see :doc:`logging`.

Health Checks
^^^^^^^^^^^^^

Implement health check endpoints for orchestration platforms:

.. code-block:: python

   from pathlib import Path
   from datetime import datetime, timedelta
   
   def check_model_health(model_id: str, storage_path: Path) -> bool:
       """Verify model is recent and predictions are being generated."""
       
       # Check model age
       model_file = storage_path / f"{model_id}/model.pkl"
       if not model_file.exists():
           return False
       
       model_age = datetime.now() - datetime.fromtimestamp(model_file.stat().st_mtime)
       if model_age > timedelta(days=7):
           logger.warning(f"Model {model_id} is {model_age.days} days old")
           return False
       
       # Check recent predictions
       predictions_file = storage_path / f"{model_id}/latest_predictions.csv"
       if not predictions_file.exists():
           return False
       
       pred_age = datetime.now() - datetime.fromtimestamp(predictions_file.stat().st_mtime)
       if pred_age > timedelta(hours=2):
           logger.warning(f"Last prediction for {model_id} was {pred_age} ago")
           return False
       
       return True

Configuration Management
------------------------

Manage environment-specific configuration using environment variables or configuration files:

.. code-block:: python

   from pydantic import BaseModel, Field
   from pathlib import Path
   import os
   
   class DeploymentConfig(BaseModel):
       """Production deployment configuration."""
       
       model_id: str = Field(..., description="Unique model identifier")
       storage_path: Path = Field(default=Path("/mnt/models"))
       data_source: str = Field(default="influxdb")
       
       # Data source configuration
       influx_url: str = Field(default_factory=lambda: os.getenv("INFLUX_URL", ""))
       influx_token: str = Field(default_factory=lambda: os.getenv("INFLUX_TOKEN", ""))
       
       # Model configuration
       train_interval_hours: int = Field(default=168)  # Weekly
       prediction_interval_hours: int = Field(default=1)  # Hourly
       
       # Monitoring
       enable_metrics: bool = Field(default=True)
       metrics_endpoint: str | None = None
   
   # Load from environment
   config = DeploymentConfig(
       model_id=os.getenv("MODEL_ID", "default"),
   )

Best Practices
--------------

**Model Versioning**: Always tag models with version information and track which model version generated which predictions. Use the ``tags`` parameter in ``ForecastingWorkflowConfig``.

**Graceful Degradation**: Handle missing data and model failures gracefully. Consider fallback strategies like using the previous forecast or a simple baseline model.

**Resource Limits**: Set appropriate CPU and memory limits based on your data volume and model complexity. XGBoost models typically need 2-4 GB RAM for moderate-sized datasets.

**Retries**: Implement retry logic for transient failures (network issues, temporary data unavailability), but fail fast for permanent errors (invalid configuration, corrupted models).

**Data Freshness**: Monitor input data freshness and alert when data is stale. Energy forecasts degrade quickly with outdated weather or load data.

**Separate Training and Prediction**: In production, training and prediction often run on different schedules. Training might be weekly or daily, while predictions run hourly or more frequently.

See Also
--------

- :doc:`data_integration` - Loading data from various sources
- :doc:`logging` - Configuring logging for production
- :doc:`use_cases` - Common forecasting scenarios