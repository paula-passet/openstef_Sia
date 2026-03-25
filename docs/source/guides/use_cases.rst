OpenSTEF Use Cases
==================


Overview
--------


Use cases represent the real-world applications and scenarios where OpenSTEF's forecasting capabilities provide value. Understanding these use cases is crucial for evaluating whether OpenSTEF aligns with your forecasting needs and for selecting the appropriate implementation approach. OpenSTEF originated from congestion management in electrical grids, where accurate load forecasting helps prevent overloads and enables proactive demand response. However, the library has evolved to support a diverse range of applications including transport forecasts, grid loss prediction, district heating optimization, EV charging capacity estimation, and topology-aware forecasting for medium-voltage route congestion. Each use case presents unique requirements for data handling, model configuration, and deployment patterns, making it essential to identify your specific scenario before diving into implementation details.


OpenSTEF is a flexible forecasting library designed to adapt to a wide range of energy and infrastructure forecasting scenarios. Originally developed for electricity grid congestion management, the library has evolved to support diverse use cases including transport forecasts, grid loss predictions, district heating systems, EV charging capacity estimation, and MV route congestion analysis. The modular architecture of OpenSTEF allows organizations to customize and extend the library's capabilities to meet their specific forecasting requirements, whether for research experimentation, small-scale deployments, or large-scale production systems across different geographical regions and energy domains.


.. note::

   OpenSTEF is a machine learning library for time series forecasting, not a complete end-to-end application. While it provides powerful forecasting capabilities and components, users need to integrate it into their own systems for data retrieval, storage, and deployment. The library is designed to be modular and extensible, allowing you to build custom forecasting solutions tailored to your specific requirements and infrastructure.


Grid Congestion Forecasting
---------------------------


Grid congestion occurs when electricity demand approaches or exceeds the capacity of transmission and distribution infrastructure, potentially leading to voltage drops, equipment overload, and service disruptions. For grid operators, accurate congestion forecasting is critical for maintaining system reliability and preventing costly outages. OpenSTEF enables precise predictions of peak load periods across various aggregation levels, from highly aggregated network points to individual customer connections and medium-voltage substations. By forecasting congestion events in advance, grid operators can proactively manage load distribution, schedule maintenance during low-demand periods, and make informed decisions about infrastructure investments and capacity planning.


OpenSTEF approaches congestion forecasting by prioritizing accuracy during peak load periods when grid stress is highest. The library supports highly variable aggregation levels, from very aggregated distribution points down to individual customer forecasts, enabling grid operators to predict congestion at substations, medium-voltage distribution networks (MSRs), and even specific customer connections. This flexible approach recognizes that individual customer forecasts can be particularly challenging due to behavioral variability, while aggregated forecasts benefit from statistical smoothing effects. The modular architecture allows operators to configure forecasting pipelines that focus computational resources on the most critical time periods and grid locations where congestion is most likely to occur.


- Enables proactive maintenance scheduling by predicting when grid components will experience high stress or congestion

- Supports strategic capacity planning by forecasting future load patterns and identifying infrastructure upgrade needs

- Maintains grid stability through accurate peak load predictions that help operators balance supply and demand

- Reduces operational costs by preventing emergency interventions and optimizing resource allocation

- Improves service reliability by anticipating potential bottlenecks before they impact customers


.. code-block:: python

   ```python
   from openstef import OpenSTEF
   from openstef.model import XGBoostQuantileOpenstfRegressor
   from openstef.feature_engineering import ApplyOpenstfFeatures
   import pandas as pd

   # Initialize OpenSTEF for congestion forecasting
   forecaster = OpenSTEF()

   # Configure for grid congestion use case
   config = {
       'model': XGBoostQuantileOpenstfRegressor(),
       'horizon_hours': 48,  # 48-hour forecast horizon
       'resolution_minutes': 15,  # 15-minute resolution
       'quantiles': [0.1, 0.5, 0.9],  # Include uncertainty bounds
       'feature_engineering': ApplyOpenstfFeatures(
           lag_features=True,
           weather_features=True,
           calendar_features=True
       )
   }

   # Load historical load data for a substation
   load_data = pd.read_csv('substation_load_history.csv',
                          parse_dates=['datetime'],
                          index_col='datetime')

   # Load weather forecast data
   weather_data = pd.read_csv('weather_forecast.csv',
                             parse_dates=['datetime'],
                             index_col='datetime')

   # Train the congestion forecasting model
   forecaster.fit(
       load_data=load_data,
       weather_data=weather_data,
       config=config
   )

   # Generate congestion forecast
   forecast = forecaster.predict(
       weather_forecast=weather_data,
       horizon_hours=48
   )

   # Extract peak load predictions (critical for congestion management)
   peak_forecast = forecast.resample('H').max()
   print(f"Peak load forecast: {peak_forecast.head()}")
   ```


.. [DIAGRAM: Grid congestion forecasting workflow showing data inputs, model training, and forecast output]


Grid congestion forecasting typically requires historical load data at 15-minute intervals, weather information including temperature and solar irradiance, and calendar features to capture seasonal and daily patterns. The data requirements vary significantly based on the aggregation level - from highly aggregated substation data to individual customer consumption patterns, which can be particularly challenging due to behavioral variability. Forecast horizons commonly range from short-term operational planning (1-48 hours ahead) to medium-term capacity planning (several days to weeks), with accuracy requirements being most critical during peak load periods when congestion risks are highest. Weather data becomes increasingly important for longer forecast horizons, while recent load patterns and calendar effects drive short-term predictions.


Free Space Estimation
---------------------


Free space in the electrical grid context refers to the available capacity on transmission and distribution networks that can accommodate new connections without exceeding operational limits. This metric is crucial for grid operators and energy companies when evaluating requests for new renewable energy installations, industrial connections, or residential developments. By accurately forecasting available grid capacity, operators can make informed decisions about infrastructure investments, prevent network congestion, and optimize the integration of distributed energy resources. OpenSTEF's machine learning capabilities enable precise estimation of this free space by analyzing historical load patterns, weather dependencies, and grid constraints to predict future capacity availability across different time horizons.


Free space estimation in electrical grids relies fundamentally on accurate load forecasting to determine available capacity. OpenSTEF's forecasting capabilities enable grid operators to predict future electricity demand at specific network points, which serves as the foundation for calculating remaining grid capacity. By forecasting the expected load on transformers, cables, and other grid components, operators can subtract these predicted values from the maximum rated capacity to determine how much additional load the infrastructure can safely accommodate. This relationship is critical because grid capacity is not static - it varies continuously based on current and forecasted demand patterns, making real-time load forecasting essential for dynamic capacity management and safe grid operation.


- Planning new customer connections by forecasting available grid capacity at connection points

- Integrating distributed energy resources such as solar panels and battery storage systems while maintaining grid stability

- Making informed grid expansion and infrastructure investment decisions based on predicted capacity constraints


.. code-block:: python

   ```python
   from openstef.model.regressors import ARIMAOpenstfRegressor, XGBOpenstfRegressor
   from openstef.pipeline import train_model, create_forecast
   from openstef.feature_engineering.apply_features import apply_features
   import pandas as pd

   # Configuration for free space estimation forecasting
   config = {
       "id": 307,
       "name": "Grid_Substation_A_Free_Space",
       "type": "demand",
       "resolution_minutes": 15,
       "forecast_type": "demand",
       "model": "xgb",
       "hyper_params": {
           "subsample": 0.9,
           "max_depth": 7,
           "gamma": 0.1,
           "colsample_bytree": 0.8,
           "learning_rate": 0.1,
           "min_child_weight": 5,
           "objective": "reg:squarederror"
       },
       "feature_names": [
           "T-1d", "T-7d", "T-14d",
           "hour", "weekday", "month",
           "temp", "windspeed_100m", "radiation"
       ]
   }

   # Load historical load and capacity data
   load_data = pd.read_csv('substation_load_history.csv', index_col=0, parse_dates=True)
   capacity_data = pd.read_csv('substation_capacity.csv', index_col=0, parse_dates=True)

   # Calculate free space (available capacity)
   free_space_data = capacity_data['max_capacity'] - load_data['actual_load']
   free_space_data = free_space_data.to_frame('load')

   # Apply feature engineering for free space forecasting
   input_data_with_features = apply_features(
       free_space_data,
       config["feature_names"]
   )

   # Train model for free space estimation
   trained_model = train_model(
       input_data=input_data_with_features,
       model_type=config["model"],
       model_params=config["hyper_params"]
   )

   # Create free space forecast
   forecast = create_forecast(
       trained_model=trained_model,
       input_data=input_data_with_features,
       horizon_minutes=2880  # 48 hours ahead
   )

   print(f"Free space forecast for next 48 hours:")
   print(forecast[['forecast', 'forecast_quality']].head(10))
   ```


.. image:: _static/images/placeholder_example_visualization_of_forecasted_free_space_over_time.png
   :alt: Example visualization of forecasted free space over time
   :align: center


Grid Loss Forecasting
---------------------


Grid losses refer to the electrical energy that is lost during transmission and distribution through the electricity network, occurring as power flows from generation sources to end consumers. These losses are an inevitable consequence of electrical resistance in power lines, transformers, and other grid infrastructure, typically representing 2-10% of total electricity generation depending on the grid's age, design, and operating conditions. For grid operators, accurately forecasting these losses is crucial for maintaining energy efficiency and managing operational costs, as losses must be compensated by purchasing additional energy or adjusting generation schedules. The financial impact is substantial - even a 1% reduction in grid losses can translate to millions of euros in savings annually for large utilities, while improved loss forecasting enables better energy procurement strategies and more accurate billing to customers who ultimately bear these costs through their electricity tariffs.


OpenSTEF models grid losses by treating them as forecasting targets within its machine learning framework, similar to load or generation forecasting. The library applies its comprehensive feature engineering capabilities to capture the complex dependencies that drive transmission and distribution losses, including load patterns, weather conditions, and grid topology effects. Loss patterns are modeled using the same probabilistic approach as other forecasting targets, generating uncertainty bands that help grid operators understand the range of expected losses. The framework's built-in domain knowledge for energy systems enables it to automatically engineer relevant features that capture the non-linear relationships between system load, ambient temperature, and equipment characteristics that influence loss behavior. By leveraging historical loss data alongside external predictors like weather forecasts and load predictions, OpenSTEF can identify temporal patterns and correlations that traditional methods might miss, providing grid operators with accurate loss forecasts essential for optimal grid operation and planning.


- Accurate energy accounting by quantifying losses at different grid levels and time periods

- Optimization of grid efficiency through identification of loss patterns and peak loss periods

- Fair cost allocation by distributing transmission and distribution loss costs based on actual usage patterns

- Improved grid planning by understanding where and when losses occur most significantly

- Enhanced regulatory compliance through precise loss reporting and documentation


.. code-block:: python

   ```python
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.feature_engineering.apply_features import apply_features
   import pandas as pd

   # Load historical grid loss data
   loss_data = pd.read_csv('grid_losses.csv', index_col='datetime', parse_dates=True)

   # Configure prediction job for grid loss forecasting
   pj = {
       'id': 'grid_loss_forecast',
       'name': 'Distribution Grid Loss Forecasting',
       'model': 'xgb_quantile',
       'horizon_minutes': 2880,  # 48 hours ahead
       'resolution_minutes': 15,
       'feature_names': [
           'load_entsoe',  # Total grid load
           'pv_measurement',  # Solar generation
           'wind_measurement',  # Wind generation
           'temperature',  # Weather impact on losses
           'humidity',  # Additional weather factor
           'hour',  # Time-based patterns
           'dayofweek',  # Weekly patterns
           'month'  # Seasonal variations
       ]
   }

   # Apply feature engineering for loss forecasting
   input_data_with_features = apply_features(
       loss_data,
       pj,
       weather_data=weather_df,
       load_data=load_df
   )

   # Train model for grid loss prediction
   model = train_model_pipeline(
       pj=pj,
       input_data=input_data_with_features,
       model_type=XGBQuantileOpenstfRegressor()
   )
   ```


.. [DIAGRAM: Grid loss forecasting showing relationship between load, weather, and losses]


Transport Forecasting
---------------------


Transport forecasting in the context of electrification involves predicting energy demand patterns for electric transportation infrastructure, including electric vehicle charging stations, public transit systems, and fleet electrification networks. As transportation systems transition from fossil fuels to electricity, accurate forecasting becomes critical for grid operators and energy planners to ensure adequate capacity, prevent congestion, and optimize charging infrastructure deployment. OpenSTEF provides the forecasting capabilities needed to model the unique demand characteristics of electrified transport, which often exhibit different temporal patterns compared to traditional energy loads, with potential for rapid load changes during peak commuting hours and varying usage patterns based on route schedules, weather conditions, and user behavior.


Transportation electrification forecasting presents unique challenges that distinguish it from traditional energy forecasting. Mobility patterns create highly variable demand profiles, as electric vehicle charging depends on commuting schedules, travel distances, and driver behavior rather than consistent consumption patterns. Charging behavior adds another layer of complexity, with users exhibiting diverse preferences for charging times, locations, and frequency based on their individual routines and access to charging infrastructure. Seasonal variations further complicate predictions, as temperature affects both battery performance and heating/cooling energy requirements, while holiday periods and vacation seasons dramatically alter typical mobility patterns. These factors combine to create forecasting scenarios where individual customer behavior can be particularly unpredictable, requiring models that can adapt to the dynamic nature of transportation electrification adoption and usage patterns.


- EV charging infrastructure planning and load management - forecasting charging demand patterns to optimize grid capacity and prevent overloading at charging stations

- Public transport electrification - predicting power requirements for electric bus fleets, tram networks, and electric train services to ensure adequate grid infrastructure

- Freight logistics optimization - forecasting energy demands for electric delivery vehicles, warehouse operations, and distribution centers to support sustainable supply chain electrification


.. code-block:: python

   ```python
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline
   from openstef.feature_engineering.apply_features import apply_features

   # Configure transport electrification forecasting
   transport_config = {
       'model': XGBQuantileOpenstfRegressor(),
       'horizon_minutes': 2880,  # 48 hours ahead
       'resolution_minutes': 15,
       'feature_names': [
           'T-1d',  # Temperature lag
           'T-7d',  # Weekly temperature pattern
           'humidity',
           'windspeed_100m',
           'radiation_horizontal',
           'IsWeekDay',
           'Month',
           'Hour'
       ],
       'quantiles': [0.1, 0.5, 0.9],  # Uncertainty bounds for grid planning
       'train_horizons_minutes': [15, 60, 240, 1440],  # Multi-horizon training
   }

   # Create pipeline for transport load forecasting
   pipeline = create_forecast_pipeline(
       pj=transport_config,
       model_type='xgb_quantile'
   )

   # Apply transport-specific feature engineering
   features_df = apply_features(
       data=load_data,
       feature_names=transport_config['feature_names'],
       pj=transport_config
   )

   # Generate forecasts with uncertainty quantiles
   forecast = pipeline.predict(
       input_data=features_df,
       horizon_minutes=transport_config['horizon_minutes']
   )
   ```


.. image:: _static/images/placeholder_example_forecast_showing_transport_load_patterns_with_daily_and_weekly_cycles.png
   :alt: Example forecast showing transport load patterns with daily and weekly cycles
   :align: center


District Heating
----------------


District heating systems distribute thermal energy from centralized sources to multiple buildings through a network of insulated pipes carrying hot water or steam. These systems serve entire neighborhoods, campuses, or city districts, making accurate demand forecasting critical for efficient operation and planning. Thermal energy demand forecasting in district heating presents unique challenges compared to electrical load forecasting, as it must account for weather dependencies, building thermal inertia, and the complex relationship between ambient temperature and heating requirements. OpenSTEF's forecasting capabilities can be applied to predict thermal energy demand at various aggregation levels, from individual buildings to entire district heating networks, enabling operators to optimize heat generation, manage peak loads, and ensure reliable service delivery while minimizing operational costs and environmental impact.


Thermal energy demand forecasting presents unique challenges compared to electrical load forecasting due to fundamental differences in system behavior. Thermal systems exhibit significant thermal inertia, meaning buildings and heating networks retain heat for extended periods, creating a delayed response to changes in weather conditions or heating demand. This inertia smooths out short-term fluctuations but makes the system more dependent on sustained weather patterns rather than instantaneous conditions. Additionally, thermal demand shows heightened sensitivity to specific weather variables, particularly outdoor temperature, wind speed, and solar radiation, with complex interactions between these factors affecting heat loss rates and building energy requirements. Unlike electrical systems where demand can change rapidly, thermal systems require forecasting models that account for these lag effects and the cumulative impact of weather conditions over time, making feature engineering and temporal modeling approaches distinctly different from traditional electrical load forecasting.


- Optimize heat production schedules by accurately predicting thermal energy demand patterns across different time horizons

- Improve thermal storage management through precise demand forecasting, enabling better charge and discharge timing decisions

- Enhance overall system efficiency by balancing heat generation with actual consumption needs, reducing energy waste

- Enable proactive capacity planning for district heating networks based on predicted peak demand periods

- Support grid balancing and load management through integration with broader energy system forecasting


.. code-block:: python

   ```python
   import pandas as pd
   from openstef import OpenSTEF
   from openstef.data_classes import PredictionJobDataClass
   from openstef.feature_engineering import WeatherFeatures

   # Create prediction job for district heating demand
   prediction_job = PredictionJobDataClass(
       id=1001,
       name="district_heating_demand",
       model_type="xgb",
       quantiles=[0.05, 0.5, 0.95],
       resolution_minutes=15,
       forecast_type="demand",
       train_components=1.0
   )

   # Load thermal demand data with datetime index
   demand_data = pd.read_csv("thermal_demand.csv", index_col=0, parse_dates=True)

   # Load weather data including temperature features
   weather_data = pd.read_csv("weather_data.csv", index_col=0, parse_dates=True)

   # Initialize OpenSTEF forecasting system
   forecaster = OpenSTEF()

   # Add temperature-based features for thermal demand
   weather_features = WeatherFeatures()
   enhanced_weather = weather_features.add_temperature_features(
       weather_data,
       features=["temp", "temp_min", "temp_max", "heating_degree_days", "cooling_degree_days"]
   )

   # Combine demand and weather data
   training_data = pd.concat([demand_data, enhanced_weather], axis=1)

   # Train model with temperature dependencies
   model = forecaster.train_model(
       prediction_job=prediction_job,
       input_data=training_data,
       validation_split=0.2
   )

   # Generate thermal demand forecast
   forecast = forecaster.create_forecast(
       prediction_job=prediction_job,
       model=model,
       input_data=training_data
   )
   ```


.. [DIAGRAM: District heating forecasting workflow showing weather data, thermal models, and demand prediction]


MV Route Congestion Management
------------------------------


Medium voltage (MV) route congestion occurs when electrical demand or generation along specific network segments approaches or exceeds the physical capacity of power lines, transformers, or other grid infrastructure. This creates operational challenges for distribution system operators who must prevent equipment overload while maintaining reliable power supply. Traditional congestion management approaches often involve reactive measures such as calling customers in advance to reduce energy consumption or generation through demand response programs with compensation. However, these methods require accurate forecasting of peak demand moments to be effective. The complexity increases significantly when considering the topology-aware nature of electrical networks, where congestion in one segment can cascade effects throughout the connected grid infrastructure, making precise spatial and temporal forecasting critical for proactive grid management.


OpenSTEF integrates with Power Grid Model (PGM) to enable topology-aware forecasting for medium voltage route congestion management. This integration allows the library to understand the physical structure and connectivity of the electrical grid, enabling more accurate predictions of power flows and potential congestion points. By incorporating grid topology information through PGM, OpenSTEF can account for how electrical loads and generation are distributed across the network infrastructure, considering factors such as transformer capacities, line ratings, and network connectivity. This topology awareness is essential for identifying which specific routes or network segments are likely to experience congestion, enabling distribution system operators to take proactive measures such as demand response or grid switching operations before overloads occur.


- Route-specific load and generation forecasting for individual medium voltage network segments

- Integration with power-grid-model for topology-aware predictions that account for network configuration changes

- Support for switching operations analysis to evaluate alternative network configurations

- Peak moment identification to enable proactive congestion management decisions

- Demand response planning capabilities to prevent network overloads through customer engagement


.. code-block:: python

   ```python
   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.preprocessing.preprocessing import prepare_forecast
   from power_grid_model import PowerGridModel
   from power_grid_model.data_types import Dataset

   # Load MV network topology data
   grid_data = Dataset(
       node=[
           {"id": 1, "u_rated": 10500.0},  # MV busbar
           {"id": 2, "u_rated": 10500.0},  # Load connection point
       ],
       line=[
           {"id": 10, "from_node": 1, "to_node": 2, "r1": 0.25, "x1": 0.1, "c1": 0.0}
       ],
       source=[{"id": 100, "node": 1, "status": 1, "u_ref": 1.0}],
       sym_load=[{"id": 200, "node": 2, "status": 1, "p_specified": 1e6, "q_specified": 0.0}]
   )

   # Initialize power grid model for topology analysis
   pgm = PowerGridModel(grid_data)

   # Load historical load data for MV route
   load_data = pd.read_csv('mv_route_load_data.csv', parse_dates=['datetime'])
   load_data = load_data.set_index('datetime')

   # Apply topology-aware feature engineering
   # Include network impedance and thermal capacity constraints
   topology_features = pd.DataFrame({
       'line_thermal_capacity': [150.0] * len(load_data),  # Amperes
       'network_impedance': [0.269] * len(load_data),     # Ohms
       'voltage_level': [10.5] * len(load_data),          # kV
   })

   # Combine load data with topology features
   forecast_data = pd.concat([load_data, topology_features], axis=1)

   # Apply standard OpenSTEF feature engineering
   forecast_data = apply_features(forecast_data, pj={'id': 'mv_route_001'})

   # Prepare data for forecasting with topology constraints
   train_data, validation_data = prepare_forecast(
       forecast_data,
       horizon_minutes=60,
       backtest_months=12
   )

   # Train model with topology-aware features
   model = XGBQuantileOpenstfRegressor()
   model.fit(
       train_data[model.feature_names],
       train_data['load'],
       validation_data[model.feature_names],
       validation_data['load']
   )

   # Generate congestion-aware forecast
   forecast_input = forecast_data.tail(1)
   predicted_load = model.predict(forecast_input[model.feature_names])

   # Check against thermal limits using PGM
   grid_data['sym_load'][0]['p_specified'] = predicted_load[0] * 1000  # Convert to W
   result = pgm.calculate_power_flow(grid_data)

   # Extract line loading percentage
   line_loading = abs(result['line']['i_from'][0]) / topology_features['line_thermal_capacity'].iloc[0]
   congestion_risk = line_loading > 0.8  # 80% threshold

   print(f"Predicted load: {predicted_load[0]:.1f} kW")
   print(f"Line loading: {line_loading:.1%}")
   print(f"Congestion risk: {'HIGH' if congestion_risk else 'LOW'}")
   ```


.. [DIAGRAM: MV network topology with forecasting points and congestion management workflow]


.. note::

   This is an advanced use case that requires integration with the power-grid-model library for topology-aware forecasting. Unlike basic load forecasting, MV route congestion management combines electrical network topology with time series forecasting to predict potential bottlenecks in medium voltage distribution networks. This integration enables more sophisticated grid management but requires additional expertise in both power systems modeling and the power-grid-model library ecosystem.


Choosing the Right Use Case
---------------------------


Selecting the right use case for your OpenSTEF implementation depends on several key factors: your data availability, forecasting requirements, and technical constraints. The OpenSTEF library offers multiple forecasting approaches through its comprehensive model selection framework, including traditional time series models like ARIMA, machine learning regressors such as XGBoost and LightGBM, and advanced techniques like the Domain Adaptation for Zero Shot Learning in Sequence (DAZLS) method for split forecasting scenarios. Consider your forecast horizon needs, whether you require confidence intervals, the complexity of your energy system, and your available computational resources when choosing between single-shot multi-horizon forecasting, component-based forecasting, or basecase forecasting approaches. Each use case is designed to address specific challenges in energy forecasting, from simple load prediction to complex grid management scenarios with multiple interdependent components.


- Data availability and quality: Consider the frequency, completeness, and reliability of your historical load data, weather data, and other relevant features

- Forecast horizon requirements: Determine if you need short-term forecasts (minutes to hours), medium-term (days), or longer horizons, as this affects model selection and accuracy expectations

- Accuracy requirements and tolerance: Define acceptable error margins for your specific application, balancing prediction accuracy with computational resources and model complexity

- Operational context and constraints: Evaluate your deployment environment, real-time processing needs, computational resources, and integration requirements with existing systems

- Confidence estimation needs: Assess whether you require uncertainty quantification alongside point forecasts for risk management and decision-making processes

- Model interpretability requirements: Consider if you need explainable predictions for regulatory compliance or operational transparency versus black-box performance


.. [DIAGRAM: Decision tree for selecting appropriate OpenSTEF use case based on requirements]


In practice, OpenSTEF's modular architecture allows you to combine multiple use cases within a single implementation. For example, you might use the library to create both short-term operational forecasts and longer-term capacity planning forecasts for the same energy system, leveraging different model configurations and feature sets for each horizon. The pipeline components can be orchestrated to run different forecasting workflows simultaneously - perhaps generating 15-minute ahead forecasts for real-time grid operations while also producing day-ahead forecasts for energy trading. Additionally, you can combine forecasting with model monitoring by integrating the performance measurement capabilities to track forecast accuracy across different use cases, ensuring that each application maintains its required performance standards. This flexibility stems from OpenSTEF being a library rather than a rigid application, allowing you to compose the specific combination of models, pipelines, and monitoring tools that best serve your organization's diverse forecasting needs.


Implementation Considerations
-----------------------------


When implementing OpenSTEF across different use cases, several common patterns emerge that can guide your approach. As a Python library, OpenSTEF provides a flexible foundation that can be adapted to various forecasting scenarios through consistent implementation strategies. The core pattern involves combining input data preparation with feature engineering, followed by OpenSTEF's single-shot, multi-horizon forecasting methodology. Most implementations benefit from modular architecture where data fetching, preprocessing, model training, and prediction components are clearly separated. This separation allows for easier maintenance and enables different use cases to share common components while customizing specific aspects like data sources, feature sets, or forecasting horizons. Additionally, leveraging OpenSTEF's built-in confidence estimation methods provides valuable uncertainty quantification across all use cases, helping users understand the reliability of their forecasts regardless of the specific application domain.


- Ensure high-quality input data with proper validation, cleaning, and consistency checks before feeding into OpenSTEF models

- Implement robust feature engineering pipelines that handle data preprocessing, feature selection, and transformation consistently across training and prediction phases

- Establish comprehensive model validation procedures including cross-validation, performance metrics evaluation, and confidence interval assessment to ensure forecast reliability

- Maintain centralized data preprocessing logic to reduce duplication and improve consistency between validation and modeling components

- Design flexible configuration mechanisms to adapt to different data formats, availability scenarios, and domain-specific requirements

- Implement proper test coverage and standardized coding practices to ensure maintainability and reliability of the forecasting pipeline


When implementing OpenSTEF for specific use cases, several key considerations must be addressed to ensure optimal performance and integration. As a Python library, OpenSTEF requires careful attention to data preparation and feature engineering, which should be tailored to your specific domain and data characteristics. The library's single-shot, multi-horizon forecasting capability allows for efficient prediction across multiple time horizons simultaneously, but this requires proper configuration of your input data pipeline and feature selection process. For applications beyond the Netherlands energy grid context, you'll need to customize domain-specific elements such as holiday calendars, regional weather patterns, and local energy consumption behaviors. The confidence estimation methods available in OpenSTEF should be selected based on your specific uncertainty quantification requirements and downstream decision-making processes. Additionally, when deploying OpenSTEF as part of a larger application architecture, consider implementing complementary components such as data fetchers for automated input data collection, data APIs for seamless integration with existing systems, and forecaster services for scheduled model training and prediction tasks. The modular design of OpenSTEF allows for flexible integration patterns, enabling you to adapt the library's capabilities to your specific operational requirements and existing infrastructure constraints.


.. code-block:: python

   ```python
   from openstef.model.regressors import XGBOpenstfRegressor
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd

   # Generic implementation pattern for OpenSTEF use cases
   def implement_forecasting_use_case(
       train_data: pd.DataFrame,
       predict_data: pd.DataFrame,
       prediction_job: PredictionJob,
       model_type: str = "xgb"
   ):
       """
       Generic pattern that can be adapted for different forecasting use cases.

       Args:
           train_data: Historical data with target variable
           predict_data: Recent data for making predictions
           prediction_job: Configuration for the specific use case
           model_type: Type of model to use ("xgb", "linear", etc.)
       """

       # Step 1: Configure model based on use case requirements
       if model_type == "xgb":
           model = XGBOpenstfRegressor()
       else:
           # Add other model types as needed for your use case
           raise ValueError(f"Unsupported model type: {model_type}")

       # Step 2: Apply feature engineering specific to your domain
       feature_applicator = TrainFeatureApplicator(
           horizons=prediction_job.horizons,
           feature_names=prediction_job.feature_modules
       )

       # Step 3: Train the model using OpenSTEF pipeline
       trained_model = train_model_pipeline(
           pj=prediction_job,
           input_data=train_data,
           model=model
       )

       # Step 4: Generate forecasts with confidence intervals
       forecast_data = create_forecast_pipeline(
           pj=prediction_job,
           input_data=predict_data,
           model=trained_model
       )

       return {
           'model': trained_model,
           'forecasts': forecast_data,
           'horizons': prediction_job.horizons
       }

   # Example adaptation for different use cases:
   # - Energy demand forecasting: Use load-specific features and XGB model
   # - Solar generation: Include weather features and adjust horizons
   # - Price forecasting: Add market indicators and use linear model
   # - Custom domain: Modify feature_modules and validation logic
   ```


.. note::

   For detailed implementation steps and practical examples, refer to the tutorials and how-to guides in the documentation. These resources provide step-by-step instructions for setting up data pipelines, configuring forecasting models, and integrating OpenSTEF into your application architecture. The tutorials cover common implementation patterns and best practices for deploying OpenSTEF as part of a complete forecasting system with data fetchers, APIs, and scheduling components.


Next Steps
----------


After exploring the various use cases for OpenSTEF, you should now have a clearer understanding of how this machine learning library can be applied to your specific forecasting needs. Whether you're implementing basic load forecasting, handling complex multi-component predictions, or developing advanced applications with confidence intervals, the key is to start with your data requirements and business objectives. Consider the complexity of your forecasting scenario, the available input data, and your deployment constraints when selecting the most appropriate approach. For hands-on experience, begin with the OpenSTEF-offline-example Jupyter notebooks to experiment with different functionalities, then progress to the OpenSTEF-reference implementation if you need a complete application stack, or integrate the core OpenSTEF library directly into your existing systems for custom implementations.


- Getting Started Tutorial - Complete walkthrough from data loading to forecast creation

- First Use Guide - Step-by-step instructions for loading data, training models, and creating forecasts

- Backtesting Guide - Learn how to validate your models using historical data

- Energy Split Forecasting - Advanced tutorial on domain adaptation techniques

- Custom Target Provider - How to implement custom data sources for your specific use case

- API Reference Documentation - Complete reference for all OpenSTEF classes and functions

- OpenSTEF-offline-example - Jupyter notebooks with practical examples for different use cases

- OpenSTEF-reference - Full stack deployment example with databases and UI components

- Architecture and Methodology Guide - Understanding OpenSTEF's machine learning pipeline and confidence estimation methods


Now that you understand the various use cases for OpenSTEF, we encourage you to dive deeper by experimenting with the quick start guide and tutorials. The OpenSTEF library provides extensive documentation and examples to help you get hands-on experience with energy forecasting. Start with the first use tutorials to learn the fundamentals of loading data, training models, and creating forecasts, then explore the advanced features like backtesting and custom implementations. The OpenSTEF-offline-example repository contains Jupyter Notebooks that demonstrate practical applications you can adapt to your specific use case, making it an ideal playground for experimentation and learning.


