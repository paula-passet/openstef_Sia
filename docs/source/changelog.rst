Changelog
=========

This page records the version history of the OpenSTEF library, summarising new features, bug fixes, and breaking changes for each release. Entries are listed in reverse chronological order so the most recent changes appear first.

For step-by-step instructions on upgrading between major versions, see the :doc:`user_guide/migration` page.

----

Version 4.0 (Current)
----------------------

OpenSTEF 4.0 is a major release representing a significant architectural refactor of the library. The primary goals were to improve modularity, broaden applicability beyond a single organisation's infrastructure, and make the library easier to integrate into diverse production environments. Users upgrading from 3.x should consult the migration guide before updating.

New Features
^^^^^^^^^^^^

**Mono-repo package structure**

The library has been reorganised into a set of focused, self-contained packages that can be installed independently or together:

- ``openstef-core`` — shared data types, interfaces, base classes, and testing utilities that underpin all other packages.
- ``openstef-models`` — forecasting models, data preprocessing pipelines, energy-specific feature transforms, explainability helpers, and ready-to-use presets.
- ``openstef-meta`` — meta-learning and ensemble model architectures for advanced use cases.
- ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM) tooling for regression testing and benchmarking model changes.

This structure means you only install what you need. A research notebook that only requires model training and evaluation no longer pulls in production-oriented dependencies.

**Decoupled external dependencies**

MLflow, ``openstef-dbc``, and the XGBoost ``gblinear`` booster are no longer hard dependencies of the core library. MLflow support is now provided through an optional integration module:

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

   # Attach MLflow tracking as a callback — only needed when you want it
   callback = MLFlowStorageCallback(experiment_name="my_experiment")

Install the optional extras to enable this integration:

.. code-block:: bash

   pip install openstef-models[mlflow]

**Modular transform pipeline**

Feature engineering is now expressed as a composable pipeline of explicit transform objects. Each transform is independently configurable and testable. The full set of built-in transforms includes:

.. code-block:: python

   from openstef_models.transforms.general import (
       EmptyFeatureRemover,
       Imputer,
       NaNDropper,
       OutlierHandler,
       SampleWeighter,
       Scaler,
       Selector,
       Shifter,
   )
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.postprocessing import (
       ConfidenceIntervalApplicator,
       QuantileSorter,
   )

**Configurable holiday calendars**

The ``HolidayFeatureAdder`` transform now accepts any ISO 3166-1 alpha-2 country code, removing the previous hard-coded dependency on Dutch public holidays. This makes the library usable for forecasting applications outside the Netherlands without patching internal logic:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder

   # Use German holidays instead of the default
   holiday_transform = HolidayFeatureAdder(country="DE")

**Expanded model zoo**

The following forecasters are available in ``openstef-models``:

- ``XGBoostForecaster`` — gradient-boosted trees via XGBoost.
- ``LGBMForecaster`` — gradient-boosted trees via LightGBM.
- ``LGBMLinearForecaster`` — LightGBM with a linear booster for interpretable models.
- ``GBLinearForecaster`` — gradient-boosted linear model.
- ``MedianForecaster`` — simple median baseline.
- ``FlatlinerForecaster`` — constant-output fallback for degenerate inputs.

Each forecaster exposes a typed hyperparameter dataclass (e.g., ``XGBoostHyperParams``, ``LGBMHyperParams``) for validated, IDE-friendly configuration.

**High-level ``ForecastingModel`` API**

A new ``ForecastingModel`` class in ``openstef-models`` orchestrates the complete train-predict pipeline, including feature engineering, model fitting, quantile estimation, and postprocessing:

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   forecaster = XGBoostForecaster(hyperparams=XGBoostHyperParams(n_estimators=200))
   model = ForecastingModel(forecaster=forecaster)

   model.fit(train_dataset)
   predictions = model.predict(forecast_dataset)

**Full type safety throughout the codebase**

All public APIs now carry complete type annotations. This improves IDE auto-completion, enables static analysis with tools such as ``mypy``, and catches configuration errors before runtime.

**BEAM evaluation framework**

The new ``openstef-beam`` package provides structured backtesting and benchmarking tooling. It is designed to answer the question *"are my model changes statistically significant?"* and supports regression testing against stored baselines — a capability previously unavailable in the library.

Breaking Changes
^^^^^^^^^^^^^^^^

The 4.0 release introduces several breaking changes relative to 3.x. The most significant are listed below; full migration instructions are in the :doc:`user_guide/migration` guide.

- **Package imports have changed.** The top-level ``openstef`` namespace has been reorganised into the sub-packages described above. Any import of the form ``from openstef.pipeline import ...`` or ``from openstef.model import ...`` will need to be updated.
- **``openstef-dbc`` is no longer a dependency.** Code that relied on the database connector being available transitively must now declare it explicitly or replace it with a custom data-loading layer.
- **MLflow is opt-in.** Existing code that used MLflow tracking without explicitly importing it may need to add the ``[mlflow]`` extra and update import paths to ``openstef_models.integrations.mlflow``.
- **Hard-coded Dutch holiday logic has been removed.** If your pipeline relied on the implicit Dutch calendar, pass ``country="NL"`` explicitly to ``HolidayFeatureAdder``.
- **Hyperparameter configuration uses typed dataclasses.** Dictionary-based hyperparameter passing is no longer supported; use the appropriate ``*HyperParams`` dataclass for each model.

.. note::

   See :doc:`user_guide/migration` for a complete mapping of old import paths to new ones and worked examples of the most common upgrade patterns.

Bug Fixes
^^^^^^^^^

- Centralised data preprocessing logic that was previously duplicated across validation and model components, eliminating inconsistencies between training and inference pipelines.
- Resolved edge cases in lag feature generation where features at horizon boundaries could be incorrectly included, leading to data leakage in backtesting scenarios.
- Fixed quantile output ordering in probabilistic forecasts; quantile curves are now guaranteed to be monotonically non-decreasing via ``QuantileSorter``.
- Improved handling of sparse or missing input data so that pipelines degrade gracefully rather than raising unhandled exceptions.

----

Version 3.x Series
-------------------

The 3.x series established OpenSTEF as a production-grade short-term energy forecasting library used in grid operations at Alliander. It introduced the pipeline-based task API (``train_model_and_upload_pipeline``, ``create_forecast_pipeline``), the ``PredictionJobDataClass`` configuration object, and integrated MLflow model tracking as a first-class feature.

Key milestones across the 3.x series included:

- Introduction of probabilistic forecasting via quantile regression, enabling uncertainty bands around point forecasts.
- Support for wind and solar component models alongside net-load forecasting.
- The ``openstef-dbc`` connector for reading measurement data and writing forecasts to a relational database.
- XGBoost and LightGBM model backends with automated hyperparameter optimisation via Optuna.
- Feature importance reporting and SHAP-based explainability for trained models.
- Structured logging and alerting hooks for production monitoring.

.. note::

   Active maintenance of the 3.x series has ended. Critical security fixes may be backported on a case-by-case basis, but new features will only be developed against 4.x. Users are encouraged to migrate.

----

Version 2.x Series
-------------------

Version 2.x was the first public open-source release of OpenSTEF (then still closely tied to Alliander's internal tooling). It introduced the core concept of a *prediction job* as the unit of configuration for a forecasting task, and established the XGBoost-based gradient boosting approach that remains central to the library today.

Notable additions during the 2.x lifecycle:

- Initial open-source release under the MPL-2.0 licence.
- XGBoost model backend with lag and calendar feature engineering.
- Basic backtesting and cross-validation utilities.
- Integration with the Dutch national holiday calendar for automatic feature generation.
- First version of the ``PredictionJobDataClass`` schema.

----

Versioning Policy
-----------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_ (SemVer):

- **Major versions** (e.g., 3 → 4) introduce breaking changes to public APIs. A migration guide is published alongside each major release.
- **Minor versions** (e.g., 4.0 → 4.1) add new functionality in a backwards-compatible manner.
- **Patch versions** (e.g., 4.0.0 → 4.0.1) contain backwards-compatible bug fixes only.

Pre-release versions (alpha, beta, release candidate) are tagged with the suffixes ``a``, ``b``, and ``rc`` respectively (e.g., ``4.0.0rc1``).

The current stable release is always available via:

.. code-block:: bash

   pip install openstef

To pin to a specific major version and receive only compatible updates:

.. code-block:: bash

   pip install "openstef>=4.0,<5.0"

----

Contributing to the Changelog
------------------------------

When opening a pull request, add a brief entry to the *Unreleased* section at the top of this file describing the change. Use one of the following categories:

- **New Feature** — new public API or capability.
- **Bug Fix** — correction of incorrect behaviour.
- **Breaking Change** — any change that requires callers to update their code.
- **Deprecation** — functionality that will be removed in a future major release.
- **Internal** — refactoring, test improvements, or documentation updates with no user-facing impact.