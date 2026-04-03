Advanced Customization
======================

OpenSTEF is designed for extensibility. While the library provides sensible defaults for most forecasting tasks, you can customize nearly every aspect of the pipeline: from feature engineering to data preprocessing to model behavior. This guide shows you the main extension points and patterns for power users who need to adapt OpenSTEF to specialized requirements.

If you're new to OpenSTEF, start with the :doc:`quickstart` or :doc:`first_forecast` tutorials before diving into customization.

Custom Feature Engineering
---------------------------

OpenSTEF's feature engineering system is built around the ``Transform`` interface. All transforms follow a consistent ``fit()`` / ``transform()`` pattern and can be chained together in a ``TransformPipeline``.

Creating a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To create a custom feature transform, implement the ``Transform`` interface with your feature logic:

.. code-block:: python

   from openstef_core.mixins import Transform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig
   from pydantic import Field
   import pandas as pd

   class TemperatureInteractionAdder(BaseConfig, Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Add temperature interaction features for energy forecasting."""
       
       temp_column: str = Field(default="temp", description="Temperature column name")
       hour_column: str = Field(default="hour", description="Hour column name")
       
       @property
       def is_fitted(self) -> bool:
           """This transform doesn't require fitting."""
           return True
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """No fitting required for this transform."""
           pass
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add temperature-hour interaction features."""
           df = data.data.copy()
           
           # Create interaction features
           if self.temp_column in df.columns and self.hour_column in df.columns:
               df['temp_x_hour'] = df[self.temp_column] * df[self.hour_column]
               df['temp_squared'] = df[self.temp_column] ** 2
               df['temp_cooling'] = df[self.temp_column].clip(lower=18) - 18
               df['temp_heating'] = 18 - df[self.temp_column].clip(upper=18)
           
           return data.copy_with(df)
       
       def features_added(self) -> list[str]:
           """Return list of features added by this transform."""
           return ['temp_x_hour', 'temp_squared', 'temp_cooling', 'temp_heating']

Key points:

- Inherit from both ``BaseConfig`` (for Pydantic validation) and ``Transform``
- Implement ``is_fitted``, ``fit()``, and ``transform()``
- Always return a new ``TimeSeriesDataset`` instance using ``copy_with()``
- Add a ``features_added()`` method to document what features you create

Using Custom Transforms in Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you've created a custom transform, add it to a ``TransformPipeline``:

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder
   from openstef_models.transforms.general import Clipper

   # Build a pipeline with built-in and custom transforms
   pipeline = TransformPipeline[TimeSeriesDataset](
       transforms=[
           DatetimeFeaturesAdder(),  # Built-in: adds hour, day, month, etc.
           TemperatureInteractionAdder(temp_column="temperature"),  # Your custom transform
           Clipper(features_to_clip=["temperature", "temp_x_hour"]),  # Built-in: clip outliers
       ]
   )

   # Fit and transform your data
   pipeline.fit(training_data)
   transformed_data = pipeline.transform(training_data)

The pipeline applies transforms sequentially, with each transform receiving the output of the previous one. All transforms are fitted on the intermediate outputs during ``fit()``.

Stateful Transforms
^^^^^^^^^^^^^^^^^^^

Some transforms need to learn parameters from training data. For example, a normalization transform needs to remember mean and standard deviation:

.. code-block:: python

   class FeatureNormalizer(BaseConfig, Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Normalize specified features to zero mean and unit variance."""
       
       features: list[str] = Field(description="Features to normalize")
       _means: dict[str, float] = {}
       _stds: dict[str, float] = {}
       _fitted: bool = False
       
       @property
       def is_fitted(self) -> bool:
           return self._fitted
       
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn normalization parameters from training data."""
           df = data.data
           for feature in self.features:
               if feature in df.columns:
                   self._means[feature] = df[feature].mean()
                   self._stds[feature] = df[feature].std()
           self._fitted = True
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply learned normalization."""
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           df = data.data.copy()
           for feature in self.features:
               if feature in df.columns:
                   df[feature] = (df[feature] - self._means[feature]) / self._stds[feature]
           
           return data.copy_with(df)

Store learned parameters as private attributes (prefixed with ``_``) and set ``_fitted`` to track state.

Custom Data Preparation
------------------------

Beyond feature engineering, you may need to customize how data flows through the forecasting pipeline. OpenSTEF models use a ``preprocessing`` pipeline that you can fully control.

Customizing Model Preprocessing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every forecasting model has a ``preprocessing`` attribute that defines its data preparation pipeline:

.. code-block:: python

   from openstef_models.models.xgb import XGBForecastingModel, XGBForecastingModelConfig
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder,
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.weather_domain import DaylightFeatureAdder
   from openstef_core.types import CountryAlpha2

   # Create a custom preprocessing pipeline
   custom_preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           DatetimeFeaturesAdder(),
           CyclicFeaturesAdder(),
           HolidayFeatureAdder(country=CountryAlpha2.NL),
           DaylightFeatureAdder(latitude=52.37, longitude=4.89),
           TemperatureInteractionAdder(),  # Your custom transform
       ]
   )

   # Create model with custom preprocessing
   model = XGBForecastingModel(
       XGBForecastingModelConfig(
           target_column="load",
           cutoff_history=pd.Timedelta(days=14),
       ),
       preprocessing=custom_preprocessing,
   )

   # Train model - preprocessing is fitted automatically
   model.fit(training_data)
   
   # Make predictions - preprocessing is applied automatically
   forecast = model.predict(new_data)

The model handles fitting and applying the preprocessing pipeline automatically during ``fit()`` and ``predict()``.

.. note::

   The ``cutoff_history`` parameter is crucial when using lag-based features. If your pipeline includes transforms that create lagged features (e.g., 14-day lags), set ``cutoff_history=pd.Timedelta(days=14)`` to exclude rows with NaN values from training.

Custom Pipeline Workflows
--------------------------

For advanced use cases, you may want to bypass the standard model interface and build custom workflows.

Manual Pipeline Control
^^^^^^^^^^^^^^^^^^^^^^^^

You can manually control the preprocessing pipeline for maximum flexibility:

.. code-block:: python

   from openstef_models.models.xgb import XGBForecastingModel, XGBForecastingModelConfig
   
   # Create model with preprocessing
   model = XGBForecastingModel(
       XGBForecastingModelConfig(target_column="load"),
       preprocessing=custom_preprocessing,
   )
   
   # Manually fit preprocessing on training data
   model.preprocessing.fit(training_data)
   
   # Transform training data
   processed_training = model.preprocessing.transform(training_data)
   
   # Fit the underlying model on processed data
   # (Note: this bypasses the model's built-in prepare_input logic)
   model.fit(processed_training)
   
   # Transform and predict on new data
   processed_new = model.preprocessing.transform(new_data)
   forecast = model.predict(processed_new)

This pattern is useful when you need to inspect intermediate outputs or apply custom logic between preprocessing and prediction.

Combining Multiple Data Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For complex scenarios involving multiple data sources, you can create custom workflows that merge data before forecasting:

.. code-block:: python

   def forecast_with_external_features(
       model: XGBForecastingModel,
       base_data: TimeSeriesDataset,
       external_features: pd.DataFrame,
   ) -> ForecastDataset:
       """Custom workflow that merges external features before forecasting."""
       
       # Merge external features into base data
       merged_df = base_data.data.join(external_features, how='left')
       merged_data = base_data.copy_with(merged_df)
       
       # Apply preprocessing
       processed = model.preprocessing.transform(merged_data)
       
       # Generate forecast
       return model.predict(processed)

This approach gives you complete control over data flow while still leveraging OpenSTEF's preprocessing and modeling capabilities.

Built-in Transform Library
---------------------------

OpenSTEF includes a comprehensive library of transforms you can use as building blocks:

**Time domain transforms** (``openstef_models.transforms.time_domain``):

- ``DatetimeFeaturesAdder``: Extracts hour, day, month, weekday features
- ``CyclicFeaturesAdder``: Creates cyclic encodings (sin/cos) for periodic features
- ``HolidayFeatureAdder``: Adds holiday indicators for specific countries
- ``RollingAggregatesAdder``: Computes rolling statistics (mean, std, min, max)

**Weather domain transforms** (``openstef_models.transforms.weather_domain``):

- ``DaylightFeatureAdder``: Adds sunrise, sunset, and daylight duration
- ``RadiationDerivedFeaturesAdder``: Computes radiation-based features

**Energy domain transforms** (``openstef_models.transforms.energy_domain``):

- ``WindPowerFeatureAdder``: Converts wind speed to wind power estimates

**General transforms** (``openstef_models.transforms.general``):

- ``Clipper``: Clips feature values to observed ranges

See the :doc:`/api/index` for complete documentation of all available transforms.

Next Steps
----------

- Explore the :doc:`backtesting` tutorial to evaluate your custom pipelines
- Review the :doc:`/api/index` for detailed transform documentation
- Check the :doc:`/examples/index` for real-world customization patterns