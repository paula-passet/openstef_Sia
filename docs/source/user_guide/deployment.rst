Production Deployment
=====================

This page covers practical patterns for deploying OpenSTEF in production environments,
from simple scheduled scripts to fully orchestrated distributed systems. OpenSTEF is a
library — it provides the building blocks for forecasting workflows, and it is your
responsibility to embed those building blocks into whatever execution environment suits
your infrastructure.

For data integration patterns (reading from S3, Databricks, InfluxDB, etc.) see
:doc:`data_integration`. For real-world use-case walkthroughs see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Choosing a Deployment Pattern
------------------------------

OpenSTEF workflows are stateless Python callables. This makes them easy to embed in
almost any execution model. The right choice depends on your operational requirements:

- **Scheduled script** — lowest operational overhead; suitable for a single machine
  or a small number of prediction points with relaxed latency requirements.
- **Containerised service** — portable, reproducible, and easy to scale horizontally;
  the recommended baseline for most production teams.
- **Orchestrated platform** — full DAG scheduling, retries, observability, and
  parallelism; appropriate when you manage many prediction points or need tight SLA
  guarantees.

The sections below address each tier in turn.

Scheduled Script
----------------

The simplest production deployment is a Python script executed on a cron schedule.
The script loads data, runs the workflow, and writes results back to your data store.

.. code-block:: python

    # forecast_job.py
    import logging
    from datetime import timedelta
    from pathlib import Path

    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_models.integrations.joblib import JoblibModelSerializer
    from openstef_models.models.storage import LocalModelStorage
    from openstef_models.workflows import CustomForecastingWorkflow

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    MODEL_DIR = Path("/var/openstef/models")
    MODEL_ID = "grid_connection_42"


    def load_dataset() -> VersionedTimeSeriesDataset:
        # Replace with your data integration logic.
        # See the data_integration page for S3/Databricks/InfluxDB patterns.
        ...


    def write_forecasts(forecasts) -> None:
        # Write results to your time-series database or message bus.
        ...


    def main() -> None:
        storage = LocalModelStorage(
            storage_dir=MODEL_DIR,
            serializer=JoblibModelSerializer(),
        )

        workflow = CustomForecastingWorkflow.from_storage(
            model_id=MODEL_ID,
            storage=storage,
        )

        dataset = load_dataset()
        forecasts = workflow.predict(dataset)
        write_forecasts(forecasts)
        logger.info("Forecast complete: %d rows written", len(forecasts.data))


    if __name__ == "__main__":
        main()

Schedule this with ``cron``, ``systemd`` timers, or a cloud-native scheduler such as
AWS EventBridge or Azure Logic Apps. Keep the script idempotent — if it runs twice in
the same window the second run should produce the same output without side effects.

.. note::

   ``LocalModelStorage`` serialises models with joblib. Never load a ``.pkl`` file
   from an untrusted source, as joblib is based on Python's pickle protocol and can
   execute arbitrary code on load.

Containerisation
----------------

Packaging your forecasting job as a container image gives you a reproducible,
portable artefact that runs identically in development and production.

A minimal ``Dockerfile`` for the script above:

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    # Install OpenSTEF and any extras you need.
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY forecast_job.py .

    # Models are mounted at runtime — do not bake them into the image.
    VOLUME ["/var/openstef/models"]

    CMD ["python", "forecast_job.py"]

A matching ``requirements.txt``:

.. code-block:: text

    openstef-core
    openstef-models[joblib]
    # Add openstef-beam if you need backtesting or evaluation utilities.

Build and run locally:

.. code-block:: bash

    docker build -t openstef-forecast:latest .
    docker run --rm \
        -v /path/to/local/models:/var/openstef/models \
        openstef-forecast:latest

In production, replace the bind mount with a persistent volume or a remote model
store. Push the image to your container registry and trigger it from your scheduler
of choice (Kubernetes CronJob, AWS ECS Scheduled Task, Azure Container Instances, etc.).

Training vs. Inference Containers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is good practice to separate training and inference into distinct container images
or at least distinct entry points. Training jobs are typically long-running and
resource-intensive; inference jobs are short and latency-sensitive. Separating them
lets you scale and schedule each independently.

.. code-block:: dockerfile

    # Use ARG to select the entry point at build time, or use two separate images.
    ARG JOB_TYPE=forecast
    CMD ["python", "${JOB_TYPE}_job.py"]

Cloud Deployment Options
------------------------

OpenSTEF has no cloud-specific dependencies, so it runs on any platform that can
execute Python. The patterns below are illustrative; adapt them to your environment.

**Kubernetes CronJob**

.. code-block:: yaml

    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: openstef-forecast
    spec:
      schedule: "*/15 * * * *"   # every 15 minutes
      jobTemplate:
        spec:
          template:
            spec:
              containers:
                - name: forecast
                  image: your-registry/openstef-forecast:latest
                  volumeMounts:
                    - name: model-store
                      mountPath: /var/openstef/models
              volumes:
                - name: model-store
                  persistentVolumeClaim:
                    claimName: openstef-models-pvc
              restartPolicy: OnFailure

**AWS ECS / Fargate**

Define a task definition that references your ECR image and mounts an EFS volume for
model persistence. Trigger the task from EventBridge Scheduler on your desired cadence.

**Azure Container Apps Jobs**

Use a Container Apps Job with a cron trigger. Mount an Azure Files share for the model
directory, or implement a custom ``ModelStorage`` backend that reads and writes to
Azure Blob Storage.

Orchestration Platforms
-----------------------

When you manage many prediction points, need dependency tracking between training and
inference runs, or require fine-grained retry logic, a workflow orchestrator is the
right tool.

Apache Airflow
^^^^^^^^^^^^^^

Wrap each OpenSTEF workflow call in a ``PythonOperator`` or ``@task``-decorated
function. A typical DAG has two tasks: retrain (runs nightly) and forecast (runs every
15 minutes).

.. code-block:: python

    from datetime import datetime, timedelta

    from airflow.decorators import dag, task

    @dag(
        schedule="*/15 * * * *",
        start_date=datetime(2024, 1, 1),
        catchup=False,
        default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    )
    def openstef_forecast_dag():

        @task()
        def run_forecast():
            from pathlib import Path
            from openstef_models.models.storage import LocalModelStorage
            from openstef_models.integrations.joblib import JoblibModelSerializer
            from openstef_models.workflows import CustomForecastingWorkflow

            storage = LocalModelStorage(
                storage_dir=Path("/opt/airflow/models"),
                serializer=JoblibModelSerializer(),
            )
            workflow = CustomForecastingWorkflow.from_storage(
                model_id="grid_connection_42",
                storage=storage,
            )
            dataset = _load_dataset()   # your data loading function
            forecasts = workflow.predict(dataset)
            _write_forecasts(forecasts)

        run_forecast()


    openstef_forecast_dag()

Prefect and Dagster follow the same pattern — wrap the workflow call in a flow/task
decorator and configure your schedule and retry policy through the platform's API.

Monitoring and Observability
-----------------------------

OpenSTEF's ``CustomForecastingWorkflow`` exposes a callback interface that lets you
hook into key lifecycle events without modifying library code. This is the recommended
integration point for metrics, alerting, and structured logging.

.. code-block:: python

    import logging
    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback

    logger = logging.getLogger(__name__)


    class ProductionMonitoringCallback(ForecastingCallback):
        """Emit structured log events and push metrics at each workflow stage."""

        def on_fit_start(self, context, dataset):
            logger.info(
                "Training started",
                extra={"model_id": context.model_id, "n_samples": len(dataset.data)},
            )

        def on_fit_end(self, context, result):
            logger.info(
                "Training complete",
                extra={
                    "model_id": context.model_id,
                    "metrics": result.metrics,
                },
            )
            # Push to your metrics backend here, e.g. Prometheus, Datadog, CloudWatch.

        def on_predict_end(self, context, dataset, forecasts):
            logger.info(
                "Forecast generated",
                extra={
                    "model_id": context.model_id,
                    "n_forecasts": len(forecasts.data),
                },
            )


    # Attach the callback when constructing the workflow.
    workflow = CustomForecastingWorkflow(
        model=my_model,
        model_id="grid_connection_42",
        callbacks=[ProductionMonitoringCallback()],
    )

Key metrics to track in production:

- **Forecast latency** — time from data ingestion to forecast write.
- **Training duration** — flag regressions caused by data growth or model changes.
- **Forecast coverage** — percentage of prediction points that produced a result in
  each scheduling window.
- **Model age** — time since the last successful training run; stale models degrade
  silently.
- **Data freshness** — lag between the latest observation timestamp and the current
  wall-clock time; a large lag often precedes forecast quality issues.

For deeper quality evaluation — backtesting, lead-time analysis, and benchmark
comparisons — use ``openstef-beam``, which is purpose-built for that workflow.

Model Storage in Production
----------------------------

``LocalModelStorage`` with ``JoblibModelSerializer`` is appropriate for single-machine
deployments. For distributed or cloud deployments you will typically want a shared
storage backend so that training and inference containers can access the same model
artefacts.

Options include:

- **Network file system** — mount an NFS share or cloud file service (EFS, Azure Files,
  Filestore) at the same path in every container.
- **Object storage** — implement a custom ``ModelStorage`` class that reads and writes
  to S3, GCS, or Azure Blob Storage. Serialise with ``JoblibModelSerializer`` and
  stream the bytes to/from the object store.
- **MLflow Model Registry** — wrap the registry client in a ``ModelStorage``
  implementation to gain versioning, stage promotion, and a UI out of the box.

Whichever backend you choose, keep model artefacts versioned and retain at least one
previous version so you can roll back quickly if a newly trained model degrades.

.. note::

   When loading models across Python or library version boundaries, validate that the
   serialised artefact was produced by a compatible environment. Pin your OpenSTEF
   dependency versions in both training and inference images to avoid subtle
   deserialisation failures.

Further Reading
---------------

- :doc:`data_integration` — connecting OpenSTEF to S3, Databricks, InfluxDB, and
  other data sources used in production pipelines.
- :doc:`use_cases` — end-to-end examples including congestion forecasting and other
  common energy-grid scenarios.
- :doc:`migration_v3_v4` — if you are upgrading an existing deployment, review the
  breaking changes before updating your container images.