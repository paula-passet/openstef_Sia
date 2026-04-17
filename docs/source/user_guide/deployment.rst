Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from a simple cron-driven script to a fully orchestrated pipeline with model tracking and containerised execution. It focuses on the *how* of deployment — scheduling, persistence, monitoring, and infrastructure — rather than the forecasting logic itself. For data ingestion patterns see :doc:`data_integration`, and for use-case context see :doc:`use_cases`.

.. note:: [DIAGRAM: High-level deployment flow — data source → scheduled job → CustomForecastingWorkflow (fit / predict) → model storage (MLflow or local) → forecast sink → monitoring]

Core Deployment Unit
--------------------

Every production deployment of OpenSTEF revolves around ``CustomForecastingWorkflow``. A single workflow instance handles both training and inference, and its behaviour is extended through *callbacks* rather than subclassing. The minimal production loop looks like this:

.. code-block:: python

    import logging
    from pathlib import Path
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback
    from openstef_core.datasets import VersionedTimeSeriesDataset

    logger = logging.getLogger(__name__)

    TRACKING_URI = "/var/openstef/mlflow"
    ARTIFACTS_PATH = Path("/var/openstef/artifacts")

    def build_workflow(model_id: str) -> CustomForecastingWorkflow:
        storage = MLFlowStorage(
            tracking_uri=TRACKING_URI,
            local_artifacts_path=ARTIFACTS_PATH,
        )
        callback = MLFlowStorageCallback(
            storage=storage,
            model_reuse_enable=True,       # skip re-fit if a recent run exists
            model_selection_enable=True,   # keep the better model automatically
        )
        # build your ForecastingModel here (see the configuring_model_pipeline example)
        model = build_forecasting_model()
        return CustomForecastingWorkflow(
            model_id=model_id,
            model=model,
            callbacks=[callback],
        )

    def run_cycle(model_id: str, dataset: VersionedTimeSeriesDataset) -> None:
        workflow = build_workflow(model_id)
        fit_result = workflow.fit(dataset)
        if fit_result:
            logger.info("Training metrics:\n%s", fit_result.metrics_full.to_dataframe())
        forecast = workflow.predict(dataset)
        logger.info("Forecast tail:\n%s", forecast.data.tail())

The same ``workflow`` object is reused for both ``fit`` and ``predict``. In practice you will call ``fit`` on a longer cadence (daily or weekly) and ``predict`` on every scheduling interval (e.g. every 15 minutes or hourly).

Model Persistence
-----------------

OpenSTEF ships two storage backends out of the box.

**Local storage** is the simplest option and requires no external services. It is suitable for single-machine deployments or development environments:

.. code-block:: python

    from openstef_models.integrations.joblib import LocalModelStorage

    storage = LocalModelStorage(base_path=Path("/var/openstef/models"))

**MLflow storage** is recommended for production. It provides model versioning, experiment tracking, hyperparameter logging, and feature-importance artefacts with no extra code in your workflow:

.. code-block:: python

    from openstef_models.integrations.mlflow import MLFlowStorage

    # Point at a local directory, or a remote MLflow tracking server URI
    storage = MLFlowStorage(
        tracking_uri="http://mlflow.internal:5000",
        local_artifacts_path=Path("/tmp/openstef_artifacts"),
    )

When ``MLFlowStorageCallback`` is attached to a workflow it automatically logs hyperparameters, evaluation metrics, and serialised model artefacts on every ``fit`` call. The ``model_reuse_enable`` flag prevents unnecessary re-training when a sufficiently recent run already exists, which is useful when the training job runs more frequently than the model actually needs to be updated.

Scheduling Patterns
-------------------

Simple Cron Job
^^^^^^^^^^^^^^^

For many operators a cron job is sufficient. Write a standalone Python script that loads data, calls ``run_cycle``, and exits. Schedule it with the system cron or a cloud scheduler (AWS EventBridge, GCP Cloud Scheduler, Azure Logic Apps):

.. code-block:: bash

    # /etc/cron.d/openstef
    # Retrain daily at 06:00, forecast every 15 minutes
    0 6 * * *  openstef  python /opt/openstef/train.py  >> /var/log/openstef/train.log 2>&1
    */15 * * * * openstef  python /opt/openstef/forecast.py >> /var/log/openstef/forecast.log 2>&1

Keep ``train.py`` and ``forecast.py`` as thin entry points that import and call your workflow functions. This separation makes it easy to promote the same code to a more sophisticated scheduler later.

Workflow Orchestrators
^^^^^^^^^^^^^^^^^^^^^^

For teams that already use Apache Airflow, Prefect, or Dagster, wrapping the workflow in a task is straightforward:

.. code-block:: python

    # Airflow example — airflow/dags/openstef_forecast.py
    from datetime import datetime, timedelta
    from airflow.decorators import dag, task

    @dag(schedule="*/15 * * * *", start_date=datetime(2024, 1, 1), catchup=False)
    def openstef_forecast():

        @task()
        def load_data() -> dict:
            # load from your source — see the data_integration page
            dataset = fetch_latest_dataset()
            return dataset.model_dump()

        @task()
        def run_forecast(dataset_dict: dict) -> None:
            from openstef_core.datasets import VersionedTimeSeriesDataset
            dataset = VersionedTimeSeriesDataset.model_validate(dataset_dict)
            run_cycle(model_id="grid_connection_A", dataset=dataset)

        run_forecast(load_data())

    openstef_forecast()

The same pattern applies to Prefect flows and Dagster ops — the OpenSTEF workflow is always a plain Python callable, so it slots into any orchestrator without special adapters.

Containerisation
----------------

Packaging OpenSTEF in a container makes deployments reproducible and portable across cloud environments.

A minimal ``Dockerfile``:

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    # Install OpenSTEF and its optional MLflow integration
    RUN pip install --no-cache-dir \
        openstef-core \
        openstef-models[mlflow] \
        openstef-beam

    COPY src/ ./src/
    COPY entrypoint.py .

    # Persist models and MLflow tracking outside the container
    VOLUME ["/var/openstef/mlflow", "/var/openstef/artifacts"]

    ENV MLFLOW_TRACKING_URI=/var/openstef/mlflow
    ENV LOG_LEVEL=INFO

    ENTRYPOINT ["python", "entrypoint.py"]

Build and run:

.. code-block:: bash

    docker build -t openstef-forecaster:latest .

    # Training run
    docker run --rm \
      -v openstef_mlflow:/var/openstef/mlflow \
      -v openstef_artifacts:/var/openstef/artifacts \
      -e MODE=train \
      openstef-forecaster:latest

    # Forecast run
    docker run --rm \
      -v openstef_mlflow:/var/openstef/mlflow \
      -v openstef_artifacts:/var/openstef/artifacts \
      -e MODE=forecast \
      openstef-forecaster:latest

Mount the MLflow tracking directory as a named volume (or point ``MLFLOW_TRACKING_URI`` at a remote server) so that model artefacts survive container restarts.

Cloud Deployment Options
------------------------

The container above can be deployed on any cloud platform without modification. Common patterns:

- **AWS**: Run the container as an ECS Fargate task triggered by EventBridge Scheduler. Store MLflow artefacts in S3 by setting ``tracking_uri`` to an S3 path or pointing at a self-hosted MLflow server on EC2/ECS.
- **GCP**: Use Cloud Run Jobs for scheduled execution. Mount a Cloud Filestore volume or use a GCS-backed MLflow server for artefact storage.
- **Azure**: Azure Container Instances or AKS CronJobs work well. Azure Blob Storage can back an MLflow tracking server deployed alongside the forecaster.
- **Kubernetes**: A ``CronJob`` resource runs the container on schedule. Use a ``PersistentVolumeClaim`` for local MLflow storage, or point at a centralised MLflow deployment in the cluster.

.. note::

   When running multiple forecasters in parallel (one per grid connection, for example), give each workflow a unique ``model_id``. MLflow will create a separate experiment per ``model_id``, keeping runs isolated.

Monitoring and Observability
----------------------------

Workflow Callbacks
^^^^^^^^^^^^^^^^^^

The ``ForecastingCallback`` interface provides hooks at every stage of the workflow lifecycle. Use it to push metrics to your monitoring stack without modifying the core workflow:

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback

    class PrometheusCallback(ForecastingCallback):
        """Push training and forecast metrics to a Prometheus Pushgateway."""

        def on_fit_end(self, context, result):
            if result and result.metrics_test is not None:
                mae = result.metrics_test.to_dataframe()["mae"].iloc[0]
                push_to_gateway("http://pushgateway:9091", job="openstef_train",
                                registry=build_gauge("openstef_train_mae", mae))

        def on_predict_end(self, context, forecast):
            n_points = len(forecast.data)
            push_to_gauge("openstef_forecast_points_total", n_points)

Attach the callback alongside ``MLFlowStorageCallback`` when constructing the workflow:

.. code-block:: python

    workflow = CustomForecastingWorkflow(
        model_id="grid_connection_A",
        model=model,
        callbacks=[mlflow_callback, PrometheusCallback()],
    )

MLflow Experiment Tracking
^^^^^^^^^^^^^^^^^^^^^^^^^^

When ``MLFlowStorageCallback`` is active, every training run is automatically recorded in MLflow with:

- All model hyperparameters and per-component hyperparameters
- Full and test-set evaluation metrics
- Feature importance plots
- The serialised model artefact

You can query these programmatically to detect model drift or degraded accuracy:

.. code-block:: python

    import mlflow

    client = mlflow.MlflowClient(tracking_uri="http://mlflow.internal:5000")
    runs = client.search_runs(
        experiment_ids=["grid_connection_A"],
        order_by=["start_time DESC"],
        max_results=10,
    )
    for run in runs:
        print(run.info.run_id, run.data.metrics.get("test_mae"))

.. note:: [VISUALIZATION: MLflow UI showing experiment runs for a single model_id, with MAE trend over time and hyperparameter columns]

Structured Logging
^^^^^^^^^^^^^^^^^^

OpenSTEF uses Python's standard ``logging`` module throughout. Configure structured JSON logging in production to make logs queryable in tools like Loki, CloudWatch, or Datadog:

.. code-block:: python

    import logging
    import json

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps({
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "model_id": getattr(record, "model_id", None),
            })

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.getLogger("openstef").addHandler(handler)
    logging.getLogger("openstef").setLevel(logging.INFO)

Configuration Management
------------------------

Avoid hardcoding connection strings and paths. Use environment variables or a secrets manager and read them at startup:

.. code-block:: python

    import os
    from pathlib import Path
    from openstef_models.integrations.mlflow import MLFlowStorage

    storage = MLFlowStorage(
        tracking_uri=os.environ["MLFLOW_TRACKING_URI"],
        local_artifacts_path=Path(os.environ.get("ARTIFACTS_PATH", "/tmp/openstef")),
    )

For Kubernetes deployments, inject secrets via ``envFrom`` referencing a ``Secret`` object. For AWS, use Secrets Manager with the ECS secrets injection. Never bake credentials into the container image.

.. note::

   The ``model_reuse_enable`` and ``model_selection_enable`` flags on ``MLFlowStorageCallback`` are particularly valuable in production. They prevent redundant training runs and automatically retain the best-performing model, reducing both compute cost and the risk of deploying a regressed model.

Related Pages
-------------

- :doc:`data_integration` — how to read live data from S3, Databricks, InfluxDB, and other sources into the ``VersionedTimeSeriesDataset`` expected by the workflow.
- :doc:`use_cases` — end-to-end examples for congestion forecasting and other common scenarios that can be adapted as deployment templates.
- :doc:`migration_v3_v4` — if you are upgrading an existing deployment, consult this guide for breaking changes in the workflow and storage APIs.