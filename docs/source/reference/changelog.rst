Changelog
=========

This page provides a comprehensive version history of the OpenSTEF Python machine learning library, combining information from the CHANGELOG.md file with GitHub release notes. The changelog tracks breaking changes, new features, bug fixes, and improvements across all releases.

.. note::
   This page is automatically generated from the project's CHANGELOG.md file and GitHub releases. For the most up-to-date information, see the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0 Series
------------------

OpenSTEF 4.0 represents a major architectural redesign focused on modularity, flexibility, and enterprise integration. This release introduces a mono-repo structure with multiple self-contained packages and significantly improves the library's extensibility.

Version 4.0.0-alpha (Current Development)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Release Status:** Alpha - In active development

**Major Changes:**

- **Modular Architecture:** Complete restructure into a mono-repo with five core packages:
  
  - ``openstef-core``: Data types, interfaces, and base classes
  - ``openstef-models``: Forecasting models and preprocessing pipelines  
  - ``openstef-meta``: Meta-learning and ensemble models
  - ``openstef-beam``: Backtesting, evaluation, analysis, and metrics
  - ``openstef-reference``: Reference implementations and examples

- **Versioned Time Series Support:** New ``VersionedTimeSeriesDataset`` class for handling data availability constraints and multi-part composition

- **Enhanced Type Safety:** Full type annotations throughout the codebase with strict mypy compliance

- **Flexible Configuration:** Replaced hard-coded assumptions with configurable parameters for broader applicability

**Breaking Changes:**

- API restructure requires migration from v3.x - see the migration guide in how-to guides for details
- Import paths changed due to new package structure
- Configuration format updated to support new modular design

**New Features:**

- Support for custom target providers and workflows
- Advanced feature engineering capabilities
- Improved support for diverse data availability scenarios
- Enhanced model explainability features
- New preset configurations for common use cases

**Production Status:**

Currently deployed at Alliander processing 10,000+ daily forecasts. Stable release planned with comprehensive documentation and deployment examples.

Version 3.x Series
------------------

The 3.x series established OpenSTEF as a production-ready forecasting library with robust model training and evaluation capabilities.

Version 3.3.0
^^^^^^^^^^^^^^

**New Features:**

- Enhanced model validation and cross-validation support
- Improved weather data integration
- Extended support for custom feature engineering
- Better handling of missing data scenarios

**Bug Fixes:**

- Fixed memory leaks in long-running forecast processes
- Resolved timezone handling issues in data preprocessing
- Corrected quantile calculation edge cases

**Improvements:**

- Performance optimizations for large datasets
- Enhanced logging and debugging capabilities
- Updated documentation with more examples

Version 3.2.0
^^^^^^^^^^^^^^

**New Features:**

- Support for ensemble models
- Advanced hyperparameter tuning capabilities
- Integration with MLflow for experiment tracking
- New evaluation metrics for forecast quality assessment

**Bug Fixes:**

- Fixed issues with seasonal decomposition
- Resolved data leakage in cross-validation
- Corrected handling of daylight saving time transitions

Version 3.1.0
^^^^^^^^^^^^^^

**New Features:**

- Quantile regression support for uncertainty estimation
- Improved feature selection algorithms
- Enhanced support for multiple prediction horizons
- New visualization tools for forecast analysis

**Improvements:**

- Faster model training through optimized algorithms
- Better memory management for large time series
- Enhanced error messages and debugging information

Version 3.0.0
^^^^^^^^^^^^^^

**Major Release:** First stable public release of OpenSTEF

**Core Features:**

- XGBoost-based forecasting models optimized for energy applications
- Comprehensive data preprocessing and feature engineering
- Built-in validation and backtesting capabilities
- Support for multiple aggregation levels and use cases
- Integration with common data sources and formats

**Supported Use Cases:**

- Congestion management forecasts
- Transport capacity planning
- Grid loss estimation
- Load forecasting at various aggregation levels

Migration Information
---------------------

**From v3.x to v4.x:**

The v4.0 release introduces significant architectural changes. Users migrating from v3.x should:

1. Review the new package structure and update import statements
2. Migrate configuration files to the new format
3. Update custom components to use new interfaces
4. Test thoroughly with existing data and models

See the migration guide in the how-to guides section for detailed migration instructions and examples.

**Backward Compatibility:**

- v4.0 is not backward compatible with v3.x due to architectural changes
- Migration tools and documentation are provided to ease the transition
- v3.x will continue to receive critical bug fixes during the transition period

Development and Release Process
-------------------------------

**Release Schedule:**

- Major releases (x.0.0): Annual, with significant new features or architectural changes
- Minor releases (x.y.0): Quarterly, with new features and improvements
- Patch releases (x.y.z): As needed, for bug fixes and security updates

**Development Process:**

- All changes tracked in CHANGELOG.md following Keep a Changelog format
- Semantic versioning for clear compatibility expectations
- Comprehensive testing and validation before releases
- Community feedback incorporated through GitHub issues and discussions

**Getting Involved:**

The OpenSTEF project welcomes contributions. See the project's GitHub repository for contribution guidelines and development setup instructions.