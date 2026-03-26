Architecture
============

OpenSTEF V4 introduces a modular architecture designed for flexibility, extensibility, and enterprise integration. Understanding this architecture helps you leverage the library's components effectively and integrate them into your forecasting workflows.

.. note:: [DIAGRAM: Repository-level architecture showing mono-repo structure with openstef-core, openstef-models, openstef-beam, and openstef-meta packages and their relationships]

Modular Design Principles
--------------------------

OpenSTEF V4 is structured as a **modular mono-repo** with multiple self-contained packages that can be used independently or together. This design follows several key principles:

- **Modularity First**: Components work in isolation and compose into larger systems
- **Type Safety**: Full type safety throughout the codebase for early bug detection
- **Extensibility**: Clear interfaces for adding custom models, transforms, and metrics
- **Performance**: Efficient implementations optimized for production use cases

The modular approach allows you to use only the components you need. For example, you might use ``openstef-models`` for forecasting without requiring the full evaluation capabilities of ``openstef-beam``.

Core Package (openstef-core)
-----------------------------

The foundation package provides shared data types, interfaces, and utilities used across all other modules:

- **Data types and interfaces**: Common data structures for time series and forecasting models
- **Base classes**: Abstract base classes that define the contract for forecasting components
- **Shared exceptions**: Consistent error handling across the library
- **Testing utilities**: Common test fixtures and helpers

.. code-block:: python

   from openstef_core.datasets import Dataset
   from openstef_core.base_model import BaseForecastingModel
   
   # Core data structures used throughout OpenSTEF
   dataset = Dataset.from_csv("energy_data.csv")

.. note:: [DIAGRAM: openstef-core component showing data types, base classes, exceptions, and utilities modules]

Models Package (openstef-models)
---------------------------------

The models package contains the machine learning pipeline components for forecasting:

- **Forecasting models**: Model-agnostic implementations supporting various ML algorithms
- **Data preprocessing**: Feature engineering and data transformation pipelines
- **Energy-specific transformations**: Domain knowledge for energy forecasting (e.g., solar radiation to PV generation)
- **Explainability features**: Tools for understanding model predictions
- **Presets for quick start**: Pre-configured models for common use cases

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.transforms import WeatherTransform
   
   # Create a complete forecasting pipeline
   model = ForecastingModel(
       preprocessor=WeatherTransform(),
       forecaster="xgboost"
   )
   
   # Train and predict
   model.fit(train_data)
   forecast = model.predict(forecast_horizon=48)

.. note:: [DIAGRAM: openstef-models component showing preprocessing, models, transforms, and explainability modules with data flow]

BEAM Package (openstef-beam)
-----------------------------

BEAM (Backtesting, Evaluation, Analysis, Metrics) provides comprehensive model evaluation and performance analysis:

- **Backtesting**: Simulate real-world forecasting performance
- **Evaluation**: Structured performance reports and metrics
- **Analysis**: Visualizations and insights from evaluation results
- **Metrics**: Energy-specific forecasting metrics
- **Benchmarking**: Compare multiple models across forecasting targets

.. code-block:: python

   from openstef_beam.backtesting import Backtester
   from openstef_beam.metrics import energy_score, mae
   
   # Evaluate model performance
   backtester = Backtester(
       model=model,
       metrics=[energy_score, mae]
   )
   
   results = backtester.run(test_data, n_splits=10)

.. note:: [DIAGRAM: openstef-beam component showing backtesting, evaluation, analysis, metrics, and benchmarking modules]

Meta Package (openstef-meta)
-----------------------------

The meta-learning package provides advanced ensemble models and modern architectures:

- **Modern ensemble models**: State-of-the-art ensemble techniques
- **Advanced model architectures**: Cutting-edge forecasting approaches
- **Meta-learning algorithms**: Models that learn from multiple forecasting tasks

This package extends the core forecasting capabilities with research-oriented and advanced production techniques.

Package Interactions
---------------------

The packages interact through well-defined interfaces, enabling flexible composition:

.. code-block:: python

   # Complete workflow using multiple packages
   from openstef_core.datasets import Dataset
   from openstef_models.models import ForecastingModel
   from openstef_beam.evaluation import ModelEvaluator
   
   # Load data using core utilities
   dataset = Dataset.from_influxdb(connection_params)
   
   # Create and train model
   model = ForecastingModel.from_preset("congestion_management")
   model.fit(dataset.train_split())
   
   # Evaluate performance
   evaluator = ModelEvaluator(model)
   performance = evaluator.evaluate(dataset.test_split())

.. note:: [DIAGRAM: Package interaction flow showing data flow from openstef-core through openstef-models to openstef-beam, with openstef-meta as an optional enhancement layer]

Integration Patterns
---------------------

OpenSTEF V4's modular architecture supports various integration patterns:

**Research and Experimentation**
   Use individual components in notebooks with flexible APIs for custom implementations

**Small-Scale Deployments**
   Combine packages into simple forecasting services with minimal infrastructure

**Enterprise Integration**
   Integrate specific components into existing ML pipelines using the library's flexible interfaces

The architecture ensures you can start simple and scale complexity as your forecasting needs grow, while maintaining the ability to customize any component of the pipeline.

For detailed API documentation of each package, see the API Reference. To understand how these components work together in practice, explore the tutorials and use case guides available in the documentation.