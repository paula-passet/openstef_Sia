Production Deployment
=====================

This page covers practical patterns for deploying OpenSTEF in production environments — from simple cron-based scheduled jobs to fully orchestrated cloud pipelines. It focuses on the mechanics of running training and prediction workflows reliably, persisting models, and monitoring forecast quality over time.

For reading data from external sources such as S3, Databricks, or InfluxDB, see :doc:`data_integration`. For use-case-specific pipeline configurations, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Core Deployment Pattern
-----------------------

Every OpenSTEF production deployment revolves around two recurring jobs:

- **Training job** — periodically retrains the model on fresh historical data and stores the result.
- **Prediction job** — loads the latest trained model and produces forecasts on demand or on a schedule.

These two jobs are intentionally decoupled. Training is expensive and runs infrequently (e.g., weekly); prediction is cheap and runs frequently (e.g., every 15 minutes or hourly).

The ``CustomForecastingWorkflow`` class from ``openstef_models`` is the primary entry point for both jobs. It accepts callbacks that handle side effects such as model persistence and experiment tracking, keeping the core workflow logic clean.

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    from openstef_models.workflows.forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.models.storage.local_model_storage import LocalModelStorage
    from openstef_core.datasets import VersionedTimeSeriesDataset

    logging.basicConfig(level=logging.INFO)

    # Shared storage — points to a directory on disk (or a mounted volume in containers)
    storage = LocalModelStorage(storage_dir=Path("/models/openstef"))

    workflow = CustomForecastingWorkflow(
        model_id="substation_amsterdam_west",
        storage=storage,
    )

Training Job
------------

The training job fits the model on a historical window and persists the result via the configured storage backend. Run this on a weekly or daily schedule depending on how quickly your load patterns drift.

.. code-block:: python

    from openstef_models.workflows.forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.models.storage.local_model_storage import LocalModelStorage
    from openstef_core.datasets import VersionedTimeSeriesDataset
    from pathlib import Path

    def run_training(training_data: VersionedTimeSeriesDataset) -> None:
        storage = LocalModelStorage(storage_dir=Path("/models/openstef"))

        workflow = CustomForecastingWorkflow(
            model_id="substation_amsterdam_west",
            storage=storage,
        )

        result = workflow.fit(training_data)
        print(f"Training complete. Metrics: {result.metrics_to_flat_dict()}")

The workflow automatically stores the fitted model under ``{storage_dir}/{model_id}.pkl``. The storage directory is created if it does not exist.

.. warning::

   ``LocalModelStorage`` uses ``joblib`` (pickle-based) serialization. Never load models from untrusted sources — doing so executes arbitrary Python code. In multi-tenant environments, restrict filesystem permissions on the model directory.

Prediction Job
--------------

The prediction job loads the most recently trained model and produces forecasts. Because the workflow checks ``model.is_fitted`` before attempting a load, you can safely call ``predict`` without manually managing model state.

.. code-block:: python

    from openstef_models.workflows.forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.models.storage.local_model_storage import LocalModelStorage
    from openstef_core.datasets import ForecastDataset
    from pathlib import Path

    def run_prediction(forecast_data: ForecastDataset):
        storage = LocalModelStorage(storage_dir=Path("/models/openstef"))

        workflow = CustomForecastingWorkflow(
            model_id="substation_amsterdam_west",
            storage=storage,
        )

        forecast = workflow.predict(forecast_data)
        return forecast

.. note:: [VISUALIZATION: Example forecast output plot showing probabilistic bands around the median prediction over a 48-hour horizon]

MLflow Integration
------------------

For production systems that need experiment tracking, model versioning, and metric history, swap ``LocalModelStorage`` for the MLflow-backed callback. This records every training run, stores feature importance plots, and enables model selection based on held-out metrics.

.. code-block:: python

    from openstef_models.integrations.mlflow.mlflow_storage_callback import (
        MLFlowStorageCallback,
    )
    from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage
    from openstef_models.workflows.forecasting_workflow import CustomForecastingWorkflow
    from datetime import timedelta

    mlflow_storage = MLFlowStorage(tracking_uri="http://mlflow-server:5000")

    callback = MLFlowStorageCallback(
        storage=mlflow_storage,
        model_reuse_enable=True,
        model_reuse_max_age=timedelta(days=7),
        model_selection_enable=True,
        model_selection_metric=("Q0.5", "R2", "higher_is_better"),
        store_feature_importance_plot=True,
    )

    workflow = CustomForecastingWorkflow(
        model_id="substation_amsterdam_west",
        callbacks=[callback],
    )

With ``model_selection_enable=True``, the callback compares the newly trained model against the incumbent using the configured metric. A penalty factor (default ``1.2``) biases selection toward the existing model, preventing unnecessary churn from small random improvements.

.. mermaid:: /diagrams/user_guide/deployment_diagram_2.mmd

Containerization
----------------

Packaging OpenSTEF jobs as containers makes deployments reproducible and portable across environments.

A minimal ``Dockerfile`` for a training or prediction job:

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    # Install OpenSTEF and dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY src/ ./src/

    # Model storage is mounted at runtime — do not bake models into the image
    VOLUME ["/models/openstef"]

    ENTRYPOINT ["python", "src/train.py"]

A matching ``requirements.txt``:

.. code-block:: text

    openstef-core
    openstef-models
    openstef-beam

Keep model artifacts outside the image. Mount a persistent volume (cloud storage bucket, NFS share, or a Kubernetes ``PersistentVolumeClaim``) at ``/models/openstef`` so that trained models survive container restarts and are shared between the training and prediction containers.

Scheduled Jobs
--------------

Simple Cron
^^^^^^^^^^^

For single-machine deployments, ``cron`` is often sufficient. A typical schedule runs training weekly and prediction every 15 minutes:

.. code-block:: text

    # Retrain every Sunday at 02:00
    0 2 * * 0  docker run --rm -v /data/models:/models/openstef openstef-train:latest

    # Predict every 15 minutes
    */15 * * * *  docker run --rm -v /data/models:/models/openstef openstef-predict:latest

Kubernetes CronJob
^^^^^^^^^^^^^^^^^^

For cloud-native deployments, a Kubernetes ``CronJob`` provides the same scheduling with automatic retries, resource limits, and log aggregation.

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
                  image: openstef-train:latest
                  env:
                    - name: MLFLOW_TRACKING_URI
                      value: "http://mlflow-service:5000"
                  volumeMounts:
                    - name: model-storage
                      mountPath: /models/openstef
              restartPolicy: OnFailure
              volumes:
                - name: model-storage
                  persistentVolumeClaim:
                    claimName: openstef-models-pvc

    ---
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
                - name: predict
                  image: openstef-predict:latest
                  env:
                    - name: MLFLOW_TRACKING_URI
                      value: "http://mlflow-service:5000"
                  volumeMounts:
                    - name: model-storage
                      mountPath: /models/openstef
              restartPolicy: OnFailure
              volumes:
                - name: model-storage
                  persistentVolumeClaim:
                    claimName: openstef-models-pvc

Cloud Deployment Options
------------------------

The table below summarises common cloud deployment patterns. All of them follow the same train/predict job structure — only the scheduling and storage backends differ.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Platform
     - Scheduling
     - Model Storage
   * - AWS
     - EventBridge + ECS Fargate tasks
     - S3 bucket mounted via s3fs, or MLflow on EC2/ECS
   * - Azure
     - Azure Container Apps Jobs or Azure ML pipelines
     - Azure Blob Storage or Azure ML model registry
   * - GCP
     - Cloud Scheduler + Cloud Run jobs
     - GCS bucket or Vertex AI model registry
   * - On-premise
     - Kubernetes CronJob or Airflow DAG
     - NFS / Ceph volume or self-hosted MLflow

For all cloud options, the recommended pattern is:

1. Store trained model artifacts in object storage (S3, GCS, Azure Blob).
2. Run MLflow tracking server backed by the same object storage for artifact URIs.
3. Pass ``MLFLOW_TRACKING_URI`` as an environment variable — no code changes needed between environments.

Apache Airflow
^^^^^^^^^^^^^^

For teams already running Airflow, the train and predict jobs map naturally to tasks in a DAG:

.. code-block:: python

    from airflow import DAG
    from airflow.providers.docker.operators.docker import DockerOperator
    from datetime import datetime, timedelta

    with DAG(
        dag_id="openstef_forecast",
        schedule_interval="*/15 * * * *",
        start_date=datetime(2024, 1, 1),
        catchup=False,
        default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    ) as dag:

        predict = DockerOperator(
            task_id="run_prediction",
            image="openstef-predict:latest",
            environment={"MLFLOW_TRACKING_URI": "http://mlflow:5000"},
            mounts=["/data/models:/models/openstef"],
            auto_remove=True,
        )

    # Separate weekly DAG for training
    with DAG(
        dag_id="openstef_train_weekly",
        schedule_interval="0 2 * * 0",
        start_date=datetime(2024, 1, 1),
        catchup=False,
    ) as train_dag:

        train = DockerOperator(
            task_id="run_training",
            image="openstef-train:latest",
            environment={"MLFLOW_TRACKING_URI": "http://mlflow:5000"},
            mounts=["/data/models:/models/openstef"],
            auto_remove=True,
        )

Monitoring
----------

Model Metric Tracking
^^^^^^^^^^^^^^^^^^^^^

When using ``MLFlowStorageCallback``, training metrics are automatically logged to MLflow after every run. Set up alerts on key metrics — for example, trigger a notification if the median-quantile R² drops below a threshold:

.. code-block:: python

    from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage

    storage = MLFlowStorage(tracking_uri="http://mlflow-server:5000")

    # Retrieve the latest run metrics for a model
    run = storage.find_run(model_id="substation_amsterdam_west", run_name="latest")
    if run is not None:
        r2 = run.data.metrics.get("Q0.5_R2", None)
        if r2 is not None and r2 < 0.80:
            print(f"WARNING: R2 degraded to {r2:.3f} — consider retraining.")

Operational Health Checks
^^^^^^^^^^^^^^^^^^^^^^^^^^

Beyond model quality, monitor the operational health of the jobs themselves:

- **Job completion** — alert if the prediction CronJob has not produced output within two scheduling intervals.
- **Model staleness** — alert if the model file modification time exceeds ``model_reuse_max_age`` (default 7 days). The ``MLFlowStorageCallback`` enforces this automatically by triggering a retrain, but an external check provides a safety net.
- **Data freshness** — if the input data pipeline stalls, the model will produce forecasts on stale features. Add a check that the most recent observation timestamp is within an expected window before invoking the prediction job. See :doc:`data_integration` for patterns to validate incoming data.

.. note::

   OpenSTEF does not ship a built-in alerting system. Integrate metric checks with your existing observability stack (Prometheus, Grafana, PagerDuty, etc.) by reading metrics from MLflow's REST API or by emitting structured log lines that your log aggregator can parse.

Configuration Management
------------------------

Avoid hardcoding model IDs, storage paths, and tracking URIs in job scripts. A simple pattern is to drive configuration from environment variables, which works uniformly across cron, Kubernetes, and Airflow:

.. code-block:: python

    import os
    from pathlib import Path
    from openstef_models.models.storage.local_model_storage import LocalModelStorage

    MODEL_ID = os.environ["OPENSTEF_MODEL_ID"]
    STORAGE_DIR = Path(os.environ.get("OPENSTEF_STORAGE_DIR", "/models/openstef"))
    MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI")

    if MLFLOW_URI:
        from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage
        storage = MLFlowStorage(tracking_uri=MLFLOW_URI)
    else:
        storage = LocalModelStorage(storage_dir=STORAGE_DIR)

This pattern lets you use ``LocalModelStorage`` locally and ``MLFlowStorage`` in CI/production without changing application code.

.. note::

   For multi-target deployments (many substations or grid points), iterate over a list of model IDs and run each as a separate workflow instance. Each model is stored independently under its own ``model_id``, so training and prediction jobs for different targets are fully isolated.