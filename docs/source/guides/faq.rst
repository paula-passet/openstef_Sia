Frequently Asked Questions
==========================


General Questions
-----------------


OpenSTEF is a Python machine learning library designed for short-term energy forecasting, not a complete standalone application. The library provides all components for the machine learning pipeline required to generate forecasts, including data preparation, feature engineering, model training, and prediction capabilities with confidence estimates.


- Short-term forecasting predicts energy loads hours to days ahead using machine learning on historical data and weather forecasts

- Grid topology is not required - OpenSTEF works with individual measurement points and their associated data

- Required data includes historical load measurements, weather data (temperature, wind, solar radiation), and optionally additional features like holidays or tariffs

- OpenSTEF is a Python library that requires integration with data sources, databases, and scheduling systems to function as a complete application

- The library performs single-shot, multi-horizon forecasting meaning one model run produces predictions for multiple time steps ahead

- Confidence estimates are provided with forecasts using two available methods to quantify prediction uncertainty


Technical Requirements and Data
-------------------------------


OpenSTEF requires energy load data as the primary input, along with weather data and other relevant features. The library accepts standard tabular data formats and does not impose specific grid topology requirements - it works with any energy system where historical load data is available. Minimum data needs include at least several months of historical energy consumption data with corresponding timestamps, though more data generally improves forecast accuracy.


- Computational requirements scale with data volume and forecast horizon length - larger datasets and longer horizons require more processing power

- Memory usage depends on feature engineering complexity and model type - XGBoost models typically require 2-4GB RAM for standard forecasting tasks

- Training time varies from minutes for simple models to hours for complex ensemble models with extensive feature engineering

- Forecasting is computationally lightweight - generating predictions typically takes seconds to minutes depending on horizon length

- Horizontal scaling possible through parallel processing of multiple prediction jobs across different locations or time periods

- Database performance impacts overall system speed - optimize queries and indexing for time-series data retrieval

- GPU acceleration not required but can improve training speed for large datasets with gradient boosting models


What Makes OpenSTEF Special
---------------------------


OpenSTEF differentiates itself through energy-specific feature engineering that transforms weather data into PV generation estimates and incorporates domain knowledge for grid forecasting. Unlike generic forecasting tools, it provides probabilistic forecasts with quantile-based confidence intervals, enabling uncertainty-aware decision making. The library's operational focus delivers single-shot, multi-horizon predictions optimized for real-world energy grid management rather than academic research.


- Built-in fallback strategies ensure reliable forecasts even when primary models fail or data quality degrades

- Energy split decomposition automatically separates total load into components like solar generation and base consumption

- Industry validation through real-world deployment at major European grid operators like Alliander

- Single-shot multi-horizon forecasting generates predictions for multiple time steps simultaneously

- Probabilistic forecasts with confidence intervals provide uncertainty estimates alongside point predictions

- Domain-specific feature engineering includes solar radiation to PV generation conversion and weather impact modeling


Accuracy and Performance
------------------------


OpenSTEF forecast accuracy varies significantly based on data quality, prediction horizon, and system characteristics. Short-term forecasts (1-6 hours ahead) typically achieve higher accuracy than longer horizons. Performance depends on factors including weather data availability, historical load patterns, seasonal variations, and the complexity of the forecasted system. The library provides confidence estimates and uncertainty bands alongside point forecasts to help users understand prediction reliability.


.. note::

   Forecast accuracy varies significantly based on input data quality, specific use case requirements, and local grid conditions. OpenSTEF provides confidence estimates and probabilistic forecasts to help quantify uncertainty, but results depend heavily on available weather data, historical load patterns, and regional characteristics.


Machine Learning and Deep Learning
----------------------------------


OpenSTEF currently focuses on XGBoost as its primary machine learning algorithm for energy load forecasting. This gradient boosting approach was selected for its proven effectiveness in time series forecasting, robust handling of mixed data types, and reliable performance across diverse energy grid scenarios. The library's architecture supports XGBoost quantile models, enabling probabilistic forecasts with uncertainty quantification essential for energy sector applications.


- OpenSTEF currently focuses on traditional machine learning algorithms like XGBoost for energy forecasting

- Deep learning models are not currently implemented in the core OpenSTEF library

- Traditional ML approaches often perform well for energy forecasting due to their interpretability and efficiency

- Deep learning may be beneficial for complex multi-modal data or very large datasets with non-linear patterns

- Future deep learning support would depend on community contributions and demonstrated performance improvements

- Users can extend OpenSTEF pipelines to integrate custom deep learning models if needed


Getting Help and Next Steps
---------------------------


For technical questions about implementing OpenSTEF in your forecasting pipeline, consult the API documentation and tutorials. Join our GitHub Discussions for community support and to share use cases with other developers. Report bugs or request features through GitHub Issues with detailed reproduction steps.


- New users: Start with the :doc:`../tutorials/index` for hands-on learning

- Developers: Check :doc:`../reference/index` for detailed API documentation

- Advanced users: Explore :doc:`../how-to/index` for specific implementation patterns

- Contributors: Visit :doc:`../development/index` for development guidelines

- Troubleshooting: See :doc:`../how-to/troubleshooting` for common issues

- Examples: Browse :doc:`../examples/index` for real-world use cases


