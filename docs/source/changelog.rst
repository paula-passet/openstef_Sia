Changelog
=========

This page documents the version history of the OpenSTEF library, summarising new features, bug fixes,
and breaking changes for each release. Entries are listed in reverse chronological order so the most
recent changes appear first.

For step-by-step instructions on upgrading between major versions, see the
:doc:`../user_guide/migration_guide`.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. A **major** version bump signals
   breaking API changes. A **minor** version bump adds backwards-compatible functionality. A **patch**
   version bump contains backwards-compatible bug fixes only.

----

Version 4.x
-----------

4.0.0 — Major Architectural Refactor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Status: Alpha / Active Development*

Version 4.0 is a ground-up redesign of the OpenSTEF library. The primary motivation was to make
OpenSTEF genuinely useful as a standalone Python library — not just as the internal tooling it grew
from — while preserving the forecasting quality that has been running 10,000+ daily forecasts in
production at Alliander.

**Breaking changes**

- The library has been restructured into a **modular mono-repo** of independently installable packages.
  The single ``openstef`` package is replaced by focused sub-packages; code that previously imported
  from ``openstef.*`` must be updated to import from the appropriate new package.

  +-----------------------+--------------------------------------------------+
  | New package           | Responsibility                                   |
  +=======================+==================================================+
  | ``openstef-core``     | Data types, interfaces, base classes, shared     |
  |                       | exceptions, and testing utilities.               |
  +-----------------------+--------------------------------------------------+
  | ``openstef-models``   | Forecasting models, preprocessing pipelines,     |
  |                       | energy-specific transforms, explainability, and  |
  |                       | quick-start presets.                             |
  +-----------------------+--------------------------------------------------+
  | ``openstef-meta``     | Meta-learning, modern ensemble models, and       |
  |                       | advanced model architectures.                    |
  +-----------------------+--------------------------------------------------+
  | ``openstef-beam``     | Backtesting, Evaluation, Analysis, and Metrics   |
  |                       | (BEAM) framework.                                |
  +-----------------------+--------------------------------------------------+

- ``PredictionJob`` and related configuration objects are now Pydantic v2 models backed by
  ``openstef_core.base_model.BaseModel``. Dictionary-style construction still works, but attribute
  access is now type-checked at runtime.
- Hard-coded Dutch holiday calendars and Alliander-specific preprocessing assumptions have been
  removed from the default pipelines. Equivalent behaviour can be restored through the new
  configuration layer (see :doc:`../user_guide/configuration`).
- MLflow and ``openstef-dbc`` are no longer required dependencies. They are now optional integrations.
  Remove any unconditional ``import mlflow`` calls from code that wraps OpenSTEF pipelines.
- The ``gblinear`` model backend has been decoupled from the core XGBoost dependency. Install
  ``openstef-models[gblinear]`` to retain this model type.

**New features**

- *Modular package architecture.* Each sub-package can be installed and used independently, making it
  straightforward to embed only the components you need into an existing system.

- *``openstef-beam`` framework.* A dedicated backtesting, evaluation, analysis, and metrics package
  that answers the question "are my model changes statistically significant?" It supports regression
  testing against benchmark datasets and was spun out of an internal Alliander project.

  .. code-block:: python

      from openstef_beam.analysis import BacktestAnalysis

      analysis = BacktestAnalysis.from_results(backtest_results)
      report = analysis.compare_to_baseline(baseline_results)
      print(report.summary())

- *``ForecastingWorkflowConfig`` presets.* The new ``openstef_models.presets`` module provides
  high-level configuration objects that wire together models, feature engineering, and evaluation
  settings with sensible defaults, reducing boilerplate for common use cases.

  .. code-block:: python

      from openstef_models.presets import ForecastingWorkflowConfig

      config = ForecastingWorkflowConfig(
          model_id="my_substation",
          model="xgboost",
          horizons=[0.25, 1.0, 24.0, 47.0],  # hours ahead
          quantiles=[0.1, 0.5, 0.9],
          radiation_column="shortwave_radiation",
          wind_speed_column="wind_speed_80m",
          temperature_column="temperature_2m",
          rolling_aggregate_features=["mean", "median", "max", "min"],
          mlflow_storage=None,  # disable MLflow for local runs
      )

- *LightGBM forecaster.* ``openstef-models`` now ships a first-class LightGBM backend
  (``openstef_models.models.forecasting.lgbm_forecaster``) alongside the existing XGBoost and
  GBLinear backends. All three expose the same multi-quantile forecasting interface.

- *YAML-based configuration persistence.* ``BaseConfig`` objects can be serialised to and
  deserialised from YAML files, making it easier to version-control experiment configurations.

  .. code-block:: python

      from openstef_core.base_model import read_yaml_config
      from openstef_models.presets import ForecastingWorkflowConfig

      # Load a saved configuration from disk
      config = read_yaml_config("configs/substation_a.yaml", ForecastingWorkflowConfig)

      # Persist a modified configuration
      config.write_yaml("configs/substation_a_v2.yaml")

- *Full type safety throughout the codebase.* All public APIs are fully annotated. Type errors that
  previously surfaced only at runtime are now caught by static analysis tools such as mypy and pyright.

- *Flexible data input constraints.* The library no longer enforces a rigid column schema on input
  DataFrames. Required columns are declared per-model and validated at pipeline entry points with
  clear error messages.

- *Customisable holiday calendars.* Holiday feature generation now accepts any
  ``pandas.tseries.holiday.AbstractHolidayCalendar`` subclass, removing the previous hard dependency
  on Dutch public holidays.

- *Energy price features.* Pipelines can now ingest day-ahead electricity prices (e.g., EPEX) as
  an additional predictor via the ``energy_price_column`` configuration key.

- *``openstef-meta`` package.* Introduces meta-learning capabilities and modern ensemble
  architectures for users who need to push beyond single-model performance.

**Bug fixes and improvements**

- Centralised data preprocessing logic that was previously duplicated across validation and model
  components into a single, well-tested preprocessing module.
- Standardised coding practices and documentation styles across the entire codebase.
- Increased test coverage and streamlined test execution via a unified test runner.
- Improved handling of data availability constraints such as delayed measurements and delayed weather
  forecast ingestion.

.. note::

   For a complete guide to upgrading from v3 to v4, including import path mappings and configuration
   migration examples, see :doc:`../user_guide/migration_guide`.

----

Version 3.x
-----------

3.4.x — Stability and Minor Enhancements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The 3.4 series focused on stability, test coverage, and incremental improvements to the existing
pipeline architecture. It represents the last stable release line before the v4 architectural refactor.

**Notable changes across the 3.4 series**

- Improved robustness of the train-validate-predict pipeline when input data contains gaps or
  irregular timestamps.
- Additional feature engineering options exposed through ``PredictionJob`` configuration fields.
- Performance improvements to the XGBoost hyperparameter optimisation step.
- Expanded support for probabilistic forecasting quantiles beyond the default set.
- Various fixes to the MLflow experiment tracking integration.

3.3.x — Quantile Forecasting and Explainability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Version 3.3 introduced probabilistic (quantile) forecasting as a first-class feature and added
initial SHAP-based model explainability support.

**Highlights**

- Multi-quantile output from all gradient boosting model backends.
- SHAP feature importance integration for trained models.
- ``PredictionJob`` extended with ``quantiles`` field to control output quantile levels.
- Improved back-testing utilities for evaluating probabilistic forecast quality.

3.2.x — Pipeline Consolidation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Version 3.2 consolidated the train, validate, and predict workflows into a unified pipeline API,
reducing the amount of orchestration code users needed to write themselves.

**Highlights**

- Unified ``run_train_pipeline``, ``run_forecast_pipeline``, and ``run_backtest_pipeline`` entry
  points.
- Standardised logging and error handling across all pipelines.
- Initial support for the GBLinear model backend as an alternative to gradient boosting trees.

3.1.x — Weather Feature Improvements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Version 3.1 expanded the set of weather-derived features available to forecasting models and
improved the handling of missing weather data.

**Highlights**

- Additional derived weather features: wind power density, clear-sky irradiance ratio, and
  temperature-humidity index.
- Graceful degradation when weather forecast data is partially unavailable.
- Configurable weather feature column name mappings to ease integration with different data sources.

3.0.0 — Open Source Release
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Version 3.0 marked the first public open-source release of OpenSTEF under the
`Mozilla Public License 2.0 <https://www.mozilla.org/en-US/MPL/2.0/>`_, contributed to the
`LF Energy <https://lfenergy.org/>`_ foundation.

**Highlights**

- Public release of the core forecasting library previously developed internally at Alliander.
- XGBoost-based gradient boosting model as the primary forecasting backend.
- ``PredictionJob`` as the central configuration object for describing a forecasting task.
- Integration with MLflow for experiment tracking and model registry.
- Integration with ``openstef-dbc`` for database connectivity (optional reference implementation).
- Dutch public holiday calendar and Alliander-specific preprocessing included as defaults.

----

Versioning Policy
-----------------

OpenSTEF uses the following conventions:

- **Major releases** (e.g., 3.0, 4.0) may introduce breaking changes to public APIs. A migration
  guide is published alongside each major release.
- **Minor releases** (e.g., 3.3, 3.4) add new functionality in a backwards-compatible manner.
  Deprecation warnings are issued for features scheduled for removal in the next major release.
- **Patch releases** (e.g., 3.4.1, 3.4.2) contain only backwards-compatible bug fixes and
  security patches. Upgrading within a patch series is always safe.

Deprecation warnings are emitted via Python's standard ``warnings.warn`` mechanism with
``DeprecationWarning`` or ``FutureWarning`` category. To surface all deprecation warnings during
development, run your code with::

    python -W default::DeprecationWarning your_script.py

or add the following to your test configuration:

.. code-block:: python

    import warnings
    warnings.filterwarnings("error", category=DeprecationWarning)

----

Reporting Issues
----------------

If you encounter a regression or unexpected behaviour in any release, please open an issue on the
`OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_. When reporting a bug, include:

- The OpenSTEF package version (``pip show openstef-models`` or equivalent).
- A minimal reproducible example.
- The full traceback if an exception was raised.

For questions about upgrading between versions, see :doc:`../user_guide/migration_guide` or start a
discussion on the project's GitHub Discussions page.