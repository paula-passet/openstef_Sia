Changelog
=========

This page documents the version history of OpenSTEF, including new features, improvements, bug fixes, and breaking changes. For detailed migration instructions when upgrading between major versions, see the :doc:`../user_guide/migration_guide`.

OpenSTEF follows `semantic versioning <https://semver.org/>`_. Version numbers follow the format MAJOR.MINOR.PATCH where:

- **MAJOR** versions introduce breaking changes that may require code modifications
- **MINOR** versions add functionality in a backward-compatible manner
- **PATCH** versions include backward-compatible bug fixes

To check your current version:

.. code-block:: bash

   pip show openstef

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions.

Version 4.0.0 (2025)
--------------------

OpenSTEF 4.0 represents a major architectural refactor focused on modularity, type safety, and extensibility. This release transforms OpenSTEF from a monolithic application into a flexible library suitable for diverse forecasting use cases beyond the original Dutch grid operator context.

Breaking Changes
^^^^^^^^^^^^^^^^

**Modular Package Structure**

OpenSTEF is now split into multiple packages:

- ``openstef-core``: Core abstractions, data structures, and interfaces
- ``openstef-models``: Forecasting models and feature engineering transforms
- ``openstef-metrics``: Evaluation metrics and scoring functions
- ``openstef``: Meta-package that installs all components

Existing imports will need updating. For example:

.. code-block:: python

   # Old (v3.x)
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   
   # New (v4.x)
   from openstef_models.models.xgb import XGBQuantileRegressor
   from openstef_models.transforms import DatetimeFeaturesAdder, LagFeaturesAdder

**Configuration System**

Hard-coded configuration values have been replaced with explicit, type-safe configuration objects using Pydantic:

.. code-block:: python

   # Old (v3.x)
   model = XGBQuantileOpenstfRegressor()
   model.fit(X, y)
   
   # New (v4.x)
   from openstef_models.models.xgb import XGBQuantileRegressor, XGBQuantileRegressorConfig
   
   config = XGBQuantileRegressorConfig(
       n_estimators=100,
       max_depth=5,
       quantiles=[0.1, 0.5, 0.9]
   )
   model = XGBQuantileRegressor(config=config)
   model.fit(data)

**Data Structures**

The library now uses structured dataset objects instead of raw pandas DataFrames:

.. code-block:: python

   # Old (v3.x)
   predictions = model.predict(df)
   
   # New (v4.x)
   from openstef_core.datasets import TimeSeriesDataset
   
   dataset = TimeSeriesDataset(
       data=df,
       target_column="load",
       datetime_column="datetime"
   )
   predictions = model.predict(dataset)

**Transform Pipeline**

Feature engineering has been redesigned around composable transforms:

.. code-block:: python

   # Old (v3.x)
   df_with_features = apply_features(df, feature_names=["hour", "dayofweek"])
   
   # New (v4.x)
   from openstef_models.transforms import DatetimeFeaturesAdder, Pipeline
   
   pipeline = Pipeline([
       DatetimeFeaturesAdder(features=["hour", "day_of_week"])
   ])
   transformed_data = pipeline.fit_transform(dataset)

See the :doc:`../user_guide/migration_guide` for comprehensive migration instructions.

New Features
^^^^^^^^^^^^

**Flexible Transform System**

The new transform architecture provides composable, reusable feature engineering components:

- ``DatetimeFeaturesAdder``: Extract temporal features (hour, day, month, etc.)
- ``CyclicFeaturesAdder``: Create cyclic encodings for periodic features
- ``LagFeaturesAdder``: Add lagged values for time series modeling
- ``RollingAggregatesAdder``: Compute rolling statistics
- ``HolidayFeatureAdder``: Add holiday indicators with customizable calendars
- ``CompletenessChecker``: Validate data quality before training

Transforms can be chained into pipelines and serialized for production deployment.

**Versioned Time Series Support**

New ``VersionedTimeSeriesDataset`` enables handling forecast data with multiple versions:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.transforms import VersionedLagsAdder
   
   versioned_data = VersionedTimeSeriesDataset(
       data=df,
       target_column="load",
       datetime_column="datetime",
       version_column="forecast_version"
   )
   
   # Lags respect data availability constraints
   transform = VersionedLagsAdder(lags=[24, 48, 168])
   transformed = transform.fit_transform(versioned_data)

**Customizable Holiday Calendars**

Holiday features are no longer limited to Dutch holidays:

.. code-block:: python

   from openstef_models.transforms import HolidayFeatureAdder
   
   # Use built-in calendars
   adder = HolidayFeatureAdder(country="DE")
   
   # Or define custom holidays
   custom_holidays = {
       "New Year": "01-01",
       "Independence Day": "07-04"
   }
   adder = HolidayFeatureAdder(custom_holidays=custom_holidays)

**Enhanced Metrics**

The new ``openstef-metrics`` package provides comprehensive evaluation tools:

- Quantile-specific metrics (rMAE@quantile, skill score at peaks)
- Cost-weighted error metrics for financial optimization
- CRPS (Continuous Ranked Probability Score) for probabilistic forecasts
- Custom metric definitions for domain-specific evaluation

**Type Safety Throughout**

Full type annotations enable static type checking with mypy or pyright, catching errors before runtime:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.xgb import XGBQuantileRegressor
   
   def train_model(data: TimeSeriesDataset) -> XGBQuantileRegressor:
       model = XGBQuantileRegressor()
       model.fit(data)
       return model  # Type checker validates return type

**State Versioning**

Models and transforms now include version metadata for safe serialization:

.. code-block:: python

   # Save model with version information
   model.save("model.pkl")
   
   # Load automatically migrates from older versions
   loaded_model = XGBQuantileRegressor.load("model.pkl")
   # Warning issued if loading legacy format

Improvements
^^^^^^^^^^^^

**Decoupled Dependencies**

- MLflow integration is now optional (install with ``pip install openstef[mlflow]``)
- Database dependencies removed from core library
- Model-specific dependencies isolated to relevant packages

**Test Coverage**

- Increased test coverage across all packages
- Faster test execution through better isolation
- Property-based testing for data transforms

**Documentation**

- Complete rewrite following the Diátaxis framework
- Separate tutorials, how-to guides, reference, and explanatory content
- Expanded examples covering diverse use cases
- Clear distinction between library and reference implementation

**Performance**

- Optimized transform implementations for large datasets
- Reduced memory footprint for rolling aggregates
- Faster serialization for production deployment

Version 3.x
-----------

OpenSTEF 3.x was the production version used by Alliander and other grid operators for operational forecasting. It provided a complete forecasting pipeline with feature engineering, model training, and evaluation capabilities.

.. note::

   Version 3.x is no longer actively maintained. Users are encouraged to migrate to 4.0 for ongoing support and new features.

Key capabilities in 3.x included:

- XGBoost-based quantile regression models
- Automated feature engineering for Dutch grid operator use cases
- MLflow integration for experiment tracking
- Database integration for operational deployment
- Validation and data quality checks

Version 2.x and Earlier
-----------------------

Earlier versions of OpenSTEF were developed internally at Alliander before the project was open-sourced. These versions are not publicly available.

Release Schedule
----------------

OpenSTEF follows a continuous release model:

- **Patch releases** are issued as needed for bug fixes
- **Minor releases** occur when new features are ready and tested
- **Major releases** are planned when breaking changes accumulate or significant architectural improvements are ready

Security updates are prioritized and may be released outside the normal schedule.

Deprecation Policy
------------------

When features are deprecated:

1. A deprecation warning is added in a minor release
2. The feature remains functional for at least one minor version
3. The feature is removed in the next major release

Deprecated features are documented in release notes with migration guidance.

Getting Help
------------

If you encounter issues after upgrading:

- Check the :doc:`../user_guide/migration_guide` for version-specific guidance
- Review the `GitHub issues <https://github.com/OpenSTEF/openstef/issues>`_ for known problems
- Join the discussion on the `LF Energy Slack <https://slack.lfenergy.org/>`_ (#openstef channel)
- Open a new issue if you discover a bug or regression

Contributing to Changelog
--------------------------

OpenSTEF uses conventional commits to automatically generate changelog entries. When contributing:

- Use semantic commit messages (``feat:``, ``fix:``, ``docs:``, etc.)
- Include breaking change markers (``!``) for incompatible changes
- Reference issue numbers in commit messages
- See :doc:`../contributor_guide/development_workflow` for details

Changelog entries are automatically compiled from commit messages during the release process.