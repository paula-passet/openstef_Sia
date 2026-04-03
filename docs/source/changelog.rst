Changelog
=========

OpenSTEF follows `semantic versioning <https://semver.org/>`_. This page documents the version history, including new features, bug fixes, and breaking changes for each release.

For detailed migration instructions when upgrading between major versions, see the :doc:`/user_guide/migration_guide`.

.. note::

   OpenSTEF 4.0 represents a major architectural shift to a modular package structure. If you're upgrading from 3.x, review the migration guide carefully.

Version 4.0.0 (2025-01-XX)
--------------------------

Major release introducing modular architecture and modern Python tooling.

Breaking Changes
^^^^^^^^^^^^^^^^

**Modular Package Structure**

OpenSTEF has been split into separate packages:

- ``openstef-core``: Shared utilities and dataset types
- ``openstef-models``: Core forecasting models and pipelines
- ``openstef-beam``: Backtesting and evaluation tools
- ``openstef``: Meta-package for convenient installation

This change affects imports throughout the codebase:

.. code-block:: python

   # Old (v3.x)
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import train_model
   
   # New (v4.0)
   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   from openstef_models.pipeline import train_model

**Python Version Requirements**

- Minimum Python version: 3.12 (previously 3.10)
- Python 3.13 now supported
- Dropped support for Python 3.10 and 3.11

**Versioned State Management**

Models and transformers now include version metadata for state serialization:

.. code-block:: python

   # Models automatically handle version migration
   model = XGBQuantileOpenstfRegressor()
   state = model.__getstate__()
   # state now includes {"__version__": 1, "state": {...}}
   
   # Loading legacy models triggers a warning
   legacy_model = load_model("old_model.pkl")
   # UserWarning: Loading legacy XGBQuantileOpenstfRegressor without version metadata

**Dataset API Changes**

The ``VersionedTimeSeriesDataset`` API has been refined:

- Feature names now use ISO 8601 duration format for lags (e.g., ``load_lag_-PT1H`` instead of ``load_lag_-1h``)
- Improved type safety with strict typing throughout
- Better handling of time zones and daylight saving transitions

New Features
^^^^^^^^^^^^

**Modern Development Tooling**

- Migration to ``uv`` for dependency management and builds
- Workspace-based monorepo structure for better package coordination
- Improved CI/CD with faster test execution
- Pre-commit hooks for code quality

**Enhanced Documentation**

- Comprehensive restructuring with clearer navigation
- New tutorial series covering common workflows
- Improved API reference with better type annotations
- Migration guide for v3.x users

**Model Improvements**

- Better handling of missing data in feature engineering
- Improved quantile regression stability
- Enhanced model serialization with forward compatibility warnings
- Automatic state migration for backward compatibility

**BEAM Enhancements**

- Separated evaluation tools into dedicated ``openstef-beam`` package
- Improved benchmark storage and comparison utilities
- Better integration with modern data science workflows

Improvements
^^^^^^^^^^^^

- **Performance**: Faster data loading and transformation with optimized pandas operations
- **Type Safety**: Comprehensive type hints throughout the codebase
- **Error Messages**: More informative error messages with actionable guidance
- **Memory Efficiency**: Reduced memory footprint for large datasets
- **Testing**: Expanded test coverage with property-based testing

Bug Fixes
^^^^^^^^^

- Fixed daylight saving time handling in lag feature generation
- Corrected quantile prediction ordering in ensemble models
- Resolved memory leaks in long-running forecast pipelines
- Fixed edge cases in missing data imputation
- Corrected timezone-aware datetime handling in dataset validation

Deprecations
^^^^^^^^^^^^

- Legacy import paths (use package-specific imports instead)
- Python 3.10 and 3.11 support (use 3.12+)
- Unversioned model serialization (automatic migration provided)

Version 3.x Series
------------------

Version 3.5.0
^^^^^^^^^^^^^

**Release Date**: 2024-XX-XX

Features:

- Added support for external regressor features in XGBoost models
- Improved handling of categorical features in feature engineering
- Enhanced validation pipeline with better error reporting

Bug Fixes:

- Fixed issue with quantile crossing in multi-output predictions
- Corrected feature importance calculation for ensemble models
- Resolved pandas FutureWarning messages

Version 3.4.0
^^^^^^^^^^^^^

**Release Date**: 2024-XX-XX

Features:

- Introduced configurable feature engineering pipelines
- Added support for custom validation metrics
- Improved model persistence with compression options

Improvements:

- Faster training for large datasets (>1M samples)
- Better memory management in cross-validation
- Enhanced logging with structured output

Version 3.3.0
^^^^^^^^^^^^^

**Release Date**: 2024-XX-XX

Features:

- Added quantile regression support for all model types
- Introduced automated hyperparameter tuning
- New evaluation metrics for probabilistic forecasts

Bug Fixes:

- Fixed rare race condition in parallel model training
- Corrected handling of leap years in seasonal features
- Resolved compatibility issues with scikit-learn 1.3+

Version 3.2.0
^^^^^^^^^^^^^

**Release Date**: 2023-XX-XX

Features:

- Added support for multiple forecast horizons
- Introduced model ensembling capabilities
- New preprocessing transformers for weather data

Improvements:

- Reduced model training time by 30% on average
- Better handling of missing weather data
- Enhanced documentation with more examples

Version 3.1.0
^^^^^^^^^^^^^

**Release Date**: 2023-XX-XX

Features:

- Added support for Python 3.11
- Introduced feature importance analysis tools
- New validation strategies for time series data

Bug Fixes:

- Fixed issue with duplicate timestamps in training data
- Corrected seasonal feature calculation for southern hemisphere
- Resolved pandas deprecation warnings

Version 3.0.0
^^^^^^^^^^^^^

**Release Date**: 2023-XX-XX

Major release with significant API improvements.

Breaking Changes:

- Refactored model API for consistency across estimators
- Changed configuration format for pipeline definitions
- Updated feature naming conventions

Features:

- Complete rewrite of feature engineering pipeline
- Added support for custom model architectures
- Introduced comprehensive validation framework
- New visualization tools for forecast analysis

Improvements:

- 50% faster feature generation
- Better error messages and validation
- Improved documentation and examples

Version 2.x Series
------------------

Version 2.8.0
^^^^^^^^^^^^^

**Release Date**: 2023-XX-XX

Final release in the 2.x series. Users are encouraged to upgrade to 3.x for continued support.

Features:

- Added support for additional weather features
- Improved handling of holiday effects
- Enhanced model evaluation metrics

Bug Fixes:

- Fixed issue with DST transitions in feature generation
- Corrected quantile prediction bounds
- Resolved compatibility with pandas 2.0

Version 2.7.0
^^^^^^^^^^^^^

**Release Date**: 2022-XX-XX

Features:

- Introduced support for multiple prediction quantiles
- Added configurable feature lag windows
- New preprocessing options for load data

Improvements:

- Better handling of outliers in training data
- Enhanced model serialization format
- Improved test coverage

Version 2.6.0
^^^^^^^^^^^^^

**Release Date**: 2022-XX-XX

Features:

- Added support for Python 3.10
- Introduced automated feature selection
- New validation metrics for forecast quality

Bug Fixes:

- Fixed memory leak in long-running processes
- Corrected timezone handling in data loading
- Resolved scikit-learn compatibility issues

Earlier Versions
----------------

For release notes for versions 2.5.0 and earlier, please refer to the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Upgrade Path
------------

**From 3.x to 4.0**

1. Upgrade Python to 3.12 or higher
2. Review the :doc:`/user_guide/migration_guide` for detailed instructions
3. Update imports to use new package structure
4. Test thoroughly with your existing models (automatic state migration provided)

**From 2.x to 4.0**

We recommend upgrading to 3.x first, then to 4.0:

1. Upgrade to the latest 3.x release
2. Address any deprecation warnings
3. Follow the 3.x to 4.0 upgrade path above

**From 2.x to 3.x**

1. Review API changes in configuration and model interfaces
2. Update feature engineering pipelines to new format
3. Retrain models with new feature naming conventions
4. Update validation and evaluation code

Release Schedule
----------------

OpenSTEF follows a regular release cadence:

- **Major releases** (X.0.0): Annual, with significant new features or breaking changes
- **Minor releases** (X.Y.0): Quarterly, with new features and improvements
- **Patch releases** (X.Y.Z): As needed, for bug fixes and small improvements

Security Updates
----------------

Security vulnerabilities are addressed in patch releases as soon as possible. Critical security issues are announced on our `GitHub Security Advisories <https://github.com/OpenSTEF/openstef/security/advisories>`_ page.

To report a security vulnerability, please email openstef@lfenergy.org rather than filing a public issue.

Staying Informed
----------------

To stay updated on new releases:

- **GitHub Releases**: Subscribe to `release notifications <https://github.com/OpenSTEF/openstef/releases>`_
- **Slack**: Join the `LF Energy Slack workspace <https://slack.lfenergy.org/>`_ (#openstef channel)
- **Mailing List**: Contact openstef@lfenergy.org to join our announcement list

Contributing
------------

We welcome contributions! If you'd like to propose a feature or report a bug:

1. Check existing `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_
2. Review our :doc:`/contribute/index` guide
3. Follow our conventional commit format for clear release notes
4. Join our four-weekly co-coding sessions

For more information, see our :doc:`/project/support` page.