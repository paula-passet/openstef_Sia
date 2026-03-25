Changelog
=========


Release Notes Overview
----------------------


OpenSTEF follows semantic versioning principles with major, minor, and patch releases. Major versions like 4.0 introduce breaking changes and architectural improvements, while minor versions add features and patch versions fix bugs. The changelog is organized chronologically with each release documenting changes, improvements, and migration guidance to help users understand version impacts and upgrade paths.


.. note::

   This changelog is automatically generated from CHANGELOG.md and GitHub releases. Manual edits may be overwritten during updates.


Latest Releases
---------------


OpenSTEF 4.0 represents a major architectural advancement focused on modularity, type safety, and broader domain applicability. This release decouples external dependencies, introduces flexible configuration mechanisms, and generalizes domain-specific logic to support use cases beyond the Netherlands energy sector. Key improvements include enhanced code quality with increased test coverage, centralized data preprocessing, and comprehensive documentation following the Diátaxis framework.


- 4.0.0 - Major architectural overhaul with modular design, decoupled dependencies, improved type safety, and enhanced extensibility for diverse forecasting use cases

- 3.0.0 - Significant improvements in model performance, expanded preprocessing capabilities, and enhanced integration with MLFlow for experiment tracking


Version History
---------------


This section contains the complete version history for the OpenSTEF library, automatically generated from the project's CHANGELOG.md file. Each release entry includes version numbers, release dates, and detailed descriptions of new features, improvements, bug fixes, and breaking changes. The changelog tracks the evolution from early versions through the current V4 Alpha release, which represents a major redesign focused on flexibility and modularity while maintaining strong forecasting capabilities used in production environments.


Migration Guide References
--------------------------


For major version upgrades, consult the migration guides in the documentation. OpenSTEF 4.0 introduces significant architectural changes including modular design, decoupled dependencies, and enhanced type safety. Breaking changes affect model interfaces, configuration mechanisms, and data preprocessing logic. Review version-specific migration documentation before upgrading production systems.


.. warning::

   OpenSTEF 4.0 introduces significant architectural changes that may break existing code. Key deprecations include hard-coded domain assumptions, rigid data format requirements, and tightly coupled external dependencies. Review migration documentation before upgrading production systems.


