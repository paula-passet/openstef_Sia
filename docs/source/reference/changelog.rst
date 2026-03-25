Changelog
=========


Release History Overview
------------------------


OpenSTEF follows semantic versioning (SemVer) principles with version numbers in MAJOR.MINOR.PATCH format. Major versions like 4.0 introduce breaking changes and architectural improvements. Minor versions add backward-compatible features, while patch versions contain bug fixes and small improvements. Users should expect migration requirements when upgrading across major versions.


.. note::

   Changes are categorized by impact level and component area. Major releases introduce breaking changes, minor releases add features, and patch releases fix bugs. Each entry includes affected modules and migration guidance where applicable.


Major Version Changes
---------------------


OpenSTEF 4.0 represents a significant architectural evolution focused on modularity, type safety, and broader domain applicability. This major release decouples external dependencies, introduces flexible configuration mechanisms, and generalizes domain-specific logic beyond Netherlands-specific use cases. The modular design enables easier integration of custom models and components while maintaining performance for production deployments. Breaking changes include restructured APIs, centralized preprocessing logic, and relaxed input data constraints to support diverse forecasting scenarios from research experimentation to enterprise integration.


- Version 4.0 introduces modular architecture requiring migration from monolithic imports to component-specific imports

- External dependencies like MLFlow and openstef-dbc are decoupled - update integration code accordingly

- Data preprocessing logic centralized - custom preprocessing workflows need refactoring

- Configuration system replaces hard-coded assumptions - migrate settings to new config format

- Type safety enforced throughout - add type annotations to existing custom code

- Flexible data format support may require updating rigid input validation logic

- Domain-specific logic generalized - review Netherlands-specific implementations for compatibility


Recent Releases
---------------


OpenSTEF 4.0 Alpha represents a major architectural redesign focused on modularity, flexibility, and enterprise integration. The library now features decoupled external dependencies, improved type safety throughout the codebase, and enhanced support for diverse data formats beyond the original Netherlands energy grid use case.

Currently deployed in production at Alliander processing over 10,000 daily forecasts, the alpha release demonstrates significant improvements in code quality with increased test coverage and standardized practices. The modular design enables easier integration of custom models and transforms while maintaining the robust forecasting capabilities of version 3.

Key enhancements include centralized data preprocessing logic, flexible configuration mechanisms replacing hard-coded assumptions, and generalized domain logic supporting broader applicability. The release maintains backward compatibility while introducing clear interfaces for extensibility and improved documentation following the Diátaxis framework.


Historical Versions
-------------------


This section contains archived version information automatically extracted from historical CHANGELOG.md entries. OpenSTEF has evolved through multiple major versions, with V4 Alpha representing a significant redesign focused on flexibility and modularity. The library maintains backward compatibility while introducing enhanced enterprise integration capabilities. Historical releases demonstrate OpenSTEF's progression from initial forecasting functionality to a comprehensive short-term forecasting solution deployed in production environments with thousands of daily forecasts.


