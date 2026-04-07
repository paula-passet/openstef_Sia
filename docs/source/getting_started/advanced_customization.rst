Advanced Customization
======================

OpenSTEF is designed for extensibility. While the library provides sensible defaults for most forecasting tasks, you can customize nearly every aspect of the pipeline to match your specific requirements. This guide shows you how to extend the library with custom data preparation, feature engineering, and pipeline workflows.

This page assumes you've already completed :doc:`first_forecast` and understand the basic forecasting workflow.

Understanding Extension Points
------------------------------

OpenSTEF provides three main extension points for customization:

1. **Custom transforms** - Modify data preprocessing and feature engineering
2. **Custom pipelines** - Compose transforms into reusable workflows  
3. **Custom data preparation** - Control how raw data becomes model-ready features

All customization follows the scikit-learn pattern of ``fit()`` and ``transform()`` methods, making it familiar if you've worked with scikit-learn pipelines.

Creating Custom Transforms
---------------------------

Transforms are the building blocks of data processing in OpenSTEF. A transform takes a dataset as input, applies some operation, and returns a modified dataset.

Basic Transform Structure
^^^^^^^^^^^^^^^^^^^^^^^^^^

To create a custom transform, inherit from ``TimeSeriesTransform`` and implement three key methods:

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd

   class TemperatureSmoothingTransform(TimeSeriesTransform):
       """Smooth temperature readings using a rolling average."""
       
       def __init__(self, window_hours: int = 3):
           self.window_hours = window_hours
           self.temperature_columns = None
       
       @property
       def is_fitted(self) -> bool:
           """Check if the transform has been fitted."""
           return self.temperature_columns is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn which columns contain temperature data."""
           # Identify temperature columns during fit
           self.temperature_columns = [
               col for col in data.data.columns 
               if 'temp' in col.lower()
           ]
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply smoothing to temperature columns."""
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           # Create a copy to avoid modifying the original
           smoothed_data = data.data.copy()
           
           # Apply rolling average to temperature columns
           for col in self.temperature_columns:
               if col in smoothed_data.columns:
                   smoothed_data[col] = smoothed_data[col].rolling(
                       window=self.window_hours, 
                       min_periods=1
                   ).mean()
           
           return TimeSeriesDataset(smoothed_data, data.sample_interval)
       
       def features_added(self) -> list[str]:
           """This transform modifies existing features, doesn't add new ones."""
           return []

The ``is_fitted`` property tracks whether ``fit()`` has been called. The ``fit()`` method learns parameters from training data (like which columns exist), and ``transform()`` applies the operation using those learned parameters.

Adding New Features
^^^^^^^^^^^^^^^^^^^

Transforms can also create entirely new features. Here's an example that adds domain-specific features:

.. code-block:: python

   class WorkdayFeatureTransform(TimeSeriesTransform):
       """Add features indicating workday patterns."""
       
       def __init__(self):
           self._fitted = False
       
       @property
       def is_fitted(self) -> bool:
           return self._fitted
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """No parameters to learn, but mark as fitted."""
           self._fitted = True
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add workday-related features."""
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           df = data.data.copy()
           
           # Add is_workday feature (Monday-Friday)
           df['is_workday'] = df.index.dayofweek < 5
           
           # Add workday_hour (hour of day on workdays, -1 otherwise)
           df['workday_hour'] = df.index.hour.where(df['is_workday'], -1)
           
           # Add business_hours flag (9 AM - 5 PM on workdays)
           df['business_hours'] = (
               df['is_workday'] & 
               (df.index.hour >= 9) & 
               (df.index.hour < 17)
           )
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           """List the new features this transform creates."""
           return ['is_workday', 'workday_hour', 'business_hours']

Stateful Transforms
^^^^^^^^^^^^^^^^^^^

Some transforms need to learn parameters from training data and apply them consistently to new data. Here's a normalization transform that remembers training statistics:

.. code-block:: python

   class FeatureNormalizer(TimeSeriesTransform):
       """Normalize features using training data statistics."""
       
       def __init__(self, columns: list[str]):
           self.columns = columns
           self.means = None
           self.stds = None
       
       @property
       def is_fitted(self) -> bool:
           return self.means is not None and self.stds is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn mean and standard deviation from training data."""
           self.means = data.data[self.columns].mean()
           self.stds = data.data[self.columns].std()
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Normalize using training statistics."""
           if not self.is_fitted:
               raise ValueError("Must fit before transform")
           
           df = data.data.copy()
           
           # Apply normalization using training statistics
           for col in self.columns:
               if col in df.columns:
                   df[col] = (df[col] - self.means[col]) / self.stds[col]
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return []

Building Custom Pipelines
--------------------------

Individual transforms are powerful, but the real flexibility comes from composing them into pipelines. OpenSTEF provides ``TransformPipeline`` to chain transforms together.

Creating a Pipeline
^^^^^^^^^^^^^^^^^^^

A pipeline applies transforms sequentially, where each transform receives the output of the previous one:

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_core.datasets import TimeSeriesDataset

   # Create individual transforms
   smoother = TemperatureSmoothingTransform(window_hours=3)
   workday_features = WorkdayFeatureTransform()
   normalizer = FeatureNormalizer(columns=['temp', 'humidity'])

   # Compose into a pipeline
   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[smoother, workday_features, normalizer]
   )

   # Fit the entire pipeline on training data
   preprocessing.fit(training_data)

   # Transform new data through the entire pipeline
   processed_data = preprocessing.transform(new_data)

The pipeline automatically handles the fit/transform flow: during ``fit()``, each transform is fitted on the output of the previous transform. During ``transform()``, data flows through each transform in sequence.

Using Pipelines in Models
^^^^^^^^^^^^^^^^^^^^^^^^^^

Forecasting models in OpenSTEF accept a ``preprocessing`` parameter where you can inject your custom pipeline:

.. code-block:: python

   from openstef_models.models.forecaster import Forecaster, ForecasterConfig
   from openstef_models.models.forecaster.xgb import XGBForecasterConfig

   # Create your custom preprocessing pipeline
   custom_preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           TemperatureSmoothingTransform(window_hours=3),
           WorkdayFeatureTransform(),
       ]
   )

   # Create a forecaster with custom preprocessing
   forecaster = Forecaster(
       forecaster=XGBForecasterConfig(name="my_xgb_model"),
       preprocessing=custom_preprocessing,
       target_column="load"
   )

   # Train the model - preprocessing is applied automatically
   forecaster.fit(training_data)

   # Make predictions - preprocessing is applied to new data
   forecast = forecaster.predict(forecast_input_data)

Model-Specific Preprocessing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When working with ensemble models, you may want different preprocessing for different base models. OpenSTEF supports this through model-specific preprocessing:

.. code-block:: python

   from openstef_models.models.forecaster.ensemble import (
       EnsembleForecaster, 
       EnsembleForecasterConfig
   )

   # Common preprocessing applied to all models
   common_preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[TemperatureSmoothingTransform(window_hours=3)]
   )

   # Model-specific preprocessing for individual forecasters
   model_specific = {
       "xgb_model": TransformPipeline[TimeSeriesDataset](
           transforms=[WorkdayFeatureTransform()]
       ),
       "lgb_model": TransformPipeline[TimeSeriesDataset](
           transforms=[FeatureNormalizer(columns=['temp', 'humidity'])]
       ),
   }

   # Create ensemble with both common and model-specific preprocessing
   ensemble = EnsembleForecaster(
       forecasters={
           "xgb_model": XGBForecasterConfig(name="xgb"),
           "lgb_model": LGBForecasterConfig(name="lgb"),
       },
       preprocessing=common_preprocessing,
       model_specific_preprocessing=model_specific,
       target_column="load"
   )

The common preprocessing runs first, then each model receives its own model-specific preprocessing on top of that.

Advanced Data Preparation Patterns
-----------------------------------

Beyond transforms and pipelines, you can customize how data flows through the entire forecasting process.

Conditional Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes you want different features depending on the data characteristics. Here's a pattern for conditional feature engineering:

.. code-block:: python

   class AdaptiveFeatureTransform(TimeSeriesTransform):
       """Add features based on data characteristics."""
       
       def __init__(self):
           self.has_temperature = False
           self.has_solar = False
       
       @property
       def is_fitted(self) -> bool:
           return True  # Always fitted after checking columns
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Detect available features."""
           self.has_temperature = any('temp' in col.lower() 
                                     for col in data.data.columns)
           self.has_solar = 'solar_radiation' in data.data.columns
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add features based on what's available."""
           df = data.data.copy()
           
           # Only add temperature-based features if temperature exists
           if self.has_temperature:
               temp_cols = [col for col in df.columns if 'temp' in col.lower()]
               if temp_cols:
                   df['temp_range'] = df[temp_cols].max(axis=1) - df[temp_cols].min(axis=1)
           
           # Only add solar features if solar data exists
           if self.has_solar:
               df['is_daylight'] = df['solar_radiation'] > 0
               df['solar_intensity'] = df['solar_radiation'].clip(lower=0)
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           """Return features that might be added."""
           features = []
           if self.has_temperature:
               features.append('temp_range')
           if self.has_solar:
               features.extend(['is_daylight', 'solar_intensity'])
           return features

Custom Validation and Cleaning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can create transforms that validate and clean data before it reaches the model:

.. code-block:: python

   class DataQualityTransform(TimeSeriesTransform):
       """Validate and clean input data."""
       
       def __init__(self, required_columns: list[str], max_missing_pct: float = 0.1):
           self.required_columns = required_columns
           self.max_missing_pct = max_missing_pct
           self._fitted = False
       
       @property
       def is_fitted(self) -> bool:
           return self._fitted
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Validate training data quality."""
           missing = data.data[self.required_columns].isnull().sum()
           missing_pct = missing / len(data.data)
           
           if (missing_pct > self.max_missing_pct).any():
               bad_cols = missing_pct[missing_pct > self.max_missing_pct]
               raise ValueError(
                   f"Columns have too much missing data: {bad_cols.to_dict()}"
               )
           
           self._fitted = True
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Clean data by forward-filling small gaps."""
           if not self.is_fitted:
               raise ValueError("Must fit before transform")
           
           df = data.data.copy()
           
           # Forward fill small gaps (up to 3 periods)
           df[self.required_columns] = df[self.required_columns].fillna(
               method='ffill', 
               limit=3
           )
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return []

Practical Tips
--------------

**Start Simple**: Begin with one custom transform and verify it works before building complex pipelines.

**Test Transforms Independently**: Test your transforms on sample data before integrating them into a full forecasting workflow.

**Preserve Immutability**: Always copy dataframes before modifying them (``df.copy()``) to avoid side effects.

**Document Feature Names**: Use descriptive names in ``features_added()`` to help with debugging and model interpretation.

**Handle Missing Data**: Consider how your transform behaves when expected columns are missing or contain NaN values.

**Version Your Transforms**: When you change a transform's behavior, consider versioning it to maintain reproducibility of past experiments.

Next Steps
----------

Now that you understand customization, you might want to:

- Learn about :doc:`backtesting` to evaluate your custom features
- Explore the API reference for built-in transforms
- See the examples directory for more complex customization patterns

For questions about specific use cases, consult the OpenSTEF community or review the source code of existing transforms in the library.