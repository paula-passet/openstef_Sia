Feature Engineering for Energy Forecasting
===========================================

Feature engineering is the process of creating predictor variables that help machine learning models learn patterns in energy consumption and generation. In OpenSTEF, good features are crucial—the library combines classical machine learning models with domain-specific features to achieve high forecasting accuracy.

This page explains what makes effective features for short-term energy forecasting, covers the built-in feature types OpenSTEF provides, and shows how to add custom features to your forecasting pipeline.

Why Features Matter
-------------------

OpenSTEF relies on classical machine learning models (XGBoost, LightGBM, linear models) rather than deep learning. These models don't automatically learn complex patterns from raw data—they need well-engineered features that capture the physics and patterns of energy systems.

Good features for energy forecasting typically fall into these categories:

- **Weather features**: Temperature, solar radiation, wind speed, and derived atmospheric variables
- **Time features**: Hour of day, day of week, month, holidays—capturing daily and seasonal patterns
- **Load patterns**: Historical load values, rolling aggregates, and lag features
- **Custom domain features**: Energy prices, special events, or system-specific variables

Built-in Feature Types
----------------------

OpenSTEF provides several feature adders that automatically create predictor variables from your input data. These are implemented as transforms in the preprocessing pipeline.

Weather-Derived Features
^^^^^^^^^^^^^^^^^^^^^^^^

Weather is a primary driver of energy demand and renewable generation. OpenSTEF includes several transforms that create features from raw weather data:

**Wind power features** convert wind speed to estimated power output using a standard power curve:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   # Automatically adds wind power feature from wind speed
   wind_adder = WindPowerFeatureAdder(
       windspeed_reference_column="windspeed_100m"
   )

**Atmospheric features** derive additional variables from pressure, temperature, and humidity:

.. code-block:: python

   from openstef_models.transforms.energy_domain import AtmosphereDerivedFeaturesAdder
   
   adder = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="humidity",
       temperature_column="temp"
   )

**Radiation features** calculate solar position and derived radiation metrics based on location:

.. code-block:: python

   from openstef_models.transforms.energy_domain import RadiationDerivedFeaturesAdder
   from openstef_core.location import Coordinate
   
   adder = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(latitude=52.1326, longitude=5.2913),
       radiation_column="radiation"
   )

Time-Based Features
^^^^^^^^^^^^^^^^^^^

Temporal patterns are essential for capturing daily cycles, weekly patterns, and seasonal effects.

**Datetime features** extract components like hour, day of week, and month:

.. code-block:: python

   from openstef_models.transforms.general import DatetimeFeaturesAdder
   
   # Creates hour, day, month, etc. features
   # onehot_encode=False creates numeric features for tree models
   datetime_adder = DatetimeFeaturesAdder(onehot_encode=False)

**Cyclic features** encode time as sine/cosine pairs to preserve cyclical nature:

.. code-block:: python

   from openstef_models.transforms.general import CyclicFeaturesAdder
   
   # Converts time features to sin/cos pairs
   # Ensures hour 23 is "close" to hour 0
   cyclic_adder = CyclicFeaturesAdder()

**Daylight features** add sunrise/sunset times and daylight duration based on location:

.. code-block:: python

   from openstef_models.transforms.general import DaylightFeatureAdder
   
   daylight_adder = DaylightFeatureAdder(
       coordinate=Coordinate(latitude=52.1326, longitude=5.2913)
   )

**Holiday features** mark national and regional holidays:

.. code-block:: python

   from openstef_models.transforms.general import HolidayFeatureAdder
   
   # Uses country-specific holiday calendars
   holiday_adder = HolidayFeatureAdder(country_code="NL")

Load Pattern Features
^^^^^^^^^^^^^^^^^^^^^

Historical load patterns help models learn autocorrelation and recent trends.

**Rolling aggregates** create features from recent load history:

.. code-block:: python

   from openstef_models.transforms.general import RollingAggregatesAdder
   from openstef_core.enums import AggregationFunction
   from datetime import timedelta
   
   # Add mean and max of recent load
   rolling_adder = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=[
           AggregationFunction.MEAN,
           AggregationFunction.MAX
       ],
       horizons=[timedelta(hours=24), timedelta(hours=168)]
   )

This creates features like "load_mean_24h" and "load_max_168h" that capture recent patterns.

Feature Preprocessing
---------------------

After creating features, OpenSTEF applies preprocessing transforms to improve model performance.

**Clipping** constrains features to observed ranges, preventing extrapolation issues:

.. code-block:: python

   from openstef_models.transforms.general import Clipper
   from openstef_models.utils.feature_selection import Include
   
   # Clip specific features to training data ranges
   clipper = Clipper(
       selection=Include("temperature", "windspeed"),
       mode="standard"
   )

**Scaling** normalizes features for models sensitive to feature magnitude:

.. code-block:: python

   from openstef_models.transforms.general import Scaler
   from openstef_models.utils.feature_selection import Exclude
   
   # Standardize all features except target
   scaler = Scaler(
       selection=Exclude("load"),
       method="standard"
   )

**Empty feature removal** drops features with no variation:

.. code-block:: python

   from openstef_models.transforms.general import EmptyFeatureRemover
   
   # Automatically removes constant features
   remover = EmptyFeatureRemover()

Feature Selection
-----------------

OpenSTEF provides a flexible feature selection system for controlling which features transforms operate on.

The ``FeatureSelection`` class supports include/exclude patterns:

.. code-block:: python

   from openstef_models.utils.feature_selection import FeatureSelection, Include, Exclude
   
   # Select specific features
   selection = FeatureSelection(include={"load", "temperature", "radiation"})
   
   # Exclude specific features
   selection = FeatureSelection(exclude={"humidity"})
   
   # Combine patterns
   selection = Include("temp.*").combine(Exclude("temp_dewpoint"))

Use the ``Selector`` transform to filter features in a pipeline:

.. code-block:: python

   from openstef_models.transforms.general import Selector
   
   selector = Selector(
       selection=FeatureSelection(include={"load", "temperature"})
   )

Creating Custom Features
------------------------

For domain-specific requirements, you can add custom features by creating your own transform classes. All feature adders inherit from ``TimeSeriesTransform``.

Here's a simple example that adds a custom feature:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.base import TimeSeriesTransform
   from openstef_core.base_model import BaseConfig
   from pydantic import PrivateAttr
   
   class CustomFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add a custom domain-specific feature."""
       
       _is_fitted: bool = PrivateAttr(default=False)
       
       @property
       def is_fitted(self) -> bool:
           return self._is_fitted
       
       def fit(self, data: TimeSeriesDataset) -> None:
           self._is_fitted = True
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Create new feature from existing data
           new_data = data.data.copy()
           new_data["custom_feature"] = (
               new_data["temperature"] * new_data["load"]
           )
           return TimeSeriesDataset(new_data, data.resolution)
       
       def features_added(self) -> list[str]:
           return ["custom_feature"]

Add your custom transform to a pipeline configuration:

.. code-block:: python

   from openstef_models.pipelines import create_pipeline
   
   pipeline = create_pipeline(
       config=config,
       additional_transforms=[CustomFeatureAdder()]
   )

What Makes Good Features
-------------------------

Effective features for energy forecasting share these characteristics:

**Physical relevance**: Features should relate to actual drivers of energy demand or generation. Temperature affects heating/cooling load, solar radiation drives PV output, wind speed determines wind power.

**Temporal alignment**: Weather forecasts and load patterns must align with the forecast horizon. Don't use future information that wouldn't be available at prediction time.

**Stability**: Features should be reliably available and not prone to data quality issues. Missing or erratic features hurt model performance.

**Low correlation**: Highly correlated features provide redundant information. OpenSTEF's feature importance analysis can help identify redundant features.

**Appropriate granularity**: Feature resolution should match forecast resolution. Hourly forecasts need hourly features, not daily averages.

Configuration Example
---------------------

Here's how feature engineering fits into a complete pipeline configuration:

.. code-block:: python

   from openstef_core.config import PipelineConfig
   from openstef_core.location import Location, Coordinate
   from openstef_core.enums import AggregationFunction
   from datetime import timedelta
   
   config = PipelineConfig(
       # Location for solar/daylight features
       location=Location(
           coordinate=Coordinate(latitude=52.1326, longitude=5.2913),
           country_code="NL"
       ),
       
       # Enable rolling aggregate features
       rolling_aggregate_features=[
           AggregationFunction.MEAN,
           AggregationFunction.MAX
       ],
       
       # Configure feature clipping
       clip_features=FeatureSelection(
           include={"temperature", "windspeed", "radiation"}
       ),
       
       # Weather column mappings
       temperature_column="temp",
       wind_speed_column="windspeed_100m",
       radiation_column="radiation",
       pressure_column="pressure",
       relative_humidity_column="humidity"
   )

The pipeline automatically creates all standard features based on this configuration.

Next Steps
----------

- See :doc:`model_selection` for how different models use features
- Learn about :doc:`forecasting_basics` to understand how features drive predictions
- Explore :doc:`reliability_and_fallback` for handling missing feature data

Feature engineering is where domain knowledge meets machine learning. OpenSTEF provides sensible defaults for energy forecasting, but the best results come from understanding your specific use case and tailoring features accordingly.