Changelog
=========

This page provides the complete version history of OpenSTEF, automatically generated from the CHANGELOG.md file and GitHub release notes. It tracks all major releases, breaking changes, new features, and bug fixes across the OpenSTEF ecosystem.

.. note::
   This changelog is programmatically generated and updated with each release. For the most current information, see the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0.0-alpha (Current)
------------------------------

OpenSTEF V4 represents a complete architectural redesign focused on modularity, type safety, and enterprise integration. This alpha release is currently in production at Alliander, generating forecasts for over 10,000 grid locations daily.

**Major Changes**

- **Modular mono-repo architecture**: Split into self-contained packages (openstef-core, openstef-models, openstef-meta, openstef-beam, openstef-foundation)
- **Full type safety**: Complete mypy coverage throughout the codebase
- **Versioned datasets**: Support for data availability constraints and temporal versioning
- **Flexible configuration**: Replace hard-coded assumptions with configurable presets
- **Enterprise integration**: Pipeline APIs and custom component development support

**Breaking Changes**

- Complete API redesign - migration from V3 required
- New data structures and interfaces
- Different configuration format
- Modular package structure requires updated imports

**New Features**

- Versioned time series datasets with availability constraints
- Modular transform pipeline system
- Enhanced backtesting and evaluation framework (openstef-beam)
- Pre-trained models and transfer learning (openstef-foundation)
- Improved explainability features
- Support for custom models, transforms, and metrics

**Performance Improvements**

- Optimized data processing pipelines
- Efficient multi-part dataset composition
- Enhanced memory usage for large-scale deployments

Version 3.x Series
------------------

**Version 3.7.0**

- Enhanced model explainability features
- Improved weather data integration
- Bug fixes in quantile prediction handling
- Performance optimizations for large datasets

**Version 3.6.0**

- Added support for additional model types
- Improved error handling and logging
- Enhanced data validation mechanisms
- Documentation improvements

**Version 3.5.0**

- Expanded feature engineering capabilities
- Better handling of missing data
- Improved model selection algorithms
- Enhanced evaluation metrics

**Version 3.4.0**

- Added support for ensemble models
- Improved hyperparameter optimization
- Enhanced cross-validation procedures
- Bug fixes in data preprocessing

**Version 3.3.0**

- Improved quantile forecasting accuracy
- Enhanced weather feature integration
- Better handling of seasonal patterns
- Performance optimizations

**Version 3.2.0**

- Added support for custom holiday calendars
- Improved model persistence and loading
- Enhanced logging and monitoring capabilities
- Bug fixes in feature selection

**Version 3.1.0**

- Improved handling of data gaps
- Enhanced model validation procedures
- Better error messages and debugging
- Performance improvements

**Version 3.0.0**

- Major refactoring of core forecasting engine
- Improved quantile prediction capabilities
- Enhanced feature engineering pipeline
- Better integration with MLflow
- Comprehensive evaluation framework

Version 2.x Series
------------------

**Version 2.3.0**

- Added support for probabilistic forecasting
- Improved model selection algorithms
- Enhanced data preprocessing capabilities
- Bug fixes and performance improvements

**Version 2.2.0**

- Improved handling of weather data
- Enhanced feature engineering
- Better model validation
- Documentation updates

**Version 2.1.0**

- Added support for additional data sources
- Improved error handling
- Enhanced logging capabilities
- Performance optimizations

**Version 2.0.0**

- Complete rewrite of forecasting algorithms
- Improved accuracy and performance
- Enhanced data handling capabilities
- Better integration with external systems

Migration Guide
---------------

**From V3 to V4**

OpenSTEF V4 introduces significant architectural changes. See the migration guide in the how-to guides section for detailed migration instructions.

**Key Migration Steps:**

1. Update package imports to use modular structure
2. Migrate data structures to versioned datasets
3. Update configuration format
4. Adapt custom components to new interfaces
5. Update evaluation and backtesting code

**Breaking Changes Summary:**

- API redesign requires code updates
- New data structures and interfaces
- Different configuration approach
- Modular package imports
- Updated evaluation framework

Release Notes Format
--------------------

Each release follows semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes that require migration
- **MINOR**: New features with backward compatibility
- **PATCH**: Bug fixes and minor improvements

**Categories:**

- **Breaking Changes**: API changes requiring code updates
- **New Features**: Added functionality and capabilities
- **Improvements**: Performance and usability enhancements
- **Bug Fixes**: Resolved issues and corrections
- **Documentation**: Updates to guides and references

Contributing to Releases
-------------------------

Release planning and development happens in the open:

- **GitHub Issues**: Track bugs, features, and improvements
- **Community Meetings**: Bi-weekly discussions on progress and priorities
- **Public Roadmap**: Available on the OpenSTEF GitHub repository
- **Co-coding Sessions**: Regular community development sessions

For contributing to releases, see the `contributing guidelines <https://github.com/OpenSTEF/openstef/blob/main/CONTRIBUTING.md>`_ and join the community discussions.