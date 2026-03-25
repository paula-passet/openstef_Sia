Changelog
=========

This page provides a comprehensive version history of OpenSTEF, combining information from CHANGELOG.md files and GitHub release notes. The changelog tracks major releases, breaking changes, new features, and bug fixes across the OpenSTEF ecosystem.

.. note::
   This page is automatically generated from repository changelog files and GitHub releases. For the most up-to-date information, check the individual package repositories.

Version 4.0 Series
------------------

OpenSTEF 4.0 represents a major architectural redesign focused on modularity, flexibility, and enterprise integration while maintaining the strong forecasting capabilities of previous versions.

Version 4.0.0-alpha (Current Development)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Release Status**: Alpha - Currently in production at Alliander with 10,000+ daily forecasts

**Major Changes**

- **Complete architectural redesign** to modular mono-repo structure
- **Breaking changes** from OpenSTEF 3.x - see migration guide for upgrade path
- **New package structure** with four core modules:

  - ``openstef-core``: Data types, interfaces, and base classes
  - ``openstef-models``: Forecasting models and preprocessing pipelines  
  - ``openstef-beam``: Backtesting, evaluation, analysis, and metrics
  - ``openstef-meta``: Meta-learning and advanced ensemble models

**New Features**

- **Modular design** - Components work in isolation and compose into larger systems
- **Full type safety** throughout the codebase for better maintainability
- **Extensible interfaces** for custom models, transforms, and metrics
- **Flexible configuration** mechanisms replacing hard-coded assumptions
- **Enhanced data availability support** for delayed measurements and weather forecasts
- **Broader domain applicability** beyond Netherlands-specific use cases
- **Customizable holiday calendars** and dynamic energy pricing support
- **Improved enterprise integration** with flexible callback mechanisms

**Performance Improvements**

- **Optimized implementations** for production use cases
- **Streamlined test execution** with increased coverage
- **Centralized data preprocessing** logic reducing duplication

**Documentation**

- **Complete documentation overhaul** following Diátaxis framework
- **Improved getting started experience** with clearer onboarding
- **Enhanced API documentation** with comprehensive examples
- **Clear distinction** between library and reference implementation

Version 3.0 Series
------------------

OpenSTEF 3.0 established the foundation for production forecasting systems with robust model training and evaluation capabilities.

Version 3.x.x (Legacy)
^^^^^^^^^^^^^^^^^^^^^^

**Status**: Legacy - Migration to 4.0 recommended for new projects

**Key Features**

- **Production-ready forecasting** with XGBoost and linear models
- **MLFlow integration** for experiment tracking
- **Comprehensive feature engineering** pipeline
- **Energy-specific transformations** and lag features
- **Quantile forecasting** support
- **Basic evaluation metrics** and reporting

**Known Limitations**

- **Monolithic architecture** limiting flexibility
- **Hard-coded assumptions** for specific use cases
- **Limited extensibility** for custom models
- **Netherlands-specific** domain logic
- **Tight coupling** with external dependencies

Breaking Changes from 3.x to 4.0
---------------------------------

The transition from OpenSTEF 3.x to 4.0 introduces significant breaking changes due to the architectural redesign:

**Package Structure**
^^^^^^^^^^^^^^^^^^^^

- **Old**: Single ``openstef`` package
- **New**: Modular packages (``openstef-core``, ``openstef-models``, ``openstef-beam``, ``openstef-meta``)

**Import Changes**
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # OpenSTEF 3.x
   from openstef.model.regressors import XGBQuantileOptunaRegressor
   from openstef.feature_engineering.apply_features import apply_features
   
   # OpenSTEF 4.0
   from openstef_models.regressors import XGBQuantileOptunaRegressor  
   from openstef_models.transforms import FeatureEngineeringPipeline

**Configuration Changes**
^^^^^^^^^^^^^^^^^^^^^^^^

- **Old**: Hard-coded model parameters and feature engineering
- **New**: Flexible configuration system with presets and customization

**Data Interface Changes**  
^^^^^^^^^^^^^^^^^^^^^^^^^

- **Old**: Pandas DataFrame-centric interfaces
- **New**: Typed dataset classes with versioning support

Migration Support
-----------------

**Migration Guide Available**

Comprehensive migration documentation is available at :doc:`../guides/how_to_guides/migrate_from_v3` covering:

- **Step-by-step upgrade process** from 3.x to 4.0
- **Code transformation examples** for common patterns  
- **Configuration migration** strategies
- **Testing and validation** approaches

**Community Support**

- **GitHub Discussions** for migration questions
- **Example repositories** demonstrating 4.0 patterns
- **Community feedback** integration from early adopters

Release Schedule
---------------

**Stable Release Timeline**

- **4.0.0-alpha**: Current development version (production-tested at Alliander)
- **4.0.0-beta**: Planned Q2 2024 with complete documentation
- **4.0.0-stable**: Planned Q3 2024 with deployment examples

**Maintenance Policy**

- **OpenSTEF 4.x**: Active development and support
- **OpenSTEF 3.x**: Security fixes only until 4.0 stable release
- **Migration window**: 6 months overlap support for 3.x users

Contributing to Changelog
-------------------------

**Automated Generation**

This changelog is automatically generated from:

- **CHANGELOG.md files** in each package repository
- **GitHub release notes** with semantic versioning tags
- **Pull request labels** indicating feature/bugfix/breaking change types

**Manual Updates**

For significant releases or architectural changes, manual curation ensures:

- **Clear impact assessment** for users
- **Migration guidance** for breaking changes  
- **Context and rationale** for major decisions

.. note::
   For detailed technical changes and API modifications, refer to the individual package documentation and GitHub release pages.