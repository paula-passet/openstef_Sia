Changelog
=========

This page documents the version history of OpenSTEF, including new features, bug fixes, breaking changes, and deprecations for each release. OpenSTEF follows `semantic versioning <https://semver.org/>`_ (MAJOR.MINOR.PATCH).

For detailed migration instructions when upgrading between major versions, see the :doc:`migration_guide` in the user guide.

Version 4.0.0 (2025-01-15)
--------------------------

OpenSTEF 4.0 represents a major architectural redesign of the library, introducing a modular package structure, improved type safety, and enhanced forecasting capabilities. This release requires Python 3.12+ and includes several breaking changes from the 3.x series.

Breaking Changes
^^^^^^^^^^^^^^^^

**Modular Package Architecture**

OpenSTEF has been restructured into separate, independently installable packages:

- ``openstef-core``: Core utilities, datasets, and base classes
- ``openstef-models``: Forecasting models and pipelines
- ``openstef-beam``: Backtesting and evaluation tools
- ``openstef``: Meta-package that bundles core components

**Migration impact:** Update your imports to use the new package names:

.. code-block:: python

   # Old (v3.x)
   from openstef.model import forecasting
   from openstef.validation import validation
   
   # New (v4.0)
   from openstef_models import forecasting
   from openstef_beam import evaluation

**Python Version Requirement**

- Minimum Python version increased from 3.10 to 3.12
- Python 3.13 is now officially supported
- Improved type safety using modern Python features

**State Versioning System**

All stateful objects now implement versioned serialization with automatic migration:

.. code-block:: python

   # Models automatically handle version migrations
   from openstef_models.model.serializer import MLflowSerializer
   
   # Load a model saved with an older version
   model = MLflowSerializer.load("path/to/model")
   # Automatic migration with warnings if version mismatch detected

**Dataset API Changes**

The dataset classes have been redesigned with clearer semantics:

- ``TimeSeriesDataset``: For regular time series without versioning
- ``VersionedTimeSeriesDataset``: For time series with data availability tracking
- New properties: ``sample_interval``, ``feature_names``, ``is_versioned``

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # New API with explicit versioning support
   dataset = VersionedTimeSeriesDataset(data, timestamp_col="timestamp")
   
   # Access metadata
   print(dataset.sample_interval)  # timedelta object
   print(dataset.feature_names)    # List of feature columns
   print(dataset.is_versioned)     # True for versioned datasets

New Features
^^^^^^^^^^^^

**Versioned Lag Features**

New transform for creating lag features while preserving data availability constraints:

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder
   from datetime import timedelta
   
   # Create lag features that respect data availability
   lag_transform = VersionedLagsAdder(
       lags=[timedelta(hours=1), timedelta(hours=24)],
       columns=["load", "temperature"]
   )
   
   transformed_data = lag_transform.fit_transform(dataset)

**Enhanced Model Serialization**

Improved MLflow integration with better metadata tracking:

- Automatic version migration for backward compatibility
- Enhanced model metadata and lineage tracking
- Support for custom serialization strategies

**Improved Type Safety**

- Full type hints throughout the codebase
- Pydantic-based configuration validation
- Better IDE support and autocomplete

**Modern Build System**

- Migration to ``uv`` for dependency management
- Faster installation and dependency resolution
- Improved reproducibility with lock files

Improvements
^^^^^^^^^^^^

**Performance**

- Optimized dataset operations for large time series
- Reduced memory footprint in transform pipelines
- Faster model training with improved data handling

**Documentation**

- Comprehensive restructuring with clearer navigation
- New tutorials and examples for v4 API
- Enhanced API reference with type information
- Migration guide for upgrading from v3.x

**Developer Experience**

- Simplified development setup with ``uv sync``
- Pre-commit hooks for code quality
- Improved test coverage and CI/CD pipeline
- Better error messages and validation

**Installation Options**

Flexible installation based on use case:

.. code-block:: bash

   # Complete installation
   pip install "openstef[all]"
   
   # Core models only
   pip install openstef-models
   
   # Models + evaluation tools
   pip install "openstef[beam]"

Bug Fixes
^^^^^^^^^

- Fixed edge cases in time series alignment
- Improved handling of missing weather data
- Corrected timezone handling in dataset operations
- Fixed memory leaks in long-running forecasting pipelines

Deprecations
^^^^^^^^^^^^

- Legacy import paths from v3.x are no longer supported
- Python 3.10 and 3.11 are no longer supported (use v3.x for these versions)
- Old-style configuration dictionaries (use Pydantic models instead)

Version 3.x Series
------------------

The 3.x series was the last version to support Python 3.10 and 3.11. For users who cannot upgrade to Python 3.12+, we recommend staying on the latest 3.x release.

**Key features of 3.x:**

- Monolithic package structure
- Support for Python 3.10, 3.11
- Traditional configuration approach
- Established forecasting models and pipelines

For detailed 3.x release notes, see the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 2.x Series
------------------

The 2.x series introduced several foundational features that remain in OpenSTEF today:

- Core forecasting models (XGBoost, LightGBM, linear models)
- Feature engineering pipeline
- Model validation and evaluation framework
- Integration with MLflow for model tracking

Version 2.x is no longer maintained. Users should upgrade to 4.x for the latest features and security updates.

Version 1.x Series
------------------

The initial public release of OpenSTEF, providing:

- Basic forecasting capabilities for energy systems
- Time series data handling
- Model training and prediction interfaces
- Initial documentation and examples

Version 1.x is no longer maintained.

Release Cadence
---------------

OpenSTEF follows a regular release schedule:

- **Major releases** (x.0.0): Approximately annually, may include breaking changes
- **Minor releases** (4.x.0): Every 2-3 months, backward-compatible new features
- **Patch releases** (4.0.x): As needed for bug fixes and security updates

Staying Updated
---------------

To stay informed about new releases:

1. **GitHub Releases**: Subscribe to `OpenSTEF releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications
2. **Upgrade regularly**: Check for updates and review release notes before upgrading

.. code-block:: bash

   # Check your current version
   pip show openstef
   
   # Upgrade to the latest version
   pip install --upgrade openstef

3. **Breaking changes**: Always review breaking changes before upgrading major versions
4. **Migration guide**: Consult the :doc:`migration_guide` when upgrading between major versions

Contributing to Releases
-------------------------

OpenSTEF uses `Conventional Commits <https://www.conventionalcommits.org/>`_ to automatically generate release notes:

- ``feat``: New features (minor version bump)
- ``fix``: Bug fixes (patch version bump)
- ``feat!`` or ``fix!``: Breaking changes (major version bump)
- ``docs``, ``style``, ``refactor``, ``perf``, ``test``, ``build``, ``ci``, ``chore``: Other changes

Example commit messages:

.. code-block:: bash

   # New feature
   git commit -m "feat(models): add transformer-based forecasting model"
   
   # Bug fix with detailed description
   git commit -m "fix(validation): handle missing weather data gracefully
   
   Previously the validation would crash when weather data was missing.
   Now it logs a warning and continues with available features.
   
   Fixes #456"
   
   # Breaking change
   git commit -m "feat!: redesign dataset API for better type safety
   
   BREAKING CHANGE: Dataset constructors now require explicit column names"

For more information on contributing, see the :doc:`../contribute/development_workflow` guide.

Support for Older Versions
---------------------------

**Version 4.x**: Active development and support

**Version 3.x**: Security fixes only until 2026-01-01

**Version 2.x and earlier**: No longer supported

If you're using an older version, we strongly recommend upgrading to 4.x to receive the latest features, performance improvements, and security updates. See the :doc:`migration_guide` for upgrade instructions.