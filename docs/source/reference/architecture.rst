Architecture
============

OpenSTEF V4 is designed as a modular machine learning library for short-term energy forecasting. This page explains the architectural decisions behind the library's structure and how the different components work together to provide a flexible, extensible forecasting framework.

Design Principles
-----------------

OpenSTEF V4 follows several key architectural principles that guide its design:

- **Modularity First**: Components work in isolation and can be easily composed into larger systems
- **Machine Learning Library Focus**: Remains focused on forecasting and evaluation, not application deployment
- **Unopinionated Design**: Not built for a single use case, supporting diverse forecasting scenarios
- **Performance**: No compromise on model quality or execution speed
- **Extensibility**: Clear interfaces for adding custom models, transforms, and metrics

These principles ensure that OpenSTEF can adapt to different organizational needs while maintaining its core strength as a forecasting library.

Repository Structure
--------------------

.. note:: [DIAGRAM: Mono-repo structure showing the relationship between core packages, their dependencies, and how they compose into the main OpenSTEF library]

OpenSTEF V4 is structured as a modular mono-repo containing multiple self-contained packages. Each package serves a specific purpose and can be used independently or in combination:

.. code-block:: text

   openstef/
   ├── packages/
   │   ├── openstef-core/          # Foundation layer
   │   ├── openstef-models/        # Forecasting models
   │   ├── openstef-beam/          # Evaluation framework
   │   └── openstef-meta/          # Advanced ensembles
   └── openstef/                   # Main package combining all components

This structure allows users to install only the components they need while maintaining compatibility across the entire ecosystem.

Core Package Architecture
-------------------------

.. note:: [DIAGRAM: Component-level diagram showing openstef-core internal structure with data types, interfaces, base classes, and shared utilities]

The ``openstef-core`` package provides the foundation for all other components:

- **Data Types**: Standardized representations for time series data, forecasts, and energy components
- **Base Classes**: Abstract interfaces that define contracts for models and transforms
- **Shared Utilities**: Common functionality used across all packages
- **Exception Handling**: Consistent error handling throughout the library

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseModel
   
   # Core data structures are used throughout the library
   dataset = TimeSeriesDataset.from_dataframe(df)
   
   # All models inherit from base classes defined in core
   class CustomModel(BaseModel):
       def fit(self, data: TimeSeriesDataset) -> None:
           pass

Models Package Architecture
---------------------------

.. note:: [DIAGRAM: Component-level diagram showing openstef-models structure with preprocessing pipelines, model implementations, and feature engineering components]

The ``openstef-models`` package handles the complete forecasting workflow:

- **Preprocessing Pipelines**: Data cleaning, feature engineering, and transformation
- **Model Implementations**: Forecasting algorithms and ensemble methods
- **Energy-Specific Features**: Domain knowledge encoded as reusable transforms
- **Explainability Tools**: Model interpretation and feature importance analysis

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.transforms import WeatherTransform
   
   # Models combine preprocessing, forecasting, and postprocessing
   model = ForecastingModel(
       preprocessor=WeatherTransform(),
       forecaster="xgboost",
       postprocessor=None
   )
   
   model.fit(train_data)
   forecast = model.predict(test_data)

BEAM Package Architecture
-------------------------

.. note:: [DIAGRAM: Component-level diagram showing openstef-beam evaluation framework with backtesting, metrics, analysis, and benchmarking components]

The ``openstef-beam`` package (Backtesting, Evaluation, Analysis, Metrics) provides comprehensive model evaluation:

- **Backtesting**: Simulate historical performance to validate model improvements
- **Metrics**: Energy-specific performance measures for forecasting accuracy
- **Analysis**: Transform evaluation results into actionable insights
- **Benchmarking**: Compare multiple models across different forecasting targets

.. code-block:: python

   from openstef_beam.backtesting import BacktestRunner
   from openstef_beam.metrics import energy_score, quantile_loss
   
   # Comprehensive evaluation workflow
   runner = BacktestRunner(
       models=[model1, model2],
       metrics=[energy_score, quantile_loss]
   )
   
   results = runner.run_backtest(historical_data)
   analysis = runner.analyze_results(results)

Component Interactions
----------------------

.. note:: [DIAGRAM: System-level diagram showing how all packages interact during a typical forecasting workflow, from data input through model training to evaluation]

The packages work together in a layered architecture:

1. **Data Layer** (``openstef-core``): Provides consistent data structures and interfaces
2. **Model Layer** (``openstef-models``): Implements forecasting algorithms using core interfaces
3. **Evaluation Layer** (``openstef-beam``): Validates model performance using standardized metrics
4. **Advanced Layer** (``openstef-meta``): Adds sophisticated ensemble methods and meta-learning

This separation allows each component to evolve independently while maintaining compatibility. Users can replace individual components with custom implementations without affecting the rest of the system.

Integration Patterns
--------------------

OpenSTEF V4's modular architecture supports several integration patterns:

**Library Integration**: Import specific components into existing Python applications:

.. code-block:: python

   from openstef_models import ForecastingModel
   from openstef_beam import BacktestRunner
   
   # Use only the components you need
   model = ForecastingModel.from_preset("congestion_forecast")
   model.fit(your_data)

**Pipeline Integration**: Compose components into custom forecasting pipelines:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms import FeatureEngineeringPipeline
   from openstef_models.models import ComponentSplittingModel
   
   # Build custom workflows
   pipeline = FeatureEngineeringPipeline([
       WeatherTransform(),
       CalendarTransform(),
       LagTransform(lags=[1, 24, 168])
   ])
   
   model = ComponentSplittingModel(preprocessor=pipeline)

**Enterprise Integration**: Flexible APIs for integration with existing systems and custom deployment patterns. The modular design makes it easy to embed OpenSTEF components into larger applications while maintaining clear separation of concerns.

For specific implementation examples, see the :doc:`../getting_started/tutorials` and :doc:`../guides/how_to_guides` sections.