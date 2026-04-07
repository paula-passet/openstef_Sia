Production Deployment
=====================

This page covers patterns for deploying OpenSTEF in production environments. Since OpenSTEF is a library---not a standalone application---deployment means integrating its forecasting workflows into your own infrastructure. You decide how to schedule training and prediction, where to store models, and how to monitor the system.

For data source integration, see :doc:`data_integration`. For logging configuration, see :doc:`logging`.

.. contents:: On this page
   :local:
   :depth: 2

Core Concepts
-------------

A production deployment of OpenSTEF typically involves two recurring tasks:

- **Training**: Periodically retrain models on fresh data (e.g., daily or weekly).
- **Prediction**: Generate forecasts on a regular schedule (e.g., every 15 minutes).

Both tasks use the ``ForecastingWorkflow`` from ``openstef-models``, which orchestrates preprocessing, model fitting, and postprocessing. The workflow stores trained models via MLflow, so your deployment must provide an MLflow tracking server or a compatible storage backend.

.. code-block:: python

   from openstef_models.forecasting import ForecastingWorkflow, ForecastingWorkflowConfig
   from openstef_models.integrations.mlflow import MLFlowStorage
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.quantiles import Q
   from pathlib import Path

   # Configure the workflow once; reuse across train and predict
   config = ForecastingWorkflowConfig(
       model_id="solar_farm_01",
       horizons=[0.25, 0.5, 1.0, 4.0, 24.0, 48.0],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       mlflow_storage=MLFlowStorage(
           tracking_uri="http://mlflow.internal:5000",
           local_artifacts_path=Path("/tmp/mlflow_artifacts"),
       ),
   )

   workflow = ForecastingWorkflow(config)

Simple Scheduled Jobs
---------------------

The most straightforward deployment is a cron job or systemd timer that runs a Python script. This works well for small-scale deployments with a handful of prediction jobs.

**Example: cron-based training and prediction**

.. code-block:: python

   # train.py — Run daily via cron
   import logging
   from my_project.data import load_training_data
   from my_project.workflow import create_workflow

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   def main():
       workflow = create_workflow()
       dataset = load_training_data()

       result = workflow.fit(dataset)
       if result is not None:
           logger.info("Training complete. Metrics: %s", result.metrics_full.to_dataframe())
       else:
           logger.warning("Training returned no result (possible flatliner)")

   if __name__ == "__main__":
       main()

.. code-block:: python

   # predict.py — Run every 15 minutes via cron
   import logging
   from my_project.data import load_recent_data, store_forecast
   from my_project.workflow import create_workflow

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   def main():
       workflow = create_workflow()
       dataset = load_recent_data()

       forecast = workflow.predict(dataset)
       store_forecast(forecast)
       logger.info("Forecast generated: %d rows", len(forecast.data))

   if __name__ == "__main__":
       main()

The corresponding crontab entries:

.. code-block:: text

   # Retrain daily at 02:00
   0 2 * * * /opt/openstef/venv/bin/python /opt/openstef/train.py >> /var/log/openstef/train.log 2>&1

   # Predict every 15 minutes
   */15 * * * * /opt/openstef/venv/bin/python /opt/openstef/predict.py >> /var/log/openstef/predict.log 2>&1

Containerization
----------------

Packaging your forecasting scripts in a Docker container ensures reproducible environments and simplifies deployment across different platforms.

**Dockerfile**

.. code-block:: dockerfile

   FROM python:3.12-slim

   WORKDIR /app

   # Install system dependencies for scientific packages
   RUN apt-get update && apt-get install -y --no-install-recommends \
       build-essential \
       && rm -rf /var/lib/apt/lists/*

   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY src/ ./src/

   # Default entrypoint — override with "train" or "predict"
   ENTRYPOINT ["python", "-m", "src.main"]

**requirements.txt**

.. code-block:: text

   openstef-models>=4.0.0
   openstef-core>=4.0.0
   mlflow>=2.0

**Entry point with subcommands**

.. code-block:: python

   # src/main.py
   import sys
   from src.train import run_training
   from src.predict import run_prediction

   def main():
       if len(sys.argv) < 2:
           print("Usage: python -m src.main [train|predict]")
           sys.exit(1)

       command = sys.argv[1]
       if command == "train":
           run_training()
       elif command == "predict":
           run_prediction()
       else:
           print(f"Unknown command: {command}")
           sys.exit(1)

   if __name__ == "__main__":
       main()

Build and run:

.. code-block:: bash

   docker build -t openstef-forecast:latest .
   docker run --rm openstef-forecast:latest train
   docker run --rm openstef-forecast:latest predict

Workflow Orchestration
----------------------

For production systems managing multiple prediction jobs, a workflow orchestrator provides scheduling, retries, dependency management, and monitoring. OpenSTEF integrates naturally with any Python-compatible orchestrator.

Apache Airflow
^^^^^^^^^^^^^^

.. code-block:: python

   # dags/openstef_forecast.py
   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator

   default_args = {
       "owner": "energy-team",
       "retries": 2,
       "retry_delay": timedelta(minutes=5),
   }

   def train_model(**kwargs):
       from my_project.workflow import create_workflow
       from my_project.data import load_training_data

       workflow = create_workflow()
       dataset = load_training_data()
       result = workflow.fit(dataset)
       return result is not None

   def run_prediction(**kwargs):
       from my_project.workflow import create_workflow
       from my_project.data import load_recent_data, store_forecast

       workflow = create_workflow()
       dataset = load_recent_data()
       forecast = workflow.predict(dataset)
       store_forecast(forecast)

   with DAG(
       "openstef_forecast",
       default_args=default_args,
       schedule_interval="*/15 * * * *",
       start_date=datetime(2024, 1, 1),
       catchup=False,
   ) as dag:

       predict_task = PythonOperator(
           task_id="run_prediction",
           python_callable=run_prediction,
       )

   # Separate DAG for training (daily)
   with DAG(
       "openstef_training",
       default_args=default_args,
       schedule_interval="0 2 * * *",
       start_date=datetime(2024, 1, 1),
       catchup=False,
   ) as training_dag:

       train_task = PythonOperator(
           task_id="train_model",
           python_callable=train_model,
       )

Prefect / Dagster
^^^^^^^^^^^^^^^^^

The same pattern applies to other orchestrators. Wrap your OpenSTEF workflow calls in the orchestrator's task/op abstraction:

.. code-block:: python

   # Example with Prefect
   from prefect import flow, task
   from prefect.tasks import task_input_hash
   from datetime import timedelta

   @task(retries=2, cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
   def load_data():
       from my_project.data import load_recent_data
       return load_recent_data()

   @task(retries=1)
   def generate_forecast(dataset):
       from my_project.workflow import create_workflow
       workflow = create_workflow()
       return workflow.predict(dataset)

   @task
   def store_results(forecast):
       from my_project.data import store_forecast
       store_forecast(forecast)

   @flow(name="openstef-prediction")
   def prediction_flow():
       dataset = load_data()
       forecast = generate_forecast(dataset)
       store_results(forecast)

Cloud Deployment
----------------

OpenSTEF's library design makes it portable across cloud platforms. Below are common patterns for major providers.

.. list-table:: Cloud Deployment Options
   :header-rows: 1
   :widths: 20 30 50

   * - Provider
     - Service
     - Best For
   * - AWS
     - Lambda, ECS, SageMaker
     - Serverless prediction, containerized training
   * - Azure
     - Functions, Container Apps, ML
     - Event-driven forecasting, managed ML
   * - GCP
     - Cloud Run, Cloud Functions, Vertex AI
     - Autoscaling containers, managed pipelines

**Kubernetes CronJob**

For container-orchestrated environments, a Kubernetes CronJob is a natural fit:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-predict
   spec:
     schedule: "*/15 * * * *"
     concurrencyPolicy: Forbid
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: forecast
               image: openstef-forecast:latest
               args: ["predict"]
               env:
               - name: MLFLOW_TRACKING_URI
                 value: "http://mlflow.internal:5000"
               resources:
                 requests:
                   memory: "512Mi"
                   cpu: "500m"
                 limits:
                   memory: "2Gi"
                   cpu: "2000m"
             restartPolicy: OnFailure
         backoffLimit: 3

MLflow Configuration
--------------------

OpenSTEF uses MLflow for model storage, versioning, and experiment tracking. In production, you should run a dedicated MLflow tracking server rather than using local file storage.

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage
   from pathlib import Path

   # Production: remote tracking server with S3 artifact store
   mlflow_storage = MLFlowStorage(
       tracking_uri="http://mlflow.internal:5000",
       local_artifacts_path=Path("/tmp/mlflow_cache"),
   )

   # Development: local tracking
   mlflow_storage = MLFlowStorage(
       tracking_uri="file:///home/user/mlflow_tracking",
       local_artifacts_path=Path("./mlflow_artifacts"),
   )

.. note::

   MLflow supports multiple artifact backends including S3, Azure Blob Storage, GCS, and HDFS. Configure the MLflow server's ``--default-artifact-root`` to match your cloud storage.

Monitoring and Health Checks
----------------------------

Production deployments need monitoring to detect issues early. Since OpenSTEF is a library, monitoring is your responsibility, but there are clear patterns to follow.

**Key metrics to track:**

- Forecast generation latency
- Training duration and success rate
- Prediction error metrics (MAE, RMSE) from evaluation results
- Flatliner detection events
- Data freshness (time since last input data point)

**Structured logging for observability**

.. code-block:: python

   import logging
   import time
   import json

   logger = logging.getLogger("openstef.production")

   def run_prediction_with_monitoring(workflow, dataset):
       start_time = time.time()

       try:
           forecast = workflow.predict(dataset)
           duration = time.time() - start_time

           logger.info(
               json.dumps({
                   "event": "prediction_complete",
                   "duration_seconds": round(duration, 2),
                   "forecast_rows": len(forecast.data),
                   "model_id": workflow.config.model_id,
               })
           )
           return forecast

       except Exception as e:
           duration = time.time() - start_time
           logger.error(
               json.dumps({
                   "event": "prediction_failed",
                   "duration_seconds": round(duration, 2),
                   "error": str(e),
                   "model_id": workflow.config.model_id,
               })
           )
           raise

**Health check endpoint** (if running as a long-lived service):

.. code-block:: python

   from http.server import HTTPServer, BaseHTTPRequestHandler
   import threading
   import json

   class HealthHandler(BaseHTTPRequestHandler):
       last_prediction_time = None
       last_prediction_success = False

       def do_GET(self):
           if self.path == "/health":
               status = {
                   "status": "healthy" if self.last_prediction_success else "degraded",
                   "last_prediction": str(self.last_prediction_time),
               }
               self.send_response(200)
               self.send_header("Content-Type", "application/json")
               self.end_headers()
               self.wfile.write(json.dumps(status).encode())

   def start_health_server(port=8080):
       server = HTTPServer(("", port), HealthHandler)
       thread = threading.Thread(target=server.serve_forever, daemon=True)
       thread.start()
       return server

For detailed logging configuration including log levels and custom handlers, see :doc:`logging`.

Scaling Considerations
----------------------

When deploying OpenSTEF for many prediction jobs, keep these patterns in mind:

- **Separate training from prediction**: Training is resource-intensive and infrequent. Run it on larger instances or dedicated hardware. Prediction is lightweight and frequent.
- **Parallelize by model**: Each ``ForecastingWorkflow`` instance is independent. Run multiple prediction jobs in parallel using your orchestrator's concurrency controls.
- **Use model reuse**: The MLflow integration supports skipping retraining if a recent model exists. Configure ``model_reuse_enable`` in your workflow config to avoid unnecessary training runs.
- **Right-size containers**: Prediction typically needs 512MB--2GB RAM. Training may need 4--8GB depending on dataset size and model complexity.
- **Cache data aggressively**: If multiple models consume the same weather data, load it once and share across workflows rather than fetching repeatedly.

.. warning::

   OpenSTEF's ``ForecastingWorkflow`` is not thread-safe. If you need concurrent predictions, use separate workflow instances per thread or process, not a shared instance.