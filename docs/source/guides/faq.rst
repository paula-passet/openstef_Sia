Frequently Asked Questions
==========================

Common questions from conferences and new users about OpenSTEF, the Python machine learning library for short-term energy forecasting.

What do you mean by "short-term"?
----------------------------------

Short-term forecasting means predicting energy load hours to days ahead. OpenSTEF typically forecasts 15 minutes to 47 hours into the future, making it ideal for operational grid management rather than long-term planning.

.. code-block:: python

   # Example: forecast horizons from 15 minutes to 47 hours
   training_horizons = [0.25, 47.0]  # 0.25 = 15 minutes, 47.0 = 47 hours

This time range is perfect for congestion management - you can identify peak load moments 1-2 days ahead and take preventive action.

Do you need the topology of the grid?
--------------------------------------

No, OpenSTEF works without grid topology. It forecasts each measurement point independently based on historical load data and weather information.

However, you *can* combine OpenSTEF with topology-aware tools like `power-grid-model` for advanced use cases. Research has shown this combination can improve accuracy for certain applications, but it's not required for basic operation.

What makes OpenSTEF special compared to other forecasting frameworks?
----------------------------------------------------------------------

OpenSTEF is purpose-built for energy forecasting with several unique features:

- **Domain knowledge embedded**: Built-in feature engineering that understands energy patterns (e.g., solar radiation automatically converts to PV generation estimates)
- **Probabilistic forecasts**: Provides uncertainty bands, not just point predictions - crucial for risk management in grid operations
- **Fallback strategies**: Always delivers a forecast, even when primary models fail
- **Energy-specific metrics**: Specialized evaluation metrics for peak detection and congestion management

.. code-block:: python

   # OpenSTEF automatically creates energy-relevant features
   # from weather data without manual feature engineering
   forecast = model.predict(data_with_weather)
   # Returns probabilistic forecast with confidence intervals

What is the accuracy of OpenSTEF forecasts?
--------------------------------------------

Accuracy depends heavily on your use case and data quality. Typical performance ranges:

- **High-quality substations**: 5-15% MAPE for day-ahead forecasts
- **Volatile renewable sources**: 15-30% MAPE
- **Peak detection**: Often 70-90% precision/recall for congestion events

The key insight: OpenSTEF focuses on *operational accuracy* - correctly identifying when and where problems will occur, not just minimizing average error.

How expensive is it to run OpenSTEF?
-------------------------------------

OpenSTEF is computationally lightweight. A typical deployment:

- **Training**: Minutes to hours per model on standard hardware
- **Forecasting**: Seconds per prediction
- **Resource requirements**: Runs efficiently on modest cloud instances or on-premises servers

The library uses classical machine learning models (XGBoost, LightGBM) that are much more efficient than deep learning approaches while achieving comparable accuracy for energy forecasting tasks.

What about deep learning?
--------------------------

OpenSTEF currently focuses on classical machine learning models (decision trees, linear regression, gradient boosting) because they:

- Train faster and require less computational resources
- Provide better interpretability for operational decisions  
- Achieve excellent performance when combined with domain-specific feature engineering
- Are more reliable in production environments

A deep learning module is in development for future releases, but classical ML remains the recommended approach for most energy forecasting applications.

Is OpenSTEF just another time series library?
----------------------------------------------

No, OpenSTEF is specifically designed for energy grid operations. Unlike general time series libraries, it includes:

- Pre-built energy domain knowledge
- Specialized metrics for peak detection and congestion management
- Fallback strategies for critical infrastructure reliability
- Integration patterns common in energy sector IT environments

See the :doc:`../guides/use_cases` guide to understand which energy forecasting scenarios OpenSTEF addresses.