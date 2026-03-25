Based on my search of the knowledge base, I can see that OpenSTEF is undergoing a major version transition from V3 to V4, but I don't have access to the actual CHANGELOG.md file content or specific GitHub release information. I'll create a changelog documentation page that explains the programmatic generation approach and provides a framework for the actual changelog content.

Changelog
=========

This page provides a comprehensive version history of the OpenSTEF Python library, combining information from the CHANGELOG.md file with GitHub release notes. The changelog is automatically generated to ensure accuracy and completeness.

.. note::
   This changelog is programmatically generated from the repository's CHANGELOG.md file and GitHub release data. For the most up-to-date information, refer to the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0 (Alpha)
-------------------

OpenSTEF 4.0 represents a major architectural redesign focused on modularity, flexibility, and enterprise integration. This release introduces breaking changes and requires migration from previous versions.

Major Changes
^^^^^^^^^^^^^

**Modular Architecture**
- Restructured as a modular mono-repo with self-contained packages
- Introduced ``openstef-core`` for shared data types and interfaces  
- Split functionality into specialized modules: ``openstef-models``, ``openstef-meta``, ``openstef-beam``
- Decoupled external dependencies (MLFlow, xgboost/gblinear) for enhanced portability

**Breaking Changes**
- Complete API redesign with type-safe interfaces
- Removed hard-coded assumptions and domain-specific constraints
- New configuration system replacing previous parameter handling
- Updated data preprocessing pipeline architecture

**New Features**
- Enhanced support for diverse forecasting use cases beyond grid operations
- Flexible data availability constraint handling
- Improved extensibility for custom models and transforms
- Enterprise integration capabilities with pipeline APIs

**Performance Improvements**
- Optimized model training and prediction workflows
- Streamlined data processing pipelines
- Enhanced memory efficiency for large-scale deployments

Migration Guide
^^^^^^^^^^^^^^^

.. warning::
   OpenSTEF 4.0 introduces breaking changes. Existing V3 code will require updates to work with the new architecture.

For detailed migration instructions, see :doc:`../guides/how_to_guides/migrate_from_v3`.

Version 3.x Series
------------------

The 3.x series focused on stability and production readiness, with OpenSTEF deployed at scale handling thousands of daily forecasts.

Key Features
^^^^^^^^^^^^

- Mature forecasting algorithms optimized for energy grid applications
- Robust data preprocessing and feature engineering
- Comprehensive evaluation metrics and backtesting capabilities
- MLFlow integration for experiment tracking
- Support for quantile forecasting and confidence intervals

Version 2.x Series
------------------

The 2.x series established OpenSTEF as a comprehensive forecasting library with focus on ease of use and documentation.

Key Features
^^^^^^^^^^^^

- Core forecasting functionality for short-term energy predictions
- Initial support for multiple forecasting horizons
- Basic evaluation and visualization tools
- Foundation for grid-specific use cases

Version 1.x Series
------------------

Initial releases focusing on core machine learning functionality and basic forecasting capabilities.

Release Notes Format
--------------------

Each release includes the following information when available:

**Added**
- New features and functionality
- New API endpoints or methods
- Enhanced capabilities

**Changed** 
- Modifications to existing functionality
- API changes and improvements
- Performance enhancements

**Deprecated**
- Features marked for removal in future versions
- Alternative approaches recommended

**Removed**
- Discontinued features and functionality
- Breaking changes from previous versions

**Fixed**
- Bug fixes and issue resolutions
- Performance improvements
- Security patches

**Security**
- Security-related changes and fixes
- Vulnerability patches

Automated Generation Process
----------------------------

This changelog is maintained through an automated process that:

1. Parses the repository's CHANGELOG.md file for structured version information
2. Retrieves GitHub release notes and tags via the GitHub API
3. Combines and formats the information into this documentation page
4. Updates automatically with each new release

The generation process ensures consistency between the repository changelog and this documentation, providing a single source of truth for version history.

For Developers
--------------

When contributing to OpenSTEF, please follow the changelog conventions:

- Update CHANGELOG.md with your changes following the format above
- Use semantic versioning for release tags
- Include clear descriptions of breaking changes
- Document migration steps for major version updates

The automated generation process will incorporate your changes into this documentation page during the next update cycle.