Changelog
=========

This page documents the version history of OpenSTEF, including new features, improvements, bug fixes, and breaking changes for each release. OpenSTEF follows `semantic versioning <https://semver.org/>`_ (MAJOR.MINOR.PATCH).

For detailed migration instructions when upgrading between major versions, see the :doc:`user_guide/migration_guide`.

Version 4.0.0 (2025)
--------------------

**Major architectural refactor** - OpenSTEF 4.0 represents a complete redesign focused on modularity, type safety, and broader applicability beyond the original Dutch DSO use case.

Breaking Changes
^^^^^^^^^^^^^^^^

- **Modular package structure**: OpenSTEF is now split into separate packages (``openstef-core``, ``openstef-models``, ``openstef-metrics``) that can be installed independently
- **Decoupled external dependencies**: MLFlow, database connectors, and specific model implementations are no longer required dependencies
- **New configuration system**: Hard-coded assumptions replaced with flexible configuration using Pydantic models
- **Versioned datasets**: Introduction of ``VersionedTimeSeriesDataset`` with explicit data availability tracking
- **Transform pipeline redesign**: New transform base classes with versioned state management for reproducible pipelines
- **Removed legacy validation**: Old validation logic consolidated into cleaner preprocessing transforms
- **API changes**: Many function signatures updated for type safety and clarity

.. warning::
   Version 4.0 is **not backward compatible** with 3.x. Existing code will require updates. See the :doc:`user_guide/migration_guide` for step-by-step migration instructions.

New Features
^^^^^^^^^^^^

**Core Architecture**

- **Versioned state management**: All stateful components now support versioning with automatic migration between versions
- **Type-safe throughout**: Complete type annotations with strict type checking enabled
- **Extensible interfaces**: Clear base classes for custom models, transforms, and metrics
- **Modular design**: Components work in isolation and compose cleanly into larger systems

**Dataset Management**

- **VersionedTimeSeriesDataset**: Track multiple versions of data with different availability times, enabling automatic selection of appropriate data quality for different forecast horizons
- **Data availability constraints**: Explicit modeling of when data becomes available, preventing look-ahead bias
- **Flexible data formats**: Relaxed rigid input requirements to support diverse data structures

**Transform System**

- **VersionedLagsAdder**: Create lag features while preserving data availability constraints across versioned datasets
- **Pipeline composition**: Easily chain transforms with automatic state management
- **Custom transforms**: Simple interface for adding domain-specific preprocessing

**Model Support**

- **Model-agnostic framework**: Support for any scikit-learn compatible model
- **Quantile forecasting**: Built-in support for probabilistic forecasts
- **Component models**: Split forecasts into components (e.g., solar, wind, base load)

**Documentation**

- **Diátaxis framework**: Complete documentation restructure following best practices (tutorials, how-to guides, reference, explanation)
- **Comprehensive examples**: Working code examples for common forecasting scenarios
- **Clear library positioning**: Emphasis that OpenSTEF is a library, not a deployable application

Improvements
^^^^^^^^^^^^

- **Test coverage**: Significantly increased test coverage with streamlined execution
- **Performance optimizations**: Efficient implementations for production workloads
- **Better error messages**: Clear, actionable error messages with context
- **Standardized code style**: Consistent formatting and documentation across codebase
- **Reduced duplication**: Centralized preprocessing logic eliminates redundancy

Use Case Expansion
^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 is designed to support diverse energy forecasting applications:

- **Congestion management**: Accuracy near peak loads for substation and customer-level forecasts
- **Transport forecasts**: Reliable predictions for grid capacity planning and coordination
- **Grid losses**: Cost-weighted optimization considering market prices
- **District heating**: Thermal demand forecasting (initial support)
- **Custom domains**: Flexible enough to adapt to new energy forecasting scenarios

Version 3.x Series
------------------

Version 3.0.0
^^^^^^^^^^^^^

The 3.x series represented the production-ready version of OpenSTEF used by Alliander and other Dutch grid operators.

**Key Features**

- XGBoost-based forecasting models
- MLFlow integration for experiment tracking
- Database connectors for operational deployment
- Validation and preprocessing pipelines
- Dutch holiday calendar and domain-specific logic
- Quantile regression support

**Known Limitations**

- Tightly coupled to specific deployment environment
- Hard-coded assumptions for Dutch DSO use case
- Limited extensibility for custom models
- Rigid input data requirements
- Validation and preprocessing logic duplicated across components

Version 2.x Series
------------------

Early development versions with basic forecasting capabilities. Not recommended for production use.

Release Schedule
----------------

OpenSTEF releases follow a predictable schedule:

- **Major versions** (X.0.0): Architectural changes, breaking API updates - as needed
- **Minor versions** (4.X.0): New features, non-breaking enhancements - quarterly
- **Patch versions** (4.0.X): Bug fixes, documentation updates - as needed

Staying Updated
---------------

To check your current version and upgrade:

.. code-block:: bash

   # Check current version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef
   
   # Install specific version
   pip install openstef==4.0.0

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions.

Deprecation Policy
------------------

OpenSTEF follows these deprecation guidelines:

1. **Deprecation warnings**: Features marked for removal will emit warnings for at least one minor version before removal
2. **Migration guides**: Breaking changes include detailed migration instructions
3. **Compatibility period**: Critical bug fixes backported to previous major version for 6 months after new major release
4. **Clear communication**: Deprecations announced in release notes, documentation, and runtime warnings

Contributing to Releases
-------------------------

OpenSTEF uses `Conventional Commits <https://www.conventionalcommits.org/>`_ for automated changelog generation:

.. code-block:: text

   <type>[optional scope]: <description>
   
   [optional body]
   
   [optional footer(s)]

**Commit Types**

- ``feat``: New feature for users
- ``fix``: Bug fix
- ``docs``: Documentation changes
- ``refactor``: Code changes that neither fix bugs nor add features
- ``perf``: Performance improvements
- ``test``: Test additions or corrections
- ``build``: Build system or dependency changes
- ``ci``: CI configuration changes
- ``chore``: Other changes that don't modify src or test files

**Examples**

.. code-block:: bash

   # New feature
   git commit -m "feat(models): add transformer-based forecasting model"
   
   # Bug fix with details
   git commit -m "fix(validation): handle missing weather data gracefully
   
   Previously the validation would crash when weather data was missing.
   Now it logs a warning and continues with available features.
   
   Fixes #456"
   
   # Breaking change
   git commit -m "feat!: redesign transform pipeline API
   
   BREAKING CHANGE: Transform base class signature changed"

Breaking changes are indicated with ``!`` after the type or a ``BREAKING CHANGE:`` footer.

See Also
--------

- :doc:`user_guide/migration_guide` - Step-by-step migration instructions between major versions
- :doc:`user_guide/installation` - Installation instructions for different environments
- `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_ - Detailed release notes and downloads