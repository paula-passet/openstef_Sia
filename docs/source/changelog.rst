Changelog
=========

This page records what changed in each release of OpenSTEF. Entries are listed in reverse-chronological order. Each section covers new features, bug fixes, deprecations, and breaking changes for that release.

For step-by-step instructions on upgrading between major versions, see the :doc:`user_guide/migration` guide.

----

Version 4.0 (Current)
----------------------

OpenSTEF 4.0 is a major architectural release. The library has been restructured from a single-package codebase into a **modular mono-repo** composed of focused, independently installable packages. This redesign improves composability, reduces mandatory dependencies, and broadens the range of use cases the library can support.

.. note::

   Version 4.0 is a breaking release. Code written against the v3 API will require updates. See the :doc:`user_guide/migration` guide for a full walkthrough.

New Features
^^^^^^^^^^^^

**Modular package structure**

The library is now split into five self-contained packages. You install only what you need:

- ``openstef-core`` — shared data types, base classes, interfaces, and exceptions. Every other package depends on this.
- ``openstef-models`` — forecasting models, data preprocessing pipelines, energy-specific feature transforms, explainability utilities, and ready-to-use presets.
- ``openstef-meta`` — meta-learning and advanced ensemble model architectures.
- ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM). Answers the question *"are my model changes statistically significant?"* and supports regression testing against benchmark datasets.
- ``openstef-reference`` — a reference implementation showing how to wire the library packages together for a production deployment.

Install the full stack or individual packages:

.. code-block:: python

   # Full installation
   pip install openstef

   # Individual packages
   pip install openstef-core openstef-models openstef-beam

**Type safety throughout**

All public APIs now carry full type annotations. ``BaseConfig`` (from ``openstef-core``) is the foundation for model configuration objects, enabling IDE auto-completion and static analysis with ``mypy`` or ``pyright``.

.. code-block:: python

   from openstef_core.base_model import BaseConfig

   class MyModelConfig(BaseConfig):
       horizon_hours: int = 48
       sample_interval_minutes: int = 15
       max_lag_hours: int = 72

**Versioned time-series datasets**

A new ``VersionedTimeSeriesDataset`` class in ``openstef-core`` models data that arrives with delays or is revised over time. This is essential for realistic backtesting — lag features are built only from data that would have been available at prediction time, eliminating look-ahead bias.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

   # Simulate weather data arriving 6 hours after measurement
   weather_data = pd.DataFrame(
       {"temperature": [20.5, 21.0, 19.8]},
       index=pd.DatetimeIndex([
           datetime(2025, 1, 1, 8, 0),
           datetime(2025, 1, 1, 9, 0),
           datetime(2025, 1, 1, 10, 0),
       ]),
   )
   weather_data["available_at"] = datetime(2025, 1, 1, 16, 0)

   part = TimeSeriesDataset(weather_data, timedelta(hours=1))
   dataset = VersionedTimeSeriesDataset([part])

   # Reconstruct the dataset as it looked at a specific point in time
   snapshot = dataset.select_version(as_of=datetime(2025, 1, 1, 16, 0))

.. note:: [DIAGRAM: Data flow showing how VersionedTimeSeriesDataset composes multiple TimeSeriesDataset parts and resolves a point-in-time snapshot via select_version()]

**Versioned lag features**

``VersionedLagsAdder`` (in ``openstef-models``) creates lag features that respect data-availability constraints. Unlike a naive lag transform, it will not use a measurement that would not yet have been available at the forecast creation time.

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder

   lags = VersionedLagsAdder(
       column="load_mw",
       lag_durations=["PT15M", "PT1H", "PT24H", "PT48H"],
   )
   dataset_with_lags = lags.transform(dataset)

**Flexible configuration**

Hard-coded assumptions from v3 (Dutch public holidays, fixed 15-minute resolution, Alliander-specific data schemas) have been replaced with explicit, overridable configuration. Holiday calendars, sample intervals, and data schemas are now parameters rather than constants.

**Decoupled external dependencies**

MLflow, ``openstef-dbc``, and specific gradient-boosting backends (XGBoost ``gblinear``) are no longer mandatory dependencies of the core library. They are optional extras or belong to the reference implementation.

**Expanded use-case support**

The 4.0 API is designed to support forecasting scenarios beyond electricity distribution, including district heating (thermal demand), grid losses with market-price-weighted error minimisation, and congestion management with peak-detection objectives.

Bug Fixes
^^^^^^^^^

- Resolved O(n²) memory growth when concatenating DataFrames with misaligned ``(timestamp, available_at)`` index pairs during backtesting. The new ``VersionedTimeSeriesDataset`` uses lazy composition, deferring DataFrame concatenation until ``select_version()`` is called.
- Corrected look-ahead bias in lag feature construction during historical backtests.
- Standardised logging configuration across all packages — ``NullHandler`` is now attached at the library root so host applications control log output.

Breaking Changes
^^^^^^^^^^^^^^^^

- **Package imports have changed.** The top-level ``openstef`` namespace is reorganised. Imports from ``openstef.pipeline``, ``openstef.model``, and ``openstef.validation`` must be updated to the new package paths (``openstef_core``, ``openstef_models``, etc.).
- **Configuration objects replace keyword arguments.** Functions that previously accepted loose ``**kwargs`` now expect typed ``BaseConfig`` subclasses.
- **``openstef-dbc`` is no longer bundled.** Database connectivity is the responsibility of the reference implementation or the caller.
- **Holiday calendar defaults removed.** Callers must supply a calendar explicitly; there is no implicit fallback to Dutch public holidays.
- **Minimum Python version is 3.10.**

See the :doc:`user_guide/migration` guide for a complete mapping of old import paths to new ones and worked upgrade examples.

----

Version 3.x
-----------

Version 3 established OpenSTEF as a production forecasting library running at Alliander, generating over 10,000 forecasts daily. The 3.x series focused on stabilising the single-package API, adding MLflow experiment tracking, and expanding the set of supported gradient-boosting backends.

Notable 3.x milestones
^^^^^^^^^^^^^^^^^^^^^^

**3.x series highlights (selected)**

- Introduced the ``PredictionJobManager`` abstraction for managing multiple concurrent forecasting tasks.
- Added quantile regression support, enabling probabilistic forecasts alongside point estimates.
- Integrated MLflow for experiment tracking and model registry.
- Shipped built-in feature engineering for Dutch public holidays, lag features, and weather-derived predictors (irradiance, wind speed, temperature).
- Added ``openstef-dbc`` as the standard database connectivity layer.
- Introduced the ``train_model`` / ``create_forecast`` pipeline API that became the primary entry point for most users.
- Expanded XGBoost support to include the ``gblinear`` booster alongside ``gbtree``.
- Added SHAP-based explainability for trained models.

.. note::

   Active development on the 3.x series has ended. Critical security fixes will be considered on a case-by-case basis, but new features are developed exclusively on 4.x. Users are encouraged to migrate.

----

Version 2.x
-----------

Version 2 was the first public open-source release of OpenSTEF (then called *short-term forecasting* internally at Alliander). It established the core forecasting loop — feature engineering, model training, and forecast creation — and introduced the prediction job concept as the unit of work.

Notable 2.x milestones
^^^^^^^^^^^^^^^^^^^^^^

- Initial open-source release under the LF Energy umbrella.
- XGBoost as the primary model backend.
- Lag-based feature engineering for 15-minute resolution electricity load data.
- Basic validation and data-cleaning pipelines.
- First version of the ``openstef-dbc`` connector for reading from and writing to the Alliander data platform.

----

Version 1.x
-----------

Version 1 was an internal Alliander release, not publicly distributed via PyPI. It is documented here for historical completeness. The 1.x codebase was a research prototype; the public API was formalised in version 2.

----

Deprecation Policy
------------------

OpenSTEF follows these conventions for deprecating functionality:

- A feature is marked deprecated with a ``DeprecationWarning`` at least one **minor** release before removal.
- Breaking changes are reserved for **major** version increments.
- The :doc:`user_guide/migration` guide is updated alongside every deprecation notice, providing a concrete replacement for each removed API.

If you rely on a feature that has been deprecated, open an issue on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_ to discuss the timeline or request an extension.

----

.. note::

   Patch-level release notes (e.g., 4.0.1, 4.0.2) are published as GitHub Releases on the repository. This page covers only significant minor and major releases.