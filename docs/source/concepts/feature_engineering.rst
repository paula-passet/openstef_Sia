Feature Engineering
===================

Feature engineering is the process of transforming raw input data into predictive features that machine learning models can use effectively. In energy forecasting, good features capture the patterns that drive energy consumption and generation: weather conditions, time-based cycles, historical load patterns, and domain-specific indicators.

OpenSTEF provides a comprehensive set of feature transforms that handle the most important predictors for short-term energy forecasting. These transforms are composable, allowing you to build custom feature pipelines tailored to your specific forecasting needs.

What Makes Good Features for Energy Forecasting
------------------------------------------------

Energy consumption and generation follow predictable patterns driven by a few key factors:

**Weather conditions** are the primary external driver. Temperature affects heating and cooling loads, solar radiation drives PV generation, wind speed determines wind power output, and humidity influences perceived temperature and comfort-driven consumption.

**Time-based patterns** capture human behavior and natural cycles. Daily patterns reflect work schedules and activity levels, weekly patterns distinguish weekdays from weekends, seasonal cycles track heating and cooling seasons, and holiday effects capture reduced industrial activity or changed residential patterns.

**Historical load patterns** provide context about recent behavior. Recent load values capture short-term momentum, rolling aggregates smooth out noise and reveal trends, and lag features allow models to learn autoregressive relationships.

**Domain-specific features** encode expert knowledge. For solar forecasting, daylight hours and sun position matter. For wind forecasting, atmospheric pressure gradients are relevant. For demand forecasting, energy prices may influence consumption.

The best features are those that:

- Have strong correlation with the target variable
- Are available at forecast time (no data leakage)
- Are reliable and consistently measured
- Capture non-linear relationships through appropriate transformations
- Are interpretable to domain experts

Weather Features
----------------

Weather is the most important external predictor for energy forecasting. OpenSTEF provides several transforms for working with weather data.

Basic weather features include temperature, radiation, wind speed, pressure, and humidity. These are typically provided by weather services or measurement stations. OpenSTEF expects these as columns in your input data.

**Derived atmospheric features** calculate additional predictors from basic weather measurements:

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder
   
   transform = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="humidity",
       temperature_column="temp"
   )
   
   # Adds derived features like dew point, heat index, etc.
   transformed_data = transform.transform(input_data)

**Radiation-derived features** are particularly important for solar forecasting:

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
   from openstef_core.location import Coordinate
   
   transform = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(lat=52.1326, lon=5.2913),  # Utrecht
       radiation_column="radiation"
   )
   
   transformed_data = transform.transform(input_data)

This transform calculates features like solar angle, theoretical clear-sky radiation, and cloud cover indicators based on the difference between measured and theoretical radiation.

**Wind power features** convert wind speed into estimated power output:

.. code-block:: python

   from openstef_models.transforms.weather_domain import WindPowerFeatureAdder
   
   transform = WindPowerFeatureAdder(
       windspeed_reference_column="windspeed_100m"
   )
   
   transformed_data = transform.transform(input_data)

This applies a power curve transformation that captures the non-linear relationship between wind speed and turbine output.

Time Features
-------------

Time-based features capture cyclical patterns in energy consumption and generation. OpenSTEF provides several transforms for extracting temporal patterns.

**Datetime features** extract basic time components:

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder
   
   transform = DatetimeFeaturesAdder(onehot_encode=False)
   transformed_data = transform.transform(input_data)

This adds features like hour of day, day of week, month, and quarter. The ``onehot_encode`` parameter controls whether these are encoded as integers or one-hot vectors. Tree-based models typically work better with integer encoding, while linear models may benefit from one-hot encoding.

**Cyclic features** encode time components as sine/cosine pairs to capture their cyclical nature:

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder
   
   transform = CyclicFeaturesAdder()
   transformed_data = transform.transform(input_data)

This ensures that hour 23 and hour 0 are treated as adjacent, which is important for capturing patterns that span midnight.

**Holiday features** flag special days with different consumption patterns:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder
   
   transform = HolidayFeatureAdder(country_code="NL")
   transformed_data = transform.transform(input_data)

This adds binary indicators for national holidays, which often show significantly different load patterns than regular days.

**Daylight features** capture sunrise, sunset, and day length:

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder
   from openstef_core.location import Coordinate
   
   transform = DaylightFeatureAdder(
       coordinate=Coordinate(lat=52.1326, lon=5.2913)
   )
   
   transformed_data = transform.transform(input_data)

These features are particularly useful for residential load forecasting, where lighting and activity patterns follow daylight hours.

Load Pattern Features
---------------------

Historical load values provide crucial context for forecasting. The most common approach is to use rolling aggregates that summarize recent behavior.

**Rolling aggregates** compute statistics over recent time windows:

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from openstef_core.enums import AggregationFunction
   from openstef_core.lead_time import LeadTime
   
   transform = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=[
           AggregationFunction.MEAN,
           AggregationFunction.MIN,
           AggregationFunction.MAX
       ],
       horizons=[LeadTime.from_string("PT24H")]
   )
   
   transformed_data = transform.transform(input_data)

This creates features like "mean load over the past 24 hours" or "maximum load over the past 24 hours". These features help models understand recent trends and typical operating ranges.

Common aggregation windows include:

- Last 24 hours: captures daily patterns
- Last 7 days: captures weekly patterns  
- Last hour: captures very short-term momentum

Be careful with rolling aggregates to avoid data leakage. The window should only include data that would be available at forecast time. OpenSTEF's transforms handle this automatically by respecting the forecast horizon.

Building Custom Feature Pipelines
----------------------------------

OpenSTEF's transform system is composable. You can chain multiple transforms together to build custom feature engineering pipelines:

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       DaylightFeatureAdder
   )
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       HolidayFeatureAdder,
       DatetimeFeaturesAdder
   )
   from openstef_core.location import Coordinate
   
   # Define location
   location = Coordinate(lat=52.1326, lon=5.2913)
   
   # Build feature pipeline
   transforms = [
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity", 
           temperature_column="temp"
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=location,
           radiation_column="radiation"
       ),
       DaylightFeatureAdder(coordinate=location),
       CyclicFeaturesAdder(),
       HolidayFeatureAdder(country_code="NL"),
       DatetimeFeaturesAdder(onehot_encode=False)
   ]
   
   # Apply transforms sequentially
   data = input_data
   for transform in transforms:
       data = transform.transform(data)

This pattern is exactly what OpenSTEF's forecasting workflows use internally. The workflow configuration controls which transforms are included and how they're configured.

Feature Selection and Importance
---------------------------------

Not all features are equally useful. OpenSTEF provides tools to understand which features matter most for your forecasts.

**Feature importance** shows which predictors have the strongest influence on model predictions:

.. code-block:: python

   from openstef_models.forecasters import XGBoostForecaster
   
   # After training a model
   forecaster = XGBoostForecaster(...)
   forecaster.fit(training_data)
   
   # Get feature importances
   importances = forecaster.feature_importances
   print(importances)

This returns a DataFrame ranking features by their contribution to the model. Use this to:

- Validate that important domain features are being used
- Identify redundant or noisy features
- Debug unexpected model behavior
- Communicate model logic to stakeholders

**Feature selection** allows you to include or exclude specific features:

.. code-block:: python

   from openstef_core.feature_selection import Include, Exclude
   
   # Only clip specific features
   clip_selection = Include(["temp", "radiation", "windspeed"])
   
   # Exclude target from scaling
   scale_selection = Exclude(["load"])

This is useful when you want to apply certain preprocessing steps (like clipping outliers or scaling) only to specific features.

Best Practices
--------------

**Start simple, then add complexity.** Begin with basic weather and time features. Add rolling aggregates and derived features only if they improve validation performance. More features aren't always better—they can lead to overfitting and slower training.

**Match features to your use case.** Solar forecasting needs radiation features. Wind forecasting needs wind features. Demand forecasting may need price features. Don't blindly apply all available transforms.

**Validate feature availability.** Ensure all features will be available at forecast time. Weather forecasts may not include all measured variables. Historical load data may have gaps. Use OpenSTEF's completeness checks to catch these issues early.

**Monitor feature quality.** Weather data can have sensor failures, communication issues, or quality problems. Use OpenSTEF's data validation transforms to detect flatliners, outliers, and missing data before they corrupt your forecasts.

**Consider computational cost.** Some features are expensive to compute (e.g., complex rolling aggregates over long windows). Balance predictive value against training and inference time.

**Document your choices.** Feature engineering encodes domain knowledge. Document why you included specific features and what patterns they're meant to capture. This helps others understand and maintain your forecasting system.

See Also
--------

- :doc:`forecasting_basics` - Understanding what short-term forecasting is and why feature engineering matters
- :doc:`model_selection` - How different models use features differently
- :doc:`/workflows/index` - How feature engineering fits into complete forecasting workflows