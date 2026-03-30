Architecture
============

OpenSTEF V4 is built as a modular Python machine learning library for short-term energy forecasting. Understanding its architecture helps you choose the right components for your use case and integrate them effectively into your forecasting workflows.

.. note:: [DIAGRAM: Repository-level architecture showing how mono-repo components fit together, based on FOSDEM 2026 presentation slide]

Modular Design Philosophy
-------------------------

OpenSTEF V4 follows a "modularity first" approach where each package can work independently while providing clear interfaces for composition into larger systems. This design enables flexible deployment patterns from research notebooks to enterprise production systems.

The library is structured as a mono-repo containing multiple self-contained packages:

- **openstef-core**: Foundation data types and interfaces
- **openstef-models**: Machine learning models and feature engineering
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics
- **openstef-meta**: Meta-learning and ensemble models

Core Package (openstef-core)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The core package provides the foundational components that all other packages depend on. It establishes common data structures, base classes, and shared utilities.

.. note:: [DIAGRAM: Core package component diagram showing data types, interfaces, base classes, and their relationships]

**Key Components:**

- **Data Types**: Standardized structures for time series data, prediction jobs, and model configurations
- **Base Interfaces**: Abstract classes defining contracts for models, transforms, and data providers
- **Shared Exceptions**: Common error types used across all packages
- **Testing Utilities**: Helpers for consistent testing patterns

The core package ensures type safety throughout the library and provides the foundation for extensibility. When you create custom models or transforms, you implement the interfaces defined here.

.. code-block:: python

   from openstef_core.base_model import BaseModel
   from openstef_core.datasets import Dataset
   
   # Core provides the foundation for all other components
   class CustomModel(BaseModel):
       def fit(self, dataset: Dataset) -> None:
           # Your implementation here
           pass

Models Package (openstef-models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The models package contains the machine learning components for training and prediction. It's designed to be model-agnostic, supporting various algorithms while providing energy-specific optimizations.

.. note:: [DIAGRAM: Models package architecture showing the relationship between models, transforms, feature engineering, and explainability components]

**Key Components:**

- **Forecasting Models**: XGBoost, linear models, and other algorithms optimized for energy forecasting
- **Feature Engineering**: Energy-specific transformations like weather lag features and calendar effects
- **Data Preprocessing**: Pipelines for cleaning, validation, and preparation
- **Explainability**: Tools for understanding model predictions and feature importance
- **Presets**: Pre-configured setups for common use cases

The models package emphasizes performance and provides presets that work well out-of-the-box for typical energy forecasting scenarios.

.. code-block:: python

   from openstef_models.models import XGBoostModel
   from openstef_models.transforms import WeatherTransform
   
   # Models package provides ready-to-use forecasting components
   model = XGBoostModel(preset="congestion_forecast")
   transform = WeatherTransform(lag_hours=[1, 24, 168])

BEAM Package (openstef-beam)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

BEAM (Backtesting, Evaluation, Analysis, Metrics) provides comprehensive tools for assessing forecast quality and comparing model performance. Originally developed as an internal Alliander project, it became a core part of OpenSTEF V4.

.. note:: [DIAGRAM: BEAM package workflow showing the flow from backtesting through evaluation to analysis and reporting]

**Key Components:**

- **Backtesting**: Simulate historical performance to validate model changes
- **Evaluation**: Structured performance reports with energy-specific metrics
- **Analysis**: Visualization and interpretation tools for forecast results
- **Metrics**: Specialized measures like rMAE, rCRPS, and peak detection accuracy
- **Benchmarking**: Automated comparison studies across multiple forecasting targets

BEAM answers the critical question: "Are my model changes statistically significant?" It provides regression testing capabilities to ensure new models actually improve performance.

.. code-block:: python

   from openstef_beam.backtesting import BacktestRunner
   from openstef_beam.metrics import calculate_rmae
   
   # BEAM provides comprehensive evaluation capabilities
   runner = BacktestRunner(models=[model_v1, model_v2])
   results = runner.run_backtest(historical_data)
   
   # Compare performance with energy-specific metrics
   rmae_scores = calculate_rmae(results.predictions, results.actuals)

Meta Package (openstef-meta)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The meta package focuses on advanced ensemble methods and meta-learning approaches. It provides modern model architectures that can combine predictions from multiple base models.

.. note:: [DIAGRAM: Meta-learning architecture showing how ensemble models combine base model predictions]

**Key Components:**

- **Ensemble Models**: Sophisticated methods for combining multiple forecasts
- **Meta-Learning**: Algorithms that learn how to best combine different models
- **Advanced Architectures**: State-of-the-art forecasting approaches

The meta package is designed for users who need cutting-edge performance and are willing to invest in more complex model architectures.

Package Interactions
--------------------

The packages interact through well-defined interfaces, enabling flexible composition while maintaining clear separation of concerns.

.. note:: [DIAGRAM: Package interaction diagram showing data flow and dependencies between core, models, beam, and meta packages]

**Typical Workflow:**

1. **Core** provides data structures and base interfaces
2. **Models** implements forecasting algorithms using core interfaces
3. **BEAM** evaluates model performance using standardized metrics
4. **Meta** combines models using ensemble techniques

**Example Integration:**

.. code-block:: python

   from openstef_core.datasets import load_dataset
   from openstef_models.models import XGBoostModel
   from openstef_beam.evaluation import evaluate_forecast
   from openstef_meta.ensemble import WeightedEnsemble
   
   # Load data using core utilities
   dataset = load_dataset("energy_consumption.csv")
   
   # Train models using the models package
   model1 = XGBoostModel(preset="transport_forecast")
   model2 = XGBoostModel(preset="congestion_forecast")
   
   model1.fit(dataset.train)
   model2.fit(dataset.train)
   
   # Create ensemble using meta package
   ensemble = WeightedEnsemble([model1, model2])
   predictions = ensemble.predict(dataset.test)
   
   # Evaluate using BEAM
   results = evaluate_forecast(predictions, dataset.test.targets)

Design Principles in Practice
-----------------------------

The modular architecture embodies several key design principles:

**Modularity First**
   Each package can be used independently. You can use only the models package for simple forecasting without needing BEAM or meta components.

**Type Safety**
   All interfaces use type hints to catch integration errors early and improve code maintainability.

**Extensibility**
   Clear interfaces make it straightforward to add custom models, transforms, or metrics without modifying core library code.

**Performance**
   Components are optimized for production use with efficient implementations and minimal overhead.

**Unopinionated Design**
   The library supports multiple use cases rather than being built for a single scenario, allowing flexibility in how you compose components.

This architectural approach enables OpenSTEF to serve diverse deployment scenarios from research experimentation to enterprise integration while maintaining code quality and performance. For specific implementation guidance, see the :doc:`../getting_started/tutorials` and :doc:`../guides/how_to_guides` sections.