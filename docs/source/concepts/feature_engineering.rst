Feature Engineering
===================

Feature engineering is the process of creating predictive variables that help forecasting models understand and predict energy demand patterns. In energy forecasting, good features capture the key drivers of load: weather conditions, temporal patterns, and historical behavior. This page explains what makes effective features for short-term energy forecasting and how to create them using OpenSTEF.

Why Features Matter
-------------------

Energy demand follows predictable patterns driven by weather, time of day, day of week, and seasonal cycles. A forecasting model is only as good as the features you provide it. Well-engineered features help models:

- Capture seasonal and daily cycles
- Respond to weather changes (temperature, solar radiation, wind)
- Recognize special days (holidays, weekends)
- Learn from recent load patterns

OpenSTEF provides built-in transforms that automatically generate these features from basic inputs like timestamps and weather data.

Core Feature Categories
-----------------------

Weather Features
^^^^^^^^^^^^^^^^

Weather is the primary driver of energy demand. Temperature affects heating and cooling loads, solar radiation impacts solar generation and cooling demand, and wind speed influences wind power output.

OpenSTEF includes several weather-related transforms:

**AtmosphereDerivedFeaturesAdder** calculates derived meteorological features from basic weather data like pressure, relative humidity, and temperature. These derived features often capture non-linear relationships better than raw measurements.

**RadiationDerivedFeaturesAdder** computes solar position and radiation-based features using geographic coordinates. This helps models understand solar generation patterns and temperature-radiation interactions.

**WindPowerFeatureAdder** transforms wind speed into wind power estimates, which is crucial for wind generation forecasting or understanding wind's impact on demand.

Here's how to use weather transforms:

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta
   import pandas as pd

   # Your data with basic weather columns
   data = pd.DataFrame({
       'load': [100.0, 110.0, 105.0],
       'temperature': [20.0, 22.0, 21.0],
       'radiation': [200.0, 400.0, 300.0],
       'windspeed': [5.0, 7.0, 6.0],
       'pressure': [1013.0, 1012.0, 1013.5],
       'humidity': [60.0, 65.0, 62.0],
   }, index=pd.date_range('2024-01-01', periods=3, freq='h', tz='UTC'))

   dataset = TimeSeriesDataset(data, timedelta(hours=1))

   # Add derived weather features
   atmosphere_adder = AtmosphereDerivedFeaturesAdder(
       pressure_column='pressure',
       relative_humidity_column='humidity',
       temperature_column='temperature',
   )
   dataset = atmosphere_adder.transform(dataset)

   radiation_adder = RadiationDerivedFeaturesAdder(
       coordinate=(52.0, 5.0),  # latitude, longitude
       radiation_column='radiation',
   )
   dataset = radiation_adder.transform(dataset)

   wind_adder = WindPowerFeatureAdder(windspeed_reference_column='windspeed')
   dataset = wind_adder.transform(dataset)

Time Features
^^^^^^^^^^^^^

Temporal patterns are fundamental to energy forecasting. Load varies by hour of day, day of week, and season. OpenSTEF provides several time-based transforms:

**DatetimeFeaturesAdder** extracts basic temporal features like hour, day of week, month, and year from the timestamp index.

**CyclicFeaturesAdder** creates cyclic encodings of time features using sine and cosine transformations. This helps models understand that hour 23 and hour 0 are adjacent, or that December and January are consecutive months.

**HolidayFeatureAdder** adds indicators for national holidays and special days, which often have different load patterns than regular weekdays.

**DaylightFeatureAdder** computes sunrise, sunset, and daylight duration based on geographic location. This is particularly useful for solar forecasting and understanding lighting-related demand.

Example of time feature engineering:

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder,
       HolidayFeatureAdder,
       DaylightFeatureAdder,
   )

   # Add datetime features
   datetime_adder = DatetimeFeaturesAdder(onehot_encode=False)
   dataset = datetime_adder.transform(dataset)

   # Add cyclic encodings (hour, day of week, month)
   cyclic_adder = CyclicFeaturesAdder()
   dataset = cyclic_adder.transform(dataset)

   # Add holiday indicators
   holiday_adder = HolidayFeatureAdder(country_code='NL')
   dataset = holiday_adder.transform(dataset)

   # Add daylight features
   daylight_adder = DaylightFeatureAdder(coordinate=(52.0, 5.0))
   dataset = daylight_adder.transform(dataset)

Load Pattern Features
^^^^^^^^^^^^^^^^^^^^^

Historical load patterns contain valuable information about recent trends and typical behavior. The **RollingAggregatesAdder** creates lagged and rolling statistics from the target variable.

You can compute various aggregations (mean, min, max, standard deviation) over different time windows. This helps models learn from recent load behavior and detect unusual patterns.

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from openstef_models.utils.aggregation_functions import AggregationFunction
   from openstef_core.time import LeadTime

   # Add rolling aggregates of load
   rolling_adder = RollingAggregatesAdder(
       feature='load',
       aggregation_functions=[
           AggregationFunction.MEAN,
           AggregationFunction.MIN,
           AggregationFunction.MAX,
       ],
       horizons=[LeadTime.from_string('PT24H')],
   )
   dataset = rolling_adder.transform(dataset)

.. warning::

   Rolling aggregate features use historical target values. Be careful about data leakage when creating features for future predictions - only use information that would be available at prediction time.

Custom Features
^^^^^^^^^^^^^^^

While OpenSTEF provides many built-in features, you may need domain-specific predictors. You can add custom features directly to your input DataFrame before creating a TimeSeriesDataset, or implement custom transforms following the TimeSeriesTransform interface.

Common custom features for energy forecasting include:

- Energy prices (day-ahead market prices)
- Industrial activity indicators
- School calendar information
- Special events or maintenance schedules
- Derived features specific to your grid or customer base

.. code-block:: python

   # Add custom features to your data
   data['energy_price'] = [50.0, 55.0, 52.0]  # EUR/MWh
   data['is_school_holiday'] = [0, 0, 1]
   
   dataset = TimeSeriesDataset(data, timedelta(hours=1))

Feature Selection and Importance
---------------------------------

Not all features improve model performance. Too many irrelevant features can lead to overfitting and slower training. OpenSTEF provides tools for feature selection and understanding feature importance.

The **Selector** transform allows you to include or exclude specific features:

.. code-block:: python

   from openstef_models.transforms.general import Selector
   from openstef_models.utils.feature_selection import FeatureSelection

   # Select only specific features
   selector = Selector(
       selection=FeatureSelection(include={'load', 'temperature', 'radiation'})
   )
   dataset = selector.transform(dataset)

After training a model, you can examine feature importances to understand which predictors are most valuable:

.. code-block:: python

   # Train a model (see model_selection page for details)
   # Then examine feature importances
   importances = model.feature_importances
   print(importances.sort_values(ascending=False))

This helps you identify which features drive predictions and which might be removed to simplify the model.

Feature Preprocessing
---------------------

Raw features often need preprocessing before model training. OpenSTEF includes several preprocessing transforms:

**Clipper** limits feature values to reasonable ranges, preventing outliers from distorting models.

**Scaler** standardizes features to have similar scales, which improves convergence for many algorithms.

**EmptyFeatureRemover** automatically drops features with all missing or constant values.

These transforms are typically applied after feature creation:

.. code-block:: python

   from openstef_models.transforms.general import Clipper, Scaler, EmptyFeatureRemover
   from openstef_models.utils.feature_selection import Include, Exclude

   # Clip specific features to standard ranges
   clipper = Clipper(
       selection=Include('temperature', 'radiation'),
       mode='standard'
   )
   dataset = clipper.transform(dataset)

   # Scale all features except the target
   scaler = Scaler(
       selection=Exclude('load'),
       method='standard'
   )
   dataset = scaler.transform(dataset)

   # Remove empty features
   remover = EmptyFeatureRemover()
   dataset = remover.transform(dataset)

Best Practices
--------------

**Start with built-in features**: OpenSTEF's default feature set works well for most energy forecasting tasks. Start there before adding custom features.

**Understand your domain**: The best features depend on what you're forecasting. Solar generation needs radiation features, wind generation needs wind features, demand forecasting needs temperature and time features.

**Avoid data leakage**: Only use information that would be available at prediction time. Don't include future values of the target or features that contain future information.

**Test feature impact**: Add features incrementally and measure their impact on forecast accuracy. Not every feature improves performance.

**Consider computational cost**: More features mean longer training times. Balance accuracy gains against computational resources.

**Monitor feature availability**: In production, missing weather data or other features can break forecasts. See :doc:`reliability_and_fallback` for handling missing data.

Next Steps
----------

Now that you understand feature engineering, explore:

- :doc:`model_selection` - Choose the right model for your features
- :doc:`forecasting_basics` - Understand the forecasting task
- :doc:`quantiles_and_confidence` - Learn about probabilistic forecasts

For implementation details, see the API documentation for specific transforms in the ``openstef_models.transforms`` module.