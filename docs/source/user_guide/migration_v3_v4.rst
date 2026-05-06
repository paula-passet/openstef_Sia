Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant redesign of the library. The monolithic ``openstef`` package has been replaced by a modular mono-repo of focused packages, the ``PredictionJobDataClass``-centred API has been replaced by typed configuration objects and composable workflow classes, and the high-level pipeline functions (``train_model_pipeline``, ``create_forecast_pipeline``) no longer exist as top-level entry points.

This page covers every breaking change you are likely to encounter, with before/after code examples for each one. If you are looking for practical end-to-end examples of what to build *after* migrating, see :doc:`use_cases`. For production deployment patterns see :doc:`deployment`.

.. note::

   V4 is structured as a **mono-repo**. Install the sub-packages you need rather than a single ``openstef`` wheel:

   .. code-block:: bash

      pip install openstef-core openstef-models          # core + standard forecasting
      pip install openstef-beam                          # backtesting / evaluation
      pip install openstef-meta                          # ensemble / meta-learning models

---

What Changed and Why
--------------------

V3 was built around a single ``openstef`` package with a flat pipeline API. Every workflow started by constructing a ``PredictionJobDataClass`` dictionary and passing it to a pipeline function. This worked well for the original Alliander use case but made it hard to extend, test, or integrate into other software stacks.

V4 introduces four design goals that drive every breaking change:

- **Modularity** — install only what you need; extend without forking.
- **Typed configuration** — ``ForecastingWorkflowConfig`` replaces the loosely-typed prediction job dict.
- **Composable models** — ``ForecastingModel`` wraps preprocessing, a forecaster, and postprocessing as explicit pipeline stages.
- **Unopinionated orchestration** — V4 does not assume MLflow, a specific scheduler, or a specific data store.

---

Package Structure
-----------------

The single ``openstef`` package is gone. Its responsibilities are now split across the mono-repo packages.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - V3 import path
     - V4 replacement
   * - ``openstef.data_classes.prediction_job``
     - ``openstef_models.presets.forecasting_workflow`` (``ForecastingWorkflowConfig``)
   * - ``openstef.pipeline.train_model``
     - ``openstef_models.models`` (``ForecastingModel``)
   * - ``openstef.pipeline.create_forecast``
     - ``openstef_models.models`` (``ForecastingModel``)
   * - ``openstef.pipeline.*`` (all pipelines)
     - ``openstef_models.presets.forecasting_workflow`` (``create_forecasting_workflow``)
   * - ``openstef.model.regressors.*``
     - ``openstef_models.models.forecasting.*`` (e.g. ``XGBoostForecaster``)
   * - Backtesting utilities
     - ``openstef_beam``
   * - Ensemble / meta-learning
     - ``openstef_meta``

---

Defining a Forecasting Job
--------------------------

The most pervasive change is the replacement of the ``PredictionJobDataClass`` dict with ``ForecastingWorkflowConfig``. The new class is a Pydantic model: every field is typed, validated on construction, and documented via ``Field`` descriptions.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
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
   )

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
   )
   from openstef_core.data_types import Quantile as Q

   config = ForecastingWorkflowConfig(
       model_id="forecast-287",
       model="xgboost",
       quantiles=[Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9)],
       location=LocationConfig(
           name="Example",
           coordinate=(52.0, 5.0),
           country_code="NL",
       ),
       sample_interval=timedelta(minutes=15),
   )

Key differences to note:

- ``id`` (integer) becomes ``model_id`` (string identifier).
- ``model="xgb"`` becomes ``model="xgboost"`` — model names are now the full canonical names.
- Quantiles are typed ``Quantile`` values in the range ``[0, 1]``, not integer percentages.
- ``lat``/``lon`` are grouped into a ``LocationConfig`` object, which also drives holiday feature generation via ``country_code``.
- ``horizon_minutes`` and ``resolution_minutes`` are replaced by ``sample_interval`` (a ``timedelta``); horizon is now a property of the data splitter, not the job.

---

Training a Model
----------------

V3 exposed a single ``train_model_pipeline`` function. V4 uses ``ForecastingModel``, which separates the pipeline stages (preprocessing transforms, forecaster, postprocessing transforms) and exposes a standard ``fit`` / ``predict`` interface.

**Before (V3):**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(id=287, model="xgb", ...)
   input_data = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)

   train, val, test = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   import pandas as pd
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_models.integrations.mlflow import MLFlowStorage
   from openstef_core.data_types import Quantile as Q
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model_id="forecast-287",
       model="xgboost",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       location=LocationConfig(name="Example", coordinate=(52.0, 5.0)),
       sample_interval=timedelta(minutes=15),
       mlflow_storage=MLFlowStorage(tracking_uri="./mlflow_trained_models"),
   )

   workflow = create_forecasting_workflow(config)

   input_data = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)
   workflow.fit(input_data)

The ``create_forecasting_workflow`` factory assembles the correct preprocessing transforms, forecaster, and postprocessing steps from the config. MLflow integration is now opt-in: pass an ``MLFlowStorage`` instance to the config rather than a tracking URI string argument.

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_1.mmd

---

Making a Forecast
-----------------

**Before (V3):**

.. code-block:: python

   import numpy as np
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Mask the load column for the forecast horizon
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   # After workflow.fit() has been called (or a model loaded from MLflow):
   forecast = workflow.predict(input_data)

The ``predict`` method on ``ForecastingModel`` handles feature engineering and postprocessing internally. You no longer need to manually null out the load column — the model's data splitter determines which rows are targets and which are context.

---

Model Types and Forecaster Names
---------------------------------

The short aliases used in V3 ``model`` fields have been replaced with explicit forecaster class names and canonical string identifiers.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - V3 ``model`` string
     - V4 config string
     - V4 forecaster class
   * - ``"xgb"``
     - ``"xgboost"``
     - ``openstef_models.models.forecasting.xgboost_forecaster.XGBoostForecaster``
   * - ``"lgb"``
     - ``"lgbm"``
     - ``openstef_models.models.forecasting.lgbm_forecaster.LGBMForecaster``
   * - ``"gblinear"``
     - ``"gblinear"``
     - ``openstef_models.models.forecasting.gblinear_forecaster.GBLinearForecaster``

For ensemble and meta-learning models (stacking, learned-weights combiners) use ``openstef-meta``:

.. code-block:: python

   from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
   from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
       XGBCombinerHyperParams,
       WeightsCombiner,
   )

---

Feature Engineering and Transforms
------------------------------------

In V3, feature engineering was implicit — the pipeline functions applied a fixed set of transforms internally. In V4, transforms are explicit pipeline stages passed to ``ForecastingModel``.

**Before (V3):** transforms were invisible to the caller.

**After (V4):** you compose transforms explicitly, giving full control:

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_models.transforms.general import (
       OutlierHandler,
       Imputer,
       Scaler,
       Shifter,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_core.transforms import TransformPipeline

   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=[
           OutlierHandler(),
           Imputer(),
           WindPowerFeatureAdder(),
           Shifter(lags=[1, 2, 3, 48]),   # lag features
       ]),
       forecaster=XGBoostForecaster(XGBoostHyperParams()),
       postprocessing=TransformPipeline(transforms=[Scaler()]),
       target_column="load",
       cutoff_history=14,   # days to drop due to lag-14 NaNs
   )

.. warning::

   The ``cutoff_history`` parameter is critical when using lag-based transforms. A ``Shifter`` with a lag of *N* days creates NaN values for the first *N* days of training data. Set ``cutoff_history=N`` to exclude those rows. This cannot be inferred automatically.

---

MLflow Integration
------------------

V3 passed MLflow URIs as string arguments to pipeline functions. V4 makes MLflow an explicit, optional callback.

**Before (V3):**

.. code-block:: python

   train_model_pipeline(
       pj, data,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

   storage = MLFlowStorage(tracking_uri="./mlflow_trained_models")

   # Pass to config (preset path):
   config = ForecastingWorkflowConfig(..., mlflow_storage=storage)

   # Or attach directly to a workflow (manual path):
   from openstef_models.models.forecasting_model import CustomForecastingWorkflow
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="forecast-287",
       callbacks=[MLFlowStorageCallback(storage=storage)],
   )

Model reuse and model selection (previously ``check_old_model_age``) are now controlled by fields on ``MLFlowStorageCallback``:

.. code-block:: python

   MLFlowStorageCallback(
       storage=storage,
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
       model_selection_enable=True,
       model_selection_metric="mae",
   )

---

Backtesting and Evaluation
--------------------------

V3 included backtesting utilities inside the main ``openstef`` package. In V4 these live in the dedicated ``openstef-beam`` package (Backtesting, Evaluation, Analysis, Metrics).

.. code-block:: python

   # V4 — backtesting
   from openstef_beam.backtesting.pipeline import Pipeline as BacktestPipeline

   # V4 — evaluation
   from openstef_beam.evaluation.pipeline import EvaluationPipeline
   from openstef_beam.evaluation.config import EvaluationConfig

The evaluation pipeline computes metrics across prediction availability times, lead times, and rolling windows. See :doc:`use_cases` for a worked backtesting example.

---

Step-by-Step Migration Checklist
---------------------------------

Work through these steps in order when migrating an existing V3 codebase.

1. **Update dependencies.** Replace ``openstef`` in your ``requirements.txt`` / ``pyproject.toml`` with the relevant V4 packages (``openstef-core``, ``openstef-models``, and optionally ``openstef-beam`` / ``openstef-meta``).

2. **Replace prediction job construction.** Find every ``PredictionJobDataClass(...)`` call and replace it with ``ForecastingWorkflowConfig``. Pay attention to:

   - ``model`` string aliases (``"xgb"`` → ``"xgboost"``, ``"lgb"`` → ``"lgbm"``).
   - Quantiles as ``Quantile`` fractions, not integer percentages.
   - ``lat``/``lon`` wrapped in ``LocationConfig``.

3. **Replace pipeline function calls.** Replace ``train_model_pipeline(pj, data, ...)`` with ``create_forecasting_workflow(config)`` followed by ``workflow.fit(data)``. Replace ``create_forecast_pipeline(pj, data, ...)`` with ``workflow.predict(data)``.

4. **Audit feature engineering.** If you relied on V3's implicit transforms, replicate them explicitly using ``TransformPipeline`` and the transforms in ``openstef_models.transforms``. Set ``cutoff_history`` appropriately for any lag-based transforms.

5. **Migrate MLflow wiring.** Replace URI string arguments with ``MLFlowStorage`` and ``MLFlowStorageCallback``. Move ``check_old_model_age`` logic to ``model_reuse_max_age`` on the callback.

6. **Move backtesting code.** If you used V3 backtesting utilities, migrate to ``openstef_beam``.

7. **Run your test suite.** V4's typed config will surface mismatches (wrong quantile range, unknown model name, missing required fields) at construction time rather than deep inside a pipeline call.

.. note::

   If you maintain a custom ``AbstractDataManager`` or ``AbstractPredictionDataManager`` subclass from V3, those interfaces no longer exist in V4. Data loading is now the caller's responsibility — pass a plain ``pd.DataFrame`` to ``fit`` and ``predict``. See :doc:`data_integration` for patterns that read from S3, Databricks, and InfluxDB.