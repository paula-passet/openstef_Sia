Frequently Asked Questions
==========================


General Questions
-----------------


OpenSTEF is a machine learning library, not a complete application. It provides Python frameworks for data preprocessing, feature engineering, model training, and forecasting. To deploy as a full application, you need additional components like data fetchers, APIs, and user interfaces.

Short-term forecasting in OpenSTEF means predicting energy loads hours to days ahead. The library generates probabilistic forecasts with uncertainty estimates, incorporating domain-specific knowledge for energy grid applications like congestion management and capacity planning.


Technical Requirements
----------------------


OpenSTEF requires timeseries data of measured net load or generation from grid locations to perform forecasting. The library validates input data completeness using configurable thresholds and minimal table length requirements. Grid topology information helps optimize forecasting accuracy, though OpenSTEF can operate with basic load measurements. Data validation includes checks for flatliners, missing values, and sufficient historical data to train machine learning models effectively.


- Historical load or generation timeseries data (essential)

- Weather data including temperature, wind speed, and solar irradiance (essential for accuracy)

- Grid topology information defining network structure and connections (essential)

- Market price data for enhanced forecasting performance (optional)

- Holiday calendars for improved seasonal modeling (optional)

- Additional external predictors like economic indicators (optional)


OpenSTEF vs Other Frameworks
----------------------------


OpenSTEF incorporates specialized energy domain knowledge through built-in feature engineering that transforms weather data into solar radiation and PV generation estimates. The library delivers probabilistic forecasts using quantile regression, providing uncertainty bands rather than single-point predictions. This energy-specific approach includes automated handling of renewable generation patterns, grid load characteristics, and market price integration, distinguishing it from generic forecasting frameworks that lack domain expertise.


Performance and Quality
-----------------------


OpenSTEF forecast accuracy varies significantly by use case and aggregation level. Congestion management forecasts typically achieve higher accuracy for aggregated substations compared to individual customer predictions, which face greater behavioral variability. The library supports standard evaluation metrics including MAE, RMSE, and MAPE for comprehensive performance assessment.

Computational requirements scale with data volume and model complexity. Basic XGBoost models handle typical grid forecasting workloads efficiently, while ensemble approaches require additional resources. The modular architecture allows users to balance accuracy needs against computational constraints through configurable model selection and preprocessing pipelines.


.. note::

   Forecast accuracy varies significantly based on data quality, aggregation level, and specific use case requirements. Individual customer forecasts are inherently less predictable than aggregated loads due to behavioral variability.


