Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from simple
scheduled scripts to containerised services and full orchestration platforms. It assumes
you have already integrated your data sources (see :doc:`data_integration`) and have
working training and forecasting code. For logging configuration, see :doc:`logging`.

.. mermaid:: diagrams/user_guide/deployment_diagram_1.mmd

Overview
--------

OpenSTEF is a **library**, not a service. There is no long-running daemon to start; you
write Python scripts or functions that call OpenSTEF workflows, and then you decide how
and when those scripts run. This gives you full control over scheduling, infrastructure,
and observability while keeping the forecasting logic itself clean and portable.

A typical production setup involves two recurring jobs:

- **Training job** — re-trains models on fresh historical data, saves artifacts to
  storage (e.g. MLflow), and runs on a slower cadence (daily or weekly).
- **Forecasting job** — loads the latest trained model and generates predictions,
  runs on a faster cadence (hourly or every 15 minutes).

Both jobs are ordinary Python scripts and can run anywhere Python runs.

Structuring Your Jobs
---------------------

The ``openstef-models`` package provides ``CustomForecastingWorkflow`` and
``CustomComponentSplitWorkflow`` as the primary entry points for production use. Each
workflow accepts a model, a model identifier, and an optional callback object that hooks
into lifecycle events (fit start, fit end, predict start, predict end).

A minimal training script looks like this:

.. code-block:: python

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.integrations.mlflow import MLFlowStorageCallback
    from my_project.models import build_forecasting_model
    from my_project.data import load_training_data

    MODEL_ID = "substation_a_load"

    def run_training() -> None:
        data = load_training_data()

        workflow = CustomForecastingWorkflow(
            model=build_forecasting_model(),
            model_id=MODEL_ID,
            callbacks=MLFlowStorageCallback(),
        ).with_run_name("daily-retrain")

        workflow.fit(data)

    if __name__ == "__main__":
        run_training()

The corresponding forecasting script reuses the same workflow object. When
``MLFlowStorageCallback`` is attached, it automatically loads the latest saved model
from MLflow at predict time if the in-memory model is not already fitted:

.. code-block:: python

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.integrations.mlflow import MLFlowStorageCallback
    from my_project.models import build_forecasting_model
    from my_project.data import load_forecast_input, write_forecast_output

    MODEL_ID = "substation_a_load"

    def run_forecast() -> None:
        data = load_forecast_input()

        # Model is loaded from MLflow automatically via the callback
        workflow = CustomForecastingWorkflow(
            model=build_forecasting_model(),
            model_id=MODEL_ID,
            callbacks=MLFlowStorageCallback(),
        ).with_run_name("daily-retrain")

        forecast = workflow.predict(data)
        write_forecast_output(forecast)

    if __name__ == "__main__":
        run_forecast()

Keeping training and forecasting in separate scripts makes it straightforward to
schedule them independently and to restart one without affecting the other.

Scheduled Jobs
--------------

The simplest production deployment is a cron job or a cloud scheduler that invokes
your scripts on a fixed cadence. No additional infrastructure is required.

**Linux cron example** (retrain daily at 02:00, forecast every hour):

.. code-block:: bash

    # /etc/cron.d/openstef
    0  2 * * *  openstef  /opt/openstef/venv/bin/python /opt/openstef/train.py
    0  * * * *  openstef  /opt/openstef/venv/bin/python /opt/openstef/forecast.py

**Systemd timer** (preferred on modern Linux systems):

.. code-block:: ini

    # /etc/systemd/system/openstef-forecast.timer
    [Unit]
    Description=OpenSTEF hourly forecast

    [Timer]
    OnCalendar=hourly
    Persistent=true

    [Install]
    WantedBy=timers.target

.. code-block:: ini

    # /etc/systemd/system/openstef-forecast.service
    [Unit]
    Description=OpenSTEF forecast job

    [Service]
    Type=oneshot
    User=openstef
    ExecStart=/opt/openstef/venv/bin/python /opt/openstef/forecast.py
    EnvironmentFile=/etc/openstef/env

Containerisation
----------------

Packaging your jobs as Docker containers makes them portable across environments and
simplifies dependency management. The recommended approach is one image per job type,
using a minimal base image.

.. code-block:: dockerfile

    # Dockerfile
    FROM python:3.12-slim

    WORKDIR /app

    # Install uv for fast dependency resolution
    RUN pip install --no-cache-dir uv

    COPY pyproject.toml uv.lock ./
    RUN uv sync --no-dev --frozen

    COPY src/ ./src/

    # Default command runs the forecast job; override for training
    CMD ["uv", "run", "python", "-m", "my_project.forecast"]

Build and run:

.. code-block:: bash

    docker build -t openstef-forecast:latest .

    docker run --rm \
      --env-file .env \
      -v /data/mlflow:/mlflow \
      openstef-forecast:latest

Pass configuration through environment variables rather than baking it into the image.
A typical ``.env`` file for a containerised job:

.. code-block:: bash

    MLFLOW_TRACKING_URI=http://mlflow.internal:5000
    MLFLOW_EXPERIMENT_NAME=substation_a
    DATA_SOURCE_URL=postgresql://user:pass@db.internal/energy
    LOG_LEVEL=INFO

.. note::

   Mount MLflow artifact storage (or configure S3/GCS artifact URIs) so that model
   artifacts persist beyond the container lifecycle. See :doc:`data_integration` for
   storage backend patterns.

Cloud Deployment Options
------------------------

OpenSTEF jobs are stateless Python processes, which means they map cleanly onto most
cloud compute primitives.

**Kubernetes CronJob**

The most common pattern for teams already running Kubernetes:

.. code-block:: yaml

    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: openstef-forecast
    spec:
      schedule: "0 * * * *"
      concurrencyPolicy: Forbid
      jobTemplate:
        spec:
          template:
            spec:
              restartPolicy: OnFailure
              containers:
                - name: forecast
                  image: registry.example.com/openstef-forecast:latest
                  envFrom:
                    - secretRef:
                        name: openstef-secrets
                    - configMapRef:
                        name: openstef-config
                  resources:
                    requests:
                      memory: "1Gi"
                      cpu: "500m"
                    limits:
                      memory: "4Gi"
                      cpu: "2"

Set ``concurrencyPolicy: Forbid`` to prevent overlapping forecast runs if a job takes
longer than expected.

**Serverless / cloud functions**

For low-frequency jobs (e.g. daily retraining), serverless platforms such as AWS
Lambda, Google Cloud Run, or Azure Container Apps work well. The main constraint is
execution time limits — retraining large models may exceed function timeouts, in which
case a container-based approach is more appropriate.

**Managed workflow platforms**

If your organisation already uses Apache Airflow, Prefect, or Dagster, OpenSTEF jobs
integrate naturally as tasks or flows. Each workflow call (``workflow.fit``,
``workflow.predict``) is a single Python function call and requires no special adapter.

.. code-block:: python

    # Example: Airflow task using the TaskFlow API
    from airflow.decorators import dag, task
    from datetime import datetime

    @dag(schedule="0 * * * *", start_date=datetime(2024, 1, 1), catchup=False)
    def openstef_pipeline():

        @task()
        def forecast():
            from my_project.forecast import run_forecast
            run_forecast()

        forecast()

    openstef_pipeline()

Monitoring and Alerting
-----------------------

**MLflow experiment tracking**

``MLFlowStorageCallback`` records training metrics, hyperparameters, and model
artifacts automatically on every ``workflow.fit`` call. You can query recent runs
programmatically to detect degraded model performance:

.. code-block:: python

    from openstef_models.integrations.mlflow import MLFlowStorage

    storage = MLFlowStorage(tracking_uri="http://mlflow.internal:5000")

    runs = storage.search_latest_runs(
        model_id="substation_a_load",
        limit=5,
        filter_string="attribute.status = 'FINISHED'",
        order_by=["start_time DESC"],
    )

    for run in runs:
        print(run.info.run_id, run.data.metrics)

**Job-level health checks**

The simplest monitoring strategy is to treat a non-zero exit code as a failure and
route it to your alerting system (PagerDuty, Opsgenie, email, etc.). Wrap your entry
point in a try/except that logs the exception and exits with a non-zero code:

.. code-block:: python

    import logging
    import sys

    logger = logging.getLogger(__name__)

    def main() -> None:
        try:
            run_forecast()
        except Exception:
            logger.exception("Forecast job failed")
            sys.exit(1)

    if __name__ == "__main__":
        main()

**Staleness detection**

For production systems, it is worth checking that a forecast was actually produced
recently before serving it downstream. A simple approach is to record a ``last_success``
timestamp to a shared store (Redis, a database, or a file) at the end of each job and
alert if it is older than two forecast intervals.

**Structured logging**

Configure structured (JSON) logging so that log aggregators (Elasticsearch, Loki,
CloudWatch) can index and query your job output. See :doc:`logging` for OpenSTEF
logging configuration details.

Configuration Management
------------------------

Avoid hard-coding connection strings, model identifiers, or thresholds in your scripts.
A lightweight pattern is to load configuration from environment variables with
``pydantic-settings``:

.. code-block:: python

    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        mlflow_tracking_uri: str = "http://localhost:5000"
        model_id: str = "default_model"
        data_source_url: str

        class Config:
            env_file = ".env"

    settings = Settings()

This approach works identically in local development (reading from ``.env``), in
containers (reading from environment variables), and in Kubernetes (reading from
ConfigMaps and Secrets).

.. note::

   For multi-model deployments where you run the same job for many substations or
   assets, pass the ``model_id`` as a command-line argument or environment variable
   rather than running separate container images per model. A single parameterised job
   definition scales to hundreds of models without image proliferation.

Further Reading
---------------

- :doc:`data_integration` — connecting OpenSTEF to S3, Databricks, InfluxDB, and
  other data backends
- :doc:`logging` — structured logging configuration and best practices
- :doc:`use_cases` — end-to-end examples for common forecasting scenarios