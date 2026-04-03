Feature Engineering for Energy Forecasting
===========================================

Feature engineering is the process of creating predictive variables from raw data. In energy forecasting, good features capture the patterns that drive electricity demand: weather conditions, time-based patterns, and historical load behavior. OpenSTEF provides a comprehensive set of transforms to generate these features automatically.

This page explains what makes effective features for energy forecasting and how to use OpenSTEF's feature engineering capabilities.

Why Features Matter
-------------------

Energy demand follows predictable patterns. Temperature drives heating and cooling loads. Time of day determines when people wake up, commute, and work. Historical load patterns reveal weekly cycles and seasonal trends. The forecasting model's job is to learn these relationships—but only if the features make them visible.

A model trained on raw timestamps and temperature readings will struggle. But add features like "hour of day," "is_weekend," and "temperature deviation from normal," and patterns become learnable. Feature engineering transforms raw data into a representation that exposes the underlying structure.

Weather Features
----------------

Weather is the primary driver of energy demand variability. OpenSTEF provides several weather-related transforms:

**Basic Weather Variables**

Temperature, wind speed, humidity, and radiation are standard inputs. These come from weather forecasts or observations and are typically already present in your dataset.

**Derived Atmospheric Features**

The ``AtmosphereDerivedFeaturesAdder`` transform calculates additional meteorological features from basic weather data. This includes derived quantities that better capture atmospheric conditions affecting energy demand.

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder
   
   # Add derived atmospheric features
   transform = AtmosphereDerivedFeaturesAdder()
   enriched_data = transform.transform(dataset)
   
   # Check what features were added
   print(transform.features_added())

**Radiation Features**

Solar radiation affects both demand (through temperature) and supply (for solar generation forecasts). The ``RadiationDerivedFeaturesAdder`` computes features related to solar radiation patterns.

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
   
   transform = RadiationDerivedFeaturesAdder()
   enriched_data = transform.transform(dataset)

**Daylight Features**

Day length and solar position influence demand patterns, especially for lighting and heating. The ``DaylightFeatureAdder`` extracts these temporal-solar features.

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder
   
   transform = DaylightFeatureAdder()
   enriched_data = transform.transform(dataset)

**Wind Power Features**

For wind generation forecasting, wind speed alone is insufficient. The ``WindPowerFeatureAdder`` converts wind speed to estimated power output using a power curve relationship.

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   transform = WindPowerFeatureAdder()
   enriched_data = transform.transform(dataset)

Time-Based Features
-------------------

Energy demand has strong temporal patterns: daily cycles, weekly rhythms, seasonal variations, and holiday effects. OpenSTEF's time-domain transforms capture these patterns.

Time features are typically added automatically by forecasting pipelines, but you can also apply them manually when building custom workflows. These include cyclic encodings of hour, day of week, and day of year, as well as binary indicators for weekends and holidays.

Lag Features
------------

Lag features are shifted copies of the target variable (load). They capture autocorrelation—the tendency of energy demand to be similar to recent past values. A lag of -1 hour means "what was the load 1 hour ago?" A lag of -24 hours captures daily patterns.

OpenSTEF provides the ``LagsAdder`` transform to create these features:

.. code-block:: python

   from openstef_models.transforms.time_domain import LagsAdder
   from datetime import timedelta
   
   # Add 1-hour and 24-hour lag features
   transform = LagsAdder(
       feature='load',
       lags=[timedelta(hours=-1), timedelta(hours=-24)]
   )
   enriched_data = transform.transform(dataset)
   
   # Feature names will be like 'load_lag_-PT1H', 'load_lag_-PT24H'
   print(transform.features_added())

**Important**: Lag features are constrained to the original dataset's time range. If your dataset covers 10:00-13:00 and you add a -2 hour lag, features will only be available from 12:00-13:00 (where the lagged values exist within the dataset).

**Choosing Lags**

Effective lag selection depends on your forecast horizon and data patterns:

- **Short horizons** (0-6 hours): Recent lags (-15min, -1h, -2h) are highly predictive
- **Medium horizons** (6-24 hours): Daily patterns matter (-24h, -25h, -26h)
- **Long horizons** (24-48 hours): Weekly patterns emerge (-168h for same time last week)

Too many lags can cause overfitting. Start with a few strategic lags and evaluate their importance using the model's explainability features.

Custom Features
---------------

Beyond the built-in transforms, you may need domain-specific features. Examples include:

- **Economic indicators**: Industrial production indices for large industrial loads
- **Event data**: Sports events, concerts, or conferences that affect local demand
- **Operational data**: Planned outages, maintenance schedules, or grid constraints
- **Derived features**: Temperature-humidity interactions, degree-days, or custom weather indices

To add custom features, create your own transform by implementing the ``TimeSeriesTransform`` interface:

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig
   
   class CustomFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add custom domain-specific features."""
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add custom features to the dataset."""
           df = data.data.copy()
           
           # Example: Add a temperature-humidity interaction term
           if 'temperature' in df.columns and 'humidity' in df.columns:
               df['temp_humidity_interaction'] = df['temperature'] * df['humidity']
           
           # Return new dataset with added features
           return TimeSeriesDataset(
               data=df,
               target_column=data.target_column,
               sample_interval=data.sample_interval
           )
       
       def features_added(self) -> list[str]:
           """Return list of feature names added by this transform."""
           return ['temp_humidity_interaction']

Then use it like any other transform in your pipeline.

Feature Pipelines
-----------------

In practice, you'll chain multiple transforms together. OpenSTEF's pipeline architecture makes this straightforward—each transform takes a dataset and returns an enriched version:

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder
   )
   from openstef_models.transforms.time_domain import LagsAdder
   from datetime import timedelta
   
   # Build a feature engineering pipeline
   dataset = original_dataset
   
   # Add weather features
   dataset = AtmosphereDerivedFeaturesAdder().transform(dataset)
   dataset = DaylightFeatureAdder().transform(dataset)
   
   # Add lag features
   dataset = LagsAdder(
       feature='load',
       lags=[timedelta(hours=-1), timedelta(hours=-24)]
   ).transform(dataset)
   
   # Now dataset contains all engineered features

Understanding Feature Importance
---------------------------------

After training a model, examine which features actually matter. OpenSTEF models that implement the ``ExplainableForecaster`` interface provide feature importance scores:

.. code-block:: python

   # Train your model
   model.fit(training_data)
   
   # Get feature importances
   importances = model.feature_importances
   print(importances.head(10))  # Top 10 features
   
   # Visualize
   fig = model.plot_feature_importances()
   fig.show()

This feedback loop is essential. If your carefully engineered features rank low in importance, they may not capture the patterns you expected. Conversely, high-ranking features validate your engineering choices and suggest where to focus further refinement.

What Makes Good Features
-------------------------

Effective features for energy forecasting share several characteristics:

**Predictive Power**

The feature should correlate with the target variable in a way the model can learn. Temperature is predictive because demand rises with extreme temperatures. Random noise is not predictive.

**Availability at Forecast Time**

You can't use features that won't be available when making real forecasts. Historical load is available (as lags). Future load is not. Weather forecasts are available. Actual weather observations are not.

**Stability**

Features should have consistent relationships with the target over time. A feature that predicts well for six months then stops working creates unreliable forecasts.

**Minimal Leakage**

Feature leakage occurs when information from the future accidentally enters the training data. For example, using a "daily average temperature" feature calculated over the entire day would leak future information when forecasting morning hours. Always ensure features use only past and present information.

Next Steps
----------

Feature engineering is iterative. Start with OpenSTEF's built-in transforms, train a model, examine feature importances, and refine. For related topics:

- :doc:`forecasting_basics` - Understanding what you're trying to predict
- :doc:`model_selection` - Choosing models that work well with your features
- See the API documentation for complete transform references

Good features make the difference between mediocre and excellent forecasts. Invest time here—it pays off.