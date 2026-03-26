Key Forecasting Concepts
========================

Understanding how to interpret and work with OpenSTEF forecasts is essential for making effective decisions in energy systems. This page explains the fundamental concepts behind the library's design through practical examples, helping you understand not just how to use OpenSTEF, but why it works the way it does.

Understanding Forecast Results
------------------------------

OpenSTEF generates probabilistic forecasts rather than single-point predictions. This means each forecast includes not just a predicted value, but also information about the uncertainty of that prediction.

.. code-block:: python

   import pandas as pd
   from openstef_models import ForecastingModel
   
   # A typical forecast result contains multiple columns
   forecast = model.predict(input_data)
   print(forecast.columns)
   # ['forecast', 'stdev', 'quantile_P10', 'quantile_P50', 'quantile_P90']

The ``forecast`` column contains the primary prediction, while quantile columns show different confidence levels. For example, ``quantile_P10`` means there's a 10% chance the actual value will be below this level, while ``quantile_P90`` indicates a 90% confidence threshold.

This probabilistic approach is crucial for energy applications because it enables risk-based decision making. Instead of asking "what will the load be?", you can ask "what's the probability the load will exceed our equipment limits?"

Quantiles and Confidence Intervals
-----------------------------------

OpenSTEF provides confidence estimates through two complementary methods: standard deviation-based intervals and quantile regression.

The standard deviation approach assumes forecast errors follow a normal distribution. This works well for many forecasting scenarios and is computationally efficient:

.. code-block:: python

   # Standard deviation method creates confidence bands
   upper_bound = forecast['forecast'] + 1.96 * forecast['stdev']  # ~95% confidence
   lower_bound = forecast['forecast'] - 1.96 * forecast['stdev']

Quantile regression, available for certain model types, learns the uncertainty patterns directly from training data without assuming a specific error distribution. This often provides more accurate confidence estimates for complex energy patterns:

.. code-block:: python

   # Quantile columns provide direct confidence intervals
   confidence_90 = forecast['quantile_P95'] - forecast['quantile_P05']
   median_forecast = forecast['quantile_P50']

.. note::
   The choice between methods depends on your model type. XGBoost models can use quantile regression, while linear models typically use the standard deviation approach.

Model Choice for Different Use Cases
-------------------------------------

Selecting the right model depends on your specific forecasting requirements and data characteristics. OpenSTEF supports multiple model types, each optimized for different scenarios.

For congestion management, where accuracy during peak periods is critical, XGBoost models often perform best due to their ability to capture complex non-linear patterns:

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   
   # XGBoost excels at peak detection and handles complex interactions
   xgb_model = XGBoostForecaster(config=xgb_config)
   # Particularly effective for low-aggregation, high-variability scenarios

For transport forecasts requiring consistent accuracy across all time periods, linear models may provide more stable and interpretable results:

.. code-block:: python

   from openstef_models.models.forecasting.linear_forecaster import LinearForecaster
   
   # Linear models offer stability and interpretability
   linear_model = LinearForecaster(config=linear_config)
   # Well-suited for medium-aggregated points with clear patterns

The aggregation level of your data significantly influences model choice. Highly aggregated data (like grid losses) shows stronger temporal patterns where simpler models often suffice, while individual customer forecasts require more sophisticated approaches to handle behavioral variability.

Weather Dependency and Key Predictors
--------------------------------------

Weather variables play different roles depending on your forecasting context and aggregation level. OpenSTEF includes built-in feature engineering that transforms raw weather data into energy-relevant predictors.

Solar radiation becomes crucial when forecasting areas with significant photovoltaic generation:

.. code-block:: python

   # OpenSTEF automatically converts solar radiation to PV generation estimates
   # This domain knowledge is built into the feature engineering pipeline
   features = ['temperature', 'irradiance', 'cloud_cover']

Temperature affects both heating and cooling demand, with the relationship varying by season and customer type. Wind speed influences both wind generation and heating demand through wind chill effects.

At highly aggregated levels (like grid losses), weather predictors have diminished impact because system-wide patterns dominate. However, for individual customers or small aggregations, weather dependency remains strong and can be the primary driver of forecast accuracy.

.. note::
   OpenSTEF's feature engineering automatically handles the transformation of weather variables into energy-relevant features, incorporating domain knowledge about solar generation, temperature effects, and seasonal patterns.

Fallback Strategies for Reliability
------------------------------------

Energy forecasting systems must be resilient because forecast availability is critical for operational decisions. OpenSTEF implements multiple fallback strategies to ensure a forecast is always available, even when primary models fail.

The primary fallback strategy uses historical patterns from extreme days:

.. code-block:: python

   from openstef.model.fallback import generate_fallback, FallbackStrategy
   
   # Generate fallback forecast using extreme day strategy
   fallback_forecast = generate_fallback(
       forecast_input=input_data,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Fallback forecasts are clearly marked
   print(fallback_forecast['quality'].unique())
   # ['substituted']

When a fallback forecast is issued, it's always labeled as such in the ``quality`` column. This transparency allows you to track which forecasts were primary model predictions versus fallback estimates, enabling proper decision audit trails.

The extreme day strategy identifies the most extreme historical day (highest peak load) and uses its daily profile as the forecast. While less accurate than model-based predictions, this approach provides a conservative estimate that's often sufficient for operational decisions.

.. warning::
   Always monitor the ``quality`` column in your forecasts. Fallback forecasts should trigger alerts in production systems so operators know when model performance has degraded.

Evaluating Forecast Quality
---------------------------

Understanding forecast quality requires appropriate metrics that align with your business objectives. OpenSTEF provides several evaluation metrics, each suited to different use cases.

For congestion management, relative Mean Absolute Error (rMAE) during peak periods is often most relevant:

.. code-block:: python

   from openstef.metrics.metrics import r_mae_highest
   
   # Evaluate accuracy during peak periods (top 5%)
   peak_accuracy = r_mae_highest(realized_values, forecast_values, percentile=0.95)

For probabilistic forecasts, the Continuous Ranked Probability Score (CRPS) evaluates the entire forecast distribution:

.. code-block:: python

   from openstef_beam.metrics import crps
   
   # CRPS measures quality of probabilistic forecasts
   forecast_quality = crps(y_true, y_pred_quantiles, quantiles)

CRPS is particularly valuable because it rewards forecasts that are both accurate and well-calibrated. A well-calibrated forecast means that when you predict a 20% chance of exceeding a threshold, it actually happens about 20% of the time.

The choice of evaluation metric should align with your operational needs. Transport forecasts might prioritize overall rMAE, while congestion management focuses on peak accuracy, and financial applications might weight errors by market prices.

.. note::
   Different use cases require different evaluation approaches. See the use cases guide for specific recommendations on metrics for congestion management, transport forecasts, and grid losses.