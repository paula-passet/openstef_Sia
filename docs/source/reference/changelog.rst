Changelog
=========

This page contains the complete version history of OpenSTEF, including all releases, features, bug fixes, and breaking changes. The changelog is automatically generated from the project's CHANGELOG.md file and GitHub release notes.

OpenSTEF follows `semantic versioning <https://semver.org/>`_: MAJOR.MINOR.PATCH where:

- **MAJOR** version changes indicate breaking changes that require code modifications
- **MINOR** version changes add functionality in a backward-compatible manner
- **PATCH** version changes include backward-compatible bug fixes

.. note::

   OpenSTEF 4.0 introduced a major architectural change to a modular package structure. See the :doc:`../guides/how_to_guides` for migration guidance from version 3.x to 4.x.

Version History
---------------

The complete changelog is maintained in the project repository and includes detailed information about each release:

- **New features** - Enhancements and new capabilities added to the library
- **Bug fixes** - Corrections to existing functionality
- **Breaking changes** - Changes that require updates to existing code
- **Deprecations** - Features marked for removal in future versions
- **Performance improvements** - Optimizations and efficiency enhancements
- **Documentation updates** - Improvements to guides, examples, and API documentation

.. note::

   [PROGRAMMATIC CONTENT: This section is automatically populated from CHANGELOG.md and GitHub releases during documentation build. The content includes all version entries with their respective changes organized by type (feat, fix, docs, refactor, perf, test, build, ci, chore).]

Recent Releases
---------------

Major Version 4.0
^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 represents a significant architectural evolution with a modular package structure:

**Breaking Changes:**

- Requires Python 3.12 or higher (Python 3.13 supported)
- Restructured into separate packages: ``openstef-core``, ``openstef-models``, ``openstef-beam``
- Import paths changed to use package-specific namespaces (e.g., ``from openstef_models import forecasting``)
- Meta-package ``openstef`` provides convenient installation of core components

**New Features:**

- Modular architecture allows installing only needed components
- Improved type safety with modern Python features
- Enhanced performance optimizations
- Flexible installation options with extras (``[all]``, ``[beam]``, ``[foundational-models]``)

**Migration:**

See :doc:`../guides/how_to_guides` for detailed migration instructions from version 3.x.

Understanding Change Types
--------------------------

OpenSTEF uses `conventional commits <https://www.conventionalcommits.org/>`_ to categorize changes:

- ``feat`` - New features for users of the library
- ``fix`` - Bug fixes that correct existing functionality
- ``docs`` - Documentation-only changes
- ``refactor`` - Code changes that neither fix bugs nor add features
- ``perf`` - Performance improvements
- ``test`` - Test additions or corrections
- ``build`` - Build system or dependency changes
- ``ci`` - Continuous integration configuration changes
- ``chore`` - Maintenance tasks that don't modify source or test files

Changes marked with ``!`` (e.g., ``feat!``) or containing ``BREAKING CHANGE`` in the footer indicate breaking changes that require user action.

Staying Updated
---------------

To upgrade to the latest version:

**Using pip:**

.. code-block:: bash

   # Check current version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef

**Using uv:**

.. code-block:: bash

   # Check current version
   uv list | grep openstef
   
   # Upgrade to latest version
   uv upgrade openstef

**Using conda:**

.. code-block:: bash

   # Check current version
   conda list openstef
   
   # Upgrade to latest version
   conda update openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ to receive notifications about new versions, features, and important updates.

Reporting Issues
----------------

If you encounter issues with a specific version:

1. Check the changelog to see if the issue is already addressed in a newer version
2. Search the `GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_ for existing reports
3. Submit a new issue with version information and reproduction steps

See the :doc:`../contribute/contributing_guide` for detailed guidance on reporting bugs and requesting features.

Release Schedule
----------------

OpenSTEF follows a continuous delivery model with releases published as features and fixes are completed. Major versions are planned when significant architectural changes or breaking changes are necessary.

- **Patch releases** - Published as needed for bug fixes
- **Minor releases** - Published when new features are ready
- **Major releases** - Published when breaking changes are necessary

All releases undergo thorough testing and review before publication. Development builds are available from the main branch for early testing of upcoming features.