Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant architectural overhaul of the library. The monolithic
``openstef`` package has been split into focused sub-packages, the ``PredictionJob``
dictionary-driven API has been replaced with typed model classes, and the high-level
pipeline functions have given way to composable, object-oriented workflows. This page
walks through every breaking change and shows you exactly what to update.

.. note::

   This guide covers code-level migration. For deployment patterns after upgrading,
   see :doc:`deployment`. For connecting new data sources to V4 pipelines, see
   :doc:`data_integration`.

What Changed and Why
--------------------

V3 centred on a single ``openstef`` package where a ``PredictionJobDataClass`` dict
described every aspect of a job, and top-level functions such as
``train_model_pipeline`` and ``create_forecast_pipeline`` executed the full workflow in
one call. This made quick experiments easy but made it hard to customise individual
steps, swap model backends, or test components in isolation.

V4 decomposes the library into three co-installable packages:

- **openstef-core** – shared data structures, base classes, and interfaces
  (``openstef_core``)
- **openstef-models** – concrete forecasting models, preprocessing, and the
  ``ForecastingModel`` pipeline class (``openstef_models``)
- **openstef-beam** – optional Apache Beam runners for large-scale backtesting and
  batch inference (``openstef_beam``)

The result is a scikit-learn-style ``fit`` / ``predict`` API built around typed
datasets (``TimeSeriesDataset``) instead of raw ``pandas.DataFrame`` objects passed
through loosely-typed dictionaries.

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_1.mmd

Package Installation
--------------------

Before (V3):
^^^^^^^^^^^^

.. code-block:: python

   # Single package covered everything
   pip install openstef

After (V4):
^^^^^^^^^^^

.. code-block:: python

   # Install the packages you actually need
   pip install openstef-core            # always required
   pip install openstef-models          # models and forecasting pipelines
   pip install openstef-beam            # optional: large-scale / Beam runners

Import paths change accordingly. Any ``from openstef.*`` import will need to be
updated to ``from openstef_core.*`` or ``from openstef_models.*`` depending on what
you are importing.

Defining a Forecasting Job
--------------------------

The ``PredictionJobDataClass`` dictionary is gone. V4 replaces it with a typed
``ForecastingModel`` that is configured through explicit constructor arguments and
``BaseConfig`` subclasses.

Before (V3):
^^^^^^^^^^^^

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   import pandas as pd

   # Job defined as a plain dict, then cast to a dataclass
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

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   train_data = input_data.iloc[:-200, :]

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

After (V4):
^^^^^^^^^^^

.. code-block:: python

   from openstef_models.models.forecasting.model import ForecastingModel
   from openstef_core.datasets.time_series import TimeSeriesDataset
   import pandas as pd

   # Load your data into the typed dataset wrapper
   raw = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   dataset = TimeSeriesDataset(data=raw, sample_interval=pd.Timedelta(minutes=15))

   # Split into train / validation / test
   train_data = dataset.slice(end=-200)
   val_data   = dataset.slice(start=-200, end=-48)
   test_data  = dataset.slice(start=-48)

   # Construct the model directly – no PredictionJob dict required
   model = ForecastingModel(
       forecaster="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       max_horizon="PT47H",
   )

   result = model.fit(data=train_data, data_val=val_data, data_test=test_data)

Key differences:

- Quantiles are expressed as floats (``0.10``) rather than integers (``10``).
- Horizons use ISO 8601 duration strings (``"PT47H"``) instead of ``horizon_minutes``.
- ``TimeSeriesDataset`` carries the sample interval, removing the need for
  ``resolution_minutes`` on the job.
- ``fit()`` returns a ``ModelFitResult`` object with training metrics; there is no
  separate MLflow call required at the call site.

Making a Forecast
-----------------

Before (V3):
^^^^^^^^^^^^

.. code-block:: python

   import numpy as np
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Mask the load column for the forecast window
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

After (V4):
^^^^^^^^^^^

.. code-block:: python

   from openstef_core.datasets.time_series import TimeSeriesDataset

   # Prepare a dataset that covers the forecast window
   forecast_input = TimeSeriesDataset(
       data=raw_forecast_window,
       sample_interval=pd.Timedelta(minutes=15),
   )

   forecast = model.predict(data=forecast_input)
   # forecast is a ForecastDataset with quantile columns (quantile_P10, etc.)

The ``create_forecast_pipeline`` function no longer exists. The model object itself
holds the trained state and exposes ``predict()``. You no longer need to pass an
MLflow tracking URI at prediction time because the model is already in memory.

.. note::

   If you relied on automatic MLflow model loading inside ``create_forecast_pipeline``,
   you now handle serialisation explicitly. Use ``model.save()`` / ``ForecastingModel.load()``
   or integrate with your own model registry. See :doc:`deployment` for production
   patterns.

Evaluating and Scoring
-----------------------

Before (V3):
^^^^^^^^^^^^

V3 had no standardised scoring interface on the model object. Metrics were computed
inside the pipeline and written to MLflow artefacts, or calculated manually from the
returned DataFrames.

After (V4):
^^^^^^^^^^^

.. code-block:: python

   # score() returns a SubsetMetric with standard energy-forecasting metrics
   metrics = model.score(data=test_data)
   print(metrics)

The ``score()`` method is part of the ``BaseForecastingModel`` interface, so it works
identically across all model types (single forecaster, ensemble, etc.).

Feature Contributions (Explainability)
---------------------------------------

Before (V3):
^^^^^^^^^^^^

.. code-block:: python

   # Contributions were accessed via a separate utility, not the model object
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   # ... manual SHAP calls or report artefacts from train_model_pipeline

After (V4):
^^^^^^^^^^^

.. code-block:: python

   contributions = model.predict_contributions(data=forecast_input)
   # Returns a TimeSeriesDataset with one column per feature

Models that do not support contributions raise ``NotImplementedError`` with a clear
message. You can check support at runtime:

.. code-block:: python

   from openstef_models.models.forecasting.model import ForecastingModel
   from openstef_core.mixins.predictor import Predictor

   # get_explainable_components() returns a dict of named explainable sub-models
   components = model.get_explainable_components()

Backtesting
-----------

V3 did not ship a first-class backtesting pipeline. V4 introduces
``BacktestPipeline`` in ``openstef-beam`` (or its non-Beam equivalent in
``openstef-models``) built around ``VersionedTimeSeriesDataset``.

.. code-block:: python

   from openstef_models.backtesting.pipeline import BacktestPipeline
   from openstef_models.backtesting.config import BacktestConfig
   from openstef_core.datasets.versioned_time_series import VersionedTimeSeriesDataset

   config = BacktestConfig(
       available_ats=["D-1T06:00"],
       lead_times=["PT36H"],
   )

   dataset = VersionedTimeSeriesDataset(
       data=raw,
       sample_interval=pd.Timedelta(minutes=15),
   )

   pipeline = BacktestPipeline(forecaster=model, config=config)
   results = pipeline.run(dataset=dataset)
   # results is a TimeSeriesDataset of all out-of-sample predictions

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_2.mmd

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order to migrate an existing V3 codebase:

1. **Update dependencies.** Replace ``openstef`` in your ``requirements.txt`` or
   ``pyproject.toml`` with ``openstef-core`` and ``openstef-models``. Add
   ``openstef-beam`` only if you use distributed backtesting.

2. **Find all ``PredictionJobDataClass`` usages.** Each one becomes a
   ``ForecastingModel`` constructor call. Map the old dict keys using the table below.

3. **Replace pipeline function calls.** Swap ``train_model_pipeline`` →
   ``model.fit()``, ``create_forecast_pipeline`` → ``model.predict()``.

4. **Wrap DataFrames in ``TimeSeriesDataset``.** Every place you pass a raw
   ``pd.DataFrame`` to a pipeline function, wrap it first. The only required extra
   argument is ``sample_interval``.

5. **Update quantile notation.** Change integer percentiles (``10``, ``90``) to
   float fractions (``0.10``, ``0.90``).

6. **Update horizon notation.** Change ``horizon_minutes=2820`` to
   ``max_horizon="PT47H"`` (ISO 8601 duration).

7. **Replace MLflow artefact paths.** V4 does not write artefacts automatically.
   Serialise models explicitly and integrate with your registry. See :doc:`deployment`.

8. **Run your test suite.** The ``score()`` method gives you a quick sanity check
   that the retrained model produces comparable metrics.

Key Parameter Mapping
---------------------

+----------------------------------+------------------------------------------+
| V3 ``PredictionJobDataClass``    | V4 ``ForecastingModel`` argument         |
+==================================+==========================================+
| ``model="xgb"``                  | ``forecaster="xgb"``                     |
+----------------------------------+------------------------------------------+
| ``quantiles=[10, 50, 90]``       | ``quantiles=[0.10, 0.50, 0.90]``         |
+----------------------------------+------------------------------------------+
| ``horizon_minutes=2820``         | ``max_horizon="PT47H"``                  |
+----------------------------------+------------------------------------------+
| ``resolution_minutes=15``        | ``TimeSeriesDataset(sample_interval=…)`` |
+----------------------------------+------------------------------------------+
| ``hyper_params={}``              | ``hyperparams=HyperParams(…)``           |
+----------------------------------+------------------------------------------+
| ``lat=52.0, lon=5.0``            | Passed to preprocessing transform config |
+----------------------------------+------------------------------------------+
| ``mlflow_tracking_uri``          | Handled externally; see :doc:`deployment`|
+----------------------------------+------------------------------------------+

.. note::

   ``forecast_type``, ``id``, and ``name`` from the V3 prediction job have no direct
   V4 equivalents on the model object. Use your own metadata layer (e.g., a config
   file or database record) to track these identifiers.

Common Errors After Migration
------------------------------

``ImportError: cannot import name 'PredictionJobDataClass' from 'openstef'``
   The ``openstef`` package no longer exists. Install ``openstef-core`` and update
   the import to ``from openstef_core.data_classes.prediction_job import …`` — or,
   preferably, migrate fully to ``ForecastingModel`` as described above.

``TypeError: fit() got an unexpected keyword argument 'check_old_model_age'``
   This V3 argument is not present in V4. Model age checks are now your
   responsibility; compare ``model.is_fitted`` and your own versioning metadata.

``ValueError: quantile 10 out of range [0, 1]``
   Quantiles must be floats in ``[0, 1]``. Change ``10`` → ``0.10``, ``90`` → ``0.90``.

``AttributeError: 'DataFrame' object has no attribute 'sample_interval'``
   You passed a raw ``pd.DataFrame`` where a ``TimeSeriesDataset`` is expected. Wrap
   it: ``TimeSeriesDataset(data=df, sample_interval=pd.Timedelta(minutes=15))``.