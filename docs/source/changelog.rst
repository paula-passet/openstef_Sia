Changelog
=========

This page records the version history of the OpenSTEF library, summarising new features, bug fixes,
and breaking changes for each release. Entries are listed in reverse chronological order so the most
recent changes are always at the top.

If you are upgrading between major versions, the changelog entries below describe *what* changed.
For step-by-step instructions on adapting your code, see the
:doc:`/user_guide/migration` page in the user guide.

----

Version 4.0 (current)
----------------------

OpenSTEF 4.0 is a major architectural release. The library has been restructured from a single
package into a **modular mono-repo** of focused, independently installable packages. The goals
driving this redesign were modularity, full type safety, extensibility without modifying core code,
and broader applicability beyond the Dutch energy sector. Users upgrading from 3.x should read the
:doc:`/user_guide/migration` guide before updating.

New packages
^^^^^^^^^^^^

The single ``openstef`` package is now a meta-package that installs four specialised libraries.
Each can also be installed on its own.

- **openstef-core** — shared data types, interfaces, base classes, and testing utilities.
  All other packages depend on this foundation.
- **openstef-models** — forecasting models, data preprocessing pipelines, energy-specific
  feature transforms, explainability helpers, and ready-to-use presets.
- **openstef-meta** — meta-learning and ensemble model architectures for advanced use cases.
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics (BEAM). Answers the
  question *"are my model changes statistically significant?"* through realistic walk-forward
  backtesting and probabilistic scoring.

Install everything at once:

.. code-block:: python

   # pip install openstef
   # or install individual packages:
   # pip install openstef-core openstef-models openstef-beam openstef-meta

New data model: ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ad-hoc ``pandas.DataFrame`` convention used in v3 has been replaced by two validated
dataset classes that live in ``openstef-core``.

``TimeSeriesDataset`` wraps a ``DataFrame`` with a ``DatetimeIndex`` and enforces a consistent
``sample_interval``. It exposes typed properties for horizons, feature names, and data
availability, and supports Parquet round-trips out of the box:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.DataFrame(
       {"load_mw": [100.0, 102.5, 98.3]},
       index=pd.date_range("2024-01-01", periods=3, freq="15min"),
   )
   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   print(dataset.feature_names)   # ['load_mw']
   print(dataset.sample_interval) # 0:15:00

   dataset.to_parquet("load.parquet")
   restored = TimeSeriesDataset.read_parquet("load.parquet")

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts into a unified
dataset that tracks *when* each measurement became available. This is essential for realistic
backtesting where measurements arrive with delays or are revised over time:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   weather = pd.DataFrame(
       {"temperature": [18.0, 19.5]},
       index=pd.DatetimeIndex([datetime(2024, 6, 1, 10), datetime(2024, 6, 1, 11)]),
   )
   weather["available_at"] = datetime(2024, 6, 1, 16, 0)

   weather_part = TimeSeriesDataset(weather, timedelta(hours=1))
   versioned = VersionedTimeSeriesDataset([weather_part])

   print(versioned.is_versioned)  # True

New backtesting pipeline (``openstef-beam``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A dedicated ``BacktestPipeline`` replaces the previous ad-hoc backtesting utilities. It runs a
walk-forward simulation that respects data availability constraints, so the evaluation mirrors
real production conditions:

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

   config = BacktestConfig(
       train_interval="P7D",
       predict_interval="PT1H",
       prediction_sample_interval="PT15M",
   )

   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)
   predictions = pipeline.run(
       ground_truth=versioned_ground_truth,
       predictors=versioned_predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
   )

New evaluation pipeline (``openstef-beam``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``EvaluationPipeline`` computes probabilistic metrics across multiple dimensions — prediction
availability times, lead times, and rolling windows — and always includes calibration via the
observed-probability metric:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_core.types import AvailableAt, LeadTime, Window
   from datetime import timedelta

   config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

   pipeline = EvaluationPipeline(
       config=config,
       quantiles=quantiles,
       window_metric_providers=window_providers,
       global_metric_providers=global_providers,
   )

New feature transforms (``openstef-models``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A ``VersionedLagsAdder`` transform creates lag features while honouring data availability
constraints, so lag values only use measurements that would have been observable at prediction
time:

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder

   lags = VersionedLagsAdder(lags=["PT1H", "PT2H", "P1D"])
   dataset_with_lags = lags.transform(versioned_dataset)

Type safety and configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All configuration objects now derive from ``BaseConfig`` (a Pydantic model defined in
``openstef-core``). This means configuration is validated at construction time and IDE
auto-complete works throughout:

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from pydantic import Field

   class MyForecasterConfig(BaseConfig):
       horizon_hours: int = Field(default=48, ge=1, le=168)
       quantiles: list[float] = Field(default=[0.1, 0.5, 0.9])

Python version requirement raised
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 requires **Python ≥ 3.12**. Python 3.10 and 3.11 are no longer supported.

Breaking changes in 4.0
^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

   Version 4.0 contains breaking changes throughout the public API. The items below are the
   most impactful. See :doc:`/user_guide/migration` for full migration instructions.

- **Package structure** — the single ``openstef`` package is now a meta-package. Direct imports
  from ``openstef.*`` no longer work; use ``openstef_core``, ``openstef_models``,
  ``openstef_beam``, or ``openstef_meta`` instead.
- **``PredictionJob`` removed** — the ``PredictionJob`` dataclass and the pipeline functions
  that accepted it (``train_model_pipeline``, ``create_forecast_pipeline``, etc.) have been
  removed. Forecasting is now expressed through the ``Forecaster`` interface and
  ``TimeSeriesDataset`` inputs.
- **DataFrame conventions replaced** — raw ``pandas.DataFrame`` inputs are no longer accepted
  by pipeline functions. Wrap your data in ``TimeSeriesDataset`` or
  ``VersionedTimeSeriesDataset`` before passing it to any pipeline.
- **MLflow and openstef-dbc decoupled** — these integrations are no longer bundled. If you
  relied on the built-in MLflow experiment tracking, you must wire it up yourself using the
  callback hooks provided in ``openstef-models``.
- **Holiday calendar** — the hard-coded Dutch holiday calendar has been replaced by a
  configurable calendar. If you relied on the default, pass an explicit calendar object to
  your preprocessing pipeline.
- **Minimum Python version** — Python 3.10 and 3.11 are no longer supported.

----

Version 3.x
------------

.. note::

   Version 3.x is no longer actively maintained. Critical security fixes may still be
   backported on a best-effort basis. Users are encouraged to migrate to 4.0.

Version 3.4 (final 3.x release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added quantile regression support to the XGBoost model preset.
- Improved data cleaning heuristics for outlier removal in the preprocessing step.
- Fixed an issue where the feature importance plot could fail when all importances were zero.
- Dependency pins relaxed: ``scikit-learn >=1.2``, ``xgboost >=1.7``.

Version 3.3
^^^^^^^^^^^^

- Introduced experimental support for probabilistic forecasts (prediction intervals) via
  conformal prediction wrappers.
- Added ``rMAE`` and ``rCRPS`` as built-in evaluation metrics.
- Fixed a timezone-handling bug that caused incorrect lag features near DST transitions.
- ``create_forecast_pipeline`` now raises ``ValueError`` instead of returning ``None`` when
  the input data is insufficient.

Version 3.2
^^^^^^^^^^^^

- Solar and wind component models added as optional split-component forecasters.
- Improved MLflow integration: model artefacts are now logged with a consistent schema.
- Fixed a memory leak in the rolling-window cross-validation helper.
- Dropped support for Python 3.9.

Version 3.1
^^^^^^^^^^^^

- ``train_model_pipeline`` gained an ``early_stopping_rounds`` parameter for gradient-boosted
  models.
- Added a ``backtest_pipeline`` helper function for simple walk-forward evaluation.
- Performance: feature engineering is now vectorised, reducing training time by roughly 30 %
  on large datasets.
- Fixed incorrect handling of ``NaN`` values in the target column during validation.

Version 3.0
^^^^^^^^^^^^

- Major release introducing the ``PredictionJob`` abstraction as the central configuration
  object for all pipeline functions.
- Unified ``train_model_pipeline`` and ``create_forecast_pipeline`` entry points.
- Added built-in support for XGBoost, LightGBM, and linear regression model types.
- Introduced the ``openstef-dbc`` connector for database-backed workflows.
- Dropped Python 3.8 support.

----

Version 2.x
------------

Version 2.x established the pipeline-based API and the ``PredictionJob`` concept that carried
forward into 3.x. It is no longer supported.

Notable milestones:

- **2.5** — Added lag feature generation and holiday-calendar features.
- **2.3** — Introduced MLflow experiment tracking integration.
- **2.0** — Refactored from a monolithic script collection into an installable Python library.

----

Versioning policy
-----------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_:

- **Major** versions (e.g. 3 → 4) may contain breaking API changes.
- **Minor** versions add functionality in a backwards-compatible manner.
- **Patch** versions contain backwards-compatible bug fixes only.

Pre-release versions are published to PyPI with a ``dev`` suffix (e.g. ``4.0.0.dev1``) and
should not be used in production.

To pin to a compatible minor release in your project:

.. code-block:: python

   # requirements.txt
   openstef>=4.0,<5

----

.. note::

   For detailed, step-by-step instructions on upgrading from OpenSTEF 3.x to 4.0, including
   code-level before/after examples, see :doc:`/user_guide/migration`.