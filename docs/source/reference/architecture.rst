Architecture
============

OpenSTEF is designed as a modular Python machine learning library for short-term energy forecasting. Understanding its architecture helps you leverage the library effectively and integrate it into your own systems. This page provides architectural diagrams at multiple levels and explains how the components interact.

Repository-Level Architecture
------------------------------

OpenSTEF V4 is structured as a modular mono-repo containing multiple self-contained packages that work together to provide comprehensive forecasting capabilities.

.. note::
   [DIAGRAM: Repository-level Sia-style diagram showing the mono-repo structure with openstef-core at the center, connected to openstef-models, openstef-beam, and openstef-meta packages. Shows data flow between packages and external dependencies like scikit-learn, XGBoost, and pandas.]

The mono-repo architecture enables:

- **Coordinated releases** across all components
- **Shared development workflows** and testing infrastructure  
- **Consistent interfaces** between packages
- **Simplified dependency management** for users

Core Design Principles
^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF follows several key architectural principles:

- **Machine learning library focus** - Not an application, but a library for building forecasting solutions
- **Modular design** - Self-contained packages that can be used independently or together
- **Unopinionated approach** - Flexible enough for diverse use cases, not built for a single scenario
- **Performance first** - No compromise on model quality or execution speed
- **Leverage existing tools** - Build on proven libraries rather than reinventing functionality

Package Architecture
--------------------

The library consists of four main packages, each with distinct responsibilities:

Core Package (openstef-core)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Component-level Sia diagram for openstef-core showing modules: datasets (time series data), base_model (interfaces), utils (helpers), and exceptions (error handling). Shows how other packages depend on these foundational components.]

The foundation package providing:

- **Data types and interfaces** - Common structures used across all packages
- **Base classes** - Abstract interfaces for models and transformations
- **Shared utilities** - Helper functions and common operations
- **Exception handling** - Consistent error types across the library

.. code-block:: python

   from openstef_core.datasets import Dataset
   from openstef_core.base_model import BaseModel
   
   # Core provides the foundation for all other packages
   dataset = Dataset.from_csv("energy_data.csv")
   
Models Package (openstef-models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Component-level Sia diagram for openstef-models showing the flow from raw data through transforms (feature engineering), to models (XGBoost, LightGBM, etc.), and finally explainability outputs. Shows presets as a simplified entry point.]

Handles the machine learning pipeline:

- **Model implementations** - XGBoost, LightGBM, and other forecasting models
- **Feature engineering** - Energy-specific data transformations and preprocessing
- **Explainability** - SHAP values and feature importance analysis
- **Presets** - Pre-configured pipelines for common use cases

.. code-block:: python

   from openstef_models.models import XGBModel
   from openstef_models.transforms import WeatherTransform
   from openstef_models.explainability import explain_forecast
   
   # Transform data and train model
   transform = WeatherTransform()
   processed_data = transform.fit_transform(dataset)
   
   model = XGBModel()
   model.fit(processed_data)
   
   # Generate explanations
   explanations = explain_forecast(model, processed_data)

BEAM Package (openstef-beam)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Component-level Sia diagram for openstef-beam showing the evaluation workflow: backtesting generates historical performance data, metrics calculate performance scores, evaluation structures results, analysis creates visualizations, and benchmarking compares multiple models.]

Provides comprehensive model evaluation:

- **Backtesting** - Simulate historical model performance
- **Metrics** - Energy-specific performance measurements
- **Evaluation** - Structured performance reporting
- **Analysis** - Visualization and decision-making tools
- **Benchmarking** - Compare multiple models across targets

.. code-block:: python

   from openstef_beam.backtesting import backtest_model
   from openstef_beam.metrics import calculate_metrics
   from openstef_beam.analysis import create_performance_report
   
   # Evaluate model performance
   backtest_results = backtest_model(model, historical_data)
   metrics = calculate_metrics(backtest_results)
   report = create_performance_report(metrics)

Meta Package (openstef-meta)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Component-level Sia diagram for openstef-meta showing advanced ensemble architectures: multiple base models feeding into meta-learning algorithms that produce improved forecasts. Shows connection to modern deep learning approaches.]

Advanced ensemble and meta-learning capabilities:

- **Ensemble models** - Combine multiple forecasting approaches
- **Meta-learning** - Learn from model performance patterns
- **Advanced architectures** - Modern forecasting techniques

Package Interactions
--------------------

The packages interact in a layered architecture where each builds upon the previous:

Data Flow
^^^^^^^^^

1. **openstef-core** provides the foundational data structures and interfaces
2. **openstef-models** uses core interfaces to implement forecasting models
3. **openstef-beam** evaluates models using core data types
4. **openstef-meta** combines models and evaluation results for advanced ensembles

Dependency Structure
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Example showing package interaction
   from openstef_core.datasets import Dataset
   from openstef_models.models import XGBModel
   from openstef_beam.backtesting import backtest_model
   from openstef_meta.ensemble import EnsembleModel
   
   # Core provides data structures
   dataset = Dataset.from_database(connection)
   
   # Models package handles ML pipeline
   model = XGBModel()
   model.fit(dataset.train_data)
   
   # BEAM evaluates performance
   results = backtest_model(model, dataset.test_data)
   
   # Meta combines multiple approaches
   ensemble = EnsembleModel([model, other_model])
   ensemble.fit(dataset.train_data, validation_results=results)

Integration Patterns
---------------------

The modular architecture supports various integration patterns:

Library Integration
^^^^^^^^^^^^^^^^^^^

Use individual packages as needed in your own applications:

.. code-block:: python

   # Use only the models package
   from openstef_models.models import XGBModel
   
   # Or combine with evaluation
   from openstef_models.models import XGBModel
   from openstef_beam.metrics import calculate_mae

Enterprise Integration
^^^^^^^^^^^^^^^^^^^^^^

The flexible architecture accommodates complex enterprise environments:

- **Custom data connectors** - Integrate with existing data systems
- **API wrappers** - Expose functionality through REST or GraphQL APIs
- **Orchestration** - Use with Airflow, Dagster, or other workflow tools
- **Monitoring** - Integrate with MLOps platforms for model monitoring

For detailed implementation examples, see our :doc:`../guides/how_to_guides` and :doc:`../getting_started/tutorials`.