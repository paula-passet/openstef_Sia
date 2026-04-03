Feature Engineering
===================

Feature engineering is the process of creating predictive variables (features) from raw data to improve forecasting accuracy. In energy forecasting, good features capture the physical drivers of energy consumption and generation—weather conditions, time patterns, and load dynamics. OpenSTEF provides a comprehensive set of transforms for creating and processing features tailored to short-term energy forecasting.

This page explains what makes effective features for energy forecasting and how to use OpenSTEF's feature engineering capabilities.

Why Features Matter
-------------------

Energy consumption and generation are driven by measurable factors. Temperature affects heating and cooling loads. Time of day determines baseline consumption patterns. Wind speed drives renewable generation. The quality of your features directly determines how well your model can learn these relationships.

Good features for energy forecasting share several characteristics:

- **Physical relevance**: They relate to known drivers of energy behavior
- **Temporal alignment**: They're available at forecast time (no look-ahead bias)
- **Consistent quality**: Missing or erratic data degrades model performance
- **Appropriate scale**: Normalized or standardized to prevent dominance by large-magnitude features

Weather Features
----------------

Weather is the primary external driver of energy consumption and renewable generation. OpenSTEF provides several transforms for weather-based features.

Basic Weather Variables
^^^^^^^^^^^^^^^^^^^^^^^

Temperature, wind speed, humidity, and radiation are fundamental inputs. These should be sourced from weather forecasts aligned with your prediction horizon:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   import pandas as pd
   from datetime import timedelta
   
   # Weather data from your forecast provider
   data = pd.DataFrame({
       'load': [100.0, 110.0, 120.0, 130.0],
       'temperature': [15.0, 16.0, 17.0, 18.0],
       'windspeed': [5.0, 6.0, 7.0, 8.0],
       'radiation': [200.0, 300.0, 400.0, 350.0]
   }, index=pd.date_range('2025-01-01', periods=4, freq='h'))
   
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data, 
       timedelta(hours=1)
   )

Derived Weather Features
^^^^^^^^^^^^^^^^^^^^^^^^

Raw weather variables often need transformation to capture their true impact. OpenSTEF provides transforms for common derived features:

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       DaylightFeatureAdder
   )
   from openstef_core.location import Coordinate
   
   # Add atmospheric features (e.g., dew point, heat index)
   atmosphere_transform = AtmosphereDerivedFeaturesAdder(
       pressure_column='pressure',
       relative_humidity_column='humidity',
       temperature_column='temperature'
   )
   
   # Add radiation-based features (solar angle, clear sky radiation)
   radiation_transform = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(latitude=52.0, longitude=5.0),
       radiation_column='radiation'
   )
   
   # Add daylight features (sunrise, sunset, day length)
   daylight_transform = DaylightFeatureAdder(
       coordinate=Coordinate(latitude=52.0, longitude=5.0)
   )
   
   # Apply transforms
   dataset = atmosphere_transform.transform(dataset)
   dataset = radiation_transform.transform(dataset)
   dataset = daylight_transform.transform(dataset)

Energy-Specific Features
^^^^^^^^^^^^^^^^^^^^^^^^

For renewable energy forecasting, wind power calculations convert wind speed to expected generation:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   wind_power_transform = WindPowerFeatureAdder(
       windspeed_reference_column='windspeed'
   )
   
   dataset = wind_power_transform.transform(dataset)

This applies a power curve relationship (typically cubic) to convert wind speed to power output, capturing the non-linear relationship between wind and generation.

Time Features
-------------

Energy consumption follows strong temporal patterns—daily cycles, weekly rhythms, seasonal variations. Time-based features help models learn these patterns.

Datetime Features
^^^^^^^^^^^^^^^^^

OpenSTEF extracts cyclical time features automatically:

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder
   )
   
   # Add hour, day of week, month, etc.
   datetime_transform = DatetimeFeaturesAdder(onehot_encode=False)
   
   # Convert to cyclical (sin/cos) representations
   cyclic_transform = CyclicFeaturesAdder()
   
   dataset = datetime_transform.transform(dataset)
   dataset = cyclic_transform.transform(dataset)

Cyclical encoding (sine and cosine transformations) ensures that hour 23 and hour 0 are treated as adjacent, not distant values.

Holiday Features
^^^^^^^^^^^^^^^^

Holidays disrupt normal consumption patterns. OpenSTEF includes holiday calendars:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder
   
   holiday_transform = HolidayFeatureAdder(country_code='NL')
   dataset = holiday_transform.transform(dataset)

This adds binary indicators for holidays and special days based on the country's calendar.

Lag Features
------------

Historical load values are powerful predictors. A lag feature is a past value of the target variable, shifted forward in time.

Creating Lag Features
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's ``LagsAdder`` creates lag features from the target variable:

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder
   from datetime import timedelta
   
   # Create 1-hour and 24-hour lag features
   lag_transform = VersionedLagsAdder(
       feature='load',
       lags=[timedelta(hours=-1), timedelta(hours=-24)]
   )
   
   dataset = lag_transform.transform(dataset)

The negative timedelta indicates looking backward in time. A -1 hour lag means "what was the load 1 hour ago?"

.. note::
   Lag features are constrained to the dataset's time range. If your data covers 10:00-13:00, a -2 hour lag will only have values from 12:00-13:00, not extending beyond the dataset boundaries.

Choosing Lag Periods
^^^^^^^^^^^^^^^^^^^^

Effective lag periods depend on your forecast horizon and the periodicity of your load:

- **Short-term patterns**: 1-hour, 2-hour lags capture immediate trends
- **Daily patterns**: 24-hour lags (or 96 for 15-minute data) capture day-over-day similarity
- **Weekly patterns**: 168-hour lags capture week-over-week patterns

For horizons beyond a few hours, recent lags may not be available at forecast time. Use lags that will be available when making real predictions.

Rolling Aggregate Features
---------------------------

Rolling statistics (mean, min, max) over recent windows capture short-term trends:

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from datetime import timedelta
   
   rolling_transform = RollingAggregatesAdder(
       feature='load',
       aggregation_functions=['mean', 'max', 'min'],
       horizons=[timedelta(hours=h) for h in [1, 3, 6, 12, 24]]
   )
   
   dataset = rolling_transform.transform(dataset)

This creates features like "average load over the past 3 hours" or "maximum load in the past 24 hours," helping models detect trends and volatility.

Custom Features
---------------

You can add domain-specific features by creating custom transforms. All transforms implement the ``TimeSeriesTransform`` interface:

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig
   
   class CustomFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add a custom feature based on domain knowledge."""
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Access the dataframe
           df = data.data.copy()
           
           # Add your custom feature
           df['custom_feature'] = df['temperature'] * df['windspeed']
           
           # Return updated dataset
           return data.with_data(df)
       
       def features_added(self) -> list[str]:
           return ['custom_feature']

This pattern allows you to encode specialized knowledge—interaction terms, threshold indicators, or business-specific variables—while maintaining compatibility with OpenSTEF's pipeline architecture.

Feature Preprocessing
---------------------

Raw features often need preprocessing before modeling.

Scaling and Normalization
^^^^^^^^^^^^^^^^^^^^^^^^^^

Standardization ensures features contribute proportionally:

.. code-block:: python

   from openstef_models.transforms.general import Scaler
   from openstef_core.selection import Exclude
   
   # Standardize all features except the target
   scaler = Scaler(
       selection=Exclude('load'),
       method='standard'
   )
   
   dataset = scaler.fit(dataset)
   dataset = scaler.transform(dataset)

Clipping Outliers
^^^^^^^^^^^^^^^^^

Extreme values can distort models. Clipping constrains features to observed ranges:

.. code-block:: python

   from openstef_models.transforms.general import Clipper
   from openstef_core.selection import Include
   
   clipper = Clipper(
       selection=Include(['temperature', 'windspeed']),
       mode='standard'
   )
   
   dataset = clipper.fit(dataset)
   dataset = clipper.transform(dataset)

Handling Missing Values
^^^^^^^^^^^^^^^^^^^^^^^

Missing data is inevitable. Imputation fills gaps:

.. code-block:: python

   from openstef_models.transforms.general import Imputer
   
   imputer = Imputer(
       selection=Exclude('load'),
       imputation_strategy='mean'
   )
   
   dataset = imputer.fit(dataset)
   dataset = imputer.transform(dataset)

Feature Selection and Importance
---------------------------------

Not all features improve predictions. OpenSTEF models expose feature importance to identify valuable predictors:

.. code-block:: python

   from openstef_models.regressors import XGBoostForecaster
   
   forecaster = XGBoostForecaster(
       quantiles=[0.1, 0.5, 0.9],
       horizons=[timedelta(hours=h) for h in [1, 6, 12, 24]]
   )
   
   forecaster.fit(train_data)
   
   # Access feature importance
   importance_df = forecaster.feature_importances
   print(importance_df.head(10))

This shows which features contribute most to predictions, guiding feature engineering efforts.

Practical Guidelines
--------------------

When engineering features for energy forecasting:

1. **Start simple**: Begin with weather and time features before adding complexity
2. **Respect forecast horizons**: Ensure features will be available at prediction time
3. **Monitor data quality**: Track missing values and outliers in production
4. **Iterate based on importance**: Use feature importance scores to refine your feature set
5. **Test incrementally**: Add features one group at a time and measure impact

Feature engineering is iterative. Start with OpenSTEF's built-in transforms, evaluate model performance, and add custom features as needed.

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding what you're predicting
- :doc:`model_selection` - Choosing models that work with your features
- :doc:`quantiles_and_confidence` - How features affect prediction uncertainty