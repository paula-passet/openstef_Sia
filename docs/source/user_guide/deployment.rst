Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from simple
cron-based scheduled jobs to fully orchestrated pipelines on cloud platforms. It
addresses containerization, environment configuration, model persistence, and
monitoring integration.

For related topics, see :doc:`data_integration` for connecting to production data
sources, :doc:`logging` for structured log configuration, and :doc:`use_cases` for
domain-specific pipeline examples.

.. note:: [DIAGRAM: High-level deployment topology showing a scheduler triggering a
   training job and a prediction job, both reading from a data store and writing
   forecasts and model artifacts to persistent storage, with MLflow tracking on the
   side.]

Deployment Philosophy
---------------------

OpenSTEF is a **library**, not a service. It does not ship a server, a daemon, or a
built-in scheduler. Instead, it provides composable Python building blocks —
workflows, callbacks, model storage — that you embed inside whatever execution
environment already exists in your organisation. This means the deployment footprint
is entirely under your control: a single Python script run by cron is a valid
production deployment, as is a multi-step Dagster pipeline running on Kubernetes.

The two recurring operations in any OpenSTEF deployment are:

- **Training** — periodically refit models on fresh historical data.
- **Prediction** — run inference on a schedule aligned to your forecast horizon.

Both operations are expressed through the same workflow API, so the code structure
is identical regardless of the scheduler wrapping it.

Structuring Your Entry Points
------------------------------

Keep training and prediction as separate, independently schedulable Python scripts
(or callable functions). This separation lets you retrain weekly while generating
forecasts every 15 minutes without coupling the two processes.

A minimal training entry point:

.. code-block:: python

   # train.py
   import logging
   from pathlib import Path
   from datetime import timedelta

   from openstef_models.workflow import CustomForecastingWorkflow
   from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage
   from openstef_models.integrations.mlflow.mlflow_storage_callback import (
       MLFlowStorageCallback,
   )
   from openstef_core.dataset import VersionedTimeSeriesDataset

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   ARTIFACTS_DIR = Path("/var/openstef/artifacts")
   MLFLOW_DIR = Path("/var/openstef/mlflow")


   def train(dataset: VersionedTimeSeriesDataset) -> None:
       mlflow_storage = MLFlowStorage(
           tracking_uri=str(MLFLOW_DIR / "tracking"),
           local_artifacts_path=MLFLOW_DIR / "artifacts",
       )
       callback = MLFlowStorageCallback(
           storage=mlflow_storage,
           model_reuse_enable=True,
           model_reuse_max_age=timedelta(days=7),
           model_selection_enable=True,
       )
       workflow = CustomForecastingWorkflow(
           # ... model and model_id configuration ...
           callbacks=[callback],
       )
       result = workflow.fit(dataset)
       if result is not None:
           logger.info("Training metrics:\n%s", result.metrics_full.to_dataframe())


   if __name__ == "__main__":
       # Load your dataset here — see the data_integration page for patterns
       dataset = load_dataset()  # replace with your data loading logic
       train(dataset)

A minimal prediction entry point follows the same pattern but calls
``workflow.predict(dataset)`` and writes the resulting ``ForecastDataset`` to your
output sink.

.. note::

   ``MLFlowStorageCallback`` supports model reuse: if a run younger than
   ``model_reuse_max_age`` already exists in MLflow, the callback skips retraining
   and loads the existing model instead. This makes it safe to call the training
   entry point on a tight schedule without unnecessary compute.

Scheduled Execution with Cron
------------------------------

For straightforward deployments, a cron job is often sufficient. The key is to
ensure the Python environment is fully isolated and reproducible.

.. code-block:: bash

   # /etc/cron.d/openstef
   # Retrain every Sunday at 02:00
   0 2 * * 0  openstef  /opt/openstef/venv/bin/python /opt/openstef/train.py

   # Generate forecasts every 15 minutes
   */15 * * * *  openstef  /opt/openstef/venv/bin/python /opt/openstef/predict.py

Use the full path to the virtual-environment interpreter so the job is not affected
by system Python upgrades. Redirect stdout and stderr to a log file or a log
aggregator — see :doc:`logging` for structured logging configuration that works well
with log shippers like Fluentd or Filebeat.

Containerization
-----------------

Packaging OpenSTEF jobs as containers gives you reproducible environments and
simplifies deployment to any container runtime (Docker, Kubernetes, cloud run
services).

A minimal ``Dockerfile`` for a forecasting job:

.. code-block:: dockerfile

   FROM python:3.12-slim

   WORKDIR /app

   # Install uv for fast, reproducible dependency resolution
   RUN pip install --no-cache-dir uv

   COPY pyproject.toml uv.lock ./
   RUN uv sync --no-dev --frozen

   COPY src/ ./src/

   # Default command — override at runtime for train vs predict
   CMD [".venv/bin/python", "src/predict.py"]

Build separate images (or use a single image with a different ``CMD``) for training
and prediction jobs. Keep model artifacts and MLflow tracking data on a mounted
volume or remote storage so they survive container restarts:

.. code-block:: bash

   docker run \
     -v /data/openstef/mlflow:/var/openstef/mlflow \
     -v /data/openstef/artifacts:/var/openstef/artifacts \
     -e DATA_SOURCE_URI="influxdb://..." \
     my-org/openstef-train:latest

Pass environment-specific configuration (database URIs, credentials, feature
flags) through environment variables rather than baking them into the image.

Cloud Deployment Options
-------------------------

Because OpenSTEF is a library, it runs wherever Python runs. The following patterns
cover the most common cloud execution models.

**Serverless / Function-as-a-Service**

Short-running prediction jobs (seconds to low minutes) are a natural fit for AWS
Lambda, Google Cloud Functions, or Azure Functions. Package the virtual environment
as a Lambda layer or use a container-based Lambda. Store model artifacts in S3 or
Azure Blob Storage and load them at cold-start. Be mindful of cold-start latency for
time-sensitive forecasts.

**Container-based batch jobs**

AWS Batch, Google Cloud Run Jobs, and Azure Container Instances are well suited for
training jobs that run for several minutes. Define a job definition pointing to your
training container image, mount artifact storage, and trigger the job from a
scheduler (EventBridge, Cloud Scheduler, or Logic Apps).

**Kubernetes CronJobs**

For organisations already running Kubernetes, a ``CronJob`` resource provides
cron-like scheduling with container isolation:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-train
   spec:
     schedule: "0 2 * * 0"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
               - name: train
                 image: my-org/openstef-train:latest
                 env:
                   - name: DATA_SOURCE_URI
                     valueFrom:
                       secretKeyRef:
                         name: openstef-secrets
                         key: data-source-uri
                 volumeMounts:
                   - name: mlflow-storage
                     mountPath: /var/openstef/mlflow
             volumes:
               - name: mlflow-storage
                 persistentVolumeClaim:
                   claimName: openstef-mlflow-pvc
             restartPolicy: OnFailure

**Workflow orchestrators**

For pipelines with dependencies between steps (e.g., validate data → train → evaluate
→ promote model → predict), a dedicated orchestrator gives you retries, dependency
management, and a UI for observability. Dagster, Prefect, and Apache Airflow all work
well. Wrap each OpenSTEF function call in an op/task and connect them into a graph:

.. code-block:: python

   # dagster_pipeline.py (illustrative — adapt to your Dagster version)
   from dagster import job, op, Out, In
   from my_openstef_jobs import load_dataset, train, predict, write_forecast


   @op(out=Out())
   def load_data_op():
       return load_dataset()


   @op(ins={"dataset": In()}, out=Out())
   def train_op(dataset):
       train(dataset)
       return dataset


   @op(ins={"dataset": In()})
   def predict_op(dataset):
       forecast = predict(dataset)
       write_forecast(forecast)


   @job
   def openstef_pipeline():
       dataset = load_data_op()
       trained = train_op(dataset)
       predict_op(trained)

Model Persistence and Versioning
----------------------------------

OpenSTEF's MLflow integration handles model versioning automatically. Each training
run is logged as an MLflow experiment run, and ``MLFlowStorageCallback`` can compare
the new model against the incumbent using a configurable metric before promoting it:

.. code-block:: python

   callback = MLFlowStorageCallback(
       storage=MLFlowStorage(
           tracking_uri="http://mlflow.internal:5000",  # remote MLflow server
           local_artifacts_path=Path("/tmp/mlflow_artifacts"),
       ),
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
       model_selection_enable=True,
       # Promote only if new model improves R² by more than the penalty factor
       model_selection_metric=("Q0.5", "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
       store_feature_importance_plot=True,
   )

With a remote MLflow tracking server, all team members and all deployment
environments share the same model registry, making rollbacks straightforward.

For simpler setups without a remote MLflow server, ``LocalModelStorage`` persists
models to a local directory. This is sufficient for single-machine deployments but
does not provide cross-environment model sharing.

Monitoring and Alerting
------------------------

OpenSTEF does not include a built-in alerting system, but it produces the artefacts
you need to build one.

**Training metrics** — ``workflow.fit()`` returns a result object whose
``metrics_full`` and ``metrics_test`` attributes expose evaluation metrics as
DataFrames. Log these to your observability stack (Prometheus, Datadog, CloudWatch)
after every training run to track model quality over time.

.. code-block:: python

   result = workflow.fit(dataset)
   if result is not None:
       metrics = result.metrics_full.to_dataframe()
       for _, row in metrics.iterrows():
           # Push to your metrics backend
           push_metric(name=row["metric"], value=row["value"], tags={"model": model_id})

**Prediction health checks** — after generating a forecast, validate that the output
is non-empty, falls within expected physical bounds, and has no unexpected NaN
values before writing it to your output sink. A failed validation should raise an
exception so the scheduler marks the job as failed and triggers an alert.

**Structured logging** — configure Python's standard ``logging`` module to emit JSON
and ship logs to your log aggregation platform. See :doc:`logging` for recommended
configuration patterns.

.. note::

   MLflow's built-in UI (``mlflow ui``) provides a quick way to inspect training
   runs, compare metrics across versions, and browse stored artifacts during
   development. In production, point ``tracking_uri`` at a shared MLflow server so
   all runs are visible in one place.

Environment Configuration
--------------------------

Avoid hard-coding paths, credentials, or environment-specific settings in your
pipeline code. A lightweight approach is to read configuration from environment
variables at startup:

.. code-block:: python

   import os
   from pathlib import Path

   MLFLOW_TRACKING_URI = os.environ["MLFLOW_TRACKING_URI"]
   DATA_SOURCE_URI = os.environ["DATA_SOURCE_URI"]
   ARTIFACTS_PATH = Path(os.environ.get("ARTIFACTS_PATH", "/var/openstef/artifacts"))
   MODEL_REUSE_MAX_DAYS = int(os.environ.get("MODEL_REUSE_MAX_DAYS", "7"))

For more complex configuration needs, a settings library such as ``pydantic-settings``
works well alongside OpenSTEF's Pydantic-based configuration objects.

Summary
-------

A production OpenSTEF deployment involves three concerns:

- **Execution** — choose a scheduler (cron, Kubernetes CronJob, orchestrator) that
  matches your operational complexity.
- **Persistence** — use ``MLFlowStorageCallback`` with a shared MLflow server for
  model versioning and automatic model selection, or ``LocalModelStorage`` for
  single-machine setups.
- **Observability** — emit training metrics to your monitoring stack, validate
  forecast outputs before writing them, and ship structured logs to your aggregation
  platform.

Because OpenSTEF is a library, none of these concerns require adopting a specific
platform — you integrate OpenSTEF into the infrastructure you already operate.