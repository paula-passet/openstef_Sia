OpenSTEF Use Cases
==================


Overview
--------


OpenSTEF is a flexible forecasting library designed to solve diverse time series prediction problems across multiple domains. The library supports various use cases from congestion management and energy trading to demand response and grid optimization, each with distinct accuracy requirements and aggregation levels. Whether forecasting individual customer consumption or highly aggregated substation loads, OpenSTEF provides modular components that adapt to different business contexts and technical constraints.


- Energy demand forecasting for grid operators and utilities with varying aggregation levels from individual customers to substations

- Congestion management predictions focusing on peak load periods for transmission and distribution network planning

- Renewable energy generation forecasting for solar, wind, and other variable energy sources

- Load balancing and grid stability forecasting to optimize energy distribution and prevent outages

- Market price forecasting for energy trading and procurement optimization

- Capacity planning forecasts for long-term infrastructure investment decisions

- Real-time operational forecasting for immediate grid management and control systems


Grid Infrastructure Forecasting
-------------------------------


OpenSTEF enables grid operators to predict network congestion by forecasting load at substations and individual customer connections. Congestion forecasts help identify when electrical infrastructure approaches capacity limits, allowing operators to take preventive measures before outages occur.

Free space estimation calculates available capacity on grid components by comparing forecasted demand against maximum ratings. For example, a 10 MVA transformer with 8 MVA predicted load shows 2 MVA of remaining capacity for new connections or load growth.

Grid loss forecasts predict energy losses during transmission and distribution, typically ranging from 2-8% of total throughput. These forecasts support operational planning and regulatory reporting by estimating losses at different voltage levels across the network infrastructure.


.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.pipeline.train_model import train_model_pipeline
   import pandas as pd

   # Load grid load data with datetime index
   load_data = pd.read_csv('substation_load.csv', index_col='datetime', parse_dates=True)

   # Apply feature engineering for grid forecasting
   features_data = apply_features(
       data=load_data,
       pj={'id': 'substation_001', 'type': 'demand'},
       horizon_minutes=60
   )

   # Configure model for congestion management
   model = XGBQuantileOpenstfRegressor(
       quantiles=[0.1, 0.5, 0.9],
       max_depth=8,
       n_estimators=200
   )

   # Train forecasting model
   trained_model = train_model_pipeline(
       pj={'id': 'substation_001', 'type': 'demand'},
       model=model,
       input_data=features_data,
       mlflow_tracking_uri=None
   )


Advanced Grid Management
------------------------


OpenSTEF enables sophisticated MV route congestion management by combining topology-aware forecasting with the power-grid-model (PGM) library. This integration allows grid operators to predict congestion points across medium-voltage networks while accounting for actual grid topology and electrical constraints. Transport forecasts complement this approach by providing demand predictions for electric vehicle charging infrastructure and other transportation-related loads. The combination enables proactive congestion management through accurate peak moment forecasting and targeted demand response interventions before grid limits are exceeded.


.. [DIAGRAM: MV grid topology integration with OpenSTEF forecasting workflow]


Beyond Electrical Grids
-----------------------


OpenSTEF's forecasting capabilities extend beyond electrical grids to district heating networks, where accurate demand predictions optimize heat generation and distribution. The library's flexible architecture supports diverse infrastructure applications including water distribution systems, gas networks, and transportation demand forecasting. By adapting the core forecasting models and preprocessing pipelines, organizations can leverage OpenSTEF for any time-series infrastructure challenge requiring load prediction and capacity planning.


.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline
   from openstef.data_classes import ModelSpecificationDataClass
   import pandas as pd

   # Configure district heating load forecasting
   model_specs = ModelSpecificationDataClass(
       id=1001,
       name="district_heating_main_line",
       model="xgb_quantile",
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=60,  # Hourly resolution
       train_components=["load", "weather", "holiday"],
       hyper_params={
           "subsample": 0.8,
           "max_depth": 8,
           "learning_rate": 0.1,
           "gamma": 0.1,
           "colsample_bytree": 0.8
       }
   )

   # Create pipeline for thermal load forecasting
   pipeline = create_forecast_pipeline(
       model_specs=model_specs,
       model_type=XGBQuantileOpenstfRegressor
   )

   # Input data with thermal-specific features
   input_data = pd.DataFrame({
       'load': [150.2, 142.8, 138.5],  # MW thermal load
       'T_ambient': [2.1, 1.8, 0.9],   # Outdoor temperature
       'wind_speed': [4.2, 3.8, 5.1],
       'radiation': [0, 0, 0],          # Night hours
       'holiday': [0, 0, 0]
   })

   # Generate district heating demand forecast
   forecast = pipeline.predict(input_data)


Choosing the Right Use Case
---------------------------


Selecting the appropriate use case depends on three critical factors: data availability, forecasting horizon, and business requirements. Short-term forecasting (hours to days ahead) requires high-frequency historical data and weather forecasts, making it suitable for operational decisions like congestion management. Medium-term forecasting needs less granular data but benefits from seasonal patterns for capacity planning. Consider your business context: grid operators may prioritize peak load prediction for equipment protection, while energy traders focus on price forecasting accuracy. The OpenSTEF library's model-agnostic framework supports various regressors from simple linear models to advanced XGBoost implementations, allowing you to match model complexity to data quality and computational constraints.


- Short-term forecasting (hours to days): Requires high-frequency historical data, weather forecasts, and calendar features. Achieves 5-15% MAPE with moderate complexity using LGBM or XGBoost regressors

- Medium-term forecasting (weeks to months): Needs seasonal patterns, economic indicators, and weather statistics. Typically 10-25% MAPE with higher complexity due to uncertainty propagation

- Congestion management: Demands grid topology data, customer profiles, and real-time measurements. Achieves 8-20% MAPE but requires complex feature engineering for equipment limits

- Basecase forecasting: Uses minimal features like historical load and basic weather. Simple implementation with 15-30% MAPE using linear or ARIMA models

- Component forecasting: Requires detailed asset data, maintenance schedules, and operational parameters. High complexity with 10-40% MAPE depending on component type


