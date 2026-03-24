Repository Structure
====================

OpenSTEF is organized as a mono-repository with a modular architecture designed around clear dependency relationships and separation of concerns. This structure enables users to install only the components they need while maintaining clean interfaces between different functionality layers.

.. [DIAGRAM: Mono-repo structure showing core → models → meta/beam dependency graph]

Component Overview
==================

The OpenSTEF repository contains four main components with a clear dependency hierarchy:

Core Foundation
---------------

**openstef-core**
  The foundational layer containing data types, interfaces, and core abstractions. This module defines the essential building blocks that all other components depend on, including:
  
  - Base data structures and type definitions
  - Core interfaces for models and pipelines
  - Configuration management systems
  - Common utilities and helper functions

Machine Learning Layer
----------------------

**openstef-models**
  Built on top of openstef-core, this module provides the primary machine learning functionality for energy forecasting:
  
  - Individual ML model implementations (XGBoost, LightGBM, Linear models)
  - Data preprocessing and feature engineering
  - Model training and inference pipelines
  - Explainability and interpretability tools
  - Probabilistic forecasting capabilities

Advanced Functionality
----------------------

**openstef-meta**
  Extends the models layer with ensemble and meta-learning capabilities:
  
  - Ensemble model implementations
  - Meta-learning algorithms for model selection
  - Advanced forecasting strategies
  - Model combination and weighting techniques

**openstef-beam**
  Provides backtesting, evaluation, and analysis tools:
  
  - Comprehensive backtesting framework
  - Performance evaluation metrics
  - Analysis and reporting tools
  - Benchmarking utilities
  - Historical performance assessment

Dependency Relationships
========================

The modular architecture follows a strict dependency hierarchy:

.. code-block:: text

   openstef-core (foundation)
        ↑
   openstef-models (ML forecasting)
        ↑
   openstef-meta & openstef-beam (advanced features)

This design ensures:

- **Clean separation**: Each component has a well-defined responsibility
- **Minimal dependencies**: Users can install only what they need
- **Type safety**: Full type safety throughout the dependency chain
- **Extensibility**: Clear interfaces for adding custom functionality

Benefits of Modular Architecture
=================================

Flexible Installation
---------------------

Users can choose their installation level based on their needs:

.. code-block:: bash

   # Minimal installation - core functionality only
   pip install openstef-core
   
   # Standard installation - includes ML models
   pip install openstef-models
   
   # Full installation - all components
   pip install openstef[all]

Development Efficiency
----------------------

The modular structure supports:

- **Independent development**: Teams can work on different components simultaneously
- **Focused testing**: Each component can be tested in isolation
- **Clear interfaces**: Well-defined boundaries between components
- **Easier maintenance**: Changes in one component have minimal impact on others

Production Deployment
---------------------

Organizations can deploy only the components they need:

- **Reduced footprint**: Smaller deployments with fewer dependencies
- **Better security**: Fewer dependencies mean reduced attack surface
- **Easier updates**: Update individual components without affecting the entire system
- **Custom integrations**: Build custom solutions using specific components

Integration Patterns
====================

The modular architecture supports various integration patterns:

**Standalone Usage**
  Use individual components for specific tasks without the full OpenSTEF pipeline.

**Full Pipeline**
  Leverage all components together for comprehensive forecasting workflows.

**Custom Combinations**
  Mix and match components to create domain-specific solutions.

**External Integration**
  Integrate OpenSTEF components into existing systems and workflows.