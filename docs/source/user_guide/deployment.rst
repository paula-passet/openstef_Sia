Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from simple
cron-based scheduled jobs to fully orchestrated pipelines. It addresses containerization,
model persistence, cloud deployment, and monitoring via the library's built-in callback
system.

For reading data from external sources such as S3, Databricks, or InfluxDB, see
:doc:`data_integration`. For concrete end-to-end use cases, see :doc:`use_cases`.

.. note:: [DIAGRAM: High-level deployment topology showing a scheduler triggering a
   Python process that loads data, runs a workflow, persists the model, and writes
   forecasts to a data store.]

.. contents:: On this page
   :local:
   :depth: 2

Overview
--------

OpenSTEF is a Python library, not a server or daemon. Deploying it means writing a
Python script (or set of scripts) that calls the library's workflow API on a schedule,
then letting your infrastructure handle the rest. This design gives you full control
over the execution environment, scheduling cadence, and data plumbing without imposing
any particular platform.

A production deployment typically involves three recurring jobs:

- **Training** – periodically refit the model on fresh historical data and persist it.
- **Forecasting** – load the persisted model and generate predictions on the current
  inference window.
- **Monitoring** – validate forecast quality and emit metrics after each run.

All three concerns can be wired together through ``CustomForecastingWorkflow`` and its
callback system.

Core Workflow Pattern
---------------------

The ``CustomForecastingWorkflow`` class is the recommended entry point for production
use. It combines model management, lifecycle hooks, and optional persistence into a
single object.

.. code-block:: python

    import logging
    from pathlib import Path

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.integrations.joblib import JoblibModelSerializer
    from openstef_core.datasets import VersionedTimeSeriesDataset

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # --- Model storage (local filesystem) ---
    storage_dir = Path("/var/openstef/models")
    storage = JoblibModelSerializer(storage_dir=storage_dir)

    # --- Load or initialise the workflow ---
    MODEL_ID = "grid_substation_42"

    try:
        workflow = CustomForecastingWorkflow.from_storage(
            model_id=MODEL_ID,
            storage=storage,
        )
        logger.info("Loaded existing model from storage.")
    except Exception:
        # First run: build the workflow from scratch (see use_cases for full setup)
        workflow = build_new_workflow(MODEL_ID)   # your factory function
        logger.info("Initialised new model.")

    # --- Training ---
    training_dataset: VersionedTimeSeriesDataset = load_training_data()  # your loader
    result = workflow.fit(training_dataset)
    storage.save(workflow, model_id=MODEL_ID)
    logger.info("Training complete. Metrics: %s", result)

    # --- Forecasting ---
    inference_dataset = load_inference_data()
    forecasts = workflow.predict(inference_dataset)
    write_forecasts(forecasts)   # your writer

Splitting training and forecasting into separate scripts (or separate DAG tasks) is
common in practice. The pattern above shows them together for brevity.

Monitoring with Callbacks
-------------------------

OpenSTEF's callback system lets you inject monitoring logic at key lifecycle points
without modifying the workflow itself. Subclass ``ForecastingCallback`` and override
only the hooks you need.

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback

    class ProductionMonitoringCallback(ForecastingCallback):
        """Emit metrics and validate outputs after each workflow stage."""

        def on_fit_start(self, context, data):
            logger.info(
                "Training started. Dataset size: %d rows", len(data.data)
            )

        def on_fit_end(self, context, result):
            logger.info("Training finished. Result: %s", result)
            # Push metrics to your observability platform here, e.g.:
            # metrics_client.gauge("openstef.training.mae", result.mae)

        def on_predict_start(self, context, data):
            logger.info("Prediction started for %d rows.", len(data.data))

        def on_predict_end(self, context, data, result):
            n_forecasts = len(result.data)
            logger.info("Generated %d forecast rows.", n_forecasts)
            if n_forecasts == 0:
                raise RuntimeError("Empty forecast – aborting downstream write.")

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id=MODEL_ID,
        callbacks=[ProductionMonitoringCallback()],
    )

Because callbacks are plain Python classes, you can integrate with any observability
stack (Prometheus, Datadog, OpenTelemetry, etc.) by adding the relevant client calls
inside the hook methods.

Scheduled Jobs
--------------

The simplest production pattern is a cron job or a cloud scheduler that invokes a
Python script directly.

**Linux cron example** – retrain nightly, forecast every 15 minutes:

.. code-block:: bash

    # /etc/cron.d/openstef
    # Retrain at 02:00 every day
    0 2 * * *  openstef_user  /opt/openstef/venv/bin/python /opt/openstef/train.py

    # Forecast every 15 minutes
    */15 * * * *  openstef_user  /opt/openstef/venv/bin/python /opt/openstef/forecast.py

**Systemd timer** – an alternative to cron with better logging integration:

.. code-block:: ini

    # /etc/systemd/system/openstef-forecast.timer
    [Unit]
    Description=OpenSTEF 15-minute forecast

    [Timer]
    OnCalendar=*:0/15
    Persistent=true

    [Install]
    WantedBy=timers.target

.. code-block:: ini

    # /etc/systemd/system/openstef-forecast.service
    [Unit]
    Description=OpenSTEF forecast job

    [Service]
    Type=oneshot
    User=openstef_user
    ExecStart=/opt/openstef/venv/bin/python /opt/openstef/forecast.py
    StandardOutput=journal
    StandardError=journal

Containerization
----------------

Packaging the library and your scripts into a Docker image makes deployments
reproducible and portable across environments.

**Dockerfile**:

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    # Install OpenSTEF and dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy your pipeline scripts
    COPY scripts/ ./scripts/

    # Default entrypoint – override CMD at runtime
    ENTRYPOINT ["python"]
    CMD ["scripts/forecast.py"]

**requirements.txt** (minimal):

.. code-block:: text

    openstef
    openstef-models
    openstef-core

**Running the container**:

.. code-block:: bash

    # Forecast job – mount model storage from the host
    docker run --rm \
        -v /var/openstef/models:/var/openstef/models \
        -e OPENSTEF_MODEL_DIR=/var/openstef/models \
        myregistry/openstef:latest scripts/forecast.py

    # Training job
    docker run --rm \
        -v /var/openstef/models:/var/openstef/models \
        myregistry/openstef:latest scripts/train.py

.. note::

   When using ``LocalModelStorage`` / ``JoblibModelSerializer``, mount the model
   directory as a volume so that trained models persist across container restarts.
   For multi-replica deployments, use a shared network filesystem or a cloud object
   store instead.

Cloud Deployment Options
------------------------

OpenSTEF imposes no cloud-specific requirements. The patterns below map the library's
workflow API onto common cloud primitives.

Kubernetes CronJob
^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

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
              containers:
                - name: forecast
                  image: myregistry/openstef:latest
                  args: ["scripts/forecast.py"]
                  env:
                    - name: OPENSTEF_MODEL_DIR
                      value: /mnt/models
                  volumeMounts:
                    - name: model-storage
                      mountPath: /mnt/models
              volumes:
                - name: model-storage
                  persistentVolumeClaim:
                    claimName: openstef-models-pvc
              restartPolicy: OnFailure

Managed Workflow Orchestrators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more complex pipelines – fan-out across many substations, conditional retraining,
cross-job dependencies – a workflow orchestrator is a natural fit. OpenSTEF's library
design means each task is just a Python function call:

- **Apache Airflow** – wrap ``workflow.fit()`` and ``workflow.predict()`` in
  ``PythonOperator`` tasks inside a DAG.
- **Prefect / Dagster** – decorate your training and forecasting functions with
  ``@flow`` / ``@asset`` respectively; the library calls remain unchanged.
- **Azure ML Pipelines / AWS Step Functions** – invoke the containerised scripts as
  pipeline steps, passing model artefact paths between steps via environment variables
  or shared storage.

.. code-block:: python

    # Example: Airflow PythonOperator task
    from airflow.decorators import task

    @task()
    def run_forecast(model_id: str, model_dir: str) -> int:
        from pathlib import Path
        from openstef_models.workflows import CustomForecastingWorkflow
        from openstef_models.integrations.joblib import JoblibModelSerializer

        storage = JoblibModelSerializer(storage_dir=Path(model_dir))
        workflow = CustomForecastingWorkflow.from_storage(
            model_id=model_id, storage=storage
        )
        dataset = load_inference_data(model_id)   # your loader
        forecasts = workflow.predict(dataset)
        write_forecasts(forecasts, model_id)
        return len(forecasts.data)

Model Storage in the Cloud
---------------------------

``JoblibModelSerializer`` writes ``.pkl`` files to a local path. For cloud deployments
you have two options:

1. **Mount cloud storage as a local path** – use an S3 FUSE mount (``s3fs``), Azure
   Blob FUSE, or a GCS FUSE adapter. The serializer code is unchanged; only the
   ``storage_dir`` path changes.

2. **Implement a custom serializer** – subclass the storage interface and add your
   own ``save`` / ``load`` logic backed by ``boto3``, the Azure SDK, or the GCS
   client library.

.. warning::

   ``JoblibModelSerializer`` uses Python pickle under the hood. Only load model files
   from trusted sources. Never expose the model storage directory to untrusted users
   or public network paths.

Environment Configuration
--------------------------

Keep deployment-specific settings out of your scripts by reading them from environment
variables or a secrets manager:

.. code-block:: python

    import os
    from pathlib import Path

    MODEL_DIR = Path(os.environ.get("OPENSTEF_MODEL_DIR", "/tmp/openstef/models"))
    MODEL_ID   = os.environ.get("OPENSTEF_MODEL_ID", "default_model")
    LOG_LEVEL  = os.environ.get("LOG_LEVEL", "INFO")

    import logging
    logging.basicConfig(level=getattr(logging, LOG_LEVEL))

This pattern works equally well with Kubernetes ``ConfigMap``/``Secret`` objects,
AWS Parameter Store, Azure Key Vault, or HashiCorp Vault.

Recommended Deployment Checklist
----------------------------------

- Configure structured logging (JSON) so log aggregators can parse fields.
- Use the ``on_predict_end`` callback to validate that forecast output is non-empty
  before writing downstream.
- Store model artefacts with a versioned path (e.g. include a date stamp) so you can
  roll back to a previous model if quality degrades.
- Set resource limits (CPU/memory) on containers – training jobs are more
  memory-intensive than forecasting jobs.
- Run training and forecasting as separate jobs so a slow retraining run does not
  delay forecast delivery.
- Emit a heartbeat metric from the ``on_predict_end`` callback so your alerting system
  can detect silent failures (job never ran).

Related Pages
-------------

- :doc:`data_integration` – connecting OpenSTEF to S3, Databricks, InfluxDB, and
  other data sources.
- :doc:`use_cases` – end-to-end examples including congestion forecasting and load
  prediction.
- :doc:`migration_v3_v4` – if you are upgrading an existing deployment from V3 to V4.