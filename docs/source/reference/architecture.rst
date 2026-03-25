Architecture
============

OpenSTEF V4 adopts a modular monorepo architecture designed to provide maximum flexibility while maintaining clear separation of concerns. This architecture enables users to compose forecasting solutions from well-defined components, whether for research experimentation, small-scale deployments, or enterprise integration.

.. note:: [DIAGRAM: Repository-level architecture showing the four core packages and their relationships, based on FOSDEM 2026 slide]

Monorepo Structure
------------------

OpenSTEF V4 is organized as a modular monorepo containing four self-contained packages that can be used independently or together:

**openstef-core**
   The foundation package providing shared data types, interfaces, and base classes. Contains common exceptions and testing utilities used across all other modules. This package defines the core abstractions that enable interoperability between components.

**openstef-models**
   The primary forecasting package containing model-agnostic implementations, data preprocessing pipelines, and energy-specific transformations. Includes explainability features and presets for quick start scenarios. This is where most users will interact with the library's forecasting capabilities.

**openstef-meta**
   Advanced meta-learning capabilities including modern ensemble models and sophisticated model architectures. Provides state-of-the-art forecasting techniques for users requiring maximum accuracy.

**openstef-beam**
   Backtesting, Evaluation, Analysis, and Metrics package that answers the critical question: "Are my model changes significant?" Includes regression testing against benchmarks and was originally developed as an internal Alliander project before becoming a core part of OpenSTEF V4.

.. note:: [DIAGRAM: Component-level architecture for openstef-meta showing internal structure and interfaces, similar to Sia diagrams shown in community meetings]

Design Principles
-----------------

The V4 architecture follows several key principles that guide component interaction and system design:

**Modularity First**
   Each component works in isolation and can be easily composed into larger systems. Dependencies between packages are explicit and minimal.

**Unopinionated Design**
   The library avoids assumptions about specific use cases, deployment environments, or data sources. Users can adapt components to their specific requirements.

**Type Safety**
   Full type safety throughout the codebase catches bugs early and improves maintainability. All interfaces use proper type annotations.

**Performance**
   Efficient implementations optimized for production use cases without compromising on model quality or execution speed.

Component Interactions
----------------------

The modular design enables flexible composition patterns depending on your use case:

.. code-block:: python

   # Simple forecasting with presets
   from openstef.models import create_forecast_pipeline
   from openstef.core import PredictionJob
   
   # Create a forecast using preset configuration
   pipeline = create_forecast_pipeline(preset="transport_forecast")
   forecast = pipeline.predict(data, prediction_job)

.. code-block:: python

   # Advanced meta-learning approach
   from openstef.meta import EnsembleModel
   from openstef.models import XGBModel, LinearModel
   from openstef.beam import BacktestEvaluator
   
   # Combine multiple models with meta-learning
   ensemble = EnsembleModel([XGBModel(), LinearModel()])
   evaluator = BacktestEvaluator()
   
   # Evaluate ensemble performance
   results = evaluator.evaluate(ensemble, test_data)

.. note:: [DIAGRAM: Data flow diagram showing how components interact during training and prediction workflows]

Data Flow Architecture
----------------------

OpenSTEF processes data through a well-defined pipeline that separates concerns and enables customization at each stage:

**Data Ingestion**
   Raw time series data enters through standardized interfaces defined in openstef-core. The library supports various data availability constraints including delayed measurements and weather forecasts.

**Feature Engineering**
   Data preprocessing and feature creation happens in openstef-models using configurable pipelines. Energy-specific transformations handle domain requirements like seasonal patterns and weather dependencies.

**Model Training**
   Training occurs through model-agnostic interfaces that support multiple algorithms. The system handles hyperparameter optimization and cross-validation automatically.

**Prediction Generation**
   Forecasts are generated using trained models with confidence intervals and quantile predictions. The system supports both point forecasts and probabilistic outputs.

**Evaluation and Analysis**
   openstef-beam provides comprehensive evaluation metrics and backtesting capabilities to assess model performance and compare different approaches.

Integration Patterns
--------------------

The modular architecture supports three primary integration patterns:

**Research and Experimentation**
   Use Jupyter notebooks with pre-built components and flexible APIs for quick prototyping. Educational tutorials and examples provide starting points for custom implementations.

**Small-Scale Deployments**
   Deploy using Docker Compose with minimal infrastructure requirements. Clear migration paths exist from examples to production environments.

**Enterprise Integration**
   Integrate with existing systems using pipeline APIs and flexible callback mechanisms. Custom component development is supported through well-defined interfaces.

The architecture ensures that users can start simple and scale complexity as needed, whether adding custom models, integrating with enterprise systems, or deploying at scale.