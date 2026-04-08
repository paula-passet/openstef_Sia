Advanced Customization
======================

OpenSTEF is designed for extensibility. This guide shows you how to customize the library's behavior by creating custom transforms, modifying preprocessing pipelines, and building specialized workflows for your forecasting needs.

This page assumes you're comfortable with the basics covered in :doc:`first_forecast` and want to adapt OpenSTEF to specific requirements.

Understanding Extension Points
------------------------------

OpenSTEF provides three main extension points:

- **Custom transforms**: Add domain-specific feature engineering or data preprocessing
- **Pipeline customization**: Modify the preprocessing and postprocessing pipelines that wrap models
- **Workflow customization**: Build specialized orchestration for complex forecasting scenarios

All customization follows the same pattern: OpenSTEF components are composable building blocks that you can mix, match, and extend.

Creating Custom Transforms
---------------------------

Custom transforms let you inject domain-specific logic into OpenSTEF's preprocessing pipelines. All transforms inherit from ``TimeSeriesTransform`` and implement two key methods: ``fit()`` and ``transform()``.

Basic Transform Structure
^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a simple custom transform that adds a rolling average feature:

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   
   class RollingAverageAdder(TimeSeriesTransform):
       """Add rolling average features to time series data."""
       
       def __init__(self, window_hours: int = 24, target_column: str = "load"):
           self.window_hours = window_hours
           self.target_column = target_column
       
       @property
       def is_fitted(self) -> bool:
           # Stateless transforms are always "fitted"
           return True
       
       def fit(self, data: TimeSeriesDataset) -> None:
           # No parameters to learn from training data
           pass
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add rolling average feature."""
           df = data.data.copy()
           
           # Calculate rolling average
           feature_name = f"{self.target_column}_rolling_{self.window_hours}h"
           df[feature_name] = df[self.target_column].rolling(
               window=self.window_hours, 
               min_periods=1
           ).mean()
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           """Report which features this transform adds."""
           return [f"{self.target_column}_rolling_{self.window_hours}h"]

The ``features_added()`` method helps OpenSTEF track which columns come from which transforms, useful for debugging and feature importance analysis.

Stateful Transforms
^^^^^^^^^^^^^^^^^^^

Some transforms need to learn parameters during training. Here's a custom normalizer that learns scaling factors:

.. code-block:: python

   class CustomNormalizer(TimeSeriesTransform):
       """Normalize features using training data statistics."""
       
       def __init__(self, columns: list[str]):
           self.columns = columns
           self.means_ = None
           self.stds_ = None
       
       @property
       def is_fitted(self) -> bool:
           return self.means_ is not None and self.stds_ is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn mean and std from training data."""
           df = data.data[self.columns]
           self.means_ = df.mean()
           self.stds_ = df.std()
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply learned normalization."""
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           df = data.data.copy()
           df[self.columns] = (df[self.columns] - self.means_) / self.stds_
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           # This transform modifies existing features, doesn't add new ones
           return []

Stateful transforms store learned parameters (like ``means_`` and ``stds_``) as instance attributes. The ``is_fitted`` property tracks whether the transform is ready to use.

Customizing Preprocessing Pipelines
------------------------------------

Models in OpenSTEF have ``preprocessing`` and ``postprocessing`` pipelines that you can customize. These are ``TransformPipeline`` objects containing ordered sequences of transforms.

Modifying an Existing Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can add your custom transforms to a model's pipeline:

.. code-block:: python

   from openstef_models.models import XGBQuantileForecaster
   from openstef_models.transforms.general import Selector
   from openstef_models.transforms.feature_adders import DatetimeFeaturesAdder
   from openstef_core.transforms import TransformPipeline
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create a forecaster
   model = XGBQuantileForecaster()
   
   # Build a custom preprocessing pipeline
   model.preprocessing = TransformPipeline(
       transforms=[
           RollingAverageAdder(window_hours=24, target_column="load"),
           DatetimeFeaturesAdder(onehot_encode=False),
           CustomNormalizer(columns=["load", "load_rolling_24h"]),
           Selector(selection=Include("load", "load_rolling_24h", "hour", "dayofweek")),
       ]
   )
   
   # Use the model with custom preprocessing
   model.fit(train_data)
   forecast = model.predict(test_data)

The pipeline executes transforms in order. Each transform receives the output of the previous one, following a functional composition pattern.

Pipeline Execution Flow
^^^^^^^^^^^^^^^^^^^^^^^

Understanding how pipelines execute helps you design effective customizations:

1. **Fit phase**: ``pipeline.fit(data)`` calls ``fit()`` on each transform in sequence, passing transformed data forward
2. **Transform phase**: ``pipeline.transform(data)`` calls ``transform()`` on each fitted transform
3. **Fit-transform phase**: ``pipeline.fit_transform(data)`` combines both for convenience

Here's what happens during training:

.. code-block:: python

   # During model.fit(train_data):
   # 1. RollingAverageAdder.fit(train_data) - no-op for stateless transform
   # 2. data = RollingAverageAdder.transform(train_data)
   # 3. DatetimeFeaturesAdder.fit(data) - no-op
   # 4. data = DatetimeFeaturesAdder.transform(data)
   # 5. CustomNormalizer.fit(data) - learns means and stds
   # 6. data = CustomNormalizer.transform(data)
   # 7. Selector.fit(data) - no-op
   # 8. data = Selector.transform(data)
   # 9. Pass final data to underlying model

During prediction, only ``transform()`` is called on each component, using parameters learned during fitting.

Building Custom Workflows
--------------------------

For complex scenarios, you can create custom workflows that orchestrate multiple models and processing steps. OpenSTEF provides ``CustomForecastingWorkflow`` as a foundation.

Workflow Structure
^^^^^^^^^^^^^^^^^^

Workflows combine:

- **Model management**: Handling model lifecycle (fit, predict, save, load)
- **Callbacks**: Hooks for monitoring, logging, and custom logic
- **Preprocessing/postprocessing**: Separate pipelines for different workflow stages

Here's a simplified custom workflow that adds validation logic:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.models import XGBQuantileForecaster
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   import logging
   
   logger = logging.getLogger(__name__)
   
   class ValidatedForecastingWorkflow(CustomForecastingWorkflow):
       """Workflow with custom validation logic."""
       
       def __init__(self, min_data_points: int = 1000, **kwargs):
           super().__init__(**kwargs)
           self.min_data_points = min_data_points
       
       def fit(
           self, 
           data: TimeSeriesDataset,
           data_val: TimeSeriesDataset | None = None,
           data_test: TimeSeriesDataset | None = None,
       ) -> None:
           """Fit with validation checks."""
           
           # Custom validation
           if len(data.data) < self.min_data_points:
               raise ValueError(
                   f"Insufficient training data: {len(data.data)} points "
                   f"(minimum: {self.min_data_points})"
               )
           
           # Check for data quality issues
           if data.data[self.model.target_column].isna().sum() > 0:
               logger.warning("Training data contains missing target values")
           
           # Proceed with standard fitting
           super().fit(data, data_val, data_test)
       
       def predict(self, data: TimeSeriesDataset) -> ForecastDataset:
           """Predict with output validation."""
           forecast = super().predict(data)
           
           # Validate predictions
           if forecast.forecast.isna().any().any():
               logger.error("Forecast contains NaN values")
           
           return forecast

This pattern lets you wrap OpenSTEF's standard workflows with domain-specific validation, logging, or error handling.

Ensemble Preprocessing Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ensemble models have more complex preprocessing with three pipeline types:

- **Common preprocessing**: Applied once to input data
- **Model-specific preprocessing**: Applied separately for each base forecaster
- **Combiner preprocessing**: Prepares data for the ensemble combiner

Here's how to customize ensemble preprocessing:

.. code-block:: python

   from openstef_models.models import EnsembleForecaster
   from openstef_models.models.regressors import XGBQuantileOpenstfRegressor
   from openstef_core.transforms import TransformPipeline
   
   # Create ensemble with custom preprocessing
   ensemble = EnsembleForecaster(
       forecasters={
           "xgb_short": XGBQuantileForecaster(),
           "xgb_long": XGBQuantileForecaster(),
       },
       combiner=XGBQuantileOpenstfRegressor(),
   )
   
   # Common preprocessing: shared by all forecasters
   ensemble.preprocessing = TransformPipeline(
       transforms=[
           RollingAverageAdder(window_hours=24),
           DatetimeFeaturesAdder(onehot_encode=False),
       ]
   )
   
   # Model-specific preprocessing: unique to each forecaster
   ensemble.model_specific_preprocessing["xgb_short"] = TransformPipeline(
       transforms=[
           Selector(selection=Include("load", "load_rolling_24h", "hour")),
       ]
   )
   
   ensemble.model_specific_preprocessing["xgb_long"] = TransformPipeline(
       transforms=[
           Selector(selection=Include("load", "dayofweek", "month")),
       ]
   )

This pattern lets you train specialized forecasters on different feature sets while sharing expensive feature engineering in the common pipeline.

Practical Customization Examples
---------------------------------

Domain-Specific Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For energy forecasting, you might need weather-dependent features:

.. code-block:: python

   class TemperatureSensitivityAdder(TimeSeriesTransform):
       """Add temperature sensitivity features for heating/cooling loads."""
       
       def __init__(
           self, 
           temp_column: str = "temperature",
           heating_threshold: float = 15.0,
           cooling_threshold: float = 22.0,
       ):
           self.temp_column = temp_column
           self.heating_threshold = heating_threshold
           self.cooling_threshold = cooling_threshold
       
       @property
       def is_fitted(self) -> bool:
           return True
       
       def fit(self, data: TimeSeriesDataset) -> None:
           pass
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           
           # Heating degree hours
           df["heating_degree_hours"] = (
               self.heating_threshold - df[self.temp_column]
           ).clip(lower=0)
           
           # Cooling degree hours
           df["cooling_degree_hours"] = (
               df[self.temp_column] - self.cooling_threshold
           ).clip(lower=0)
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return ["heating_degree_hours", "cooling_degree_hours"]

Add this to your preprocessing pipeline for temperature-sensitive load forecasting.

Data Quality Transforms
^^^^^^^^^^^^^^^^^^^^^^^

Custom transforms can also handle data quality issues:

.. code-block:: python

   class OutlierClipper(TimeSeriesTransform):
       """Clip outliers based on training data quantiles."""
       
       def __init__(self, columns: list[str], lower_q: float = 0.01, upper_q: float = 0.99):
           self.columns = columns
           self.lower_q = lower_q
           self.upper_q = upper_q
           self.lower_bounds_ = None
           self.upper_bounds_ = None
       
       @property
       def is_fitted(self) -> bool:
           return self.lower_bounds_ is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn clipping bounds from training data."""
           df = data.data[self.columns]
           self.lower_bounds_ = df.quantile(self.lower_q)
           self.upper_bounds_ = df.quantile(self.upper_q)
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           for col in self.columns:
               df[col] = df[col].clip(
                   lower=self.lower_bounds_[col],
                   upper=self.upper_bounds_[col]
               )
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return []

Best Practices
--------------

When customizing OpenSTEF, follow these guidelines:

**Transform design**:

- Keep transforms focused on a single responsibility
- Make transforms stateless when possible (simpler to reason about)
- Always implement ``features_added()`` accurately for debugging
- Validate inputs in ``transform()`` to catch pipeline configuration errors early

**Pipeline composition**:

- Order matters: put feature generation before feature selection
- Fit expensive transforms (like normalization) after cheap filtering
- Use ``Selector`` as the last transform to ensure only required features reach the model

**Testing custom components**:

- Test transforms independently before adding to pipelines
- Verify stateful transforms work correctly on unseen data
- Check that ``fit()`` and ``transform()`` produce consistent results

**Performance considerations**:

- Profile custom transforms if training is slow
- Consider vectorized pandas operations over row-by-row processing
- Cache expensive computations in stateful transforms during ``fit()``

Next Steps
----------

- See :doc:`first_forecast` for basic model usage patterns
- Check :doc:`backtesting` for evaluating custom preprocessing pipelines
- Explore the API reference for built-in transforms you can extend

Custom transforms and workflows let you adapt OpenSTEF to specialized forecasting problems while leveraging the library's robust training and prediction infrastructure.