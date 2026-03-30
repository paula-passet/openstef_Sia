Changelog
=========

This page provides a comprehensive version history of OpenSTEF, combining information from the CHANGELOG.md file with GitHub release notes. OpenSTEF follows semantic versioning to help you understand the impact of updates.

.. note::
   This changelog is automatically generated from the project's CHANGELOG.md file and GitHub releases. For the most up-to-date information, visit the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version Format
--------------

OpenSTEF uses semantic versioning (MAJOR.MINOR.PATCH) where:

- **MAJOR** version changes indicate breaking changes that may require code modifications
- **MINOR** version changes add new features while maintaining backward compatibility  
- **PATCH** version changes include bug fixes and small improvements

Breaking changes are marked with ⚠️ and include migration guidance where applicable.

OpenSTEF 4.0 Series
--------------------

Version 4.0.0 (Latest)
^^^^^^^^^^^^^^^^^^^^^^

**Release Date:** TBD

**Major Changes:**

⚠️ **Breaking Changes:**
- Complete architectural redesign with modular package structure
- Minimum Python version increased to 3.12
- New package names: ``openstef-core``, ``openstef-models``, ``openstef-beam``
- Removed hard dependencies on MLFlow and openstef-dbc
- Updated import paths for all modules

**New Features:**
- Modular architecture allowing installation of only needed components
- Enhanced type safety throughout the codebase
- Flexible configuration system replacing hard-coded assumptions
- Improved support for diverse data formats and availability scenarios
- New BEAM package for backtesting, evaluation, analysis, and metrics
- Enhanced enterprise integration capabilities

**Improvements:**
- Significantly increased test coverage
- Centralized data preprocessing logic
- Better documentation following Diátaxis framework
- Improved performance optimizations
- Support for custom models, transforms, and metrics

**Migration Guide:**

To migrate from OpenSTEF 3.x to 4.0:

.. code-block:: python

   # Old (v3.x)
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   
   # New (v4.0)
   from openstef_models.models import XGBQuantileOpenstfRegressor
   from openstef_models.transforms import apply_features

See the :doc:`../guides/how_to_guides` for detailed migration instructions.

OpenSTEF 3.x Series
--------------------

Version 3.8.0
^^^^^^^^^^^^^^

**Release Date:** 2024-03-15

**New Features:**
- Enhanced weather feature integration
- Improved quantile regression capabilities
- Additional validation metrics

**Bug Fixes:**
- Fixed memory leak in long-running forecasting loops
- Resolved timezone handling issues in data preprocessing
- Corrected edge cases in feature engineering pipeline

Version 3.7.2
^^^^^^^^^^^^^^

**Release Date:** 2024-02-28

**Bug Fixes:**
- Fixed compatibility issues with pandas 2.0
- Resolved XGBoost version conflicts
- Improved error handling for missing data scenarios

Version 3.7.1
^^^^^^^^^^^^^^

**Release Date:** 2024-02-14

**Bug Fixes:**
- Critical fix for forecast horizon calculations
- Resolved memory usage in batch processing
- Fixed validation pipeline edge cases

Version 3.7.0
^^^^^^^^^^^^^^

**Release Date:** 2024-01-30

**New Features:**
- Support for custom holiday calendars
- Enhanced model explainability features
- Improved backtesting framework

**Improvements:**
- Better handling of data gaps
- Optimized feature engineering performance
- Enhanced logging and debugging capabilities

Earlier Versions
----------------

Version 3.6.x Series
^^^^^^^^^^^^^^^^^^^^^

The 3.6.x series focused on stability improvements and performance optimizations:

- Enhanced data validation
- Improved model serialization
- Better error messages and debugging
- Performance optimizations for large datasets

Version 3.5.x Series
^^^^^^^^^^^^^^^^^^^^^

The 3.5.x series introduced:

- Quantile forecasting capabilities
- Enhanced weather integration
- Improved model evaluation metrics
- Better support for missing data

Version 3.0.x - 3.4.x Series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Earlier 3.x versions established:

- Core forecasting framework
- XGBoost-based models
- Feature engineering pipeline
- Basic evaluation capabilities

Getting Updates
---------------

To stay informed about new releases:

1. **GitHub Releases:** Subscribe to `OpenSTEF releases <https://github.com/OpenSTEF/openstef/releases>`_
2. **PyPI:** Monitor the `OpenSTEF PyPI page <https://pypi.org/project/openstef/>`_
3. **Community:** Join our `Slack workspace <https://slack.lfenergy.org/>`_ (#openstef channel)

Upgrading
---------

Before upgrading to a new version:

1. Review the changelog for breaking changes
2. Test your code with the new version in a development environment
3. Update your dependencies as needed
4. Follow any migration guides provided

.. code-block:: bash

   # Check current version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef
   
   # Or upgrade to specific version
   pip install openstef==4.0.0

For development installations:

.. code-block:: bash

   # Update development installation
   cd openstef
   git pull origin main
   uv sync --all-extras --dev

Contributing to Releases
-------------------------

OpenSTEF follows conventional commit messages for automatic changelog generation:

- ``feat:`` for new features
- ``fix:`` for bug fixes  
- ``docs:`` for documentation changes
- ``perf:`` for performance improvements
- ``test:`` for test additions or corrections

Breaking changes are marked with ``!`` (e.g., ``feat!: redesign API``).

See the :doc:`../contribute/contributing_guide` for detailed contribution guidelines.