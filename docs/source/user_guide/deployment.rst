Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production — from a simple cron job on a single machine to a fully orchestrated, containerised pipeline in the cloud. It focuses on the *how* of deployment: packaging, scheduling, model storage, and monitoring. For details on reading data from external sources, see :doc:`data_integration`.

.. note:: [DIAGRAM: High-level deployment architecture showing a scheduler triggering a training job and a prediction job, both reading/writing to a model store (MLflow or local), with a monitoring callback emitting metrics to an observability platform]

Deployment Patterns
-------------------

OpenSTEF is a library, so there is no built-in server or daemon to run. A production deployment is simply a Python script — or a set of scripts — that calls the library on a schedule. The three most common patterns are:

- **Cron / scheduled job** — a Python script executed by cron, a cloud scheduler, or a CI runner. Simplest to set up; suitable for low-frequency forecasts (hourly or daily).
- **Workflow orchestrator** — the same script wrapped as a task in Airflow, Prefect, or Dagster. Adds dependency management, retries, and observability.
- **Streaming / event-driven** — a consumer that reacts to new measurement data arriving on a message bus (Kafka, Azure Event Hubs). Suitable for near-real-time forecasts.

All three patterns use the same OpenSTEF API. The sections below show how to structure the core script, then how to package and schedule it.

Core Script Structure
---------------------

A production run typically has two separate entry points: one for periodic **model retraining** and one for **generating forecasts**. Keeping them separate lets you retrain weekly while forecasting every 15 minutes.

.. code-block:: python

   # train.py  — run once per day / week
   import logging
   from pathlib import Path
   from datetime import timedelta

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.feature_pipeline import FeaturePipeline
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage

   logging.basicConfig(level=logging.INFO)

   MODEL_ID = "substation_a"
   STORAGE_PATH = Path("/var/openstef/models")

   def train():
       dataset = load_training_data()   # your data-loading logic

       model = ForecastingModel(
           feature_pipeline=FeaturePipeline(
               include_holiday_features=True,
               lag_transforms=[timedelta(hours=h) for h in [1, 24, 168]],
           ),
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       )
       storage = LocalModelStorage(base_path=STORAGE_PATH)
       workflow = CustomForecastingWorkflow(
           model=model,
           model_id=MODEL_ID,
           storage=storage,
       )
       result = workflow.fit(dataset)
       logging.info("Training complete. Metrics: %s", result.metrics_to_flat_dict())

   if __name__ == "__main__":
       train()

.. code-block:: python

   # predict.py  — run every 15 minutes
   from pathlib import Path
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage

   MODEL_ID = "substation_a"
   STORAGE_PATH = Path("/var/openstef/models")

   def forecast():
       dataset = load_recent_data()   # your data-loading logic

       storage = LocalModelStorage(base_path=STORAGE_PATH)
       workflow = CustomForecastingWorkflow.from_storage(
           model_id=MODEL_ID,
           storage=storage,
       )
       forecasts = workflow.predict(dataset)
       write_forecasts(forecasts)   # your output logic

   if __name__ == "__main__":
       forecast()

.. note::

   ``CustomForecastingWorkflow.from_storage`` raises ``ModelNotFoundError`` if no trained model exists yet. Run ``train.py`` at least once before scheduling ``predict.py``.

Model Storage
-------------

Local Storage
^^^^^^^^^^^^^

``LocalModelStorage`` persists models as joblib-serialised files under a directory tree keyed by ``model_id``. It requires no external services and is the right choice for single-machine deployments or development.

.. code-block:: python

   from openstef_models.storage.local_model_storage import LocalModelStorage

   storage = LocalModelStorage(base_path="/var/openstef/models")

Mount the storage directory as a persistent volume when running in a container (see :ref:`containerisation` below).

MLflow Storage
^^^^^^^^^^^^^^

For multi-node deployments or when you need experiment tracking, model versioning, and a central registry, use ``MLFlowStorage``:

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage

   storage = MLFlowStorage(
       tracking_uri="http://mlflow.internal:5000",
       experiment_name="substation_a_forecasts",
   )

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id=MODEL_ID,
       storage=storage,
   )

MLflow also provides the ``MLFlowStorageCallback``, which logs hyperparameters, metrics, feature-importance plots, and training artefacts automatically on every fit:

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorageCallback

   callback = MLFlowStorageCallback(tracking_uri="http://mlflow.internal:5000")
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id=MODEL_ID,
       callbacks=[callback],
   )

.. _containerisation:

Containerisation
----------------

Packaging OpenSTEF as a Docker image makes deployments reproducible and portable across cloud providers.

A minimal ``Dockerfile``:

.. code-block:: dockerfile

   FROM python:3.11-slim

   WORKDIR /app

   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application scripts
   COPY train.py predict.py ./

   # Default command — override at runtime
   CMD ["python", "predict.py"]

A matching ``requirements.txt``:

.. code-block:: text

   openstef-core
   openstef-models
   openstef-beam        # optional, for distributed pipelines

Build and run locally:

.. code-block:: bash

   docker build -t openstef-forecast:latest .

   # Run prediction with a mounted model directory
   docker run --rm \
     -v /var/openstef/models:/var/openstef/models \
     -e MLFLOW_TRACKING_URI=http://mlflow.internal:5000 \
     openstef-forecast:latest python predict.py

Pass configuration through environment variables rather than baking it into the image. Read them in your scripts with ``os.environ``.

Scheduling
----------

Cron
^^^^

For simple deployments, two crontab entries are sufficient:

.. code-block:: text

   # Retrain every Sunday at 02:00
   0 2 * * 0  docker run --rm -v /var/openstef/models:/var/openstef/models openstef-forecast:latest python train.py

   # Forecast every 15 minutes
   */15 * * * *  docker run --rm -v /var/openstef/models:/var/openstef/models openstef-forecast:latest python predict.py

Airflow
^^^^^^^

Wrap each script as a ``DockerOperator`` or ``PythonOperator`` task. A minimal DAG:

.. code-block:: python

   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.providers.docker.operators.docker import DockerOperator

   with DAG(
       dag_id="openstef_forecast",
       start_date=datetime(2024, 1, 1),
       schedule_interval="*/15 * * * *",
       catchup=False,
   ) as dag:

       predict = DockerOperator(
           task_id="predict",
           image="openstef-forecast:latest",
           command="python predict.py",
           mounts=["/var/openstef/models:/var/openstef/models"],
           environment={"MLFLOW_TRACKING_URI": "http://mlflow.internal:5000"},
       )

   # Separate DAG for weekly retraining
   with DAG(
       dag_id="openstef_train",
       start_date=datetime(2024, 1, 1),
       schedule_interval="0 2 * * 0",
       catchup=False,
   ) as train_dag:

       train = DockerOperator(
           task_id="train",
           image="openstef-forecast:latest",
           command="python train.py",
           mounts=["/var/openstef/models:/var/openstef/models"],
       )

Cloud Deployment Options
------------------------

Kubernetes (any cloud)
^^^^^^^^^^^^^^^^^^^^^^

Deploy the container as a ``CronJob`` resource. The pattern mirrors the cron approach but gains pod-level isolation, resource limits, and automatic restarts:

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
               - name: forecast
                 image: openstef-forecast:latest
                 command: ["python", "predict.py"]
                 env:
                   - name: MLFLOW_TRACKING_URI
                     value: "http://mlflow-service:5000"
                 volumeMounts:
                   - name: model-store
                     mountPath: /var/openstef/models
             volumes:
               - name: model-store
                 persistentVolumeClaim:
                   claimName: openstef-models-pvc
             restartPolicy: OnFailure

Azure / AWS / GCP
^^^^^^^^^^^^^^^^^

All major cloud providers offer a managed container scheduling service that accepts a Docker image and a cron expression:

- **Azure Container Apps Jobs** — schedule a container job with ``az containerapp job create --cron-expression "*/15 * * * *"``. Use Azure Blob Storage or an Azure-hosted MLflow instance for model storage.
- **AWS ECS Scheduled Tasks** — attach a CloudWatch Events rule to an ECS task definition. Use S3 or a SageMaker MLflow server for storage.
- **Google Cloud Run Jobs** — trigger via Cloud Scheduler. Use GCS or Vertex AI Experiments for storage.

In all cases the application code is identical; only the infrastructure configuration changes.

Monitoring and Observability
----------------------------

OpenSTEF exposes monitoring hooks through the ``ForecastingCallback`` interface. Implement a callback to push metrics to any observability backend:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback

   class PrometheusCallback(ForecastingCallback):
       """Push training and prediction metrics to a Prometheus pushgateway."""

       def on_fit_end(self, context, result):
           metrics = result.metrics_to_flat_dict()
           for name, value in metrics.items():
               push_to_gateway(name, value)   # your pushgateway client

       def on_predict_end(self, context, data, forecasts):
           push_to_gateway("forecast_count", len(forecasts.data))

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id=MODEL_ID,
       storage=storage,
       callbacks=[PrometheusCallback()],
   )

.. note:: [VISUALIZATION: Example Grafana dashboard showing forecast count, training MAE, and prediction latency over time for a production OpenSTEF deployment]

Key signals to monitor in production:

- **Training metrics** — MAE, RMSE, and skill score per model, logged by ``on_fit_end``. A sudden degradation indicates data drift or a data-pipeline issue.
- **Prediction latency** — time between ``on_predict_start`` and ``on_predict_end``. Spikes may indicate slow data retrieval or model bloat.
- **Forecast count** — number of forecast rows produced per run. A drop to zero usually means the input dataset was empty.
- **Model age** — time since last successful ``fit``. Alert if retraining has not run within its expected window.

For experiment tracking and model comparison, ``MLFlowStorageCallback`` logs all of the above automatically to an MLflow server without any custom callback code.

.. note::

   The ``DataSaveCallback`` (``openstef_models.callbacks.data_save_callback``) writes raw input data, prepared features, and forecast outputs to Parquet files on disk. Enable it during initial production rollout to simplify debugging before removing it once the pipeline is stable.

Related Pages
-------------

- :doc:`data_integration` — connecting OpenSTEF to S3, Databricks, InfluxDB, and other data sources.
- :doc:`use_cases` — end-to-end worked examples including congestion forecasting.
- :doc:`migration_v3_v4` — breaking changes to be aware of when upgrading an existing deployment.