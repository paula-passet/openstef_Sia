Changelog
=========


Release History
---------------


OpenSTEF follows semantic versioning with major.minor.patch format. Major versions like 4.0 introduce breaking changes and architectural improvements. Minor versions add features while maintaining compatibility. Patch versions contain bug fixes and small updates. Each release entry lists key changes, improvements, and any breaking modifications that may affect existing implementations.


.. note::

   OpenSTEF follows semantic versioning (MAJOR.MINOR.PATCH). Major version changes may introduce breaking changes to the public API. Minor versions add backward-compatible functionality. Patch versions contain backward-compatible bug fixes.


Version 4.x Series
------------------


OpenSTEF 4.0 represents a major architectural advancement focused on modularity, type safety, and broader domain applicability. This release decouples external dependencies like MLFlow and openstef-dbc, introduces flexible configuration mechanisms, and generalizes domain-specific logic beyond Netherlands-specific implementations. Key improvements include centralized data preprocessing, enhanced test coverage, and modular design supporting diverse forecasting use cases from research experimentation to enterprise integration.

The 4.0 series emphasizes extensibility through clear interfaces for custom models and transforms, while maintaining performance optimization for production deployments. Breaking changes include removal of hard-coded assumptions and restructured APIs to support the new modular architecture. Documentation follows the Diátaxis framework with comprehensive getting started guides and clearer distinction between the standalone library and reference implementations.


Version 3.x Series (Legacy)
---------------------------


The OpenSTEF 3.x series represents the legacy release line that established the foundational architecture and core forecasting capabilities of the library. These releases introduced the initial machine learning pipeline, XGBoost integration, and basic preprocessing components that formed the basis for energy forecasting applications. Version 3.x provided the original implementation of feature engineering, model training workflows, and prediction generation that served as the foundation for subsequent development. While superseded by version 4.0's modular architecture and enhanced flexibility, the 3.x series remains available for reference and migration planning purposes.


.. warning::

   Version 3.x series has reached end-of-life status. Users should migrate to OpenSTEF 4.0 for continued support, enhanced modularity, and improved documentation. The 4.0 release addresses architectural limitations and provides better extensibility for diverse forecasting applications.


Migration Guides
----------------


- Migration Guide: OpenSTEF 3.x to 4.0 - Comprehensive upgrade instructions covering breaking changes, new features, and code migration examples

- Version 4.0 Breaking Changes - Detailed list of API changes, deprecated features, and required code modifications

- Configuration Migration - Guide for updating configuration files and settings for version 4.0 compatibility

- Dependency Updates - Instructions for handling new and updated dependencies in OpenSTEF 4.0


