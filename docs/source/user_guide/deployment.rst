Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production — from a simple cron job on a single machine to a fully orchestrated, containerised pipeline on a cloud platform. It focuses on the *how* of deployment: packaging, scheduling, model storage, and monitoring. For details on reading data from cloud sources such as S3 or Databricks, see :doc:`data_integration`. For use-case context, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Deployment Patterns
-------------------

OpenSTEF is a library, so "deploying" it means embedding it inside a process you own and schedule. Three patterns cover most production scenarios:

- **Scheduled script** — a Python script invoked by cron, a cloud scheduler, or a CI runner. Simplest to start with; works well for a small number of prediction units.
- **Containerised job** — the same script packaged as a Docker image and run by a container orchestrator (Kubernetes CronJob, AWS ECS Scheduled Task, Azure Container Instances). Portable and reproducible.
- **Orchestration platform** — the workflow is expressed as a DAG in Airflow, Prefect, or a similar tool. Best when you need dependency management, retries, alerting, and audit logs across many prediction units.

All three patterns share the same core loop: load data → run ``CustomForecastingWorkflow.predict()`` (and periodically ``fit()``) → write forecasts somewhere useful.

The Core Production Loop
------------------------

A minimal production script looks like this:

.. code-block:: python

    # forecast_job.py
    import logging
    from datetime import timedelta
    from pathlib import Path

    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
        ForecastingCallback,
    )
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.storage.local_model_storage import LocalModelStorage
    from openstef_models.forecasters.constant_median import ConstantMedianForecaster

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

    MODEL_DIR = Path("/var/openstef/models")
    MODEL_ID = "grid_connection_A"

    # --- storage ---
    storage = LocalModelStorage(base_path=MODEL_DIR)

    # --- load or build workflow ---
    try:
        workflow = CustomForecastingWorkflow.from_storage(
            model_id=MODEL_ID,
            storage=storage,
        )
        log.info("Loaded existing model from storage.")
    except Exception:
        log.info("No saved model found — building a new one.")
        model = ForecastingModel(
            forecaster=ConstantMedianForecaster(
                horizons=[LeadTime.from_string("PT1H")],
                quantiles=[Q(0.1), Q(0.5), Q(0.9)],
            )
        )
        workflow = CustomForecastingWorkflow(
            model=model,
            model_id=MODEL_ID,
            storage=storage,
        )

    # --- fetch live data (replace with your data source) ---
    dataset = create_synthetic_forecasting_dataset()

    # --- retrain weekly, predict every run ---
    fit_result = workflow.fit(dataset)
    forecasts = workflow.predict(dataset)

    log.info("Generated %d forecast rows.", len(forecasts.data))
    # write forecasts to your database / message bus here

This script is self-contained and stateless between runs — the model is persisted to ``MODEL_DIR`` and reloaded on the next invocation.

Containerisation
----------------

Packaging the job as a Docker image makes it portable across environments and eliminates "works on my machine" problems.

A minimal ``Dockerfile``:

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    # Install OpenSTEF packages
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY forecast_job.py .

    # Model artefacts are mounted at runtime — do not bake them into the image
    VOLUME ["/var/openstef/models"]

    CMD ["python", "forecast_job.py"]

A matching ``requirements.txt``:

.. code-block:: text

    openstef-core
    openstef-models
    openstef-beam          # optional: for Apache Beam / large-scale pipelines

Build and run locally:

.. code-block:: bash

    docker build -t openstef-forecast:latest .
    docker run --rm \
        -v /data/openstef/models:/var/openstef/models \
        openstef-forecast:latest

.. note::

    Mount model storage as a volume (or point ``LocalModelStorage`` at a cloud path) so that trained models survive container restarts. Never bake model artefacts into the image itself — they change far more often than the code.

Scheduling
----------

**Cron (Linux/macOS)**

The simplest scheduler. Add an entry to your crontab to run the container every 15 minutes:

.. code-block:: bash

    # crontab -e
    */15 * * * * docker run --rm \
        -v /data/openstef/models:/var/openstef/models \
        openstef-forecast:latest >> /var/log/openstef.log 2>&1

**Kubernetes CronJob**

For cloud-native environments, a ``CronJob`` manifest gives you retries, history limits, and resource constraints:

.. code-block:: yaml

    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: openstef-forecast
    spec:
      schedule: "*/15 * * * *"
      concurrencyPolicy: Forbid
      successfulJobsHistoryLimit: 3
      failedJobsHistoryLimit: 1
      jobTemplate:
        spec:
          template:
            spec:
              restartPolicy: OnFailure
              containers:
                - name: forecast
                  image: your-registry/openstef-forecast:latest
                  volumeMounts:
                    - name: model-storage
                      mountPath: /var/openstef/models
              volumes:
                - name: model-storage
                  persistentVolumeClaim:
                    claimName: openstef-models-pvc

**Cloud schedulers**

All major clouds offer a managed equivalent:

- **AWS** — EventBridge Scheduler triggering an ECS Fargate task or a Lambda function.
- **Azure** — Azure Container Instances with a Logic Apps or Azure Scheduler trigger; or Azure Functions with a timer trigger.
- **GCP** — Cloud Scheduler invoking a Cloud Run job.

The container image and volume-mount pattern is identical across all three.

Model Storage Backends
-----------------------

``LocalModelStorage`` is the right choice for single-machine or shared-filesystem deployments. For multi-node or cloud deployments, switch to the MLflow backend, which stores artefacts in a central tracking server and supports model versioning.

.. code-block:: python

    from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

    storage = MLFlowStorage(
        tracking_uri="http://mlflow.internal:5000",
        experiment_name="grid_connection_forecasts",
    )

    mlflow_callback = MLFlowStorageCallback(storage=storage)

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id=MODEL_ID,
        storage=storage,
        callbacks=[mlflow_callback],
    )

The ``MLFlowStorageCallback`` automatically logs hyperparameters, training metrics, and feature-importance plots to the MLflow run on every ``fit()`` call. You can then compare runs, roll back to a previous model version, and serve models via the MLflow Model Registry — all without changing your forecasting code.

.. note:: [VISUALIZATION: MLflow experiment tracking UI showing multiple training runs for a single model ID, with metrics columns (MAE, RMSE) and a link to stored artefacts]

Monitoring and Alerting
-----------------------

OpenSTEF's callback system is the natural integration point for production monitoring. Implement ``ForecastingCallback`` to emit metrics to any observability backend:

.. code-block:: python

    import time
    from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback

    class PrometheusCallback(ForecastingCallback):
        """Emit forecast latency and row-count metrics to a Prometheus push gateway."""

        def on_predict_start(self, context, data):
            self._t0 = time.monotonic()

        def on_predict_end(self, context, data, result):
            elapsed = time.monotonic() - self._t0
            n_rows = len(result.data)
            # push to your metrics backend here, e.g.:
            # push_to_gateway("http://pushgateway:9091", job="openstef",
            #                 registry=build_registry(elapsed, n_rows))
            print(f"predict latency={elapsed:.2f}s rows={n_rows}")

    class AlertingCallback(ForecastingCallback):
        """Send an alert when a training run produces unexpectedly poor metrics."""

        RMSE_THRESHOLD = 50.0  # MW — tune per use case

        def on_fit_end(self, context, result):
            metrics = result.metrics_to_flat_dict()
            rmse = metrics.get("rmse", 0.0)
            if rmse > self.RMSE_THRESHOLD:
                # send_alert(f"Model {context.workflow.model_id} RMSE={rmse:.1f} exceeds threshold")
                print(f"WARNING: high RMSE {rmse:.1f} for {context.workflow.model_id}")

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id=MODEL_ID,
        storage=storage,
        callbacks=[PrometheusCallback(), AlertingCallback()],
    )

Callbacks are composable — pass a list and all of them fire at each lifecycle event (``on_fit_start``, ``on_fit_end``, ``on_predict_start``, ``on_predict_end``). This keeps monitoring logic cleanly separated from forecasting logic.

For debugging data issues in production, the built-in ``DataSaveCallback`` writes prepared inputs and raw forecasts to Parquet files on disk, which is invaluable when diagnosing unexpected forecast behaviour:

.. code-block:: python

    from openstef_models.callbacks.data_save_callback import DataSaveCallback

    debug_callback = DataSaveCallback(
        cache_dir=Path("/var/openstef/debug"),
        save_prepared_data=True,
        save_forecast=True,
    )

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id=MODEL_ID,
        callbacks=[debug_callback],
    )

.. warning::

    ``DataSaveCallback`` writes one Parquet file per run. Disable it or add a retention policy in long-running production deployments to avoid unbounded disk growth.

Environment Configuration
--------------------------

Avoid hardcoding paths, URIs, and thresholds in your script. Use environment variables and read them at startup:

.. code-block:: python

    import os
    from pathlib import Path

    MODEL_DIR = Path(os.environ.get("OPENSTEF_MODEL_DIR", "/var/openstef/models"))
    MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "")
    MODEL_ID = os.environ.get("OPENSTEF_MODEL_ID", "default_model")

Pass these into your container via Kubernetes ``env`` / ``envFrom`` (referencing a ``ConfigMap`` or ``Secret``), an ECS task definition, or a ``.env`` file for local development.

Choosing a Pattern
------------------

+----------------------------+------------------+-------------------+--------------------+
| Criterion                  | Cron script      | Container job     | Orchestration DAG  |
+============================+==================+===================+====================+
| Setup complexity           | Low              | Medium            | High               |
+----------------------------+------------------+-------------------+--------------------+
| Portability                | Low              | High              | High               |
+----------------------------+------------------+-------------------+--------------------+
| Retry / dependency logic   | Manual           | Limited           | Built-in           |
+----------------------------+------------------+-------------------+--------------------+
| Suitable for N models      | < 10             | < 100             | Unlimited          |
+----------------------------+------------------+-------------------+--------------------+
| Model versioning           | Manual           | Via MLflow        | Via MLflow         |
+----------------------------+------------------+-------------------+--------------------+

Start with a cron script to validate your pipeline end-to-end, then migrate to a container job once you need reproducibility across environments, and add an orchestration layer when the number of prediction units or inter-job dependencies grows beyond what a single script can manage cleanly.

Related Pages
-------------

- :doc:`data_integration` — connecting OpenSTEF to S3, Databricks, InfluxDB, and other data sources.
- :doc:`use_cases` — worked examples for congestion forecasting and other common scenarios.
- :doc:`migration_v3_v4` — breaking changes and update steps if you are upgrading an existing deployment.