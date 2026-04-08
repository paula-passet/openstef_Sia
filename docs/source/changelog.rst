Changelog
=========

This page documents the version history of OpenSTEF, a Python machine learning library for short-term energy forecasting. Each release includes new features, improvements, bug fixes, and breaking changes.

OpenSTEF follows `semantic versioning <https://semver.org/>`_. For detailed migration instructions when upgrading between major versions, see the :doc:`user_guide/migration_guide`.

.. note::
   Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions and features.

Version 4.0 (Alpha)
-------------------

**Release Date:** In Development

OpenSTEF 4.0 represents a complete architectural redesign focused on modularity, flexibility, and enterprise integration. This major release transforms OpenSTEF from a monolithic package into a modular mono-repo with multiple self-contained packages.

Breaking Changes
^^^^^^^^^^^^^^^^

**Modular Package Structure**

OpenSTEF V4 splits the library into specialized packages:

- **openstef-core**: Data types, interfaces, base classes, and shared utilities
- **openstef-models**: Forecasting models, preprocessing pipelines, and transformations
- **openstef-meta**: Meta-learning and ensemble models
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics
- **openstef-viz**: Visualization tools for forecasting results

Applications built on V3 must be refactored to use the new package structure. See :doc:`user_guide/migration_guide` for step-by-step migration instructions.

**Decoupled External Dependencies**

V4 removes hard-coded dependencies on MLFlow, openstef-dbc, and specific model implementations. Users now have full control over:

- Model registry and experiment tracking systems
- Database connections and data sources
- Model selection and configuration

**Flexible Data Formats**

V3's rigid input data constraints have been relaxed. V4 supports:

- Custom holiday calendars (no longer Netherlands-specific)
- Flexible time series structures
- Diverse data availability scenarios
- Multiple data versions with different availability times

**New Transform API**

The preprocessing pipeline has been completely redesigned with a modular transform system:

.. code-block:: python

   from openstef_models.transforms import VersionedLagsAdder
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import timedelta
   
   # Create lag features with data availability constraints
   transform = VersionedLagsAdder(
       feature='load',
       lags=[timedelta(hours=-1), timedelta(hours=-2)]
   )
   
   result = transform.fit_transform(dataset)

New Features
^^^^^^^^^^^^

**Versioned Time Series Datasets**

V4 introduces ``VersionedTimeSeriesDataset``, which tracks data availability constraints essential for production forecasting:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Create dataset with availability tracking
   data = pd.DataFrame({
       'available_at': pd.date_range('2025-01-01 10:00', periods=4, freq='h'),
       'load': [100.0, 110.0, 120.0, 130.0]
   }, index=pd.date_range('2025-01-01 10:00', periods=4, freq='h'))
   
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data, 
       resolution=timedelta(hours=1)
   )
   
   # Select appropriate data version for forecast time
   snapshot = dataset.select_version()

**State Versioning and Migration**

All stateful objects now include version metadata and automatic state migration:

- Forward compatibility warnings when loading newer versions
- Automatic migration from legacy formats
- Clear upgrade paths between versions

**Improved Type Safety**

Full type annotations throughout the codebase enable better IDE support, earlier bug detection, and improved maintainability.

**Modular Transform System**

New transform architecture with clear interfaces:

- Time domain transforms (lags, rolling features)
- Validation transforms (completeness checking)
- Feature engineering transforms
- Composable pipelines

**Enhanced Documentation**

Complete documentation rewrite following the `Diátaxis framework <https://diataxis.fr/>`_:

- Tutorials for learning
- How-to guides for tasks
- Reference for technical details
- Explanation for understanding concepts

Improvements
^^^^^^^^^^^^

**Generalized Domain Logic**

V4 removes Netherlands-specific assumptions:

- Configurable holiday calendars for any region
- Flexible energy pricing models
- Customizable grid topology

**Increased Test Coverage**

Comprehensive test suite with:

- Unit tests for all core components
- Integration tests for pipelines
- Regression tests against benchmarks

**Standardized Code Quality**

- Consistent coding practices across all packages
- Centralized documentation standards
- Improved code readability

**Production-Ready Performance**

Currently running in production at Alliander with 10,000+ forecasts daily, demonstrating:

- Efficient implementations optimized for scale
- Reliable execution in production environments
- Proven performance characteristics

Migration Path
^^^^^^^^^^^^^^

V3 applications require significant refactoring to adopt V4. Key migration steps:

1. Update package imports to new modular structure
2. Replace hard-coded dependencies with configurable alternatives
3. Adopt new transform API for preprocessing
4. Update data loading to use new dataset types
5. Refactor model training and evaluation code

See :doc:`user_guide/migration_guide` for complete migration instructions with code examples.

Version 3.x
-----------

**Status:** Legacy (Maintenance Mode)

OpenSTEF 3.x is the previous stable release. While still functional, it is in maintenance mode with only critical bug fixes. New projects should use V4.

Key Features
^^^^^^^^^^^^

- Monolithic package structure
- Integrated MLFlow support
- Netherlands-specific domain logic
- Fixed preprocessing pipelines
- XGBoost and linear models

For V3 documentation, see the `legacy documentation site <https://openstef.readthedocs.io/>`_.

Checking Your Version
---------------------

To check which version of OpenSTEF you have installed:

.. code-block:: bash

   # Using pip
   pip show openstef
   
   # Using uv
   uv list | grep openstef
   
   # Using conda
   conda list openstef
   
   # Using pixi
   pixi list | grep openstef

Upgrading OpenSTEF
------------------

To upgrade to the latest version:

.. code-block:: bash

   # Using pip
   pip install --upgrade openstef
   
   # Using uv
   uv upgrade openstef
   
   # Using conda
   conda update openstef
   
   # Using pixi
   pixi upgrade openstef

.. warning::
   Upgrading from V3 to V4 requires code changes. Review the migration guide before upgrading production systems.

Release Schedule
----------------

OpenSTEF follows a continuous release model:

- **Major versions** (e.g., 3.0 → 4.0): Breaking changes, architectural updates
- **Minor versions** (e.g., 4.0 → 4.1): New features, backward-compatible changes
- **Patch versions** (e.g., 4.1.0 → 4.1.1): Bug fixes, security updates

Major releases are announced at least 3 months in advance with migration guides. Minor and patch releases follow semantic versioning guarantees.

Contributing to Releases
-------------------------

OpenSTEF is an open-source project under the LF Energy Foundation. To contribute features or fixes:

1. Review the `contribution guidelines <https://github.com/OpenSTEF/openstef/blob/main/CONTRIBUTING.md>`_
2. Submit pull requests to the appropriate package
3. Include tests and documentation updates
4. Follow the established code quality standards

All contributions are reviewed by maintainers and included in the next appropriate release.