OpenSTEF Use Cases
==================


Overview of OpenSTEF Use Cases
------------------------------


OpenSTEF is a comprehensive forecasting library designed to support diverse energy system applications. The library enables organizations to build robust forecasting solutions across multiple domains, from grid congestion management to renewable energy integration. Its modular architecture supports various aggregation levels, from individual customer predictions to large-scale substation forecasting, accommodating the unique accuracy requirements and optimization targets of different energy forecasting scenarios.


.. [DIAGRAM: Overview diagram showing different OpenSTEF use cases and their relationships to grid components]


Grid Infrastructure Forecasting
-------------------------------


OpenSTEF enables grid operators to forecast congestion by predicting peak load periods at substations and medium-voltage infrastructure. These forecasts help estimate available grid capacity and free space for new connections or increased demand. The library supports highly variable aggregation levels, from individual customer predictions to substation-wide forecasts, allowing operators to identify potential bottlenecks before they occur. Grid loss forecasts complement congestion management by predicting energy losses across transmission and distribution networks, enabling more accurate capacity planning and operational efficiency improvements.


.. code-block:: python

   from openstef.model import OpenstfRegressor
   from openstef.data_classes import PredictionJobDataClass
   from openstef.pipeline import create_forecast_pipeline

   # Configure congestion forecast for substation monitoring
   job_config = PredictionJobDataClass(
       id=1001,
       name="substation_congestion_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       train_components=["load", "weather", "apx"],
       horizon_minutes=2880,  # 48 hours ahead
       feature_names=["T-1d", "T-7d", "temp", "humidity", "windspeed"]
   )

   # Initialize model with grid-specific parameters
   model = OpenstfRegressor(
       model_type="xgb",
       quantiles=[0.1, 0.5, 0.9],
       feature_importance=True
   )

   # Create pipeline for congestion forecasting
   pipeline = create_forecast_pipeline(
       job_config=job_config,
       model=model,
       validation_split=0.2
   )

   # Train model on historical load data
   pipeline.train(train_data)
   forecast = pipeline.predict(horizon_hours=48)


Transport and Distribution Networks
-----------------------------------


OpenSTEF enables transport and distribution network operators to forecast congestion at medium voltage routes and substations with high accuracy during peak load periods. The library supports forecasting at multiple aggregation levels, from individual customer predictions to substation-wide forecasts, accommodating the variable predictability of behavioral patterns. Integration with Probabilistic Graphical Models (PGM) allows operators to incorporate network topology constraints and dependencies into their forecasting models, enabling more sophisticated congestion management strategies that account for the interconnected nature of electrical distribution systems.


- Peak load period accuracy is critical for congestion management and capacity planning

- Aggregation levels vary significantly from individual customers to substation-wide forecasts

- Medium voltage substation (MSR) forecasting requires handling behavioral variability

- Individual customer predictions face high unpredictability due to usage patterns

- Grid operator requirements demand precise forecasting near capacity limits

- Substation-level forecasting supports infrastructure investment decisions

- Real-time forecasting capabilities enable dynamic load management

- Historical load patterns must account for transport network growth


District Heating Systems
------------------------


OpenSTEF library enables thermal energy forecasting for district heating networks, supporting demand prediction across residential and commercial zones. The library's modular architecture accommodates varying aggregation levels from individual buildings to entire heating districts. Forecasting applications include peak load prediction for system optimization, thermal storage management, and supply-demand balancing. OpenSTEF's flexible configuration mechanisms adapt to different heating system characteristics, seasonal patterns, and regional climate variations, making it suitable for diverse thermal energy infrastructure deployments.


.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.pipeline.train_model import train_model_pipeline
   import pandas as pd

   # Configure thermal demand forecasting with weather dependencies
   config = {
       'model': 'xgb_quantile',
       'quantiles': [0.1, 0.5, 0.9],
       'feature_modules': [
           'weather',
           'holiday',
           'temporal'
       ],
       'weather_features': [
           'temp',
           'windspeed',
           'radiation',
           'humidity'
       ],
       'lag_features': [1, 2, 7, 14],
       'horizon_minutes': 1440
   }

   # Load thermal demand data with weather
   thermal_data = pd.read_csv('thermal_demand.csv', parse_dates=['datetime'])
   weather_data = pd.read_csv('weather_data.csv', parse_dates=['datetime'])

   # Merge datasets
   data = thermal_data.merge(weather_data, on='datetime')

   # Apply feature engineering for thermal forecasting
   features_data = apply_features(
       data,
       feature_names=config['weather_features'] + ['load'],
       horizon_minutes=config['horizon_minutes']
   )

   # Train thermal demand model
   model = train_model_pipeline(
       features_data,
       model_type=config['model'],
       quantiles=config['quantiles']
   )


Choosing the Right Use Case
---------------------------


Selecting the right use case depends on your forecasting objectives, data characteristics, and accuracy requirements. Consider congestion management if you need high accuracy during peak periods and work with variable aggregation levels from individual customers to substations. Evaluate your data availability scenarios, as OpenSTEF supports diverse formats and structures. Match your deployment scale to the appropriate implementation approach, from research notebooks to enterprise pipeline integration.


.. note::

   Consider your data availability, forecasting horizon, and required accuracy when selecting use cases. Congestion management requires high accuracy near peaks but faces unpredictability at individual customer levels. Energy trading needs different optimization targets than grid operations. Model complexity should match your computational resources and deployment constraints.


