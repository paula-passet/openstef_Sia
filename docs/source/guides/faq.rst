Frequently Asked Questions
==========================


What is OpenSTEF?
-----------------


OpenSTEF is a Python machine learning library designed for short-term energy forecasting. It is not a ready-to-use application with a graphical interface, but rather a software package that provides the core functionality for building forecasting systems. The library performs machine learning operations to predict energy loads on the electrical grid using single-shot, multi-horizon forecasting methods.


.. note::

   OpenSTEF is a Python library, not a standalone application. To run it as a full application with GUI frontend, you must integrate it with additional components like data fetchers, APIs, and schedulers.


Technical Requirements & Capabilities
-------------------------------------


- Grid topology requirements: OpenSTEF works with any electricity grid structure - no specific topology needed, just timeseries load/generation data

- Short-term forecasting definition: Predicting electrical load hours to days ahead using machine learning on historical consumption patterns

- Data requirements: Timeseries of measured load/generation data, optional weather data and market prices for enhanced accuracy

- Computational costs: Lightweight Python library designed for cloud deployment with automated pipelines - scales based on data volume and model complexity


OpenSTEF distinguishes itself from generic forecasting frameworks through its specialized energy sector focus and proven operational track record. Built by grid operators at Alliander, it incorporates deep domain expertise including energy-specific feature engineering, grid topology awareness, and resilient fallback strategies critical for energy applications. Unlike model-centric solutions, OpenSTEF provides a complete machine learning framework with built-in knowledge of energy patterns, weather correlations, and grid constraints developed through real-world deployment experience.


Performance & Implementation
----------------------------


OpenSTEF forecast accuracy varies significantly based on aggregation level, data availability, and use case requirements. Highly aggregated forecasts typically achieve better accuracy than individual customer predictions, which can be unpredictable due to behavioral variability. Performance depends on factors including historical data quality, weather data availability, feature engineering, and the specific forecasting horizon. Grid operators should expect different accuracy ranges for congestion management versus load balancing applications, with peak load period accuracy being critical for operational decisions.


- Minimal hardware requirements: 4GB RAM, 2 CPU cores for small-scale deployments with basic forecasting models

- Docker-compose deployments suitable for research and experimentation with low infrastructure overhead

- Enterprise integration requires scalable infrastructure to handle multiple aggregation levels from individual customers to substation forecasts

- Memory usage scales with model complexity and training data size - XGBoost models typically require 1-8GB depending on feature count

- CPU-intensive operations during model training and hyperparameter optimization - consider multi-core systems for faster execution

- Production deployments benefit from containerized environments with horizontal scaling capabilities for handling multiple forecast points

- Peak load forecasting for congestion management requires higher computational resources due to complex feature engineering

- Batch processing recommended for large-scale deployments with hundreds of forecast points to optimize resource utilization


Getting Help & Contributing
---------------------------


For questions not covered in this FAQ, open an issue on the OpenSTEF GitHub repository or join our community discussions in the OpenSTEF Teams channel. Additional support resources and community meeting information are available on our community support page. The comprehensive documentation and contributing guidelines provide further assistance for technical questions and collaboration opportunities.


