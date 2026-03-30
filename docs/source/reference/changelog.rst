Changelog
=========

This page documents the complete version history of OpenSTEF, combining information from the project's CHANGELOG.md file with GitHub release notes. The changelog follows the `Keep a Changelog <https://keepachangelog.com/>`_ format and uses `Semantic Versioning <https://semver.org/>`_.

.. note::
   This page is automatically generated from the project's CHANGELOG.md file and GitHub releases. For the most up-to-date information, visit the `OpenSTEF GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0.0 - Major Architecture Refactor
--------------------------------------------

**Release Date:** TBD

OpenSTEF 4.0 represents a complete architectural overhaul of the library, introducing a modular design that allows users to install only the components they need.

Breaking Changes
^^^^^^^^^^^^^^^^

- **Python Version Requirement:** OpenSTEF 4.0 requires Python 3.12 or higher
- **Package Structure:** Complete reorganization into separate packages:
  
  - ``openstef-core``: Shared utilities and dataset types
  - ``openstef-models``: Core forecasting functionality
  - ``openstef-beam``: Backtesting and evaluation tools
  - ``openstef``: Meta-package for convenient installation

- **Import Changes:** Package imports have changed to reflect the new structure:

.. code-block:: python

   # OpenSTEF 4.0
   from openstef_models import forecasting
   from openstef_beam import evaluation
   
   # Not: from openstef.models import forecasting

- **Configuration System:** Hard-coded assumptions replaced with flexible configuration mechanisms
- **External Dependencies:** Decoupled MLFlow, openstef-dbc, and other external dependencies for improved modularity

New Features
^^^^^^^^^^^^

- **Modular Architecture:** Install only the components you need for your use case
- **Enhanced Type Safety:** Full type safety throughout the codebase
- **Improved Extensibility:** Clear interfaces for adding custom models, transforms, and metrics
- **Better Documentation:** Comprehensive documentation following the Diátaxis framework
- **Performance Optimizations:** Efficient implementations optimized for production use cases

Migration Guide
^^^^^^^^^^^^^^^

Users migrating from OpenSTEF 3.x should:

1. **Update Python Version:** Ensure you're using Python 3.12 or higher
2. **Update Installation:** Choose the appropriate package(s) for your use case:

.. code-block:: bash

   # For most users (equivalent to old openstef)
   pip install openstef
   
   # For complete functionality
   pip install "openstef[all]"
   
   # For specific components only
   pip install openstef-models  # Core forecasting only
   pip install openstef-beam    # Evaluation tools only

3. **Update Imports:** Modify import statements to use the new package structure
4. **Review Configuration:** Update any hard-coded configurations to use the new flexible system

For detailed migration instructions, see the :doc:`../guides/how_to_guides` page.

Previous Versions
-----------------

Version 3.x Series
^^^^^^^^^^^^^^^^^^

OpenSTEF 3.x was the stable release series that established the library's core forecasting capabilities and gained widespread adoption in the energy sector.

**Key Features:**
- Comprehensive forecasting models for energy applications
- Integration with MLFlow for experiment tracking
- Support for various data sources and formats
- Established API patterns and conventions

**Supported Python Versions:** Python 3.10, 3.11

.. note::
   OpenSTEF 3.x is now in maintenance mode. Users are encouraged to migrate to 4.0 for new projects and long-term support.

Version 2.x and Earlier
^^^^^^^^^^^^^^^^^^^^^^^

Earlier versions of OpenSTEF focused on establishing the foundational forecasting capabilities and proving the concept in production environments.

For complete historical information about all releases, including detailed changelogs for each version, please visit the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Release Process
---------------

OpenSTEF follows a structured release process:

**Version Numbering**
- **Major versions** (e.g., 3.0 → 4.0): Breaking changes, architectural updates
- **Minor versions** (e.g., 4.0 → 4.1): New features, backward compatible
- **Patch versions** (e.g., 4.1.0 → 4.1.1): Bug fixes, security updates

**Release Types**
- **Stable releases**: Fully tested and recommended for production use
- **Release candidates**: Pre-release versions for testing and feedback
- **Development releases**: Snapshot builds for early testing

**Staying Updated**

To stay informed about new releases:

- Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_
- Join the `LF Energy Slack workspace <https://slack.lfenergy.org/>`_ (#openstef channel)
- Follow the project on `PyPI <https://pypi.org/project/openstef/>`_

**Upgrading**

Check your current version and upgrade using your preferred package manager:

.. code-block:: bash

   # Check current version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef

For major version upgrades, always review the breaking changes section and migration guides before upgrading production systems.