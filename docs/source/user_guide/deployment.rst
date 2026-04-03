Production Deployment
=====================

OpenSTEF is a Python library for short-term energy forecasting. Deploying it to production means integrating it into your operational infrastructure—whether that's a simple scheduled job, a containerized service, or a full orchestration platform. This page covers practical deployment patterns, containerization strategies, cloud deployment options, and monitoring setup.

Deployment Approaches
---------------------

The right deployment approach depends on your operational requirements, infrastructure, and scale.

Simple Scheduled Jobs
^^^^^^^^^^^^^^^^^^^^^^

For many use cases, a scheduled job running on a timer is sufficient. This approach works well when:

- Forecasts are needed at regular intervals (e.g., every 15 minutes or hourly)
- Training happens less frequently (e.g., daily or weekly)
- You have modest computational requirements
- Your infrastructure already has job scheduling capabilities

**Using cron:**

.. code-block:: bash

   # Run predictions every 15 minutes
   */15 * * * * /path/to/venv/bin/python /path/to/forecast_job.py

   # Retrain models daily at 2 AM
   0 2 * * * /path/to/venv/bin/python /path/to/training_job.py

**Example prediction job:**

.. code-block:: python

   """Simple scheduled prediction job."""
   import logging
   from datetime import datetime, timedelta
   from pathlib import Path

   from openstef_core.data import VersionedTimeSeriesDataset
   from openstef_models.forecasting_model import ForecastingModel
   from openstef_models.model_storage import LocalModelStorage

   # Configure logging (see logging page for details)
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   logger = logging.getLogger(__name__)

   def run_prediction():
       """Execute a single prediction run."""
       try:
           # Load model from storage
           storage = LocalModelStorage(base_path=Path("/models"))
           model = storage.load_model(model_id="grid_123")
           
           # Load recent data (see data_integration page)
           data = load_recent_data(hours=48)  # Your data loading function
           
           # Make prediction
           prediction = model.predict(data)
           
           # Save results
           save_prediction(prediction)  # Your storage function
           
           logger.info("Prediction completed successfully")
           
       except Exception as e:
           logger.error(f"Prediction failed: {e}", exc_info=True)
           raise

   if __name__ == "__main__":
       run_prediction()

**Using systemd timers (Linux):**

.. code-block:: ini

   # /etc/systemd/system/openstef-forecast.service
   [Unit]
   Description=OpenSTEF Forecasting Job
   After=network.target

   [Service]
   Type=oneshot
   User=openstef
   WorkingDirectory=/opt/openstef
   Environment="PATH=/opt/openstef/venv/bin"
   ExecStart=/opt/openstef/venv/bin/python forecast_job.py
   StandardOutput=journal
   StandardError=journal

.. code-block:: ini

   # /etc/systemd/system/openstef-forecast.timer
   [Unit]
   Description=Run OpenSTEF forecasts every 15 minutes

   [Timer]
   OnBootSec=5min
   OnUnitActiveSec=15min
   AccuracySec=1s

   [Install]
   WantedBy=timers.target

Orchestration Platforms
^^^^^^^^^^^^^^^^^^^^^^^^

For more complex workflows with dependencies, retries, and monitoring, use an orchestration platform.

**Apache Airflow example:**

.. code-block:: python

   """Airflow DAG for OpenSTEF forecasting workflow."""
   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator

   def train_model(**context):
       """Train forecasting model."""
       from openstef_models.forecasting_model import ForecastingModel
       from openstef_models.model_storage import LocalModelStorage
       
       # Load training data
       data = load_training_data()  # Your data function
       
       # Create and train model
       model = ForecastingModel.from_config(config_path="config.yaml")
       model.fit(data)
       
       # Save trained model
       storage = LocalModelStorage(base_path="/models")
       storage.save_model(model, model_id="grid_123")

   def generate_forecast(**context):
       """Generate forecast using trained model."""
       from openstef_models.forecasting_model import ForecastingModel
       from openstef_models.model_storage import LocalModelStorage
       
       storage = LocalModelStorage(base_path="/models")
       model = storage.load_model(model_id="grid_123")
       
       data = load_recent_data()
       prediction = model.predict(data)
       
       save_prediction(prediction)

   default_args = {
       'owner': 'energy-team',
       'depends_on_past': False,
       'start_date': datetime(2024, 1, 1),
       'email_on_failure': True,
       'email_on_retry': False,
       'retries': 2,
       'retry_delay': timedelta(minutes=5),
   }

   with DAG(
       'openstef_forecasting',
       default_args=default_args,
       description='Energy forecasting with OpenSTEF',
       schedule_interval='*/15 * * * *',
       catchup=False,
   ) as dag:

       train_task = PythonOperator(
           task_id='train_model',
           python_callable=train_model,
           # Run training daily at 2 AM
           trigger_rule='all_success',
       )

       forecast_task = PythonOperator(
           task_id='generate_forecast',
           python_callable=generate_forecast,
       )

       train_task >> forecast_task

**Dagster example:**

.. code-block:: python

   """Dagster pipeline for OpenSTEF."""
   from dagster import asset, job, schedule, Definitions
   from datetime import datetime

   @asset
   def trained_model():
       """Train and persist forecasting model."""
       from openstef_models.forecasting_model import ForecastingModel
       from openstef_models.model_storage import LocalModelStorage
       
       model = ForecastingModel.from_config(config_path="config.yaml")
       data = load_training_data()
       model.fit(data)
       
       storage = LocalModelStorage(base_path="/models")
       storage.save_model(model, model_id="grid_123")
       
       return {"model_id": "grid_123", "trained_at": datetime.now()}

   @asset(deps=[trained_model])
   def forecast():
       """Generate forecast from trained model."""
       from openstef_models.model_storage import LocalModelStorage
       
       storage = LocalModelStorage(base_path="/models")
       model = storage.load_model(model_id="grid_123")
       
       data = load_recent_data()
       prediction = model.predict(data)
       
       save_prediction(prediction)
       return {"forecast_generated_at": datetime.now()}

   @schedule(cron_schedule="*/15 * * * *", job_name="forecast_job")
   def forecast_schedule():
       return {}

   defs = Definitions(
       assets=[trained_model, forecast],
       schedules=[forecast_schedule],
   )

Containerization
----------------

Containerizing OpenSTEF provides reproducible deployments and simplifies dependency management.

Docker Setup
^^^^^^^^^^^^

**Basic Dockerfile:**

.. code-block:: dockerfile

   FROM python:3.11-slim

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       g++ \
       && rm -rf /var/lib/apt/lists/*

   # Set working directory
   WORKDIR /app

   # Copy requirements and install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY . .

   # Create directory for model storage
   RUN mkdir -p /models

   # Run as non-root user
   RUN useradd -m -u 1000 openstef && chown -R openstef:openstef /app /models
   USER openstef

   # Default command
   CMD ["python", "forecast_job.py"]

**requirements.txt:**

.. code-block:: text

   openstef-core>=4.0.0
   openstef-models>=4.0.0
   openstef-beam>=4.0.0
   pandas>=2.0.0
   # Add your data connectors
   boto3>=1.28.0  # For S3
   # Add monitoring libraries
   prometheus-client>=0.19.0

**Build and run:**

.. code-block:: bash

   # Build image
   docker build -t openstef-forecast:latest .

   # Run prediction job
   docker run --rm \
     -v /path/to/models:/models \
     -v /path/to/config:/config \
     -e LOG_LEVEL=INFO \
     openstef-forecast:latest

**Multi-stage build for smaller images:**

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
   COPY --from=builder /root/.local /root/.local
   COPY . .

   ENV PATH=/root/.local/bin:$PATH
   RUN mkdir -p /models && \
       useradd -m -u 1000 openstef && \
       chown -R openstef:openstef /app /models

   USER openstef
   CMD ["python", "forecast_job.py"]

Docker Compose for Local Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   version: '3.8'

   services:
     forecast:
       build: .
       volumes:
         - ./models:/models
         - ./config:/config
         - ./data:/data
       environment:
         - LOG_LEVEL=INFO
         - MODEL_STORAGE_PATH=/models
       command: python forecast_job.py

     training:
       build: .
       volumes:
         - ./models:/models
         - ./config:/config
         - ./data:/data
       environment:
         - LOG_LEVEL=INFO
         - MODEL_STORAGE_PATH=/models
       command: python training_job.py

     # Optional: Prometheus for monitoring
     prometheus:
       image: prom/prometheus:latest
       ports:
         - "9090:9090"
       volumes:
         - ./prometheus.yml:/etc/prometheus/prometheus.yml
         - prometheus-data:/prometheus

   volumes:
     prometheus-data:

Cloud Deployment
----------------

Cloud platforms provide managed infrastructure for running OpenSTEF at scale.

AWS Deployment
^^^^^^^^^^^^^^

**Using AWS Batch for scheduled jobs:**

.. code-block:: python

   """AWS Batch job definition."""
   import boto3

   batch = boto3.client('batch')

   # Submit job
   response = batch.submit_job(
       jobName='openstef-forecast',
       jobQueue='energy-forecasting-queue',
       jobDefinition='openstef-forecast-job:1',
       containerOverrides={
           'environment': [
               {'name': 'MODEL_ID', 'value': 'grid_123'},
               {'name': 'S3_BUCKET', 'value': 'my-forecasts'},
           ],
       },
   )

**Using ECS with EventBridge for scheduling:**

.. code-block:: json

   {
     "containerDefinitions": [
       {
         "name": "openstef-forecast",
         "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/openstef:latest",
         "memory": 2048,
         "cpu": 1024,
         "environment": [
           {"name": "MODEL_STORAGE_PATH", "value": "/models"},
           {"name": "LOG_LEVEL", "value": "INFO"}
         ],
         "mountPoints": [
           {
             "sourceVolume": "efs-models",
             "containerPath": "/models"
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
     ],
     "volumes": [
       {
         "name": "efs-models",
         "efsVolumeConfiguration": {
           "fileSystemId": "fs-12345678"
         }
       }
     ]
   }

Azure Deployment
^^^^^^^^^^^^^^^^

**Using Azure Container Instances with Logic Apps for scheduling:**

.. code-block:: bash

   # Deploy container instance
   az container create \
     --resource-group openstef-rg \
     --name openstef-forecast \
     --image myregistry.azurecr.io/openstef:latest \
     --cpu 2 \
     --memory 4 \
     --environment-variables \
       LOG_LEVEL=INFO \
       MODEL_STORAGE_PATH=/models \
     --azure-file-volume-account-name mystorageaccount \
     --azure-file-volume-account-key $STORAGE_KEY \
     --azure-file-volume-share-name models \
     --azure-file-volume-mount-path /models

**Using Azure Functions for event-driven forecasting:**

.. code-block:: python

   """Azure Function for OpenSTEF forecasting."""
   import azure.functions as func
   import logging

   def main(timer: func.TimerRequest) -> None:
       """Timer-triggered forecast generation."""
       logging.info('Starting forecast generation')
       
       from openstef_models.forecasting_model import ForecastingModel
       from openstef_models.model_storage import LocalModelStorage
       
       storage = LocalModelStorage(base_path="/models")
       model = storage.load_model(model_id="grid_123")
       
       data = load_recent_data()
       prediction = model.predict(data)
       
       save_to_blob_storage(prediction)
       
       logging.info('Forecast generation completed')

GCP Deployment
^^^^^^^^^^^^^^

**Using Cloud Run with Cloud Scheduler:**

.. code-block:: bash

   # Deploy to Cloud Run
   gcloud run deploy openstef-forecast \
     --image gcr.io/my-project/openstef:latest \
     --platform managed \
     --region us-central1 \
     --memory 2Gi \
     --cpu 2 \
     --no-allow-unauthenticated \
     --set-env-vars LOG_LEVEL=INFO,MODEL_STORAGE_PATH=/models

   # Create scheduled job
   gcloud scheduler jobs create http openstef-forecast-job \
     --schedule="*/15 * * * *" \
     --uri="https://openstef-forecast-xxxxx.run.app/forecast" \
     --http-method=POST \
     --oidc-service-account-email=scheduler@my-project.iam.gserviceaccount.com

Kubernetes Deployment
^^^^^^^^^^^^^^^^^^^^^

**CronJob for scheduled forecasting:**

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
             - name: forecast
               image: myregistry.io/openstef:latest
               env:
               - name: LOG_LEVEL
                 value: "INFO"
               - name: MODEL_STORAGE_PATH
                 value: "/models"
               volumeMounts:
               - name: models
                 mountPath: /models
               resources:
                 requests:
                   memory: "2Gi"
                   cpu: "1000m"
                 limits:
                   memory: "4Gi"
                   cpu: "2000m"
             volumes:
             - name: models
               persistentVolumeClaim:
                 claimName: openstef-models-pvc
             restartPolicy: OnFailure

Configuration Management
------------------------

Externalize configuration for different environments.

**Environment variables:**

.. code-block:: python

   """Load configuration from environment."""
   import os
   from pathlib import Path

   CONFIG = {
       'model_storage_path': Path(os.getenv('MODEL_STORAGE_PATH', '/models')),
       'log_level': os.getenv('LOG_LEVEL', 'INFO'),
       'data_source': os.getenv('DATA_SOURCE', 's3'),
       's3_bucket': os.getenv('S3_BUCKET'),
       'model_id': os.getenv('MODEL_ID', 'default'),
   }

**Configuration files:**

.. code-block:: yaml

   # config/production.yaml
   model:
     storage_path: /models
     id: grid_123
   
   data:
     source: s3
     bucket: production-forecasts
     region: us-east-1
   
   logging:
     level: INFO
     format: json
   
   monitoring:
     prometheus_port: 8000
     health_check_port: 8080

Monitoring and Health Checks
-----------------------------

Production deployments need observability to detect and diagnose issues.

Health Check Endpoint
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   """Simple health check for containerized deployments."""
   from http.server import HTTPServer, BaseHTTPRequestHandler
   import threading
   import logging

   logger = logging.getLogger(__name__)

   class HealthCheckHandler(BaseHTTPRequestHandler):
       def do_GET(self):
           if self.path == '/health':
               self.send_response(200)
               self.send_header('Content-type', 'application/json')
               self.end_headers()
               self.wfile.write(b'{"status": "healthy"}')
           elif self.path == '/ready':
               # Check if model is loaded
               try:
                   # Your readiness check logic
                   self.send_response(200)
                   self.wfile.write(b'{"status": "ready"}')
               except Exception as e:
                   self.send_response(503)
                   self.wfile.write(f'{{"status": "not ready", "error": "{e}"}}'.encode())

   def start_health_server(port=8080):
       """Start health check server in background thread."""
       server = HTTPServer(('', port), HealthCheckHandler)
       thread = threading.Thread(target=server.serve_forever, daemon=True)
       thread.start()
       logger.info(f"Health check server started on port {port}")

Prometheus Metrics
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   """Expose Prometheus metrics for monitoring."""
   from prometheus_client import Counter, Histogram, Gauge, start_http_server
   import time

   # Define metrics
   predictions_total = Counter(
       'openstef_predictions_total',
       'Total number of predictions made',
       ['model_id', 'status']
   )

   prediction_duration = Histogram(
       'openstef_prediction_duration_seconds',
       'Time spent generating predictions',
       ['model_id']
   )

   model_age = Gauge(
       'openstef_model_age_seconds',
       'Age of the loaded model in seconds',
       ['model_id']
   )

   def run_prediction_with_metrics(model_id: str):
       """Run prediction with metric collection."""
       start_time = time.time()
       
       try:
           # Your prediction logic
           result = generate_forecast(model_id)
           
           predictions_total.labels(model_id=model_id, status='success').inc()
           return result
           
       except Exception as e:
           predictions_total.labels(model_id=model_id, status='error').inc()
           raise
           
       finally:
           duration = time.time() - start_time
           prediction_duration.labels(model_id=model_id).observe(duration)

   # Start Prometheus metrics server
   start_http_server(8000)

Logging in Production
^^^^^^^^^^^^^^^^^^^^^

See the :doc:`logging` page for detailed logging configuration. Key considerations for production:

- Use structured logging (JSON format) for easier parsing
- Set appropriate log levels (INFO or WARNING in production)
- Configure log rotation to prevent disk space issues
- Send logs to centralized logging systems (CloudWatch, Stackdriver, etc.)

.. code-block:: python

   """Production logging configuration."""
   import logging
   import json
   from datetime import datetime

   class JSONFormatter(logging.Formatter):
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

   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.root.addHandler(handler)
   logging.root.setLevel(logging.INFO)

Best Practices
--------------

**Resource management:**

- Set appropriate CPU and memory limits based on your data volume
- Monitor resource usage and adjust as needed
- Use horizontal scaling for high-frequency predictions

**Error handling:**

- Implement retry logic with exponential backoff
- Log errors with sufficient context for debugging
- Set up alerts for critical failures

**Model versioning:**

- Tag models with version information
- Keep multiple model versions for rollback capability
- Test new models in staging before production deployment

**Security:**

- Run containers as non-root users
- Use secrets management for credentials (AWS Secrets Manager, Azure Key Vault, etc.)
- Restrict network access to necessary services only
- Keep dependencies updated for security patches

**Testing:**

- Test deployment configurations in staging environments
- Validate model loading and prediction generation
- Monitor initial production deployments closely

Next Steps
----------

- See :doc:`data_integration` for connecting to data sources
- See :doc:`logging` for detailed logging configuration
- See :doc:`use_cases` for complete application examples