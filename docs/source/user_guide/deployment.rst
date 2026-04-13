Production Deployment
=====================

This page covers practical patterns for deploying OpenSTEF in production environments, from simple scheduled scripts to fully orchestrated pipelines. It assumes you are already familiar with the core forecasting workflow — see :doc:`use_cases` for introductory examples and :doc:`data_integration` for connecting OpenSTEF to your data sources.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Introduction
------------

OpenSTEF is a Python library, not a standalone application. This means deployment is entirely in your hands: you write the orchestration code, choose the scheduler, and decide how models are stored and monitored. The upside is that OpenSTEF integrates naturally into whatever infrastructure you already operate — a simple cron job is enough to get started, and you can migrate to Kubernetes or Apache Airflow later without changing your forecasting logic.

The three main concerns when deploying OpenSTEF are:

- **Scheduling** — triggering training and prediction runs on a regular cadence
- **Model storage** — persisting trained models between runs and tracking experiment history
- **Observability** — surfacing errors, data quality issues, and forecast accuracy in production

Scheduled Jobs
--------------

The simplest production pattern is a Python script executed on a schedule. OpenSTEF's ``CustomForecastingWorkflow`` encapsulates both training and prediction, so a single script can handle both tasks.

.. code-block:: python

    # forecast_job.py
    import logging
    from datetime import timedelta
    from pathlib import Path

    import pandas as pd

    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.storage.local import LocalModelStorage

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    MODEL_ID = "grid_substation_42"
    STORAGE_DIR = Path("/var/openstef/models")


    def load_recent_data() -> pd.DataFrame:
        # Replace with your data source — see the data_integration guide
        ...


    def run_forecast():
        storage = LocalModelStorage(storage_dir=STORAGE_DIR)

        # Try to load an existing trained model; train from scratch if none exists
        try:
            workflow = CustomForecastingWorkflow.from_storage(
                model_id=MODEL_ID,
                storage=storage,
            )
            logger.info("Loaded existing model for %s", MODEL_ID)
        except Exception:
            logger.info("No existing model found — training from scratch")
            workflow = CustomForecastingWorkflow(
                model=ForecastingModel(...),
                model_id=MODEL_ID,
            )

        data = load_recent_data()
        forecasts = workflow.predict(data)
        logger.info("Generated %d forecast rows", len(forecasts.data))
        return forecasts


    if __name__ == "__main__":
        run_forecast()

Schedule this script with **cron** (Linux/macOS) or **Task Scheduler** (Windows). A typical setup runs prediction every 15 minutes and retraining once per day:

.. code-block:: text

    # /etc/cron.d/openstef
    */15 * * * *  openstef  python /opt/openstef/forecast_job.py --mode predict
    0    2 * * *  openstef  python /opt/openstef/forecast_job.py --mode train

For logging configuration in scheduled jobs, see :doc:`logging`.

Model Storage
-------------

OpenSTEF provides two storage backends out of the box. Choose based on your infrastructure.

**LocalModelStorage** serialises models to ``.pkl`` files on disk using ``joblib``. It is suitable for single-machine deployments, development environments, and situations where you do not need experiment tracking.

.. code-block:: python

    from pathlib import Path
    from openstef_models.storage.local import LocalModelStorage

    storage = LocalModelStorage(storage_dir=Path("/var/openstef/models"))
    # Models are stored as /var/openstef/models/<model_id>.pkl
    # The directory is created automatically if it does not exist

.. warning::

    ``LocalModelStorage`` uses ``joblib`` pickle serialisation. Never load model
    files from an untrusted source, as arbitrary code can execute during
    deserialisation.

**MLFlowStorage** records every training run — hyperparameters, metrics, feature importances, and the serialised model — to an MLflow tracking server. This is the recommended choice for production because it gives you a full audit trail and enables model comparison across runs.

.. code-block:: python

    from openstef_models.storage.mlflow import MLFlowStorage

    # Point at a remote MLflow server
    storage = MLFlowStorage(
        tracking_uri="http://mlflow.internal:5000",
        local_artifacts_path="/tmp/openstef_artifacts",
        experiment_name_prefix="substation_",
    )

    # Or use a local SQLite-backed server for single-machine setups
    storage = MLFlowStorage(
        tracking_uri="sqlite:///openstef_mlflow.db",
    )

The ``tracking_uri`` accepts HTTP(S) URLs for remote servers, SQLite connection strings, and local filesystem paths. Local paths are automatically normalised to ``file:///`` URIs.

Containerisation
----------------

Packaging your forecasting job as a Docker container makes it portable across environments and simplifies dependency management.

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    # Install OpenSTEF and your project dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY forecast_job.py .

    # Models and data are mounted at runtime — do not bake them into the image
    VOLUME ["/var/openstef/models", "/var/openstef/data"]

    CMD ["python", "forecast_job.py"]

A minimal ``requirements.txt`` for an OpenSTEF deployment:

.. code-block:: text

    openstef-models
    openstef-core
    mlflow
    pandas
    numpy

Build and run the container, mounting your model storage directory:

.. code-block:: bash

    docker build -t openstef-forecast:latest .
    docker run --rm \
        -v /var/openstef/models:/var/openstef/models \
        -e MLFLOW_TRACKING_URI=http://mlflow.internal:5000 \
        openstef-forecast:latest

Cloud Deployment
----------------

OpenSTEF jobs are stateless between runs (state lives in the model storage backend), which makes them a natural fit for cloud-native execution patterns.

**Kubernetes CronJob**

For teams already running Kubernetes, a ``CronJob`` resource provides reliable scheduling with automatic retries and log aggregation:

.. code-block:: yaml

    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: openstef-forecast
      namespace: energy
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
                  image: your-registry/openstef-forecast:latest
                  env:
                    - name: MLFLOW_TRACKING_URI
                      value: "http://mlflow-service:5000"
                  volumeMounts:
                    - name: model-storage
                      mountPath: /var/openstef/models
              volumes:
                - name: model-storage
                  persistentVolumeClaim:
                    claimName: openstef-models-pvc

Set ``concurrencyPolicy: Forbid`` to prevent overlapping runs if a job takes longer than its schedule interval.

**Cloud Functions / Serverless**

For lower-frequency retraining jobs (e.g. daily), serverless functions (AWS Lambda, Google Cloud Functions, Azure Functions) work well. The key consideration is cold-start time: loading a large model from object storage on every invocation adds latency. Mitigate this by:

- Keeping models in a fast-access store (e.g. EFS on AWS, Filestore on GCP)
- Caching the loaded workflow in the function's global scope between warm invocations
- Separating the prediction job (frequent, latency-sensitive) from the training job (infrequent, latency-tolerant)

Workflow Orchestration
----------------------

When you have multiple prediction locations, dependencies between jobs, or complex retry logic, a dedicated orchestration platform is worth the investment. OpenSTEF integrates with any Python-based orchestrator because it is a plain library.

**Apache Airflow** example — a DAG that retrains all substations in parallel and then runs prediction:

.. code-block:: python

    from datetime import datetime, timedelta
    from airflow import DAG
    from airflow.operators.python import PythonOperator

    SUBSTATION_IDS = ["sub_001", "sub_002", "sub_003"]

    default_args = {
        "owner": "energy-team",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    }

    with DAG(
        dag_id="openstef_daily_retrain",
        default_args=default_args,
        schedule_interval="0 2 * * *",
        start_date=datetime(2024, 1, 1),
        catchup=False,
    ) as dag:

        def train_substation(model_id: str):
            from openstef_models.workflows import CustomForecastingWorkflow
            # ... build and fit workflow for model_id
            ...

        def predict_substation(model_id: str):
            from openstef_models.workflows import CustomForecastingWorkflow
            # ... load workflow and run prediction
            ...

        train_tasks = [
            PythonOperator(
                task_id=f"train_{sid}",
                python_callable=train_substation,
                op_kwargs={"model_id": sid},
            )
            for sid in SUBSTATION_IDS
        ]

        predict_tasks = [
            PythonOperator(
                task_id=f"predict_{sid}",
                python_callable=predict_substation,
                op_kwargs={"model_id": sid},
            )
            for sid in SUBSTATION_IDS
        ]

        # All training must complete before prediction starts
        for train, predict in zip(train_tasks, predict_tasks):
            train >> predict

The same pattern applies to **Prefect**, **Dagster**, and other orchestrators — import OpenSTEF inside your task functions to avoid serialisation issues with the workflow objects.

Monitoring and Alerting
-----------------------

Production deployments need visibility into three things: job execution, data quality, and forecast accuracy.

**Job execution** is best handled at the infrastructure level. Kubernetes and Airflow both expose job success/failure metrics natively. For cron-based deployments, tools like `Healthchecks.io <https://healthchecks.io>`_ provide dead-man's-switch monitoring with a single HTTP ping at the end of each successful run.

**Data quality** issues (missing values, stale feeds, out-of-range readings) should be caught before forecasting begins. OpenSTEF's preprocessing pipeline will raise exceptions on severely malformed data, but you should add explicit checks in your data loading layer. See :doc:`data_integration` for patterns.

**Forecast accuracy** tracking is built into the MLflow integration. When you use ``MLFlowStorageCallback``, evaluation metrics are logged automatically on each training run and are visible in the MLflow UI. You can query them programmatically to trigger alerts when model performance degrades:

.. code-block:: python

    import mlflow
    from openstef_models.storage.mlflow import MLFlowStorage

    storage = MLFlowStorage(tracking_uri="http://mlflow.internal:5000")
    client = mlflow.MlflowClient(tracking_uri=storage.tracking_uri)

    # Fetch the latest run for a given experiment
    experiment = client.get_experiment_by_name("substation_sub_001")
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=1,
    )

    if runs:
        r2 = runs[0].data.metrics.get("r2_score", None)
        if r2 is not None and r2 < 0.7:
            # Send alert via your preferred channel
            print(f"WARNING: R² dropped to {r2:.3f} for sub_001")

For structured logging from within your OpenSTEF jobs, see :doc:`logging`.

Environment Configuration
--------------------------

Avoid hardcoding connection strings and paths in your scripts. Use environment variables and load them at startup:

.. code-block:: python

    import os
    from pathlib import Path
    from openstef_models.storage.mlflow import MLFlowStorage
    from openstef_models.storage.local import LocalModelStorage

    def get_storage():
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
        if tracking_uri:
            return MLFlowStorage(
                tracking_uri=tracking_uri,
                local_artifacts_path=Path(
                    os.environ.get("MLFLOW_ARTIFACTS_PATH", "/tmp/openstef_artifacts")
                ),
            )
        # Fall back to local storage for development
        return LocalModelStorage(
            storage_dir=Path(os.environ.get("MODEL_STORAGE_DIR", "./models"))
        )

This pattern lets the same codebase run locally with file-based storage and in production with a remote MLflow server, controlled entirely through environment variables — a natural fit for 12-factor application conventions and Kubernetes ``ConfigMap``/``Secret`` injection.

.. note::

   For details on connecting OpenSTEF to databases, object stores, and streaming
   platforms, see :doc:`data_integration`. For use-case-specific deployment
   patterns (congestion forecasting, capacity planning), see :doc:`use_cases`.