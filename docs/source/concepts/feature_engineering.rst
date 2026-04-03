Feature Engineering
===================

Feature engineering is the process of transforming raw input data into predictors that help machine learning models learn patterns in energy consumption. OpenSTEF provides a comprehensive set of transforms to create features from weather data, time information, and historical load patterns. Good features capture the underlying drivers of energy demand and make forecasting models more accurate and reliable.

This page explains what makes effective features for energy forecasting, describes the main feature categories available in OpenSTEF, and shows how to create custom features for your specific use case.

Why Features Matter
-------------------

Energy consumption follows predictable patterns driven by weather conditions, time of day, day of week, and seasonal cycles. Raw input data like temperature measurements or timestamps don't directly capture these relationships. Feature engineering bridges this gap by creating representations that models can learn from effectively.

For example, a raw temperature value of 15°C doesn't tell the model much on its own. But derived features like "heating degree days" or "temperature deviation from seasonal average" capture the relationship between temperature and heating/cooling demand. Similarly, a timestamp becomes more useful when transformed into cyclic features that represent daily and weekly patterns.

Weather Features
----------------

Weather is the primary driver of short-term energy demand. OpenSTEF includes several transforms for creating weather-based features from standard meteorological inputs.

Basic Weather Inputs
^^^^^^^^^^^^^^^^^^^^

The most important weather predictors for energy forecasting are:

- **Temperature**: Drives heating and cooling demand
- **Radiation**: Solar radiation affects both demand (cooling) and supply (solar generation)
- **Wind speed**: Influences heating demand and wind power generation
- **Humidity**: Affects perceived temperature and cooling demand
- **Pressure**: Can indicate weather system changes

These are typically provided as columns in your input data, either from measurements or numerical weather predictions.

Derived Weather Features
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF automatically creates derived features that capture non-linear weather relationships:

**Atmosphere-derived features** combine temperature, humidity, and pressure to calculate quantities like heat index or apparent temperature. The ``AtmosphereDerivedFeaturesAdder`` transform handles this:

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder
   
   transform = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="humidity",
       temperature_column="temperature"
   )
   
   transformed_data = transform.transform(dataset)

**Radiation-derived features** account for solar angle, daylight hours, and seasonal variation. The ``RadiationDerivedFeaturesAdder`` uses geographic coordinates to calculate sun position:

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
   from openstef_core.coordinates import Coordinate
   
   transform = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(latitude=52.1, longitude=5.2),
       radiation_column="radiation"
   )

**Wind power features** convert wind speed at measurement height to estimated wind power generation. This is particularly valuable for areas with significant wind capacity:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   transform = WindPowerFeatureAdder(
       windspeed_reference_column="windspeed",
       reference_height=10.0,  # measurement height in meters
       hub_height=100.0,       # turbine hub height
       rated_power=1.0         # normalized to 1 MWp
   )
   
   transformed_data = transform.transform(dataset)
   # Adds 'windspeed_hub_height' and 'wind_power' features

The wind power calculation uses a sigmoid power curve with configurable steepness and slope parameters to model turbine behavior.

Time Features
-------------

Temporal patterns are crucial for energy forecasting. People follow daily routines, businesses operate on weekly schedules, and seasonal cycles affect both demand and supply.

Cyclic Features
^^^^^^^^^^^^^^^

Time is inherently cyclic—hour 23 is close to hour 0, December is close to January. Linear time representations break these relationships. The ``CyclicFeaturesAdder`` transform creates sine and cosine encodings that preserve cyclic structure:

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder
   
   transform = CyclicFeaturesAdder()
   transformed_data = transform.transform(dataset)

This creates paired sin/cos features for hour of day, day of week, day of year, and other temporal cycles. Models can learn smooth periodic patterns from these representations.

Datetime Features
^^^^^^^^^^^^^^^^^

The ``DatetimeFeaturesAdder`` extracts discrete time components like hour, day of week, month, and quarter:

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder
   
   # One-hot encoding for categorical treatment
   transform = DatetimeFeaturesAdder(onehot_encode=True)
   
   # Or integer encoding for tree-based models
   transform = DatetimeFeaturesAdder(onehot_encode=False)

One-hot encoding works well for linear models, while integer encoding is more efficient for tree-based models like XGBoost or LightGBM.

Holiday Features
^^^^^^^^^^^^^^^^

Holidays significantly affect energy consumption patterns. The ``HolidayFeatureAdder`` marks holidays and special days for a given country:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder
   
   transform = HolidayFeatureAdder(country_code="NL")
   transformed_data = transform.transform(dataset)

This creates binary indicators for holidays, which helps models learn that consumption patterns differ on these days.

Daylight Features
^^^^^^^^^^^^^^^^^

Daylight duration affects both energy demand (lighting) and solar generation. The ``DaylightFeatureAdder`` calculates sunrise, sunset, and daylight hours based on geographic location:

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder
   from openstef_core.coordinates import Coordinate
   
   transform = DaylightFeatureAdder(
       coordinate=Coordinate(latitude=52.1, longitude=5.2)
   )

Load Pattern Features
---------------------

Historical load patterns contain valuable information about consumption behavior. Recent load values, rolling averages, and load variability all help predict future demand.

Rolling Aggregates
^^^^^^^^^^^^^^^^^^

Rolling statistics capture recent trends and typical load levels. The ``RollingAggregatesAdder`` creates features like rolling mean, minimum, maximum, and standard deviation:

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from openstef_core.enums import AggregationFunction
   from openstef_core.models import LeadTime
   
   transform = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=[
           AggregationFunction.MEAN,
           AggregationFunction.MIN,
           AggregationFunction.MAX
       ],
       horizons=[LeadTime.from_string("PT36H")]
   )

Rolling features are particularly useful for capturing load persistence—the tendency for consumption to remain similar over short time periods.

.. warning::

   Rolling features must be calculated carefully to avoid data leakage. OpenSTEF ensures that only past data is used when creating features for future predictions.

Energy Price Features
---------------------

Energy prices (like APX day-ahead prices) can be predictive features when available. Price-responsive consumers and industrial loads may shift consumption based on price signals. Include price data as a column in your input dataset, and OpenSTEF will use it as a feature if present.

What Makes Good Features
-------------------------

Effective features for energy forecasting share several characteristics:

**Relevance**: Features should relate to actual drivers of energy consumption. Temperature matters because people heat and cool buildings. Day of week matters because work schedules affect demand.

**Availability**: Features must be available at prediction time. You can't use tomorrow's actual temperature to forecast tomorrow's load—you need temperature forecasts instead. This is why OpenSTEF distinguishes between training data (with measurements) and prediction data (with forecasts).

**Stability**: Features should have consistent meaning over time. A feature that changes definition or measurement method will confuse models and degrade accuracy.

**Non-redundancy**: Highly correlated features provide little additional information. OpenSTEF's ``EmptyFeatureRemover`` automatically drops features with zero variance, and feature scaling helps manage multicollinearity.

**Appropriate scale**: Features with very different scales can cause training difficulties. OpenSTEF's ``Scaler`` transform standardizes features to similar ranges.

Custom Features
---------------

You can create domain-specific features by implementing custom transforms. Any transform that follows the ``TimeSeriesTransform`` interface can be integrated into OpenSTEF pipelines.

A custom transform needs three methods:

.. code-block:: python

   from openstef_models.transforms.base import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   
   class CustomFeatureAdder(TimeSeriesTransform):
       def fit(self, data: TimeSeriesDataset) -> None:
           """Learn any parameters from training data."""
           pass
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add custom features to the dataset."""
           df = data.data.copy()
           
           # Example: add a feature based on domain knowledge
           df['custom_feature'] = df['temperature'] * df['humidity'] / 100.0
           
           return TimeSeriesDataset(df, data.resolution)
       
       def features_added(self) -> list[str]:
           """Return names of features this transform adds."""
           return ['custom_feature']

Custom features are most valuable when they encode domain knowledge specific to your forecasting problem—like local events, industrial schedules, or regional weather patterns.

Feature Selection
-----------------

Not all features improve model performance. Too many features can lead to overfitting, longer training times, and reduced interpretability. OpenSTEF provides configuration options for feature selection:

.. code-block:: python

   from openstef_core.enums import FeatureSelection, Include, Exclude
   
   # Select specific features to clip
   clip_features = FeatureSelection(
       include=Include("temperature", "radiation"),
       exclude=None
   )

Feature importance analysis (covered in :doc:`model_selection`) helps identify which features contribute most to forecast accuracy.

Next Steps
----------

Now that you understand feature engineering, explore:

- :doc:`model_selection` - Learn how different models use features
- :doc:`forecasting_basics` - Understand how features fit into the forecasting workflow
- :doc:`quantiles_and_confidence` - See how features affect prediction uncertainty

The API reference for transforms is available in the ``openstef_models.transforms`` module documentation.