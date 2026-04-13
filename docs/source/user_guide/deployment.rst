Production Deployment
=====================

This page covers practical patterns for deploying OpenSTEF in production environments — from simple scheduled scripts to fully orchestrated pipelines running in the cloud. OpenSTEF is a library, so the deployment topology is entirely yours to define; these patterns are starting points, not prescriptions.

For data source configuration (S3, Databricks, InfluxDB), see :doc:`data_integration`. For logging setup, see :doc:`logging`.

.. note:: [DIAGRAM: Deployment topology overview — scheduled job / orchestrator → OpenSTEF workflow → model storage → forecast sink]

Deployment Patterns
-------------------

There are three common ways to run OpenSTEF in production, each suited to different operational maturity levels:

- **Cron / scheduled script** — simplest option; a Python script executed on a timer. Good for single-node setups or quick pilots.
- **Workflow orchestrator** (Dagster, Airflow, Prefect) — adds dependency management, retries, observability, and backfill support. Recommended for production.
- **Cloud-native / serverless** — containerised tasks triggered by cloud schedulers (AWS EventBridge + ECS, Azure Container Apps, GCP Cloud Run). Best for elastic scaling.

All three patterns use the same OpenSTEF API; only the outer wrapper changes.

Scheduled Script (Cron)
-----------------------

The simplest production deployment is a Python script invoked by ``cron`` or a system timer. The script loads data, runs the workflow, and writes forecasts back to a sink.

.. code-block:: python

   # forecast_job.py
   import logging
   from datetime import timedelta
   from pathlib import Path

   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting.xgb_forecaster import XGBForecaster
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.workflow import CustomForecastingWorkflow
   from openstef_models.storage.local import LocalModelStorage

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)


   def load_data() -> VersionedTimeSeriesDataset:
       # Replace with your actual data source — see the data_integration guide
       df = pd.read_parquet("s3://my-bucket/features/latest.parquet")
       return VersionedTimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))


   def write_forecasts(forecasts) -> None:
       forecasts.data.to_parquet("s3://my-bucket/forecasts/latest.parquet")


   def main():
       storage = LocalModelStorage(base_path=Path("/opt/models"))
       workflow = CustomForecastingWorkflow.from_storage(
           model_id="grid_east_load",
           storage=storage,
       )

       dataset = load_data()
       forecasts = workflow.predict(dataset)
       write_forecasts(forecasts)
       logger.info("Forecast complete — %d rows written", len(forecasts.data))


   if __name__ == "__main__":
       main()

A matching crontab entry to run this every hour:

.. code-block:: bash

   0 * * * * /opt/venv/bin/python /opt/jobs/forecast_job.py >> /var/log/openstef/forecast.log 2>&1

.. note::

   Cron gives no retry logic or alerting out of the box. For anything beyond a pilot, consider an orchestrator (see below) or at minimum wrap the script in a shell that sends an alert on non-zero exit codes.

Orchestrator Integration (Dagster)
-----------------------------------

Orchestrators add retries, scheduling, data lineage, and a UI without requiring you to change the OpenSTEF code itself. The example below uses Dagster, but the same pattern applies to Airflow (as a ``PythonOperator``) or Prefect (as a ``@flow``).

.. code-block:: python

   # openstef_dagster/assets.py
   from datetime import timedelta
   from pathlib import Path

   from dagster import asset, AssetExecutionContext, EnvVar
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.models.workflow import CustomForecastingWorkflow
   from openstef_models.storage.local import LocalModelStorage


   @asset(
       description="Hourly load forecast for the eastern grid zone",
       group_name="forecasting",
   )
   def eastern_zone_forecast(context: AssetExecutionContext):
       model_dir = Path(EnvVar("MODEL_STORAGE_PATH").get_value())
       storage = LocalModelStorage(base_path=model_dir)

       workflow = CustomForecastingWorkflow.from_storage(
           model_id="grid_east_load",
           storage=storage,
       )

       dataset = _load_features()          # your data loading logic
       forecasts = workflow.predict(dataset)

       context.log.info("Produced %d forecast rows", len(forecasts.data))
       return forecasts.data


   def _load_features() -> VersionedTimeSeriesDataset:
       import pandas as pd
       df = pd.read_parquet(EnvVar("FEATURE_PATH").get_value())
       return VersionedTimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Dagster's asset model makes it straightforward to chain training and prediction jobs with explicit data dependencies, so a nightly retraining asset can automatically trigger the prediction asset once it completes.

Containerisation
----------------

Packaging OpenSTEF jobs as Docker containers ensures reproducibility across environments and is a prerequisite for most cloud deployment options.

A minimal ``Dockerfile`` for a forecast job:

.. code-block:: dockerfile

   FROM python:3.12-slim

   WORKDIR /app

   # Install uv for fast dependency resolution
   RUN pip install --no-cache-dir uv

   COPY pyproject.toml uv.lock ./
   RUN uv sync --no-dev --frozen

   COPY forecast_job.py ./

   # Models and config are mounted or pulled at runtime — not baked in
   ENV MODEL_STORAGE_PATH=/mnt/models

   CMD [".venv/bin/python", "forecast_job.py"]

And a matching ``pyproject.toml`` dependency block:

.. code-block:: toml

   [project]
   name = "my-forecast-service"
   requires-python = ">=3.12"
   dependencies = [
       "openstef-models",
       "openstef-core",
   ]

.. note::

   Keep model artefacts out of the image. Mount them from shared storage (NFS, S3 FUSE, Azure Files) or pull them at startup. This keeps images small and lets you update models without rebuilding.

Cloud Deployment Options
------------------------

Because OpenSTEF is a library, it runs wherever Python runs. The table below summarises common cloud patterns:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Platform
     - Pattern
     - Notes
   * - AWS
     - ECS Fargate task triggered by EventBridge Scheduler
     - Model artefacts on S3; secrets via Secrets Manager
   * - Azure
     - Azure Container Apps Job on a CRON schedule
     - Model artefacts on Azure Blob Storage; config via Key Vault references
   * - GCP
     - Cloud Run Job triggered by Cloud Scheduler
     - Model artefacts on GCS; config via Secret Manager
   * - Kubernetes
     - ``CronJob`` resource running the forecast container
     - Works on any managed Kubernetes (EKS, AKS, GKE)

All of these follow the same structure: a container runs the Python job, reads model artefacts from object storage, writes forecasts to a sink, and exits. The cloud scheduler handles timing and retries.

Example: AWS ECS Fargate task definition (excerpt)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "family": "openstef-forecast",
     "containerDefinitions": [
       {
         "name": "forecast",
         "image": "123456789.dkr.ecr.eu-west-1.amazonaws.com/openstef-forecast:latest",
         "environment": [
           {"name": "MODEL_STORAGE_PATH", "value": "/mnt/models"},
           {"name": "FEATURE_PATH",       "value": "s3://my-bucket/features/latest.parquet"}
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group":  "/ecs/openstef-forecast",
             "awslogs-region": "eu-west-1",
             "awslogs-stream-prefix": "forecast"
           }
         }
       }
     ]
   }

Configuration Management
------------------------

Hard-coding paths and credentials in scripts is fragile. Prefer environment variables for deployment-specific settings and a structured config object for model parameters.

.. code-block:: python

   import os
   from dataclasses import dataclass
   from pathlib import Path


   @dataclass
   class ForecastJobConfig:
       model_id: str
       model_storage_path: Path
       feature_path: str
       forecast_sink: str
       log_level: str = "INFO"

       @classmethod
       def from_env(cls) -> "ForecastJobConfig":
           return cls(
               model_id=os.environ["MODEL_ID"],
               model_storage_path=Path(os.environ["MODEL_STORAGE_PATH"]),
               feature_path=os.environ["FEATURE_PATH"],
               forecast_sink=os.environ["FORECAST_SINK"],
               log_level=os.environ.get("LOG_LEVEL", "INFO"),
           )

This pattern makes the job easy to test locally (set env vars in a ``.env`` file) and straightforward to configure in any container orchestration system.

Monitoring and Alerting
-----------------------

OpenSTEF's ``ForecastingCallback`` interface is the primary hook for production observability. You can attach callbacks to log metrics, push to monitoring systems, or raise alerts without modifying workflow logic.

.. code-block:: python

   from openstef_models.models.callbacks import ForecastingCallback


   class PrometheusMetricsCallback(ForecastingCallback):
       """Push forecast quality metrics to a Prometheus pushgateway."""

       def on_predict_end(self, pipeline, dataset, forecasts):
           row_count = len(forecasts.data)
           null_count = forecasts.data.isnull().sum().sum()

           # Replace with your actual metrics client
           push_metric("openstef_forecast_rows_total", row_count)
           push_metric("openstef_forecast_null_values_total", null_count)

           if null_count > 0:
               logger.warning(
                   "Forecast contains %d null values — check input data quality",
                   null_count,
               )

       def on_fit_end(self, context, result):
           push_metric("openstef_model_training_completed_total", 1)

Attach the callback when constructing the workflow:

.. code-block:: python

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="grid_east_load",
       callbacks=[PrometheusMetricsCallback()],
   )

Beyond custom callbacks, a few operational checks are worth building into any production deployment:

- **Input data freshness** — assert that the most recent timestamp in the feature dataset is within an expected window before calling ``predict``. Stale inputs produce stale forecasts silently.
- **Forecast row count** — verify the output has the expected number of rows and lead times.
- **Model age** — log when the model was last trained; alert if it exceeds a threshold (e.g., 30 days without retraining).
- **Exit codes** — ensure the job script exits non-zero on any unhandled exception so the scheduler or orchestrator can detect and retry failures.

For structured log configuration and log-level management, see :doc:`logging`.

MLflow Integration
------------------

When using MLflow for model tracking, the ``MLFlowStorageCallback`` handles run logging automatically. In production, point it at a shared MLflow tracking server rather than a local file store:

.. code-block:: python

   import mlflow
   from openstef_models.callbacks.mlflow import MLFlowStorageCallback
   from openstef_models.storage.mlflow import MLFlowModelStorage

   mlflow.set_tracking_uri("https://mlflow.internal.example.com")

   storage = MLFlowModelStorage(tracking_uri="https://mlflow.internal.example.com")
   callbacks = [
       MLFlowStorageCallback(
           storage=storage,
           model_reuse_enable=True,
           model_reuse_max_age=30,        # days
           model_selection_enable=True,
       )
   ]

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="grid_east_load",
       callbacks=callbacks,
   )

This gives you a full audit trail of every training run, metric history, and the ability to roll back to a previous model version if a new one degrades in production.

Summary
-------

The key principle for deploying OpenSTEF is that it is a library — you own the runner. Start with the simplest pattern that meets your reliability requirements (a cron job is often enough), containerise early to ensure environment consistency, and add an orchestrator when you need retries, backfills, or multi-job dependencies. Use callbacks to integrate with your existing monitoring stack without coupling OpenSTEF to any specific observability platform.

- For data source wiring, see :doc:`data_integration`.
- For structured logging configuration, see :doc:`logging`.
- For real-world use case walkthroughs, see :doc:`use_cases`.