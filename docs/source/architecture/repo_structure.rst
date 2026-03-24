Repository Structure
====================

OpenSTEF V4 is structured as a **modular mono-repo** with multiple self-contained packages. This architecture provides flexibility for different deployment scenarios while maintaining clear separation of concerns.

.. note::
   OpenSTEF is a Python library, not a deployable application. Each module can be used independently or combined to build custom energy forecasting applications.

Core Architecture
-----------------

The mono-repo contains five main modules that work together to provide comprehensive forecasting capabilities:

.. mermaid::

   graph TB
       A[openstef-core] --> B[openstef-models]
       A --> C[openstef-meta]
       A --> D[openstef-beam]
       B --> C
       B --> D
       
       subgraph "Foundation Layer"
           A
       end
       
       subgraph "ML & Forecasting"
           B
           C
       end
       
       subgraph "Evaluation & Analysis"
           D
       end

Module Overview
---------------

openstef-core
~~~~~~~~~~~~~

**Foundation module** providing shared infrastructure for all other components.

**Contains:**
- Data types, interfaces, and base classes
- Shared exceptions and testing utilities
- Common configuration structures

**Role:** Establishes the foundation that all other modules build upon, ensuring consistency across the entire system.

openstef-models
~~~~~~~~~~~~~~~

**Primary forecasting module** containing the core machine learning functionality.

**Contains:**
- Forecasting models (model-agnostic implementation)
- Data preprocessing pipelines
- Energy-specific transformations
- Explainability features
- Presets for quick start scenarios

**Role:** Handles the main forecasting workflow from data preparation through model training and prediction generation.

openstef-meta
~~~~~~~~~~~~~

**Meta-learning module** providing advanced ensemble capabilities.

**Contains:**
- Modern ensemble models
- Advanced model architectures
- Meta-learning algorithms

**Role:** Extends basic forecasting with sophisticated ensemble methods and advanced modeling techniques.

openstef-beam
~~~~~~~~~~~~~

**Backtesting, Evaluation, Analysis, and Metrics module** for comprehensive model assessment.

**Contains:**
- Backtesting frameworks
- Performance evaluation metrics
- Regression testing against benchmarks
- Statistical analysis tools

**Role:** Answers the critical question "Are my model changes significant?" through rigorous evaluation methodologies.

Integration Patterns
--------------------

The modular design supports different integration approaches:

**Standalone Usage**
   Each module can be used independently for specific tasks (e.g., using only ``openstef-beam`` for evaluation of external models).

**Full Pipeline**
   All modules work together to provide end-to-end forecasting capabilities from data ingestion to performance analysis.

**Custom Combinations**
   Users can combine specific modules based on their requirements (e.g., ``openstef-core`` + ``openstef-models`` for basic forecasting without meta-learning).

Benefits of Modular Architecture
---------------------------------

**Flexibility**
   Deploy only the components needed for your specific use case.

**Maintainability**
   Clear separation of concerns makes the codebase easier to understand and modify.

**Extensibility**
   New modules can be added without affecting existing functionality.

**Testing**
   Each module can be tested independently, improving overall code quality.

**Performance**
   Load only the functionality you need, reducing memory footprint and startup time.