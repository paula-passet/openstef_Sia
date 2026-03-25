Frequently Asked Questions
==========================


General Questions
-----------------


OpenSTEF is a Python library for machine learning-based energy forecasting, not a complete application. As a library, it provides core functionality for training models and generating predictions, but requires additional components for deployment. Users must integrate OpenSTEF with data fetchers, APIs, schedulers, and user interfaces to create a full forecasting application.


Technical Requirements
----------------------


OpenSTEF requires timeseries data of measured net load or generation from grid assets to create forecasts. The library does not impose specific topology requirements - it works with any grid component that provides load measurements. Short-term forecasting in OpenSTEF context refers to predictions spanning hours to days ahead, with a minimum horizon of 30 minutes to ensure operational relevance for grid operators managing congestion and asset utilization.


Unique Features & Performance
-----------------------------


OpenSTEF distinguishes itself through single-shot multi-horizon forecasting, combining advanced feature engineering with domain-specific energy knowledge. The library provides probabilistic forecasts with confidence intervals using two distinct methods, enabling uncertainty quantification for grid operations. Built as a model-agnostic framework, OpenSTEF incorporates specialized preprocessing for energy data, including solar radiation to PV generation transformations. Performance varies by use case and data quality, with computational requirements scaling based on forecast horizons and model complexity.


Implementation & Deployment
---------------------------


OpenSTEF is a Python library that requires additional components for full application deployment, including data fetchers, APIs, and forecasters. The library primarily uses XGBoost models rather than deep learning approaches, making computational requirements moderate. Deployment costs depend on data volume and forecast frequency, with single-shot multi-horizon forecasting providing efficiency gains. Users can choose between tasks (automated data handling) or pipelines (manual data management) based on their infrastructure needs.


