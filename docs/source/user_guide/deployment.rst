Production Deployment
=====================

This page covers practical patterns for deploying OpenSTEF in production environments — from simple scheduled scripts to fully orchestrated pipelines. It focuses on the operational concerns that arise once you move beyond experimentation: scheduling, containerization, model persistence, and monitoring.

For related topics, see :doc:`data_integration` for connecting to production data sources, and :doc:`logging` for configuring structured logging in deployed workloads.

.. note::
   OpenSTEF is a **library**. It does not ship a server, daemon, or scheduler. You integrate it into whatever execution environment suits your infrastructure — a cron job, a container, a workflow orchestrator, or a cloud function.

Deployment Patterns
-------------------

There is no single correct way to deploy OpenSTEF. The right pattern depends on how many forecasting locations you manage, how frequently you retrain, and what infrastructure you already operate. The sections below cover three common approaches in increasing order of complexity.

**Simple scheduled script**
   Suitable for a small number of locations with infrequent retraining. A Python script wraps the training and prediction workflow and is triggered by cron or a cloud scheduler.

**Containerised job**
   Suitable when you want reproducible, isolated execution. The same script runs inside a Docker container, making it straightforward to deploy on Kubernetes, AWS ECS, Google Cloud Run, or Azure Container Instances.

**Workflow orchestration**
   Suitable for large fleets, complex dependency graphs, or when you need retries, observability, and backfill support. Tools like Dagster, Airflow, or Prefect schedule individual tasks and handle failures.

Structuring Your Forecasting Script
------------------------------------

Regardless of the scheduler, the core logic follows the same pattern: load data, run the workflow, persist results. The example below shows a minimal but production-ready structure using ``CustomForecastingWorkflow`` with MLflow-backed model storage.

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   import pandas as pd

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )
   from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage
   from openstef_models.integrations.mlflow.mlflow_storage_callback import (
       MLFlowStorageCallback,
   )
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Quantile as Q

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   TRACKING_URI = Path("/var/openstef/mlflow")
   ARTIFACTS_PATH = Path("/var/openstef/artifacts")
   MODEL_ID = "substation_amsterdam_001"


   def load_data() -> VersionedTimeSeriesDataset:
       # Replace with your data source — see the data_integration guide
       df = pd.read_parquet("/data/measurements/amsterdam_001.parquet")
       return VersionedTimeSeriesDataset(
           data=df,
           sample_interval=timedelta(minutes=15),
       )


   def build_workflow() -> CustomForecastingWorkflow:
       from openstef_models.pipelines.forecasting_pipeline_factory import (
           ForecastingPipelineFactory,
       )
       from openstef_models.pipelines.forecasting_pipeline_config import (
           ForecastingPipelineConfig,
       )

       config = ForecastingPipelineConfig(
           model_id=MODEL_ID,
           model="xgb",
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           mlflow_storage=MLFlowStorage(
               tracking_uri=str(TRACKING_URI),
               local_artifacts_path=ARTIFACTS_PATH,
           ),
       )
       return ForecastingPipelineFactory.build(config)


   def run_training(workflow: CustomForecastingWorkflow, dataset: VersionedTimeSeriesDataset):
       logger.info("Starting training for %s", MODEL_ID)
       result = workflow.fit(dataset)
       if result is not None:
           logger.info("Training complete. Metrics:\n%s", result.metrics_full.to_dataframe())


   def run_prediction(workflow: CustomForecastingWorkflow, dataset: VersionedTimeSeriesDataset):
       logger.info("Generating forecast for %s", MODEL_ID)
       forecast = workflow.predict(dataset)
       output_path = Path("/data/forecasts") / f"{MODEL_ID}.parquet"
       forecast.data.to_parquet(output_path)
       logger.info("Forecast written to %s", output_path)


   if __name__ == "__main__":
       dataset = load_data()
       workflow = build_workflow()
       run_training(workflow, dataset)
       run_prediction(workflow, dataset)

In practice you will likely separate training and prediction into distinct scheduled jobs — retraining weekly or daily, predicting every 15 minutes or hourly.

Model Persistence with MLflow
------------------------------

OpenSTEF's ``MLFlowStorageCallback`` handles model versioning automatically during training. When a new model is trained, it is compared against the previously stored model using the configured selection metric. The better model is retained, protecting production forecasts from regressions caused by a bad training run.

Key configuration options on ``MLFlowStorageCallback``:

- ``model_reuse_enable`` — skip retraining if the existing model is recent enough (controlled by ``model_reuse_max_age``, default 7 days).
- ``model_selection_enable`` — compare new and old models before promoting; uses ``model_selection_metric`` to decide.
- ``model_selection_old_model_penalty`` — a multiplier (default ``1.2``) that biases selection toward the newer model, so a new model only needs to be 83% as good as the old one to be promoted.

To load an existing model from storage without retraining:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import ForecastingWorkflow
   from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage

   storage = MLFlowStorage(
       tracking_uri="/var/openstef/mlflow",
       local_artifacts_path="/var/openstef/artifacts",
   )

   workflow = ForecastingWorkflow.from_storage(
       model_id="substation_amsterdam_001",
       storage=storage,
   )

   forecast = workflow.predict(dataset)

This pattern is useful in prediction-only jobs that run frequently and should never trigger a retrain.

Containerisation
-----------------

Packaging your forecasting job as a Docker container gives you a reproducible, portable execution unit. A minimal ``Dockerfile`` for an OpenSTEF-based job looks like this:

.. code-block:: dockerfile

   FROM python:3.12-slim

   WORKDIR /app

   # Install uv for fast dependency resolution
   RUN pip install uv

   COPY pyproject.toml uv.lock ./
   RUN uv sync --no-dev

   COPY forecast_job.py ./

   # Volumes for data and model storage are mounted at runtime
   VOLUME ["/data", "/var/openstef"]

   CMD ["uv", "run", "python", "forecast_job.py"]

A corresponding ``pyproject.toml`` declares the OpenSTEF packages you need:

.. code-block:: toml

   [project]
   name = "my-forecast-job"
   version = "1.0.0"
   requires-python = ">=3.12"
   dependencies = [
       "openstef-models",
       "openstef-core",
   ]

   [tool.uv]
   # Pin to a specific OpenSTEF release for production stability
   constraint-dependencies = [
       "openstef-models==4.x.y",
   ]

.. note::
   Mount ``/var/openstef`` as a persistent volume (or point it at object storage via a FUSE mount) so that MLflow tracking data and model artifacts survive container restarts.

Scheduling Options
-------------------

**Cron / system scheduler**

The simplest option. Add an entry to your system crontab or a cloud-native equivalent (AWS EventBridge Scheduler, Google Cloud Scheduler, Azure Logic Apps):

.. code-block:: bash

   # Retrain daily at 02:00
   0 2 * * * /usr/bin/docker run --rm \
       -v /data:/data \
       -v /var/openstef:/var/openstef \
       my-forecast-job:latest python forecast_job.py --mode train

   # Predict every 15 minutes
   */15 * * * * /usr/bin/docker run --rm \
       -v /data:/data \
       -v /var/openstef:/var/openstef \
       my-forecast-job:latest python forecast_job.py --mode predict

**Kubernetes CronJob**

For teams already running Kubernetes, a ``CronJob`` resource provides the same scheduling with built-in retries and log aggregation:

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
             restartPolicy: OnFailure
             containers:
               - name: forecast
                 image: my-registry/my-forecast-job:1.0.0
                 args: ["python", "forecast_job.py", "--mode", "predict"]
                 volumeMounts:
                   - name: data
                     mountPath: /data
                   - name: openstef-state
                     mountPath: /var/openstef
             volumes:
               - name: data
                 persistentVolumeClaim:
                   claimName: forecast-data-pvc
               - name: openstef-state
                 persistentVolumeClaim:
                   claimName: openstef-state-pvc

Set ``concurrencyPolicy: Forbid`` to prevent overlapping prediction runs if a job takes longer than its schedule interval.

**Workflow orchestrators (Dagster, Airflow, Prefect)**

For larger deployments — many substations, complex dependencies between training and prediction, or the need for backfill — a workflow orchestrator gives you task-level observability and retry logic. Wrap each OpenSTEF call (data loading, training, prediction, result writing) in its own task or op so failures are isolated and retryable without re-running the entire pipeline.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Monitoring and Alerting
------------------------

OpenSTEF does not ship a monitoring dashboard, but it provides the hooks you need to feed your existing observability stack.

**Forecast quality metrics**

After each training run, ``ModelFitResult.metrics_full`` and ``metrics_test`` contain evaluation metrics (R², MAE, etc.) broken down by lead time and time window. Log these to your metrics backend or to MLflow so you can track model drift over time:

.. code-block:: python

   result = workflow.fit(dataset)
   if result is not None:
       metrics_df = result.metrics_full.to_dataframe()
       # Emit to your metrics system, e.g. Prometheus pushgateway,
       # Datadog statsd, or simply log for ingestion by your log aggregator
       for _, row in metrics_df.iterrows():
           logger.info(
               "forecast_metric",
               extra={
                   "model_id": MODEL_ID,
                   "metric": row["metric"],
                   "value": row["value"],
                   "lead_time": str(row["lead_time"]),
               },
           )

**Callbacks for custom instrumentation**

Implement ``ForecastingCallback`` to hook into workflow lifecycle events without modifying the core logic. This is the recommended way to emit custom metrics or trigger alerts:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       ForecastingCallback,
       WorkflowContext,
   )

   class MetricsEmitterCallback(ForecastingCallback):
       def on_fit_end(self, context: WorkflowContext, result) -> None:
           if result is None:
               # Model was reused — no new metrics to emit
               return
           r2 = result.metrics_test.to_dataframe().query("metric == 'R2'")["value"].mean()
           if r2 < 0.7:
               logger.warning(
                   "Model quality below threshold",
                   extra={"model_id": context.workflow.model_id, "r2": r2},
               )
           # Push to your metrics system here

       def on_predict_end(self, context: WorkflowContext, data, result) -> None:
           logger.info(
               "Forecast generated",
               extra={
                   "model_id": context.workflow.model_id,
                   "n_rows": len(result.data),
               },
           )

Pass the callback when constructing the workflow:

.. code-block:: python

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id=MODEL_ID,
       callbacks=[MLFlowStorageCallback(...), MetricsEmitterCallback()],
   )

**Health checks**

For long-running services or orchestrators that poll for job health, a simple check is to verify that the most recent forecast output file is newer than the expected interval:

.. code-block:: python

   from pathlib import Path
   from datetime import datetime, timedelta

   def check_forecast_freshness(model_id: str, max_age: timedelta) -> bool:
       output = Path(f"/data/forecasts/{model_id}.parquet")
       if not output.exists():
           return False
       age = datetime.now() - datetime.fromtimestamp(output.stat().st_mtime)
       return age < max_age

See :doc:`logging` for guidance on configuring structured log output, which makes it straightforward to route job logs to Elasticsearch, Loki, or CloudWatch for alerting.

Environment Configuration
--------------------------

Avoid hard-coding paths and credentials in your script. Use environment variables for anything that changes between environments:

.. code-block:: python

   import os
   from pathlib import Path

   MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "/var/openstef/mlflow")
   MLFLOW_ARTIFACTS_PATH = Path(os.environ.get("MLFLOW_ARTIFACTS_PATH", "/var/openstef/artifacts"))
   DATA_PATH = Path(os.environ.get("OPENSTEF_DATA_PATH", "/data"))
   MODEL_ID = os.environ["OPENSTEF_MODEL_ID"]  # Required — fail fast if missing

Pass these at runtime via your scheduler, Kubernetes ``env`` fields, or a ``.env`` file. For cloud deployments, use your platform's secrets manager (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) to inject credentials rather than baking them into the container image.

.. note::
   For S3, Databricks, or InfluxDB data sources, see :doc:`data_integration` for the connection patterns that pair with the deployment structures shown here.