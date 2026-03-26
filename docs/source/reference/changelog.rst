Changelog
=========

This page provides a comprehensive version history of OpenSTEF, combining information from the project's CHANGELOG.md file with GitHub release notes. The changelog follows conventional commit standards and semantic versioning principles.

.. note::
   This page is automatically generated from the project's CHANGELOG.md file and GitHub releases. For the most up-to-date information, visit the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0.0 - Major Architecture Redesign
--------------------------------------------

**Release Date:** 2024

**Breaking Changes:**

- **Complete architectural redesign** - OpenSTEF 4.0 introduces a modular monorepo structure with separate packages
- **Python version requirement** - Now requires Python 3.12+ (dropped support for Python 3.10/3.11)
- **Package structure changes** - Library split into ``openstef-core``, ``openstef-models``, and ``openstef-beam`` packages
- **Import path changes** - Updated import paths to reflect new modular structure
- **Configuration system overhaul** - New configuration mechanisms replace hard-coded assumptions

**New Features:**

- **Modular architecture** - Install only the components you need with independent packages
- **Enhanced type safety** - Full type safety throughout the codebase using modern Python features  
- **Improved extensibility** - Clear interfaces for adding custom models, transforms, and metrics
- **BEAM package** - New backtesting, evaluation, analysis, and metrics package spun out from internal Alliander project
- **Better enterprise integration** - More flexible architecture for complex software landscapes
- **Generalized domain logic** - Support for use cases beyond Netherlands-specific implementations
- **Performance optimizations** - Efficient implementations optimized for production use cases

**Migration Guide:**

Users migrating from OpenSTEF 3.x should:

1. Upgrade to Python 3.12 or higher
2. Update import statements to use new package structure
3. Review configuration changes and update accordingly
4. Test thoroughly as this is a major architectural change

For detailed migration guidance, see the how-to guides section.

Version 3.x Series
------------------

**Version 3.x** represented the mature version of OpenSTEF with stable APIs and proven production use at Alliander with 10,000+ daily forecasts.

**Key Features:**

- Stable forecasting models with proven accuracy
- Production-ready deployment capabilities
- Comprehensive feature engineering pipeline
- Support for multiple forecast horizons
- Weather data integration
- Model explainability features

**Bug Fixes and Improvements:**

The 3.x series included numerous bug fixes, performance improvements, and feature enhancements based on production feedback and community contributions.

Earlier Versions
----------------

**Version 2.x and Earlier:**

Earlier versions of OpenSTEF focused on establishing the core forecasting capabilities and building the foundation for energy forecasting applications. These versions included:

- Initial model implementations
- Basic feature engineering
- Weather data integration
- Core evaluation metrics
- Documentation and examples

Understanding Version Numbers
-----------------------------

OpenSTEF follows `semantic versioning <https://semver.org/>`_ (SemVer):

- **Major versions** (e.g., 3.0.0 → 4.0.0): Breaking changes that require code updates
- **Minor versions** (e.g., 4.0.0 → 4.1.0): New features that are backward compatible  
- **Patch versions** (e.g., 4.1.0 → 4.1.1): Bug fixes and small improvements

**Change Types:**

Following conventional commit standards, changes are categorized as:

- ``feat``: New features for users
- ``fix``: Bug fixes
- ``docs``: Documentation improvements
- ``perf``: Performance improvements
- ``refactor``: Code improvements without functional changes
- ``test``: Test additions or improvements
- ``build``: Build system changes
- ``ci``: CI/CD pipeline changes

Staying Updated
---------------

To stay informed about new releases:

**Subscribe to Releases:**

- Watch the `GitHub repository <https://github.com/OpenSTEF/openstef>`_ for release notifications
- Subscribe to the `releases RSS feed <https://github.com/OpenSTEF/openstef/releases.atom>`_

**Check Your Version:**

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")
   
   # Check for updates
   import subprocess
   result = subprocess.run(["pip", "show", "openstef"], capture_output=True, text=True)
   print(result.stdout)

**Upgrade Process:**

.. code-block:: bash

   # Check current version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef
   
   # Or with uv
   uv upgrade openstef

**Breaking Change Policy:**

- Breaking changes are only introduced in major versions
- Deprecation warnings are provided at least one minor version before removal
- Migration guides are provided for all breaking changes
- Legacy support is maintained where feasible

Contributing to the Changelog
------------------------------

The changelog is automatically generated from:

- **Conventional commits** in the repository following the format: ``<type>[scope]: <description>``
- **GitHub release notes** created by maintainers
- **Pull request descriptions** that follow the project's templates

**For Contributors:**

When contributing to OpenSTEF, ensure your commits follow the conventional commit format to automatically appear in future changelog entries. See the contributing guide for detailed guidelines.

**For Maintainers:**

Release notes are generated using automated tooling that parses commit messages and creates structured changelog entries. The process includes:

1. Automated parsing of conventional commits
2. Categorization by change type and scope
3. Generation of migration notes for breaking changes
4. Integration with GitHub release creation workflow