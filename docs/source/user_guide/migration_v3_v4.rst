Migration Guide: V3 to V4
=========================

This page covers everything you need to migrate an existing OpenSTEF V3 integration
to V4. V4 is a significant architectural revision — the library has been restructured
from a single monolithic package into a modular mono-repo, and the core abstractions
for defining and running forecasting jobs have changed substantially. Read this guide
before upgrading; the changes are breaking but the migration path is straightforward.

.. note::

   If you are starting a new project, skip this page entirely and go straight to the
   :doc:`use_cases` page for current V4 patterns.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 shipped as a single ``openstef`` package. Everything — data classes, pipelines,
model storage, feature engineering — lived under one import namespace. This made the
library easy to install but difficult to extend: swapping out a model backend or
integrating a custom preprocessing step required forking internal code.

V4 replaces this with a **modular mono-repo** of focused packages. Each package has a
clear responsibility and can be installed independently:

- **openstef-core** — shared data types, interfaces, base classes, and exceptions.
  This is the foundation every other package builds on.
- **openstef-models** — forecasting models, preprocessing pipelines, feature
  engineering, explainability, and workflow orchestration.
- **openstef-meta** — advanced ensemble and meta-learning model architectures.
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (the BEAM
  acronym). Answers the question *"are my model changes statistically significant?"*

The design goal is an **unopinionated machine learning library**: V4 provides
composable building blocks and sensible presets, but does not force a single
deployment topology or data source on you. See :doc:`deployment` and
:doc:`data_integration` for patterns that build on top of these primitives.

----

Package Installation
--------------------

V3 required a single install:

.. code-block:: bash

   # Before (V3)
   pip install openstef

V4 requires installing the packages relevant to your use case:

.. code-block:: bash

   # After (V4) — typical forecasting setup
   pip install openstef-core openstef-models

   # Add evaluation and backtesting support
   pip install openstef-beam

   # Add advanced ensemble models
   pip install openstef-meta

If you previously depended on ``openstef-dbc`` (the database connector companion
package), that package is unchanged and continues to work alongside V4.

----

Breaking Changes at a Glance
-----------------------------

The table below summarises the most impactful breaking changes. Detailed before/after
examples follow in the next sections.

- **PredictionJobDataClass removed** — replaced by ``ForecastingModel`` +
  ``VersionedTimeSeriesDataset`` + ``CustomForecastingWorkflow``.
- **``train_model_pipeline`` / ``create_forecast_pipeline`` removed** — replaced by
  ``ForecastingModel.fit()`` / ``ForecastingModel.predict()``.
- **MLflow coupling loosened** — model storage is now an injectable
  ``LocalModelStorage`` or ``MLFlowStorageCallback``; you are no longer required to
  pass ``mlflow_tracking_uri`` strings directly to pipeline functions.
- **Import paths changed** — all stable public APIs now live under ``openstef_core``,
  ``openstef_models``, or ``openstef_beam``. The old ``openstef.*`` paths no longer
  exist.
- **Quantile specification** — quantiles are now expressed as ``Q(0.1)`` typed values
  from ``openstef_core.types`` rather than plain integers (``10``, ``50``, etc.).
- **Horizons** — horizons are now ``LeadTime`` objects (e.g.
  ``LeadTime.from_string("PT36H")``) rather than plain integer minutes.

----

Migrating the Prediction Job Definition
-----------------------------------------

In V3, a *prediction job* was a plain dictionary (or ``PredictionJobDataClass``
instance) that bundled model type, quantiles, horizon, and geographic metadata into a
single blob passed to every pipeline function.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = dict(
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
   pj = PredictionJobDataClass(**pj)

In V4, the concept of a "prediction job" is replaced by a ``ForecastingModel`` — a
composable pipeline object that owns its preprocessing, forecaster, and
postprocessing steps explicitly. You configure it once and call ``fit`` / ``predict``
on it directly.

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_core.mixins import TransformPipeline

   horizons = [LeadTime.from_string("PT36H")]
   quantiles = [Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9)]

   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=[]),   # add your transforms here
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
       postprocessing=TransformPipeline(transforms=[]),
   )

The key difference is that model type, quantiles, and horizons are now first-class
typed objects rather than strings and raw integers. This makes configuration errors
detectable at construction time rather than deep inside a pipeline call.

----

Migrating Training
------------------

V3 exposed a single ``train_model_pipeline`` function. You passed the prediction job,
a DataFrame, and MLflow paths; the function handled everything internally.

**Before (V3):**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline

   input_data = pd.read_csv("data/load_data.csv", index_col="index", parse_dates=True)
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
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage import LocalModelStorage

   # Wrap your DataFrame in a typed dataset
   dataset = VersionedTimeSeriesDataset(data=train_data)

   # Wire up storage (optional but recommended for production)
   storage = LocalModelStorage(path=Path("./models"))

   # Build the workflow — model defined as shown in the previous section
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="demand_forecast_287",
   )

   # Train
   fit_result = workflow.fit(dataset)

The ``fit_result`` is a typed ``ModelFitResult`` object rather than a tuple of
DataFrames, making it straightforward to inspect training metrics programmatically.

.. note::

   ``CustomForecastingWorkflow`` accepts a ``callbacks`` list for lifecycle hooks
   such as logging, MLflow tracking, and model selection. See the
   :doc:`deployment` page for production callback patterns.

----

Migrating Forecasting
---------------------

V3 used a separate ``create_forecast_pipeline`` function that reloaded the model from
MLflow on every call.

**Before (V3):**

.. code-block:: python

   import numpy as np
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   to_forecast_data = input_data.copy(deep=True)
   to_forecast_data.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   forecast_dataset = VersionedTimeSeriesDataset(data=to_forecast_data)

   # The workflow already holds the fitted model in memory
   forecasts: ForecastDataset = workflow.predict(forecast_dataset)

Because the workflow object owns the model, there is no implicit MLflow round-trip on
every prediction call. If you need to load a previously persisted model, use
``CustomForecastingWorkflow.from_storage()``:

.. code-block:: python

   workflow = CustomForecastingWorkflow.from_storage(
       model_id="demand_forecast_287",
       storage=storage,
   )
   forecasts = workflow.predict(forecast_dataset)

----

Migrating Feature Engineering
------------------------------

V3 performed feature engineering automatically inside the pipeline based on fields in
the prediction job (``feature_names``, ``hyper_params``, etc.). There was no
straightforward way to inspect or modify the feature steps.

V4 makes the preprocessing pipeline explicit. You compose a ``FeaturePipeline`` (or
plain ``TransformPipeline``) from individual transform objects:

.. code-block:: python

   from openstef_models.preprocessing.feature_pipeline import FeaturePipeline
   from openstef_models.preprocessing.transforms import (
       HolidayFeatures,
       LagTransform,
       StandardScaler,
   )
   from openstef_core.mixins import TransformPipeline

   preprocessing = FeaturePipeline(
       transforms=[
           HolidayFeatures(country="NL"),
           LagTransform(lags=[timedelta(days=1), timedelta(days=7)]),
           StandardScaler(),
       ]
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=ConstantMedianForecaster(horizons=horizons, quantiles=quantiles),
       postprocessing=TransformPipeline(transforms=[]),
   )

.. warning::

   When using lag-based transforms, set ``cutoff_history`` on ``ForecastingModel``
   to exclude the initial rows that contain NaN values introduced by the lag. For
   example, a 14-day lag requires ``cutoff_history=timedelta(days=14)``. This cannot
   be inferred automatically.

----

Migrating Model Storage
------------------------

V3 coupled model persistence tightly to MLflow: ``mlflow_tracking_uri`` was a
required argument to both ``train_model_pipeline`` and ``create_forecast_pipeline``.

V4 treats storage as an injectable dependency. ``LocalModelStorage`` stores models on
disk; ``MLFlowStorageCallback`` integrates MLflow as a workflow callback. You can also
implement the ``ModelStorage`` interface for custom backends (S3, Azure Blob, etc.) —
see :doc:`data_integration` for examples.

.. code-block:: python

   # Local file-based storage (development / testing)
   from openstef_models.storage import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(path=Path("./models"))

   # MLflow storage via callback (production)
   from openstef_models.callbacks import MLFlowStorageCallback

   mlflow_callback = MLFlowStorageCallback(
       storage=storage,
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
       model_selection_enable=True,
   )

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="demand_forecast_287",
       callbacks=[mlflow_callback],
   )

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate an existing V3 codebase:

1. **Update dependencies.** Replace ``openstef`` in your ``requirements.txt`` or
   ``pyproject.toml`` with ``openstef-core`` and ``openstef-models``. Add
   ``openstef-beam`` if you use evaluation or backtesting.

2. **Update imports.** Search your codebase for ``from openstef.`` and ``import
   openstef.`` — every such import needs to be updated to the new package names
   (``openstef_core``, ``openstef_models``, ``openstef_beam``).

3. **Replace PredictionJobDataClass.** Identify every place a prediction job dict or
   ``PredictionJobDataClass`` is constructed. Replace each one with a
   ``ForecastingModel`` configured with explicit preprocessing, forecaster, and
   postprocessing components.

4. **Replace quantile integers with Q() types.** Search for quantile lists like
   ``[10, 30, 50, 70, 90]`` and replace with ``[Q(0.1), Q(0.3), Q(0.5), Q(0.7),
   Q(0.9)]``.

5. **Replace horizon integers with LeadTime objects.** Replace
   ``horizon_minutes=2880`` style fields with
   ``LeadTime.from_string("PT48H")`` or ``LeadTime(timedelta(minutes=2880))``.

6. **Replace pipeline functions with workflow calls.** Replace
   ``train_model_pipeline(...)`` with ``workflow.fit(dataset)`` and
   ``create_forecast_pipeline(...)`` with ``workflow.predict(dataset)``.

7. **Migrate storage configuration.** Replace ``mlflow_tracking_uri`` string
   arguments with a ``LocalModelStorage`` or ``MLFlowStorageCallback`` instance.

8. **Wrap DataFrames in typed datasets.** Replace bare ``pd.DataFrame`` inputs with
   ``VersionedTimeSeriesDataset(data=df)`` or ``TimeSeriesDataset(data=df)`` as
   appropriate.

9. **Run your test suite.** V4 ships with ``openstef_core.testing`` utilities
   including ``create_synthetic_forecasting_dataset`` to help you write unit tests
   without real data.

----

Quick Reference: Import Path Changes
--------------------------------------

The table below covers the most commonly used V3 symbols and their V4 equivalents.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - V3 import
     - V4 import
   * - ``openstef.data_classes.prediction_job.PredictionJobDataClass``
     - ``openstef_models.models.forecasting_model.ForecastingModel``
   * - ``openstef.pipeline.train_model.train_model_pipeline``
     - ``CustomForecastingWorkflow.fit()`` (``openstef_models.workflows``)
   * - ``openstef.pipeline.create_forecast.create_forecast_pipeline``
     - ``CustomForecastingWorkflow.predict()`` (``openstef_models.workflows``)
   * - ``openstef.model.serializer`` (MLflow coupling)
     - ``openstef_models.storage.LocalModelStorage`` / ``MLFlowStorageCallback``
   * - ``openstef.feature_engineering.*``
     - ``openstef_models.preprocessing.*``
   * - Quantiles as integers (``10``, ``50``, ``90``)
     - ``openstef_core.types.Q(0.1)``, ``Q(0.5)``, ``Q(0.9)``
   * - ``horizon_minutes`` integer field
     - ``openstef_core.types.LeadTime.from_string("PT36H")``

----

Related Pages
--------------

- :doc:`use_cases` — end-to-end V4 examples for common forecasting scenarios such as
  congestion forecasting.
- :doc:`deployment` — production deployment patterns including callback configuration,
  model versioning, and scheduling.
- :doc:`data_integration` — connecting V4 to external data sources including S3,
  Databricks, and InfluxDB.