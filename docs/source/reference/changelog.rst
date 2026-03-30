Changelog
=========

This page documents the version history of OpenSTEF, a Python machine learning library for short-term energy forecasting. The changelog combines information from the repository's CHANGELOG.md file with GitHub release notes to provide a comprehensive view of changes across all releases.

.. note::
   This page is automatically generated from the repository's CHANGELOG.md and GitHub release notes. For the most up-to-date information, visit the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

OpenSTEF follows `semantic versioning <https://semver.org/>`_. Version numbers follow the MAJOR.MINOR.PATCH format where:

- MAJOR version changes indicate incompatible API changes
- MINOR version changes add functionality in a backward-compatible manner
- PATCH version changes include backward-compatible bug fixes

Understanding Version Numbers
------------------------------

The version number structure helps you understand the impact of upgrading:

**Major versions (e.g., 3.0.0 → 4.0.0)** represent significant architectural changes that may require code modifications. These releases typically include breaking changes, new features, and substantial improvements to the library's design.

**Minor versions (e.g., 4.0.0 → 4.1.0)** add new features or capabilities while maintaining backward compatibility with the same major version. Your existing code should continue to work without modifications.

**Patch versions (e.g., 4.0.0 → 4.0.1)** contain bug fixes and minor improvements. These releases are always safe to upgrade to within the same minor version.

Migration Guides
----------------

When upgrading between major versions, consult the relevant migration guide to understand breaking changes and required code modifications:

**Migrating from OpenSTEF 3.x to 4.x**

OpenSTEF 4.0 represents a major architectural refactor focused on modularity, type safety, and broader domain applicability. Key changes include:

- **Modular package structure**: The monolithic package is now split into ``openstef-core``, ``openstef-models``, and ``openstef-beam``
- **Python version requirement**: Minimum Python version increased to 3.12 (from 3.10)
- **Import paths changed**: Update imports to use new package names (e.g., ``from openstef_models import forecasting``)
- **Decoupled dependencies**: External dependencies like MLFlow and openstef-dbc are no longer required
- **Flexible configuration**: Hard-coded assumptions replaced with configurable options

For detailed migration instructions, see the :doc:`../guides/how_to_guides` page, which includes a dedicated section on migrating from V3 to V4 based on community feedback.

**Migrating from OpenSTEF 2.x to 3.x**

OpenSTEF 3.0 introduced improved model interfaces and enhanced feature engineering capabilities. Consult the 3.0.0 release notes for specific migration steps.

Version History
---------------

This section contains the complete version history. Each release includes a summary of changes organized by type:

- **Breaking Changes**: Incompatible API changes requiring code modifications
- **New Features**: New capabilities added to the library
- **Improvements**: Enhancements to existing functionality
- **Bug Fixes**: Resolved issues and corrections
- **Documentation**: Updates to documentation and examples
- **Internal**: Changes to development tools, testing, and internal structure

Version 4.0.0 (Latest)
^^^^^^^^^^^^^^^^^^^^^^

**Release Date**: TBD

OpenSTEF 4.0 is a major architectural refactor that transforms the library into a modular, extensible toolkit for short-term energy forecasting. This release focuses on flexibility, type safety, and broader applicability beyond the original Dutch grid operator use case.

**Breaking Changes**

- Minimum Python version increased to 3.12
- Package structure reorganized into modular components (``openstef-core``, ``openstef-models``, ``openstef-beam``)
- Import paths changed to reflect new package structure
- Removed hard-coded dependencies on MLFlow and openstef-dbc
- Removed xgboost/gblinear as default model (replaced with more flexible model selection)
- Configuration system redesigned for greater flexibility

**New Features**

- Modular architecture allowing installation of only required components
- ``openstef-beam`` package for backtesting, evaluation, analysis, and metrics
- Improved type safety throughout the codebase
- Flexible configuration mechanisms replacing hard-coded assumptions
- Support for custom holiday calendars and energy pricing models
- Enhanced support for diverse data availability scenarios
- Clear interfaces for custom models, transforms, and metrics
- Improved preset system for quick start with common use cases

**Improvements**

- Significantly increased test coverage
- Standardized coding practices and documentation styles
- Centralized data preprocessing logic
- Improved performance optimizations for production use cases
- Better error messages and debugging information
- Enhanced documentation following the Diátaxis framework
- Streamlined development workflow with uv workspace support

**Documentation**

- Complete documentation overhaul with new structure
- New quick start guide for faster onboarding
- Comprehensive tutorials covering basic to advanced usage
- Task-specific how-to guides for common implementation scenarios
- Architecture diagrams explaining modular design
- Concept explanations for key forecasting principles
- FAQ addressing common questions from conferences and new users

**Internal**

- Migration to uv for dependency management
- Improved CI/CD pipelines
- Enhanced pre-commit hooks for code quality
- Better package versioning and release automation

**Migration Notes**

Upgrading from 3.x requires code changes due to the new package structure. See the migration guide in :doc:`../guides/how_to_guides` for detailed instructions and examples based on real-world migration experiences.

Version 3.x Series
^^^^^^^^^^^^^^^^^^

.. note::
   Content for version 3.x releases will be populated from the CHANGELOG.md file and GitHub release notes. This includes all 3.x releases with their features, bug fixes, and improvements.

Version 2.x Series
^^^^^^^^^^^^^^^^^^

.. note::
   Content for version 2.x releases will be populated from the CHANGELOG.md file and GitHub release notes. This includes all 2.x releases with their features, bug fixes, and improvements.

Version 1.x Series
^^^^^^^^^^^^^^^^^^

.. note::
   Content for version 1.x releases will be populated from the CHANGELOG.md file and GitHub release notes. This includes all 1.x releases with their features, bug fixes, and improvements.

Release Process
---------------

OpenSTEF releases follow a structured process to ensure quality and stability:

**Release Cadence**

- Major versions are released when significant architectural changes are ready
- Minor versions are released as new features are completed and tested
- Patch versions are released as needed for bug fixes

**Pre-release Versions**

Before stable releases, pre-release versions may be published for testing:

- **Alpha releases** (e.g., 4.0.0a1) are early previews for testing new features
- **Beta releases** (e.g., 4.0.0b1) are feature-complete but may contain bugs
- **Release candidates** (e.g., 4.0.0rc1) are final testing versions before stable release

**Release Channels**

- **Stable releases**: Recommended for production use, available via PyPI and conda-forge
- **Pre-releases**: Available via PyPI with ``--pre`` flag for early testing
- **Development versions**: Available by installing from the GitHub repository

**Staying Informed**

To stay informed about new releases:

- Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications
- Join the `LF Energy Slack workspace <https://slack.lfenergy.org/>`_ (#openstef channel)
- Follow announcements on the `LF Energy OpenSTEF project page <https://www.lfenergy.org/projects/openstef/>`_

Contributing to the Changelog
------------------------------

Contributors should follow these guidelines when making changes:

**Commit Message Format**

OpenSTEF uses conventional commits to automatically generate changelog entries. Format your commit messages as:

.. code-block:: text

   <type>[optional scope]: <description>

   [optional body]

   [optional footer(s)]

**Commit Types**

- ``feat``: A new feature for users
- ``fix``: A bug fix
- ``docs``: Documentation only changes
- ``style``: Code formatting changes (no functional changes)
- ``refactor``: Code changes that neither fix bugs nor add features
- ``perf``: Performance improvements
- ``test``: Adding or correcting tests
- ``build``: Changes to build system or dependencies
- ``ci``: Changes to CI configuration
- ``chore``: Other changes that don't modify src or test files

**Breaking Changes**

Indicate breaking changes by adding ``!`` after the type or including ``BREAKING CHANGE:`` in the footer:

.. code-block:: text

   feat!: change model interface to support custom metrics

   BREAKING CHANGE: Model.fit() now requires a metrics parameter

**Examples**

.. code-block:: text

   feat(models): add transformer-based forecasting model

   fix(validation): handle missing weather data gracefully

   docs: update installation guide for uv workspace

   perf(preprocessing): optimize feature engineering pipeline

For more information on contributing, see the :doc:`../contribute/contributing_guide` page.

See Also
--------

- :doc:`../getting_started/installation` - Install OpenSTEF and upgrade to the latest version
- :doc:`../guides/how_to_guides` - Migration guides for upgrading between major versions
- :doc:`architecture` - Understand the modular architecture introduced in 4.0
- `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_ - View detailed release notes and download specific versions