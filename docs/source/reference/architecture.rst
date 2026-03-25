Architecture
============

OpenSTEF V4 introduces a fundamentally redesigned architecture that transforms the library from a monolithic package into a modular, composable system. This architectural evolution enables better maintainability, easier integration, and clearer separation of concerns while preserving the library's core forecasting capabilities.

.. note::
   [DIAGRAM: Repository-level architecture showing mono-repo structure with openstef-core, openstef-models, openstef-meta, and openstef-beam packages and their relationships]

Design Principles
-----------------

OpenSTEF V4 is built around five core architectural principles that guide all design decisions:

**Modularity First**
   Components work in isolation and compose easily into larger systems. Each package has clear boundaries and minimal dependencies on others.

**Type Safety**
   Full type safety throughout the codebase catches bugs early and improves maintainability. All interfaces use proper type annotations.

**Extensibility**
   Clear interfaces enable adding custom models, transforms, and metrics without modifying core code. The plugin architecture supports custom components.

**Performance**
   Efficient implementations optimized for production use cases maintain OpenSTEF's reputation for fast, accurate forecasting.

**Unopinionated Design**
   The library provides building blocks rather than prescriptive solutions, supporting diverse use cases from research to enterprise deployment.

Mono-repo Structure
-------------------

OpenSTEF V4 organizes functionality into four self-contained packages within a single repository. This mono-repo approach simplifies development while maintaining clear module boundaries.

.. note::
   [DIAGRAM: Component-level diagram showing internal structure of each package and key interfaces]

Core Packages
^^^^^^^^^^^^^

**openstef-core**
   The foundation layer provides data types, interfaces, and base classes used throughout the system. Contains shared exceptions, testing utilities, and common abstractions that other packages depend on.

**openstef-models**
   The primary forecasting engine includes model-agnostic implementations, data preprocessing pipelines, energy-specific transformations, and explainability features. Provides presets for quick start scenarios.

**openstef-meta**
   Advanced meta-learning capabilities with modern ensemble models and sophisticated model architectures. Handles complex forecasting scenarios requiring multiple model coordination.

**openstef-beam**
   Backtesting, Evaluation, Analysis, and Metrics functionality answers the critical question: "Are my model changes significant?" Includes regression testing against benchmarks and comprehensive evaluation tools.

Package Interactions
^^^^^^^^^^^^^^^^^^^^

The packages interact through well-defined interfaces that maintain loose coupling:

- **openstef-core** serves as the foundation, providing common types and interfaces
- **openstef-models** depends on core for base classes and implements the primary forecasting logic  
- **openstef-meta** builds on both core and models to provide advanced ensemble capabilities
- **openstef-beam** uses all other packages for comprehensive evaluation and backtesting

This dependency structure ensures that users can install only the components they need while maintaining compatibility across the ecosystem.

Component Architecture
----------------------

Within each package, OpenSTEF follows a layered architecture that separates concerns and enables flexible customization.

Data Flow Architecture
^^^^^^^^^^^^^^^^^^^^^^

The library processes forecasting requests through a series of well-defined stages:

1. **Data Ingestion**: Flexible input handling supports various data sources and formats
2. **Feature Engineering**: Energy-specific transformations create predictive features
3. **Model Training/Inference**: Model-agnostic pipeline handles diverse ML approaches  
4. **Post-processing**: Confidence intervals, quantiles, and domain-specific adjustments
5. **Evaluation**: Comprehensive metrics and visualization for model assessment

.. note::
   [DIAGRAM: Data flow diagram showing the progression from raw data through feature engineering, modeling, and evaluation]

Interface Design
^^^^^^^^^^^^^^^^

Each component exposes clean interfaces that enable customization without breaking the overall system:

- **Transformers**: Standardized feature engineering components
- **Models**: Pluggable forecasting algorithms following scikit-learn conventions
- **Evaluators**: Extensible metrics and assessment tools
- **Pipelines**: Composable workflows that orchestrate the complete forecasting process

Migration from V3
------------------

The V4 architecture represents a significant evolution from the V3 monolithic design. Key changes include:

**Modular Structure**
   V3's single package becomes four focused packages with clear responsibilities.

**Decoupled Dependencies**
   External dependencies like MLFlow and database connectors are no longer tightly integrated, improving portability.

**Enhanced Type Safety**
   Complete type annotations replace V3's mixed typing approach.

**Flexible Configuration**
   Hard-coded assumptions give way to configurable parameters and extensible interfaces.

For detailed migration guidance, see the how-to guides section which covers the transition process and compatibility considerations.

Integration Patterns
---------------------

The modular architecture supports three primary integration patterns:

**Research and Experimentation**
   Use individual components in Jupyter notebooks with minimal setup. The modular design enables quick prototyping and experimentation.

**Small-Scale Deployment**
   Compose packages into lightweight applications using Docker or similar containerization. Clear interfaces simplify integration with existing systems.

**Enterprise Integration**
   Leverage the plugin architecture and flexible APIs to integrate with complex enterprise systems. Custom components can extend functionality without modifying core code.

Each pattern benefits from the same underlying architecture while providing appropriate abstractions for different scales and requirements.