Frequently Asked Questions
==========================


What is OpenSTEF?
-----------------


OpenSTEF is a Python machine learning library designed for energy forecasting, not a standalone application or pre-trained model. It provides the building blocks - prediction jobs, tasks, pipelines, and ML components - that developers integrate into their own systems. Users must implement data fetching, storage, and user interfaces separately to create complete forecasting applications.


.. note::

   OpenSTEF is a Python library that provides machine learning components for energy forecasting. Users must build their own implementation around these components, including data fetching, storage, and application logic to create a complete forecasting solution.


Grid Topology and Data Requirements
-----------------------------------


OpenSTEF requires minimal data to generate forecasts - primarily historical load data with timestamps. Topology information is optional and only needed when modeling grid-specific relationships or constraints. The library is designed to work with delayed measurements and weather forecasts, accommodating real-world data availability constraints. Most forecasting tasks can be performed with just time series load data and basic weather features.


- Target column (e.g., energy load measurements) with datetime index

- Historical time series data covering training period

- Weather forecast data (temperature, wind, solar radiation)

- Calendar features (holidays, weekdays, seasons)

- Optional: Sample weights for handling data quality variations

- Optional: Additional predictive features (economic indicators, grid topology)

- Optional: Delayed measurements to handle real-world data availability constraints


Short-term Forecasting Definition
---------------------------------


Short-term forecasting in OpenSTEF covers timeframes from hours up to approximately 7 days maximum. This horizon is optimized for operational planning needs such as grid management, energy trading, and congestion management. Beyond 7 days, weather forecast resolution degrades significantly, making accurate energy predictions impractical for operational decisions.


What Makes OpenSTEF Special?
----------------------------


OpenSTEF incorporates domain-specific optimizations designed for electrical grid operations. The library includes built-in feature engineering that transforms weather data into energy-relevant inputs, such as converting solar radiation into photovoltaic generation estimates. Unlike generic forecasting frameworks, OpenSTEF provides operational tools for real-world grid management, including congestion prediction and capacity planning capabilities that directly support utility decision-making processes.


- Quantile forecasting provides probabilistic predictions with uncertainty bandwidths instead of single-point estimates

- Built-in energy domain knowledge including solar radiation to PV generation feature engineering

- Model-agnostic framework supporting multiple machine learning algorithms with fallback strategies

- Single-shot multi-horizon forecasting capability predicting multiple time steps simultaneously

- Grid-aware features specifically designed for congestion management and transport capacity planning

- Complete end-to-end pipelines from data preprocessing to post-processing evaluation

- Confidence estimation methods with two available approaches for forecast reliability assessment


Performance and Implementation
------------------------------


OpenSTEF forecast accuracy varies significantly by use case and aggregation level. Highly aggregated forecasts typically achieve better accuracy than individual customer predictions, which can be unpredictable due to behavioral variability. The library is optimized for production performance while maintaining computational efficiency across different deployment scales from research notebooks to enterprise systems.


OpenSTEF prioritizes traditional machine learning algorithms over deep learning approaches to balance accuracy with computational efficiency and interpretability. The library focuses on proven techniques like XGBoost that deliver reliable performance across diverse forecasting scenarios while maintaining reasonable resource requirements for production deployments. This approach ensures the library remains accessible for small-scale implementations while supporting enterprise integration needs.


