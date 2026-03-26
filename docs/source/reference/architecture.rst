Architecture
============

OpenSTEF V4 is built around a modular architecture that separates concerns while maintaining tight integration between components. This design enables flexible deployment patterns while keeping the library focused on its core mission of energy forecasting.

.. note:: [DIAGRAM: Repository-level architecture showing mono-repo structure with openstef-core as foundation, openstef-models and openstef-beam as main packages, and openstef-meta as advanced extension, with arrows showing dependencies and data flow]

Modular Design Philosophy
-------------------------

OpenSTEF follows several key architectural principles that guide its design:

**Library-First Approach**
   OpenSTEF remains a machine learning library focused on forecasting and evaluation, not an application framework. This keeps the API surface clean and integration patterns flexible.

**Unopinionated Design**
   The library provides powerful defaults through presets while remaining flexible enough to support diverse use cases from grid congestion management to district heating forecasts.

**Performance Without Compromise**
   All architectural decisions prioritize model quality and execution speed. The modular structure enables optimizations without sacrificing functionality.

**Leverage Existing Tools**
   Rather than reinventing common functionality, OpenSTEF integrates with established libraries like scikit-learn, XGBoost, and pandas.

Core Package Structure
----------------------

The mono-repo architecture organizes functionality into focused packages with clear dependency relationships:

.. note:: [DIAGRAM: Component-level diagram for openstef-core showing data types, interfaces, base classes, exceptions, and utilities as foundational building blocks]

**openstef-core**
   Provides the foundation for all other packages. Contains data types, interfaces, base classes, shared exceptions, and testing utilities. Every other package depends on core, but core has minimal external dependencies.

**openstef-models**
   Implements the complete forecasting pipeline from data preprocessing to model training and prediction. Includes model-agnostic interfaces, energy-specific transformations, explainability features, and preset configurations for quick starts.

.. note:: [DIAGRAM: Component-level diagram for openstef-models showing preprocessing pipeline, model interfaces, feature engineering, explainability components, and preset configurations]

**openstef-beam** (Backtesting, Evaluation, Analysis, Metrics)
   Handles model evaluation and performance analysis. Originally developed as an internal Alliander project, BEAM answers the critical question: "Are my model changes significant?" It provides regression testing against benchmarks and comprehensive evaluation frameworks.

.. note:: [DIAGRAM: Component-level diagram for openstef-beam showing backtesting engine, metrics calculation, analysis tools, evaluation framework, and benchmarking capabilities]

**openstef-meta** (Meta-learning)
   Contains advanced ensemble models and modern architectures. This package extends the basic forecasting capabilities with sophisticated meta-learning approaches for improved accuracy in complex scenarios.

Package Interactions
^^^^^^^^^^^^^^^^^^^^

The packages interact through well-defined interfaces that maintain loose coupling:

.. code-block:: python

   # Core provides base classes and data types
   from openstef_core.base_model import BaseForecastingModel
   from openstef_core.datasets import Dataset

   # Models implements the forecasting pipeline
   from openstef_models.models import ForecastingModel
   from openstef_models.transforms import FeatureEngineer

   # BEAM evaluates model performance
   from openstef_beam.evaluation import ModelEvaluator
   from openstef_beam.metrics import calculate_forecast_metrics

   # Typical workflow combining packages
   model = ForecastingModel(preset="solar_forecasting")
   model.fit(training_data)
   forecasts = model.predict(forecast_horizon=48)
   
   evaluator = ModelEvaluator()
   metrics = evaluator.evaluate(forecasts, actual_values)

Data Flow Architecture
----------------------

The library processes data through a consistent pipeline regardless of the specific use case:

1. **Data Ingestion**: Time series data enters through the core dataset interfaces
2. **Feature Engineering**: Models package transforms raw data into forecasting features
3. **Model Training/Prediction**: Trained models generate probabilistic forecasts
4. **Evaluation**: BEAM package analyzes forecast quality and provides performance metrics
5. **Analysis**: Results are structured for decision-making through visualization and reporting

This flow remains consistent whether forecasting grid congestion, transport loads, or district heating demand. The modular architecture allows each stage to be customized independently while maintaining end-to-end consistency.

Integration Patterns
--------------------

The modular design supports multiple integration approaches:

**Simple Integration**
   Use presets for common scenarios with minimal configuration. The library handles complexity internally while exposing a clean API.

**Custom Workflows**
   Replace individual components (feature engineering, models, evaluation) while leveraging the rest of the pipeline.

**Enterprise Integration**
   The flexible architecture accommodates complex software landscapes with custom APIs, data policies, and deployment constraints.

The mono-repo structure ensures that all packages evolve together while maintaining stable interfaces between components. This approach provides the benefits of modular design without the complexity of managing separate repositories and version compatibility.