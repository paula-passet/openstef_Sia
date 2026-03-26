Changelog
=========

This page contains the complete version history of OpenSTEF, automatically generated from our CHANGELOG.md file and GitHub release notes. OpenSTEF follows semantic versioning and uses conventional commits to enable automated changelog generation.

.. note::
   This changelog is automatically generated from commit messages and GitHub releases. For the most up-to-date information, see the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version History
---------------

OpenSTEF uses semantic versioning (MAJOR.MINOR.PATCH) where:

- **MAJOR** version changes indicate breaking changes that require code updates
- **MINOR** version changes add new features while maintaining backward compatibility  
- **PATCH** version changes contain bug fixes and minor improvements

Breaking Changes and Migration
------------------------------

Major version releases may contain breaking changes. When upgrading across major versions, review the migration notes below and test your code thoroughly.

.. warning::
   Breaking changes are marked with ⚠️ in the changelog entries. Always review these carefully before upgrading.

v4.0.0 - Major Architecture Redesign
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Release Date:** 2024-12-XX

**Breaking Changes:**
- ⚠️ Complete package restructure into modular architecture
- ⚠️ New import paths: ``openstef_models``, ``openstef_beam``, ``openstef_core``
- ⚠️ Minimum Python version raised to 3.12
- ⚠️ Removed deprecated APIs from v3.x

**New Features:**
- Modular package design allowing selective installation
- Enhanced type safety with modern Python features
- Improved performance through optimized data structures
- New transformer-based forecasting models
- Advanced explainability tools

**Migration Guide:**
See the `How-To Guides <../guides/how_to_guides.html>`_ for detailed migration instructions from v3.x to v4.0.

v3.2.1 - Bug Fixes
^^^^^^^^^^^^^^^^^^^

**Release Date:** 2024-11-15

**Bug Fixes:**
- Fixed memory leak in long-running forecasting pipelines
- Resolved timezone handling issues in data preprocessing
- Corrected quantile calculation edge cases

v3.2.0 - Feature Release  
^^^^^^^^^^^^^^^^^^^^^^^^

**Release Date:** 2024-10-20

**New Features:**
- Added support for district heating forecasts
- Enhanced weather data integration
- Improved model selection algorithms
- New evaluation metrics for specialized use cases

**Improvements:**
- Better error messages for common configuration issues
- Performance optimizations for large datasets
- Enhanced documentation with more examples

**Bug Fixes:**
- Fixed edge case in feature engineering pipeline
- Resolved issues with missing data handling
- Corrected forecast horizon validation

v3.1.2 - Patch Release
^^^^^^^^^^^^^^^^^^^^^^

**Release Date:** 2024-09-10

**Bug Fixes:**
- Fixed compatibility issues with pandas 2.1+
- Resolved memory usage in backtesting workflows
- Corrected forecast export formatting

v3.1.1 - Patch Release
^^^^^^^^^^^^^^^^^^^^^^

**Release Date:** 2024-08-25

**Bug Fixes:**
- Fixed regression in model persistence
- Resolved configuration validation edge cases
- Improved error handling for malformed input data

v3.1.0 - Feature Release
^^^^^^^^^^^^^^^^^^^^^^^^

**Release Date:** 2024-08-01

**New Features:**
- Added MV route congestion management capabilities
- Integration with power-grid-model for topology-aware forecasting
- Enhanced backtesting framework with multiple model comparison
- New metrics for grid-specific evaluation

**Improvements:**
- Faster model training through algorithmic improvements
- Better handling of seasonal patterns
- Enhanced logging and debugging capabilities

**Bug Fixes:**
- Fixed issues with daylight saving time transitions
- Resolved edge cases in quantile forecasting
- Corrected feature importance calculations

Commit Types and Conventions
-----------------------------

OpenSTEF uses `Conventional Commits <https://www.conventionalcommits.org/>`_ to structure commit messages and enable automated changelog generation. The following commit types are recognized:

**Feature Types:**
- ``feat``: New features for users
- ``fix``: Bug fixes
- ``perf``: Performance improvements

**Development Types:**
- ``docs``: Documentation changes
- ``style``: Code formatting changes
- ``refactor``: Code restructuring without behavior changes
- ``test``: Test additions or corrections
- ``build``: Build system changes
- ``ci``: Continuous integration changes
- ``chore``: Maintenance tasks

**Breaking Changes:**
Breaking changes are indicated with ``!`` after the type (e.g., ``feat!:``) or by including ``BREAKING CHANGE:`` in the commit footer.

Release Process
---------------

OpenSTEF releases follow this automated process:

1. **Development**: Features and fixes are developed on feature branches
2. **Integration**: Changes are merged to the main branch after review
3. **Versioning**: Semantic version is determined from conventional commit messages
4. **Release**: Automated release process creates GitHub releases and publishes packages
5. **Documentation**: Changelog is automatically updated from commit history

.. note::
   Pre-release versions (alpha, beta, rc) may be available for testing new features. These are marked clearly in the version number and should not be used in production.

Staying Updated
---------------

To stay informed about OpenSTEF releases:

- **GitHub Releases**: Subscribe to `repository notifications <https://github.com/OpenSTEF/openstef/releases>`_
- **Community Slack**: Join the `#openstef channel <https://slack.lfenergy.org/>`_ for release announcements
- **Mailing List**: Contact us at openstef@lfenergy.org to join our mailing list

For installation and upgrade instructions, see the `Installation Guide <../getting_started/installation.html>`_.