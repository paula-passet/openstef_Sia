OpenSTEF Use Cases
==================


Overview of OpenSTEF Use Cases
------------------------------


OpenSTEF is a flexible forecasting library designed to address diverse energy and grid-related prediction challenges. From congestion management at substations to individual customer load forecasting, the library provides modular components that adapt to varying accuracy requirements and aggregation levels. Common patterns across use cases include handling behavioral variability, optimizing for peak periods, and supporting different temporal horizons. The library's extensible architecture enables custom model integration while maintaining consistent preprocessing and evaluation workflows across different forecasting applications.


.. [DIAGRAM: Overview diagram showing different OpenSTEF use cases and their relationships to grid operations]


Grid Operations Use Cases
-------------------------


OpenSTEF enables grid operators to forecast congestion by predicting peak load periods at substations and individual customer levels, supporting proactive capacity management. Free space estimation calculates available grid capacity by comparing forecasted demand against infrastructure limits, enabling optimal asset utilization. Grid loss forecasts predict energy dissipation across transmission networks, helping operators minimize operational costs and improve efficiency through targeted interventions at high-loss locations.


.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline
   from openstef.data_classes import ModelSpecificationDataClass
   import pandas as pd

   # Configure congestion forecasting model for substation
   model_specs = ModelSpecificationDataClass(
       id=1001,
       name="substation_congestion_forecast",
       model_type="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=15,
       train_components=["load", "weather", "apx"],
       hyper_params={
           "n_estimators": 100,
           "max_depth": 6,
           "learning_rate": 0.1,
           "subsample": 0.8
       }
   )

   # Initialize regressor for peak load accuracy
   regressor = XGBQuantileOpenstfRegressor(
       quantiles=model_specs.quantiles,
       **model_specs.hyper_params
   )

   # Create pipeline with grid-specific features
   pipeline = create_forecast_pipeline(
       model_specs=model_specs,
       regressor=regressor,
       feature_names=["T-1h", "T-7d", "windspeed_100m", "radiation_horizontal"]
   )

   # Train on historical substation load data
   train_data = pd.read_csv("substation_load_history.csv", index_col=0, parse_dates=True)
   pipeline.train(train_data)

   # Generate congestion forecast
   forecast = pipeline.predict(horizon_hours=48)


Transport and Infrastructure Forecasting
----------------------------------------


OpenSTEF's modular forecasting framework extends beyond electrical grid applications to transport and infrastructure domains. The library's flexible architecture supports transport demand forecasting for public transit systems, ride-sharing networks, and freight logistics by adapting its time-series models to passenger flow patterns and vehicle utilization data. Similarly, district heating operators can leverage OpenSTEF for thermal load prediction, using the same core algorithms to forecast heat demand across residential and commercial networks. The framework's generalized domain logic and customizable data preprocessing enable seamless adaptation to diverse infrastructure forecasting challenges while maintaining the same robust modeling capabilities developed for energy systems.


- Transport networks benefit from OpenSTEF's ability to handle highly variable aggregation levels, from individual vehicle charging stations to entire fleet operations

- District heating systems leverage the library's flexible data format support to accommodate diverse sensor configurations and measurement intervals

- Infrastructure forecasting requires robust handling of behavioral variability, which OpenSTEF addresses through its modular preprocessing and validation components

- Peak load accuracy is critical for transport applications, supported by OpenSTEF's configurable optimization targets and custom metric development

- Scalability from small pilot projects to enterprise deployments enables gradual adoption across transport and infrastructure organizations

- Integration flexibility allows transport operators to embed forecasting into existing fleet management and infrastructure monitoring systems


Advanced Grid Management
------------------------


OpenSTEF enables sophisticated MV route congestion management by integrating with Power Grid Model (PGM) for topology-aware forecasting. This combination allows distribution system operators to predict congestion points with enhanced accuracy by incorporating real-time grid topology information. The PGM integration provides detailed electrical network modeling capabilities, enabling OpenSTEF to account for power flow constraints, voltage levels, and network impedances when generating forecasts. This topology-aware approach significantly improves prediction accuracy for critical grid management decisions, supporting proactive demand response and preventing overload conditions through precise identification of peak demand moments across specific network segments.


.. [DIAGRAM: Architecture diagram showing OpenSTEF integration with Power Grid Model for topology-aware forecasting]


Choosing the Right Use Case
---------------------------


Selecting the right OpenSTEF use case depends on three key factors: your forecasting accuracy requirements, available data characteristics, and operational deployment context. Consider whether you need peak-period accuracy for congestion management, broad coverage for energy trading, or high-frequency predictions for real-time operations.

Evaluate your data availability scenario - OpenSTEF 4.0 supports diverse data formats and structures, from highly aggregated grid points to individual customer measurements. The library's flexible architecture accommodates varying data quality and frequency constraints across different operational environments.

Match your deployment needs with OpenSTEF's target scenarios: research environments benefit from low-code notebook components, small-scale deployments can leverage Docker-compose examples, while enterprise integration requires pipeline APIs and custom component development capabilities for existing infrastructure.


.. note::

   OpenSTEF is a forecasting library that requires integration work, not a ready-to-use application. You'll need to build your own data pipelines, model training workflows, and prediction systems around the core components. See the reference implementation examples for guidance on production deployments.


