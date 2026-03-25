Changelog
=========


About This Changelog
--------------------


This changelog is automatically generated from the project's CHANGELOG.md file and GitHub releases. The content is updated with each new version release to provide a comprehensive history of changes, improvements, and bug fixes in the OpenSTEF library.


.. note::

   For major version changes and breaking changes, consult the migration guides in the documentation. These guides provide detailed instructions for updating your code when upgrading between major OpenSTEF versions.


Latest Releases
---------------


OpenSTEF has evolved significantly with recent major releases, transitioning from early versions to the current V4 Alpha architecture. The library has matured into a comprehensive machine learning framework for energy forecasting, moving beyond simple model implementations to provide complete pipelines with probabilistic forecasting capabilities. Recent development has focused on model-agnostic design and domain-specific feature engineering for electricity grid applications.


- V4.0 Alpha: Complete architecture redesign with model-agnostic framework supporting multiple ML backends

- V4.0 Alpha: Added probabilistic forecasting with uncertainty quantification and confidence intervals

- V4.0 Alpha: Enhanced feature engineering pipeline with domain-specific energy transformations

- V4.0 Alpha: Breaking change - New API structure requires migration from V3.x prediction interfaces

- V4.0 Alpha: Improved performance with optimized data preprocessing and parallel model training


Version History
---------------


OpenSTEF follows semantic versioning with three-part version numbers (major.minor.patch). Major releases like 4.0 introduce breaking changes and architectural improvements. Minor releases add new features while maintaining backward compatibility. Patch releases contain bug fixes and small improvements without breaking existing functionality.


.. note::

   Detailed version entries below are automatically generated from CHANGELOG.md and GitHub releases. For the most current information, refer to the OpenSTEF GitHub repository releases page.


Breaking Changes Summary
------------------------


Breaking changes in OpenSTEF can significantly impact existing implementations, particularly as the library evolves toward greater modularity and type safety. Version 4.0 introduces architectural improvements that may require code modifications, dependency updates, and configuration changes in downstream applications.


- Version 4.0: Complete API redesign with modular architecture - requires full migration from 3.x patterns

- Version 4.0: Decoupled external dependencies (MLFlow, openstef-dbc, xgboost/gblinear) - update integration code

- Version 4.0: Centralized data preprocessing logic - refactor existing validation and model components

- Version 4.0: New configuration system replaces hard-coded assumptions - migrate configuration files

- Version 4.0: Generalized domain logic removes Netherlands-specific defaults - update holiday calendars and pricing

- Version 4.0: Relaxed input data constraints change expected formats - validate data pipelines

- Version 4.0: Type safety enforcement throughout codebase - add type annotations to custom code


