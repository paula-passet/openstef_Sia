Repository Structure
====================

OpenSTEF follows a modular mono-repository architecture designed to promote code reuse, maintainability, and flexible deployment patterns. This page explains the structure and relationships between the different components.

.. [DIAGRAM: Mono-repo structure showing core → models → meta/beam dependency graph]

Component Overview
------------------

The OpenSTEF repository is organized into four main components with clear dependency relationships:

**openstef-core**
  Foundation layer providing core data types, interfaces, and shared utilities. All other components depend on this base layer.

**openstef-models** 
  Machine learning forecasting capabilities, preprocessing pipelines, and model explainability features. Depends on openstef-core.

**openstef-meta**
  Ensemble models and meta-learning algorithms for advanced forecasting scenarios. Depends on both openstef-core and openstef-models.

**openstef-beam**
  Backtesting framework, evaluation metrics, and analysis tools for model validation and performance assessment. Depends on openstef-core and openstef-models.

Dependency Architecture
-----------------------

The components follow a layered dependency structure:

- **Core Layer**: openstef-core (no internal dependencies)
- **Application Layer**: openstef-models (depends on core)  
- **Advanced Layer**: openstef-meta and openstef-beam (depend on core and models)

This design ensures that:

- Core functionality remains stable and lightweight
- Models can be used independently of advanced features
- Meta-learning and backtesting capabilities build on the solid foundation
- Components can be deployed selectively based on use case requirements

Benefits of Modular Architecture
--------------------------------

**Selective Deployment**
  Users can install only the components they need. For example, a simple forecasting application might only require openstef-core and openstef-models.

**Clear Separation of Concerns**
  Each component has a well-defined responsibility, making the codebase easier to understand and maintain.

**Independent Development**
  Teams can work on different components without interfering with each other, as long as they respect the interface contracts.

**Testing and Validation**
  Components can be tested in isolation, and the dependency structure prevents circular dependencies that complicate testing.

**Extensibility**
  New components can be added that depend on existing layers without modifying the core functionality.

Directory Structure
-------------------

The repository follows Python packaging conventions with each component as a separate package:

.. code-block:: text

   openstef/
   ├── openstef-core/
   │   ├── openstef/
   │   │   ├── core/
   │   │   └── __init__.py
   │   └── setup.py
   ├── openstef-models/
   │   ├── openstef/
   │   │   ├── models/
   │   │   └── __init__.py
   │   └── setup.py
   ├── openstef-meta/
   │   ├── openstef/
   │   │   ├── meta/
   │   │   └── __init__.py
   │   └── setup.py
   └── openstef-beam/
       ├── openstef/
       │   ├── beam/
       │   └── __init__.py
       └── setup.py

Integration Patterns
--------------------

**Full Installation**
  Install all components for complete functionality:

.. code-block:: bash

   pip install openstef[all]

**Minimal Installation**
  Install only core forecasting capabilities:

.. code-block:: bash

   pip install openstef-core openstef-models

**Custom Combinations**
  Install specific combinations based on your use case:

.. code-block:: bash

   # For backtesting and evaluation
   pip install openstef-core openstef-models openstef-beam
==========================================================
   # For ensemble modeling
   pip install openstef-core openstef-models openstef-meta