Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from simple
scheduled scripts to fully orchestrated pipelines. It addresses containerization,
cloud deployment, model persistence with MLflow, and basic operational monitoring.

For reading data from external systems (S3, Databricks, InfluxDB), see
:doc:`data_integration`. For logging configuration, see :doc:`logging`.

.. note:: [DIAGRAM: Overview of a production OpenSTEF deployment — data sources feed into a scheduled runner, which calls the forecasting workflow, persists models via MLflow, and writes forecasts to a downstream store.]

Deployment Patterns
-------------------

OpenSTEF is a Python library, not a server or daemon. A production deployment is
simply a Python process — or a set of processes — that calls OpenSTEF's workflow
APIs on a schedule. How you schedule and host that process is entirely up to you.
Three common patterns are described below, in increasing order of operational
complexity.

**Cron / scheduled job**
  The simplest option. A Python script is executed on a fixed schedule (e.g. every
  15 minutes) by cron, a cloud scheduler, or a CI/CD timer. Suitable for a small
  number of forecasting locations with modest data volumes.

**Container-based task**
  The script is packaged as a Docker image and executed as a one-shot container by
  a container orchestrator (Kubernetes CronJob, AWS ECS Scheduled Task, Azure
  Container Apps job, etc.). This gives you reproducible environments, easy scaling,
  and straightforward secret management.

**Workflow orchestration platform**
  For larger deployments, tools such as Dagster, Apache Airflow, or Prefect can
  manage dependencies between training and prediction tasks, handle retries, and
  surface run history. OpenSTEF integrates naturally because each workflow call is
  a plain Python function.

The following sections show concrete examples of each pattern.

Simple Scheduled Script
-----------------------

The entry point for any deployment is a script that builds a
``CustomForecastingWorkflow``, loads data, and calls ``fit`` and/or ``predict``.
The example below shows the minimal structure:

.. code-block:: python

    # forecast_job.py
    import logging
    from datetime import timedelta

    import pandas as pd
    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.models.forecasting.xgb_forecaster import XGBForecaster
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )
    from openstef_models.integrations.mlflow.mlflow_storage import MLflowStorage
    from openstef_models.integrations.mlflow.mlflow_storage_callback import (
        MLFlowStorageCallback,
    )

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    MODEL_ID = "substation_amsterdam_001"
    MLFLOW_TRACKING_URI = "http://mlflow.internal:5000"

    def load_data() -> VersionedTimeSeriesDataset:
        # Replace with your actual data source — see the data_integration page
        df = pd.read_parquet("s3://my-bucket/features/amsterdam_001.parquet")
        return VersionedTimeSeriesDataset(
            data=df,
            sample_interval=timedelta(minutes=15),
        )

    def run_forecast():
        storage = MLflowStorage(tracking_uri=MLFLOW_TRACKING_URI)
        mlflow_cb = MLFlowStorageCallback(storage=storage)

        horizons = [LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")]
        model = ForecastingModel(
            forecaster=XGBForecaster(horizons=horizons, quantiles=[Q(0.1), Q(0.5), Q(0.9)]),
        )

        # Load existing model from storage, fall back to the fresh model if none exists
        workflow = ForecastingWorkflow.from_storage(
            model_id=MODEL_ID,
            storage=storage,
            fallback_model=model,
            callbacks=[mlflow_cb],
        )

        dataset = load_data()
        forecasts = workflow.predict(dataset)
        logger.info("Generated %d forecast rows for %s", len(forecasts.data), MODEL_ID)
        # Write forecasts to your downstream store here

    if __name__ == "__main__":
        run_forecast()

A separate training job (run less frequently, e.g. nightly or weekly) calls
``workflow.fit(dataset)`` instead of ``workflow.predict``. Keeping training and
prediction as separate invocations makes each job simpler to reason about and
easier to retry independently.

Containerization
----------------

Packaging the script as a Docker image ensures that the Python version, library
versions, and system dependencies are identical across development, staging, and
production.

A minimal ``Dockerfile`` for an OpenSTEF forecasting job:

.. code-block:: dockerfile

    FROM python:3.12-slim

    WORKDIR /app

    # Install uv for fast dependency resolution
    RUN pip install --no-cache-dir uv

    COPY pyproject.toml uv.lock ./
    RUN uv sync --no-dev --frozen

    COPY forecast_job.py ./

    # Run as a non-root user
    RUN useradd --create-home appuser
    USER appuser

    CMD ["uv", "run", "python", "forecast_job.py"]

A matching ``pyproject.toml`` pinning the relevant OpenSTEF packages:

.. code-block:: toml

    [project]
    name = "my-forecast-service"
    version = "1.0.0"
    requires-python = ">=3.12"
    dependencies = [
        "openstef-models>=4.0",
        "openstef-core>=4.0",
    ]

.. note::

   Pass secrets (MLflow credentials, cloud storage keys) via environment variables
   or a secrets manager — never bake them into the image. Use ``os.environ`` or a
   library like ``python-dotenv`` to read them at runtime.

Cloud Deployment Options
------------------------

The container image above can be deployed to any cloud platform that supports
scheduled container execution. The table below summarises common choices:

- **Kubernetes CronJob** — full control, works on any Kubernetes cluster (AKS, EKS,
  GKE, on-premises). Define a ``CronJob`` manifest that pulls your image and runs
  on the desired schedule.
- **AWS ECS Scheduled Tasks** — managed container execution without Kubernetes
  overhead. Pair with EventBridge Scheduler for cron expressions.
- **Azure Container Apps Jobs** — serverless scheduled jobs with built-in secret
  integration via Key Vault references.
- **Google Cloud Run Jobs** — pay-per-use execution, triggered by Cloud Scheduler.

Below is an example Kubernetes ``CronJob`` manifest that runs the prediction job
every 15 minutes:

.. code-block:: yaml

    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: openstef-predict
      namespace: forecasting
    spec:
      schedule: "*/15 * * * *"
      concurrencyPolicy: Forbid          # prevent overlapping runs
      successfulJobsHistoryLimit: 3
      failedJobsHistoryLimit: 5
      jobTemplate:
        spec:
          template:
            spec:
              restartPolicy: OnFailure
              containers:
                - name: forecast-job
                  image: myregistry.azurecr.io/openstef-forecast:1.0.0
                  env:
                    - name: MLFLOW_TRACKING_URI
                      valueFrom:
                        secretKeyRef:
                          name: mlflow-secret
                          key: tracking-uri
                    - name: AWS_DEFAULT_REGION
                      value: eu-west-1
                  resources:
                    requests:
                      cpu: "500m"
                      memory: "1Gi"
                    limits:
                      cpu: "2"
                      memory: "4Gi"

Adjust ``resources`` based on the number of forecasting locations and the size of
your feature matrices. XGBoost training in particular benefits from more CPU cores.

Model Persistence with MLflow
------------------------------

OpenSTEF's ``MLFlowStorageCallback`` integrates model lifecycle management directly
into the workflow. When attached to a ``CustomForecastingWorkflow``, it
automatically:

- Logs hyperparameters and training metrics to an MLflow experiment on each fit
- Stores the serialised model as a run artefact
- Supports **model reuse**: if a recent run already exists for a given
  ``model_id``, re-training can be skipped to save compute
- Supports **model selection**: automatically promotes the best-performing run
  based on a configurable metric

.. code-block:: python

    from openstef_models.integrations.mlflow.mlflow_storage import MLflowStorage
    from openstef_models.integrations.mlflow.mlflow_storage_callback import (
        MLFlowStorageCallback,
    )

    storage = MLflowStorage(tracking_uri="http://mlflow.internal:5000")

    mlflow_cb = MLFlowStorageCallback(
        storage=storage,
        model_reuse_enable=True,
        model_reuse_max_age=timedelta(days=7),   # skip re-train if model < 7 days old
        model_selection_enable=True,
        model_selection_metric="rmse",
    )

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="substation_amsterdam_001",
        callbacks=[mlflow_cb],
    )

At prediction time, ``ForecastingWorkflow.from_storage`` loads the most recent
finished run for the given ``model_id``, so the prediction job never needs to
know which specific run produced the active model.

.. note::

   You can run a self-hosted MLflow tracking server, or use a managed offering
   such as Azure ML, Databricks MLflow, or AWS SageMaker Experiments — all expose
   the same MLflow tracking API.

Workflow Orchestration
-----------------------

For deployments with many forecasting locations, or where training and prediction
have explicit dependencies, a workflow orchestration platform adds significant
value. OpenSTEF's library design makes integration straightforward: each workflow
call is a plain Python function that can be wrapped in a task.

The following sketch shows a Dagster asset-based pattern:

.. code-block:: python

    from dagster import asset, ScheduleDefinition, define_asset_job, AssetExecutionContext
    from my_project.openstef_helpers import build_workflow, load_dataset, write_forecasts

    @asset
    def trained_model(context: AssetExecutionContext):
        """Re-train the model nightly."""
        workflow = build_workflow(model_id="substation_amsterdam_001")
        dataset = load_dataset()
        workflow.fit(dataset)
        context.log.info("Training complete")

    @asset(deps=[trained_model])
    def forecasts(context: AssetExecutionContext):
        """Generate forecasts every 15 minutes."""
        workflow = build_workflow(model_id="substation_amsterdam_001")
        dataset = load_dataset()
        result = workflow.predict(dataset)
        write_forecasts(result)
        context.log.info("Wrote %d forecast rows", len(result.data))

    nightly_training = ScheduleDefinition(
        job=define_asset_job("train_job", selection=[trained_model]),
        cron_schedule="0 2 * * *",
    )

The same pattern applies to Airflow (wrap each step in a ``PythonOperator``) or
Prefect (wrap in a ``@task``).

Operational Monitoring
-----------------------

Because OpenSTEF is a library, operational monitoring uses the same tools you
would apply to any Python application. The key signals to track are:

**Job-level health**
  Monitor whether the scheduled job completes successfully and within its expected
  time window. Most orchestration platforms (Kubernetes, Dagster, Airflow) expose
  job success/failure metrics natively. Add an alerting rule on consecutive
  failures.

**Forecast quality**
  Use ``openstef-beam``'s ``EvaluationPipeline`` to compute metrics (e.g. RMSE,
  calibration) across rolling time windows and lead times. Run this as a separate
  periodic job and push results to your metrics store.

**Custom callbacks**
  ``ForecastingCallback`` hooks (``on_fit_end``, ``on_predict_end``) are the
  natural place to emit application metrics. For example:

  .. code-block:: python

      import time
      from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback

      class PrometheusCallback(ForecastingCallback):
          def on_predict_end(self, context, data, forecasts):
              forecast_rows.labels(model_id=context.model_id).set(len(forecasts.data))
              last_predict_timestamp.labels(model_id=context.model_id).set(time.time())

  Attach this callback alongside ``MLFlowStorageCallback`` when constructing the
  workflow.

**Structured logging**
  Configure Python's ``logging`` module to emit JSON-structured logs so that your
  log aggregation platform (Datadog, Loki, CloudWatch) can filter and alert on
  error messages from OpenSTEF internals. See :doc:`logging` for recommended
  configuration.

.. note::

   OpenSTEF does not ship a built-in metrics server or health-check endpoint —
   these concerns belong to your deployment infrastructure. The callback system
   gives you the hooks to integrate with whatever observability stack you already
   use.

Further Reading
---------------

- :doc:`data_integration` — connecting OpenSTEF to S3, Databricks, InfluxDB, and
  other data sources
- :doc:`logging` — structured logging configuration and best practices
- :doc:`use_cases` — end-to-end examples for congestion management and other
  common scenarios