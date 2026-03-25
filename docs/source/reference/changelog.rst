Changelog
=========

This page provides a comprehensive history of OpenSTEF releases, combining information from the project's CHANGELOG.md file with GitHub release notes. Track version history, breaking changes, new features, and bug fixes across all releases.

.. note::
   This page is automatically generated from the project's CHANGELOG.md file and GitHub release information. For the most up-to-date information, see the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0 (Alpha)
-------------------

OpenSTEF 4.0 represents a major architectural redesign focused on modularity, flexibility, and enterprise integration. This release is currently in alpha and is being tested in production at Alliander with over 10,000 daily forecasts.

Breaking Changes
^^^^^^^^^^^^^^^^

- **Complete architectural refactor**: OpenSTEF 4.0 introduces a modular mono-repo structure with separate packages for core functionality, models, meta-learning, and evaluation
- **New package structure**: The library is now split into ``openstef-core``, ``openstef-models``, ``openstef-meta``, and ``openstef-beam`` packages
- **API changes**: Many APIs have been redesigned to support the new modular architecture
- **Dependency changes**: Decoupled external dependencies including MLFlow, openstef-dbc, and specific model implementations

New Features
^^^^^^^^^^^^

- **Modular design**: Components work in isolation and are easily composable into larger systems
- **Full type safety**: Complete type annotations throughout the codebase
- **Extensibility**: Clear interfaces for adding custom models, transforms, and metrics
- **Flexible configuration**: Configurable mechanisms replace hard-coded assumptions
- **Broader domain support**: Generalized logic supports use cases beyond the Netherlands
- **Improved data handling**: More flexible data formats and availability constraints
- **Enhanced documentation**: Following the Diátaxis framework for comprehensive documentation

Core Modules
^^^^^^^^^^^^^

- **openstef-core**: Data types, interfaces, base classes, and shared utilities
- **openstef-models**: Forecasting models, preprocessing pipelines, and energy-specific transformations
- **openstef-meta**: Modern ensemble models and advanced architectures
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics for model validation

Target Deployments
^^^^^^^^^^^^^^^^^^

- **Research and experimentation**: Low-code notebooks with pre-built components
- **Small-scale deployments**: Docker-compose examples with minimal infrastructure
- **Enterprise integration**: Pipeline APIs and flexible callback mechanisms

Migration Notes
^^^^^^^^^^^^^^^

Users migrating from OpenSTEF 3.x should refer to the migration guide in the how-to guides section for detailed migration instructions.

Version 3.x Series
------------------

.. note::
   [UNDER CONSTRUCTION] Detailed changelog information for OpenSTEF 3.x releases will be populated from the CHANGELOG.md file and GitHub release notes.

Key improvements in the 3.x series included:

- Enhanced forecasting accuracy for various use cases
- Improved model training and validation workflows  
- Better support for different data sources and formats
- Expanded documentation and examples

Version 2.x Series
------------------

.. note::
   [UNDER CONSTRUCTION] Detailed changelog information for OpenSTEF 2.x releases will be populated from the CHANGELOG.md file and GitHub release notes.

The 2.x series established OpenSTEF as a production-ready forecasting library with:

- Stable API for energy forecasting workflows
- Support for multiple forecasting models
- Integration with common data sources
- Comprehensive evaluation metrics

Version 1.x Series
------------------

.. note::
   [UNDER CONSTRUCTION] Detailed changelog information for OpenSTEF 1.x releases will be populated from the CHANGELOG.md file and GitHub release notes.

The initial 1.x releases provided:

- Core forecasting functionality
- Basic model training and prediction capabilities
- Initial documentation and examples
- Foundation for future development

Release Information
-------------------

For complete release information including:

- Detailed feature descriptions
- Bug fix lists
- Performance improvements
- Contributor acknowledgments

Visit the `OpenSTEF GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Reporting Issues
----------------

If you encounter bugs or have feature requests, please report them on the `GitHub issues page <https://github.com/OpenSTEF/openstef/issues>`_.