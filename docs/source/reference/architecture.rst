Architecture
============

OpenSTEF is designed as a modular machine learning library for short-term energy forecasting. This page explains the architectural decisions, component relationships, and design principles that make OpenSTEF flexible and maintainable.

Design Philosophy
-----------------

OpenSTEF follows several key architectural principles:

- **Library-first approach**: OpenSTEF is a Python library, not an application. It provides building blocks for forecasting systems rather than a complete end-to-end solution.
- **Modular design**: Components are loosely coupled and can be used independently or combined as needed.
- **Unopinionated architecture**: The library supports multiple use cases without forcing specific implementation patterns.
- **Performance focus**: No compromise on model quality or execution speed.
- **Standards compliance**: Leverages existing Python ecosystem tools rather than reinventing functionality.

Repository Structure
--------------------

.. note:: [DIAGRAM: Repository-level architecture showing mono-repo structure with core packages and their relationships, similar to FOSDEM 2026 slide]

OpenSTEF V4 is structured as a **modular mono-repo** containing multiple self-contained packages. This approach provides several benefits:

- **Unified versioning**: All packages are released together with consistent version numbers
- **Shared development**: Common tooling, testing, and CI/CD across all components
- **Clear boundaries**: Each package has well-defined responsibilities and interfaces
- **Independent usage**: Packages can be installed and used separately when needed

The repository contains these core packages:

.. code-block:: python

   # Install all packages together
   pip install openstef
   
   # Or install individual packages
   pip install openstef-core
   pip install openstef-models
   pip install openstef-beam

Core Package Architecture
-------------------------

.. note:: [DIAGRAM: Component-level diagram for openstef-core showing data types, interfaces, and base classes]

The ``openstef-core`` package provides the foundation for all other OpenSTEF components:

**Data Types and Interfaces**
   Core data structures for time series, forecasts, and model configurations. These types ensure consistency across all OpenSTEF packages.

**Base Classes**
   Abstract base classes that define contracts for models, transformations, and evaluation components.

**Shared Utilities**
   Common functionality used throughout the library, including data validation, configuration management, and testing utilities.

**Exception Handling**
   Standardized exception hierarchy for consistent error handling across all packages.

.. code-block:: python

   from openstef_core.datasets import Dataset
   from openstef_core.base_model import BaseForecastingModel
   from openstef_core.exceptions import OpenSTEFError

Models Package Architecture
---------------------------

.. note:: [DIAGRAM: Component-level diagram for openstef-models showing preprocessing pipelines, model implementations, and explainability features]

The ``openstef-models`` package implements the core forecasting functionality:

**Forecasting Models**
   Model-agnostic implementations including single forecasters and ensemble methods. All models inherit from the base interfaces defined in ``openstef-core``.

**Data Preprocessing**
   Feature engineering pipelines specifically designed for energy forecasting, including weather integration, lag features, and temporal transformations.

**Energy-Specific Transformations**
   Domain-specific preprocessing for energy data, such as component splitting for solar and wind generation.

**Explainability Features**
   Tools for understanding model predictions and feature importance, crucial for operational forecasting systems.

**Presets for Quick Start**
   Pre-configured model pipelines for common use cases, allowing users to get started quickly without deep configuration.

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.transforms import WeatherTransform
   from openstef_models.explainability import FeatureImportance

BEAM Package Architecture
-------------------------

.. note:: [DIAGRAM: Component-level diagram for openstef-beam showing backtesting, evaluation, analysis, and metrics components]

The ``openstef-beam`` package (Backtesting, Evaluation, Analysis, Metrics) handles model validation and performance assessment:

**Backtesting Framework**
   Simulates how models would perform in real operational conditions, accounting for data availability constraints and forecast horizons.

**Evaluation Metrics**
   Comprehensive metrics specifically designed for energy forecasting, including accuracy measures, reliability indicators, and business-relevant KPIs.

**Analysis Tools**
   Transforms evaluation results into actionable insights through visualizations and statistical analysis.

**Benchmarking System**
   Enables systematic comparison of different models and configurations across multiple forecasting targets.

.. code-block:: python

   from openstef_beam.backtesting import BacktestRunner
   from openstef_beam.metrics import ForecastMetrics
   from openstef_beam.analysis import PerformanceAnalyzer

Package Interactions
--------------------

.. note:: [DIAGRAM: Data flow diagram showing how packages interact during typical forecasting workflow]

The packages work together in a layered architecture:

1. **Foundation Layer** (``openstef-core``): Provides data types and interfaces
2. **Implementation Layer** (``openstef-models``): Implements forecasting algorithms
3. **Validation Layer** (``openstef-beam``): Evaluates and analyzes model performance
4. **Extension Layer** (``openstef-meta``): Advanced ensemble methods and meta-learning

A typical forecasting workflow demonstrates these interactions:

.. code-block:: python

   from openstef_core.datasets import Dataset
   from openstef_models.models import ForecastingModel
   from openstef_beam.evaluation import ModelEvaluator
   
   # Load data using core data types
   dataset = Dataset.from_csv("energy_data.csv")
   
   # Create and train model using models package
   model = ForecastingModel.from_preset("solar_pv")
   model.fit(dataset.train_data)
   
   # Generate forecasts
   forecasts = model.predict(dataset.test_data)
   
   # Evaluate performance using BEAM package
   evaluator = ModelEvaluator()
   metrics = evaluator.evaluate(forecasts, dataset.test_targets)

Integration Patterns
--------------------

The modular architecture supports several integration patterns:

**Standalone Usage**
   Each package can be used independently for specific tasks like data preprocessing or model evaluation.

**Custom Workflows**
   Users can combine packages in custom ways, implementing their own orchestration and data flow.

**Enterprise Integration**
   The flexible architecture accommodates complex software landscapes with custom APIs and policies.

**Research and Development**
   Researchers can extend individual components without affecting the entire system.

This architectural approach makes OpenSTEF suitable for a wide range of deployment scenarios, from simple research projects to large-scale operational forecasting systems.

For more details on using specific components, see the :doc:`../api/index` and :doc:`../getting_started/tutorials`.