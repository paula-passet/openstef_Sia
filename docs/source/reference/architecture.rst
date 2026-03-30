Architecture
============

OpenSTEF is designed as a modular Python library for short-term energy forecasting. Its architecture emphasizes flexibility, maintainability, and ease of integration while maintaining high performance for production forecasting systems.

Repository Structure
--------------------

OpenSTEF V4 adopts a monorepo architecture with multiple self-contained packages that work together to provide comprehensive forecasting capabilities. This design allows users to install only the components they need while maintaining clear separation of concerns.

.. note::
   [DIAGRAM: Repository-level architecture showing the four main packages (openstef-core, openstef-models, openstef-beam, openstef-meta) and their relationships within the monorepo structure]

The monorepo contains four primary packages:

- **openstef-core**: Foundation layer with shared data types and interfaces
- **openstef-models**: Core forecasting models and feature engineering
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics
- **openstef-meta**: Advanced ensemble models and meta-learning approaches

This structure enables independent development and deployment of each component while ensuring compatibility through shared interfaces defined in the core package.

Core Package (openstef-core)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The core package serves as the foundation for all other OpenSTEF components. It provides essential data structures, base classes, and shared utilities that ensure consistency across the entire library.

.. note::
   [DIAGRAM: Core package internal structure showing datasets, base_model, utils, and exceptions modules with their key classes and interfaces]

Key components include:

- **Base model classes**: Abstract interfaces that define the contract for all forecasting models
- **Dataset management**: Versioned data access and time series handling utilities
- **Shared exceptions**: Consistent error handling across all packages
- **Configuration utilities**: Common configuration patterns used throughout OpenSTEF

The core package has minimal external dependencies, making it lightweight and suitable for embedding in larger systems.

Models Package (openstef-models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The models package contains the primary forecasting functionality, including model implementations, feature engineering pipelines, and preprocessing utilities specifically designed for energy forecasting.

.. note::
   [DIAGRAM: Models package architecture showing the flow from raw data through transforms, models, and explainability components to produce forecasts]

The package is organized around three main areas:

- **Transforms module**: Feature engineering utilities including weather feature creation, lag generation, and energy-specific transformations
- **Models module**: Implementation of forecasting models including single forecasters, ensemble methods, and component splitting approaches
- **Explainability module**: Tools for understanding model behavior and feature importance

This modular design allows users to mix and match components based on their specific forecasting requirements while leveraging proven energy forecasting techniques.

BEAM Package (openstef-beam)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

BEAM (Backtesting, Evaluation, Analysis, Metrics) provides comprehensive model evaluation capabilities. Originally developed as an internal Alliander project, BEAM has been integrated as a core component of OpenSTEF V4.

.. note::
   [DIAGRAM: BEAM package workflow showing the progression from backtesting through evaluation to analysis and final reporting]

The package addresses the critical question: "Are my model changes significant?" through:

- **Backtesting**: Simulates how models would perform in real operational conditions
- **Evaluation**: Organizes forecasting results into structured performance reports  
- **Analysis**: Transforms evaluation results into visualizations and actionable insights
- **Metrics**: Specialized metrics for energy forecasting performance measurement
- **Benchmarking**: Runs complete model comparison studies across multiple targets

BEAM enables rigorous testing and validation of forecasting improvements before deployment to production systems.

Meta Package (openstef-meta)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The meta package focuses on advanced ensemble methods and meta-learning approaches for energy forecasting. It represents the cutting edge of OpenSTEF's forecasting capabilities.

.. note::
   [DIAGRAM: Meta package showing ensemble model architecture with multiple base models feeding into meta-learners to produce improved forecasts]

Key features include:

- **Modern ensemble models**: Advanced techniques for combining multiple forecasting models
- **Meta-learning approaches**: Models that learn how to best combine predictions from other models
- **Advanced model architectures**: Sophisticated forecasting approaches beyond traditional methods

The meta package builds upon the foundation provided by the other packages, using their interfaces and utilities to implement more complex forecasting strategies.

Package Interactions
--------------------

The modular design enables clear separation of concerns while maintaining strong integration between components. Dependencies flow primarily in one direction, with each package building upon the capabilities of its dependencies.

.. note::
   [DIAGRAM: Package dependency graph showing how openstef-models, openstef-beam, and openstef-meta all depend on openstef-core, with optional cross-dependencies between the higher-level packages]

**Dependency relationships:**

- All packages depend on **openstef-core** for shared interfaces and utilities
- **openstef-beam** can evaluate models from **openstef-models** and **openstef-meta**
- **openstef-meta** can ensemble models from **openstef-models**
- Each package can be installed and used independently based on user needs

This architecture supports various deployment scenarios, from simple single-model forecasting to complex ensemble systems with comprehensive evaluation pipelines.

Design Principles
-----------------

OpenSTEF's architecture is guided by several key principles that ensure it remains effective as both a research tool and production system:

**Library-first approach**: OpenSTEF is designed as a Python library, not an application. This makes it easy to integrate into existing systems and workflows while avoiding the complexity of application-specific concerns.

**Modular and unopinionated**: The library provides building blocks that can be combined in different ways rather than prescribing a single approach. Users can choose which components to use based on their specific requirements.

**Performance without compromise**: All architectural decisions prioritize maintaining high-quality forecasts and fast execution times, essential for operational energy systems.

**Data availability awareness**: The design accounts for real-world constraints like delayed measurements and weather forecast availability, ensuring robust operation in production environments.

This architectural foundation enables OpenSTEF to serve diverse use cases while maintaining the flexibility needed for ongoing development and improvement.