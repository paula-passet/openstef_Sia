Architecture
============

OpenSTEF is designed as a modular machine learning library with a clear separation of concerns across multiple packages. This architecture enables flexible integration into diverse forecasting workflows while maintaining high performance and extensibility.

Repository-Level Architecture
-----------------------------

OpenSTEF V4 uses a **modular mono-repo** structure that organizes functionality into self-contained packages while enabling seamless integration between components.

.. note:: [DIAGRAM: Repository overview showing the mono-repo structure with packages/openstef-core, packages/openstef-models, packages/openstef-beam, and packages/openstef-meta, along with their primary responsibilities and dependencies]

The workspace is defined in the root ``pyproject.toml`` file:

.. code-block:: python

   [tool.uv.workspace]
   members = [
       "packages/openstef-models",
       "packages/openstef-beam", 
       "packages/openstef-core",
       "docs",
   ]

This structure provides several key benefits:

- **Unified development**: All packages are developed together with automatic dependency resolution
- **Modular deployment**: Each package can be installed independently based on use case requirements
- **Clear interfaces**: Well-defined APIs between packages prevent tight coupling
- **Flexible integration**: Components can be used individually or combined into complete forecasting pipelines

Core Package Architecture
-------------------------

The ``openstef-core`` package serves as the foundation for all other OpenSTEF components, providing shared data structures, interfaces, and utilities.

.. note:: [DIAGRAM: Core package internal structure showing datasets, base_model, utils, and exceptions modules with their key classes and relationships]

Key components include:

- **Data types and interfaces**: Common data structures used across all packages
- **Base model classes**: Abstract interfaces that define the forecasting model contract
- **Shared utilities**: Helper functions for data manipulation and validation
- **Exception handling**: Standardized error types for consistent error reporting

.. code-block:: python

   from openstef_core.base_model import BaseForecastingModel
   from openstef_core.datasets import Dataset
   from openstef_core.exceptions import OpenSTEFError

Models Package Architecture  
---------------------------

The ``openstef-models`` package implements the core forecasting functionality with a modular pipeline design.

.. note:: [DIAGRAM: Models package architecture showing the flow from raw data through transforms, models, and explainability components, with clear separation between preprocessing, forecasting, and postprocessing stages]

The package is organized around three main components:

**Transform Pipeline**
   Feature engineering and data preprocessing components that prepare time series data for forecasting models.

**Model Implementations**
   Concrete forecasting models that implement the ``BaseForecastingModel`` interface, including both single models and ensemble approaches.

**Explainability Tools**
   Components for interpreting model predictions and understanding feature importance.

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.transforms import FeatureEngineer
   from openstef_models.explainability import ShapExplainer

   # Create a complete forecasting pipeline
   model = ForecastingModel(
       preprocessor=FeatureEngineer(),
       forecaster=XGBRegressor(),
       postprocessor=QuantileProcessor()
   )

BEAM Package Architecture
-------------------------

The ``openstef-beam`` package (Backtesting, Evaluation, Analysis, Metrics) provides comprehensive model evaluation and comparison capabilities.

.. note:: [DIAGRAM: BEAM package workflow showing the progression from backtesting through evaluation to analysis and benchmarking, with feedback loops for model improvement]

BEAM is structured around four core modules:

**Backtesting**
   Simulates historical forecasting scenarios to test model performance under realistic conditions.

**Evaluation** 
   Organizes forecasting results into structured performance reports with standardized metrics.

**Analysis**
   Transforms evaluation results into visualizations and insights for decision-making.

**Benchmarking**
   Runs comprehensive model comparison studies across multiple forecasting targets.

.. code-block:: python

   from openstef_beam.backtesting import BacktestRunner
   from openstef_beam.evaluation import ModelEvaluator
   from openstef_beam.analysis import PerformanceAnalyzer

   # Run complete model evaluation
   backtest = BacktestRunner(model, historical_data)
   results = backtest.run()
   
   evaluator = ModelEvaluator()
   metrics = evaluator.evaluate(results)
   
   analyzer = PerformanceAnalyzer()
   report = analyzer.generate_report(metrics)

Package Interaction Patterns
-----------------------------

The modular design enables several common usage patterns depending on your forecasting requirements:

**Simple Forecasting**
   Use only ``openstef-core`` and ``openstef-models`` for basic forecasting workflows.

**Production Deployment**
   Combine ``openstef-models`` with custom data integration and orchestration systems.

**Model Development**
   Use all packages together for comprehensive model development, evaluation, and comparison.

**Research Applications**
   Leverage the full stack with ``openstef-meta`` for advanced ensemble methods and experimental approaches.

The architecture's flexibility allows you to start simple and add complexity as your forecasting requirements evolve, making OpenSTEF suitable for both research prototypes and production deployments.