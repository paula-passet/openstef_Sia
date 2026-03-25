Frequently Asked Questions
==========================

Common questions from conferences and new users about OpenSTEF, the Python machine learning library for short-term energy forecasting.

What do you mean by "short-term" forecasting?
----------------------------------------------

Short-term forecasting means predicting energy load hours to days ahead. OpenSTEF focuses on forecasting horizons from a few hours up to 2-3 days, which is the critical timeframe for operational grid management decisions like congestion management and transport planning.

This is distinct from long-term forecasting (months to years ahead) used for infrastructure planning, or real-time forecasting (minutes ahead) used for immediate control systems.

Do I need grid topology data to use OpenSTEF?
----------------------------------------------

No, OpenSTEF works with point-based forecasting - you forecast each grid point independently without requiring topology information. You only need historical load measurements and weather data for each location.

However, OpenSTEF can be combined with topology-aware approaches. There's published research on integrating OpenSTEF with power-grid-model for topology-aware forecasting, but this is optional and not required for basic operation.

What makes OpenSTEF special compared to other forecasting frameworks?
----------------------------------------------------------------------

OpenSTEF's key differentiators are:

- **Domain knowledge embedded**: Built-in feature engineering specific to energy forecasting, such as converting solar radiation and temperature data into PV generation estimates
- **Probabilistic forecasts**: Generates uncertainty bands, not just point predictions, which is crucial for risk management in grid operations
- **Complete pipeline**: Includes data validation, feature engineering, model training, forecasting, and evaluation - not just the model
- **Production-tested**: Currently running 10,000+ forecasts daily at Alliander with multiple fallback strategies for reliability

The combination of classical ML models (XGBoost, LightGBM) with energy-specific smart features often outperforms more complex approaches.

What accuracy can I expect from OpenSTEF forecasts?
----------------------------------------------------

Accuracy depends heavily on your use case and data quality. The best approach is to test OpenSTEF with your own benchmark dataset and evaluate metrics relevant to your specific application.

Different use cases have different accuracy requirements:
- Congestion management focuses on accuracy near peak periods
- Transport forecasts need balanced accuracy across all time periods  
- Grid loss forecasting optimizes for cost-weighted error minimization

OpenSTEF is currently used operationally by Alliander for thousands of daily forecasts, demonstrating production-grade reliability.

How expensive is OpenSTEF to run computationally?
--------------------------------------------------

OpenSTEF is designed to be computationally efficient. It primarily uses classical machine learning models (XGBoost, LightGBM, linear models) rather than deep learning, which keeps computational requirements modest.

The library can run on standard hardware and doesn't require specialized GPU infrastructure. Training and forecasting tasks can be scheduled efficiently, and the modular design allows you to scale components independently based on your needs.

What about deep learning models?
--------------------------------

OpenSTEF currently focuses on classical ML approaches (XGBoost, LightGBM, linear models) combined with domain-specific feature engineering. This approach often achieves excellent performance while remaining computationally efficient and interpretable.

A deep learning module is in development for future releases, but the current classical ML approach with smart energy-specific features has proven highly effective in production environments.

The framework is model-agnostic, so you can integrate custom deep learning models if needed for your specific use case.

Is OpenSTEF an application I can deploy?
-----------------------------------------

No, OpenSTEF is a Python library, not a deployable application. You integrate it into your own systems and workflows.

To use OpenSTEF in production, you'll need to build additional components around it, such as:
- Data fetchers to retrieve weather and load data
- Schedulers to run training and forecasting tasks
- APIs to serve forecast results
- Databases to store inputs and outputs

See our :doc:`../guides/how_to_guides` for examples of setting up simple deployments with cron jobs or orchestration tools like Dagster.

Can OpenSTEF work outside the Netherlands?
-------------------------------------------

Yes, OpenSTEF V4 is designed to be more generalizable beyond the Netherlands and Alliander's specific use cases. The library includes configurable components for:
- Holiday calendars for different countries
- Different data formats and availability scenarios  
- Flexible feature engineering for various energy markets

While originally developed for Dutch grid operations, the core forecasting methodology applies to any electricity grid with appropriate data inputs.