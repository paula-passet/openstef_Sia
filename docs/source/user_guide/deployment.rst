Production Deployment
=====================

This page covers practical patterns for deploying OpenSTEF-based forecasting systems in production. It assumes you already have a working pipeline — if you are still building one, start with the :doc:`use_cases` page for end-to-end examples.

OpenSTEF is a **library**, not a deployable application. You integrate it into your own infrastructure: a cron job, a containerised service, an orchestration platform, or a cloud workflow. The patterns below cover the most common approaches, from the simplest possible setup to full enterprise orchestration.

.. note:: [DIAGRAM: Deployment topology showing the three tiers — scheduled script, containerised service, and orchestrated pipeline — with arrows indicating data flow from source systems through OpenSTEF to forecast sinks.]

.. contents:: On this page
   :local:
   :depth: 2


Anatomy of a Production Forecasting Job
----------------------------------------

Regardless of the deployment platform, every production OpenSTEF job performs the same logical steps:

1. **Fetch input data** — load recent measurements and weather features from your data store.
2. **Train or reload a model** — either retrain periodically or load a previously persisted model.
3. **Generate forecasts** — call ``workflow.predict()``.
4. **Write outputs** — push forecasts to a database, message bus, or object store.
5. **Emit metrics** — record timing, data quality, and forecast quality indicators.

The sections below show how to wrap these steps in different deployment contexts. For data ingestion patterns, see :doc:`data_integration`.


Scheduled Script (Simplest Approach)
--------------------------------------

The lowest-overhead deployment is a Python script executed on a schedule by cron, a task scheduler, or a cloud function trigger. This is appropriate for a single forecasting target with modest data volumes.

.. code-block:: python

   # forecast_job.py
   import logging
   from datetime import timedelta
   from pathlib import Path

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.integrations.mlflow import MLFlowStorage
   from openstef_models.integrations.mlflow.mlflow_storage_callback import MLFlowStorageCallback
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_models.presets.forecasting_workflow import GBLinearForecaster
   from openstef_core.types import LeadTime, Q

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   MODEL_DIR = Path("/var/lib/openstef/models")
   MLFLOW_URI = "sqlite:///var/lib/openstef/mlflow.db"

   def load_data() -> TimeSeriesDataset:
       # Replace with your data source — see the data_integration guide
       raise NotImplementedError

   def write_forecasts(forecast) -> None:
       # Replace with your output sink
       raise NotImplementedError

   def main():
       dataset = load_data()

       storage = MLFlowStorage(
           tracking_uri=MLFLOW_URI,
           local_artifacts_path=MODEL_DIR,
       )

       workflow = create_forecasting_workflow(
           config=ForecastingWorkflowConfig(
               model_id="substation_a_load",
               model="gblinear",
               horizons=[LeadTime.from_string("PT36H")],
               quantiles=[Q(0.1), Q(0.5), Q(0.9)],
               target_column="load",
               temperature_column="temperature_2m",
               mlflow_storage=storage,
               gblinear_hyperparams=GBLinearForecaster.HyperParams(n_steps=100),
           )
       )

       logger.info("Fitting model")
       result = workflow.fit(dataset)
       if result is not None:
           logger.info("Training metrics:\n%s", result.metrics_full.to_dataframe())

       logger.info("Generating forecast")
       forecast = workflow.predict(dataset)
       write_forecasts(forecast)

   if __name__ == "__main__":
       main()

A crontab entry to run this every 15 minutes would look like:

.. code-block:: text

   */15 * * * * /usr/bin/python /opt/openstef/forecast_job.py >> /var/log/openstef/forecast.log 2>&1

.. note::

   Retraining on every run is expensive. In practice, use the ``model_reuse_enable`` and
   ``model_reuse_max_age`` options on ``MLFlowStorageCallback`` to skip retraining when a
   recent model already exists. See `Model Persistence`_ below.


Containerisation with Docker
------------------------------

Packaging your forecasting job as a Docker image makes it portable across environments and simplifies dependency management.

A minimal ``Dockerfile``:

.. code-block:: text

   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY forecast_job.py .

   CMD ["python", "forecast_job.py"]

A matching ``requirements.txt``:

.. code-block:: text

   openstef-core
   openstef-models[mlflow,gblinear]
   openstef-beam

For local testing with a mounted model directory:

.. code-block:: text

   docker run --rm \
     -v /var/lib/openstef:/var/lib/openstef \
     -e MLFLOW_TRACKING_URI=sqlite:////var/lib/openstef/mlflow.db \
     my-openstef-job:latest

.. note::

   Pass secrets (database credentials, API keys) via environment variables or a secrets manager — never bake them into the image. Read them in your Python code with ``os.environ``.


Model Persistence
------------------

OpenSTEF separates model training from prediction. The ``MLFlowStorageCallback`` handles both persistence and intelligent model reuse, so you do not need to manage model files manually.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.integrations.mlflow import MLFlowStorage
   from openstef_models.integrations.mlflow.mlflow_storage_callback import MLFlowStorageCallback
   from openstef_core.types import Q

   storage = MLFlowStorage(
       tracking_uri="postgresql+psycopg2://user:pass@db-host/mlflow",
       local_artifacts_path="/mnt/shared/mlflow_artifacts",
   )

   callback = MLFlowStorageCallback(
       storage=storage,
       # Skip retraining if a model was trained within the last 7 days
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
       # Keep the better-performing model when a new one is trained
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       # Bias selection slightly toward newer models
       model_selection_old_model_penalty=1.2,
   )

Key points:

- ``model_reuse_enable=True`` means the workflow will load and reuse the last trained model if it is
  younger than ``model_reuse_max_age``. Only the ``predict`` path runs on most invocations.
- ``model_selection_enable=True`` means a newly trained model only replaces the stored model if it
  scores better (accounting for the age penalty).
- For single-machine deployments or development, ``LocalModelStorage`` from
  ``openstef_models.integrations.joblib`` provides file-based persistence without an MLflow server.

.. warning::

   ``LocalModelStorage`` uses joblib/pickle serialisation. Never load a model file from an untrusted
   source, as arbitrary code can execute during deserialisation.


Cloud Deployment Options
--------------------------

OpenSTEF jobs are stateless between runs (state lives in the model store and data store), which makes them straightforward to deploy on any cloud compute primitive.

**Kubernetes CronJob**

Run the containerised job on a schedule inside a Kubernetes cluster:

.. code-block:: text

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
                 image: my-registry/openstef-job:latest
                 env:
                   - name: MLFLOW_TRACKING_URI
                     valueFrom:
                       secretKeyRef:
                         name: openstef-secrets
                         key: mlflow-uri
             restartPolicy: OnFailure

**Serverless Functions (AWS Lambda / Azure Functions / GCP Cloud Run Jobs)**

For infrequent or event-driven forecasting, a serverless function avoids the overhead of a persistent container. Package your job as a Lambda layer or a Cloud Run Job image. The main constraint is cold-start time — loading a large model from object storage on every invocation adds latency. Mitigate this by:

- Keeping models in a fast store (e.g., EFS on AWS, Filestore on GCP) mounted to the function.
- Using ``model_reuse_enable=True`` so the function only retrains on a weekly schedule, not every call.

**Managed Workflow Orchestrators (Airflow, Prefect, Dagster)**

For multi-target deployments or pipelines with complex dependencies, an orchestrator gives you retries, observability, and parallelism. Wrap each OpenSTEF step as a task:

.. code-block:: python

   # Example: Airflow task structure (pseudocode — adapt to your DAG framework)
   from airflow.decorators import task, dag
   from datetime import datetime

   @dag(schedule="*/15 * * * *", start_date=datetime(2024, 1, 1), catchup=False)
   def openstef_pipeline():

       @task
       def fetch_data(model_id: str) -> dict:
           # Load from your data source
           ...

       @task
       def train_and_forecast(model_id: str, data: dict) -> dict:
           # Run OpenSTEF workflow
           ...

       @task
       def write_output(forecast: dict) -> None:
           # Push to output sink
           ...

       for model_id in ["substation_a", "substation_b", "substation_c"]:
           data = fetch_data(model_id)
           forecast = train_and_forecast(model_id, data)
           write_output(forecast)

   openstef_pipeline()

This pattern scales naturally to hundreds of forecasting targets by mapping over a list of model IDs.


Monitoring and Observability
------------------------------

**Structured logging**

OpenSTEF uses Python's standard ``logging`` module throughout. Configure a structured log handler (e.g., JSON output to stdout) and ship logs to your preferred log aggregation platform:

.. code-block:: python

   import logging
   import json

   class JsonFormatter(logging.Formatter):
       def format(self, record):
           return json.dumps({
               "level": record.levelname,
               "logger": record.name,
               "message": record.getMessage(),
               "timestamp": self.formatTime(record),
           })

   handler = logging.StreamHandler()
   handler.setFormatter(JsonFormatter())
   logging.getLogger("openstef").addHandler(handler)
   logging.getLogger("openstef").setLevel(logging.INFO)

**Forecast quality metrics**

After each training run, ``ModelFitResult`` exposes evaluation metrics that you should record:

.. code-block:: python

   result = workflow.fit(dataset)
   if result is not None:
       metrics_df = result.metrics_full.to_dataframe()
       # Emit to your metrics platform (Prometheus, Datadog, CloudWatch, etc.)
       for _, row in metrics_df.iterrows():
           emit_metric(name=row["metric"], value=row["value"], tags={"model_id": "substation_a"})

       if result.metrics_test is not None:
           test_df = result.metrics_test.to_dataframe()
           # Log held-out test metrics separately for drift detection

For deeper retrospective analysis — evaluating accuracy across lead times, time windows, and data
subsets — use ``openstef_beam``'s ``EvaluationPipeline``:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
   from datetime import timedelta

   eval_config = EvaluationConfig()
   eval_pipeline = EvaluationPipeline(config=eval_config)
   report = eval_pipeline.run(forecast_dataset)

   # report.to_dataframe() gives per-lead-time, per-window metrics

**Health checks**

Expose a simple health endpoint if your job runs as a long-lived service. At minimum, check that:

- The model store is reachable (MLflow tracking URI responds).
- The last successful forecast timestamp is within the expected interval.
- Input data freshness — flag stale data before it silently degrades forecast quality.


Separation of Training and Prediction
---------------------------------------

In high-frequency deployments it is common to decouple the training schedule from the prediction schedule. Training might run nightly while predictions run every 15 minutes. The ``MLFlowStorageCallback`` supports this naturally: the prediction job loads the latest stored model without triggering a refit.

.. code-block:: python

   # Prediction-only job: model_reuse_max_age is long, so fit() is always skipped
   callback = MLFlowStorageCallback(
       storage=storage,
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=30),  # Never retrain in this job
   )

   workflow = CustomForecastingWorkflow(
       model_id="substation_a_load",
       model=model,
       callbacks=[callback],
   )

   # fit() loads the stored model; predict() generates the forecast
   workflow.fit(versioned_dataset)
   forecast = workflow.predict(versioned_dataset)

The separate training job uses a short ``model_reuse_max_age`` (e.g., one day) and runs on its own schedule.


Summary
--------

- **Start simple**: a cron-scheduled Python script is sufficient for a single forecasting target.
- **Containerise early**: Docker makes your job portable and reproducible across environments.
- **Use MLflow for model management**: ``MLFlowStorageCallback`` handles persistence, reuse, and selection automatically.
- **Decouple training from prediction** when prediction frequency is high.
- **Emit metrics after every run**: use ``ModelFitResult.metrics_full`` for online monitoring and ``EvaluationPipeline`` for retrospective analysis.

For data ingestion patterns (S3, Databricks, InfluxDB), see :doc:`data_integration`. For use-case-specific pipeline configurations, see :doc:`use_cases`.