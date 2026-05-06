Changelog
=========

This page records the version history of OpenSTEF, summarising new features, bug fixes, and breaking changes for each release. If you are upgrading between major versions, see the :doc:`/user_guide/migration_guide` for step-by-step migration instructions.

Releases are listed in reverse chronological order — most recent first.

----

Version 4.0 (Current)
----------------------

OpenSTEF 4.0 is a major architectural redesign of the library. The headline change is a shift from a single monolithic package to a **modular mono-repo** composed of four independently installable packages. This restructuring improves modularity, reduces unnecessary dependencies, and makes it significantly easier to integrate OpenSTEF into existing software landscapes.

.. mermaid:: /diagrams/root/changelog_diagram_1.mmd

New packages
^^^^^^^^^^^^

The ``openstef`` meta-package now installs four focused sub-packages:

- **openstef-core** — data types, base classes, shared exceptions, and testing utilities. Every other package depends on this foundation.
- **openstef-models** — forecasting models, data preprocessing pipelines, energy-specific transforms, explainability features, and presets for common use cases.
- **openstef-meta** — meta-learning and ensemble model architectures built on top of ``openstef-models``.
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Answers the question *"are my model changes statistically significant?"* and supports regression testing against benchmarks.

You can install the full stack or only the packages you need:

.. code-block:: python

   # Full installation
   # pip install openstef

   # Individual packages
   # pip install openstef-core
   # pip install openstef-models
   # pip install openstef-beam[all]

   # Verify installed versions
   import openstef_core
   import openstef_models
   import openstef_beam

New features
^^^^^^^^^^^^

**Versioned time series datasets**

A new ``VersionedTimeSeriesDataset`` class in ``openstef-core`` tracks *when* each measurement became available, not just its timestamp. This enables point-in-time reconstruction of the data that would have been visible at any historical moment — a prerequisite for realistic backtesting when measurements arrive with delays or are revised after the fact.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # A weather observation that became available 6 hours after the measurement time
   weather_data = pd.DataFrame(
       {"temperature": [20.5], "available_at": [datetime(2025, 1, 1, 16, 0)]},
       index=pd.DatetimeIndex([datetime(2025, 1, 1, 10, 0)]),
   )
   weather_part = TimeSeriesDataset(weather_data, timedelta(hours=1))

   # Combine into a versioned dataset
   dataset = VersionedTimeSeriesDataset([weather_part])
   assert dataset.is_versioned

**Versioned lag features**

``VersionedLagsAdder`` in ``openstef-models`` creates lag features while respecting data availability constraints. Unlike a naive lag transform, it ensures that a lag feature for time *t* only uses data that would have been observable at prediction time — preventing look-ahead bias in training.

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder

   lags_transform = VersionedLagsAdder(
       column="load",
       lags=["PT1H", "PT24H", "P7D"],
   )

**YAML-based configuration**

All configuration objects now extend ``BaseConfig``, which supports reading from and writing to YAML files. This makes pipeline configurations portable and version-controllable without custom serialisation code.

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

**Validated domain datasets**

``openstef-core`` ships typed dataset wrappers — ``ForecastInputDataset``, ``ForecastDataset``, ``EnergyComponentDataset``, and ``EnsembleForecastDataset`` — that enforce domain-specific constraints at construction time, catching data quality issues before they reach model training.

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset, ForecastDataset

**Serialisation versioning**

Model objects now carry a ``_VERSION`` integer. When a saved model is loaded from a different version, ``_migrate_state`` is called automatically to transform the stored state to the current schema. A ``UserWarning`` is raised when forward compatibility cannot be guaranteed.

**Decoupled external dependencies**

MLflow, XGBoost, and LightGBM are now optional extras rather than hard dependencies. Install only what you need:

.. code-block:: bash

   pip install openstef-models[lgbm]
   pip install openstef-models[xgb-cpu]
   pip install openstef-models[xgb-gpu]

**Generalised domain logic**

Hard-coded assumptions tied to the Dutch energy grid (holiday calendars, fixed grid topology, Alliander-specific data schemas) have been removed or made configurable. OpenSTEF 4.0 is designed to work across geographies and grid operators.

Breaking changes
^^^^^^^^^^^^^^^^

.. warning::

   OpenSTEF 4.0 is a major release with breaking changes throughout. Review the :doc:`/user_guide/migration_guide` before upgrading.

The most significant breaking changes are:

- **Package restructuring.** The single ``openstef`` package has been split into ``openstef-core``, ``openstef-models``, ``openstef-meta``, and ``openstef-beam``. All import paths have changed.
- **Python version requirement.** Python 3.12 or later is now required (previously 3.9+).
- **Removed hard-coded data schemas.** Code that relied on specific column names or data structures from V3 will need to be updated to use the new typed dataset classes.
- **MLflow is optional.** Projects that relied on automatic MLflow tracking must now explicitly install ``openstef-models`` (which includes ``mlflow-skinny``) and configure tracking themselves.
- **Configuration API.** Pipeline configuration previously passed as dictionaries or ``PredictionJobDict`` objects must be migrated to ``BaseConfig`` subclasses.

See the :doc:`/user_guide/migration_guide` for a complete mapping of old import paths to new ones and worked migration examples.

Bug fixes
^^^^^^^^^

- Resolved O(n²) space complexity when concatenating DataFrames with misaligned ``(timestamp, available_at)`` index pairs. The new ``VersionedTimeSeriesDataset`` uses lazy composition, deferring actual DataFrame concatenation until ``select_version()`` is called.
- Eliminated look-ahead bias in lag feature generation during backtesting.
- Standardised exception types across the codebase; callers can now reliably catch ``openstef_core.exceptions.MissingColumnsError`` and related exceptions.

----

Version 3.x
------------

Version 3 was the first publicly released stable series of OpenSTEF. It established the core forecasting pipeline — training, prediction, and backtesting — as a single ``openstef`` package.

Key capabilities introduced across the 3.x series:

- XGBoost and LightGBM gradient-boosted tree models for load forecasting.
- Automated feature engineering including lag features, calendar features, and weather-derived inputs.
- MLflow integration for experiment tracking and model registry.
- Backtesting utilities for evaluating forecast quality over historical periods.
- Quantile forecasting support for probabilistic predictions.
- Solar and wind generation component models.
- ``openstef-dbc`` connector for database-backed prediction job management.

.. note::

   Active maintenance of the 3.x series has ended. Security fixes may be backported on a case-by-case basis, but new features will only be developed in 4.x. Users are encouraged to migrate to 4.0.

----

Version 2.x
------------

Version 2 introduced the ``PredictionJob`` abstraction, which became the central configuration object for the 3.x series. It also added:

- Structured logging throughout the pipeline.
- Initial support for probabilistic (quantile) forecasts.
- Improved handling of missing measurements and data gaps.
- The ``create_forecast`` and ``train_model`` pipeline entry points that remained stable through 3.x.

----

Version 1.x
------------

The initial open-source release of OpenSTEF (then called *openstf*). Version 1 extracted the short-term forecasting system developed internally at Alliander into a standalone Python library. Core functionality included:

- XGBoost-based point forecasts for electricity load at substation level.
- Basic feature engineering for time-of-day, day-of-week, and weather inputs.
- Simple backtesting over a rolling window.

----

Versioning policy
-----------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_:

- **Major versions** (1→2, 2→3, 3→4) may contain breaking changes to public APIs and import paths.
- **Minor versions** add new functionality in a backwards-compatible manner.
- **Patch versions** contain backwards-compatible bug fixes only.

Pre-release versions are published to PyPI with ``dev`` or ``alpha`` suffixes (e.g., ``4.0.0.dev0``). These are suitable for testing and feedback but forward compatibility is not guaranteed.

To pin to a stable minor series in your project:

.. code-block:: bash

   pip install "openstef>=4.0,<5"
   # or for individual packages:
   pip install "openstef-models>=4.0,<5"