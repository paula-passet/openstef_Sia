Architecture
============

OpenSTEF V4 is built on a modular architecture that separates concerns, enables flexible deployment patterns, and supports diverse forecasting use cases. This page explains how the library's components fit together and how they interact to deliver short-term energy forecasting capabilities.

.. note:: OpenSTEF is a Python library, not a standalone application. The architecture described here focuses on the library's internal structure and how you integrate it into your own systems.


Repository Structure
--------------------

OpenSTEF V4 is organized as a mono-repo containing multiple self-contained Python packages. This structure enables you to install only the components you need while maintaining clear boundaries between different concerns.

.. note:: [DIAGRAM: Mono-repo structure showing packages (openstef-core, openstef-models, openstef-beam, openstef-meta) and their relationships. Based on FOSDEM 2026 presentation slide showing how components fit together in the repository.]

The mono-repo contains four primary packages:

- **openstef-core**: Foundation layer providing data types, interfaces, base classes, and shared utilities
- **openstef-models**: Forecasting models, feature engineering, preprocessing pipelines, and explainability tools
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics for model validation
- **openstef-meta**: Advanced meta-learning and ensemble model architectures (experimental)

Each package is independently installable via pip, allowing you to compose exactly the functionality you need. For example, production forecasting systems might install only ``openstef-models``, while research environments typically install all packages.


Core Package
^^^^^^^^^^^^

The ``openstef-core`` package provides the foundation for all other components:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.exceptions import InputDataError
   
   # Core data structures used throughout OpenSTEF
   dataset = TimeSeriesDataset(
       data=df,
       target_column="load",
       datetime_column="datetime"
   )

This package defines interfaces and base classes that other packages depend on, ensuring consistent data handling across the library. It contains no machine learning logic—only the shared infrastructure.


Models Package
^^^^^^^^^^^^^^

The ``openstef-models`` package implements the forecasting functionality:

.. code-block:: python

   from openstef_models.workflows import TrainPredictWorkflow
   from openstef_models.transforms import FeatureEngineer
   
   # Create and train a forecasting model
   workflow = TrainPredictWorkflow(preset="congestion")
   workflow.fit(train_data)
   forecast = workflow.predict(input_data)

This package includes model implementations (XGBoost, LightGBM, linear models), feature engineering pipelines, data preprocessing, and explainability tools. It's designed to be model-agnostic—you can plug in custom models by implementing the standard interfaces.


BEAM Package
^^^^^^^^^^^^

The ``openstef-beam`` package handles model evaluation and comparison:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline
   from openstef_beam.metrics import calculate_metrics
   
   # Evaluate model performance
   backtest = BacktestPipeline(config=backtest_config)
   results = backtest.run(model, historical_data)
   metrics = calculate_metrics(results)

BEAM originated as an internal Alliander project for answering "Are my model changes significant?" It provides regression testing against benchmarks and comprehensive evaluation reports.


Component Interactions
----------------------

The packages interact through well-defined interfaces, enabling modular composition while maintaining clear dependencies.

.. note:: [DIAGRAM: Component interaction diagram showing data flow between openstef-core (data types), openstef-models (training/prediction), and openstef-beam (evaluation). Show how data flows from raw input through feature engineering to model training/prediction and finally to evaluation.]

Data flows through the system in this pattern:

1. **Input data** arrives as pandas DataFrames or similar structures
2. **openstef-core** wraps data in typed containers (``TimeSeriesDataset``)
3. **openstef-models** applies feature engineering and preprocessing
4. **Models** generate forecasts with uncertainty estimates
5. **openstef-beam** evaluates forecast quality against actuals

Each stage can be customized or replaced without affecting other components. For example, you can implement custom feature engineering while using standard models and evaluation.


Forecasting Workflow Architecture
----------------------------------

OpenSTEF implements a pipeline-based architecture for forecasting workflows. This design separates data preparation, model training, prediction, and evaluation into composable stages.

.. note:: [DIAGRAM: Workflow pipeline showing the sequence: Data Validation → Feature Engineering → Model Training → Prediction → Post-Processing. Include feedback loop from evaluation back to model training.]

Training Pipeline
^^^^^^^^^^^^^^^^^

The training pipeline orchestrates model development:

.. code-block:: python

   from openstef_models.workflows import TrainPredictWorkflow
   
   workflow = TrainPredictWorkflow(
       model_type="xgboost",
       feature_set="standard",
       horizons=[0.25, 24.0, 47.0]
   )
   
   # Pipeline handles: validation → feature engineering → training
   workflow.fit(train_data, validation_data)

Internally, the pipeline executes these steps:

1. **Data validation**: Check for missing values, flatliners, and data quality issues
2. **Feature engineering**: Generate lag features, weather transformations, calendar features
3. **Model training**: Train quantile regression models for probabilistic forecasts
4. **Model evaluation**: Assess performance on validation data

Each step can raise exceptions if data quality is insufficient, preventing unreliable models from reaching production.


Prediction Pipeline
^^^^^^^^^^^^^^^^^^^

The prediction pipeline generates forecasts from trained models:

.. code-block:: python

   # Load trained model and generate forecast
   forecast = workflow.predict(
       input_data,
       horizons=[0.25, 24.0, 47.0]
   )
   
   # Forecast includes quantiles for uncertainty estimation
   print(forecast[["forecast_q50", "forecast_q10", "forecast_q90"]])

The prediction pipeline:

1. Loads the trained model from storage
2. Applies the same feature engineering as training
3. Generates multi-horizon forecasts in a single pass
4. Post-processes results (e.g., component splitting for solar/wind)

This single-shot, multi-horizon approach is more efficient than training separate models for each forecast horizon.


Deployment Patterns
-------------------

OpenSTEF's modular architecture supports multiple deployment patterns, from simple scripts to enterprise-scale systems.

.. note:: [DIAGRAM: Deployment architecture showing three patterns: (1) Notebook/script using openstef-models directly, (2) Scheduled jobs with cron/Dagster orchestration, (3) Enterprise integration with custom data connectors and APIs.]

Library-Only Usage
^^^^^^^^^^^^^^^^^^

The simplest deployment uses OpenSTEF as a library in scripts or notebooks:

.. code-block:: python

   import pandas as pd
   from openstef_models.workflows import TrainPredictWorkflow
   
   # Load your data
   data = pd.read_csv("historical_load.csv")
   
   # Train and predict
   workflow = TrainPredictWorkflow(preset="transport")
   workflow.fit(data)
   forecast = workflow.predict(data)
   
   # Save results
   forecast.to_csv("forecast_output.csv")

This pattern works well for research, experimentation, and small-scale deployments. You handle data retrieval, storage, and orchestration yourself.


Orchestrated Deployment
^^^^^^^^^^^^^^^^^^^^^^^

For operational systems, integrate OpenSTEF with workflow orchestrators:

.. code-block:: python

   # Example: Dagster asset for scheduled forecasting
   from dagster import asset
   from openstef_models.workflows import TrainPredictWorkflow
   
   @asset
   def daily_forecast(context, historical_data):
       workflow = TrainPredictWorkflow.load("model_registry/substation_123")
       forecast = workflow.predict(historical_data)
       return forecast

See :doc:`../guides/how_to_guides` for detailed examples of cron-based and Dagster orchestration.


Enterprise Integration
^^^^^^^^^^^^^^^^^^^^^^

Large organizations typically integrate OpenSTEF into existing data platforms:

.. code-block:: python

   from openstef_models.workflows import TrainPredictWorkflow
   from your_company.data import DataConnector
   
   # Custom data integration
   connector = DataConnector(config)
   train_data = connector.fetch_training_data(location_id)
   
   # Standard OpenSTEF workflow
   workflow = TrainPredictWorkflow(preset="congestion")
   workflow.fit(train_data)
   
   # Custom storage
   connector.save_model(workflow, model_id)

The ``openstef-dbc`` package (separate repository) provides reference implementations for database connectivity, but most enterprises implement custom connectors matching their infrastructure.


Extension Points
----------------

OpenSTEF V4 provides clear extension points for customization without modifying core code.

Custom Models
^^^^^^^^^^^^^

Implement custom forecasting models by inheriting from base interfaces:

.. code-block:: python

   from openstef_core.base_model import BaseForecaster
   
   class CustomNeuralNetwork(BaseForecaster):
       def fit(self, X, y):
           # Your training logic
           pass
       
       def predict(self, X):
           # Your prediction logic
           pass
   
   # Use with standard workflows
   workflow = TrainPredictWorkflow(model=CustomNeuralNetwork())

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add domain-specific features through the transform interface:

.. code-block:: python

   from openstef_models.transforms import BaseTransform
   
   class IndustryHolidayTransform(BaseTransform):
       def transform(self, data):
           # Add custom holiday features
           data["industry_shutdown"] = self.detect_shutdowns(data)
           return data
   
   workflow = TrainPredictWorkflow(
       transforms=[IndustryHolidayTransform(), "standard"]
   )

Custom Metrics
^^^^^^^^^^^^^^

Define custom evaluation metrics for specific use cases:

.. code-block:: python

   from openstef_beam.metrics import BaseMetric
   
   class PeakAccuracyMetric(BaseMetric):
       def calculate(self, forecast, actual):
           # Focus on accuracy during peak hours
           peaks = actual > actual.quantile(0.9)
           return mae(forecast[peaks], actual[peaks])

Design Principles
-----------------

OpenSTEF V4's architecture embodies several key design principles:

**Modularity First**: Components work in isolation and compose cleanly. You can use feature engineering without models, or models without BEAM evaluation.

**Unopinionated Design**: The library doesn't assume a single deployment pattern or use case. It provides building blocks you arrange to match your needs.

**Type Safety**: Full type annotations throughout enable early error detection and better IDE support.

**Performance**: Efficient implementations optimized for production use. No compromise on model quality or execution speed.

**Extensibility**: Clear interfaces for custom models, transforms, and metrics without modifying core code.

These principles guide architectural decisions and ensure OpenSTEF remains flexible as forecasting requirements evolve.


Related Documentation
---------------------

- :doc:`../getting_started/quickstart` - Get started with basic usage patterns
- :doc:`../guides/how_to_guides` - Deployment and integration examples  
- :doc:`concepts` - Understand forecasting concepts and methodology
- :doc:`../guides/use_cases` - See architecture applied to specific use cases