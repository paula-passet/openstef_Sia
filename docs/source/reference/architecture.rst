Architecture Overview
=====================

OpenSTEF is organized as a modular library with three core packages that work together to provide a complete energy forecasting solution. This page explains the architectural design, how components interact, and the reasoning behind the structure.

The Three-Package Architecture
-------------------------------

OpenSTEF is split into three independently installable packages, each with a distinct responsibility:

**openstef_core**: Foundation layer providing data structures, datasets, and utilities that other packages depend on. This includes the ``TimeSeriesDataset`` class, versioned data access, configuration utilities, and custom exceptions.

**openstef_models**: Machine learning layer containing model implementations, feature engineering transforms, and explainability tools. This package depends on ``openstef_core`` for data structures but can be used independently for model training and prediction.

**openstef_beam**: Evaluation layer providing backtesting, metrics, analysis, and benchmarking capabilities. This package depends on both ``openstef_core`` and ``openstef_models`` to evaluate forecasting performance.

This separation allows users to install only what they need. For example, a production system might only need ``openstef_core`` and ``openstef_models``, while a research environment would install all three packages for comprehensive evaluation.

.. note::
   [DIAGRAM: Three-layer architecture showing openstef_core at the base, openstef_models in the middle, and openstef_beam at the top, with dependency arrows pointing upward]

Core Package Structure
----------------------

The ``openstef_core`` package provides the foundational abstractions that make OpenSTEF extensible:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_core.base_model import BaseModel
   from openstef_core.exceptions import InputDataError
   
   # Core data structure for time series
   dataset = TimeSeriesDataset(
       data=df,
       metadata={"location": "Amsterdam"}
   )
   
   # Versioned datasets track data lineage
   versioned = VersionedTimeSeriesDataset(
       data=df,
       version="2024-01-15",
       metadata={"source": "SCADA"}
   )

The ``datasets`` module defines the standard data containers used throughout OpenSTEF. All models and transforms operate on these structures, ensuring consistency across the library.

The ``base_model`` module provides abstract base classes that define the interface for models and transforms. This enables users to implement custom models that integrate seamlessly with OpenSTEF pipelines.

Models Package Structure
------------------------

The ``openstef_models`` package is organized around the forecasting workflow:

**transforms**: Feature engineering organized by domain (time_domain, weather_domain, energy_domain, general, validation). Each subpackage contains transforms that can be composed into pipelines.

**models**: Model implementations including forecasters, component splitters, and quantile models. All models implement a common interface defined in ``openstef_core``.

**explainability**: Tools for interpreting model predictions and understanding feature importance.

.. code-block:: python

   from openstef_models.transforms.time_domain import AddLagFeatures
   from openstef_models.transforms.weather_domain import AddWeatherFeatures
   from openstef_models.models.forecasting import ForecastingModel
   from openstef_core.mixins import TransformPipeline
   
   # Build a feature engineering pipeline
   preprocessing = TransformPipeline()
   preprocessing.add(AddLagFeatures(lags=[1, 24, 168]))
   preprocessing.add(AddWeatherFeatures())
   
   # Wrap a forecaster with preprocessing
   model = ForecastingModel(
       forecaster=my_forecaster,
       preprocessing=preprocessing
   )

This modular design allows you to mix and match transforms, swap out forecasting algorithms, and customize the pipeline for your specific use case.

.. note::
   [DIAGRAM: Flow diagram showing data flowing through preprocessing pipeline → forecaster → postprocessing pipeline, with TransformPipeline boxes containing individual transforms]

BEAM Package Structure
----------------------

The ``openstef_beam`` package implements the evaluation workflow:

**metrics**: Performance metrics specific to energy forecasting (MAE, RMSE, skill scores, etc.)

**backtesting**: Simulates operational forecasting by training models on historical data and evaluating predictions on held-out periods.

**evaluation**: Organizes backtesting results into structured performance reports.

**analysis**: Generates visualizations and statistical summaries from evaluation results.

**benchmarking**: Orchestrates complete model comparison studies across multiple forecasting targets.

.. code-block:: python

   from openstef_beam.backtesting import backtest_model
   from openstef_beam.metrics import calculate_metrics
   from openstef_beam.analysis import generate_performance_report
   
   # Backtest a model on historical data
   results = backtest_model(
       model=trained_model,
       data=historical_data,
       train_window="365D",
       test_window="7D"
   )
   
   # Calculate performance metrics
   metrics = calculate_metrics(
       predictions=results.predictions,
       actuals=results.actuals
   )
   
   # Generate analysis report
   report = generate_performance_report(metrics)

The BEAM package is designed for offline analysis and model development. It's not typically used in production forecasting systems, which focus on real-time prediction.

Pipeline Composition Pattern
----------------------------

OpenSTEF uses a consistent pipeline pattern throughout the library. The ``TransformPipeline`` class from ``openstef_core.mixins`` provides a composable interface for chaining operations:

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_models.transforms.validation import ValidateColumns
   from openstef_models.transforms.time_domain import AddTimeFeatures
   from openstef_models.transforms.general import RemoveMissingValues
   
   # Build preprocessing pipeline
   preprocessing = TransformPipeline()
   preprocessing.add(ValidateColumns(required=["load", "temperature"]))
   preprocessing.add(RemoveMissingValues())
   preprocessing.add(AddTimeFeatures(features=["hour", "dayofweek"]))
   
   # Fit and transform in one step
   transformed_data = preprocessing.fit_transform(data=training_data)
   
   # Transform new data using fitted pipeline
   new_transformed = preprocessing.transform(data=new_data)

This pattern appears at multiple levels:

- **Feature engineering**: Chains of transforms that prepare data for modeling
- **Model composition**: Models wrapped with preprocessing and postprocessing pipelines
- **Component splitting**: Preprocessing → splitter → postprocessing

The pipeline pattern ensures that all transformations are applied consistently during training and prediction, preventing common bugs like data leakage or inconsistent feature engineering.

.. note::
   [DIAGRAM: Nested pipeline diagram showing ForecastingModel containing preprocessing TransformPipeline (with 3 transforms) → forecaster → postprocessing TransformPipeline (with 2 transforms)]

Design Principles
-----------------

Several key principles guide OpenSTEF's architecture:

**Separation of concerns**: Each package has a clear responsibility. Core provides data structures, models provides algorithms, BEAM provides evaluation. This makes the codebase easier to understand and maintain.

**Dependency inversion**: Models depend on abstract interfaces (``BaseModel``) rather than concrete implementations. This allows users to implement custom models without modifying OpenSTEF code.

**Composition over inheritance**: Functionality is built by composing small, focused components (transforms, models, pipelines) rather than creating deep inheritance hierarchies.

**Explicit over implicit**: Configuration is explicit and visible. Pipelines are constructed programmatically, making the data flow clear and debuggable.

**Type safety**: OpenSTEF uses type hints throughout and validates data at runtime. The ``TimeSeriesDataset`` class ensures that data has the expected structure before it reaches models.

These principles make OpenSTEF flexible enough for research while remaining reliable for production use.

Extending the Architecture
--------------------------

OpenSTEF is designed to be extended at multiple levels:

**Custom transforms**: Implement the transform interface to add domain-specific feature engineering:

.. code-block:: python

   from openstef_core.base_model import BaseTransform
   from openstef_core.datasets import TimeSeriesDataset
   
   class MyCustomTransform(BaseTransform):
       def fit(self, data: TimeSeriesDataset) -> None:
           # Learn parameters from training data
           self.mean = data.data["load"].mean()
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Apply transformation
           transformed_df = data.data.copy()
           transformed_df["normalized_load"] = transformed_df["load"] / self.mean
           return TimeSeriesDataset(data=transformed_df, metadata=data.metadata)

**Custom models**: Implement the forecaster interface to integrate new algorithms:

.. code-block:: python

   from openstef_core.base_model import BaseForecaster
   
   class MyCustomForecaster(BaseForecaster):
       def fit(self, X, y):
           # Train your model
           pass
       
       def predict(self, X):
           # Generate predictions
           pass

**Custom metrics**: Add domain-specific evaluation metrics to the BEAM package.

The modular architecture ensures that custom components integrate seamlessly with existing OpenSTEF functionality.

Component Interaction Example
------------------------------

Here's how the packages work together in a typical forecasting workflow:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.mixins import TransformPipeline
   from openstef_models.transforms.time_domain import AddLagFeatures
   from openstef_models.models.forecasting import ForecastingModel
   from openstef_models.models.forecasting.constant_median import ConstantMedianForecaster
   from openstef_beam.backtesting import backtest_model
   
   # Core: Load and version data
   dataset = VersionedTimeSeriesDataset(
       data=raw_df,
       version="2024-01-15",
       metadata={"location": "Amsterdam"}
   )
   
   # Models: Build forecasting pipeline
   preprocessing = TransformPipeline()
   preprocessing.add(AddLagFeatures(lags=[1, 24, 168]))
   
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(),
       preprocessing=preprocessing
   )
   
   # Models: Train model
   model.fit(data=dataset)
   
   # Models: Generate predictions
   predictions = model.predict(data=test_dataset)
   
   # BEAM: Evaluate performance
   results = backtest_model(
       model=model,
       data=historical_dataset,
       train_window="365D",
       test_window="7D"
   )

This example shows data flowing from ``openstef_core`` through ``openstef_models`` for training and prediction, then into ``openstef_beam`` for evaluation. Each package plays its role without tight coupling to the others.

.. note::
   [DIAGRAM: Sequence diagram showing workflow: User → openstef_core (create dataset) → openstef_models (build pipeline, train, predict) → openstef_beam (evaluate) → User (results)]