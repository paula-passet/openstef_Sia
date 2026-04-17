Production Deployment
=====================

This page covers practical patterns for running OpenSTEF in production — from a simple cron-driven script to a fully orchestrated, containerised pipeline with model tracking and alerting. OpenSTEF is a library, so it imposes no particular runtime topology; the patterns here represent common approaches you can adapt to your own infrastructure.

**[DIAGRAM: Deployment topology options — from cron/script at the left through containerised service to full orchestration platform at the right, with shared components (model storage, data source, monitoring) shown below each tier]**

.. note::

   This page focuses on *how to run* OpenSTEF in production. For *what data to feed it*, see :doc:`data_integration`. For *what to do with the forecasts*, see :doc:`use_cases`.

.. contents:: On this page
   :local:
   :depth: 2

----

Choosing a Deployment Pattern
------------------------------

OpenSTEF's ``CustomForecastingWorkflow`` is the central object you will instantiate and call on a schedule. Everything else — containerisation, orchestration, storage back-ends — is infrastructure that wraps that call. The right amount of infrastructure depends on your operational requirements:

- **Scheduled script** — lowest overhead; suitable for a handful of forecasting locations with relaxed SLAs.
- **Containerised job** — reproducible environment, easy horizontal scaling, natural fit for Kubernetes CronJobs or cloud-managed schedulers.
- **Full orchestration** (Airflow, Prefect, etc.) — recommended when you have many locations, complex dependencies between training and inference runs, or need fine-grained retry and alerting logic.

All three patterns share the same Python code at their core; they differ only in how that code is packaged and triggered.

----

The Core Production Script
---------------------------

Regardless of the surrounding infrastructure, a production run follows the same three steps: load data, call ``workflow.fit`` (on a retraining schedule) or ``workflow.predict``, and persist the result.

The example below shows a self-contained script that trains a gradient-boosted model and writes forecasts to disk. It uses ``MLFlowStorageCallback`` so that every training run is tracked automatically.

.. code-block:: python

   import logging
   from pathlib import Path

   from openstef_core.datasets import ForecastDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )
   from openstef_models.models.storage import MLFlowStorage, MLFlowStorageCallback
   from openstef_models.transforms.general import Imputer, NaNDropper, Scaler
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.postprocessing import (
       ConfidenceIntervalApplicator,
       QuantileSorter,
   )
   from openstef_core.base_model import TransformPipeline
   from openstef_models.workflows import CustomForecastingWorkflow

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   WORKSPACE = Path("/var/openstef")
   MODEL_ID = "substation_north_v1"

   # --- Build the model ---------------------------------------------------
   horizons = [LeadTime(hours=h) for h in [1, 4, 24, 48]]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=[
           NaNDropper(),
           Imputer(),
           DatetimeFeaturesAdder(),
           HolidayFeatureAdder(country="NL"),
           LagsAdder(horizons=horizons),
           Scaler(),
       ]),
       forecaster=GBLinearForecaster(
           horizons=horizons,
           quantiles=quantiles,
           hyperparams=GBLinearHyperParams(),
       ),
       postprocessing=TransformPipeline(transforms=[
           QuantileSorter(),
           ConfidenceIntervalApplicator(quantiles=quantiles, add_quantiles_from_std=False),
       ]),
       target_column="load",
   )

   # --- Wrap in a workflow with MLflow tracking ---------------------------
   mlflow_storage = MLFlowStorage(
       tracking_uri=str(WORKSPACE / "mlflow_tracking"),
       local_artifacts_path=WORKSPACE / "mlflow_artifacts",
   )

   workflow = CustomForecastingWorkflow(
       model_id=MODEL_ID,
       model=model,
       callbacks=[
           MLFlowStorageCallback(
               storage=mlflow_storage,
               model_reuse_enable=True,
               model_reuse_max_age=7,   # days
           )
       ],
   )

   # --- Load your dataset (see data_integration for source patterns) ------
   # dataset = load_dataset_from_your_source(...)

   # --- Train (run on a weekly cron) --------------------------------------
   fit_result = workflow.fit(dataset)
   if fit_result is not None:
       logger.info("Training metrics:\n%s", fit_result.metrics_full.to_dataframe())

   # --- Predict (run every 15 minutes) ------------------------------------
   forecast: ForecastDataset = workflow.predict(dataset)
   logger.info("Forecast tail:\n%s", forecast.data.tail())

.. note::

   ``MLFlowStorageCallback`` handles both model persistence and loading. When ``model_reuse_enable=True``, the workflow will skip retraining if a sufficiently recent model already exists in the MLflow store — useful when training and inference are triggered by the same scheduler entry.

**[VISUALIZATION: Example MLflow experiment view showing training runs for a single model_id with metrics columns (MAE, RMSE, CRPS) and artifact links]**

----

Containerisation
----------------

Packaging the script above in a container gives you a reproducible, portable execution unit. The following ``Dockerfile`` is a minimal starting point.

.. code-block:: docker

   FROM python:3.12-slim

   WORKDIR /app

   # Install OpenSTEF with all sub-packages
   RUN pip install --no-cache-dir openstef

   # Copy your forecasting script and any config files
   COPY forecast_job.py .
   COPY config/ ./config/

   # Mount /var/openstef at runtime for model storage and outputs
   VOLUME ["/var/openstef"]

   CMD ["python", "forecast_job.py"]

Build and run locally:

.. code-block:: bash

   docker build -t openstef-forecast:latest .
   docker run --rm \
       -v /data/openstef:/var/openstef \
       -e OPENSTEF_ENV=production \
       openstef-forecast:latest

For production, push the image to your registry and reference it from your scheduler (see below).

.. note::

   OpenSTEF requires **Python >=3.12**. Verify your base image matches this constraint before building.

----

Scheduling Approaches
---------------------

Cron / Systemd Timers
^^^^^^^^^^^^^^^^^^^^^

The simplest approach for a single host. A crontab entry that runs inference every 15 minutes and retraining every Sunday night:

.. code-block:: bash

   # Inference — every 15 minutes
   */15 * * * *  docker run --rm -v /data/openstef:/var/openstef openstef-forecast:latest python forecast_job.py --mode predict

   # Retraining — Sunday at 02:00
   0 2 * * 0     docker run --rm -v /data/openstef:/var/openstef openstef-forecast:latest python forecast_job.py --mode train

Kubernetes CronJob
^^^^^^^^^^^^^^^^^^

For container-native environments, a Kubernetes ``CronJob`` provides automatic retries, resource limits, and log aggregation.

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
         backoffLimit: 2
         template:
           spec:
             restartPolicy: OnFailure
             containers:
               - name: forecast
                 image: <your-registry>/openstef-forecast:latest
                 args: ["python", "forecast_job.py", "--mode", "predict"]
                 env:
                   - name: OPENSTEF_ENV
                     value: production
                 resources:
                   requests:
                     memory: "1Gi"
                     cpu: "500m"
                   limits:
                     memory: "4Gi"
                     cpu: "2"
                 volumeMounts:
                   - name: model-storage
                     mountPath: /var/openstef
             volumes:
               - name: model-storage
                 persistentVolumeClaim:
                   claimName: openstef-pvc

.. tip::

   Set ``concurrencyPolicy: Forbid`` to prevent overlapping runs if a job takes longer than its interval. This is especially important for training jobs that can run for several minutes.

Apache Airflow
^^^^^^^^^^^^^^

When you have many forecasting locations or complex dependencies (e.g., data quality checks before training), a DAG-based orchestrator gives you better visibility and control.

.. code-block:: python

   from datetime import datetime, timedelta
   from airflow import DAG
   from airflow.operators.python import PythonOperator

   def run_forecast(**context):
       # Import here so Airflow workers only need openstef installed
       from openstef_models.workflows import CustomForecastingWorkflow
       # ... build workflow and call workflow.predict(dataset)

   def run_training(**context):
       from openstef_models.workflows import CustomForecastingWorkflow
       # ... build workflow and call workflow.fit(dataset)

   with DAG(
       dag_id="openstef_substation_north",
       start_date=datetime(2024, 1, 1),
       schedule_interval=timedelta(minutes=15),
       catchup=False,
       default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
   ) as dag:

       forecast_task = PythonOperator(
           task_id="run_forecast",
           python_callable=run_forecast,
       )

       # Retraining runs as a separate weekly DAG; this DAG is inference-only.

**[DIAGRAM: Airflow DAG showing data_quality_check → run_forecast → publish_results, with a separate weekly DAG for run_training → evaluate_model → promote_model]**

----

Cloud Deployment Options
-------------------------

OpenSTEF is cloud-agnostic. The table below maps common cloud services to the deployment patterns above.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Cloud
     - Service
     - Notes
   * - AWS
     - ECS Scheduled Tasks / EventBridge + Lambda
     - Use S3 for model artifact storage; see :doc:`data_integration` for S3 dataset patterns.
   * - Azure
     - Azure Container Apps Jobs / Azure Batch
     - Azure Blob Storage works as a drop-in for local model storage paths via ``fsspec``.
   * - GCP
     - Cloud Run Jobs / Cloud Scheduler
     - Pair with Vertex AI Experiments as an alternative to MLflow for run tracking.
   * - Any
     - Kubernetes CronJob (self-hosted or managed)
     - Most portable option; works identically across EKS, AKS, GKE, and on-premises.

For reading training data from cloud sources (S3, Databricks, InfluxDB), refer to :doc:`data_integration`.

----

Monitoring and Alerting
-----------------------

Workflow Callbacks
^^^^^^^^^^^^^^^^^^

OpenSTEF's callback system is the primary hook for production observability. Implement ``ForecastingCallback`` to emit metrics, send alerts, or write audit records at key lifecycle events:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_models.models.forecasting_model import ModelFitResult
   from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset

   class PrometheusCallback(ForecastingCallback):
       """Emit training and inference metrics to a Prometheus push-gateway."""

       def on_fit_end(
           self,
           context: WorkflowContext,
           result: ModelFitResult,
       ) -> None:
           if result is None:
               return
           flat_metrics = result.metrics_to_flat_dict()
           # push flat_metrics to your metrics backend here
           print(f"[{context.workflow.model_id}] training MAE: {flat_metrics.get('mae')}")

       def on_predict_end(
           self,
           context: WorkflowContext,
           result,
       ) -> None:
           # Log forecast latency, NaN rate, or any other runtime signal
           print(f"[{context.workflow.model_id}] forecast produced {len(result.data)} rows")

   workflow = CustomForecastingWorkflow(
       model_id="substation_north_v1",
       model=model,
       callbacks=[mlflow_callback, PrometheusCallback()],
   )

Multiple callbacks can be stacked; they execute in list order.

Evaluation Metrics
^^^^^^^^^^^^^^^^^^

After training, ``ModelFitResult.metrics_full`` contains a structured evaluation report. Use ``openstef_beam.evaluation`` to compute richer post-hoc metrics across lead times and time windows:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
   from openstef_core.types import LeadTime

   config = EvaluationConfig(
       available_ats=[],
       lead_times=[LeadTime(hours=1), LeadTime(hours=24)],
   )

   pipeline = EvaluationPipeline(
       config=config,
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       window_metric_providers=[],
       global_metric_providers=[],
   )

   report = pipeline.run_for_subset(
       filtering=LeadTime(hours=24),
       predictions=forecast,
   )

**[VISUALIZATION: Example evaluation report showing MAE and CRPS broken down by lead time (1h, 4h, 24h, 48h) as a bar chart]**

Health Checks
^^^^^^^^^^^^^

For long-running services or Kubernetes deployments, expose a simple health endpoint that verifies the workflow can load its model from storage:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow

   def health_check(model_id: str, storage) -> bool:
       try:
           workflow = CustomForecastingWorkflow.from_storage(
               model_id=model_id,
               storage=storage,
           )
           return workflow.model.is_fitted
       except Exception as exc:
           logging.error("Health check failed for %s: %s", model_id, exc)
           return False

----

Configuration Management
-------------------------

Avoid hard-coding model IDs, storage paths, and hyperparameters in your script. A lightweight pattern is to read from environment variables or a YAML file at startup:

.. code-block:: python

   import os
   from pathlib import Path

   MODEL_ID = os.environ.get("OPENSTEF_MODEL_ID", "default_model")
   MLFLOW_URI = os.environ.get("OPENSTEF_MLFLOW_URI", "/var/openstef/mlflow_tracking")
   ARTIFACTS_PATH = Path(os.environ.get("OPENSTEF_ARTIFACTS_PATH", "/var/openstef/artifacts"))

Pass these into your ``MLFlowStorage`` and ``CustomForecastingWorkflow`` constructors. This makes the same container image usable across development, staging, and production environments by varying only the environment variables injected at runtime.

----

Further Reading
---------------

- :doc:`data_integration` — connecting OpenSTEF to S3, Databricks, InfluxDB, and other data sources
- :doc:`use_cases` — end-to-end examples for congestion forecasting and other operational scenarios
- :doc:`migration_v3_v4` — if you are upgrading an existing deployment from V3