Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant architectural evolution of the library. It moves from a
single monolithic package to a modular mono-repo of focused sub-packages, and replaces
the ``PredictionJobDataClass``-centric API with a composable, type-safe pipeline built
around ``ForecastingModel``, ``CustomForecastingWorkflow``, and structured dataset
classes. This page covers every breaking change you are likely to encounter and walks
you through updating your code step by step.

.. note::

   This guide assumes you are migrating Python code that calls OpenSTEF as a library.
   If you are looking for deployment patterns or data-integration recipes, see
   :doc:`deployment` and :doc:`data_integration` respectively.

.. contents:: On this page
   :local:
   :depth: 2

---

What Changed and Why
--------------------

V3 shipped as a single ``openstef`` package. Everything — data classes, pipelines,
models, feature engineering — lived under one namespace, and the central abstraction
was the ``PredictionJobDataClass`` dictionary-like object that was threaded through
every pipeline call.

V4 restructures the library into a **modular mono-repo** of self-contained packages:

- **openstef-core** — data types, interfaces, base classes, shared exceptions, and
  testing utilities. This is the foundation every other package builds on.
- **openstef-models** — forecasting models, preprocessing pipelines, energy-specific
  transforms, explainability features, and workflow presets.
- **openstef-meta** — ensemble and advanced model architectures (meta-learning).
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM).

The goals of this restructuring are:

- **Unopinionated design** — the library no longer assumes a single deployment pattern.
- **Composability** — preprocessing, models, and storage are independent objects you
  wire together yourself.
- **Type safety** — Pydantic-backed configuration objects replace plain dictionaries.
- **Data availability awareness** — versioned datasets encode what data would have been
  available at prediction time, preventing look-ahead leakage.

---

Package Structure Changes
--------------------------

The table below maps the most common V3 import paths to their V4 equivalents.

+------------------------------------------------------+------------------------------------------------------+
| V3 import                                            | V4 import                                            |
+======================================================+======================================================+
| ``openstef.data_classes.prediction_job``             | ``openstef_core.datasets`` /                         |
|                                                      | ``openstef_models.presets``                          |
+------------------------------------------------------+------------------------------------------------------+
| ``openstef.pipeline.train_model``                    | ``openstef_models.workflows``                        |
+------------------------------------------------------+------------------------------------------------------+
| ``openstef.pipeline.create_forecast``                | ``openstef_models.workflows``                        |
+------------------------------------------------------+------------------------------------------------------+
| ``openstef.model.*``                                 | ``openstef_models.models.*``                         |
+------------------------------------------------------+------------------------------------------------------+
| ``openstef.feature_engineering.*``                   | ``openstef_models.transforms.*``                     |
+------------------------------------------------------+------------------------------------------------------+

Install the new packages with:

.. code-block:: python

   # pip install openstef-core openstef-models openstef-beam

---

.. _breaking-change-1:

Breaking Change 1: PredictionJob Replaced by Structured Configuration
----------------------------------------------------------------------

In V3, a prediction job was a plain dictionary validated by ``PredictionJobDataClass``.
It was passed as the first argument to every pipeline function.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd

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

   input_data = pd.read_csv("data/load.csv", index_col="index", parse_dates=True)
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

   from datetime import timedelta
   from pathlib import Path

   import pandas as pd
   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.transforms.feature_pipeline import FeaturePipeline
   from openstef_models.transforms.time_domain.holiday_features_adder import (
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.storage.local_model_storage import LocalModelStorage
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   horizons = [LeadTime(timedelta(hours=h)) for h in [1, 24, 48]]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       preprocessing=FeaturePipeline(
           transforms=[
               HolidayFeatureAdder(country=CountryAlpha2("NL")),
               LagsAdder(horizons=horizons),
           ]
       ),
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
   )

   storage = LocalModelStorage(base_path=Path("./models"))
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="example_model",
       storage=storage,
   )

   raw_df = pd.read_csv("data/load.csv", index_col="index", parse_dates=True)
   dataset = TimeSeriesDataset(data=raw_df, target_column="load")

   result = workflow.fit(dataset)

The key conceptual shift is that configuration is no longer a dictionary of magic
strings. Each concern — feature engineering, the forecaster, storage — is its own
typed object. This makes it straightforward to swap out any single component without
touching the rest.

---

Breaking Change 2: Unified Workflow Replaces Separate Train/Forecast Pipelines
-------------------------------------------------------------------------------

V3 exposed two separate top-level functions: ``train_model_pipeline`` and
``create_forecast_pipeline``. In V4 both operations live on the same
``CustomForecastingWorkflow`` object, which also manages model persistence.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import numpy as np

   # Training
   train_model_pipeline(
       pj, train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

   # Forecasting — must reload model from MLflow implicitly
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan
   forecast = create_forecast_pipeline(
       pj, to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   # Training — workflow holds the fitted model in memory and optionally persists it
   result = workflow.fit(train_dataset)

   # Forecasting — same workflow object, no implicit MLflow lookup
   forecast_dataset = workflow.predict(forecast_dataset)

   # Access quantile predictions directly
   print(forecast_dataset.data[["quantile_P10", "quantile_P50", "quantile_P90"]])

Because the workflow object owns the model, there is no implicit MLflow round-trip
between training and prediction. If you need to reload a previously saved model, use
``CustomForecastingWorkflow.from_storage``:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(base_path=Path("./models"))
   workflow = CustomForecastingWorkflow.from_storage(
       model_id="example_model",
       storage=storage,
   )

---

Breaking Change 3: Dataset Classes Replace Raw DataFrames
----------------------------------------------------------

V3 pipelines accepted plain ``pd.DataFrame`` objects. V4 wraps DataFrames in typed
dataset classes that carry metadata about the target column, data availability, and
versioning.

+-------------------------------+-----------------------------------------------+
| V3 pattern                    | V4 equivalent                                 |
+===============================+===============================================+
| ``pd.DataFrame``              | ``TimeSeriesDataset``                         |
+-------------------------------+-----------------------------------------------+
| ``pd.DataFrame`` (with NaNs   | ``VersionedTimeSeriesDataset``                |
| for future load)              |                                               |
+-------------------------------+-----------------------------------------------+
| Return value of forecast      | ``ForecastDataset``                           |
| pipeline                      |                                               |
+-------------------------------+-----------------------------------------------+

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   from openstef_core.datasets.versioned_timeseries_dataset import (
       VersionedTimeSeriesDataset,
   )

   # Wrap your existing DataFrame
   dataset = TimeSeriesDataset(data=df, target_column="load")

   # For production use where data availability matters
   versioned = VersionedTimeSeriesDataset(data=df, target_column="load")

.. note::

   ``VersionedTimeSeriesDataset`` is the preferred type for production workflows. It
   ensures that lag features and other time-dependent transforms only use data that
   would have been available at the time of prediction, preventing look-ahead leakage.

---

Breaking Change 4: Feature Engineering is Explicit
---------------------------------------------------

In V3, feature engineering (lag creation, holiday flags, weather-derived features) was
applied automatically inside the pipeline based on the prediction job's ``lat``,
``lon``, and ``feature_names`` fields. In V4 you compose a ``FeaturePipeline``
explicitly.

**Before (V3):** feature engineering was implicit — controlled by ``feature_names``
and coordinates in the prediction job dict.

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.types import LeadTime
   from openstef_models.transforms.feature_pipeline import FeaturePipeline
   from openstef_models.transforms.time_domain.holiday_features_adder import (
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   horizons = [LeadTime(timedelta(hours=h)) for h in [1, 24, 48]]

   preprocessing = FeaturePipeline(
       transforms=[
           HolidayFeatureAdder(country=CountryAlpha2("NL")),
           LagsAdder(horizons=horizons),
       ]
   )

This explicitness is intentional: you can add, remove, or reorder transforms without
touching model code, and each transform is independently testable.

.. warning::

   When using ``LagsAdder``, set ``cutoff_history`` on your ``ForecastingModel`` to
   exclude the initial rows where lag features are ``NaN``. For example, a 14-day lag
   requires ``cutoff_history=timedelta(days=14)``. This cannot be inferred
   automatically.

---

Breaking Change 5: Quantile Specification
------------------------------------------

V3 accepted quantiles as plain integers (e.g. ``[10, 30, 50, 70, 90]``). V4 uses the
``Q`` type from ``openstef_core.types``, which wraps a float in the range ``[0, 1]``.

**Before (V3):**

.. code-block:: python

   pj = PredictionJobDataClass(**{"quantiles": [10, 30, 50, 70, 90], ...})

**After (V4):**

.. code-block:: python

   from openstef_core.types import Q

   quantiles = [Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9)]

Output columns in ``ForecastDataset`` are named accordingly:
``quantile_P10``, ``quantile_P50``, ``quantile_P90``, and so on.

---

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order when migrating an existing V3 codebase.

**Step 1 — Install the new packages**

.. code-block:: python

   # pip install openstef-core openstef-models openstef-beam

Remove ``openstef`` (the V3 package) from your requirements file and replace it with
the sub-packages you actually need.

**Step 2 — Update imports**

Search your codebase for ``from openstef.`` and ``import openstef.`` and update each
import using the mapping table in the `Package Structure Changes`_ section above.

**Step 3 — Replace PredictionJobDataClass with typed configuration**

Identify every place you construct a ``PredictionJobDataClass`` dict and replace it
with the appropriate V4 objects: a ``ForecastingModel`` (or a preset from
``openstef_models.presets``), a ``FeaturePipeline``, and a storage backend.

**Step 4 — Wrap DataFrames in dataset classes**

Find every ``pd.DataFrame`` passed to a pipeline function and wrap it in
``TimeSeriesDataset`` or ``VersionedTimeSeriesDataset``. Set ``target_column`` to the
name of your load column.

**Step 5 — Replace pipeline calls with workflow methods**

Replace calls to ``train_model_pipeline(...)`` with ``workflow.fit(dataset)`` and
calls to ``create_forecast_pipeline(...)`` with ``workflow.predict(dataset)``.

**Step 6 — Update quantile references**

Replace integer quantile lists with ``Q(...)`` values and update any downstream code
that reads quantile columns by name (e.g. rename ``"quantile_50"`` references to
``"quantile_P50"``).

**Step 7 — Run your test suite**

V4 ships testing utilities in ``openstef_core.testing``, including
``create_synthetic_forecasting_dataset`` for generating realistic synthetic data in
unit tests. Use these to validate your migrated pipelines before running against
production data.

.. code-block:: python

   from openstef_core.testing import create_synthetic_forecasting_dataset

   dataset = create_synthetic_forecasting_dataset()
   result = workflow.fit(dataset)
   assert result is not None

---

Using Presets for a Faster Migration
--------------------------------------

If you want to migrate quickly without rebuilding your pipeline from scratch, the
``openstef_models.presets`` module provides pre-configured workflows for common
forecasting scenarios. A preset bundles a ``FeaturePipeline``, a forecaster, and
sensible defaults into a single ``CustomForecastingWorkflow`` you can use immediately.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage
   from pathlib import Path

   config = ForecastingWorkflowConfig(
       location=LocationConfig(name="Location_A", lat=52.0, lon=5.0),
       model_id="location_a_demand",
       storage=LocalModelStorage(base_path=Path("./models")),
   )

   workflow = create_forecasting_workflow(config)

Presets are a good starting point. Once you need to customise feature engineering or
swap the underlying forecaster, move to the explicit ``ForecastingModel`` construction
shown in the :ref:`breaking-change-1` section above.

---

Summary of Breaking Changes
-----------------------------

- ``openstef`` single package → ``openstef-core``, ``openstef-models``, ``openstef-beam``
- ``PredictionJobDataClass`` dict → typed ``ForecastingModel`` + ``FeaturePipeline`` + storage
- ``train_model_pipeline()`` / ``create_forecast_pipeline()`` → ``workflow.fit()`` / ``workflow.predict()``
- Raw ``pd.DataFrame`` inputs → ``TimeSeriesDataset`` / ``VersionedTimeSeriesDataset``
- Integer quantiles ``[10, 50, 90]`` → ``Q`` type ``[Q(0.1), Q(0.5), Q(0.9)]``
- Implicit feature engineering → explicit ``FeaturePipeline`` with named transforms
- MLflow-coupled model storage → pluggable storage backends (``LocalModelStorage``, or custom)

---

Further Reading
----------------

- :doc:`use_cases` — end-to-end examples using the V4 API for congestion forecasting
  and other common scenarios.
- :doc:`deployment` — production deployment patterns including model storage strategies
  and scheduling.
- :doc:`data_integration` — connecting OpenSTEF to S3, Databricks, and InfluxDB data
  sources using V4 dataset classes.