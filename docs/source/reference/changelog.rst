Changelog
=========


Changelog
=========


This changelog documents all notable changes, improvements, and updates to the OpenSTEF library. OpenSTEF is an open-source Python package for short-term energy forecasting that provides machine learning pipelines for data preprocessing, feature engineering, model training, and probabilistic forecasting. Each release entry below details the modifications made to the library's functionality, API changes, bug fixes, and new features to help users understand what has changed between versions.


.. note::

   This changelog is automatically generated from the CHANGELOG.md file in the OpenSTEF repository and GitHub release notes. For the most up-to-date version history and detailed release information, please refer to the official OpenSTEF GitHub repository at https://github.com/OpenSTEF/openstef.


Version Format
--------------


OpenSTEF follows semantic versioning (SemVer) with a MAJOR.MINOR.PATCH format. Major version increments (e.g., 3.0 to 4.0) indicate breaking changes that may require code modifications when upgrading the library. Minor version increments introduce new features while maintaining backward compatibility with existing code. Patch version increments contain bug fixes and small improvements that do not affect the public API. This versioning scheme helps users understand the impact of updates and plan their upgrade strategies accordingly.


- Major changes (X.0.0): Breaking API changes, architectural redesigns, removal of deprecated features, or significant changes to core forecasting algorithms that require code modifications

- Minor changes (X.Y.0): New features, additional model types, enhanced configuration options, new preprocessing capabilities, or backward-compatible API extensions

- Patch changes (X.Y.Z): Bug fixes, performance improvements, documentation updates, dependency updates, or minor enhancements that maintain full backward compatibility


Latest Releases
---------------


OpenSTEF 4.0 Alpha represents a significant evolution of the open-source energy forecasting library, introducing a model-agnostic framework that goes beyond simple prediction models. This major release emphasizes OpenSTEF's role as a comprehensive machine learning framework for energy forecasting, featuring complete pipelines for data preprocessing, feature engineering, model training, and evaluation. Key highlights include enhanced probabilistic forecasting capabilities that provide uncertainty estimates alongside predictions, built-in domain-specific feature engineering for energy applications, and improved architecture designed to handle the increasing complexity of modern electricity grids with renewable energy sources, electric vehicles, and heat pumps.


Version 4.x.x
-------------


OpenSTEF version 4.x represents a major evolution of the library, introducing significant architectural improvements and enhanced flexibility. This release focuses on four key areas of advancement: improved code quality through increased test coverage and standardized practices, architectural enhancements that decouple external dependencies and introduce modular design patterns, broader domain applicability that extends beyond Netherlands-specific use cases, and a completely revamped user experience with comprehensive documentation following the Diátaxis framework. The 4.x series emphasizes modularity-first design principles, full type safety throughout the codebase, and clear extensibility interfaces that allow users to integrate custom models and transforms without modifying core library code. These improvements make OpenSTEF more robust for production deployments while maintaining the flexibility needed for research and experimentation across diverse forecasting applications.


4.1.0 - 2024-XX-XX
^^^^^^^^^^^^^^^^^^


- Enhanced modularity with decoupled external dependencies for improved portability

- Introduced flexible configuration mechanisms to replace hard-coded assumptions

- Improved type safety throughout the codebase for better maintainability

- Centralized data preprocessing logic to reduce duplication across components

- Added support for diverse data availability scenarios in forecasting pipelines

- Enhanced extensibility with clear interfaces for custom models and transforms

- Improved performance optimizations for production use cases

- Added support for broader domain applicability beyond Netherlands-specific use cases

- Introduced modular design for easier integration of new models and features

- Enhanced test coverage and streamlined test execution for better reliability


- Decoupled external dependencies including MLFlow, openstef-dbc, and xgboost/gblinear for enhanced modularity

- Centralized data preprocessing logic across validation and model components

- Relaxed rigid input data constraints to support more flexible data formats and structures

- Generalized domain-specific logic to support use cases beyond Netherlands-specific implementations

- Introduced flexible configuration mechanisms replacing hard-coded assumptions

- Enhanced support for diverse data availability scenarios in forecasting pipelines


- Hard-coded holiday calendars - use configurable holiday calendar system instead

- Direct MLFlow dependencies in core forecasting - migrate to pluggable experiment tracking

- Rigid input data format requirements - transition to flexible data validation schemas

- openstef-dbc tight coupling - use abstract database interfaces

- Netherlands-specific energy pricing assumptions - implement configurable pricing models

- Fixed preprocessing pipelines - adopt modular preprocessing components


- Removed hard-coded dependencies on MLFlow for experiment tracking

- Removed tight coupling with openstef-dbc database connector

- Removed rigid xgboost/gblinear model dependencies

- Removed hard-coded Dutch holiday calendar assumptions

- Removed inflexible input data format constraints

- Removed domain-specific logic tied to Alliander use cases


- Fixed issue with test coverage reporting in CI/CD pipeline

- Resolved memory leaks in data preprocessing components

- Corrected type safety violations in model validation logic

- Fixed configuration loading errors when using custom holiday calendars

- Resolved dependency conflicts with MLFlow integration

- Fixed data format validation errors for flexible input structures

- Corrected edge cases in modular component composition

- Fixed performance bottlenecks in production forecasting pipelines


4.0.0 - 2024-XX-XX
^^^^^^^^^^^^^^^^^^


.. warning::

   This is a major release that introduces significant breaking changes to the OpenSTEF library. Version 4.0 represents a complete architectural overhaul focused on modularity, type safety, and broader domain applicability. Existing code written for OpenSTEF 3.x will require updates to work with this version. Key areas of change include decoupled external dependencies, centralized data preprocessing logic, flexible configuration mechanisms, and generalized domain-specific components. Please review the migration guide and updated documentation before upgrading production systems.


- Complete architectural redesign with modularity-first approach for better component isolation and composability

- Full type safety implementation throughout the codebase to catch bugs early and improve maintainability

- Decoupled external dependencies (MLFlow, openstef-dbc, xgboost/gblinear) for enhanced modularity and portability

- New flexible configuration mechanisms replacing hard-coded assumptions for improved adaptability

- Generalized domain-specific logic to support use cases beyond Netherlands-specific implementations

- Centralized data preprocessing logic to improve clarity and reduce duplication across components

- Clear interfaces for adding custom models, transforms, and metrics without modifying core code

- Relaxed rigid input data constraints to allow more flexible data formats and structures

- Improved support for diverse data availability scenarios enabling more resilient forecasting pipelines

- Performance optimizations for production use cases with efficient implementations


- Removed hard-coded dependencies on MLFlow - users must now explicitly configure experiment tracking if needed. See migration guide for alternative tracking solutions.

- Decoupled openstef-dbc database connector - database operations now require explicit configuration. Update your code to use the new database interface or provide custom connectors.

- Replaced rigid input data constraints with flexible schema validation - existing data pipelines may need schema updates. Use the new validation utilities to check compatibility.

- Centralized data preprocessing logic - custom preprocessing functions may need updates to work with the new unified preprocessing pipeline. Check the preprocessing migration guide.

- Removed Netherlands-specific assumptions from core forecasting logic - holiday calendars and regional settings now require explicit configuration. Update your configuration files accordingly.

- Changed model interface to support modular architecture - custom models must implement the new ModelInterface. See the model development guide for migration steps.

- Updated configuration system to replace hard-coded parameters - existing configuration files need conversion to the new format. Use the provided migration script.

- Modified API signatures for improved type safety - some function calls may require parameter updates. Enable type checking to identify required changes.


- MLFlow integration - replaced with modular experiment tracking interfaces

- Hard-coded openstef-dbc database connections - superseded by flexible data adapter system

- XGBoost gblinear dependency - removed in favor of pluggable model architecture

- Fixed Dutch holiday calendar - replaced with configurable holiday calendar system

- Rigid input data format requirements - superseded by flexible data validation framework

- Hard-coded Alliander-specific configurations - replaced with customizable configuration system

- Monolithic preprocessing pipeline - split into modular, composable preprocessing components

- Direct database query methods - replaced with abstract data source interfaces


- Increased test coverage and streamlined test execution for improved reliability

- Standardized coding practices and documentation styles across the codebase

- Centralized data preprocessing logic to reduce duplication between validation and model components

- Enhanced type safety throughout the codebase to catch bugs early

- Improved error handling and validation for edge cases in forecasting pipelines

- Optimized performance for production use cases with efficient implementations

- Fixed inconsistencies in data format handling across different modules

- Resolved issues with rigid input data constraints that limited flexibility

- Enhanced support for diverse data availability scenarios in forecasting workflows

- Improved modularity to simplify integration of new models and features


Version 3.x.x (Legacy)
----------------------


OpenSTEF version 3.x is now considered legacy and is no longer actively maintained. Users are strongly encouraged to upgrade to OpenSTEF 4.0, which introduces significant improvements in code quality, architectural design, and broader domain applicability. The 4.0 release offers enhanced modularity, better type safety, improved documentation, and more flexible configuration mechanisms that make the library more robust and easier to integrate into diverse forecasting applications.


.. note::

   Users still on OpenSTEF version 3.x should refer to the migration guide for upgrading to version 4.0. The new version introduces significant architectural improvements including enhanced modularity, better type safety, and broader domain applicability. See the migration documentation for detailed upgrade instructions and breaking changes.


3.8.0 - 2024-XX-XX (Final v3 Release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Final code quality improvements including increased test coverage and standardized coding practices

- Enhanced documentation with clearer assumptions and requirements throughout the library

- Improved data preprocessing logic centralization to reduce duplication

- Bug fixes for edge cases in forecasting pipeline components

- Performance optimizations for production use cases

- Final stability improvements before transitioning to OpenSTEF 4.0 architecture

- Enhanced error handling and logging throughout the codebase

- Compatibility updates for latest dependency versions

- Final refinements to the getting started guide and user onboarding experience


.. note::

   This is the final release in the OpenSTEF 3.x series. Version 3.8.0 marks the end of active development for the v3 branch. Users are strongly encouraged to begin planning their migration to OpenSTEF 4.0, which introduces significant architectural improvements including enhanced modularity, better type safety, decoupled dependencies, and broader domain applicability. Support for OpenSTEF 3.x will be limited to critical bug fixes only, with no new features planned. The OpenSTEF 4.0 release will provide comprehensive migration guides and tools to help users transition from v3 to the new architecture.


Earlier Versions
----------------


For information about changes and updates in OpenSTEF versions prior to 4.0, please refer to the project's GitHub repository release notes and commit history. Version 4.0 represents a significant architectural evolution of the library, building upon lessons learned from version 3.0 and earlier releases to improve code quality, modularity, and broader domain applicability.


.. note::

   For complete version history and detailed release notes, visit the OpenSTEF GitHub repository's releases page at https://github.com/OpenSTEF/openstef/releases. This includes all historical changes, bug fixes, and feature additions across all versions of the library.


Migration Guides
----------------


When upgrading between major versions of OpenSTEF, following the migration guides is crucial to ensure a smooth transition and maintain the stability of your forecasting workflows. Major version updates often introduce breaking changes, architectural improvements, and new dependencies that can significantly impact existing implementations. The migration guides provide step-by-step instructions for updating your code, configuration files, and data structures to be compatible with the new version. They also highlight deprecated features, new requirements, and best practices for leveraging enhanced functionality. Skipping these guides or attempting to upgrade without proper preparation can lead to runtime errors, degraded performance, or unexpected behavior in your forecasting pipelines. Since OpenSTEF is a library that integrates into larger systems, proper migration ensures that your entire application stack continues to function correctly after the upgrade.


- Migration Guide: OpenSTEF 3.x to 4.0 - Major architectural changes and breaking API updates

- Migration Guide: OpenSTEF 2.x to 3.0 - Model interface updates and configuration changes

- Migration Guide: OpenSTEF 1.x to 2.0 - Core functionality restructuring and dependency updates


Contributing to Changelog
-------------------------


The OpenSTEF changelog follows the Keep a Changelog format, which provides a structured and standardized way to document changes between releases. This format organizes entries by version and categorizes changes into types such as Added, Changed, Deprecated, Removed, Fixed, and Security, making it easy for users and contributors to understand what has changed in each release of the library.


This changelog page is automatically generated from the source CHANGELOG.md file in the OpenSTEF repository. For the most up-to-date information or to contribute changelog entries, please refer to the CHANGELOG.md file on GitHub.


