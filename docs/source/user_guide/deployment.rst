Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from simple
cron-based scheduled jobs to fully orchestrated pipelines with MLflow tracking,
containerisation, and cloud deployment. It assumes you are already familiar with
building a forecasting workflow — if not, start with the examples in the sibling pages
before returning here.

.. note::

   OpenSTEF is a **library**. It does not ship a server, daemon, or scheduler of its
   own. Every deployment pattern below is a thin wrapper that calls OpenSTEF's Python
   API on a schedule you control.

Introduction
------------

A production OpenSTEF deployment typically involves two recurring jobs:

- **Training job** — fits (or re-fits) a :class:`~openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow`
  on fresh historical data and persists the resulting model.
- **Inference job** — loads the persisted model and calls ``predict()`` on the latest
  input features, writing forecasts to a downstream store.

How often each job runs depends on your use case. Training is usually daily or weekly;
inference can be as frequent as every 15 minutes. The sections below show how to
structure both jobs and how to wire them into common deployment environments.

[DIAGRAM: Two-job deployment loop showing Training Job (fetch data → fit workflow → store model via MLflow) and Inference Job (fetch features → load model → predict → write forecasts), connected by a shared model store and triggered independently by a scheduler]

Core Workflow Pattern
---------------------

Both jobs share the same ``CustomForecastingWorkflow`` object. The workflow holds the
model, optional callbacks, and a stable ``model_id`` that links training runs to
inference runs.

.. code-block:: python

   # workflow_factory.py  — shared by training and inference entry points
   import logging
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.integrations.mlflow.mlflow_storage_callback import (
       MLFlowStorageCallback,
   )
   from openstef_core.types import Q

   logger = logging.getLogger(__name__)


   def build_workflow(model_id: str) -> CustomForecastingWorkflow:
       """Return a workflow wired to MLflow for model persistence."""
       from openstef_models.models.forecasting_model import ForecastingModel
       from openstef_core.feature_engineering import FeaturePipeline

       # Build your model (adapt to your own forecaster / feature pipeline)
       model = ForecastingModel(...)

       mlflow_callback = MLFlowStorageCallback(
           model_reuse_enable=True,
           model_reuse_max_age_days=7,
           model_selection_enable=True,
           model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       )

       return CustomForecastingWorkflow(
           model=model,
           model_id=model_id,
           callbacks=[mlflow_callback],
           experiment_tags={"env": "production"},
       )

The ``MLFlowStorageCallback`` handles the full model lifecycle automatically: it skips
re-training when a recent run already exists (``model_reuse_enable``), compares the new
model against the stored one before replacing it (``model_selection_enable``), and logs
hyperparameters, metrics, and feature-importance plots to MLflow.

Training Entry Point
--------------------

The training script fetches historical data, calls ``workflow.fit()``, and exits. The
callback takes care of persisting the model.

.. code-block:: python

   # train.py
   import logging
   from openstef_core.datasets import TimeSeriesDataset
   from workflow_factory import build_workflow

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   MODEL_ID = "grid-east-zone-a"


   def run_training(data: TimeSeriesDataset) -> None:
       workflow = build_workflow(MODEL_ID)
       result = workflow.fit(data=data)
       if result is None:
           logger.info("Training skipped — recent model still valid.")
       else:
           logger.info("Training complete. Metrics: %s", result.metrics_to_flat_dict())


   if __name__ == "__main__":
       # Replace with your data-loading logic (see the data_integration page)
       data = TimeSeriesDataset(...)
       run_training(data)

Inference Entry Point
---------------------

The inference script loads the latest model via the same workflow and ``model_id``, then
calls ``predict()``. Because ``MLFlowStorageCallback`` implements ``on_predict_start``,
it automatically restores the most recent stored model before prediction begins — your
script does not need to handle model loading explicitly.

.. code-block:: python

   # predict.py
   import logging
   from openstef_core.datasets import TimeSeriesDataset
   from workflow_factory import build_workflow

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   MODEL_ID = "grid-east-zone-a"


   def run_inference(features: TimeSeriesDataset) -> None:
       workflow = build_workflow(MODEL_ID)
       forecasts = workflow.predict(data=features)
       logger.info("Generated %d forecast rows.", len(forecasts.data))
       # Write forecasts to your downstream store here


   if __name__ == "__main__":
       features = TimeSeriesDataset(...)
       run_inference(features)

Scheduled Jobs
--------------

The simplest production setup is two cron jobs — one for training, one for inference —
running inside the same environment.

**Linux cron example**

.. code-block:: text

   # Retrain every day at 02:00
   0 2 * * *  /opt/openstef-env/bin/python /opt/openstef/train.py >> /var/log/openstef-train.log 2>&1

   # Run inference every 15 minutes
   */15 * * * *  /opt/openstef-env/bin/python /opt/openstef/predict.py >> /var/log/openstef-predict.log 2>&1

This is sufficient for many operational deployments. The main limitation is that cron
provides no retry logic, dependency tracking, or alerting. For those features, consider
the orchestration options below.

Containerisation
----------------

Packaging OpenSTEF jobs as Docker containers makes them portable across environments
(bare-metal, Kubernetes, cloud managed services).

**Dockerfile**

.. code-block:: text

   FROM python:3.11-slim

   WORKDIR /app

   # Install OpenSTEF and your project dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY workflow_factory.py train.py predict.py ./

   # Default command — override at runtime with "predict"
   CMD ["python", "train.py"]

**requirements.txt (minimum)**

.. code-block:: text

   openstef-core
   openstef-models
   openstef-beam
   mlflow

Build and run:

.. code-block:: text

   docker build -t openstef-forecaster:latest .

   # Training
   docker run --rm \
     -e MLFLOW_TRACKING_URI=http://mlflow-server:5000 \
     openstef-forecaster:latest python train.py

   # Inference
   docker run --rm \
     -e MLFLOW_TRACKING_URI=http://mlflow-server:5000 \
     openstef-forecaster:latest python predict.py

Pass configuration through environment variables rather than baking it into the image.
This keeps the same image usable across development, staging, and production.

Kubernetes CronJob
------------------

On Kubernetes, a ``CronJob`` resource replaces the host-level cron entry and adds
automatic retries, history retention, and integration with cluster secrets.

.. code-block:: text

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-training
   spec:
     schedule: "0 2 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             restartPolicy: OnFailure
             containers:
               - name: trainer
                 image: openstef-forecaster:latest
                 command: ["python", "train.py"]
                 env:
                   - name: MLFLOW_TRACKING_URI
                     valueFrom:
                       secretKeyRef:
                         name: openstef-secrets
                         key: mlflow-uri
                   - name: MODEL_ID
                     value: "grid-east-zone-a"

Create a second ``CronJob`` with ``schedule: "*/15 * * * *"`` and
``command: ["python", "predict.py"]`` for the inference job.

.. note::

   Set ``spec.jobTemplate.spec.backoffLimit`` to a small value (e.g. ``2``) so that a
   broken model or bad data does not cause the job to retry indefinitely.

Cloud Deployment Options
------------------------

OpenSTEF jobs are standard Python processes and run without modification on any cloud
compute service. The table below summarises common choices:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Platform
     - Training job
     - Inference job
   * - **AWS**
     - AWS Batch or ECS Fargate scheduled task
     - AWS Lambda (if <15 min) or ECS Fargate
   * - **Azure**
     - Azure Container Apps Jobs or Azure ML pipeline
     - Azure Functions or Container Apps Jobs
   * - **GCP**
     - Cloud Run Jobs triggered by Cloud Scheduler
     - Cloud Run Jobs or Cloud Functions
   * - **On-premise**
     - Kubernetes CronJob or Airflow DAG
     - Kubernetes CronJob or Airflow DAG

In all cases the container image is the same; only the trigger mechanism and secret
injection differ.

**MLflow tracking server**

All cloud options above benefit from a shared MLflow tracking server so that training
runs, metrics, and model artefacts are visible in one place. Set the
``MLFLOW_TRACKING_URI`` environment variable to point every container at the same
server:

.. code-block:: text

   MLFLOW_TRACKING_URI=https://mlflow.internal.example.com

Workflow Orchestration with Airflow
------------------------------------

For pipelines with data-dependency logic — for example, only train when enough new data
has arrived, or fan out across dozens of grid zones — Apache Airflow (or Prefect / Dagster)
is a natural fit.

.. code-block:: python

   # dags/openstef_dag.py
   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator
   from openstef_core.datasets import TimeSeriesDataset
   from workflow_factory import build_workflow

   MODEL_ID = "grid-east-zone-a"

   default_args = {
       "owner": "energy-forecasting",
       "retries": 2,
       "retry_delay": timedelta(minutes=5),
   }


   def training_task(**context):
       # Load data from your store (see the data_integration page for patterns)
       data = TimeSeriesDataset(...)
       workflow = build_workflow(MODEL_ID)
       workflow.fit(data=data)


   def inference_task(**context):
       features = TimeSeriesDataset(...)
       workflow = build_workflow(MODEL_ID)
       forecasts = workflow.predict(data=features)
       # Write forecasts downstream


   with DAG(
       dag_id="openstef_forecasting",
       default_args=default_args,
       start_date=datetime(2024, 1, 1),
       schedule_interval="*/15 * * * *",
       catchup=False,
   ) as dag:
       train = PythonOperator(task_id="train", python_callable=training_task)
       predict = PythonOperator(task_id="predict", python_callable=inference_task)

       train >> predict

Monitoring and Alerting
-----------------------

OpenSTEF provides built-in evaluation tooling through ``openstef_beam.evaluation``.
Incorporate a scoring step into your training job to track model quality over time:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_core.types import LeadTime

   def evaluate_and_alert(workflow, test_data):
       """Score the model on held-out data and raise if quality degrades."""
       score = workflow.model.score(data=test_data)
       metrics = score.metrics

       r2 = metrics.get("R2", None)
       if r2 is not None and r2 < 0.80:
           raise RuntimeError(
               f"Model quality below threshold: R2={r2:.3f} < 0.80. "
               "Investigate training data or retrigger full retraining."
           )
       return metrics

Integrate ``evaluate_and_alert`` at the end of your training entry point. When the job
exits with a non-zero status (due to the raised exception), your scheduler or cloud
platform will fire its normal alerting path (PagerDuty, email, Slack, etc.).

For richer dashboards, the ``MLFlowStorageCallback`` automatically logs all metrics
returned by ``result.metrics_to_flat_dict()`` to MLflow, where they can be visualised
in the MLflow UI or exported to Grafana via the MLflow metrics API.

[VISUALIZATION: Grafana dashboard showing R2 and RMSE trends over training runs, with a threshold line at R2=0.80 and an alert annotation]

Custom Callbacks for Operational Hooks
---------------------------------------

The ``ForecastingCallback`` interface lets you inject operational logic — writing to a
database, publishing to a message bus, sending a health-check ping — without modifying
the core workflow.

.. code-block:: python

   import logging
   import requests
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback

   logger = logging.getLogger(__name__)


   class HealthCheckCallback(ForecastingCallback):
       """Ping an uptime monitor after each successful inference run."""

       def __init__(self, ping_url: str):
           self.ping_url = ping_url

       def on_predict_end(self, context, result):
           try:
               requests.get(self.ping_url, timeout=5)
               logger.info("Health-check ping sent to %s", self.ping_url)
           except requests.RequestException as exc:
               logger.warning("Health-check ping failed: %s", exc)


   class ForecastWriterCallback(ForecastingCallback):
       """Write completed forecasts to a downstream store."""

       def on_predict_end(self, context, result):
           # result is a ForecastDataset — write result.data to your store
           logger.info("Writing %d forecast rows to store.", len(result.data))
           # your_store.write(result.data)

Compose multiple callbacks by passing them all in the ``callbacks`` list when
constructing ``CustomForecastingWorkflow``.

Further Reading
---------------

- :doc:`data_integration` — patterns for reading training and feature data from S3,
  Databricks, InfluxDB, and other sources.
- :doc:`use_cases` — end-to-end examples including congestion forecasting and load
  disaggregation that you can adapt as the basis for your deployment.
- :doc:`migration_v3_v4` — if you are upgrading an existing deployment, consult the
  migration guide for breaking API changes.