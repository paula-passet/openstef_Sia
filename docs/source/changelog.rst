Changelog
=========

This page records what changed in each release of OpenSTEF — new features, bug fixes, and breaking changes. Where a release requires changes to existing code, a summary is provided here and detailed migration steps are covered in the :doc:`/user_guide/migration` guide.

Releases are listed in reverse-chronological order (newest first).

----

Version 4.0
-----------

*Status: Alpha — in production at Alliander, stable release in progress.*

OpenSTEF 4.0 is a major architectural redesign. The library has been restructured from a single package into a **modular mono-repo** of focused, independently installable packages. The goals driving this release were improved modularity, full type safety, decoupled external dependencies, and broader applicability beyond the original Alliander/Netherlands context.

New packages
^^^^^^^^^^^^

The single ``openstef`` package is now a meta-package that installs four focused sub-packages. Each can also be installed individually.

.. code-block:: bash

   # Install everything
   pip install openstef

   # Or install only what you need
   pip install openstef-core
   pip install openstef-models
   pip install openstef-beam
   pip install openstef-meta

The four packages and their responsibilities:

- **openstef-core** — Data types, base classes, shared exceptions, and testing utilities. The foundation all other packages build on. Provides ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and the ``BaseConfig`` / ``BaseModel`` hierarchy.
- **openstef-models** — Forecasting models, data preprocessing pipelines, energy-specific transforms (lag features, PV generation, etc.), explainability helpers, and ready-to-use presets.
- **openstef-beam** — **B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics. Answers the question *"are my model changes statistically significant?"* Provides regression testing against benchmarks, scoring rules, and visualisation utilities.
- **openstef-meta** — Meta-learning and ensemble model architectures that combine outputs from ``openstef-models`` components.

New features
^^^^^^^^^^^^

**Versioned time series datasets**

A new ``VersionedTimeSeriesDataset`` class tracks *when* each measurement became available, not just its timestamp. This enables realistic backtesting where lag features only use data that would have been available at prediction time — eliminating look-ahead bias.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Build a data part with an 'available_at' column
   weather_data = pd.DataFrame(
       {"temperature": [20.5, 21.0]},
       index=pd.DatetimeIndex([
           datetime(2025, 1, 1, 10, 0),
           datetime(2025, 1, 1, 11, 0),
       ]),
   )
   weather_data["available_at"] = datetime(2025, 1, 1, 16, 0)

   weather_part = TimeSeriesDataset(weather_data, timedelta(hours=1))
   dataset = VersionedTimeSeriesDataset([weather_part])

   print(dataset.is_versioned)  # True

.. mermaid:: /diagrams/root/changelog_diagram_1.mmd

**Versioned lag features**

The new ``VersionedLagsAdder`` transform creates lag features while respecting data availability constraints. Unlike a naive lag transform, it will not use a measurement that would not yet have arrived at the time a forecast is made.

.. code-block:: python

   from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder

   lag_transform = VersionedLagsAdder(
       column="load",
       lags=["PT1H", "PT2H", "P1D"],
   )

**YAML-based configuration**

All configuration objects now extend ``BaseConfig``, which provides first-class YAML serialisation and deserialisation. This replaces ad-hoc dictionary configs used in V3.

.. code-block:: python

   from openstef_core.base_model import BaseConfig

   class MyPipelineConfig(BaseConfig):
       horizon_hours: int = 48
       sample_interval_minutes: int = 15

   # Round-trip through YAML
   config = MyPipelineConfig(horizon_hours=24)
   config.write_yaml("pipeline_config.yaml")

   loaded = MyPipelineConfig.read_yaml("pipeline_config.yaml")
   print(loaded.horizon_hours)  # 24

**Versioned model serialisation**

Model objects now carry an integer ``_VERSION`` attribute. When a saved model is loaded from a different version, ``_migrate_state()`` is called automatically to transform the stored state to the current schema. A ``UserWarning`` is raised when forward compatibility cannot be guaranteed.

**Decoupled external dependencies**

- MLflow is now an optional dependency of ``openstef-models``, not a hard requirement of the core library.
- XGBoost ships as separate CPU and GPU extras (``openstef-models[xgb-cpu]`` and ``openstef-models[xgb-gpu]``).
- LightGBM is available via ``openstef-models[lgbm]``.
- Holiday calendars are now configurable, removing the hard-coded assumption of Dutch public holidays.

**Python version**

OpenSTEF 4.0 requires **Python ≥ 3.12**.

Breaking changes
^^^^^^^^^^^^^^^^

.. warning::

   OpenSTEF 4.0 is not backwards-compatible with 3.x. The import paths, configuration format, and pipeline APIs have all changed. See the :doc:`/user_guide/migration` guide for step-by-step instructions.

The most significant breaking changes are:

- **Package restructuring** — ``openstef`` is now a meta-package. Code that imported directly from the old flat namespace (e.g., ``from openstef.model.regressors import ...``) must be updated to the new sub-package paths (e.g., ``from openstef_models.regressors import ...``).
- **Configuration format** — Dictionary-based ``PredictionJobDict`` configs are replaced by typed ``BaseConfig`` subclasses. Existing config dictionaries must be migrated to YAML or Pydantic model instances.
- **Pipeline API** — The top-level pipeline functions (``train_model_pipeline``, ``create_forecast_pipeline``, etc.) have been redesigned. The new API uses composable pipeline objects rather than standalone functions.
- **Python 3.11 and below** — No longer supported. Upgrade to Python 3.12 before migrating.
- **openstef-dbc removed from core** — Database connector logic has been fully decoupled. Users who relied on ``openstef-dbc`` for data ingestion must wire up their own data loading before passing data to the library.

----

Version 3.x
-----------

The 3.x series established OpenSTEF as a production-grade forecasting library, running 10,000+ daily forecasts at Alliander. It introduced the ``PredictionJob`` abstraction, MLflow experiment tracking, and the first set of XGBoost/GBLinear regressors.

Key milestones in the 3.x line:

- **3.0** — Initial open-source release under the LF Energy umbrella. Introduced ``PredictionJobDict``, the ``train_model_pipeline`` / ``create_forecast_pipeline`` / ``create_components_forecast_pipeline`` top-level functions, and MLflow integration.
- **3.x patch releases** — Incremental improvements to feature engineering (lag selection, Fourier features), model serialisation, and forecast horizon handling. Bug fixes for edge cases in daylight-saving-time transitions and missing-data imputation.

.. note::

   Detailed release notes for individual 3.x patch versions are available in the `GitHub releases archive <https://github.com/OpenSTEF/openstef/releases>`_.

----

Upgrade paths
-------------

+------------------+------------------+----------------------------------------------+
| From version     | To version       | Guide                                        |
+==================+==================+==============================================+
| 3.x              | 4.0              | :doc:`/user_guide/migration`                 |
+------------------+------------------+----------------------------------------------+

For all migration scenarios, the :doc:`/user_guide/migration` page provides concrete before/after code examples, a checklist of required changes, and notes on behavioural differences to watch for in test results.

----

Release policy
--------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_:

- **Major versions** (e.g., 3 → 4) may contain breaking changes to public APIs.
- **Minor versions** add new functionality in a backwards-compatible manner.
- **Patch versions** contain backwards-compatible bug fixes only.

Pre-release versions (``dev``, ``alpha``, ``beta``, ``rc``) are published to PyPI and are suitable for testing but not for production use without explicit validation. The ``openstef`` meta-package always pins to a compatible range of its sub-packages (e.g., ``openstef-core>=4.0.0.dev0,<5``).