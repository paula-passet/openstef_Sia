OpenSTEF Use Cases
==================


Overview of OpenSTEF Use Cases
------------------------------


OpenSTEF is a flexible forecasting library designed to address diverse energy and infrastructure prediction challenges. The library supports various forecasting applications, from congestion management and substation load predictions to individual customer behavior forecasting. Its modular architecture enables users to adapt the library to different accuracy requirements, aggregation levels, and optimization targets across multiple domains beyond traditional energy forecasting scenarios.


.. [DIAGRAM: Use case overview diagram showing different application domains and their relationships]


Grid Management Use Cases
-------------------------


OpenSTEF enables grid operators to forecast congestion at substations and individual customer levels, providing critical insights for capacity planning and peak load management. Free space estimation helps operators determine available grid capacity before infrastructure limits are reached, preventing costly overloads. Grid loss forecasts optimize energy distribution efficiency by predicting transmission losses across network segments. These forecasting capabilities support proactive grid management, reduce operational costs, and ensure reliable power delivery to end customers.


.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.feature_applicator import FeatureApplicator
   from openstef.pipeline import create_forecast_pipeline

   # Configuration for substation congestion forecasting
   config = {
       "model": {
           "type": "xgb_quantile",
           "params": {
               "n_estimators": 100,
               "max_depth": 6,
               "learning_rate": 0.1,
               "subsample": 0.8
           }
       },
       "features": {
           "lag_features": [1, 2, 7, 14],
           "weather_features": ["temperature", "windspeed", "radiation"],
           "calendar_features": ["hour_of_day", "day_of_week", "is_weekend"]
       },
       "forecast": {
           "horizon_hours": 48,
           "resolution_minutes": 15,
           "quantiles": [0.1, 0.5, 0.9]
       },
       "validation": {
           "cv_folds": 5,
           "test_fraction": 0.2
       }
   }

   # Initialize pipeline for grid congestion forecasting
   pipeline = create_forecast_pipeline(
       model_type="xgb_quantile",
       feature_names=config["features"],
       forecast_horizon=config["forecast"]["horizon_hours"]
   )


Transport and Distribution Use Cases
------------------------------------


OpenSTEF supports transport and distribution forecasting for medium-voltage (MV) route congestion management using Probabilistic Graphical Models (PGM). The library enables grid operators to forecast load at highly variable aggregation levels, from individual substations to entire distribution networks. PGM integration allows modeling of topological dependencies between network components, improving accuracy during peak load periods when congestion risks are highest.


- Accurate peak load forecasting for substation capacity planning and grid congestion prevention

- Support for variable aggregation levels from individual customers to medium-voltage substations

- Flexible data input handling to accommodate diverse transport network monitoring systems

- Modular architecture enabling integration with existing grid management and SCADA systems

- Type-safe APIs for reliable real-time forecasting in critical infrastructure applications

- Extensible model framework supporting custom transport-specific forecasting algorithms

- Performance optimization for high-frequency data processing in distribution networks

- Configurable holiday calendars and regional parameters for international transport operators


District Heating Forecasting
----------------------------


District heating systems present unique forecasting challenges compared to electrical demand prediction. Thermal energy demand exhibits stronger temperature dependencies and longer response times due to building thermal inertia. Unlike electrical loads, district heating demand shows pronounced seasonal variations and requires consideration of heat storage capacity in the distribution network. OpenSTEF's flexible architecture accommodates these thermal-specific characteristics through customizable feature engineering and model configurations tailored for thermal energy systems.


.. code-block:: python

   from openstef.model.regressors import XGBOpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd

   # Configure thermal demand forecasting job
   thermal_job = PredictionJob(
       id=101,
       name="district_heating_demand",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       train_components=["load", "weather", "holiday"]
   )

   # Setup weather-dependent features for thermal systems
   weather_features = [
       "temp",           # Outdoor temperature (primary driver)
       "humidity",       # Affects perceived temperature
       "windspeed",      # Wind chill factor
       "radiation",      # Solar heating contribution
       "temp_mean_24h",  # Temperature moving average
       "temp_min_24h"    # Daily minimum temperature
   ]

   # Create thermal demand forecast pipeline
   pipeline = create_forecast_pipeline(
       pj=thermal_job,
       input_data=thermal_data,
       weather_data=weather_data,
       model_type=XGBOpenstfRegressor
   )

   # Execute forecast with thermal-specific parameters
   forecast = pipeline.predict(
       horizon_hours=48,
       weather_features=weather_features,
       seasonal_components=True
   )


Choosing the Right Use Case
---------------------------


Selecting the appropriate use case depends on three key factors: data availability, forecast horizon, and business requirements. For congestion management with highly variable aggregation levels, consider data granularity from individual customers to substations. Research applications benefit from flexible APIs and low-code implementations, while enterprise deployments require robust pipeline integration. Match your forecasting accuracy needs to available data quality - individual customer predictions face behavioral variability challenges, whereas aggregated forecasts typically achieve higher reliability.


.. note::

   OpenSTEF is a flexible forecasting library designed for extensibility beyond these common patterns. The modular architecture supports custom models, transforms, and metrics without modifying core code, enabling adaptation to diverse forecasting domains and specific business requirements.


