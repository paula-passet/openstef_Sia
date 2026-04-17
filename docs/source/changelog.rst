Changelog
=========

This page documents the version history of OpenSTEF, summarising new features, bug fixes, and breaking changes for each release. Entries are listed in reverse chronological order (newest first).

For step-by-step instructions on upgrading between major versions, see the :doc:`user_guide/migration` guide.

----

Version 4.0 (Current)
----------------------

OpenSTEF 4.0 is a major architectural release. The library has been restructured from a monolithic package into a **modular mono-repo** of self-contained packages. This release reflects lessons learned from production deployments at Alliander (10,000+ forecasts daily) and broadens the library's applicability beyond a single organisation or grid topology.

.. note::

   Version 4.0 contains breaking changes relative to 3.x. If you are upgrading an existing project, read the :doc:`user_guide/migration` guide before updating.

New packages
^^^^^^^^^^^^

The single ``openstef`` package has been split into focused, independently installable packages:

- **openstef-core** — shared data types, base classes, interfaces, and testing utilities. All other packages depend on this foundation.
- **openstef-models** — forecasting models, data preprocessing pipelines, energy-specific feature transforms, explainability helpers, and presets for common use cases.
- **openstef-meta** — meta-learning and modern ensemble architectures for advanced modelling scenarios.
- **openstef-beam** (Backtesting, Evaluation, Analysis, Metrics) — statistical regression testing against benchmarks, answering the question *"are my model changes significant?"*

Install only what you need:

.. code-block:: python

   # Minimal install — core data types and interfaces only
   # pip install openstef-core

   # Forecasting models and transforms
   # pip install openstef-models

   # Full evaluation and backtesting suite
   # pip install openstef-beam

New features
^^^^^^^^^^^^

**Versioned time series support**

A new ``VersionedTimeSeriesDataset`` type tracks data availability constraints, making it possible to reconstruct exactly which data would have been available at any past prediction time. This is essential for realistic backtesting when measurements arrive with delays or are revised after the fact.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

   # Weather data with an explicit availability timestamp
   weather_data = pd.DataFrame(
       {"temperature": [20.5], "available_at": [datetime(2025, 1, 1, 16, 0)]},
       index=pd.DatetimeIndex([datetime(2025, 1, 1, 10, 0)]),
   )
   weather_part = TimeSeriesDataset(weather_data, timedelta(hours=1))

   # Compose multiple parts lazily — no O(n²) DataFrame concatenation
   dataset = VersionedTimeSeriesDataset([weather_part])
   assert dataset.is_versioned

**Versioned lag features**

``VersionedLagsAdder`` creates lag features that respect data availability constraints, so lag values only use data that would have been observable at prediction time:

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder

   lags = VersionedLagsAdder(column="load", lag_minutes=[15, 30, 60])

**Modular configuration via Pydantic**

Hard-coded assumptions (holiday calendars, resolution, horizon) have been replaced with Pydantic-validated configuration objects. Custom configurations can be passed at construction time without subclassing.

**Flexible pipeline callbacks**

Pipelines now expose callback hooks for enterprise integration scenarios, allowing custom logging, alerting, or data routing without forking core pipeline code.

**Broader domain applicability**

- Holiday calendars are now configurable — no longer hard-coded to the Netherlands.
- Input data constraints have been relaxed; the library accepts more flexible ``DataFrame`` shapes.
- Energy pricing and cost-weighted error metrics are supported out of the box for grid-losses use cases.

**Full type safety**

The entire codebase carries type annotations. All public APIs are validated with ``mypy`` in strict mode.

Breaking changes
^^^^^^^^^^^^^^^^

- The top-level ``openstef`` package no longer exists. Replace imports with the appropriate sub-package (``openstef_core``, ``openstef_models``, etc.). See the :doc:`user_guide/migration` guide for a full import mapping.
- ``PredictionJobDataClass`` has been replaced by Pydantic model classes. Dictionary-style attribute access (``pj["horizon"]``) no longer works; use attribute access (``pj.horizon``) instead.
- The ``MLFlowSerializer`` and ``openstef-dbc`` database connector are no longer bundled. They are available as optional companion packages.
- ``xgboost/gblinear`` is no longer a hard dependency. Install ``openstef-models[xgboost]`` if your pipelines use it.
- Preprocessing logic previously scattered across model classes has been centralised into explicit transform objects. Custom models that overrode preprocessing methods will need to be updated.

Bug fixes
^^^^^^^^^

- Fixed O(n²) memory growth when concatenating versioned ``DataFrame`` objects with misaligned ``(timestamp, available_at)`` index pairs. The new lazy-composition architecture in ``VersionedTimeSeriesDataset`` resolves this.
- Resolved inconsistent behaviour when ``available_at`` timestamps crossed daylight-saving-time boundaries.
- Corrected rMAE calculation at peak quantiles when the evaluation window contained fewer than the minimum required samples.

----

Version 3.x
------------

Version 3 established OpenSTEF as a production-grade forecasting library and introduced the prediction-job abstraction that drives automated retraining and inference pipelines.

Highlights
^^^^^^^^^^

- **Prediction job abstraction** — a single ``PredictionJobDataClass`` object carries all configuration needed to train, validate, and deploy a model for one forecasting point.
- **Automated retraining pipelines** — ``train_model_pipeline``, ``create_forecast_pipeline``, and ``optimize_hyperparameters_pipeline`` provide end-to-end workflows callable with minimal boilerplate.
- **XGBoost and LightGBM models** — gradient-boosted tree models with energy-specific feature engineering (lag features, calendar features, weather inputs).
- **SHAP explainability** — feature importance and individual prediction explanations via SHAP values, integrated into the standard training pipeline.
- **MLflow experiment tracking** — optional integration with MLflow for model versioning and metric logging.
- **Quantile forecasting** — probabilistic forecasts expressed as configurable quantile intervals.
- **Operational monitoring** — built-in data validation checks that flag missing data, outliers, and distribution shifts before training or inference.

Known limitations addressed in 4.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Monolithic package structure made it difficult to use individual components without pulling in all dependencies.
- Holiday calendar and other locale-specific logic was hard-coded for the Netherlands.
- Preprocessing was tightly coupled to model classes, making it hard to test or reuse independently.
- No first-class support for data availability constraints in backtesting.
- ``MLFlowSerializer`` and ``openstef-dbc`` were bundled, creating mandatory infrastructure dependencies.

----

Version 2.x
------------

Version 2 was the first public open-source release of OpenSTEF, extracted from Alliander's internal tooling.

Highlights
^^^^^^^^^^

- Initial public release on PyPI and GitHub under the LF Energy umbrella.
- Core XGBoost-based forecasting pipeline for substation load forecasting.
- Basic feature engineering: lag features, time-of-day, day-of-week, and weather inputs.
- Integration with ``openstef-dbc`` for reading and writing forecast data to a relational database.
- Hyperparameter optimisation using Optuna.
- Confidence intervals derived from quantile regression.

----

Versioning policy
-----------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_ (``MAJOR.MINOR.PATCH``):

- **MAJOR** — incompatible API changes. A migration guide is published alongside the release.
- **MINOR** — new backwards-compatible functionality.
- **PATCH** — backwards-compatible bug fixes.

Pre-release versions (alpha, beta, release candidate) are tagged with suffixes such as ``4.0.0a1`` or ``4.0.0rc1`` and may contain incomplete features or APIs that are still subject to change.

.. note::

   The ``dev`` build (version string ``0.0.0`` or containing ``+``) is built directly from the ``main`` branch and is not guaranteed to be stable. Use a pinned release version in production.

----

How to report issues
--------------------

Found a bug or unexpected behaviour? Please open an issue on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_ and include:

- The OpenSTEF package(s) and version(s) you are using.
- A minimal reproducible example.
- The full traceback if an exception was raised.

Feature requests and design proposals are welcome as GitHub Discussions before opening a pull request.