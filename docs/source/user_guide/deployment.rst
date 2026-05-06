Production Deployment
=====================

This page covers patterns for running OpenSTEF in production: from a simple cron job on a single machine to fully orchestrated pipelines on cloud infrastructure. It focuses on the operational concerns of scheduling, containerization, model persistence, and monitoring — not on how to build the forecasting pipeline itself (see :doc:`use_cases` for that).

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Choosing a Deployment Pattern
------------------------------

OpenSTEF is a library, so it has no built-in scheduler or server. You bring your own execution environment and call the library from it. Three patterns cover most production needs:

- **Cron / scheduled script** — simplest option; a Python script runs on a fixed schedule, reads data, trains or predicts, and writes results. Good for a handful of grid points on a single VM.
- **Container-based job** — the same script is packaged as a Docker image and executed by a container scheduler (Kubernetes CronJob, AWS ECS Scheduled Task, Azure Container Instances). Adds reproducibility and horizontal scaling.
- **Workflow orchestrator** — a platform such as Dagster, Airflow, or Prefect manages task dependencies, retries, and observability. Recommended when you have many prediction units, complex data dependencies, or strict SLA requirements.

All three patterns share the same core loop: load data → run ``workflow.fit()`` on a retraining schedule → run ``workflow.predict()`` on every forecast cycle → persist results.

Core Production Loop
--------------------

The ``CustomForecastingWorkflow`` class from ``openstef_models`` is the main entry point for production use. It combines model management, optional storage back-ends, and a callback system for monitoring.

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    import pandas as pd
    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.storage.local_model_storage import LocalModelStorage

    logger = logging.getLogger(__name__)

    def run_forecast_cycle(data: pd.DataFrame, model_dir: Path) -> pd.DataFrame:
        """Single forecast cycle: retrain if needed, then predict."""
        dataset = VersionedTimeSeriesDataset.from_dataframe(data)

        workflow = CustomForecastingWorkflow(
            model=ForecastingModel.from_preset("xgb"),
            storage=LocalModelStorage(model_dir=model_dir),
        )

        # fit() is a no-op when a fresh model already exists in storage
        result = workflow.fit(dataset)
        if result is not None:
            logger.info("Retrained model — MAE: %s", result.metrics_test)

        forecast = workflow.predict(dataset)
        return forecast.data

The workflow loads a previously trained model from storage on ``predict()`` and only retrains when ``fit()`` determines it is necessary (e.g., no model exists yet, or the model has expired). This makes the same script safe to call on both the training schedule and the prediction schedule.

Scheduled Script (Cron)
------------------------

For a single host, a crontab entry is sufficient. Create a script ``run_forecast.py`` that calls your production loop, then schedule it:

.. code-block:: bash

    # Predict every 15 minutes; retrain daily at 02:00
    */15 * * * *  /opt/venv/bin/python /opt/openstef/run_forecast.py --mode predict
    0    2 * * *  /opt/venv/bin/python /opt/openstef/run_forecast.py --mode train

Keep the two modes in one script and branch on a ``--mode`` argument so the same code path is tested end-to-end:

.. code-block:: python

    import argparse
    from pathlib import Path

    def main():
        parser = argparse.ArgumentParser()
        parser.add_argument("--mode", choices=["train", "predict"], required=True)
        args = parser.parse_args()

        data = load_data_from_source()   # see :doc:`data_integration`
        model_dir = Path("/var/openstef/models")

        if args.mode == "train":
            train(data, model_dir)
        else:
            forecast = predict(data, model_dir)
            write_results(forecast)

    if __name__ == "__main__":
        main()

.. note::

    Redirect stdout and stderr to a log file or a structured logging sink. Cron's default mail delivery is not suitable for production alerting.

Containerization
----------------

Packaging OpenSTEF as a Docker image makes the environment reproducible and portable across cloud providers.

**Dockerfile**

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    # Install dependencies first for layer caching
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY run_forecast.py .

    # Model storage is mounted at runtime — do not bake models into the image
    ENV MODEL_DIR=/mnt/models

    ENTRYPOINT ["python", "run_forecast.py"]

**requirements.txt** (minimum set):

.. code-block:: text

    openstef-core
    openstef-models
    openstef-beam

Mount a persistent volume at ``/mnt/models`` so trained models survive container restarts. On Kubernetes this is a ``PersistentVolumeClaim``; on cloud platforms it is typically a managed file share (Azure Files, AWS EFS, GCS Fuse).

**Kubernetes CronJob**

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
              containers:
                - name: openstef
                  image: <your-registry>/openstef:latest
                  args: ["--mode", "predict"]
                  env:
                    - name: MODEL_DIR
                      value: /mnt/models
                  volumeMounts:
                    - name: model-storage
                      mountPath: /mnt/models
              volumes:
                - name: model-storage
                  persistentVolumeClaim:
                    claimName: openstef-models-pvc
              restartPolicy: OnFailure

A separate ``CronJob`` with ``schedule: "0 2 * * *"`` and ``args: ["--mode", "train"]`` handles daily retraining.

Cloud Deployment Options
------------------------

OpenSTEF has no cloud-specific dependencies; the choice of platform is driven by your organisation's existing infrastructure.

**Azure**

- **Azure Container Instances** — run the Docker image as a scheduled container group via Logic Apps or Azure Scheduler. Simple, no cluster to manage.
- **Azure Machine Learning Pipelines** — use AML's ``CommandJob`` to run training; store models in an AML model registry instead of ``LocalModelStorage``.
- **Azure Databricks** — run OpenSTEF inside a Databricks notebook or job cluster. See :doc:`data_integration` for reading Delta tables as input.

**AWS**

- **ECS Scheduled Tasks** — equivalent to Kubernetes CronJob; attach an EFS volume for model persistence.
- **AWS Step Functions + Lambda** — suitable for lightweight prediction jobs; Lambda's 15-minute timeout may be a constraint for large training runs.
- **SageMaker Pipelines** — use a ``ProcessingStep`` to wrap the training script; SageMaker model registry replaces ``LocalModelStorage``.

**GCP**

- **Cloud Run Jobs** — trigger the container on a Cloud Scheduler schedule; mount a GCS bucket via GCS Fuse for model storage.
- **Vertex AI Pipelines** — wrap training and prediction as Kubeflow pipeline components.

Model Storage Back-ends
-----------------------

``LocalModelStorage`` writes versioned model artefacts to a local directory. For multi-node or cloud deployments, swap it for a remote back-end without changing any other code:

.. code-block:: python

    from openstef_models.storage.mlflow_storage import MLFlowStorage
    from pathlib import Path

    storage = MLFlowStorage(
        tracking_uri="https://mlflow.internal.example.com",
        local_artifacts_path=Path("/tmp/mlflow_artifacts"),
    )

    workflow = CustomForecastingWorkflow(
        model=ForecastingModel.from_preset("xgb"),
        storage=storage,
    )

MLflow provides a model registry, experiment tracking, and a UI for comparing training runs — useful when you are managing models for many grid points simultaneously.

Workflow Orchestration with Dagster
------------------------------------

For pipelines with many prediction units or complex data dependencies, a workflow orchestrator adds retries, dependency tracking, and a monitoring UI. The example below sketches a Dagster job:

.. code-block:: python

    from dagster import job, op, ScheduleDefinition, repository
    from pathlib import Path

    @op
    def fetch_measurements(context) -> dict:
        # Load from your data source — see :doc:`data_integration`
        return load_latest_measurements()

    @op
    def run_training(context, measurements: dict):
        for grid_point_id, data in measurements.items():
            model_dir = Path(f"/mnt/models/{grid_point_id}")
            train(data, model_dir)
            context.log.info("Trained model for %s", grid_point_id)

    @op
    def run_prediction(context, measurements: dict):
        results = {}
        for grid_point_id, data in measurements.items():
            model_dir = Path(f"/mnt/models/{grid_point_id}")
            results[grid_point_id] = predict(data, model_dir)
        write_all_results(results)

    @job
    def forecast_job():
        data = fetch_measurements()
        run_prediction(data)

    predict_schedule = ScheduleDefinition(job=forecast_job, cron_schedule="*/15 * * * *")

    @repository
    def openstef_repo():
        return [forecast_job, predict_schedule]

.. mermaid:: /diagrams/user_guide/deployment_diagram_2.mmd

Monitoring and Alerting
-----------------------

OpenSTEF's callback system is the primary hook for emitting operational metrics. Implement ``ForecastingCallback`` to push data to your monitoring stack:

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback
    from openstef_models.mixins.callbacks import WorkflowContext

    class PrometheusCallback(ForecastingCallback):
        """Emit forecast quality metrics to a Prometheus push gateway."""

        def on_fit_end(self, context, data, result):
            if result and result.metrics_test:
                mae = result.metrics_test.mae
                push_to_gateway(job="openstef_train", metrics={"mae": mae})

        def on_predict_end(self, context, data, forecast):
            push_to_gateway(
                job="openstef_predict",
                metrics={"forecast_horizon_h": forecast.horizon_hours},
            )

    workflow = CustomForecastingWorkflow(
        model=ForecastingModel.from_preset("xgb"),
        storage=LocalModelStorage(model_dir=Path("/mnt/models")),
        callbacks=[PrometheusCallback()],
    )

Beyond model quality metrics, monitor these operational signals:

- **Job completion** — alert if a prediction job has not run within 1.5× its expected interval.
- **Data freshness** — check that the input timestamp is recent before running a forecast; stale data produces misleading results silently.
- **Model age** — log a warning when the loaded model was trained more than N days ago.
- **Forecast range** — sanity-check that predicted values fall within physically plausible bounds for the grid point.

.. note::

    Structured logging (JSON lines to stdout) integrates cleanly with log aggregation platforms such as Loki, Datadog, or CloudWatch. Use Python's ``logging`` module with a JSON formatter rather than ``print`` statements.

Environment Configuration
--------------------------

Avoid hard-coding paths, URIs, or credentials. Use environment variables and read them at startup:

.. code-block:: python

    import os
    from pathlib import Path

    MODEL_DIR   = Path(os.environ["MODEL_DIR"])
    MLFLOW_URI  = os.environ.get("MLFLOW_TRACKING_URI", "")
    DATA_SOURCE = os.environ["DATA_SOURCE_URI"]   # see :doc:`data_integration`

For secrets (database passwords, API keys), use your platform's secret manager (Kubernetes Secrets, AWS Secrets Manager, Azure Key Vault) and inject them as environment variables at runtime. Never store credentials in the Docker image or in source control.

.. note::

    A ``pydantic-settings`` ``BaseSettings`` class is a clean way to validate all environment variables at import time, failing fast with a clear error message if a required variable is missing.

Related Pages
-------------

- :doc:`data_integration` — reading measurement data from S3, Databricks, InfluxDB, and other sources to feed into the deployment loop described here.
- :doc:`use_cases` — end-to-end examples for congestion management, EV charging, and grid loss forecasting that show what the production loop is actually computing.
- :doc:`migration_v3_v4` — if you are migrating an existing V3 deployment, this page covers the breaking API changes that affect production scripts.