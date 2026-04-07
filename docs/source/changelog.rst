Changelog
=========

This page documents the version history of OpenSTEF, including new features, bug fixes, breaking changes, and deprecations. OpenSTEF follows `semantic versioning <https://semver.org/>`_ to help you understand the impact of each release.

For detailed migration instructions when upgrading between major versions, see the :doc:`migration guide <user_guide/migration>`.

Version 4.0.0 (2025-01-XX)
--------------------------

OpenSTEF 4.0 represents a major architectural redesign of the library, introducing a modular package structure and modernizing the codebase for Python 3.12+. This release focuses on improved maintainability, better separation of concerns, and enhanced developer experience.

Breaking Changes
^^^^^^^^^^^^^^^^

**Python Version Requirement**

- Minimum Python version increased from 3.10 to 3.12
- Python 3.13 is now officially supported
- Users on Python 3.10 or 3.11 should continue using OpenSTEF 3.x

**Modular Package Architecture**

OpenSTEF is now split into multiple independent packages:

- ``openstef-core``: Core utilities, datasets, and base classes
- ``openstef-models``: Forecasting models and transforms
- ``openstef-beam``: Backtesting and evaluation tools
- ``openstef``: Meta-package for convenient installation

This change affects imports throughout your code:

.. code-block:: python

   # Old (v3.x)
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   
   # New (v4.0)
   from openstef_models.regressors import XGBQuantileRegressor
   from openstef_models.transforms import FeatureAdder

**Import Path Changes**

All import paths have been reorganized to reflect the new package structure. The old ``openstef.*`` namespace is replaced with package-specific namespaces:

- ``openstef.model.*`` → ``openstef_models.regressors.*``
- ``openstef.feature_engineering.*`` → ``openstef_models.transforms.*``
- ``openstef.pipeline.*`` → ``openstef_models.pipelines.*``
- ``openstef.validation.*`` → ``openstef_models.validation.*``

**Dataset API Changes**

The dataset API has been completely redesigned around the new ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` classes:

.. code-block:: python

   # Old (v3.x)
   import pandas as pd
   data = pd.DataFrame(...)
   
   # New (v4.0)
   from openstef_core.datasets import TimeSeriesDataset
   
   dataset = TimeSeriesDataset(
       data=df,
       target_column="load",
       datetime_column="datetime"
   )

**Feature Engineering Redesign**

Feature engineering has been reimagined as a composable transform system:

.. code-block:: python

   # Old (v3.x)
   from openstef.feature_engineering.apply_features import apply_features
   data_with_features = apply_features(data, feature_names)
   
   # New (v4.0)
   from openstef_models.transforms import FeatureAdder
   
   transform = FeatureAdder(features=["hour", "dayofweek"])
   transformed_data = transform.fit_transform(dataset)

**Model State Serialization**

Models now use a versioned state serialization system that automatically handles backward compatibility:

.. code-block:: python

   # Models include version metadata in saved state
   model = XGBQuantileRegressor()
   model.fit(train_data)
   
   # State includes __version__ field
   state = model.__getstate__()
   # {'__version__': 1, 'state': {...}}
   
   # Automatic migration when loading older models
   model.__setstate__(old_state)  # Warns if version mismatch

**Configuration System**

Configuration now uses Pydantic v2 models with strict validation:

.. code-block:: python

   # Old (v3.x)
   config = {
       "model": "xgb",
       "horizons": [0.25, 0.5, 0.75]
   }
   
   # New (v4.0)
   from openstef_models.regressors import XGBQuantileRegressor
   
   model = XGBQuantileRegressor(
       quantiles=[0.25, 0.5, 0.75],
       n_estimators=100
   )

New Features
^^^^^^^^^^^^

**Modular Installation**

Install only the components you need:

.. code-block:: bash

   # Full installation
   pip install "openstef[all]"
   
   # Models only (lightweight)
   pip install openstef-models
   
   # Models + evaluation tools
   pip install "openstef[beam]"

**Type Safety Improvements**

- Full type hints throughout the codebase
- Strict type checking with Pyright
- Better IDE support and autocomplete
- Runtime validation with Pydantic v2

**Transform System**

New composable transform system for feature engineering:

.. code-block:: python

   from openstef_models.transforms import (
       FeatureAdder,
       LagsAdder,
       HolidayFeatureAdder
   )
   from openstef_core.transforms import Pipeline
   
   pipeline = Pipeline([
       FeatureAdder(features=["hour", "dayofweek"]),
       LagsAdder(lag_hours=[24, 48, 168]),
       HolidayFeatureAdder(country="NL")
   ])
   
   transformed_data = pipeline.fit_transform(dataset)

**Versioned Time Series Support**

New ``VersionedTimeSeriesDataset`` for handling data with availability constraints:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   dataset = VersionedTimeSeriesDataset(
       data=df,
       target_column="load",
       datetime_column="datetime",
       available_at_column="available_at"
   )

**Improved Documentation**

- Comprehensive API reference with type signatures
- Hands-on tutorials for common workflows
- Architecture documentation explaining design decisions
- Migration guide for upgrading from v3.x

**Development Tools**

- Modern tooling with ``uv`` for fast dependency management
- Pre-commit hooks for code quality
- Comprehensive test suite with pytest
- Automated documentation builds

Improvements
^^^^^^^^^^^^

**Performance**

- Faster data loading with optimized dataset classes
- Reduced memory footprint for large time series
- Parallel processing utilities for batch operations
- Efficient serialization for model persistence

**Code Quality**

- Consistent code style with Ruff formatter
- Strict linting rules enforced in CI
- 100% type coverage with Pyright
- Comprehensive docstrings following NumPy style

**Testing**

- Expanded test coverage across all packages
- Property-based testing for data transforms
- Integration tests for end-to-end workflows
- Performance benchmarks for critical paths

**Developer Experience**

- Clear package boundaries and responsibilities
- Consistent API patterns across modules
- Helpful error messages with actionable guidance
- Extensive inline documentation

Deprecations
^^^^^^^^^^^^

The following components from OpenSTEF 3.x are deprecated and will not be available in 4.0:

- Legacy ``openstef.model`` namespace (use ``openstef_models.regressors``)
- Direct pandas DataFrame manipulation (use ``TimeSeriesDataset``)
- Dictionary-based configuration (use Pydantic models)
- Old feature engineering functions (use transform system)

Migration Path
^^^^^^^^^^^^^^

Upgrading from OpenSTEF 3.x requires code changes. Follow these steps:

1. **Update Python version** to 3.12 or higher
2. **Install OpenSTEF 4.0** with appropriate extras
3. **Update imports** to use new package structure
4. **Migrate to dataset API** for data handling
5. **Adopt transform system** for feature engineering
6. **Update model instantiation** to use new configuration

For detailed migration instructions with code examples, see the :doc:`migration guide <user_guide/migration>`.

Version 3.x Series
------------------

OpenSTEF 3.x was the last major version supporting Python 3.10 and 3.11. It provided a monolithic package structure with all functionality in a single ``openstef`` package.

Version 3.2.0 (2024-XX-XX)
^^^^^^^^^^^^^^^^^^^^^^^^^^

**New Features**

- Added support for custom holiday calendars
- Improved handling of missing data in feature engineering
- Enhanced model persistence with compression options

**Bug Fixes**

- Fixed timezone handling in datetime features
- Corrected quantile crossing in extreme scenarios
- Resolved memory leak in batch prediction

**Improvements**

- Optimized XGBoost hyperparameter defaults
- Better error messages for invalid input data
- Documentation updates and tutorial improvements

Version 3.1.0 (2024-XX-XX)
^^^^^^^^^^^^^^^^^^^^^^^^^^

**New Features**

- Support for Python 3.11
- New feature importance analysis tools
- Enhanced validation metrics

**Bug Fixes**

- Fixed edge cases in lag feature generation
- Corrected handling of daylight saving time transitions
- Resolved issues with categorical feature encoding

**Improvements**

- Faster model training for large datasets
- Reduced memory usage during feature engineering
- Updated dependencies to latest stable versions

Version 3.0.0 (2023-XX-XX)
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Breaking Changes**

- Minimum Python version increased to 3.10
- Removed deprecated ``old_pipeline`` module
- Changed default hyperparameters for XGBoost models

**New Features**

- Quantile regression support for all models
- Automated feature selection
- Cross-validation utilities

**Improvements**

- Modernized codebase with type hints
- Improved test coverage
- Enhanced documentation

Version 2.x Series
------------------

OpenSTEF 2.x introduced machine learning-based forecasting and established the foundation for the library's architecture.

Version 2.5.0 (2023-XX-XX)
^^^^^^^^^^^^^^^^^^^^^^^^^^

**New Features**

- Added LightGBM regressor support
- Weather feature integration
- Holiday feature engineering

**Bug Fixes**

- Fixed prediction interval calculation
- Corrected handling of missing timestamps

**Improvements**

- Performance optimizations for large datasets
- Better handling of edge cases

Version 2.0.0 (2022-XX-XX)
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Breaking Changes**

- Complete rewrite of the forecasting pipeline
- New API for model training and prediction
- Changed configuration format

**New Features**

- XGBoost-based forecasting models
- Automated hyperparameter tuning
- Feature engineering pipeline
- Model validation framework

**Improvements**

- Significantly improved forecast accuracy
- Better handling of special days and holidays
- Comprehensive documentation

Version 1.x Series
------------------

OpenSTEF 1.x was the initial open-source release, providing basic forecasting capabilities.

Version 1.0.0 (2021-XX-XX)
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Initial Release**

- Basic time series forecasting
- Linear regression models
- Simple feature engineering
- Data validation utilities

Contributing to the Changelog
------------------------------

When contributing to OpenSTEF, please follow our commit message conventions to ensure changes are properly categorized:

**Commit Types**

- ``feat``: New features for users
- ``fix``: Bug fixes
- ``docs``: Documentation changes
- ``perf``: Performance improvements
- ``refactor``: Code changes that neither fix bugs nor add features
- ``test``: Test additions or corrections
- ``build``: Build system or dependency changes
- ``ci``: CI configuration changes

**Breaking Changes**

Mark breaking changes with ``!`` after the type:

.. code-block:: bash

   git commit -m "feat!: redesign dataset API"

**Examples**

.. code-block:: bash

   # Feature with scope
   git commit -m "feat(models): add transformer-based forecasting model"
   
   # Bug fix with detailed description
   git commit -m "fix(validation): handle missing weather data gracefully
   
   Previously the validation would crash when weather data was missing.
   Now it logs a warning and continues with available features.
   
   Fixes #456"
   
   # Documentation update
   git commit -m "docs: update installation guide for uv workspace"

For more information on contributing, see the :doc:`development workflow <contribute/development_workflow>` guide.

Release Schedule
----------------

OpenSTEF follows a regular release schedule:

- **Major releases** (X.0.0): Annual, with breaking changes
- **Minor releases** (X.Y.0): Quarterly, with new features
- **Patch releases** (X.Y.Z): As needed, for bug fixes

All releases are announced on:

- `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_
- LF Energy Slack (#openstef channel)
- Project mailing list

Subscribe to `GitHub notifications <https://github.com/OpenSTEF/openstef/releases>`_ to stay informed about new releases.