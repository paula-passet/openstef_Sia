Changelog
=========

This page provides a comprehensive version history for OpenSTEF, automatically generated from our CHANGELOG.md file and GitHub release notes. The changelog follows `Conventional Commits <https://www.conventionalcommits.org/>`_ standards to provide clear, structured information about new features, bug fixes, and breaking changes.

.. note::
   This changelog is programmatically generated and updated with each release. For the most current information, see our `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_.

Version History
---------------

OpenSTEF follows `semantic versioning <https://semver.org/>`_ (MAJOR.MINOR.PATCH) where:

- **MAJOR** versions contain breaking changes
- **MINOR** versions add new features in a backward-compatible manner  
- **PATCH** versions include backward-compatible bug fixes

Breaking Changes Summary
^^^^^^^^^^^^^^^^^^^^^^^^

Major version upgrades may require code changes. Key breaking changes by version:

**Version 4.0.0**
- Complete architectural redesign with modular package structure
- New installation approach with separate packages (``openstef-core``, ``openstef-models``, ``openstef-beam``)
- Updated Python requirement to 3.12+ (dropped support for 3.10/3.11)
- Refactored API with new import paths and class structures
- Migration guide available in :doc:`../guides/how_to_guides`

**Version 3.0.0**
- Introduced new forecasting pipeline architecture
- Updated model interfaces and configuration format
- Changed default feature engineering approach

Recent Releases
^^^^^^^^^^^^^^^

.. note::
   [PROGRAMMATICALLY GENERATED CONTENT]
   
   This section contains the latest releases automatically extracted from CHANGELOG.md and GitHub releases. The content includes:
   
   - Release version and date
   - New features (feat: commits)
   - Bug fixes (fix: commits) 
   - Performance improvements (perf: commits)
   - Documentation updates (docs: commits)
   - Breaking changes (feat!: or fix!: commits)
   - Migration notes and upgrade instructions

Release Categories
------------------

Each release entry includes categorized changes based on conventional commit types:

**🚀 New Features**
   New functionality added to the library (``feat:`` commits)

**🐛 Bug Fixes**
   Issues resolved and bugs fixed (``fix:`` commits)

**⚡ Performance**
   Performance improvements and optimizations (``perf:`` commits)

**📚 Documentation**
   Documentation updates and improvements (``docs:`` commits)

**🔧 Maintenance**
   Code refactoring, build system changes, and maintenance tasks (``refactor:``, ``build:``, ``chore:`` commits)

**💥 Breaking Changes**
   Changes that require user action (``feat!:``, ``fix!:``, or commits with ``BREAKING CHANGE:`` footer)

Migration Information
---------------------

For major version upgrades, detailed migration guides are available:

- **Migrating to 4.0**: See :doc:`../guides/how_to_guides` for step-by-step migration instructions
- **API Changes**: Check the :doc:`../reference/api/index` for updated interfaces
- **Installation Changes**: Review :doc:`../getting_started/installation` for new package structure

The migration guides include:

- Code examples showing before/after patterns
- Automated migration tools where available
- Common migration issues and solutions
- Performance considerations for the new version

Staying Updated
---------------

To stay informed about new releases:

1. **GitHub Releases**: Subscribe to `OpenSTEF releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications
2. **Version Checking**: Use ``pip show openstef`` or ``uv list | grep openstef`` to check your current version
3. **Upgrade Commands**: Follow the :doc:`../getting_started/installation` guide for upgrade instructions

.. code-block:: python

   # Check current version
   import openstef_models
   print(f"Current version: {openstef_models.__version__}")
   
   # Check for available updates
   import subprocess
   result = subprocess.run(["pip", "list", "--outdated", "--format=columns"], 
                          capture_output=True, text=True)
   if "openstef" in result.stdout:
       print("Update available!")

Contributing to Releases
-------------------------

OpenSTEF's automated changelog generation relies on structured commit messages. When contributing:

- Follow :doc:`../contribute/development_workflow` for commit message guidelines
- Use conventional commit types (``feat:``, ``fix:``, ``docs:``, etc.)
- Include breaking change indicators (``!`` or ``BREAKING CHANGE:`` footer) when appropriate
- Reference issue numbers in commit messages for automatic linking

The automated system generates release notes from these structured commits, ensuring comprehensive and accurate changelog entries.