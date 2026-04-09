Feature Engineering for Energy Forecasting
===========================================

Feature engineering is the process of transforming raw input data into predictive features that help machine learning models understand energy consumption and generation patterns. In OpenSTEF, good features capture the physical relationships, temporal patterns, and external factors that drive energy demand and supply.

This page explains what makes effective features for energy forecasting, the built-in feature transformations OpenSTEF provides, and how to create custom features for your specific use case.

Why Features Matter
-------------------

Energy forecasting relies on classical machine learning models like XGBoost and LightGBM. Unlike deep learning approaches that learn representations automatically, these models depend heavily on domain knowledge embedded in features. Well-engineered features enable simple models to achieve high performance by explicitly encoding:

- **Physical relationships**: Solar radiation and temperature determine PV generation
- **Temporal patterns**: Hour of day, day of week, and seasonal cycles
- **Historical context**: Recent load patterns predict near-term demand
- **External factors**: Weather conditions, holidays, and energy prices

OpenSTEF provides a comprehensive set of feature transformations designed specifically for energy domain applications.

Weather-Based Features
----------------------

Weather conditions are primary drivers of energy demand and renewable generation. OpenSTEF includes several transformations that derive meaningful features from raw weather data.

Wind Power Features
^^^^^^^^^^^^^^^^^^^

The ``WindPowerFeatureAdder`` converts wind speed measurements into estimated wind power using standard power curve calculations:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   wind_features = WindPowerFeatureAdder(
       windspeed_reference_column="windspeed_100m"
   )
   
   # Adds wind power estimate based on wind speed
   transformed_data = wind_features.transform(dataset)

This transformation applies the physics of wind turbine power curves, accounting for cut-in speeds, rated power, and cut-out speeds.

Atmospheric Features
^^^^^^^^^^^^^^^^^^^^

The ``AtmosphereDerivedFeaturesAdder`` computes derived atmospheric variables that affect energy consumption:

.. code-block:: python

   from openstef_models.transforms.energy_domain import AtmosphereDerivedFeaturesAdder
   
   atmosphere_features = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="humidity",
       temperature_column="temp"
   )

This creates features like dew point, heat index, and other derived quantities that capture human comfort conditions affecting heating and cooling demand.

Solar Radiation Features
^^^^^^^^^^^^^^^^^^^^^^^^

The ``RadiationDerivedFeaturesAdder`` transforms solar radiation measurements into features relevant for PV generation and solar heating effects:

.. code-block:: python

   from openstef_models.transforms.energy_domain import RadiationDerivedFeaturesAdder
   
   radiation_features = RadiationDerivedFeaturesAdder(
       coordinate=(52.1326, 5.2913),  # latitude, longitude
       radiation_column="global_radiation"
   )

This accounts for geographic location, sun angle, and seasonal variations in solar energy availability.

Temporal Features
-----------------

Time-based patterns are fundamental to energy forecasting. OpenSTEF provides several transformations that encode temporal information in model-friendly formats.

Cyclic Features
^^^^^^^^^^^^^^^

The ``CyclicFeaturesAdder`` encodes periodic time features using sine and cosine transformations, which properly represent the circular nature of time:

.. code-block:: python

   from openstef_models.transforms.general import CyclicFeaturesAdder
   
   cyclic_features = CyclicFeaturesAdder()

This creates features like ``hour_sin``, ``hour_cos``, ``day_of_week_sin``, and ``day_of_week_cos`` that allow models to learn that 23:00 and 00:00 are adjacent hours, or that Sunday and Monday are consecutive days.

Datetime Features
^^^^^^^^^^^^^^^^^

The ``DatetimeFeaturesAdder`` extracts standard calendar features from timestamps:

.. code-block:: python

   from openstef_models.transforms.general import DatetimeFeaturesAdder
   
   datetime_features = DatetimeFeaturesAdder(
       onehot_encode=False  # Use integer encoding for tree-based models
   )

This adds features like hour of day, day of week, month, and week of year. For tree-based models like XGBoost, integer encoding is preferred; for linear models, one-hot encoding may be more appropriate.

Daylight Features
^^^^^^^^^^^^^^^^^

The ``DaylightFeatureAdder`` computes sunrise, sunset, and daylight duration based on geographic location:

.. code-block:: python

   from openstef_models.transforms.energy_domain import DaylightFeatureAdder
   
   daylight_features = DaylightFeatureAdder(
       coordinate=(52.1326, 5.2913)
   )

These features capture seasonal variations in daylight hours that affect both energy consumption patterns and solar generation potential.

Holiday Features
^^^^^^^^^^^^^^^^

The ``HolidayFeatureAdder`` marks national holidays and special days that alter normal energy consumption patterns:

.. code-block:: python

   from openstef_models.transforms.general import HolidayFeatureAdder
   
   holiday_features = HolidayFeatureAdder(
       country_code="NL"
   )

This is crucial for capturing the reduced industrial demand and shifted residential patterns that occur on holidays.

Load Pattern Features
---------------------

Historical load patterns provide strong signals for short-term forecasting. OpenSTEF includes transformations that capture recent trends and patterns.

Rolling Aggregates
^^^^^^^^^^^^^^^^^^

The ``RollingAggregatesAdder`` computes statistical summaries over recent time windows:

.. code-block:: python

   from openstef_models.transforms.energy_domain import RollingAggregatesAdder
   from datetime import timedelta
   
   rolling_features = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std", "min", "max"],
       horizons=[timedelta(hours=24), timedelta(hours=168)]
   )

This creates features like the mean load over the past 24 hours or the standard deviation over the past week, capturing both recent trends and variability.

.. warning::
   Rolling aggregate features introduce temporal dependencies. Ensure your training data properly handles these lags to avoid data leakage.

Feature Preprocessing
---------------------

Beyond feature creation, OpenSTEF provides transformations for preparing features for model training.

Clipping
^^^^^^^^

The ``Clipper`` constrains feature values to observed ranges, preventing extrapolation to unrealistic values:

.. code-block:: python

   from openstef_models.transforms.general import Clipper
   from openstef_core.feature_selection import Include
   
   clipper = Clipper(
       selection=Include({"temperature", "windspeed"}),
       mode="standard"
   )

This is particularly useful for weather features where forecast values might occasionally exceed historical ranges.

Scaling
^^^^^^^

The ``Scaler`` normalizes feature distributions for models sensitive to feature magnitude:

.. code-block:: python

   from openstef_models.transforms.general import Scaler
   from openstef_core.feature_selection import Exclude
   
   scaler = Scaler(
       selection=Exclude({"load"}),  # Don't scale the target
       method="standard"
   )

Standard scaling (zero mean, unit variance) is typically used. Tree-based models are invariant to feature scaling, but linear models benefit significantly.

Sample Weighting
^^^^^^^^^^^^^^^^

The ``SampleWeighter`` assigns importance weights to training samples, allowing models to focus on recent data or specific conditions:

.. code-block:: python

   from openstef_models.transforms.general import SampleWeighter
   from openstef_core.sample_weighting import SampleWeightConfig
   
   sample_weights = SampleWeighter(
       target_column="load",
       config=SampleWeightConfig(
           method="exponential",
           weight_exponent=1.0
       )
   )

This is useful for emphasizing recent patterns in non-stationary energy systems.

Building Feature Pipelines
---------------------------

OpenSTEF's transform system allows you to compose feature engineering pipelines by chaining transformations. A typical pipeline for energy forecasting might look like:

.. code-block:: python

   from openstef_models.transforms.energy_domain import (
       WindPowerFeatureAdder,
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.general import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       Clipper,
       Scaler,
   )
   from openstef_core.feature_selection import Include, Exclude
   from datetime import timedelta
   
   # Define feature engineering pipeline
   feature_pipeline = [
       # Weather-based features
       WindPowerFeatureAdder(windspeed_reference_column="windspeed"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temp"
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=(52.1326, 5.2913),
           radiation_column="radiation"
       ),
       
       # Temporal features
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=(52.1326, 5.2913)),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code="NL"),
       
       # Load pattern features
       RollingAggregatesAdder(
           feature="load",
           aggregation_functions=["mean", "std"],
           horizons=[timedelta(hours=24), timedelta(hours=168)]
       ),
       
       # Preprocessing
       Clipper(selection=Include({"temp", "windspeed"}), mode="standard"),
       Scaler(selection=Exclude({"load"}), method="standard"),
   ]
   
   # Apply pipeline
   transformed_data = dataset
   for transform in feature_pipeline:
       transformed_data = transform.fit(transformed_data).transform(transformed_data)

What Makes Good Features
-------------------------

Effective features for energy forecasting share several characteristics:

**Physical relevance**: Features should encode known physical relationships. Temperature affects heating and cooling demand; solar radiation drives PV generation. Domain knowledge is essential.

**Temporal alignment**: Features must be available at prediction time. Don't use future information or features that won't be available in production.

**Appropriate granularity**: Match feature resolution to forecast horizon. For 15-minute ahead forecasts, minute-level weather updates matter; for day-ahead forecasts, hourly averages suffice.

**Minimal redundancy**: Highly correlated features provide little additional information. Feature importance analysis helps identify redundant features.

**Stability**: Features should be robust to data quality issues. Derived features that amplify noise or missing data can harm model performance.

Feature Importance Analysis
----------------------------

After training a model, examine which features contribute most to predictions. OpenSTEF forecasters with the ``ExplainableForecaster`` mixin provide feature importance:

.. code-block:: python

   # After training a forecaster
   importance_df = forecaster.feature_importances()
   print(importance_df)
   
   # Visualize feature importance
   fig = forecaster.plot_feature_importances()
   fig.show()

This reveals which features drive predictions and helps identify opportunities to simplify models or collect better data for important features.

Custom Features
---------------

For specialized use cases, you can create custom feature transformations by implementing the ``TimeSeriesTransform`` interface:

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig
   
   class CustomFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add custom domain-specific features."""
       
       def fit(self, data: TimeSeriesDataset) -> "CustomFeatureAdder":
           # Compute any statistics needed from training data
           self._mean_value = data.data["load"].mean()
           return self
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Create new features
           new_data = data.data.copy()
           new_data["load_deviation"] = new_data["load"] - self._mean_value
           new_data["load_squared"] = new_data["load"] ** 2
           
           return TimeSeriesDataset(new_data, data.resolution)
       
       @property
       def is_fitted(self) -> bool:
           return hasattr(self, "_mean_value")
       
       def features_added(self) -> list[str]:
           return ["load_deviation", "load_squared"]

Custom transformations integrate seamlessly into OpenSTEF pipelines and maintain the same fit/transform pattern as built-in features.

Next Steps
----------

- See :doc:`forecasting_basics` for how features are used in the forecasting process
- See :doc:`model_selection` to understand how different models utilize features
- Explore the API documentation for detailed transform parameters and options