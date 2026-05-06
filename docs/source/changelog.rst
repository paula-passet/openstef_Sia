Changelog
=========

This page records the version history of OpenSTEF, summarising new features, bug fixes, and breaking changes for each release. Entries are listed in reverse chronological order — most recent first.

For step-by-step instructions on upgrading between major versions, see the :doc:`/user_guide/migration` guide.

----

Version 4.0 (Current)
----------------------

OpenSTEF 4.0 is a major architectural release. The library has been restructured from a single package into a **modular mono-repo** of self-contained, independently installable packages. This redesign improves composability, reduces unnecessary dependencies, and makes it easier to integrate OpenSTEF into existing software landscapes.

New packages
^^^^^^^^^^^^

The single ``openstef`` package is now a meta-package that installs four focused sub-packages:

- **openstef-core** — data types, base classes, shared exceptions, and testing utilities. All other packages depend on this foundation.
- **openstef-models** — forecasting models, data preprocessing pipelines, energy-specific transforms, explainability features, and presets for common use cases.
- **openstef-meta** — meta-learning and ensemble model architectures built on top of ``openstef-models``.
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Answers the question *"are my model changes statistically significant?"* with regression testing against benchmarks.

Install everything at once:

.. code-block:: bash

   pip install openstef

Or install only what you need:

.. code-block:: bash

   # Core data structures only
   pip install openstef-core

   # Models and transforms
   pip install openstef-models

   # Evaluation and backtesting
   pip install openstef-beam[baselines]

New features
^^^^^^^^^^^^

**Versioned time series datasets**

A new ``VersionedTimeSeriesDataset`` class in ``openstef-core`` tracks *when* each measurement became available, not just its timestamp. This enables point-in-time reconstruction of the data that would have been visible at any past moment — essential for realistic backtesting when measurements arrive with delays or are revised after the fact.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # A weather observation that became available 6 hours after measurement
   weather_data = pd.DataFrame(
       {"temperature": [20.5], "available_at": [datetime(2025, 1, 1, 16, 0)]},
       index=pd.DatetimeIndex([datetime(2025, 1, 1, 10, 0)]),
   )
   weather_part = TimeSeriesDataset(weather_data, timedelta(hours=1))

   # Combine parts into a versioned dataset
   dataset = VersionedTimeSeriesDataset([weather_part])
   assert dataset.is_versioned

**Versioned lag features**

``VersionedLagsAdder`` in ``openstef-models`` creates lag features that respect data availability constraints. Unlike a naive lag transform, it guarantees that each lag value uses only data that would have been available at prediction time.

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder

   lags_transform = VersionedLagsAdder(
       column="load",
       lags=[timedelta(hours=1), timedelta(hours=24), timedelta(days=7)],
   )

**YAML-based configuration**

All configuration objects now extend ``BaseConfig``, which supports reading from and writing to YAML files. This makes pipeline configuration reproducible and version-controllable without custom serialisation code.

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from pathlib import Path

   class MyPipelineConfig(BaseConfig):
       horizon_hours: int = 48
       sample_interval_minutes: int = 15

   config = MyPipelineConfig(horizon_hours=24)
   config.write_yaml(Path("pipeline_config.yaml"))

   # Later, restore from file
   loaded = MyPipelineConfig.read_yaml(Path("pipeline_config.yaml"))

**Serialisation versioning**

Model and transform objects now carry a ``_VERSION`` integer. When a saved object is loaded from a checkpoint, the library automatically calls ``_migrate_state()`` to upgrade the stored state to the current schema. A ``UserWarning`` is raised if forward compatibility cannot be guaranteed.

**Validated domain datasets**

``openstef-core`` ships typed dataset wrappers — ``ForecastInputDataset``, ``ForecastDataset``, ``EnergyComponentDataset``, and ``EnsembleForecastDataset`` — that enforce domain-specific column and dtype constraints at construction time, catching data issues before they reach the model.

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset, ForecastDataset

**Decoupled external dependencies**

MLflow, XGBoost, and LightGBM are now optional extras rather than hard dependencies. Install only the backends you need:

.. code-block:: bash

   # LightGBM backend
   pip install openstef-models[lgbm]

   # XGBoost on CPU
   pip install openstef-models[xgb-cpu]

   # XGBoost with GPU support
   pip install openstef-models[xgb-gpu]

**Generalised domain support**

Hard-coded assumptions tied to the Netherlands (holiday calendars, grid topology conventions) have been removed or made configurable. OpenSTEF 4.0 is designed to support energy forecasting use cases beyond a single operator or country.

**Python version requirement**

OpenSTEF 4.0 requires **Python ≥ 3.12**. Support for Python 3.10 and 3.11 has been dropped.

Breaking changes
^^^^^^^^^^^^^^^^

4.0 is a major release with breaking changes throughout. The highlights are:

- **Package restructure.** All imports have changed. ``openstef.*`` imports from version 3 no longer exist; use ``openstef_core.*``, ``openstef_models.*``, ``openstef_beam.*``, or ``openstef_meta.*`` instead.
- **Python ≥ 3.12 required.** Older Python versions are not supported.
- **MLflow is optional.** Code that assumed MLflow was always present will need to guard the import or install ``openstef-models`` (which includes ``mlflow-skinny``).
- **Removed hard-coded presets.** Several V3 pipeline presets with fixed feature sets and model hyperparameters have been replaced by a more flexible preset system. Existing pipeline configurations may need updating.
- **Input data constraints relaxed.** The strict column naming and dtype requirements from V3 have been replaced by validated dataset types. Code that relied on implicit column conventions should be updated to use the new typed wrappers.

.. note::

   See the :doc:`/user_guide/migration` guide for a complete list of changed import paths and a worked example of porting a V3 pipeline to V4.

----

Version 3.x
------------

Version 3 established OpenSTEF as a production-grade forecasting library, running at Alliander with over 10,000 forecasts generated daily. The 3.x series focused on stabilising the core forecasting pipeline, adding explainability features, and improving test coverage.

Key highlights from the 3.x series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **XGBoost and LightGBM models** as primary gradient-boosting backends.
- **MLflow integration** for experiment tracking and model registry.
- **Feature engineering pipeline** with lag features, calendar features, and weather-derived inputs.
- **Quantile forecasting** for probabilistic predictions alongside point forecasts.
- **openstef-dbc** connector for database-backed prediction jobs.
- **Holiday calendar** support (initially Netherlands-specific).
- **SHAP-based explainability** for feature importance and individual prediction explanations.

.. note::

   The 3.x series is in maintenance mode. Bug fixes may be backported for critical issues, but new features are developed exclusively in 4.0.

----

Version 2.x
------------

Version 2 introduced the ``PredictionJob`` abstraction as the central configuration object for a forecasting task, and established the pipeline pattern that carried forward into V3. The 2.x series also added the first automated retraining workflows and initial support for solar and wind component forecasting.

----

Version 1.x
------------

The initial open-source release of OpenSTEF (then called *openstf*). Version 1 extracted the core forecasting logic from Alliander's internal tooling and published it under the Mozilla Public License 2.0. It provided a working XGBoost-based load forecasting pipeline with basic feature engineering and a command-line entry point.

----

Release cadence and support policy
-----------------------------------

OpenSTEF follows **semantic versioning** (``MAJOR.MINOR.PATCH``):

- **MAJOR** — breaking API changes. A migration guide is published alongside the release.
- **MINOR** — new backwards-compatible features.
- **PATCH** — bug fixes and security updates.

The current stable major version (4.x) receives active feature development and bug fixes. The previous major version (3.x) receives critical bug fixes only. Older versions are unsupported.

Pre-release versions (``dev``, ``alpha``, ``beta``, ``rc``) are published to PyPI and are suitable for testing but not for production use. Forward compatibility is not guaranteed between pre-release builds.

.. note::

   To pin to a specific release in your project, use an exact version specifier:

   .. code-block:: bash

      pip install "openstef==4.0.0"

   Or constrain to a compatible minor series:

   .. code-block:: bash

      pip install "openstef>=4.0,<5"