Architecture Overview
=====================

OpenSTEF is organized as a modular library with three core packages that work together to provide a complete forecasting solution. This architecture separates concerns cleanly: data handling, model training, and evaluation each live in their own package with well-defined interfaces.

The Three-Package Structure
----------------------------

OpenSTEF consists of three packages that form a layered architecture:

**openstef_core** provides the foundation with data structures, datasets, and utilities. This package defines the ``TimeSeriesDataset`` class and other core types that flow through the entire system. It contains no machine learning logic—just the essential building blocks.

**openstef_models** implements machine learning models and feature engineering. This package depends on ``openstef_core`` for data structures but remains independent of evaluation concerns. It includes the ``transforms`` module for feature engineering, the ``models`` module for forecasting algorithms, and ``explainability`` tools for understanding predictions.

**openstef_beam** handles backtesting, evaluation, analysis, and metrics (hence BEAM). This package orchestrates model evaluation workflows, computes performance metrics, and generates visualizations. It depends on both core and models packages to run complete evaluation pipelines.

.. note:: [DIAGRAM: Three-layer architecture showing openstef_core at the base, openstef_models in the middle, and openstef_beam at the top, with dependency arrows pointing upward]

This layered design means you can use ``openstef_core`` and ``openstef_models`` for production forecasting without pulling in evaluation dependencies. The BEAM package is primarily for model development and validation.

Core Package: Data Foundations
-------------------------------

The ``openstef_core`` package provides the data structures that unify the library. The central abstraction is ``TimeSeriesDataset``, which wraps pandas DataFrames with metadata and validation:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   # Create a time series dataset
   data = pd.DataFrame({
       'datetime': pd.date_range('2024-01-01', periods=100, freq='15min'),
       'load': [100, 105, 110, ...],
       'temperature': [5.2, 5.1, 5.3, ...]
   })
   
   dataset = TimeSeriesDataset(
       data=data,
       target_column='load',
       datetime_column='datetime'
   )

The core package also includes:

- **base_model**: Configuration utilities and base classes for models
- **utils**: Helper functions used across packages
- **exceptions**: Custom exception types for error handling

By centralizing data structures in the core package, OpenSTEF ensures that models, transforms, and evaluation tools all work with consistent data formats.

Models Package: Forecasting and Features
-----------------------------------------

The ``openstef_models`` package implements the machine learning components. It's organized into three main modules:

**transforms** contains feature engineering pipelines. These are organized by domain:

- ``time_domain``: Temporal features like hour of day, day of week, holidays
- ``weather_domain``: Weather-related transformations and aggregations
- ``energy_domain``: Energy-specific features like load patterns
- ``validation``: Data validation transforms
- ``general``: General-purpose transformations

Transforms are composable through the ``TransformPipeline`` class:

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_models.transforms.time_domain import AddTemporalFeatures
   from openstef_models.transforms.weather_domain import AddWeatherFeatures
   
   # Build a feature engineering pipeline
   pipeline = TransformPipeline()
   pipeline.add_transform(AddTemporalFeatures())
   pipeline.add_transform(AddWeatherFeatures())
   
   # Apply to data
   transformed = pipeline.fit_transform(data=training_data)

**models** contains forecasting model implementations. Each model follows a consistent interface with ``fit()`` and ``predict()`` methods. Models can be simple (like XGBoost regressors) or complex (like component splitting models that decompose energy into sources).

**explainability** provides tools for understanding model predictions, including feature importance calculation and SHAP value analysis.

The models package is designed for composition. Complex models like ``ComponentSplittingModel`` combine preprocessing pipelines, core splitting logic, and postprocessing:

.. code-block:: python

   from openstef_models.models.component_splitting import ComponentSplittingModel
   from openstef_core.mixins import TransformPipeline
   
   model = ComponentSplittingModel(
       preprocessing=preprocessing_pipeline,
       component_splitter=splitter,
       postprocessing=postprocessing_pipeline,
       source_column='total_load'
   )
   
   model.fit(training_data)
   components = model.predict(new_data)

This compositional design lets you build sophisticated forecasting systems from reusable parts.

BEAM Package: Evaluation Workflows
-----------------------------------

The ``openstef_beam`` package orchestrates model evaluation. It's organized around the evaluation workflow:

**backtesting** simulates how models would have performed historically. It replays past data through models to generate realistic performance estimates.

**metrics** computes forecasting performance measures like MAE, RMSE, and quantile losses. These metrics are tailored for energy forecasting.

**evaluation** structures forecasting results into performance reports. It aggregates metrics across time periods, quantiles, and forecast horizons.

**analysis** generates visualizations from evaluation reports. It creates plots for understanding model behavior and comparing alternatives.

**benchmarking** runs complete model comparison studies. The ``BenchmarkPipeline`` coordinates backtesting, evaluation, and analysis across multiple models and targets:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline, BenchmarkConfig
   
   config = BenchmarkConfig(
       models=['xgboost', 'linear'],
       targets=['substation_1', 'substation_2'],
       metrics=['mae', 'rmse'],
       output_dir='benchmark_results'
   )
   
   pipeline = BenchmarkPipeline(config)
   results = pipeline.run()

The BEAM package depends on both core and models packages. It uses core data structures and instantiates models, but adds the evaluation layer on top.

.. note:: [DIAGRAM: BEAM workflow showing data flowing through backtesting → metrics → evaluation → analysis, with feedback loops]

Design Principles
-----------------

Several principles guide OpenSTEF's architecture:

**Separation of concerns**: Each package has a clear responsibility. Core handles data, models handle forecasting, BEAM handles evaluation. This makes the codebase easier to understand and maintain.

**Dependency management**: Dependencies flow in one direction. Core has minimal dependencies, models depends on core, BEAM depends on both. You can use lower layers without pulling in higher layers.

**Composability**: Components are designed to work together. Transforms compose into pipelines, models accept pipelines, evaluation tools work with any model. This flexibility supports experimentation.

**Type safety**: The library uses type hints extensively and validates data at boundaries. This catches errors early and makes the API self-documenting.

**Production-ready**: The architecture supports production deployment. You can package just core and models for serving predictions, leaving evaluation tools in development environments.

Integration Points
------------------

The packages integrate through well-defined interfaces:

**Data flow**: ``TimeSeriesDataset`` objects flow from core through models to evaluation. This consistent format means components can interoperate without translation layers.

**Model interface**: All models implement ``fit()`` and ``predict()`` methods. This uniform interface lets BEAM evaluate any model without model-specific code.

**Pipeline abstraction**: ``TransformPipeline`` provides a common way to compose transformations. Models use pipelines for preprocessing, BEAM uses them for data preparation.

**Configuration**: Models and pipelines use Pydantic-based configuration objects. This provides validation, serialization, and clear documentation of options.

These integration points create a cohesive system from independent packages.

Using the Architecture
----------------------

The modular design supports different use cases:

**Model development**: Use all three packages. Develop models with ``openstef_models``, evaluate them with ``openstef_beam``, and iterate based on results.

**Production forecasting**: Deploy just ``openstef_core`` and ``openstef_models``. Load trained models, apply them to incoming data, and generate predictions.

**Custom pipelines**: Build on the core abstractions. Create custom transforms, implement new models, or add evaluation metrics while leveraging existing infrastructure.

**Research**: Extend the models package with experimental algorithms. The consistent interfaces mean new models automatically work with existing evaluation tools.

The architecture provides structure without constraining how you use the library.

Related Topics
--------------

- :doc:`feature_engineering` - Details on the transforms module and feature engineering patterns
- :doc:`model_selection` - Guide to choosing and configuring models from the models package
- :doc:`reliability_and_fallback` - Production deployment patterns using the core and models packages