Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production, from simple
cron-based scheduled jobs to fully orchestrated pipelines. It assumes you are
comfortable with the library's core workflows — if not, review the use cases page
first (see :doc:`use_cases`).

Because OpenSTEF is a Python library rather than a standalone application, it
integrates naturally into whatever execution environment you already use. The
deployment patterns described here are not prescriptive; they are starting points
you can adapt to your infrastructure.

.. note:: [DIAGRAM: High-level deployment topology showing a scheduler triggering a Python process that loads data, runs a workflow, and writes results to storage and a monitoring backend.]

Scheduling Approaches
---------------------

The simplest production setup is a Python script executed on a schedule. OpenSTEF
workflows are plain Python objects, so any scheduler that can run a script works.

**Cron / system scheduler**

The most portable option. A single entry in a crontab is enough to run a recurring
forecast:

.. code-block:: bash

   # Run the forecast every hour at minute 5
   5 * * * * /opt/venv/bin/python /opt/openstef/run_forecast.py >> /var/log/openstef.log 2>&1

The script itself is straightforward:

.. code-block:: python

   # run_forecast.py
   import logging
   from datetime import datetime

   from openstef_models.workflows import CustomForecastingWorkflow

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   def main():
       logger.info("Forecast run started at %s", datetime.utcnow().isoformat())

       # Load your fitted workflow from storage (see data_integration for storage patterns)
       workflow = CustomForecastingWorkflow.from_storage(
           model_id="substation_a_v1",
           storage=your_storage_backend,
           default_model_factory=lambda: create_default_model(),
       )

       data = load_latest_features()          # your data-loading logic
       forecasts = workflow.predict(data)
       save_forecasts(forecasts)              # your persistence logic

       logger.info("Forecast run completed successfully")

   if __name__ == "__main__":
       main()

**Apache Airflow / Prefect / Dagster**

For teams that already use a workflow orchestrator, wrapping OpenSTEF calls in
tasks or operators is straightforward. The key principle is to keep the OpenSTEF
code inside a plain Python callable — the orchestrator handles retries, alerting,
and dependency management.

.. code-block:: python

   # Example Airflow task using the TaskFlow API
   from airflow.decorators import dag, task
   from datetime import datetime

   @dag(schedule="@hourly", start_date=datetime(2024, 1, 1), catchup=False)
   def openstef_forecast_dag():

       @task()
       def run_forecast():
           from openstef_models.workflows import CustomForecastingWorkflow

           workflow = CustomForecastingWorkflow.from_storage(
               model_id="substation_a_v1",
               storage=build_storage(),
               default_model_factory=create_default_model,
           )
           data = load_features()
           return workflow.predict(data)

       @task()
       def persist_results(forecasts):
           save_forecasts(forecasts)

       persist_results(run_forecast())

   openstef_forecast_dag()

Separating training runs (typically daily or weekly) from prediction runs (hourly
or sub-hourly) is a common pattern. Both are independent workflow invocations and
can be scheduled independently.

Containerization
----------------

Packaging OpenSTEF and your application code in a container image makes deployments
reproducible and simplifies dependency management.

A minimal ``Dockerfile`` for an OpenSTEF service:

.. code-block:: dockerfile

   FROM python:3.12-slim

   WORKDIR /app

   # Install uv for fast dependency resolution
   RUN pip install uv

   COPY pyproject.toml uv.lock ./
   RUN uv sync --no-dev

   COPY src/ ./src/

   CMD ["uv", "run", "python", "-m", "openstef_service.run_forecast"]

A matching ``pyproject.toml`` dependency section:

.. code-block:: toml

   [project]
   name = "openstef-service"
   version = "0.1.0"
   requires-python = ">=3.12"
   dependencies = [
       "openstef-models",
       "openstef-core",
   ]

.. note::

   Keep model artefacts out of the image. Mount them from object storage or a
   shared volume at runtime. This keeps images small and lets you update models
   without rebuilding.

For local development and testing of the containerised service, a minimal
``docker-compose.yml`` is useful:

.. code-block:: yaml

   services:
     forecast:
       build: .
       environment:
         - MODEL_STORAGE_URI=s3://my-bucket/models
         - INFLUX_URL=http://influxdb:8086
       volumes:
         - ./config:/app/config:ro
       depends_on:
         - influxdb

     influxdb:
       image: influxdb:2.7
       ports:
         - "8086:8086"

Cloud Deployment Options
------------------------

OpenSTEF has no cloud-specific dependencies; the choice of cloud platform is driven
by your data infrastructure. The following patterns are common.

**Kubernetes CronJob**

For teams running Kubernetes, a ``CronJob`` resource mirrors the cron approach but
adds resource limits, restart policies, and centralised logging:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
   spec:
     schedule: "5 * * * *"
     jobTemplate:
       spec:
         template:
           spec:
             restartPolicy: OnFailure
             containers:
               - name: forecast
                 image: your-registry/openstef-service:latest
                 resources:
                   requests:
                     memory: "512Mi"
                     cpu: "500m"
                   limits:
                     memory: "2Gi"
                     cpu: "2"
                 env:
                   - name: MODEL_STORAGE_URI
                     valueFrom:
                       secretKeyRef:
                         name: openstef-secrets
                         key: model-storage-uri

**Serverless functions**

Short-lived prediction runs (a few seconds) fit well in serverless environments
such as AWS Lambda or Azure Functions. Training runs are typically too long and
memory-intensive for serverless; use a container-based job for those.

**Managed ML platforms**

If your organisation uses a managed ML platform (Azure ML, AWS SageMaker, Vertex
AI), you can register OpenSTEF workflows as pipeline steps. The library's
``CustomForecastingWorkflow`` and ``CustomComponentSplitWorkflow`` are plain Python
objects with no framework-specific coupling, so they slot into any pipeline SDK.

Monitoring and Observability
-----------------------------

OpenSTEF's callback system is the primary integration point for production
monitoring. Both ``CustomForecastingWorkflow`` and ``CustomComponentSplitWorkflow``
accept a ``callbacks`` argument that receives lifecycle events at each stage of
training and prediction.

.. code-block:: python

   import logging
   import time
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback
   from openstef_core.base_model import BaseModel

   logger = logging.getLogger(__name__)

   class ObservabilityCallback(BaseModel, ForecastingCallback):
       """Emit structured log lines and timing metrics at each workflow stage."""

       _fit_start_time: float = 0.0

       def on_fit_start(self, context, data):
           self._fit_start_time = time.monotonic()
           logger.info(
               "fit_start",
               extra={"model_id": context.workflow.model_id, "n_samples": len(data.data)},
           )

       def on_fit_end(self, context, result):
           elapsed = time.monotonic() - self._fit_start_time
           logger.info(
               "fit_end",
               extra={
                   "model_id": context.workflow.model_id,
                   "duration_seconds": round(elapsed, 2),
               },
           )

       def on_predict_start(self, context, data):
           logger.info(
               "predict_start",
               extra={"model_id": context.workflow.model_id},
           )

       def on_predict_end(self, context, data, result):
           logger.info(
               "predict_end",
               extra={
                   "model_id": context.workflow.model_id,
                   "n_forecasts": len(result.data),
               },
           )

   workflow = CustomForecastingWorkflow(
       model=your_model,
       model_id="substation_a_v1",
       callbacks=ObservabilityCallback(),
   )

The callback receives a ``WorkflowContext`` that exposes the workflow instance,
giving you access to the model ID and any other metadata you attached. Because
``ForecastingCallback`` provides no-op defaults for all methods, you only need to
override the hooks you care about.

**Structured logging**

Pair the callback above with a JSON log formatter so that log aggregation tools
(Elasticsearch, Loki, CloudWatch Logs) can index the ``extra`` fields. See
:doc:`logging` for configuration details.

**Health checks**

For long-running services (e.g., a FastAPI wrapper around a workflow), expose a
``/health`` endpoint that verifies the model is loaded and fitted:

.. code-block:: python

   from fastapi import FastAPI, HTTPException
   from openstef_core.exceptions import NotFittedError

   app = FastAPI()

   @app.get("/health")
   def health():
       if not workflow.model.is_fitted:
           raise HTTPException(status_code=503, detail="Model not fitted")
       return {"status": "ok", "model_id": workflow.model_id}

Configuration Management
------------------------

Hard-coding connection strings and model identifiers in scripts is fragile.
A common pattern is to load configuration from environment variables at startup:

.. code-block:: python

   import os
   from dataclasses import dataclass

   @dataclass
   class Config:
       model_id: str = os.environ["OPENSTEF_MODEL_ID"]
       storage_uri: str = os.environ["OPENSTEF_STORAGE_URI"]
       log_level: str = os.environ.get("OPENSTEF_LOG_LEVEL", "INFO")
       run_name: str = os.environ.get("OPENSTEF_RUN_NAME", "default")

   cfg = Config()

For Kubernetes deployments, populate these variables from ``ConfigMap`` and
``Secret`` resources rather than baking them into the image.

.. note::

   The ``with_run_name`` method on ``CustomForecastingWorkflow`` lets you tag a
   workflow run with an identifier (e.g., a deployment version or experiment name),
   which is useful when multiple versions are running in parallel during a rollout.

   .. code-block:: python

      workflow = workflow.with_run_name(cfg.run_name)

Related Pages
-------------

- :doc:`data_integration` — connecting to S3, Databricks, InfluxDB, and other
  data sources from within your deployment scripts.
- :doc:`logging` — configuring structured logging and log levels for production
  environments.
- :doc:`use_cases` — end-to-end examples showing how training and prediction
  workflows are assembled before deployment.