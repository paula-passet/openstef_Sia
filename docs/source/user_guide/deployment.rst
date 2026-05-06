Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production: from a simple cron job on a single machine to a fully orchestrated multi-target deployment on cloud infrastructure. It focuses on the operational concerns — scheduling, containerization, model persistence, and monitoring — that arise once you move beyond exploratory notebooks.

For connecting OpenSTEF to your data sources, see :doc:`data_integration`. For a worked example of specific forecasting use cases, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/deployment_diagram_1.mmd

Deployment Patterns
-------------------

OpenSTEF is a library, so it has no built-in scheduler or server. You wire it into whatever execution environment you already operate. Three patterns cover most production scenarios:

- **Scheduled script** — a Python script invoked by cron, a cloud scheduler, or a CI/CD pipeline. Lowest operational overhead; suitable for a small number of forecasting targets.
- **Container-based job** — the same script packaged as a Docker image and executed by a container orchestrator (Kubernetes CronJob, AWS ECS Scheduled Task, Azure Container Instances). Adds reproducibility and horizontal scalability.
- **Workflow orchestration** — tasks defined in Airflow, Prefect, or a similar platform. Best when you need dependency management, retries, alerting, and audit trails across many targets.

All three patterns use the same OpenSTEF API. The sections below show each in turn.

Scheduled Script
----------------

The minimal production unit is a Python script that loads data, trains (or reuses) a model, and writes forecasts. The ``CustomForecastingWorkflow`` handles model reuse automatically: if a stored model is younger than ``model_reuse_max_age``, it skips retraining.

.. code-block:: python

    # forecast_job.py
    import logging
    from datetime import timedelta
    from pathlib import Path

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.workflow import CustomForecastingWorkflow
    from openstef_models.config import WorkflowConfig
    from openstef_models.integrations.mlflow import MLFlowStorage

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    WORKSPACE = Path("/var/openstef/workspace")

    def load_data() -> TimeSeriesDataset:
        # Replace with your data source — see the data_integration page
        ...

    def write_forecast(forecast):
        # Write to your forecast sink (database, object store, etc.)
        ...

    def main():
        dataset = load_data()

        workflow = CustomForecastingWorkflow(
            model_id="substation_a",
            config=WorkflowConfig(
                mlflow_storage=MLFlowStorage(
                    tracking_uri=str(WORKSPACE / "mlflow_tracking"),
                    local_artifacts_path=WORKSPACE / "mlflow_tracking_artifacts",
                ),
                model_reuse_enable=True,
                model_reuse_max_age=timedelta(days=7),
            ),
        )

        fit_result = workflow.fit(dataset)
        if fit_result is not None:
            logger.info("Retrained model — R²: %s", fit_result.metrics_full.to_dataframe())

        forecast = workflow.predict(dataset)
        logger.info("Forecast tail:\n%s", forecast.data.tail())
        write_forecast(forecast)

    if __name__ == "__main__":
        main()

Schedule this with a system cron entry or a cloud scheduler:

.. code-block:: bash

    # /etc/cron.d/openstef — run every 15 minutes
    */15 * * * *  openstef  /usr/bin/python /opt/openstef/forecast_job.py >> /var/log/openstef.log 2>&1

.. note::

    Set ``train_interval`` (or ``model_reuse_max_age``) to a value that matches your retraining cadence. Running the script every 15 minutes does not mean the model retrains every 15 minutes — OpenSTEF reuses the stored model until it ages out.

Containerization
----------------

Packaging the job as a Docker image makes it portable across environments and eliminates dependency drift between development and production.

A minimal ``Dockerfile``:

.. code-block:: dockerfile

    FROM python:3.11-slim

    WORKDIR /app

    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY forecast_job.py .

    # Workspace is mounted at runtime — do not bake data into the image
    ENV OPENSTEF_WORKSPACE=/var/openstef/workspace

    CMD ["python", "forecast_job.py"]

A matching ``requirements.txt``:

.. code-block:: text

    openstef-models
    openstef-core
    mlflow

Build and run locally:

.. code-block:: bash

    docker build -t openstef-forecast:latest .
    docker run --rm \
        -v /mnt/openstef-workspace:/var/openstef/workspace \
        -e OPENSTEF_WORKSPACE=/var/openstef/workspace \
        openstef-forecast:latest

For production, push the image to a registry and reference it from your scheduler.

Kubernetes CronJob
^^^^^^^^^^^^^^^^^^

A Kubernetes ``CronJob`` is a natural fit for periodic forecasting tasks. Mount a ``PersistentVolumeClaim`` (or an object-store-backed volume) for the MLflow workspace so model artifacts survive pod restarts.

.. code-block:: yaml

    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: openstef-forecast
    spec:
      schedule: "*/15 * * * *"
      concurrencyPolicy: Forbid          # prevent overlapping runs
      jobTemplate:
        spec:
          template:
            spec:
              restartPolicy: OnFailure
              containers:
                - name: forecast
                  image: <your-registry>/openstef-forecast:latest
                  env:
                    - name: OPENSTEF_WORKSPACE
                      value: /var/openstef/workspace
                  volumeMounts:
                    - name: workspace
                      mountPath: /var/openstef/workspace
              volumes:
                - name: workspace
                  persistentVolumeClaim:
                    claimName: openstef-workspace-pvc

.. note::

    Set ``concurrencyPolicy: Forbid`` to prevent a slow run from overlapping with the next scheduled execution. If a run is still active when the next trigger fires, Kubernetes skips that trigger rather than launching a second pod.

Cloud Deployment Options
------------------------

The container image described above runs unchanged on all major cloud platforms. The main difference between providers is how you schedule the job and where you store the MLflow workspace.

**AWS**

- Run the image as an ECS Scheduled Task (Fargate) triggered by an EventBridge rule.
- Store the MLflow workspace on EFS (for a local tracking server) or point ``tracking_uri`` at a managed MLflow instance on SageMaker.
- Use Secrets Manager to inject database credentials or API keys as environment variables.

**Azure**

- Use Azure Container Instances with a Logic App or Azure Scheduler for the trigger.
- Mount an Azure Files share as the workspace volume.
- Azure ML Workspaces include a managed MLflow tracking server; set ``tracking_uri`` to its endpoint.

**GCP**

- Cloud Run Jobs with Cloud Scheduler covers the cron pattern with no cluster to manage.
- Use Filestore or a GCS-backed FUSE mount for the workspace.
- Vertex AI Experiments provides a managed MLflow-compatible tracking endpoint.

In all cases the application code is identical — only the infrastructure configuration changes.

Workflow Orchestration
----------------------

When you manage many forecasting targets or need dependency chains (e.g., load data → validate → train → forecast → publish), a dedicated orchestration platform gives you retries, alerting, and a visual audit trail.

The example below shows an Airflow DAG that separates training and prediction into distinct tasks. This lets you retrain weekly while forecasting every 15 minutes without duplicating logic.

.. code-block:: python

    # dags/openstef_dag.py
    from datetime import timedelta

    from airflow.decorators import dag, task
    from airflow.utils.dates import days_ago

    @dag(
        schedule_interval="*/15 * * * *",
        start_date=days_ago(1),
        catchup=False,
        default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    )
    def openstef_forecast():

        @task()
        def run_forecast():
            from pathlib import Path
            from datetime import timedelta
            from openstef_core.datasets import TimeSeriesDataset
            from openstef_models.workflow import CustomForecastingWorkflow
            from openstef_models.config import WorkflowConfig
            from openstef_models.integrations.mlflow import MLFlowStorage

            dataset = TimeSeriesDataset(...)  # load from your source

            workflow = CustomForecastingWorkflow(
                model_id="substation_a",
                config=WorkflowConfig(
                    mlflow_storage=MLFlowStorage(
                        tracking_uri="http://mlflow-server:5000",
                    ),
                    model_reuse_enable=True,
                    model_reuse_max_age=timedelta(days=7),
                ),
            )
            workflow.fit(dataset)
            forecast = workflow.predict(dataset)
            # write forecast to sink ...

        run_forecast()

    openstef_forecast()

For Prefect or Dagster the structure is equivalent — wrap the same workflow calls in their respective task/flow decorators.

Model Persistence and MLflow
----------------------------

OpenSTEF uses MLflow as its default model store. ``MLFlowStorage`` handles serialization, versioning, and retrieval automatically when passed to ``WorkflowConfig``.

.. code-block:: python

    from openstef_models.integrations.mlflow import MLFlowStorage

    # Local filesystem (development / single-node production)
    storage = MLFlowStorage(
        tracking_uri="/var/openstef/mlflow_tracking",
        local_artifacts_path="/var/openstef/mlflow_tracking_artifacts",
    )

    # Remote tracking server (multi-node / cloud)
    storage = MLFlowStorage(
        tracking_uri="http://mlflow-server:5000",
    )

Key ``WorkflowConfig`` fields that govern model lifecycle in production:

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Field
     - Default
     - Effect
   * - ``model_reuse_enable``
     - ``True``
     - Skip retraining if a recent model exists in storage.
   * - ``model_reuse_max_age``
     - 7 days
     - Maximum age before a stored model is considered stale.
   * - ``model_selection_enable``
     - ``True``
     - Automatically promote the new model only if it outperforms the current one.
   * - ``model_selection_metric``
     - ``(Q(0.5), "R2", "higher_is_better")``
     - Metric used for the promotion decision.

With ``model_selection_enable=True``, a newly trained model replaces the stored model only when its validation metric is better (accounting for ``model_selection_old_model_penalty``). This prevents a degraded model caused by a data anomaly from being promoted automatically.

Monitoring and Callbacks
------------------------

OpenSTEF exposes lifecycle hooks through a callback interface. Implement a callback to push metrics to your monitoring stack without modifying the core workflow.

.. code-block:: python

    from openstef_models.callbacks import ForecastingCallback
    from openstef_models.workflow import WorkflowContext

    class PrometheusCallback(ForecastingCallback):
        """Push forecast quality metrics to a Prometheus Pushgateway."""

        def on_fit_end(self, context: WorkflowContext, result):
            if result is not None:
                r2 = result.metrics_full.to_dataframe()["R2"].iloc[0]
                # push r2 to your metrics endpoint
                push_to_gateway("http://pushgateway:9091", job="openstef", registry=...)

        def on_predict_end(self, context: WorkflowContext, data, result):
            n_points = len(result.data)
            # push forecast count / latency metrics
            ...

    workflow = CustomForecastingWorkflow(
        model_id="substation_a",
        config=WorkflowConfig(...),
        callbacks=[PrometheusCallback()],
    )

Available callback hooks:

- ``on_fit_start`` / ``on_fit_end`` — before and after model training.
- ``on_predict_start`` / ``on_predict_end`` — before and after forecast generation.

Beyond custom callbacks, the MLflow tracking server provides a built-in audit trail of every training run: hyperparameters, evaluation metrics, and the serialized model artifact are logged automatically whenever ``MLFlowStorage`` is configured.

.. note:: [VISUALIZATION: MLflow experiment view showing multiple training runs for a single model_id, with R² and other metrics plotted over time]

.. note::

    For large-scale deployments with many targets running in parallel, consider a shared MLflow tracking server backed by a relational database (PostgreSQL) and an object store (S3 / Azure Blob) for artifacts. The default local filesystem backend is not safe for concurrent writes from multiple workers.

Summary
-------

- Use a **scheduled script** for simple, low-volume deployments.
- Package as a **Docker container** for reproducibility and portability across cloud providers.
- Use a **Kubernetes CronJob** or a cloud-native equivalent for managed scheduling without a full orchestration platform.
- Use **Airflow / Prefect** when you need dependency management, retries, and observability across many targets.
- Configure ``MLFlowStorage`` to persist models; tune ``model_reuse_max_age`` and ``model_selection_enable`` to control retraining behaviour.
- Implement ``ForecastingCallback`` to integrate with your existing monitoring stack.