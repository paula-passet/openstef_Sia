Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from simple
scheduled scripts to fully orchestrated pipelines. It addresses containerization,
cloud deployment, and monitoring, so that you can move from a working prototype to a
reliable, repeatable forecasting service.

For data connectivity (S3, Databricks, InfluxDB) see :doc:`data_integration`. For
logging configuration see :doc:`logging`.

.. note::

   OpenSTEF is a **library**, not a server or application. Every deployment pattern
   described here is simply a way to call OpenSTEF's Python API on a schedule or in
   response to events. You own the orchestration layer; OpenSTEF owns the forecasting
   logic.

The Core Loop
-------------

Regardless of the deployment platform, a production OpenSTEF job performs the same
two operations on a schedule:

1. **Train** — periodically retrain the model on fresh historical data.
2. **Predict** — frequently generate forecasts from the latest model.

A minimal, self-contained script that implements this loop looks like the following:

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   import pandas as pd

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting.xgb_forecaster import XGBForecaster
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.workflow import CustomForecastingWorkflow
   from openstef_models.storage import LocalModelStorage

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   MODEL_DIR = Path("/var/openstef/models")
   MODEL_ID = "substation_42"

   def load_data() -> VersionedTimeSeriesDataset:
       """Replace with your data source (see data_integration docs)."""
       df = pd.read_parquet("/data/load_history.parquet")
       return VersionedTimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

   def run_train():
       logger.info("Starting training run for %s", MODEL_ID)
       dataset = load_data()
       horizons = [LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")]
       model = ForecastingModel(
           forecaster=XGBForecaster(horizons=horizons, quantiles=[Q(0.1), Q(0.5), Q(0.9)])
       )
       storage = LocalModelStorage(base_path=MODEL_DIR)
       workflow = CustomForecastingWorkflow(
           model=model, model_id=MODEL_ID, storage=storage
       )
       workflow.fit(dataset)
       logger.info("Training complete, model saved to %s", MODEL_DIR / MODEL_ID)

   def run_predict():
       logger.info("Starting prediction run for %s", MODEL_ID)
       dataset = load_data()
       storage = LocalModelStorage(base_path=MODEL_DIR)
       workflow = CustomForecastingWorkflow.from_storage(
           model_id=MODEL_ID, storage=storage
       )
       forecasts = workflow.predict(dataset)
       forecasts.data.to_parquet("/data/forecasts_latest.parquet")
       logger.info("Wrote %d forecast rows", len(forecasts.data))

   if __name__ == "__main__":
       import sys
       if sys.argv[1] == "train":
           run_train()
       elif sys.argv[1] == "predict":
           run_predict()

This script is the foundation for every pattern below. The only thing that changes
between deployment approaches is *how* and *when* this script is invoked.

Scheduled Jobs (Cron / Systemd)
--------------------------------

The simplest production setup is a cron job or a systemd timer. This is appropriate
when you have a single host, a small number of prediction points, and no need for
parallelism.

A typical schedule runs training once per day (overnight, when load is low) and
prediction every 15 minutes to keep forecasts fresh:

.. code-block:: bash

   # /etc/cron.d/openstef
   # Retrain daily at 02:00
   0 2 * * *  openstef  /opt/openstef/venv/bin/python /opt/openstef/job.py train

   # Predict every 15 minutes
   */15 * * * *  openstef  /opt/openstef/venv/bin/python /opt/openstef/job.py predict

.. note::

   Cron does not handle overlapping runs. If a training job takes longer than
   expected it can collide with the next invocation. Use a lock file or ``flock``
   to guard against this:

   .. code-block:: bash

      */15 * * * *  openstef  flock -n /tmp/openstef_predict.lock \
          /opt/openstef/venv/bin/python /opt/openstef/job.py predict

Containerization with Docker
-----------------------------

Packaging OpenSTEF in a container makes the environment reproducible and simplifies
deployment to any container runtime (Docker, Podman, Kubernetes, cloud run services).

A minimal ``Dockerfile``:

.. code-block:: dockerfile

   FROM python:3.11-slim

   WORKDIR /app

   # Install dependencies first for layer caching
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY job.py .

   # Models and data are mounted at runtime — do not bake them into the image
   VOLUME ["/var/openstef/models", "/data"]

   ENTRYPOINT ["python", "job.py"]
   CMD ["predict"]

A matching ``requirements.txt`` pins the OpenSTEF packages:

.. code-block:: text

   openstef-core>=4.0,<5.0
   openstef-models>=4.0,<5.0
   pandas>=2.0
   pyarrow>=14.0

Build and run locally:

.. code-block:: bash

   docker build -t openstef-job:latest .

   # Train
   docker run --rm \
     -v /host/models:/var/openstef/models \
     -v /host/data:/data \
     openstef-job:latest train

   # Predict
   docker run --rm \
     -v /host/models:/var/openstef/models \
     -v /host/data:/data \
     openstef-job:latest predict

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Kubernetes CronJob
------------------

On Kubernetes, a ``CronJob`` resource replaces the host-level cron entry. The
following manifest schedules the prediction job every 15 minutes:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-predict
     namespace: forecasting
   spec:
     schedule: "*/15 * * * *"
     concurrencyPolicy: Forbid          # prevents overlapping runs
     successfulJobsHistoryLimit: 3
     failedJobsHistoryLimit: 5
     jobTemplate:
       spec:
         template:
           spec:
             restartPolicy: OnFailure
             containers:
               - name: openstef-job
                 image: your-registry/openstef-job:latest
                 args: ["predict"]
                 env:
                   - name: LOG_LEVEL
                     value: "INFO"
                 volumeMounts:
                   - name: model-store
                     mountPath: /var/openstef/models
                   - name: data-store
                     mountPath: /data
             volumes:
               - name: model-store
                 persistentVolumeClaim:
                   claimName: openstef-models-pvc
               - name: data-store
                 persistentVolumeClaim:
                   claimName: openstef-data-pvc

A separate ``CronJob`` with ``schedule: "0 2 * * *"`` and ``args: ["train"]``
handles the daily retraining.

Workflow Orchestration (Dagster / Airflow)
------------------------------------------

For more complex pipelines — multiple substations, dependency management, retries,
and observability — a workflow orchestrator is the right tool. OpenSTEF integrates
naturally because each operation is a plain Python function call.

The following example shows a Dagster asset-based approach:

.. code-block:: python

   from dagster import asset, AssetExecutionContext, ScheduleDefinition, define_asset_job

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.models.workflow import CustomForecastingWorkflow
   from openstef_models.storage import LocalModelStorage
   from pathlib import Path

   STORAGE = LocalModelStorage(base_path=Path("/var/openstef/models"))

   @asset
   def training_data(context: AssetExecutionContext) -> VersionedTimeSeriesDataset:
       """Load and validate the training dataset."""
       dataset = load_data()  # your data-loading function
       context.log.info("Loaded %d rows of training data", len(dataset.data))
       return dataset

   @asset(deps=[training_data])
   def trained_model(
       context: AssetExecutionContext,
       training_data: VersionedTimeSeriesDataset,
   ) -> None:
       """Train and persist the forecasting model."""
       workflow = build_workflow(model_id="substation_42", storage=STORAGE)
       workflow.fit(training_data)
       context.log.info("Model training complete")

   @asset(deps=[trained_model])
   def forecasts(
       context: AssetExecutionContext,
       training_data: VersionedTimeSeriesDataset,
   ) -> None:
       """Generate and store forecasts."""
       workflow = CustomForecastingWorkflow.from_storage(
           model_id="substation_42", storage=STORAGE
       )
       result = workflow.predict(training_data)
       result.data.to_parquet("/data/forecasts_latest.parquet")
       context.log.info("Wrote %d forecast rows", len(result.data))

   daily_retrain = ScheduleDefinition(
       job=define_asset_job("retrain_job", selection=[training_data, trained_model]),
       cron_schedule="0 2 * * *",
   )

   quarter_hourly_predict = ScheduleDefinition(
       job=define_asset_job("predict_job", selection=[forecasts]),
       cron_schedule="*/15 * * * *",
   )

The same pattern applies to Apache Airflow: wrap each operation in a
``PythonOperator`` or ``@task`` and connect them with dependencies.

Cloud Deployment
----------------

OpenSTEF runs on any cloud platform that can execute Python. The main consideration
is model storage: replace ``LocalModelStorage`` with a cloud-backed alternative so
that models persist across ephemeral compute instances.

**AWS**

- Run jobs as AWS Lambda functions (for short predict runs) or ECS Fargate tasks
  (for longer training runs).
- Store models in S3 and load them at the start of each invocation.
- Use EventBridge Scheduler to trigger jobs on a cron expression.

**Azure**

- Use Azure Container Instances or Azure Functions for job execution.
- Store models in Azure Blob Storage.
- Trigger via Azure Logic Apps or Azure Data Factory pipelines.

**GCP**

- Cloud Run Jobs handle both training and prediction workloads well.
- Store models in Google Cloud Storage.
- Schedule with Cloud Scheduler.

In all cases the code change is minimal — swap the storage backend:

.. code-block:: python

   # Instead of:
   from openstef_models.storage import LocalModelStorage
   storage = LocalModelStorage(base_path=Path("/var/openstef/models"))

   # Use a cloud-backed storage implementation, for example:
   from openstef_models.storage import BlobModelStorage
   storage = BlobModelStorage(container_url="https://myaccount.blob.core.windows.net/models")

See :doc:`data_integration` for patterns covering cloud data sources alongside cloud
model storage.

Monitoring and Alerting
-----------------------

A production forecasting service needs two layers of monitoring: **infrastructure
health** (is the job running?) and **forecast quality** (are the forecasts accurate?).

Infrastructure health
^^^^^^^^^^^^^^^^^^^^^

Standard container/job monitoring covers this layer:

- Alert on non-zero exit codes from the job container.
- Track job duration — a training run that takes twice as long as usual often
  signals a data quality problem upstream.
- Emit a heartbeat metric (a counter increment) at the end of each successful
  predict run and alert if it stops arriving.

Forecast quality
^^^^^^^^^^^^^^^^

OpenSTEF provides evaluation utilities that you can run as part of the predict job
to measure ongoing forecast accuracy:

.. code-block:: python

   from openstef_models.evaluation import ForecastEvaluator
   from openstef_core.types import Q

   def run_predict_with_evaluation():
       dataset = load_data()
       workflow = CustomForecastingWorkflow.from_storage(
           model_id=MODEL_ID, storage=storage
       )
       forecasts = workflow.predict(dataset)

       # Evaluate against recent actuals
       evaluator = ForecastEvaluator(quantiles=[Q(0.1), Q(0.5), Q(0.9)])
       report = evaluator.evaluate(
           predictions=forecasts,
           ground_truth=dataset,
           target_column="load",
       )

       for subset in report.subsets:
           logger.info(
               "Lead time %s — MAE: %.3f, RMSE: %.3f",
               subset.filtering,
               subset.metrics.get("mae", float("nan")),
               subset.metrics.get("rmse", float("nan")),
           )

       # Raise an alert if accuracy degrades beyond a threshold
       median_mae = report.subsets[0].metrics.get("mae", 0)
       if median_mae > MAE_ALERT_THRESHOLD:
           send_alert(f"Forecast MAE {median_mae:.3f} exceeds threshold")

       return forecasts

Log structured output (JSON) so that metrics can be ingested by your observability
platform (Datadog, Grafana Loki, CloudWatch Logs Insights, etc.). See :doc:`logging`
for how to configure OpenSTEF's structured logging.

.. note::

   Model retraining frequency and forecast quality are closely linked. If accuracy
   degrades gradually over days, the model may need more frequent retraining or
   additional input features. If it degrades suddenly, suspect a data pipeline
   problem rather than a model problem.

Environment Configuration
--------------------------

Avoid hard-coding paths, credentials, or thresholds in your job script. Use
environment variables and validate them at startup:

.. code-block:: python

   import os
   from pathlib import Path

   def get_config():
       return {
           "model_dir": Path(os.environ["OPENSTEF_MODEL_DIR"]),
           "model_id": os.environ["OPENSTEF_MODEL_ID"],
           "data_path": Path(os.environ["OPENSTEF_DATA_PATH"]),
           "mae_threshold": float(os.environ.get("OPENSTEF_MAE_THRESHOLD", "50.0")),
           "log_level": os.environ.get("LOG_LEVEL", "INFO"),
       }

This makes the same container image usable across development, staging, and
production environments by changing only the environment variables passed to the
container.

Summary
-------

The table below summarises when to choose each deployment pattern:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Pattern
     - Best for
     - Key consideration
   * - Cron / systemd
     - Single host, low volume
     - Simple but no retry or parallelism
   * - Docker + cron
     - Reproducible environments, small teams
     - Mount model and data volumes correctly
   * - Kubernetes CronJob
     - Container-native infrastructure
     - Use ``concurrencyPolicy: Forbid``
   * - Dagster / Airflow
     - Many substations, complex dependencies
     - Observability and retry logic built in
   * - Cloud Run / Lambda
     - Serverless, variable load
     - Cold-start latency; use cloud model storage