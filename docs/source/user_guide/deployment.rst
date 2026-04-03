Production Deployment
=====================

This page covers practical deployment patterns for running OpenSTEF in production environments. OpenSTEF is a Python library, not a standalone application—you integrate it into your own systems and choose the deployment approach that fits your infrastructure.

Deployment approaches range from simple scheduled scripts running on a single server to sophisticated orchestration platforms managing distributed workloads. This guide walks through common patterns with concrete examples.


Deployment Approaches
---------------------

Simple Scheduled Jobs
^^^^^^^^^^^^^^^^^^^^^

For many use cases, a straightforward cron job or scheduled task is sufficient. This approach works well when:

- You have a manageable number of forecasting targets (dozens to hundreds)
- Forecasts run on a predictable schedule (e.g., hourly)
- A single machine has adequate resources
- You don't need complex dependency management

Here's a minimal production script that trains models and generates forecasts:

.. code-block:: python

   #!/usr/bin/env python3
   """Hourly forecasting job for production deployment."""
   
   import logging
   from datetime import datetime, timedelta
   
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.enums import LeadTime, Quantile as Q
   from openstef_models.forecasting import ForecastingModel, ForecastingWorkflow
   from openstef_models.forecasting.forecasters import XGBForecaster
   
   from my_company.data import load_historical_data, load_weather_forecast
   from my_company.storage import save_forecast_to_database
   
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   
   def run_forecast(target_id: str, model_storage):
       """Generate forecast for a single target."""
       logger.info(f"Starting forecast for {target_id}")
       
       # Load data for training and prediction
       historical = load_historical_data(
           target_id=target_id,
           start=datetime.now() - timedelta(days=30),
           end=datetime.now()
       )
       
       # Create or load workflow
       try:
           workflow = ForecastingWorkflow.from_storage(
               model_id=target_id,
               storage=model_storage,
               fallback_model=create_default_model()
           )
       except Exception as e:
           logger.warning(f"Could not load model: {e}. Training new model.")
           workflow = ForecastingWorkflow(
               model=create_default_model(),
               model_id=target_id,
               storage=model_storage
           )
           workflow.fit(historical)
       
       # Generate forecast
       forecast = workflow.predict(historical)
       
       # Save to production database
       save_forecast_to_database(target_id, forecast)
       logger.info(f"Completed forecast for {target_id}")
   
   
   def create_default_model():
       """Create standard production forecasting model."""
       horizons = [LeadTime.from_string(f"PT{h}H") for h in range(1, 48)]
       quantiles = [Q(0.1), Q(0.5), Q(0.9)]
       
       return ForecastingModel(
           forecaster=XGBForecaster(
               horizons=horizons,
               quantiles=quantiles,
               n_estimators=100,
               max_depth=7
           )
       )
   
   
   if __name__ == "__main__":
       from my_company.config import TARGETS, MODEL_STORAGE
       
       for target in TARGETS:
           try:
               run_forecast(target, MODEL_STORAGE)
           except Exception as e:
               logger.error(f"Failed to forecast {target}: {e}", exc_info=True)

Schedule this with cron:

.. code-block:: bash

   # Run every hour at 5 minutes past
   5 * * * * /opt/openstef/venv/bin/python /opt/openstef/forecast.py >> /var/log/openstef/forecast.log 2>&1

Containerized Deployment
^^^^^^^^^^^^^^^^^^^^^^^^

Containers provide consistency across environments and simplify dependency management. Here's a production-ready Dockerfile:

.. code-block:: dockerfile

   FROM python:3.12-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       g++ \
       && rm -rf /var/lib/apt/lists/*
   
   # Create application user
   RUN useradd -m -u 1000 openstef
   WORKDIR /app
   
   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY --chown=openstef:openstef . .
   
   # Switch to non-root user
   USER openstef
   
   # Run the forecasting script
   CMD ["python", "forecast.py"]

Example ``requirements.txt``:

.. code-block:: text

   openstef-core==4.0.0
   openstef-models==4.0.0
   openstef-beam==4.0.0
   pandas==2.2.0
   psycopg2-binary==2.9.9  # If using PostgreSQL
   boto3==1.34.0           # If using AWS S3

Build and run:

.. code-block:: bash

   docker build -t my-company/openstef-forecaster:latest .
   docker run -e DATABASE_URL=postgresql://... my-company/openstef-forecaster:latest

Orchestration Platforms
^^^^^^^^^^^^^^^^^^^^^^^

For larger deployments with hundreds or thousands of targets, orchestration platforms like Apache Airflow or Kubernetes CronJobs provide better scalability and monitoring.

**Apache Airflow Example:**

.. code-block:: python

   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   
   from my_company.forecasting import run_forecast, TARGETS
   
   default_args = {
       'owner': 'data-team',
       'depends_on_past': False,
       'start_date': datetime(2025, 1, 1),
       'email_on_failure': True,
       'email': ['alerts@company.com'],
       'retries': 2,
       'retry_delay': timedelta(minutes=5),
   }
   
   dag = DAG(
       'openstef_hourly_forecasts',
       default_args=default_args,
       description='Generate hourly energy forecasts',
       schedule_interval='5 * * * *',  # 5 minutes past each hour
       catchup=False,
   )
   
   # Create one task per forecasting target
   for target_id in TARGETS:
       task = PythonOperator(
           task_id=f'forecast_{target_id}',
           python_callable=run_forecast,
           op_kwargs={'target_id': target_id},
           dag=dag,
       )

**Kubernetes CronJob Example:**

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecaster
     namespace: production
   spec:
     schedule: "5 * * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: forecaster
               image: my-company/openstef-forecaster:latest
               env:
               - name: DATABASE_URL
                 valueFrom:
                   secretKeyRef:
                     name: openstef-secrets
                     key: database-url
               resources:
                 requests:
                   memory: "2Gi"
                   cpu: "1000m"
                 limits:
                   memory: "4Gi"
                   cpu: "2000m"
             restartPolicy: OnFailure

Cloud Deployment
----------------

AWS Lambda
^^^^^^^^^^

For event-driven or infrequent forecasting, serverless functions can be cost-effective:

.. code-block:: python

   import json
   import logging
   from my_company.forecasting import run_forecast
   
   logger = logging.getLogger()
   logger.setLevel(logging.INFO)
   
   def lambda_handler(event, context):
       """AWS Lambda handler for forecast generation."""
       target_id = event.get('target_id')
       
       if not target_id:
           return {
               'statusCode': 400,
               'body': json.dumps({'error': 'target_id required'})
           }
       
       try:
           run_forecast(target_id)
           return {
               'statusCode': 200,
               'body': json.dumps({'message': f'Forecast completed for {target_id}'})
           }
       except Exception as e:
           logger.error(f"Forecast failed: {e}", exc_info=True)
           return {
               'statusCode': 500,
               'body': json.dumps({'error': str(e)})
           }

Package dependencies as a Lambda layer or use container images for Lambda.

Azure Functions and Google Cloud Functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similar patterns apply to other cloud providers. The key is wrapping your forecasting logic in the provider's function handler interface.

Monitoring and Health Checks
-----------------------------

Production deployments need monitoring to detect failures and performance issues.

Health Check Endpoint
^^^^^^^^^^^^^^^^^^^^^

If running as a service, expose a health check endpoint:

.. code-block:: python

   from flask import Flask, jsonify
   from datetime import datetime
   
   app = Flask(__name__)
   
   @app.route('/health')
   def health_check():
       """Basic health check endpoint."""
       return jsonify({
           'status': 'healthy',
           'timestamp': datetime.now().isoformat(),
           'version': '4.0.0'
       })
   
   @app.route('/ready')
   def readiness_check():
       """Check if service can handle requests."""
       try:
           # Verify database connection, model availability, etc.
           check_database_connection()
           check_model_storage()
           return jsonify({'status': 'ready'})
       except Exception as e:
           return jsonify({'status': 'not ready', 'error': str(e)}), 503

Logging Configuration
^^^^^^^^^^^^^^^^^^^^^

Configure structured logging for production. See the :doc:`logging` page for detailed guidance.

.. code-block:: python

   import logging
   import json
   from datetime import datetime
   
   class JSONFormatter(logging.Formatter):
       """Format logs as JSON for structured logging systems."""
       
       def format(self, record):
           log_data = {
               'timestamp': datetime.utcnow().isoformat(),
               'level': record.levelname,
               'logger': record.name,
               'message': record.getMessage(),
           }
           
           if record.exc_info:
               log_data['exception'] = self.formatException(record.exc_info)
           
           return json.dumps(log_data)
   
   # Configure root logger
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.root.addHandler(handler)
   logging.root.setLevel(logging.INFO)

Metrics Collection
^^^^^^^^^^^^^^^^^^

Track key operational metrics:

.. code-block:: python

   from prometheus_client import Counter, Histogram, Gauge, start_http_server
   
   # Define metrics
   forecasts_generated = Counter(
       'openstef_forecasts_generated_total',
       'Total number of forecasts generated',
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
   
   def run_forecast_with_metrics(target_id: str):
       """Run forecast with Prometheus metrics."""
       with forecast_duration.labels(target_id=target_id).time():
           try:
               run_forecast(target_id)
               forecasts_generated.labels(target_id=target_id, status='success').inc()
           except Exception as e:
               forecasts_generated.labels(target_id=target_id, status='failure').inc()
               raise
   
   # Start metrics server
   start_http_server(8000)

Configuration Management
------------------------

Separate configuration from code using environment variables or configuration files:

.. code-block:: python

   import os
   from pathlib import Path
   from pydantic import BaseModel, Field
   
   class DeploymentConfig(BaseModel):
       """Production deployment configuration."""
       
       database_url: str = Field(..., description="Database connection string")
       model_storage_path: Path = Field(default=Path("/data/models"))
       log_level: str = Field(default="INFO")
       forecast_horizon_hours: int = Field(default=47)
       training_history_days: int = Field(default=30)
       max_workers: int = Field(default=4)
       
       @classmethod
       def from_env(cls):
           """Load configuration from environment variables."""
           return cls(
               database_url=os.environ["DATABASE_URL"],
               model_storage_path=Path(os.getenv("MODEL_STORAGE_PATH", "/data/models")),
               log_level=os.getenv("LOG_LEVEL", "INFO"),
               forecast_horizon_hours=int(os.getenv("FORECAST_HORIZON_HOURS", "47")),
               training_history_days=int(os.getenv("TRAINING_HISTORY_DAYS", "30")),
               max_workers=int(os.getenv("MAX_WORKERS", "4")),
           )

Error Handling and Retries
---------------------------

Implement robust error handling for production reliability:

.. code-block:: python

   from tenacity import retry, stop_after_attempt, wait_exponential
   import logging
   
   logger = logging.getLogger(__name__)
   
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=60),
       reraise=True
   )
   def run_forecast_with_retry(target_id: str):
       """Run forecast with automatic retries on failure."""
       try:
           return run_forecast(target_id)
       except Exception as e:
           logger.warning(f"Forecast attempt failed for {target_id}: {e}")
           raise

Performance Considerations
--------------------------

- **Parallel Processing**: Use multiprocessing or concurrent.futures to forecast multiple targets in parallel
- **Resource Limits**: Set memory and CPU limits appropriate for your workload
- **Model Caching**: Keep trained models in memory when processing multiple predictions
- **Batch Predictions**: Group predictions by model to minimize model loading overhead

See :doc:`data_integration` for patterns on efficiently loading data from various sources.

Related Topics
--------------

- :doc:`use_cases` - Common forecasting scenarios and implementation patterns
- :doc:`data_integration` - Loading data from databases, cloud storage, and time series databases
- :doc:`logging` - Detailed logging configuration for production environments
- :doc:`migration_v3_v4` - Upgrading existing deployments from OpenSTEF v3