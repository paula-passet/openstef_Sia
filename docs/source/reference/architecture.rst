Architecture
============

OpenSTEF V4 introduces a modular monorepo architecture designed for flexibility, maintainability, and enterprise integration. This page explains how the library's components work together and how you can leverage this modular design in your forecasting applications.

Monorepo Structure
------------------

OpenSTEF V4 is structured as a modular monorepo containing multiple self-contained packages that work together to provide comprehensive forecasting capabilities. Each package has a specific responsibility and can be used independently or as part of the complete OpenSTEF ecosystem.

.. note::
   [DIAGRAM: Repository-level architecture showing the five main packages (openstef-core, openstef-models, openstef-meta, openstef-beam, openstef-dbc) and their relationships, based on FOSDEM 2026 presentation slide]

The monorepo contains five core packages:

- **openstef-core**: Foundation layer with data types, interfaces, and shared utilities
- **openstef-models**: Machine learning models, preprocessing, and feature engineering
- **openstef-meta**: Advanced ensemble models and meta-learning capabilities  
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics
- **openstef-dbc**: Database connectivity and task orchestration (separate package)

Core Package (openstef-core)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The core package provides the foundation for all other OpenSTEF components. It defines common data structures, base classes, and interfaces that ensure consistency across the entire library.

Key components:

- **Data types and interfaces**: Standardized data structures for time series, forecasts, and model configurations
- **Base model classes**: Abstract interfaces that all forecasting models implement
- **Shared exceptions**: Common error handling across all packages
- **Testing utilities**: Shared test fixtures and utilities for consistent testing

.. code-block:: python

   from openstef_core.datasets import Dataset
   from openstef_core.base_model import BaseModel
   
   # Core provides standardized interfaces
   class CustomModel(BaseModel):
       def fit(self, data: Dataset) -> None:
           # Implementation using core interfaces
           pass

Models Package (openstef-models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The models package contains the machine learning components for forecasting, including preprocessing pipelines, feature engineering, and model implementations.

.. note::
   [DIAGRAM: Component-level diagram for openstef-models showing the flow from raw data through transforms, feature engineering, model training, to forecast output with explainability features]

Key components:

- **Transforms**: Data preprocessing and feature engineering pipelines
- **Models**: Model-agnostic forecasting implementations (XGBoost, Linear, etc.)
- **Explainability**: Tools for understanding model predictions and feature importance
- **Presets**: Pre-configured setups for common use cases

.. code-block:: python

   from openstef_models.models import XGBQuantileModel
   from openstef_models.transforms import WeatherTransform
   
   # Models package provides ready-to-use components
   model = XGBQuantileModel()
   weather_transform = WeatherTransform()
   
   # Transform and train in a pipeline
   transformed_data = weather_transform.fit_transform(raw_data)
   model.fit(transformed_data)

Meta Package (openstef-meta)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The meta package implements advanced ensemble methods and meta-learning approaches for improved forecasting performance.

Key components:

- **Modern ensemble models**: Advanced combination techniques
- **Meta-learning algorithms**: Learning from multiple forecasting tasks
- **Advanced model architectures**: Sophisticated forecasting approaches

BEAM Package (openstef-beam)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

BEAM (Backtesting, Evaluation, Analysis, Metrics) provides comprehensive tools for model evaluation and performance analysis.

.. note::
   [DIAGRAM: BEAM package workflow showing backtesting simulation, evaluation metrics calculation, analysis visualization, and benchmarking comparison across multiple models]

Key components:

- **Backtesting**: Simulate historical model performance
- **Evaluation**: Structured performance reporting
- **Analysis**: Visualization and reporting tools
- **Metrics**: Energy-specific performance measures
- **Benchmarking**: Compare multiple models systematically

.. code-block:: python

   from openstef_beam.backtesting import BacktestRunner
   from openstef_beam.metrics import energy_metrics
   
   # BEAM provides comprehensive evaluation
   backtest = BacktestRunner(model, historical_data)
   results = backtest.run()
   
   # Calculate energy-specific metrics
   metrics = energy_metrics(results.predictions, results.actuals)

Package Interactions
--------------------

The modular design allows packages to work together seamlessly while maintaining clear separation of concerns.

Data Flow Architecture
^^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Data flow diagram showing how data moves through the system - from input data through core data structures, models package for training/prediction, BEAM for evaluation, and meta for ensemble methods]

1. **Data ingestion**: Raw time series data enters through core data structures
2. **Preprocessing**: Models package transforms and engineers features
3. **Training/Prediction**: Models package performs machine learning operations
4. **Evaluation**: BEAM package analyzes model performance
5. **Ensemble**: Meta package combines multiple model outputs
6. **Results**: Structured forecasts with uncertainty quantification

Dependency Relationships
^^^^^^^^^^^^^^^^^^^^^^^^

The packages follow a clear dependency hierarchy:

- **openstef-core**: No dependencies on other OpenSTEF packages (foundation layer)
- **openstef-models**: Depends on openstef-core for base classes and data types
- **openstef-meta**: Depends on openstef-core and openstef-models
- **openstef-beam**: Depends on openstef-core and openstef-models for evaluation
- **openstef-dbc**: Depends on all packages for orchestration and data connectivity

This hierarchy ensures clean separation and allows you to use only the components you need.

Integration Patterns
--------------------

The modular architecture supports different integration approaches depending on your use case.

Library Integration
^^^^^^^^^^^^^^^^^^^

Use OpenSTEF as a Python library by importing specific components:

.. code-block:: python

   # Minimal integration - just forecasting
   from openstef_models.models import XGBQuantileModel
   from openstef_core.datasets import Dataset
   
   model = XGBQuantileModel()
   model.fit(training_data)
   forecast = model.predict(future_data)

.. code-block:: python

   # Full integration - complete pipeline
   from openstef_models.transforms import FeatureEngineer
   from openstef_beam.evaluation import ModelEvaluator
   from openstef_meta.ensemble import EnsembleModel
   
   # Build complete forecasting pipeline
   pipeline = Pipeline([
       FeatureEngineer(),
       EnsembleModel([model1, model2]),
       ModelEvaluator()
   ])

Custom Component Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The modular design makes it easy to extend OpenSTEF with custom components:

.. code-block:: python

   from openstef_core.base_model import BaseModel
   from openstef_models.transforms import BaseTransform
   
   class CustomTransform(BaseTransform):
       def transform(self, data):
           # Your custom preprocessing logic
           return transformed_data
   
   class CustomModel(BaseModel):
       def fit(self, data):
           # Your custom model implementation
           pass

Design Principles
-----------------

The V4 architecture follows key design principles that guide component interaction and development:

**Modularity First**: Each package can function independently and be composed into larger systems. You can use just the models package for basic forecasting or combine all packages for comprehensive analysis.

**Type Safety**: Full type annotations throughout the codebase ensure reliable component interaction and catch integration errors early.

**Extensibility**: Clear interfaces make it straightforward to add custom models, transforms, and metrics without modifying core OpenSTEF code.

**Performance**: Efficient implementations optimized for production use cases, with careful attention to memory usage and computational efficiency.

**Unopinionated Design**: The library doesn't enforce specific deployment patterns or data sources, allowing integration into diverse environments and workflows.

This modular architecture makes OpenSTEF V4 suitable for everything from research notebooks to enterprise-scale deployments, while maintaining the flexibility to adapt to your specific forecasting requirements.