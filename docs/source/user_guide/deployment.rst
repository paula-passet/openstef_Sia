Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from simple cron-based jobs to
containerised workloads and cloud-orchestrated pipelines. It focuses on the operational concerns that
arise once you move beyond a notebook or development environment — model persistence, scheduling,
monitoring, and infrastructure choices.

For reading data from external sources such as S3, Databricks, or InfluxDB, see :doc:`data_integration`.
For common forecasting use cases that inform how you structure a deployment, see :doc:`use_cases`.

.. note::

   OpenSTEF is a **library**, not a deployable application. The patterns on this page show how to
   embed OpenSTEF into your own service or pipeline. You own the scheduler, the container, and the
   infrastructure; OpenSTEF provides the forecasting logic.


Deployment Patterns Overview
-----------------------------

There is no single "correct" way to deploy OpenSTEF. The right architecture depends on how many
forecast targets you manage, how frequently models need retraining, and what infrastructure your
organisation already operates. Three patterns cover most real-world scenarios:

- **Scheduled script** — a Python script invoked by cron, a cloud scheduler, or a CI/CD pipeline.
  Suitable for a small number of forecast points with infrequent retraining.
- **Containerised job** — the same script packaged as a Docker image and executed by a container
  orchestrator (Kubernetes CronJob, AWS ECS Scheduled Task, Azure Container Instances). Suitable for
  teams that want reproducible environments and horizontal scaling.
- **Orchestration platform** — a DAG-based workflow tool such as Apache Airflow or Prefect manages
  train and predict tasks as separate, dependent steps. Suitable for large fleets of forecast points
  or complex dependency graphs.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd


Scheduled Script
-----------------

The simplest production deployment is a Python script that runs on a fixed schedule. The script
loads recent data, runs the forecast workflow, and writes results to a database or file store.

.. code-block:: python

   # forecast_job.py
   import logging
   from datetime import timedelta
   from pathlib import Path

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.integrations.mlflow import MLFlowStorage
   from openstef_core.datasets import TimeSeriesDataset

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)


   def load_data() -> TimeSeriesDataset:
       # Replace with your data integration logic.
       # See the data_integration page for S3/Databricks/InfluxDB patterns.
       raise NotImplementedError


   def write_forecast(forecast):
       # Write results to your database or message bus.
       raise NotImplementedError


   def main():
       storage = MLFlowStorage(
           tracking_uri="http://mlflow.internal:5000",
           experiment_name_prefix="production",
       )

       workflow = CustomForecastingWorkflow.load(
           model_id="substation_42",
           storage=storage,
       )

       data = load_data()
       forecast = workflow.predict(data)
       write_forecast(forecast)
       logger.info("Forecast complete for substation_42")


   if __name__ == "__main__":
       main()

A cron entry to run this every 15 minutes looks like:

.. code-block:: bash

   */15 * * * * /opt/venv/bin/python /opt/jobs/forecast_job.py >> /var/log/openstef.log 2>&1

Keep the training job separate from the prediction job. Retraining typically runs daily or weekly,
while prediction runs every 15–60 minutes. Mixing them in a single script creates unnecessary
coupling and makes it harder to tune each schedule independently.


Model Storage Backends
-----------------------

OpenSTEF ships two storage backends out of the box. Choosing the right one early avoids painful
migrations later.

**Local filesystem (development and single-node deployments)**

``JoblibModelSerializer`` serialises models to ``.pkl`` files on disk. It requires no external
services and is the fastest option for getting started.

.. code-block:: python

   from pathlib import Path
   from openstef_models.integrations.joblib import JoblibModelSerializer

   serializer = JoblibModelSerializer()
   # Serialise a trained model to a binary stream
   with open(Path("models") / "substation_42.pkl", "wb") as f:
       serializer.serialize(model, f)

   # Deserialise
   with open(Path("models") / "substation_42.pkl", "rb") as f:
       model = serializer.deserialize(f)

.. warning::

   Joblib serialisation is pickle-based. Never load a ``.pkl`` file from an untrusted source, as
   it can execute arbitrary code on deserialisation.

**MLflow (recommended for production)**

``MLFlowStorage`` integrates with an MLflow Tracking Server to version models, log hyperparameters,
and store training artefacts. It is the recommended backend for any deployment with more than a
handful of forecast targets.

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback
   from openstef_models.workflows import CustomForecastingWorkflow

   storage = MLFlowStorage(
       tracking_uri="http://mlflow.internal:5000",
       local_artifacts_path="/tmp/mlflow_artifacts",
       experiment_name_prefix="grid_forecasting",
   )

   callback = MLFlowStorageCallback(storage=storage)

   workflow = CustomForecastingWorkflow(
       model_id="substation_42",
       model=...,          # your configured ForecastingModel
       callbacks=[callback],
   )

   # Training automatically logs metrics, hyperparameters, and the model artefact
   result = workflow.fit(train_dataset)

The ``MLFlowStorageCallback`` fires on ``on_fit_start`` and ``on_fit_end`` events, logging
hyperparameters per component, storing training data as Parquet, and uploading the serialised model
— all without any extra code in your training script.

When pointing ``tracking_uri`` at a local path rather than an HTTP server, ``MLFlowStorage``
normalises it to a ``file:///`` URI automatically, so the same code works in both local and
remote configurations.


Containerisation
-----------------

Packaging your forecasting job as a Docker image ensures that the Python environment is identical
across development, CI, and production.

A minimal ``Dockerfile`` for a prediction job:

.. code-block:: dockerfile

   FROM python:3.11-slim

   WORKDIR /app

   # Install OpenSTEF and your project dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY forecast_job.py .

   CMD ["python", "forecast_job.py"]

A representative ``requirements.txt``:

.. code-block:: text

   openstef-core
   openstef-models[mlflow]
   openstef-beam

Keep training and prediction images separate if their dependency footprints differ significantly —
training images often include heavier packages (e.g., full MLflow with UI dependencies) that are
unnecessary at inference time.

**Kubernetes CronJob**

For teams running Kubernetes, a ``CronJob`` resource schedules the container without requiring a
separate orchestration tool:

.. code-block:: yaml

   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-predict
   spec:
     schedule: "*/15 * * * *"
     jobTemplate:
       spec:
         template:
           spec:
             restartPolicy: OnFailure
             containers:
               - name: forecast
                 image: your-registry/openstef-predict:latest
                 env:
                   - name: MLFLOW_TRACKING_URI
                     value: "http://mlflow-service:5000"
                 resources:
                   requests:
                     memory: "512Mi"
                     cpu: "250m"
                   limits:
                     memory: "2Gi"
                     cpu: "1"

Pass sensitive configuration (database passwords, API keys) via Kubernetes Secrets mounted as
environment variables rather than baking them into the image.


Cloud Deployment Options
-------------------------

OpenSTEF's library design means it runs wherever Python runs. The table below summarises common
cloud deployment targets and the relevant managed service for scheduling:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Cloud
     - Scheduling service
     - Notes
   * - AWS
     - ECS Scheduled Tasks / EventBridge + Lambda
     - Use ECS for CPU-intensive training; Lambda for lightweight prediction if cold-start latency is acceptable.
   * - Azure
     - Azure Container Instances + Logic Apps / Azure ML Pipelines
     - Azure ML Pipelines integrate naturally with MLflow tracking.
   * - GCP
     - Cloud Run Jobs + Cloud Scheduler
     - Cloud Run Jobs support GPU instances for training workloads.
   * - On-premises
     - Kubernetes CronJob / Airflow
     - Airflow is preferred when forecast targets have complex dependency graphs.

Regardless of cloud provider, the pattern is the same: your container image embeds the OpenSTEF
library and your pipeline code; the cloud service handles scheduling and execution.


Orchestration with Airflow
---------------------------

When you manage many forecast targets or need fine-grained control over retries, dependencies, and
backfill, a DAG-based orchestrator such as Apache Airflow is a natural fit. Each DAG represents one
forecast target, with separate tasks for training and prediction.

.. code-block:: python

   # dags/substation_42_dag.py
   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback


   def train_model():
       storage = MLFlowStorage(tracking_uri="{{ var.value.mlflow_uri }}")
       callback = MLFlowStorageCallback(storage=storage)
       workflow = CustomForecastingWorkflow(
           model_id="substation_42",
           model=...,
           callbacks=[callback],
       )
       workflow.fit(load_training_data())


   def run_forecast():
       storage = MLFlowStorage(tracking_uri="{{ var.value.mlflow_uri }}")
       workflow = CustomForecastingWorkflow.load(
           model_id="substation_42",
           storage=storage,
       )
       forecast = workflow.predict(load_recent_data())
       write_forecast(forecast)


   with DAG(
       dag_id="substation_42",
       start_date=datetime(2024, 1, 1),
       schedule_interval=timedelta(minutes=15),
       catchup=False,
       default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
   ) as dag:

       train = PythonOperator(
           task_id="train_model",
           python_callable=train_model,
           # Run training once per day via a separate scheduled DAG in practice
       )

       predict = PythonOperator(
           task_id="run_forecast",
           python_callable=run_forecast,
       )

       train >> predict

.. note::

   In practice, training and prediction DAGs are usually separate, with the prediction DAG
   triggered on its own 15-minute schedule and the training DAG on a daily or weekly schedule.
   The example above shows them in sequence for clarity.


Monitoring and Observability
-----------------------------

Production forecasting systems need two layers of monitoring: infrastructure health (is the job
running?) and forecast quality (are the predictions accurate?).

**Infrastructure health**

Standard container and job monitoring applies: track exit codes, execution duration, and memory
usage through your existing observability stack (Prometheus, Datadog, CloudWatch, etc.). Set alerts
on job failures and on jobs that exceed their expected runtime — a training job that takes three
times longer than usual often signals a data quality problem upstream.

**Forecast quality**

OpenSTEF's evaluation framework, provided by ``openstef-beam``, computes performance metrics across
lead times, time windows, and custom filters. Integrate it into a post-prediction step to track
accuracy over time:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
   from openstef_beam.evaluation.models import Window
   from datetime import timedelta

   eval_config = EvaluationConfig(
       windows=[
           Window(duration=timedelta(days=7)),   # rolling 7-day window
           Window(duration=timedelta(days=30)),  # rolling 30-day window
       ],
   )

   pipeline = EvaluationPipeline(config=eval_config)
   report = pipeline.run(forecast_dataset)

   # Log summary metrics to your monitoring system
   for subset_report in report.subset_reports:
       print(subset_report.metrics)

Key metrics to track in production:

- **rMAE** (relative Mean Absolute Error) — overall accuracy, suitable for transport forecasts.
- **rCRPS** (relative Continuous Ranked Probability Score) — probabilistic accuracy, important for
  congestion management where quantile coverage matters.
- **Lead-time degradation** — how quickly accuracy drops as the forecast horizon extends. A sudden
  change in this curve often indicates a change in input data quality.

Log these metrics to your MLflow tracking server or time-series database so you can plot trends and
set threshold-based alerts.

**Structured logging**

OpenSTEF uses Python's standard ``logging`` module throughout. Configure a structured formatter
(e.g., ``python-json-logger``) to emit JSON log lines that your log aggregator can index and query:

.. code-block:: python

   import logging
   from pythonjsonlogger import jsonlogger

   handler = logging.StreamHandler()
   handler.setFormatter(jsonlogger.JsonFormatter())
   logging.getLogger().addHandler(handler)
   logging.getLogger().setLevel(logging.INFO)

This makes it straightforward to build dashboards and alerts on log fields such as ``model_id``,
``lead_time``, and ``mae`` without parsing free-text log lines.


Configuration Management
-------------------------

Avoid hard-coding connection strings, model identifiers, and schedule parameters in source code.
A lightweight pattern is to read configuration from environment variables, which works uniformly
across local development, Docker, and Kubernetes:

.. code-block:: python

   import os
   from openstef_models.integrations.mlflow import MLFlowStorage

   storage = MLFlowStorage(
       tracking_uri=os.environ["MLFLOW_TRACKING_URI"],
       experiment_name_prefix=os.environ.get("MLFLOW_EXPERIMENT_PREFIX", ""),
   )

For more complex deployments, a YAML or TOML configuration file loaded at startup keeps settings
auditable in version control while still allowing environment-specific overrides via environment
variables.


Summary
--------

The deployment approach that works best for your team depends on scale and existing infrastructure:

- Start with a **scheduled script** and local model storage to validate the end-to-end pipeline
  quickly.
- Move to **containerised jobs** with MLflow storage as soon as you need reproducibility or more
  than one forecast target.
- Adopt an **orchestration platform** when you need fine-grained retry logic, complex dependencies,
  or a large fleet of forecast points.

In all cases, instrument your jobs with structured logging and run the ``openstef-beam`` evaluation
pipeline regularly to catch accuracy regressions before they affect operational decisions.