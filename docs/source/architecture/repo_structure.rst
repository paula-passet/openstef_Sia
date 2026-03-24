Repository Structure
====================

OpenSTEF follows a modular mono-repository architecture designed to promote code reuse, maintainability, and clear separation of concerns. The repository is organized into distinct modules with well-defined dependencies and responsibilities.

.. [DIAGRAM: Mono-repo structure showing core → models → meta/beam dependency graph]

Module Architecture
-------------------

The OpenSTEF repository consists of four main modules arranged in a dependency hierarchy:

**openstef-core** → **openstef-models** → **openstef-meta/beam**

This structure ensures that:

- Core functionality remains stable and lightweight
- Model implementations can evolve independently
- Advanced features build upon solid foundations
- Dependencies flow in one direction, preventing circular imports

Core Module (openstef-core)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The foundation layer providing essential data types, interfaces, and utilities used throughout the entire system.

**Key Components:**

- **Data Types**: Standardized data structures for forecasts, predictions, and configurations
- **Interfaces**: Abstract base classes defining contracts for models, transformers, and pipelines
- **Utilities**: Common helper functions for data manipulation, validation, and type checking
- **Configuration**: Base configuration classes and validation logic

**Purpose**: Establishes the fundamental building blocks that all other modules depend on, ensuring consistency and type safety across the entire codebase.

Models Module (openstef-models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The machine learning layer containing forecasting algorithms, preprocessing logic, and model explainability tools.

**Key Components:**

- **ML Forecasting**: XGBoost, LightGBM, and Linear model implementations
- **Preprocessing**: Feature engineering, data validation, and transformation pipelines
- **Explainability**: Model interpretation tools and feature importance analysis
- **Model Selection**: Automatic model selection and hyperparameter optimization

**Dependencies**: Built on top of openstef-core, using its data types and interfaces.

**Purpose**: Provides the core forecasting capabilities while maintaining flexibility for different model types and use cases.

Meta Module (openstef-meta)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Advanced modeling capabilities including ensemble methods and meta-learning approaches.

**Key Components:**

- **Ensemble Models**: Combining multiple base models for improved performance
- **Meta-Learning**: Learning from multiple forecasting tasks to improve generalization
- **Advanced Algorithms**: Sophisticated modeling techniques beyond basic ML approaches

**Dependencies**: Builds upon both openstef-core and openstef-models.

**Purpose**: Extends basic forecasting with advanced techniques for complex scenarios and improved accuracy.

Beam Module (openstef-beam)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Evaluation and analysis tools for comprehensive model assessment and backtesting.

**Key Components:**

- **Backtesting**: Historical performance evaluation across multiple time periods
- **Evaluation Metrics**: Comprehensive suite of forecasting accuracy measures
- **Analysis Tools**: Statistical analysis and performance visualization
- **Benchmarking**: Comparative analysis between different models and approaches

**Dependencies**: Utilizes openstef-core for data types and openstef-models for model implementations.

**Purpose**: Provides robust evaluation capabilities essential for production forecasting systems.

Benefits of Modular Architecture
---------------------------------

**Maintainability**
  Clear separation of concerns makes the codebase easier to understand, modify, and extend.

**Flexibility**
  Users can import only the modules they need, reducing dependencies and deployment complexity.

**Testing**
  Each module can be tested independently, improving test coverage and reliability.

**Development**
  Teams can work on different modules simultaneously without conflicts.

**Extensibility**
  New functionality can be added to appropriate modules without affecting the entire system.

Integration Patterns
---------------------

The modular structure supports various integration approaches:

**Full Stack Usage**
  Import all modules for complete forecasting capabilities including advanced features and comprehensive evaluation.

**Lightweight Deployment**
  Use only core and models modules for basic forecasting in resource-constrained environments.

**Custom Extensions**
  Build custom modules that depend on core interfaces while extending functionality for specific use cases.

.. note::
   The dependency hierarchy ensures that breaking changes in higher-level modules (meta, beam) do not affect lower-level modules (core, models), providing stability for basic use cases while allowing innovation in advanced features.