Feature Engineering
===================

Feature engineering is the process of creating predictive variables that help forecasting models capture the patterns in energy demand and generation. In OpenSTEF, features fall into several categories: weather-related features, temporal patterns, lag features that capture recent behavior, and domain-specific features like wind power calculations.

Good features for energy forecasting share common characteristics: they're available at prediction time, they have a clear relationship to energy patterns, and they're stable across different conditions. This page explains how to work with OpenSTEF's feature engineering capabilities and create effective features for your forecasting tasks.

Weather Features
----------------

Weather is a primary driver of energy demand and renewable generation. OpenSTEF provides transforms to derive useful features from basic meteorological data.

Temperature and Atmospheric Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``AtmosphereDerivedFeaturesAdder`` transform calculates derived meteorological features from basic weather data. These features capture non-linear relationships between weather conditions and energy patterns:

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder
   from openstef_core.datasets import VersionedTimeSeriesDataset
   import pandas as pd
   from datetime import timedelta
   
   # Create dataset with basic weather data
   data = pd.DataFrame({
       'load': [100, 110, 105, 115],
       'temperature': [15, 20, 18, 22],
       'humidity': [70, 65, 68, 60]
   }, index=pd.date_range('2025-01-01', periods=4, freq='h'))
   
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data, 
       timedelta(hours=1),
       target_column='load'
   )
   
   # Add derived atmospheric features
   transform = AtmosphereDerivedFeaturesAdder()
   enriched = transform.transform(dataset)
   
   # Check what features were added
   print(transform.features_added())

Solar Radiation Features
^^^^^^^^^^^^^^^^^^^^^^^^^

For solar generation forecasting or capturing solar-driven demand patterns, the ``RadiationDerivedFeaturesAdder`` creates features from radiation data. The ``DaylightFeatureAdder`` adds features based on sunrise, sunset, and daylight duration:

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder
   )
   
   # Add daylight-based features
   daylight_transform = DaylightFeatureAdder()
   dataset_with_daylight = daylight_transform.transform(dataset)
   
   # Add radiation-derived features if you have radiation data
   radiation_transform = RadiationDerivedFeaturesAdder()
   dataset_with_radiation = radiation_transform.transform(dataset_with_daylight)

Wind Power Features
^^^^^^^^^^^^^^^^^^^

When forecasting wind generation or systems affected by wind, the ``WindPowerFeatureAdder`` converts wind speed into estimated power output using standard power curve calculations:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   # Assuming your dataset has wind speed data
   wind_transform = WindPowerFeatureAdder()
   dataset_with_wind_power = wind_transform.transform(dataset)

Temporal Features
-----------------

Energy consumption and generation follow strong temporal patterns—daily cycles, weekly patterns, seasonal variations. OpenSTEF automatically handles many temporal features, but understanding them helps you interpret model behavior.

Common temporal features include:

- **Hour of day**: Captures daily load curves (morning ramp-up, evening peaks)
- **Day of week**: Distinguishes weekday vs. weekend patterns
- **Month or day of year**: Captures seasonal variations
- **Holiday indicators**: Special days with different consumption patterns

These features are typically handled automatically by OpenSTEF's forecasting pipeline, but you can add custom temporal features when needed.

Lag Features
------------

Lag features use recent historical values to predict future values. They're particularly powerful for energy forecasting because today's load often resembles yesterday's load, adjusted for weather and other factors.

Creating Lag Features
^^^^^^^^^^^^^^^^^^^^^^

The ``LagsAdder`` transform creates lagged versions of your target variable:

.. code-block:: python

   from openstef_models.transforms.time_domain import VersionedLagsAdder
   from datetime import timedelta
   
   # Create lag features at 1 hour and 24 hours ago
   lag_transform = VersionedLagsAdder(
       feature='load',
       lags=[timedelta(hours=-1), timedelta(hours=-24)]
   )
   
   dataset_with_lags = lag_transform.transform(dataset)
   snapshot = dataset_with_lags.select_version()
   
   # Lag features are named systematically
   lag_features = [col for col in snapshot.feature_names if 'lag' in col]
   print(lag_features)  # ['load_lag_-PT1H', 'load_lag_-PT24H']

The naming convention uses ISO 8601 duration format: ``load_lag_-PT1H`` means "load value from 1 hour ago" and ``load_lag_-PT24H`` means "load value from 24 hours ago".

Choosing Effective Lags
^^^^^^^^^^^^^^^^^^^^^^^^

Good lag choices depend on your forecasting horizon and the patterns in your data:

- **Recent lags** (1-3 hours): Capture short-term trends and smooth transitions
- **Daily lags** (24, 48 hours): Capture daily patterns for similar times of day
- **Weekly lags** (168 hours): Capture weekly patterns for similar days of week

For a 24-hour ahead forecast, a lag of 24 hours (T-24) gives you the value from the same time yesterday. This is often highly predictive because energy patterns repeat daily.

.. note::

   Lag features are constrained to your dataset's time range. If your data covers 10:00-13:00 and you add a 2-hour lag, features will only be available from 12:00-13:00, not extending beyond 13:00.

Custom Features
---------------

You can add domain-specific features that capture unique aspects of your forecasting problem. Custom features might include:

- **Price signals**: Day-ahead market prices that influence consumption
- **Operational indicators**: Planned outages, maintenance schedules
- **External events**: Major events that affect local demand patterns
- **Derived ratios**: Combinations of existing features

Adding Custom Features
^^^^^^^^^^^^^^^^^^^^^^

Add custom features to your dataset before applying OpenSTEF transforms:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Start with basic data
   data = pd.DataFrame({
       'load': [100, 110, 105, 115],
       'temperature': [15, 20, 18, 22]
   }, index=pd.date_range('2025-01-01', periods=4, freq='h'))
   
   # Add custom feature: temperature-squared to capture non-linear effects
   data['temp_squared'] = data['temperature'] ** 2
   
   # Add custom feature: is_business_hour indicator
   data['is_business_hour'] = data.index.hour.isin(range(8, 18)).astype(int)
   
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data,
       timedelta(hours=1),
       target_column='load'
   )

Feature Selection and Clipping
-------------------------------

Not all features improve forecast accuracy. OpenSTEF provides tools to manage feature quality.

Clipping Outliers
^^^^^^^^^^^^^^^^^

The ``Clipper`` transform constrains features to observed ranges, preventing extreme values from degrading forecasts:

.. code-block:: python

   from openstef_models.transforms.general import Clipper
   
   # Clip features to observed min/max during training
   clipper = Clipper(mode='minmax')
   clipper.fit(training_dataset)
   
   # Apply same clipping to forecast data
   clipped_forecast_data = clipper.transform(forecast_dataset)

You can also clip to statistical ranges (mean ± N standard deviations):

.. code-block:: python

   # Clip to mean ± 2 standard deviations
   clipper = Clipper(mode='standard', n_std=2.0)
   clipper.fit(training_dataset)

Understanding Feature Importance
---------------------------------

After training a model, examine which features contribute most to predictions. OpenSTEF models that support explainability expose feature importance scores:

.. code-block:: python

   from openstef_models.models import XGBForecastingModel
   
   # Train a model
   model = XGBForecastingModel()
   model.fit(training_dataset)
   
   # Get feature importance scores
   importances = model.feature_importances
   print(importances.head(10))  # Top 10 most important features

Feature importance helps you understand what drives your forecasts and identify opportunities to improve feature engineering. Weather features often dominate for temperature-sensitive loads, while lag features are crucial for capturing recent trends.

For more on model interpretation, see the API documentation for ``ExplainableForecaster``.

Best Practices
--------------

**Start simple**: Begin with basic weather features and a few well-chosen lags. Add complexity only when needed.

**Match forecast horizon**: If forecasting 24 hours ahead, ensure features will be available 24 hours in advance. Weather forecasts are available, but recent lags might not be.

**Validate feature availability**: In production, features must be available at prediction time. A feature that's perfect in backtesting but unavailable in production is useless.

**Monitor feature drift**: Feature distributions can change over time. Clipping and regular model retraining help maintain forecast quality.

**Use domain knowledge**: The best features often come from understanding your specific energy system—local weather patterns, operational constraints, or behavioral factors.

See Also
--------

- :doc:`forecasting_basics` - Understanding short-term energy forecasting
- :doc:`model_selection` - Choosing models that work well with different feature sets
- :doc:`reliability_and_fallback` - Handling missing features in production