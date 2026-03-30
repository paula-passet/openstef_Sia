Changelog
=========

This page provides a comprehensive version history of the OpenSTEF library, combining information from the project's CHANGELOG.md file with GitHub release notes. The changelog follows the `conventional commits <https://www.conventionalcommits.org/>`_ specification and tracks breaking changes, new features, bug fixes, and improvements across all OpenSTEF packages.

.. note::
   This page is automatically generated from the project's CHANGELOG.md file and GitHub releases. For the most up-to-date information, visit the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0.0 - Major Architecture Refactor
--------------------------------------------

**Release Date:** 2024

OpenSTEF 4.0.0 represents a complete architectural overhaul of the library, introducing a modular package structure and significant improvements to usability, performance, and extensibility.

Breaking Changes
^^^^^^^^^^^^^^^^

- **Python Version Requirement:** Minimum Python version increased to 3.12
- **Package Structure:** Complete reorganization into separate packages:
  
  - ``openstef-core``: Core utilities and datasets
  - ``openstef-models``: Machine learning models and feature engineering
  - ``openstef-beam``: Backtesting, evaluation, analysis and metrics
  - ``openstef``: Meta-package for easy installation

- **Import Changes:** Package imports have changed to reflect the new structure:

  .. code-block:: python

     # Old (v3.x)
     from openstef.model import forecasting
     from openstef.validation import validation
     
     # New (v4.x)
     from openstef_models import forecasting
     from openstef_beam import evaluation

- **Configuration System:** Hard-coded assumptions replaced with flexible configuration mechanisms
- **External Dependencies:** Decoupled MLFlow, openstef-dbc, and other external dependencies for improved modularity

New Features
^^^^^^^^^^^^

- **Modular Architecture:** Components can now work in isolation and be easily composed into larger systems
- **Type Safety:** Full type safety throughout the codebase using modern Python type hints
- **Extensibility:** Clear interfaces for adding custom models, transforms, and metrics without modifying core code
- **Performance Optimizations:** Efficient implementations optimized for production use cases
- **Enhanced Documentation:** Comprehensive documentation following the Diátaxis framework
- **Flexible Data Formats:** Relaxed rigid input data constraints to support more diverse data structures
- **Generalized Domain Logic:** Support for use cases beyond the Netherlands (customizable holiday calendars, dynamic pricing)

Improvements
^^^^^^^^^^^^

- **Test Coverage:** Significantly increased test coverage across all packages
- **Code Quality:** Standardized coding practices and documentation styles
- **Data Preprocessing:** Centralized data preprocessing logic to reduce duplication
- **Configuration Management:** Flexible configuration mechanisms replace hard-coded assumptions
- **Error Handling:** Improved error messages and exception handling throughout the library

Migration Guide
^^^^^^^^^^^^^^^

Users migrating from OpenSTEF 3.x should:

1. **Update Python Version:** Ensure Python 3.12+ is installed
2. **Update Installation:** Use the new package structure:

   .. code-block:: bash

      # Complete installation
      pip install "openstef[all]"
      
      # Or install specific packages
      pip install openstef-models openstef-beam

3. **Update Imports:** Modify import statements to use the new package structure
4. **Review Configuration:** Update any hard-coded configurations to use the new flexible system
5. **Test Thoroughly:** The architectural changes may affect existing workflows

For detailed migration assistance, see the :doc:`../guides/how_to_guides` page.

Version 3.x Series
------------------

**Note:** Version 3.x series documentation is maintained for reference but is no longer actively developed. Users are encouraged to migrate to version 4.0+ for the latest features and improvements.

Version 3.2.0
^^^^^^^^^^^^^^

- **Features:** Enhanced model validation and improved forecasting accuracy
- **Bug Fixes:** Resolved issues with weather data handling and missing value imputation
- **Improvements:** Performance optimizations for large datasets

Version 3.1.0
^^^^^^^^^^^^^^

- **Features:** Added support for additional model types and improved feature engineering
- **Bug Fixes:** Fixed edge cases in data preprocessing and model training
- **Improvements:** Enhanced documentation and example notebooks

Version 3.0.0
^^^^^^^^^^^^^^

- **Breaking Changes:** Restructured API for better consistency
- **Features:** Introduced new forecasting models and evaluation metrics
- **Improvements:** Significant performance improvements and code quality enhancements

Release Process and Versioning
-------------------------------

OpenSTEF follows `semantic versioning <https://semver.org/>`_ (SemVer) with the following conventions:

- **Major versions** (e.g., 3.0.0 → 4.0.0): Breaking changes that require code modifications
- **Minor versions** (e.g., 4.0.0 → 4.1.0): New features that are backward compatible
- **Patch versions** (e.g., 4.1.0 → 4.1.1): Bug fixes and small improvements

Commit Message Format
^^^^^^^^^^^^^^^^^^^^^^

The project uses conventional commits for automated changelog generation:

.. code-block:: text

   <type>[optional scope]: <description>
   
   [optional body]
   
   [optional footer(s)]

**Types:**

- ``feat``: New features
- ``fix``: Bug fixes
- ``docs``: Documentation changes
- ``style``: Code formatting changes
- ``refactor``: Code refactoring
- ``perf``: Performance improvements
- ``test``: Test additions or modifications
- ``build``: Build system changes
- ``ci``: CI/CD changes
- ``chore``: Other maintenance tasks

Getting Release Notifications
------------------------------

To stay updated with new releases:

1. **GitHub Releases:** Subscribe to the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_
2. **Package Managers:** Use your package manager's update notifications:

   .. code-block:: bash

      # Check current version
      pip show openstef
      
      # Upgrade to latest
      pip install --upgrade openstef

3. **Community Channels:** Join the `LF Energy Slack workspace <https://slack.lfenergy.org/>`_ (#openstef channel) for release announcements

Contributing to Releases
-------------------------

The OpenSTEF project welcomes contributions to improve the library. For information about contributing to releases:

- Review the :doc:`../contribute/contributing_guide` for development workflow
- Check the `GitHub issues <https://github.com/OpenSTEF/openstef/issues>`_ for planned features
- Join the community meetings to discuss upcoming releases

.. note::
   This changelog is automatically updated with each release. For the most current information and to report issues, visit the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_.