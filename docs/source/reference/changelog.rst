Changelog
=========

This page provides a comprehensive history of OpenSTEF releases, combining information from the project's CHANGELOG.md file with GitHub release notes. The changelog follows the `Conventional Commits <https://www.conventionalcommits.org/>`_ specification for clear, structured release documentation.

.. note::
   This page is automatically generated from the project's CHANGELOG.md file and GitHub releases. For the most up-to-date information, visit the `OpenSTEF releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0 Series
------------------

Version 4.0.0 (Upcoming Stable Release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Release Status:** In Development

OpenSTEF 4.0 represents a major architectural redesign focused on modularity, type safety, and enterprise integration. This release breaks compatibility with 3.x versions but provides significant improvements in flexibility and maintainability.

**Major Changes:**

- **Modular Architecture:** Complete restructure into specialized packages (openstef-core, openstef-models, openstef-beam)
- **Python 3.12+ Requirement:** Modern type safety features and performance optimizations
- **Breaking API Changes:** New interfaces for models, data handling, and configuration
- **Enhanced Documentation:** Comprehensive guides following the Diátaxis framework

**New Features:**

- ``feat(models)``: Transformer-based forecasting models with attention mechanisms
- ``feat(core)``: Flexible configuration system replacing hard-coded assumptions
- ``feat(beam)``: Enhanced backtesting and evaluation framework
- ``feat(api)``: Modular component interfaces for custom implementations

**Breaking Changes:**

- ``feat!``: New package structure requires import path updates
- ``feat!``: Configuration format changes for model parameters
- ``feat!``: Data preprocessing pipeline restructured
- ``feat!``: MLflow integration decoupled for optional use

**Bug Fixes:**

- ``fix(validation)``: Handle missing weather data gracefully
- ``fix(models)``: Improve memory efficiency for large datasets
- ``fix(core)``: Resolve timezone handling inconsistencies

**Migration Guide:**

See the :doc:`../guides/how_to_guides` for detailed migration instructions from OpenSTEF 3.x to 4.0.

Version 4.0.0-alpha (Current)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Release Date:** 2024

**Status:** Alpha - Production use at Alliander with 10,000+ daily forecasts

This alpha release introduces the new modular architecture and is currently being tested in production environments.

**Key Features:**

- Modular package design with independent installation options
- Type-safe interfaces throughout the codebase
- Improved performance and memory efficiency
- Enhanced extensibility for custom models and transforms

**Known Limitations:**

- Documentation still in development
- Some advanced features from 3.x not yet ported
- API may change before stable release

Version 3.x Series (Legacy)
---------------------------

Version 3.x releases are now in maintenance mode. Users are encouraged to migrate to OpenSTEF 4.0 for new projects.

**Final 3.x Features:**

- Established forecasting pipeline with XGBoost models
- MLflow integration for experiment tracking
- Support for various energy forecasting use cases
- Production-tested at multiple grid operators

Understanding Version Numbers
-----------------------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_:

- **Major versions** (4.0.0): Breaking changes, new architecture
- **Minor versions** (4.1.0): New features, backward compatible
- **Patch versions** (4.0.1): Bug fixes, backward compatible

**Pre-release Identifiers:**

- ``alpha``: Early development, API may change significantly
- ``beta``: Feature-complete, API stabilizing
- ``rc`` (release candidate): Final testing before stable release

Release Process
---------------

OpenSTEF releases follow a structured process:

1. **Development:** Features developed in feature branches
2. **Alpha/Beta:** Pre-release versions for testing
3. **Release Candidate:** Final validation before stable release
4. **Stable Release:** Production-ready version with full documentation

**Commit Message Format:**

All changes follow the Conventional Commits specification:

.. code-block:: text

   <type>[optional scope]: <description>
   
   [optional body]
   
   [optional footer(s)]

**Common Types:**

- ``feat``: New features
- ``fix``: Bug fixes
- ``docs``: Documentation changes
- ``refactor``: Code improvements without functional changes
- ``perf``: Performance improvements
- ``test``: Test additions or corrections

Breaking Changes
----------------

Breaking changes are marked with ``!`` in commit messages and clearly documented in release notes. Major version bumps (3.x → 4.x) indicate significant breaking changes that require code updates.

**Migration Support:**

- Detailed migration guides for major version transitions
- Compatibility layers where possible
- Community support during transition periods

Staying Updated
---------------

To stay informed about OpenSTEF releases:

- **GitHub Releases:** Subscribe to `repository notifications <https://github.com/OpenSTEF/openstef/releases>`_
- **Community:** Join the `LF Energy Slack <https://slack.lfenergy.org/>`_ (#openstef channel)
- **Mailing List:** Contact openstef@lfenergy.org for announcements

**Checking Your Version:**

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models: {openstef_models.__version__}")
   
   # For complete installation
   import openstef_beam
   print(f"OpenSTEF BEAM: {openstef_beam.__version__}")

**Upgrading:**

.. code-block:: bash

   # Upgrade to latest stable version
   pip install --upgrade openstef
   
   # Or with uv
   uv upgrade openstef

Contributing to Releases
------------------------

The OpenSTEF community welcomes contributions to releases:

- **Bug Reports:** Help identify issues for patch releases
- **Feature Requests:** Suggest improvements for minor releases
- **Code Contributions:** Submit pull requests following our :doc:`../contribute/contributing_guide`
- **Testing:** Participate in alpha/beta testing programs

For detailed contribution guidelines, see our :doc:`../contribute/index` section.