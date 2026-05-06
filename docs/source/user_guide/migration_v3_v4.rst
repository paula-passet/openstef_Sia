Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant architectural overhaul of the library. The monolithic ``openstef`` package has been split into focused sub-packages, the ``PredictionJobDataClass`` dict-based workflow has been replaced with typed configuration objects, and pipelines are now composed from explicit, reusable components. This page walks through every breaking change and shows concrete before/after code so you can migrate incrementally.

.. note::

   This guide covers the library API only. For deployment patterns after migration, see :doc:`deployment`. For connecting new data sources, see :doc:`data_integration`.

----

What Changed and Why
--------------------

V3 shipped as a single ``openstef`` package where a flat dictionary (wrapped in ``PredictionJobDataClass``) drove every pipeline. This made it easy to get started but hard to extend: adding a new model type, evaluation metric, or preprocessing step required modifying core library code.

V4 replaces that design with:

- **A multi-package layout** — functionality is split across ``openstef-core``, ``openstef-models``, ``openstef-beam``, and ``openstef-meta``.
- **Typed configuration objects** — ``BaseConfig`` / ``BaseModel`` (Pydantic-backed) replace the ``PredictionJobDataClass`` dict.
- **Composable pipelines** — ``ForecastingModel`` and ``CustomForecastingWorkflow`` are assembled from explicit preprocessing, forecaster, and postprocessing transforms rather than inferred from a job dict.
- **Python ≥ 3.12 required** — V4 uses modern type-parameter syntax (``class Predictor[I, O]``).

----

Package Structure Changes
--------------------------

The single ``openstef`` package is now a meta-package that installs four focused libraries.

**Before (V3):**

.. code-block:: python

   pip install openstef
   # Everything lives under the openstef namespace
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

**After (V4):**

.. code-block:: bash

   pip install openstef          # installs all four sub-packages
   # or install only what you need:
   pip install openstef-core     # datasets, base models, transforms
   pip install openstef-models   # forecasting model implementations
   pip install openstef-beam     # backtesting, evaluation, analysis, metrics
   pip install openstef-meta     # stacking / ensemble utilities

The top-level ``openstef`` name still works as a convenience install, but imports now come from the sub-package namespaces:

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_1.mmd

----

Defining a Forecasting Job
---------------------------

The most pervasive change is how you specify *what* to train and forecast. In V3 a plain dict was cast to ``PredictionJobDataClass``. In V4 you build a typed configuration object and pass it to a workflow factory.

**Before (V3):**

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline

   pj = PredictionJobDataClass(**dict(
       id=287,
       model="xgb",
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
       default_modelspecs=None,
       save_train_forecasts=True,
   ))

   input_data = pd.read_csv("data/model_input.csv", index_col="index", parse_dates=True)
   train_data = input_data.iloc[:-200, :]

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from pathlib import Path
   from openstef_meta.workflows.forecasting_workflow import (
       ForecastingWorkflowConfig,
       build_forecasting_workflow,
   )
   from openstef_core.datasets.time_series_dataset import TimeSeriesDataset
   import pandas as pd

   config = ForecastingWorkflowConfig(
       model="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       horizons=["PT47H"],
       target_column="load",
       mlflow_storage=MLFlowStorage(
           tracking_uri="./mlflow_tracking",
           local_artifacts_path="./mlflow_tracking_artifacts",
       ),
   )

   workflow = build_forecasting_workflow(config)

   raw = pd.read_csv("data/model_input.csv", index_col="index", parse_dates=True)
   dataset = TimeSeriesDataset.from_dataframe(raw)

   result = workflow.fit(dataset)

Key differences to note:

- Quantiles are now **fractions** (``0.10``) not percentages (``10``).
- Horizons are **ISO 8601 duration strings** (``"PT47H"``) not integer minutes.
- ``mlflow_tracking_uri`` and ``artifact_folder`` are consolidated into a single ``MLFlowStorage`` object.
- The pipeline returns a structured result object; ``train``, ``val``, ``test`` splits are no longer returned as bare DataFrames.

----

Running a Forecast
-------------------

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   forecast = create_forecast_pipeline(
       pj,
       input_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )
   print(forecast.head())

**After (V4):**

.. code-block:: python

   from openstef_beam.visualization.forecast_time_series_plotter import (
       ForecastTimeSeriesPlotter,
   )

   forecast = workflow.predict(dataset)

   # forecast is a ForecastDataset — access median and quantile series explicitly
   print(forecast.data.tail())
   print(forecast.median_series)

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=dataset.select_version().data["load"])
       .add_model(
           model_name="xgb",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot()
   )
   fig.write_html("forecast_plot.html")

.. note:: [VISUALIZATION: Example forecast plot showing median prediction line with shaded quantile bands over a 47-hour horizon]

The ``ForecastDataset`` return type gives you typed access to ``.median_series``, ``.quantiles_data``, and the full ``.data`` DataFrame rather than receiving a single untyped DataFrame.

----

Composing Custom Pipelines
---------------------------

V3 pipelines were opaque: you called a top-level function and the library decided which preprocessing steps to apply. V4 exposes the full composition so you can swap individual transforms.

**Before (V3):** No public API for customising preprocessing steps — you had to subclass or monkey-patch internal modules.

**After (V4):**

.. code-block:: python

   from openstef_core.transforms.pipeline import TransformPipeline
   from openstef_core.transforms.lags import LagsAdder
   from openstef_core.transforms.cyclic import CyclicFeaturesAdder
   from openstef_core.transforms.radiation import RadiationDerivedFeaturesAdder
   from openstef_models.forecasters.xgboost import XGBoostForecaster
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_meta.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_beam.callbacks.mlflow import MLFlowStorageCallback
   from openstef_beam.storage.mlflow import MLFlowStorage
   from datetime import timedelta
   from pathlib import Path

   workspace_dir = Path("./workspace")

   preprocessing = TransformPipeline(transforms=[
       LagsAdder(history_available=timedelta(days=14), horizons=["PT47H"]),
       CyclicFeaturesAdder(),
       RadiationDerivedFeaturesAdder(coordinate=(52.0, 5.0)),
   ])

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=XGBoostForecaster(),
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       tags={"model": "xgb", "version": "2.0.0"},
   )

   pipeline = CustomForecastingWorkflow(
       model_id="xgb_demand_v2",
       model=model,
       callbacks=[
           MLFlowStorageCallback(
               storage=MLFlowStorage(
                   tracking_uri=str(workspace_dir / "mlflow_tracking"),
                   local_artifacts_path=workspace_dir / "mlflow_tracking_artifacts",
               ),
               model_reuse_enable=False,
           )
       ],
   )

   result = pipeline.fit(dataset)
   forecast = pipeline.predict(dataset)

.. note::

   The ``cutoff_history`` parameter on ``ForecastingModel`` is important when using lag-based features. A ``LagsAdder`` with a 14-day lag creates NaN rows for the first 14 days of training data. Set ``cutoff_history=timedelta(days=14)`` to exclude those rows automatically.

----

Configuration Files
--------------------

V4 configuration objects can be serialised to and loaded from YAML, which is useful for reproducible experiments and deployment.

.. code-block:: python

   from openstef_core.base_model import write_yaml_config, read_yaml_config
   from openstef_meta.workflows.forecasting_workflow import ForecastingWorkflowConfig

   # Save
   write_yaml_config(config, Path("config/xgb_demand.yaml"))

   # Load
   config = read_yaml_config(
       Path("config/xgb_demand.yaml"),
       ForecastingWorkflowConfig,
   )

There is no equivalent in V3 — configuration was always constructed in Python code.

----

Evaluation and Backtesting
---------------------------

V3 had no first-class evaluation framework. V4 ships ``openstef-beam`` with a dedicated ``EvaluationPipeline`` that segments results across availability times, lead times, and rolling windows.

.. code-block:: python

   from openstef_beam.evaluation.evaluation_pipeline import (
       EvaluationPipeline,
       EvaluationConfig,
   )
   from openstef_beam.evaluation.config import AvailableAt, LeadTime, Window
   from datetime import timedelta

   eval_config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=config.quantiles,
       window_metric_providers=[...],
       global_metric_providers=[...],
   )

See :doc:`use_cases` for a complete backtesting walkthrough built on ``openstef-beam``.

----

Step-by-Step Migration Checklist
----------------------------------

Work through these steps in order. Each step is independently testable.

1. **Upgrade Python to ≥ 3.12.** V4 uses modern generic syntax that does not back-port.

2. **Update your install.**

   .. code-block:: bash

      pip install --upgrade openstef

3. **Replace ``PredictionJobDataClass`` construction** with a typed ``ForecastingWorkflowConfig`` (or ``CustomForecastingWorkflow`` for bespoke pipelines). Map fields using the table below.

4. **Convert quantiles from percentages to fractions** — ``[10, 50, 90]`` → ``[0.10, 0.50, 0.90]``.

5. **Convert horizon from minutes to ISO 8601** — ``horizon_minutes=2880`` → ``horizons=["PT48H"]``.

6. **Replace ``train_model_pipeline`` calls** with ``workflow.fit(dataset)``.

7. **Replace ``create_forecast_pipeline`` calls** with ``workflow.predict(dataset)``.

8. **Update MLflow arguments** — replace ``mlflow_tracking_uri`` + ``artifact_folder`` kwargs with an ``MLFlowStorage`` object passed to ``MLFlowStorageCallback``.

9. **Update import paths** throughout your codebase from ``openstef.*`` to the appropriate sub-package (``openstef_core.*``, ``openstef_models.*``, ``openstef_beam.*``).

10. **Run your test suite.** The typed return values (``ForecastDataset``, evaluation result objects) will surface any downstream code that assumed bare DataFrames.

----

V3 → V4 Field Mapping Reference
---------------------------------

+-------------------------------+------------------------------------------+-----------------------------+
| V3 ``PredictionJobDataClass`` | V4 equivalent                            | Notes                       |
+===============================+==========================================+=============================+
| ``model``                     | ``config.model``                         | Same string values          |
+-------------------------------+------------------------------------------+-----------------------------+
| ``quantiles``                 | ``config.quantiles``                     | Fractions, not percentages  |
+-------------------------------+------------------------------------------+-----------------------------+
| ``horizon_minutes``           | ``config.horizons``                      | ISO 8601 list               |
+-------------------------------+------------------------------------------+-----------------------------+
| ``resolution_minutes``        | Dataset-level, not config                | Set on ``TimeSeriesDataset``|
+-------------------------------+------------------------------------------+-----------------------------+
| ``lat`` / ``lon``             | ``config.location.coordinate``           | Tuple ``(lat, lon)``        |
+-------------------------------+------------------------------------------+-----------------------------+
| ``mlflow_tracking_uri``       | ``MLFlowStorage.tracking_uri``           | Passed via callback         |
+-------------------------------+------------------------------------------+-----------------------------+
| ``artifact_folder``           | ``MLFlowStorage.local_artifacts_path``   | Passed via callback         |
+-------------------------------+------------------------------------------+-----------------------------+
| ``feature_names``             | ``config.selected_features``             | Via ``Selector`` transform  |
+-------------------------------+------------------------------------------+-----------------------------+
| ``hyper_params``              | Forecaster constructor kwargs            | Per-forecaster class        |
+-------------------------------+------------------------------------------+-----------------------------+

----

.. note::

   If you maintain a custom database connector (``openstef-dbc`` in V3), the connector interface has also changed. See :doc:`data_integration` for the V4 data ingestion patterns.