Production Deployment
=====================

OpenSTEF is a Python library — it does not ship with a server, daemon, or scheduler. Deploying OpenSTEF in production means writing a small application that calls the library's APIs on a schedule, wiring it to your data sources, and deciding how to persist models and surface forecasts. This page covers the most common patterns for doing that, from a simple cron job to a full container-based orchestration setup.

For data integration patterns (reading from S3, Databricks, InfluxDB, etc.) see :doc:`data_integration`. For logging configuration see :doc:`logging`.

.. note:: [DIAGRAM: High-level deployment topology showing a scheduler triggering a Python process that calls OpenSTEF train/predict APIs, reads from a data store, writes models to model storage, and writes forecasts to an output sink.]


The Core Loop
-------------

Every OpenSTEF deployment, regardless of platform, reduces to the same two operations repeated on a schedule:

1. **Train** — periodically retrain the model on fresh historical data.
2. **Predict** — frequently generate forecasts using the current model.

``CustomForecastingWorkflow`` is the primary entry point for both. It combines a ``ForecastingModel`` with lifecycle callbacks and optional model persistence, and exposes a ``fit`` / ``predict`` interface that is safe to call from any scheduler:

.. code-block:: python

   import logging
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.workflows import CustomForecastingWorkflow

   logger = logging.getLogger(__name__)

   def run_predict(workflow: CustomForecastingWorkflow, data: pd.DataFrame) -> pd.DataFrame:
       """Single predict cycle — call this from your scheduler."""
       dataset = TimeSeriesDataset(data=data, target_column="load")
       forecast = workflow.predict(data=dataset)
       return forecast.data

   def run_train(workflow: CustomForecastingWorkflow, data: pd.DataFrame) -> None:
       """Single train cycle — call this less frequently than predict."""
       dataset = TimeSeriesDataset(data=data, target_column="load")
       result = workflow.fit(data=dataset)
       if result is not None:
           logger.info("Training complete. Metrics: %s", result.metrics_to_flat_dict())

The workflow's callback system lets you attach monitoring, alerting, and storage logic without modifying this core loop. See the `Monitoring`_ section below for examples.


Scheduling Approaches
---------------------

Simple Cron Job
^^^^^^^^^^^^^^^

The lowest-overhead deployment is a Python script invoked by the operating system scheduler. This is appropriate for a single forecasting target with modest data volumes.

.. code-block:: python

   #!/usr/bin/env python
   # forecast_job.py — invoked by cron every 15 minutes

   import logging
   import sys
   from pathlib import Path

   import pandas as pd

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.workflows import CustomForecastingWorkflow

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s %(name)s %(levelname)s %(message)s",
   )
   logger = logging.getLogger(__name__)

   WORKFLOW_PATH = Path("/var/openstef/models/substation_a")


   def load_recent_data() -> pd.DataFrame:
       # Replace with your data source — see the data_integration guide
       return pd.read_parquet("/var/openstef/data/recent.parquet")


   def write_forecast(forecast: pd.DataFrame) -> None:
       forecast.to_parquet("/var/openstef/forecasts/latest.parquet")


   def main() -> int:
       workflow = CustomForecastingWorkflow.load(WORKFLOW_PATH)  # load persisted workflow
       data = load_recent_data()
       forecast = workflow.predict(
           data=TimeSeriesDataset(data=data, target_column="load")
       )
       write_forecast(forecast.data)
       logger.info("Forecast written (%d rows)", len(forecast.data))
       return 0


   if __name__ == "__main__":
       sys.exit(main())

A matching crontab entry:

.. code-block:: text

   # Predict every 15 minutes; retrain nightly at 02:00
   */15 * * * *  openstef-user /usr/local/bin/python /opt/openstef/forecast_job.py
   0    2 * * *  openstef-user /usr/local/bin/python /opt/openstef/train_job.py

.. note::

   Keep train and predict jobs as separate scripts. Training is expensive and
   should run far less frequently (daily or weekly). Mixing them in a single
   script couples their failure modes unnecessarily.

Dagster / Prefect / Airflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For multiple forecasting targets or complex dependency graphs, a workflow orchestrator gives you retries, observability, and dependency management out of the box. OpenSTEF integrates naturally because each ``fit`` / ``predict`` call is a pure Python function with no hidden state beyond the workflow object.

The pattern below shows a Dagster op, but the same structure applies to any orchestrator:

.. code-block:: python

   # dagster_jobs.py
   from dagster import op, job, ScheduleDefinition, Out, In
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.workflows import CustomForecastingWorkflow

   @op(out=Out(CustomForecastingWorkflow))
   def train_model(context) -> CustomForecastingWorkflow:
       workflow = CustomForecastingWorkflow.load(context.op_config["model_path"])
       data = _load_training_data(context.op_config["data_path"])
       workflow.fit(data=TimeSeriesDataset(data=data, target_column="load"))
       workflow.save(context.op_config["model_path"])
       return workflow

   @op(ins={"workflow": In(CustomForecastingWorkflow)})
   def generate_forecast(context, workflow: CustomForecastingWorkflow) -> None:
       data = _load_recent_data(context.op_config["data_path"])
       forecast = workflow.predict(
           data=TimeSeriesDataset(data=data, target_column="load")
       )
       _write_forecast(forecast.data, context.op_config["output_path"])

   @job
   def forecasting_pipeline():
       generate_forecast(train_model())

   daily_schedule = ScheduleDefinition(job=forecasting_pipeline, cron_schedule="0 2 * * *")

The key advantage here is that the orchestrator handles retries, alerting, and run history — OpenSTEF simply provides the forecasting logic.


Containerization
----------------

Packaging OpenSTEF in a container makes deployments reproducible and portable across cloud environments.

Dockerfile
^^^^^^^^^^

.. code-block:: docker

   FROM python:3.11-slim

   WORKDIR /app

   # Install OpenSTEF and its dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY forecast_job.py train_job.py ./

   # Model and data directories are mounted at runtime
   VOLUME ["/var/openstef/models", "/var/openstef/data", "/var/openstef/forecasts"]

   # Default command runs the predict job; override for training
   CMD ["python", "forecast_job.py"]

A minimal ``requirements.txt``:

.. code-block:: text

   openstef-core>=4.0
   openstef-models>=4.0
   pandas>=2.0
   pyarrow>=14.0

Running the container with a bind-mounted model directory:

.. code-block:: bash

   # Predict
   docker run --rm \
     -v /data/openstef/models:/var/openstef/models:ro \
     -v /data/openstef/data:/var/openstef/data:ro \
     -v /data/openstef/forecasts:/var/openstef/forecasts \
     openstef-forecast:latest

   # Train (override CMD)
   docker run --rm \
     -v /data/openstef/models:/var/openstef/models \
     -v /data/openstef/data:/var/openstef/data:ro \
     openstef-forecast:latest python train_job.py

Docker Compose for Local Testing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   # docker-compose.yml
   version: "3.9"
   services:
     forecast:
       build: .
       volumes:
         - ./models:/var/openstef/models
         - ./data:/var/openstef/data
         - ./forecasts:/var/openstef/forecasts
       environment:
         - LOG_LEVEL=INFO
       restart: "no"

     train:
       build: .
       command: python train_job.py
       volumes:
         - ./models:/var/openstef/models
         - ./data:/var/openstef/data


Cloud Deployment Options
------------------------

Kubernetes CronJob
^^^^^^^^^^^^^^^^^^

On Kubernetes, a ``CronJob`` resource maps directly to the cron pattern described above. Models are typically stored on a ``PersistentVolumeClaim`` or in object storage (S3/GCS/Azure Blob — see :doc:`data_integration`).

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
                 image: your-registry/openstef-forecast:latest
                 command: ["python", "forecast_job.py"]
                 env:
                   - name: MODEL_PATH
                     value: "/mnt/models/substation_a"
                   - name: LOG_LEVEL
                     value: "INFO"
                 volumeMounts:
                   - name: model-storage
                     mountPath: /mnt/models
             volumes:
               - name: model-storage
                 persistentVolumeClaim:
                   claimName: openstef-models-pvc
             restartPolicy: OnFailure

Serverless (AWS Lambda / Azure Functions)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Serverless functions work well for predict jobs because they are short-lived and stateless. The model is loaded from object storage on each invocation. Training jobs are generally too long-running for serverless and are better suited to a container or VM.

.. code-block:: python

   # lambda_handler.py (AWS Lambda)
   import os
   import boto3
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.workflows import CustomForecastingWorkflow

   s3 = boto3.client("s3")
   MODEL_BUCKET = os.environ["MODEL_BUCKET"]
   MODEL_KEY = os.environ["MODEL_KEY"]


   def handler(event, context):
       # Download model artifact from S3 to /tmp (Lambda ephemeral storage)
       local_path = "/tmp/model"
       s3.download_file(MODEL_BUCKET, MODEL_KEY, local_path)

       workflow = CustomForecastingWorkflow.load(local_path)
       data = _fetch_recent_data()  # implement for your data source
       forecast = workflow.predict(
           data=TimeSeriesDataset(data=data, target_column="load")
       )
       _write_forecast(forecast.data)
       return {"statusCode": 200, "rows": len(forecast.data)}

.. note::

   Lambda has a 512 MB ``/tmp`` limit by default (extendable to 10 GB). For
   large models, prefer EFS mounts or load the model from S3 using a streaming
   loader rather than downloading to disk.


Monitoring
----------

OpenSTEF's callback system is the recommended way to add monitoring to a production workflow. Implement ``ForecastingCallback`` and attach it to your ``CustomForecastingWorkflow``:

.. code-block:: python

   import logging
   from datetime import datetime
   from openstef_models.workflows import ForecastingCallback, CustomForecastingWorkflow
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validated_datasets import ForecastDataset
   from openstef_models.models.forecasting_model import ModelFitResult

   logger = logging.getLogger(__name__)


   class ProductionMonitoringCallback(ForecastingCallback):
       """Emit structured log lines and push metrics to your monitoring stack."""

       def on_fit_end(
           self,
           context: WorkflowContext,
           result: ModelFitResult,
       ) -> None:
           metrics = result.metrics_to_flat_dict()
           logger.info(
               "Training complete",
               extra={
                   "model_id": str(context.workflow.model_id),
                   "run_name": context.workflow.run_name,
                   "metrics": metrics,
               },
           )
           # Push to your metrics backend here (Prometheus, Datadog, etc.)

       def on_predict_end(
           self,
           context: WorkflowContext,
           data: TimeSeriesDataset,
           forecasts: ForecastDataset,
       ) -> None:
           n_rows = len(forecasts.data)
           n_nulls = forecasts.data.isnull().sum().sum()
           logger.info(
               "Forecast generated: %d rows, %d nulls", n_rows, n_nulls
           )
           if n_nulls > 0:
               logger.warning(
                   "Forecast contains %d null values — check input data quality", n_nulls
               )


   # Attach the callback when constructing the workflow
   workflow = CustomForecastingWorkflow(
       model=my_forecasting_model,
       callbacks=[ProductionMonitoringCallback()],
   )

MLflow Integration
^^^^^^^^^^^^^^^^^^

For experiment tracking and model versioning, OpenSTEF provides ``MLFlowStorageCallback`` out of the box. Attach it alongside your custom callback:

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorageCallback, MLFlowStorage

   mlflow_callback = MLFlowStorageCallback(
       storage=MLFlowStorage(tracking_uri="http://mlflow.internal:5000"),
       model_reuse_enable=True,
       model_reuse_max_age_days=7,
       model_selection_enable=True,
   )

   workflow = CustomForecastingWorkflow(
       model=my_forecasting_model,
       callbacks=[ProductionMonitoringCallback(), mlflow_callback],
   )

``MLFlowStorageCallback`` handles model saving on ``on_fit_end``, model loading on ``on_predict_start`` (when no in-memory model is available), and logs metrics and feature importance plots automatically.

Health Checks
^^^^^^^^^^^^^

For containerized deployments behind a load balancer or Kubernetes liveness probe, expose a lightweight health endpoint. Because OpenSTEF is a library, you wire this yourself:

.. code-block:: python

   # health.py — minimal HTTP health check using the standard library
   from http.server import BaseHTTPRequestHandler, HTTPServer
   import threading
   import json
   from pathlib import Path

   MODEL_PATH = Path("/var/openstef/models/substation_a")

   class HealthHandler(BaseHTTPRequestHandler):
       def do_GET(self):
           if self.path == "/health":
               model_exists = MODEL_PATH.exists()
               status = 200 if model_exists else 503
               body = json.dumps({"model_present": model_exists}).encode()
               self.send_response(status)
               self.send_header("Content-Type", "application/json")
               self.end_headers()
               self.wfile.write(body)

   def start_health_server(port: int = 8080) -> None:
       server = HTTPServer(("", port), HealthHandler)
       thread = threading.Thread(target=server.serve_forever, daemon=True)
       thread.start()

Start ``start_health_server()`` at the top of your job script before the main loop.


Configuration Management
------------------------

Avoid hardcoding paths, credentials, or hyperparameters in your job scripts. The standard approach is environment variables, optionally loaded from a ``.env`` file in development:

.. code-block:: python

   import os
   from pathlib import Path

   # Deployment configuration — set these in your container environment or secret manager
   MODEL_PATH = Path(os.environ.get("OPENSTEF_MODEL_PATH", "/var/openstef/models"))
   DATA_PATH = Path(os.environ.get("OPENSTEF_DATA_PATH", "/var/openstef/data"))
   LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
   MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "")

In Kubernetes, inject these via ``ConfigMap`` for non-sensitive values and ``Secret`` for credentials. In cloud functions, use the platform's environment variable or secrets manager integration.

.. note::

   Never store model artifacts or forecast outputs inside the container image.
   Mount them from external storage so that the image remains stateless and
   can be replaced without data loss.


Summary
-------

The table below summarises when to choose each deployment pattern:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Pattern
     - Best for
     - Key consideration
   * - Cron job
     - Single target, low ops overhead
     - No retry logic; failures are silent unless you add alerting
   * - Orchestrator (Dagster/Airflow)
     - Multiple targets, complex dependencies
     - Additional infrastructure to operate
   * - Kubernetes CronJob
     - Container-first environments
     - Requires a running cluster; PVC or object storage for models
   * - Serverless
     - Predict-only, infrequent invocations
     - Cold-start latency; training jobs need a different mechanism

Regardless of platform, the pattern is always the same: load data, call ``workflow.fit`` or ``workflow.predict``, write results. OpenSTEF handles the forecasting; your deployment code handles the scheduling, I/O, and monitoring wiring.