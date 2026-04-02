Architecture
============

OpenSTEF is built as a modular Python library with a clear separation of concerns. This page explains how the library's components fit together and how they interact during typical forecasting workflows.

Understanding the architecture helps you customize OpenSTEF for your specific use case, whether you're building a simple forecasting pipeline or integrating it into a complex production system.

.. note:: [DIAGRAM: Sia-style repository-level architecture showing the mono-repo structure with three main library packages (openstef-core, openstef-models, openstef-beam) and their relationships. Reference: FOSDEM 2026 presentation slide showing package dependencies and data flow.]


Repository Structure
--------------------

OpenSTEF is organized as a mono-repository containing three core library packages. Each package has a focused responsibility and can be used independently or together:

**openstef-core**
   Provides fundamental data structures, datasets, and utilities. This package defines the ``TimeSeriesDataset`` type used throughout OpenSTEF and handles data versioning and validation. Use this package when you need OpenSTEF's data abstractions without the full modeling stack.

**openstef-models**
   Contains machine learning models, feature engineering transforms, and explainability tools. This is where forecasting models live, from XGBoost and LightGBM implementations to component splitting models. The ``transforms`` module provides feature engineering pipelines that prepare raw time series data for modeling.

**openstef-beam**
   Handles backtesting, evaluation, analysis, and metrics (BEAM). This package lets you test how models would have performed historically, calculate forecast accuracy metrics, and generate reports. Essential for validating model performance before deployment.

These packages build on each other: ``openstef-models`` depends on ``openstef-core``, and ``openstef-beam`` depends on both. You can install just what you need for your use case.


Core Package Architecture
-------------------------

The ``openstef-core`` package provides the foundation for all OpenSTEF functionality. Its architecture centers on typed datasets and validation:

.. note:: [DIAGRAM: Sia-style component diagram for openstef-core showing the relationships between TimeSeriesDataset, EnergyComponentDataset, validation utilities, and the versioned dataset system. Show data flow from raw inputs through validation to typed datasets.]

The ``datasets`` module defines structured data types that ensure consistency across the library. ``TimeSeriesDataset`` wraps pandas DataFrames with metadata and validation, catching common data quality issues early. ``EnergyComponentDataset`` extends this for component splitting use cases where you need to track multiple energy sources.

The ``utils`` module provides helper functions for common operations like time zone handling and data manipulation. The ``exceptions`` module defines custom error types that make debugging easier by providing clear error messages specific to forecasting workflows.

This architecture makes it straightforward to integrate OpenSTEF with your existing data infrastructure—just convert your data to a ``TimeSeriesDataset`` and the rest of the library handles validation automatically.


Models Package Architecture
---------------------------

The ``openstef-models`` package implements the forecasting logic through three main subsystems:

.. note:: [DIAGRAM: Sia-style component diagram for openstef-models showing the interaction between TransformPipeline, model implementations (XGBQuantileOpenstfRegressor, LGBMQuantileOpenstfRegressor, etc.), ComponentSplittingModel, and explainability tools. Show how data flows through preprocessing transforms, model training/prediction, and postprocessing.]

**Transform Pipeline System**

Feature engineering happens through ``TransformPipeline``, a composable system for chaining data transformations. Each transform takes a dataset as input and returns a modified dataset. Common transforms include:

- Weather feature engineering (temperature, wind speed, solar radiation)
- Time-based features (hour of day, day of week, holidays)
- Lag features (previous load values)
- Rolling statistics (moving averages, trends)

You can create custom transforms by implementing the transform interface. The pipeline automatically handles fitting on training data and applying the same transformations to prediction data.

**Model Implementations**

OpenSTEF provides several model implementations, all following a consistent interface:

.. code-block:: python

   from openstef_models.models.xgb import XGBQuantileOpenstfRegressor
   from openstef_core.datasets import TimeSeriesDataset
   
   # All models follow the same interface
   model = XGBQuantileOpenstfRegressor()
   model.fit(training_data)
   predictions = model.predict(new_data)

The quantile models (XGBQuantile, LGBMQuantile) produce probabilistic forecasts with confidence intervals, essential for risk-aware decision making. Linear models provide interpretable baselines. Component splitting models decompose total load into constituent parts like solar and wind generation.

**Explainability Tools**

The ``explainability`` module helps you understand what drives your forecasts. It provides SHAP value calculation, feature importance analysis, and visualization tools. This is crucial for building trust in production systems and debugging unexpected predictions.


BEAM Package Architecture
--------------------------

The ``openstef-beam`` package implements a complete evaluation framework:

.. note:: [DIAGRAM: Sia-style component diagram for openstef-beam showing the workflow from backtesting through metrics calculation to analysis and reporting. Show how backtesting generates predictions, evaluation structures results, metrics quantify performance, and analysis produces visualizations.]

**Backtesting System**

The ``backtesting`` module simulates how models would have performed in production. It walks through historical data, training models and generating predictions as if you were running in real-time. This reveals issues like data leakage or concept drift that wouldn't show up in simple train/test splits.

**Evaluation Framework**

The ``evaluation`` module organizes forecasting results into structured reports. It handles the complexity of comparing multiple models across different forecast horizons and time periods. Results are stored in a consistent format that feeds into analysis and metrics calculation.

**Metrics and Analysis**

The ``metrics`` module calculates forecast accuracy measures like MAE, RMSE, and skill scores. These quantify how well models perform compared to baselines. The ``analysis`` module turns these numbers into actionable insights through visualizations and reports.

The ``benchmarking`` module ties everything together, running complete comparison studies across multiple forecasting targets. This is how you determine which model works best for your specific use case.


Workflow Patterns
-----------------

OpenSTEF supports several workflow patterns depending on your needs:

**Simple Forecasting Workflow**

For basic use cases, you work directly with models:

.. code-block:: python

   from openstef_models.models.xgb import XGBQuantileOpenstfRegressor
   from openstef_models.transforms import TransformPipeline
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create and configure model
   model = XGBQuantileOpenstfRegressor()
   
   # Add feature engineering
   pipeline = TransformPipeline()
   pipeline.add_weather_features()
   pipeline.add_time_features()
   
   # Train and predict
   processed_data = pipeline.fit_transform(training_data)
   model.fit(processed_data)
   predictions = model.predict(new_data)

**Custom Workflow Pattern**

For advanced use cases, create custom workflows with callbacks:

.. code-block:: python

   from openstef_models.workflows import CustomForecastWorkflow
   from openstef_models.callbacks import CallbackList
   
   # Define custom behavior through callbacks
   callbacks = CallbackList()
   callbacks.add(data_quality_check)
   callbacks.add(model_monitoring)
   callbacks.add(result_validation)
   
   # Workflow manages the complete process
   workflow = CustomForecastWorkflow(
       model=model,
       preprocessing=pipeline,
       callbacks=callbacks
   )
   
   workflow.fit(training_data)
   predictions = workflow.predict(new_data)

Workflows provide hooks for logging, monitoring, data validation, and custom business logic. They're the recommended pattern for production deployments where you need observability and control.

**Component Splitting Workflow**

For energy component decomposition:

.. code-block:: python

   from openstef_models.workflows import CustomComponentSplitWorkflow
   from openstef_models.models.component_splitting import ComponentSplittingModel
   
   workflow = CustomComponentSplitWorkflow(
       model=ComponentSplittingModel(
           component_splitter=splitter,
           preprocessing=pipeline,
           source_column="total_load"
       ),
       callbacks=callbacks
   )
   
   workflow.fit(training_data)
   components = workflow.predict(new_data)

This pattern separates total load into components like solar generation, wind generation, and base load. Useful for understanding the composition of your forecasts.


Integration Points
------------------

OpenSTEF is designed to integrate with your existing infrastructure:

**Data Integration**

The library works with pandas DataFrames, making it easy to connect to any data source. Wrap your data in a ``TimeSeriesDataset`` and you're ready to forecast. See :doc:`../guides/how_to_guides` for examples of integrating with S3, Databricks, InfluxDB, and other systems.

**Model Persistence**

Models can be serialized and loaded for deployment. The library handles versioning to ensure compatibility between training and prediction environments.

**Orchestration**

OpenSTEF is a library, not an application—you control the orchestration. Use cron jobs for simple deployments or integrate with Dagster, Airflow, or other workflow engines for complex scenarios. See :doc:`../guides/how_to_guides` for deployment patterns.

**Monitoring and Observability**

Workflows provide callback hooks for logging, metrics collection, and alerting. Integrate with your monitoring stack to track forecast quality and model performance over time.


Design Principles
-----------------

Understanding these principles helps you work with OpenSTEF effectively:

**Modularity**

Each package and component has a single, well-defined responsibility. You can use just the pieces you need and replace components with custom implementations when necessary.

**Type Safety**

Typed datasets catch errors early. The library validates data at boundaries, failing fast with clear error messages rather than producing incorrect forecasts.

**Composability**

Transforms, models, and workflows compose naturally. Build complex pipelines from simple, reusable components.

**Extensibility**

Implement standard interfaces to add custom transforms, models, or workflows. The library provides the structure; you provide the domain-specific logic.


Next Steps
----------

Now that you understand OpenSTEF's architecture:

- See :doc:`../getting_started/quickstart` for hands-on examples
- Read :doc:`concepts` for deeper explanations of forecasting concepts
- Check :doc:`../guides/use_cases` to identify which components you need
- Explore :doc:`../api/index` for detailed API documentation