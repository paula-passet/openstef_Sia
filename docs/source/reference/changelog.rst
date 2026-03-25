Changelog
=========


Release History
---------------


OpenSTEF follows semantic versioning (MAJOR.MINOR.PATCH) where major versions introduce breaking changes, minor versions add backward-compatible features, and patch versions contain bug fixes. Version 4.0 represents a significant architectural advancement with enhanced modularity, type safety, and broader domain applicability compared to previous releases.

The changelog documents each release with clear categorization of changes including new features, breaking changes, bug fixes, and performance improvements. Each entry provides context for migration and highlights impacts on existing implementations to help users understand upgrade requirements.


.. note::

   This changelog is automatically generated from CHANGELOG.md and GitHub releases. Manual edits will be overwritten during updates.


Latest Releases
---------------


OpenSTEF 4.0 represents a major architectural advancement, introducing modular design principles, full type safety, and decoupled external dependencies. This release generalizes domain-specific logic beyond Netherlands-specific use cases, enabling broader applicability across different regions and energy markets. Enhanced documentation follows the Diátaxis framework, while improved configuration mechanisms replace hard-coded assumptions for greater flexibility.

The 4.0 release focuses on extensibility through clear interfaces for custom models and transforms, supporting diverse deployment scenarios from research notebooks to enterprise integration. Performance optimizations target production use cases, while centralized data preprocessing logic improves code clarity and reduces duplication across validation and model components.


Migration Guides
----------------


Breaking changes in OpenSTEF major releases are documented in dedicated migration guides within this changelog. Each major version includes a comprehensive migration section detailing API changes, deprecated features, and required code modifications. Version 4.0 introduces significant architectural improvements including modular design, decoupled dependencies, and enhanced type safety that may require updates to existing implementations.


- OpenSTEF 3.x to 4.0: :doc:`migration_guides/v3_to_v4` - Major architectural changes, modular design, and breaking API changes

- OpenSTEF 2.x to 3.0: :doc:`migration_guides/v2_to_v3` - Updated dependencies and configuration format changes

- OpenSTEF 1.x to 2.0: :doc:`migration_guides/v1_to_v2` - Core API restructuring and data handling improvements


Complete Version History
------------------------


.. note::

   This changelog is automatically generated from release notes and updated with each new version of the OpenSTEF library.


The complete version history is automatically generated from the project's CHANGELOG.md file. This comprehensive record includes all releases, bug fixes, feature additions, and breaking changes. Each version entry contains detailed information about modifications, contributor acknowledgments, and migration notes where applicable.


