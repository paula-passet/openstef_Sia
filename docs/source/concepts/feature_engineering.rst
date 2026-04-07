Feature Engineering
===================

Feature engineering is the process of creating predictive variables from raw data. In energy forecasting, good features capture the patterns that drive electricity demand and generation: weather conditions, time-based patterns, historical load behavior, and domain-specific factors. OpenSTEF provides a library of feature transforms that you can combine into pipelines tailored to your forecasting task.

What Makes Good Features for Energy Forecasting
------------------------------------------------

Energy systems exhibit strong patterns that translate directly into predictive features:

**Weather dependencies**: Temperature drives heating and cooling demand. Wind speed determines wind power generation. Solar radiation affects both solar generation and cooling loads. These relationships are often nonlinear—a 5°C change matters more at temperature extremes than in moderate conditions.

**Temporal patterns**: Energy use follows daily cycles (morning and evening peaks), weekly patterns (weekday vs. weekend), and seasonal variations. Holidays break normal patterns. Time-based features help models learn these recurring structures.

**Historical behavior**: Recent load values predict near-term load. A lag feature showing load from 24 hours ago captures the daily pattern. A 7-day lag captures weekly patterns. The choice of which lags to include depends on your forecast horizon and the patterns in your data.

**Domain-specific relationships**: Wind power depends on wind speed cubed (up to rated capacity). Solar generation depends on sun angle and daylight hours. These physics-based transformations often work better than letting the model learn them from raw data.

Weather Features
----------------

OpenSTEF includes transforms for common weather-based features. These transforms derive additional predictors from basic meteorological data:

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_core.datasets import VersionedTimeSeriesDataset
   import pandas as pd
   from datetime import timedelta

   # Sample weather data
   data = pd.DataFrame({
       'load': [100.0, 110.0, 120.0, 130.0],
       'temperature': [15.0, 16.0, 17.0, 18.0],
       'windspeed_100m': [5.0, 6.0, 7.0, 8.0],
       'radiation': [200.0, 300.0, 400.0, 350.0],
   }, index=pd.date_range('2025-01-01 10:00', periods=4, freq='h'))

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data, 
       timedelta(hours=1)
   )

   # Add atmosphere-derived features
   atmos_transform = AtmosphereDerivedFeaturesAdder()
   dataset = atmos_transform.transform(dataset)

   # Add daylight features (requires location)
   daylight_transform = DaylightFeatureAdder()
   dataset = daylight_transform.transform(dataset)

   # Add radiation-derived features
   radiation_transform = RadiationDerivedFeaturesAdder()
   dataset = radiation_transform.transform(dataset)

   # Check what features were added
   print(atmos_transform.features_added())
   print(daylight_transform.features_added())
   print(radiation_transform.features_added())

The ``AtmosphereDerivedFeaturesAdder`` creates features from atmospheric conditions. The ``DaylightFeatureAdder`` adds features based on sun position and daylight hours—useful for solar generation and lighting-driven load. The ``RadiationDerivedFeaturesAdder`` derives additional solar radiation features.

For wind power forecasting, use the ``WindPowerFeatureAdder`` from the energy domain:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

   # Convert wind speed to wind power
   wind_transform = WindPowerFeatureAdder()
   dataset = wind_transform.transform(dataset)

This applies the wind power curve relationship, converting wind speed to expected power output based on turbine characteristics.

Time-Based Features
-------------------

Temporal patterns are fundamental to energy forecasting. OpenSTEF provides several approaches to capturing time-based information.

Lag Features
^^^^^^^^^^^^

Lag features shift historical values forward in time, making past observations available as predictors. A 24-hour lag of load gives the model yesterday's value at the same hour:

.. code-block:: python

   from openstef_models.transforms.time_domain import LagsAdder
   from datetime import timedelta

   # Create lag features for 1-hour and 24-hour lookback
   lag_transform = LagsAdder(
       feature='load',
       lags=[timedelta(hours=-1), timedelta(hours=-24)]
   )
   
   dataset = lag_transform.transform(dataset)
   
   # Lag features are named with ISO 8601 duration format
   # e.g., 'load_lag_-PT1H' for 1-hour lag, 'load_lag_-PT24H' for 24-hour lag

Negative timedeltas indicate lookback (past values). The transform automatically handles the time alignment and creates appropriately named features.

.. note::

   Lag features are constrained to the original dataset's time range. If your dataset covers 10:00-13:00 and you add a 2-hour lag, features will only be available from 12:00-13:00, not extending to 15:00.

For most forecasting tasks, you'll want multiple lags that capture different temporal patterns. Common choices include recent lags (1-3 hours), daily lags (24, 48 hours), and weekly lags (168 hours). The optimal set depends on your forecast horizon and data patterns.

Load Pattern Features
---------------------

Energy load exhibits recurring patterns that can be captured through engineered features. Beyond simple lags, you might create:

**Rolling statistics**: Moving averages or standard deviations of recent load values smooth out noise and capture trends.

**Difference features**: The change in load from one period to the next can be more predictive than absolute values, especially for short horizons.

**Pattern indicators**: Binary features marking special conditions (e.g., is_holiday, is_weekend) help models learn pattern breaks.

These features are typically created using custom transforms or by preprocessing your data before passing it to OpenSTEF.

Building Feature Pipelines
---------------------------

In practice, you'll combine multiple transforms into a pipeline. Each transform adds features, and the final dataset contains all engineered features plus the original data:

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder
   from openstef_models.transforms.time_domain import LagsAdder
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from datetime import timedelta

   # Start with raw data
   dataset = VersionedTimeSeriesDataset.from_dataframe(raw_data, timedelta(hours=1))

   # Apply transforms in sequence
   transforms = [
       AtmosphereDerivedFeaturesAdder(),
       WindPowerFeatureAdder(),
       LagsAdder(feature='load', lags=[
           timedelta(hours=-1),
           timedelta(hours=-24),
           timedelta(hours=-168)
       ]),
   ]

   for transform in transforms:
       dataset = transform.transform(dataset)

   # Now dataset contains original + engineered features
   snapshot = dataset.select_version()
   print(f"Total features: {len(snapshot.feature_names)}")

The order of transforms can matter. For example, if you want lag features of derived weather variables, create the weather features first, then add lags.

Custom Features
---------------

For domain-specific needs, you can create custom transforms by implementing the ``TimeSeriesTransform`` interface:

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig

   class CustomFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add custom domain-specific features."""
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add custom features to the dataset."""
           # Access the underlying dataframe
           df = data.data.copy()
           
           # Create new features
           df['temperature_squared'] = df['temperature'] ** 2
           df['temp_wind_interaction'] = df['temperature'] * df['windspeed_100m']
           
           # Return new dataset with added features
           return data.with_data(df)
       
       def features_added(self) -> list[str]:
           """List features this transform adds."""
           return ['temperature_squared', 'temp_wind_interaction']

Custom transforms integrate seamlessly with built-in transforms in your pipeline.

Feature Selection and Importance
---------------------------------

Not all engineered features improve model performance. Some may be redundant, noisy, or irrelevant for your specific forecasting task. After training a model, you can inspect feature importance to understand which features drive predictions:

.. code-block:: python

   from openstef_models.forecasters import XGBForecaster

   # Train model with engineered features
   forecaster = XGBForecaster()
   forecaster.fit(dataset)

   # Examine feature importance
   importance_df = forecaster.feature_importances
   print(importance_df.sort_values(by='0.5', ascending=False).head(10))

The ``feature_importances`` property returns a DataFrame showing how much each feature contributes to model predictions. Use this to identify which features matter most and to prune features that add little value.

For more on model selection and training, see :doc:`model_selection`. For understanding forecast outputs, see :doc:`quantiles_and_confidence`.

Practical Guidelines
--------------------

When engineering features for energy forecasting:

**Start simple**: Begin with basic weather variables and a few key lags. Add complexity only if it improves validation performance.

**Match features to forecast horizon**: For 1-hour ahead forecasts, recent lags (1-3 hours) matter most. For day-ahead forecasts, daily and weekly patterns become more important.

**Consider data availability**: Features must be available at prediction time. You can't use a 1-hour lag if you need to forecast before that data arrives.

**Test on holdout data**: Feature engineering decisions should be validated on data the model hasn't seen, not just training data.

**Use domain knowledge**: Physics-based features (like wind power curves) often outperform purely statistical features.

The goal is not to maximize the number of features, but to provide the model with information that captures the true drivers of the system you're forecasting.