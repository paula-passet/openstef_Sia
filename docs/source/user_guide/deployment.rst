Production Deployment
=====================

OpenSTEF is a Python library — it does not ship with a server or daemon of its own. Deploying it to production means embedding it inside whatever execution environment your organisation already uses, from a simple cron job to a full orchestration platform. This page covers the most common patterns: packaging your forecasting code, scheduling it reliably, persisting models, and tracking runs with MLflow.

For reading data from cloud stores and time-series databases, see :doc:`data_integration`. For use-case-specific pipeline designs, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Anatomy of a Production Forecasting Job
----------------------------------------

Regardless of the scheduler or platform you choose, every production OpenSTEF job performs the same logical steps:

1. **Fetch** recent measurements and weather features from your data source.
2. **Train or retrain** the model (possibly skipping if a recent run already exists).
3. **Predict** the next horizon and write results to your forecast sink.
4. **Log** metrics, artefacts, and the serialised model to a tracking store.

The ``CustomForecastingWorkflow`` class in ``openstef-models`` is the recommended entry point for all four steps. It wires together a ``BaseForecastingModel``, an optional model-persistence callback, and any custom lifecycle hooks you need.

.. code-block:: python

    import logging
    from pathlib import Path
    from datetime import timedelta

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.integrations.mlflow import MLFlowStorage
    from openstef_models.integrations.mlflow.mlflow_storage_callback import MLFlowStorageCallback

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Assume `model` and `dataset` are already constructed
    # (see data_integration.rst for loading patterns)

    workflow = CustomForecastingWorkflow(
        model_id="substation_a_load",
        model=model,
        callbacks=[
            MLFlowStorageCallback(
                storage=MLFlowStorage(
                    tracking_uri="http://mlflow.internal:5000",
                    local_artifacts_path=Path("/tmp/mlflow_artifacts"),
                    experiment_name_prefix="prod_",
                ),
                model_reuse_enable=True,
                model_reuse_max_age=timedelta(days=7),
                model_selection_enable=True,
            )
        ],
    )

    fit_result = workflow.fit(dataset)
    forecast = workflow.predict(dataset)

The ``model_reuse_enable`` flag is particularly important in production: when ``True``, the callback checks whether a recent run already exists in MLflow and skips retraining if the model is younger than ``model_reuse_max_age``. This prevents unnecessary compute on high-frequency schedules.

Model Persistence
-----------------

OpenSTEF provides two storage backends out of the box.

**Local filesystem (development and single-node deployments)**

``JoblibModelSerializer`` serialises models to ``.pkl`` files under a directory you control. It is the default serialiser used by ``MLFlowStorage`` and requires no additional infrastructure.

.. code-block:: python

    from pathlib import Path
    from openstef_models.integrations.joblib import JoblibModelSerializer
    from openstef_models.integrations.mlflow import MLFlowStorage

    storage = MLFlowStorage(
        tracking_uri=str(Path("./mlflow_tracking")),
        local_artifacts_path=Path("./mlflow_artifacts"),
        model_serializer=JoblibModelSerializer(),
    )

.. warning::

    Joblib serialisation is pickle-based. Never load model files from untrusted sources, as arbitrary code can execute during deserialisation.

**MLflow tracking server (recommended for production)**

Point ``tracking_uri`` at a remote MLflow server to gain a full experiment history, metric comparisons, and artefact versioning. The ``MLFlowStorageCallback`` handles uploading models, training data samples, evaluation metrics, and feature-importance plots automatically.

.. code-block:: python

    from openstef_models.integrations.mlflow import MLFlowStorage

    storage = MLFlowStorage(
        tracking_uri="http://mlflow.internal:5000",
        local_artifacts_path=Path("/tmp/mlflow_artifacts"),
        experiment_name_prefix="substation_",
        enable_mlflow_stdout=False,   # suppress emoji URLs in logs
    )

Containerisation
----------------

Packaging your forecasting job as a container image is the most portable way to deploy OpenSTEF. A minimal ``Dockerfile`` looks like this:

.. code-block:: dockerfile

    FROM python:3.12-slim

    WORKDIR /app

    # Install OpenSTEF with LightGBM support
    RUN pip install --no-cache-dir "openstef-models[lgbm]"

    COPY forecast_job.py .

    CMD ["python", "forecast_job.py"]

Keep secrets and environment-specific settings out of the image. Pass them as environment variables at runtime:

.. code-block:: bash

    docker run --rm \
      -e MLFLOW_TRACKING_URI="http://mlflow.internal:5000" \
      -e DATA_SOURCE_URL="postgresql://user:pass@db/energy" \
      -v /mnt/model-store:/models \
      my-org/openstef-job:latest

Inside ``forecast_job.py``, read these with ``os.environ``:

.. code-block:: python

    import os
    from pathlib import Path
    from openstef_models.integrations.mlflow import MLFlowStorage

    storage = MLFlowStorage(
        tracking_uri=os.environ["MLFLOW_TRACKING_URI"],
        local_artifacts_path=Path("/tmp/mlflow_artifacts"),
    )

Scheduling Patterns
-------------------

**Cron / systemd timers**

For simple single-node setups, a cron entry is often sufficient. Energy forecasting jobs typically run every 15 minutes (matching the PTU interval) or hourly:

.. code-block:: bash

    # /etc/cron.d/openstef-forecast
    */15 * * * *  openstef  /usr/bin/python /app/forecast_job.py >> /var/log/openstef.log 2>&1

Use ``flock`` or a similar mutex to prevent overlapping runs if the job occasionally takes longer than the interval.

**Kubernetes CronJob**

For cloud-native deployments, a Kubernetes ``CronJob`` provides automatic retries, log aggregation, and resource limits:

.. code-block:: yaml

    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: openstef-forecast
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
                  image: my-org/openstef-job:latest
                  env:
                    - name: MLFLOW_TRACKING_URI
                      valueFrom:
                        secretKeyRef:
                          name: openstef-secrets
                          key: mlflow_uri
                    - name: DATA_SOURCE_URL
                      valueFrom:
                        secretKeyRef:
                          name: openstef-secrets
                          key: data_source_url
                  resources:
                    requests:
                      cpu: "500m"
                      memory: "1Gi"
                    limits:
                      cpu: "2"
                      memory: "4Gi"

Set ``concurrencyPolicy: Forbid`` to mirror the ``flock`` pattern and avoid parallel runs writing conflicting model versions.

**Workflow orchestrators (Airflow, Prefect, Dagster)**

If your organisation already runs an orchestration platform, wrap each OpenSTEF workflow step in a task. The key principle is to keep the OpenSTEF library calls inside ordinary Python functions — no special integration layer is required:

.. code-block:: python

    # Example: Airflow task using the TaskFlow API
    from airflow.decorators import dag, task
    from datetime import datetime, timedelta

    @dag(schedule="*/15 * * * *", start_date=datetime(2025, 1, 1), catchup=False)
    def openstef_forecast_dag():

        @task()
        def run_forecast():
            from openstef_models.workflows import CustomForecastingWorkflow
            # ... build workflow, call workflow.fit() and workflow.predict()
            return "ok"

        run_forecast()

    openstef_forecast_dag()

Cloud Deployment Options
------------------------

OpenSTEF has no cloud-specific dependencies, so it runs on any compute service that can execute a Python process.

- **AWS**: Run the container image as an ECS Fargate task triggered by EventBridge Scheduler, or as a Lambda function for short-horizon jobs (within the 15-minute timeout). Store models on S3 and point ``tracking_uri`` at a managed MLflow instance or Amazon SageMaker Experiments.
- **Azure**: Use Azure Container Instances or AKS CronJobs. Azure ML can host the MLflow tracking server natively.
- **GCP**: Cloud Run Jobs support scheduled container execution with built-in retry logic. Vertex AI Experiments provides an MLflow-compatible tracking API.

In all cases the pattern is the same: the container image is environment-agnostic, and cloud-specific endpoints are injected via environment variables or a secrets manager.

Monitoring and Alerting
-----------------------

**Structured logging**

OpenSTEF uses Python's standard ``logging`` module throughout. Configure a JSON formatter to make logs queryable in your log aggregation platform:

.. code-block:: python

    import logging
    import json

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            return json.dumps({
                "time": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            })

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

**MLflow metrics as a health signal**

The ``MLFlowStorageCallback`` logs evaluation metrics (R², RMSE, skill scores) for every training run. Query these programmatically to detect model degradation:

.. code-block:: python

    import mlflow

    client = mlflow.tracking.MlflowClient(tracking_uri="http://mlflow.internal:5000")
    runs = client.search_runs(
        experiment_ids=["1"],
        order_by=["start_time DESC"],
        max_results=10,
    )
    for run in runs:
        r2 = run.data.metrics.get("P50_R2")
        if r2 is not None and r2 < 0.7:
            print(f"WARNING: R² dropped to {r2:.3f} in run {run.info.run_id}")

**Job-level alerting**

Wrap your entry-point script in a try/except block and emit a structured error event on failure. Most orchestrators (Kubernetes, Airflow, Prefect) can be configured to send notifications on job failure without any changes to the OpenSTEF code itself.

.. code-block:: python

    import sys
    import logging

    logger = logging.getLogger(__name__)

    try:
        fit_result = workflow.fit(dataset)
        forecast = workflow.predict(dataset)
    except Exception:
        logger.exception("Forecast job failed — alerting on-call")
        sys.exit(1)

Exiting with a non-zero code is sufficient for Kubernetes, systemd, and most CI/CD systems to register the job as failed and trigger their configured alert channels.

.. note::

    The ``model_selection_enable`` flag in ``MLFlowStorageCallback`` automatically compares the newly trained model against the previous best run and retains whichever scores higher (with a configurable penalty that biases selection towards newer models). This provides a lightweight safety net against sudden model quality regressions without requiring a separate evaluation step.