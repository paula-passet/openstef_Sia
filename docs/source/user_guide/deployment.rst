Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from a simple
cron-scheduled script on a single machine to a fully orchestrated multi-target pipeline
with MLflow tracking. It focuses on the *operational* side — how you package, schedule,
persist, and monitor your forecasting workflows — rather than on modelling choices.

For reading data from external systems such as S3, Databricks, or InfluxDB, see
:doc:`data_integration`. For use-case walkthroughs that show what to build, see
:doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

-----------

Deployment Patterns
-------------------

OpenSTEF is a library, not a server. There is no daemon to start; you write a Python
script (or notebook) that calls the library, and then you decide how and when that
script runs. The three most common patterns are:

- **Scheduled script** — a cron job or cloud scheduler invokes a Python script on a
  fixed cadence (e.g. every 15 minutes). Simple, easy to debug, suitable for a handful
  of forecasting targets.
- **Containerised job** — the script is packaged as a Docker image and executed by a
  container orchestrator (Kubernetes CronJob, AWS ECS Scheduled Task, Azure Container
  Apps Job). Adds reproducibility and horizontal scaling.
- **Workflow orchestrator** — tools such as Apache Airflow, Prefect, or Azure Data
  Factory manage dependencies, retries, and parallelism across many targets.

All three patterns use the same OpenSTEF API. The sections below show how to structure
your code for each.

-----------

Structuring Your Entry-Point Script
------------------------------------

Regardless of how the script is triggered, a production forecasting job typically does
three things: load recent data, run the workflow, and write the output somewhere. A
minimal but complete entry point looks like this:

.. code-block:: python

    # forecast_job.py
    import logging
    from datetime import timedelta
    from pathlib import Path

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.integrations.mlflow import MLFlowStorage
    from openstef_models.integrations.mlflow.mlflow_storage_callback import (
        MLFlowStorageCallback,
    )
    from openstef_core.datasets import VersionedTimeSeriesDataset

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # --- 1. Load data (replace with your data source) ---
    # See the data_integration page for S3/Databricks/InfluxDB patterns.
    dataset: VersionedTimeSeriesDataset = load_my_data()

    # --- 2. Configure the workflow ---
    mlflow_storage = MLFlowStorage(tracking_uri="http://mlflow:5000")

    callback = MLFlowStorageCallback(
        storage=mlflow_storage,
        model_reuse_enable=True,
        model_reuse_max_age=timedelta(days=7),
        model_selection_enable=True,
    )

    workflow = CustomForecastingWorkflow(
        model=build_my_model(),   # your ForecastingModel instance
        model_id="substation_42",
        run_name="scheduled_retrain",
        callbacks=[callback],
    )

    # --- 3. Train (skipped automatically if a recent model exists) ---
    fit_result = workflow.fit(dataset)
    if fit_result is not None:
        logger.info("Retrained. R2 = %s", fit_result.metrics_full)

    # --- 4. Predict and write output ---
    forecast = workflow.predict(dataset)
    write_forecast(forecast)   # push to your database / message bus

The ``MLFlowStorageCallback`` handles model reuse automatically: if a run younger than
``model_reuse_max_age`` already exists in MLflow, ``fit()`` skips retraining and loads
the existing model instead. This makes it safe to call the same script on every
scheduling tick without unnecessary retraining.

-----------

Model Persistence
-----------------

Two storage backends are available out of the box.

**Local filesystem (development and single-machine deployments)**

``JoblibModelSerializer`` serialises models to ``.pkl`` files in a directory you
specify. It is the simplest option and requires no external services:

.. code-block:: python

    from pathlib import Path
    from openstef_models.integrations.joblib import JoblibModelSerializer

    serializer = JoblibModelSerializer()
    # Save
    with open(Path("/models/substation_42.pkl"), "wb") as f:
        serializer.dump(model, f)

    # Load
    with open(Path("/models/substation_42.pkl"), "rb") as f:
        model = serializer.load(f)

.. warning::

   Joblib uses Python's pickle protocol. Never load a ``.pkl`` file from an untrusted
   source, as it can execute arbitrary code on deserialisation.

**MLflow (recommended for production)**

``MLFlowStorage`` stores models, hyperparameters, metrics, and feature-importance plots
in an MLflow tracking server. It also enables the model-reuse and model-selection
logic built into ``MLFlowStorageCallback``:

.. code-block:: python

    from openstef_models.integrations.mlflow import MLFlowStorage

    storage = MLFlowStorage(
        tracking_uri="http://mlflow.internal:5000",
        local_artifacts_path="/tmp/mlflow_artifacts",
    )

Point ``tracking_uri`` at a remote MLflow server for shared access across multiple
workers. The ``local_artifacts_path`` is a scratch directory used to stage files before
uploading.

-----------

Containerisation
----------------

Packaging the job as a Docker image ensures that the Python environment is identical
across development, CI, and production.

A minimal ``Dockerfile``:

.. code-block:: text

    FROM python:3.11-slim

    WORKDIR /app

    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY forecast_job.py .

    CMD ["python", "forecast_job.py"]

A matching ``requirements.txt`` should pin your OpenSTEF packages:

.. code-block:: text

    openstef-core==<version>
    openstef-models==<version>
    openstef-beam==<version>

Pass runtime configuration (MLflow URI, data source credentials, target IDs) through
environment variables rather than baking them into the image:

.. code-block:: python

    import os
    from openstef_models.integrations.mlflow import MLFlowStorage

    storage = MLFlowStorage(
        tracking_uri=os.environ["MLFLOW_TRACKING_URI"],
    )

-----------

Scheduled Execution
-------------------

**Cron (Linux / macOS)**

For a single machine, a crontab entry is often sufficient:

.. code-block:: text

    # Run every 15 minutes
    */15 * * * * /usr/bin/python /app/forecast_job.py >> /var/log/openstef.log 2>&1

**Kubernetes CronJob**

For containerised deployments, a Kubernetes ``CronJob`` provides automatic retries and
resource limits:

.. code-block:: text

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
              restartPolicy: OnFailure
              containers:
                - name: forecast
                  image: <your-registry>/openstef-forecast:<tag>
                  env:
                    - name: MLFLOW_TRACKING_URI
                      valueFrom:
                        secretKeyRef:
                          name: mlflow-secret
                          key: uri
                    - name: DATA_SOURCE_URI
                      valueFrom:
                        secretKeyRef:
                          name: datasource-secret
                          key: uri
                  resources:
                    requests:
                      memory: "1Gi"
                      cpu: "500m"
                    limits:
                      memory: "4Gi"
                      cpu: "2"

**Cloud schedulers**

Most cloud providers offer a managed equivalent:

- **AWS** — EventBridge Scheduler triggering an ECS Fargate task or a Lambda function.
- **Azure** — Azure Container Apps Jobs with a CRON trigger, or Azure Data Factory
  pipelines for more complex dependency graphs.
- **GCP** — Cloud Scheduler invoking a Cloud Run Job.

The pattern is the same in all cases: the scheduler starts a container (or serverless
function) that runs your entry-point script and exits.

-----------

Workflow Orchestration
----------------------

When you have many forecasting targets, or when training and prediction must run on
different schedules, a workflow orchestrator adds value. OpenSTEF integrates naturally
with any orchestrator because each workflow step is an ordinary Python function call.

A simple Airflow DAG that separates the retraining and prediction steps:

.. code-block:: python

    # dags/openstef_dag.py
    from datetime import datetime, timedelta
    from airflow.decorators import dag, task

    @dag(
        schedule="0 2 * * *",        # retrain daily at 02:00
        start_date=datetime(2024, 1, 1),
        catchup=False,
        default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    )
    def openstef_daily_retrain():

        @task()
        def retrain(target_id: str):
            from openstef_models.workflows import CustomForecastingWorkflow
            # load data, build workflow, call workflow.fit(dataset)
            ...

        @task()
        def predict(target_id: str):
            from openstef_models.workflows import CustomForecastingWorkflow
            # load data, build workflow, call workflow.predict(dataset)
            ...

        targets = ["substation_42", "substation_43", "substation_44"]
        for target in targets:
            retrain(target) >> predict(target)

    openstef_daily_retrain()

Because ``CustomForecastingWorkflow`` is a plain Python object, it can be instantiated
inside any task function without special adapters.

-----------

Monitoring and Evaluation
-------------------------

**MLflow experiment tracking**

When ``MLFlowStorageCallback`` is attached, every training run automatically logs:

- Model hyperparameters (including per-component hyperparameters for ensembles).
- Evaluation metrics (R², MAE, and others) on the full training set and the held-out
  test split.
- Feature-importance plots for all explainable model components.
- The serialised model artifact.

You can query recent runs programmatically to build alerting logic:

.. code-block:: python

    from openstef_models.integrations.mlflow import MLFlowStorage
    from openstef_core.types import Q

    storage = MLFlowStorage(tracking_uri="http://mlflow.internal:5000")

    runs = storage.search_latest_runs(
        model_id="substation_42",
        limit=5,
        filter_string="attribute.status = 'FINISHED'",
        order_by=["start_time DESC"],
    )

    for run in runs:
        r2 = run.data.metrics.get("P50_R2")
        print(f"Run {run.info.run_id}: R2 = {r2}")
        if r2 is not None and r2 < 0.7:
            send_alert(f"Model quality degraded: R2={r2}")

**Structured evaluation with EvaluationPipeline**

For deeper post-hoc analysis — segmenting accuracy by lead time, time-of-day, or
season — use ``EvaluationPipeline`` from ``openstef_beam``:

.. code-block:: python

    from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
    from openstef_beam.evaluation import Window
    from datetime import timedelta

    config = EvaluationConfig(
        windows=[
            Window(duration=timedelta(days=7)),
            Window(duration=timedelta(days=30)),
        ],
    )

    pipeline = EvaluationPipeline(config=config)
    report = pipeline.run(forecast_dataset)

    # report.to_dataframe() gives a tidy DataFrame of metrics per segment
    print(report.to_dataframe())

**Application-level logging**

OpenSTEF uses Python's standard ``logging`` module throughout. Configure it at the
entry point of your job to capture structured output:

.. code-block:: python

    import logging
    import json

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps({
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            })

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.getLogger("openstef").addHandler(handler)
    logging.getLogger("openstef").setLevel(logging.INFO)

JSON-formatted logs integrate directly with cloud log aggregators (CloudWatch,
Stackdriver, Azure Monitor) and can be queried for error rates or latency trends.

-----------

Summary
-------

The table below maps deployment scale to the recommended combination of components:

.. list-table::
   :header-rows: 1
   :widths: 20 30 25 25

   * - Scale
     - Scheduler
     - Model storage
     - Monitoring
   * - Single machine
     - cron
     - ``JoblibModelSerializer``
     - Log files
   * - Small cluster
     - Kubernetes CronJob
     - MLflow (self-hosted)
     - MLflow UI + structured logs
   * - Cloud / many targets
     - Airflow / Prefect / cloud scheduler
     - MLflow (managed or self-hosted)
     - MLflow + ``EvaluationPipeline`` + alerting

Start with the simplest pattern that meets your reliability requirements and scale up
as needed. Because OpenSTEF is a library, each layer of the stack is independently
replaceable.