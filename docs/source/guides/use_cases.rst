OpenSTEF Use Cases
==================


Overview of OpenSTEF Use Cases
------------------------------


OpenSTEF is a flexible forecasting library designed to address diverse energy and grid-related forecasting challenges. The library supports applications ranging from congestion management and substation forecasting to individual customer predictions and medium-voltage substation monitoring. Each use case presents unique requirements for accuracy targets, data aggregation levels, and model optimization parameters. The modular architecture enables users to configure data preprocessing pipelines, select appropriate forecasting models, and customize performance metrics based on their specific forecasting objectives and available data sources.


.. [DIAGRAM: Use case comparison matrix showing forecasting horizon, data requirements, and typical accuracy for each use case]


Grid Infrastructure Forecasting
-------------------------------


OpenSTEF enables grid operators to predict when substations and other grid components will approach capacity limits through congestion forecasting. The library focuses on accuracy during peak load periods, supporting forecasts from highly aggregated grid points down to individual customer connections. Free space estimation capabilities help operators determine available capacity across different voltage levels, while grid loss forecasts support transformer efficiency planning by predicting energy losses in the distribution network.


.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline
   from openstef.data_classes import ModelSpecificationDataClass

   # Configure congestion forecast model for substation monitoring
   model_specs = ModelSpecificationDataClass(
       id=1001,
       name="substation_congestion_forecast",
       model_type="xgb",
       quantiles=[0.1, 0.5, 0.9],
       feature_names=["load_entsoe", "temp", "windspeed", "radiation"],
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=15,
       train_components=0.9
   )

   # Set up regressor with grid-specific parameters
   regressor = XGBQuantileOpenstfRegressor(
       quantiles=[0.1, 0.5, 0.9],
       max_depth=8,
       n_estimators=200,
       learning_rate=0.1,
       subsample=0.8,
       colsample_bytree=0.8
   )

   # Create pipeline for congestion forecasting
   pipeline = create_forecast_pipeline(
       model_specs=model_specs,
       regressor=regressor,
       split_func="openstef_splitter"
   )

   # Configure congestion thresholds (MW)
   congestion_thresholds = {
       "warning_level": 85.0,  # 85% of capacity
       "critical_level": 95.0,  # 95% of capacity
       "max_capacity": 100.0   # Maximum substation capacity
   }


Transport and Distribution Forecasting
--------------------------------------


OpenSTEF enables transport forecasting for predicting energy flows across grid segments, essential for medium voltage (MV) route congestion management. The library integrates with Power Grid Model (PGM) to provide topology-aware forecasting capabilities, allowing grid operators to anticipate load distribution patterns and potential bottlenecks across interconnected network segments. This approach combines OpenSTEF's probabilistic forecasting with detailed grid topology modeling to optimize asset utilization and prevent congestion before it occurs.


.. code-block:: python

   from openstef import OpenSTEF
   from openstef.data_classes import PredictionJob
   from openstef.feature_engineering.topology import TopologyFeatures
   import pandas as pd

   # Configure transport forecast with MV route topology
   job = PredictionJob(
       id=501,
       name="MV_Route_A12_Transport",
       model="xgb",
       horizon_minutes=2880,  # 48 hours
       resolution_minutes=15,
       feature_modules=["weather", "load", "topology"],
       quantiles=[0.05, 0.1, 0.9, 0.95]
   )

   # Load topology data for MV route
   topology_data = pd.read_csv("mv_route_topology.csv")
   topology_features = TopologyFeatures(
       route_id="A12_MV",
       upstream_stations=["ST_001", "ST_002"],
       downstream_feeders=["FD_A12_01", "FD_A12_02", "FD_A12_03"],
       cable_lengths=[2.5, 1.8, 3.2],  # km
       transformer_capacity=16000  # kVA
   )

   # Initialize forecaster with topology integration
   forecaster = OpenSTEF()
   forecaster.add_topology_features(topology_features)

   # Create transport forecast
   forecast = forecaster.create_forecast(
       job=job,
       start_time="2024-01-15T00:00:00",
       end_time="2024-01-17T00:00:00",
       include_uncertainty=True
   )

   # Route-specific congestion thresholds
   congestion_limits = {
       "normal_capacity": 12800,  # 80% of transformer capacity
       "emergency_capacity": 15200,  # 95% of transformer capacity
       "route_thermal_limit": 14500
   }

   # Apply route constraints to forecast
   constrained_forecast = forecaster.apply_route_constraints(
       forecast,
       congestion_limits
   )


District Heating Applications
-----------------------------


OpenSTEF's forecasting capabilities extend beyond electrical grids to district heating systems, where thermal demand patterns differ significantly from electrical consumption. District heating forecasts exhibit stronger correlations with outdoor temperature and longer seasonal cycles, requiring models that capture thermal inertia and building heat storage effects. Unlike electrical forecasting, thermal demand shows more pronounced weather dependencies and smoother daily patterns due to heating system thermal mass.


.. code-block:: python

   from openstef.model.model import OpenstfRegressor
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd

   # Configure district heating prediction job
   heating_job = PredictionJob(
       id=1001,
       name="district_heating_demand",
       model="xgb",
       quantiles=[0.05, 0.5, 0.95],
       feature_modules=[
           "openstef.feature_engineering.general",
           "openstef.feature_engineering.weather_features"
       ],
       resolution_minutes=60
   )

   # Create sample district heating data with temperature features
   heating_data = pd.DataFrame({
       'datetime': pd.date_range('2023-01-01', periods=8760, freq='H'),
       'load': [850, 920, 780, 650, 580, 620, 890, 950] * 1095,
       'temp': [2.5, 1.8, 4.2, 8.1, 12.3, 15.7, 18.2, 16.4] * 1095,
       'humidity': [85, 78, 82, 75, 68, 72, 79, 81] * 1095,
       'windspeed': [3.2, 4.1, 2.8, 5.5, 6.2, 4.7, 3.9, 4.3] * 1095
   })

   # Apply feature engineering with heating degree days
   feature_applicator = TrainFeatureApplicator(
       horizons=[0.25, 1, 6, 24, 47],
       feature_modules=heating_job.feature_modules
   )

   # Add heating degree day calculations (base temperature 18°C)
   heating_data['hdd_18'] = (18 - heating_data['temp']).clip(lower=0)
   heating_data['cdd_18'] = (heating_data['temp'] - 18).clip(lower=0)

   # Apply features and train model
   features_data = feature_applicator.add_features(heating_data)
   model = OpenstfRegressor(heating_job)
   model.fit(features_data.drop('load', axis=1), features_data['load'])


Choosing the Right Use Case
---------------------------


- Data availability: Minimum dataset completeness threshold and table length requirements vary by model complexity

- Forecasting horizon: Short-term predictions (hours) require different data patterns than long-term forecasts (days/weeks)

- Accuracy requirements: Higher precision needs more historical data and computational resources for model training

- Computational resources: Complex models with extensive feature engineering require more processing power and memory

- Data quality: Flatliner detection and validation thresholds must align with your data characteristics

- Update frequency: Real-time applications need faster model inference compared to batch processing scenarios


.. note::

   As a library, OpenSTEF provides flexible building blocks that can be combined for hybrid forecasting approaches or specialized applications beyond standard use cases. The modular architecture allows custom feature engineering, model selection, and validation workflows tailored to unique requirements.


