Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant architectural overhaul. The monolithic ``openstef`` package has been
split into focused sub-packages, the ``PredictionJobDataClass`` dict-based configuration has been
replaced with typed config objects, and the high-level pipeline functions have given way to
composable workflow classes. This page walks through every breaking change and shows you exactly
what to update.

.. note::

   This guide covers the library API. For deployment patterns after migration, see
   :doc:`deployment`. For connecting new data sources to V4 pipelines, see
   :doc:`data_integration`.

What Changed and Why
--------------------

V3 shipped everything — models, pipelines, data classes, feature engineering — inside a single
``openstef`` package. This made it hard to version individual components independently and forced
users to install the entire stack even when they only needed, say, the model layer. V4 splits
responsibilities across three installable packages:

- ``openstef-core`` — shared abstractions: base classes, data types, mixins, exceptions.
- ``openstef-models`` — forecasting models, preprocessing transforms, and workflow orchestration.
- ``openstef`` — the top-level package, now a thin integration layer that re-exports the most
  common entry points.

Alongside the restructure, the configuration model changed from a plain ``dict`` wrapped in a
dataclass to a fully validated Pydantic-style config hierarchy, and the pipeline functions
(``train_model_pipeline``, ``create_forecast_pipeline``) were replaced by explicit workflow
objects built from composable components.

.. note:: [DIAGRAM: V3 monolithic package vs V4 multi-package architecture showing openstef-core, openstef-models, and openstef as separate installable layers with dependency arrows]

Package Installation
--------------------

Before (V3):

.. code-block:: bash

   pip install openstef

After (V4):

.. code-block:: bash

   # Minimal install — core abstractions only
   pip install openstef-core

   # Add model training and forecasting
   pip install openstef-models

   # Full stack (pulls in both sub-packages)
   pip install openstef

If you only consume trained models at inference time, ``openstef-core`` and ``openstef-models``
are sufficient and avoid pulling in training-time dependencies.

Defining a Prediction Job
--------------------------

The ``PredictionJobDataClass`` dict pattern still exists in V4 for backward compatibility, but
the recommended path is to use the typed ``ForecastingWorkflowConfig`` (or a model-specific
config) from ``openstef_models``. The new config objects are validated at construction time,
provide IDE auto-complete, and carry explicit field documentation.

Before (V3):

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

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

After (V4):

.. code-block:: python

   from openstef_models.workflows.forecasting import ForecastingWorkflowConfig
   from openstef_core.data_types import Coordinate, LeadTime

   config = ForecastingWorkflowConfig(
       model="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],   # fractions, not percentages
       location=Coordinate(lat=52.0, lon=5.0),
       horizons=[LeadTime.from_string("PT36H")],
       target_column="load",
       model_id="example-287",
   )

Key differences to note:

- Quantiles are now **fractions** (``0.10``) rather than integer percentages (``10``).
- ``lat``/``lon`` are wrapped in a ``Coordinate`` object rather than passed as bare floats.
- ``horizon_minutes`` is replaced by a list of ``LeadTime`` objects, allowing multi-horizon
  configs in a single job.
- ``hyper_params`` and ``feature_names`` are no longer top-level fields; they live inside
  dedicated sub-configs on the workflow object.

Training a Model
----------------

V3 exposed a single ``train_model_pipeline`` function. V4 replaces this with a
``CustomForecastingWorkflow`` (or the factory helper ``build_forecasting_workflow``) that
separates construction from execution and makes each stage inspectable.

Before (V3):

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(**{...})  # as above
   input_data = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)
   train_data = input_data.iloc[:-200, :]

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

After (V4):

.. code-block:: python

   import pandas as pd
   from openstef_models.workflows.forecasting import build_forecasting_workflow
   from openstef_models.workflows.forecasting import ForecastingWorkflowConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.data_types import Coordinate, LeadTime

   config = ForecastingWorkflowConfig(
       model="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       location=Coordinate(lat=52.0, lon=5.0),
       horizons=[LeadTime.from_string("PT36H")],
       target_column="load",
       model_id="example-287",
   )

   raw = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)
   dataset = TimeSeriesDataset.from_dataframe(raw)

   workflow = build_forecasting_workflow(config)
   result = workflow.model.fit(dataset)

   print(result.metrics)   # train / val / test split metrics

The workflow object is reusable: call ``workflow.model.predict(new_dataset)`` after fitting
without rebuilding the pipeline.

Generating Forecasts
--------------------

Before (V3):

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   forecast = create_forecast_pipeline(
       pj,
       input_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

After (V4):

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   forecast_input = TimeSeriesDataset.from_dataframe(forecast_df)

   # workflow.model was fitted above, or loaded from MLflow
   forecast_dataset = workflow.model.predict(forecast_input)
   forecast_df_out = forecast_dataset.data

The ``predict`` method returns a ``ForecastDataset``, which exposes ``.data`` as a plain
``pandas.DataFrame`` for downstream compatibility.

.. note::

   MLflow storage is now opt-in via a callback rather than a required argument. Pass an
   ``MLFlowStorageCallback`` to ``build_forecasting_workflow`` via ``config.mlflow_storage``
   if you want automatic model persistence. See :doc:`deployment` for production storage
   patterns.

Preprocessing and Feature Engineering
--------------------------------------

V3 applied feature engineering implicitly inside the pipeline functions. V4 makes the
preprocessing chain explicit through a ``TransformPipeline`` composed of individual transform
classes. You can inspect, extend, or replace any step.

.. code-block:: python

   from openstef_models.preprocessing.transforms import (
       Selector,
       LagsAdder,
       CyclicFeaturesAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.preprocessing.pipeline import TransformPipeline
   from openstef_core.data_types import Coordinate, LeadTime
   from datetime import timedelta

   preprocessing = TransformPipeline(transforms=[
       Selector(selection=["load", "radiation", "wind_speed"]),
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=[LeadTime.from_string("PT36H")],
           target_column="load",
       ),
       CyclicFeaturesAdder(),
       RadiationDerivedFeaturesAdder(
           coordinate=Coordinate(lat=52.0, lon=5.0),
           radiation_column="radiation",
       ),
   ])

This replaces the implicit ``feature_names`` list on the V3 prediction job. Transforms are
applied in order and each one is independently testable.

Model Evaluation
----------------

V3 returned train/val/test DataFrames from ``train_model_pipeline`` and left metric computation
to the caller. V4 provides a dedicated ``EvaluationPipeline`` that computes metrics across
multiple dimensions — lead times, availability windows, and rolling evaluation periods — in a
single call.

.. code-block:: python

   from openstef_models.evaluation.pipeline import EvaluationPipeline, EvaluationConfig
   from openstef_core.data_types import AvailableAt, LeadTime, Window
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

   metrics = eval_pipeline.run(predictions_dataset)

.. note:: [VISUALIZATION: Example evaluation output showing metrics broken down by lead time and availability window as a table or heatmap]

Import Path Reference
---------------------

The table below maps the most commonly used V3 import paths to their V4 equivalents.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - V3 import
     - V4 import
   * - ``openstef.data_classes.prediction_job.PredictionJobDataClass``
     - ``openstef_models.workflows.forecasting.ForecastingWorkflowConfig``
   * - ``openstef.pipeline.train_model.train_model_pipeline``
     - ``openstef_models.workflows.forecasting.build_forecasting_workflow``
   * - ``openstef.pipeline.create_forecast.create_forecast_pipeline``
     - ``openstef_models.models.forecasting.ForecastingModel.predict``
   * - ``openstef.model.regressors.xgb.XGBOpenstfRegressor``
     - ``openstef_models.models.forecasters.xgb.XGBForecaster``
   * - ``openstef.feature_engineering.*``
     - ``openstef_models.preprocessing.transforms.*``
   * - ``openstef.metrics.*``
     - ``openstef_models.evaluation.*``
   * - ``openstef.exceptions.*``
     - ``openstef_core.exceptions.*``

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order to migrate an existing V3 codebase.

1. **Update dependencies.** Replace ``openstef`` in your ``requirements.txt`` or
   ``pyproject.toml`` with ``openstef-models`` (which pulls in ``openstef-core``). Keep
   ``openstef`` only if you rely on the compatibility shim.

2. **Audit prediction job construction.** Search for ``PredictionJobDataClass`` and replace
   each instance with a ``ForecastingWorkflowConfig``. Pay attention to the quantile format
   change (percentages → fractions) and the ``Coordinate`` wrapper.

3. **Replace pipeline function calls.** Swap ``train_model_pipeline(...)`` for
   ``build_forecasting_workflow(config)`` followed by ``workflow.model.fit(dataset)``.
   Swap ``create_forecast_pipeline(...)`` for ``workflow.model.predict(dataset)``.

4. **Migrate feature lists to transform pipelines.** If you passed ``feature_names`` on the
   prediction job, convert that list to a ``Selector`` transform at the head of a
   ``TransformPipeline``.

5. **Update MLflow integration.** Remove ``mlflow_tracking_uri`` and ``artifact_folder``
   arguments from pipeline calls. Configure an ``MLFlowStorageCallback`` on the workflow
   config instead.

6. **Run your test suite.** The ``TimeSeriesDataset.from_dataframe`` constructor accepts the
   same indexed DataFrames that V3 pipelines consumed, so data loading code typically needs
   no changes.

7. **Migrate metric collection.** Replace any manual metric computation on the returned
   DataFrames with an ``EvaluationPipeline`` run.

.. note::

   Steps 3–5 can be done incrementally. The ``openstef`` compatibility shim re-exports
   ``PredictionJobDataClass`` and the pipeline functions so you can migrate one prediction
   job at a time without breaking the rest of your application.

Common Pitfalls
---------------

- **Quantile format mismatch.** Passing integer percentages (``10``) where fractions (``0.10``)
  are expected raises a validation error at config construction time, not at predict time.
  Check all quantile lists when migrating.

- **Missing ``cutoff_history``.** The V4 ``ForecastingModel`` requires you to set
  ``cutoff_history`` explicitly when your preprocessing includes lag features. Omitting it
  causes the model to train on rows that contain NaN lag values, silently degrading accuracy.
  Set it to the maximum lag duration in your ``LagsAdder``.

- **``TimeSeriesDataset`` index requirements.** ``TimeSeriesDataset.from_dataframe`` expects a
  ``DatetimeIndex`` with a consistent frequency. If your V3 data had gaps, call
  ``df.asfreq("15min")`` before wrapping it.

- **MLflow model loading.** V4 MLflow artifacts store the full ``ForecastingModel`` object,
  not just the underlying regressor. Loading a V3 artifact into a V4 workflow will fail.
  Retrain models after migration rather than attempting to load old artifacts.