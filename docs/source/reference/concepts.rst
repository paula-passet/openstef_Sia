Key Forecasting Concepts
========================

This page explains the fundamental concepts behind OpenSTEF's forecasting approach through practical examples. Understanding these concepts helps you make better decisions about model selection, interpret results correctly, and build reliable forecasting systems.

Understanding Forecast Results
------------------------------

When OpenSTEF generates a forecast, it returns more than just a single predicted value. Each forecast includes uncertainty estimates that tell you how confident the model is in its predictions.

.. code-block:: python

   # A typical forecast DataFrame contains multiple columns
   forecast_df.head()
   #                      forecast    stdev    quantile_0.1    quantile_0.5    quantile_0.9    quality
   # 2024-01-01 12:00:00     150.2     12.5           135.8           150.2           165.1    good
   # 2024-01-01 12:15:00     148.7     11.8           134.1           148.7           163.8    good

The ``forecast`` column contains the most likely prediction (typically the 50th percentile). The ``stdev`` column provides a measure of uncertainty, while quantile columns give you specific confidence intervals. The ``quality`` column indicates whether this is a normal prediction or a fallback value.

Quantiles and Confidence Intervals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides two methods for estimating forecast uncertainty, each suited to different situations:

**Standard Deviation Method**: Uses a single standard deviation value and assumes normally distributed errors. This works well for most operational forecasting where you need quick uncertainty estimates.

**Quantile Regression**: Trains separate models to predict specific quantiles (10%, 30%, 50%, 70%, 90%). This provides more accurate confidence intervals, especially for extreme values, but requires more computational resources.

.. code-block:: python

   # Configure quantile forecasting
   pj = PredictionJobDataClass(
       id=123,
       model='xgb',
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],  # Enable quantile regression
       forecast_type="demand",
       horizon_minutes=15,
       resolution_minutes=15
   )

The choice between methods depends on your use case. For congestion management where you need to detect extreme peaks accurately, quantile regression performs better. For general load forecasting where computational speed matters, the standard deviation method is often sufficient.

Model Selection for Different Use Cases
----------------------------------------

OpenSTEF supports multiple model types, each with distinct strengths and appropriate use cases.

XGBoost Models
^^^^^^^^^^^^^^

XGBoost excels at learning complex relationships between weather, time patterns, and energy consumption. It handles non-linear relationships well and typically provides the most accurate forecasts for normal operating conditions.

.. code-block:: python

   # XGBoost configuration for general forecasting
   pj = PredictionJobDataClass(
       model='xgb',
       forecast_type="demand"
   )

Use XGBoost when you have sufficient historical data (at least several months) and need accurate forecasts for typical conditions. It's the default choice for most energy forecasting applications.

Linear Quantile Regression
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linear models are simpler but can outperform XGBoost in specific situations, particularly for predicting extreme peaks that weren't present in training data.

.. code-block:: python

   # Linear quantile model for peak detection
   pj = PredictionJobDataClass(
       model='linear_quantile',
       quantiles=[0.10, 0.50, 0.90],
       forecast_type="demand"
   )

Choose linear quantile regression when:
- You need to detect rare extreme events
- Training data is limited (less than 3 months)
- Model interpretability is crucial
- Computational resources are constrained

ARIMA Models
^^^^^^^^^^^^

ARIMA models focus purely on time series patterns without external features like weather. They're useful for short-term forecasts when weather data is unavailable or unreliable.

.. code-block:: python

   # ARIMA for time-series-only forecasting
   pj = PredictionJobDataClass(
       model='arima',
       order=(1, 1, 1),  # ARIMA parameters
       forecast_type="demand"
   )

Use ARIMA when weather features are not available or when you need a simple baseline model for comparison.

Important Predictors and Weather Dependency
--------------------------------------------

Understanding which features drive your forecasts helps you interpret results and identify potential issues.

Weather Features
^^^^^^^^^^^^^^^^

OpenSTEF automatically generates weather-derived features that capture the relationship between meteorological conditions and energy consumption:

.. code-block:: python

   # Weather features are calculated from latitude/longitude
   pj = PredictionJobDataClass(
       lat=52.0,  # Used for solar calculations
       lon=5.0,   # Used for solar calculations
       forecast_type="demand"
   )

Key weather predictors include:
- **Temperature**: Drives heating and cooling demand
- **Solar irradiance**: Affects both solar generation and cooling loads
- **Wind speed**: Important for wind generation and heating demand
- **Humidity**: Influences cooling system efficiency

The library calculates derived features like direct normal irradiance and global tilted irradiance based on your location coordinates. These derived features often have stronger predictive power than raw weather measurements.

Temporal Features
^^^^^^^^^^^^^^^^^

Time-based patterns capture regular consumption cycles:
- **Hour of day**: Daily consumption patterns
- **Day of week**: Weekday vs. weekend differences  
- **Month/season**: Seasonal heating and cooling patterns
- **Holidays**: Special day adjustments

Feature Importance Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides tools to understand which features matter most for your specific use case:

.. code-block:: python

   from openstef_models.explainability import FeatureImportancePlotter
   
   # After training a model, analyze feature importance
   plotter = FeatureImportancePlotter()
   fig = plotter.plot(importance_scores)

This helps you identify whether your model relies heavily on weather (indicating weather-dependent load) or primarily on time patterns (indicating more predictable, schedule-driven consumption).

Fallback Strategies for Reliability
------------------------------------

Real-world forecasting systems must handle situations where normal prediction fails. OpenSTEF provides fallback mechanisms to ensure you always get a forecast, even when data is missing or models fail.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^^

The primary fallback strategy uses historical data from the most extreme day in your dataset:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast when normal prediction fails
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )

This approach ensures conservative estimates during system failures. The forecast quality column will show "substituted" to indicate fallback usage.

When Fallbacks Activate
^^^^^^^^^^^^^^^^^^^^^^^^

Fallback forecasts are generated when:
- Insufficient training data is available
- Weather data is missing or corrupted  
- Model training fails due to data quality issues
- Real-time prediction encounters errors

Monitoring fallback usage helps you identify systemic issues with your data pipeline or model configuration.

Quality Indicators
^^^^^^^^^^^^^^^^^^

Always check the ``quality`` column in forecast results:
- ``"good"``: Normal model prediction
- ``"substituted"``: Fallback forecast used

High rates of substituted forecasts indicate problems that need investigation, such as data quality issues or inappropriate model configuration.

Practical Interpretation Guidelines
-----------------------------------

When interpreting OpenSTEF forecasts in operational settings:

**For Congestion Management**: Focus on upper quantiles (90th percentile) to ensure adequate capacity margins. Accept some over-prediction to avoid costly congestion events.

**For Energy Trading**: Use the median forecast (50th percentile) for expected values, but consider the full distribution for risk assessment.

**For Maintenance Planning**: Lower quantiles (10th percentile) help identify minimum load periods suitable for maintenance windows.

**For System Reliability**: Monitor both forecast accuracy and fallback usage rates. High fallback rates indicate system vulnerabilities that need attention.

The key to effective forecasting is matching your interpretation approach to your specific operational needs and risk tolerance.