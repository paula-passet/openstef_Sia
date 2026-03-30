Frequently Asked Questions
==========================

This page answers common questions about OpenSTEF from new users and conference attendees. For detailed tutorials, see :doc:`../getting_started/tutorials`. For specific use cases, see :doc:`use_cases`.

General Questions
-----------------

What is OpenSTEF?
^^^^^^^^^^^^^^^^^

OpenSTEF is a Python machine learning library for short-term energy forecasting. It's not an application you install and run—it's a library you integrate into your own systems. You write Python code that uses OpenSTEF's pipelines to train models and generate forecasts for your specific grid locations.

What do you mean by "short-term"?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Short-term means forecasting hours to days ahead. OpenSTEF typically forecasts from 15 minutes up to 47 hours ahead. For example, you might predict load at 13:15 when making a forecast at 13:00 (0.25 hour horizon), or predict tomorrow's peak load (24-47 hour horizon).

The forecast horizon is configurable. Common patterns:

- **Intraday operations**: 0.25 to 24 hours ahead
- **Day-ahead planning**: 24 to 47 hours ahead
- **Backtesting**: Multiple horizons to evaluate model performance across time ranges

Do I need grid topology data?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No, not for most use cases. OpenSTEF forecasts load at specific measurement points using historical load data and weather information. You don't need to know how cables connect or what the network structure looks like.

The exception is advanced MV route congestion management where you want to model power flow through the network. In that case, you can integrate OpenSTEF with power-grid-model to incorporate topology. See :doc:`use_cases` for details on this specific use case.

What data do I need?
^^^^^^^^^^^^^^^^^^^^

At minimum, you need:

- **Historical load measurements**: Timeseries of energy consumption or generation at 15-minute intervals
- **Weather data**: Temperature, wind speed, solar radiation (OpenSTEF can retrieve this automatically for Dutch locations)

Optional data that improves forecasts:

- **Weather forecasts**: For predicting future load
- **Holiday calendars**: To capture demand patterns on special days
- **Additional predictors**: Any other relevant timeseries data

Technical Questions
-------------------

What makes OpenSTEF special compared to other forecasting frameworks?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF is purpose-built for energy grid operations, not a general-purpose forecasting tool adapted for energy. The key differentiators:

**Domain-specific feature engineering**: Built-in features like solar radiation to PV generation conversion, load decomposition (baseload vs. weather-dependent), and holiday effects specific to energy consumption patterns.

**Probabilistic forecasts**: Generates quantile forecasts (P10, P30, P50, P70, P90) that give you uncertainty bands, not just a single prediction. This is critical for congestion management—you need to know "what if the forecast is wrong?"

**Operational focus**: Designed for production use at grid operators. Includes fallback strategies when models fail, handles missing data gracefully, and provides interpretable results for operators making real-time decisions.

**Multiple horizons**: Trains models optimized for different forecast horizons simultaneously, because a model good at predicting 15 minutes ahead isn't necessarily good at predicting 47 hours ahead.

What is the accuracy of OpenSTEF forecasts?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Accuracy varies significantly by use case, location, and forecast horizon. Typical performance:

- **Aggregated substations** (many customers): 2-5% relative MAE for short horizons (< 6 hours)
- **Individual feeders** (fewer customers): 10-20% relative MAE due to higher volatility
- **Solar generation**: Higher errors during sunrise/sunset transitions and cloudy conditions
- **Longer horizons**: Accuracy decreases as you predict further ahead

OpenSTEF includes comprehensive metrics (RMSE, MAE, rMAE, bias, R²) to evaluate your specific forecasts. The library also provides tools to analyze when and why the model is uncertain. See :doc:`../reference/concepts` for interpreting forecast quality.

.. note::
   Forecast accuracy depends heavily on your data quality. Clean, complete historical data with good weather coverage produces better models than sparse or noisy data.

What about deep learning?
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF primarily uses XGBoost (gradient boosting) as its default model because it consistently delivers strong performance for energy forecasting with reasonable computational cost and interpretability.

However, OpenSTEF is model-agnostic. The library supports:

- **XGBoost**: Default choice, excellent for most use cases
- **Linear quantile regression**: Better for extreme peaks not seen in training data
- **Custom models**: You can integrate any scikit-learn compatible model or implement your own

Deep learning models (LSTM, transformers, etc.) can be integrated if you have specific requirements, but in practice, XGBoost often matches or exceeds their performance for short-term energy forecasting while being faster to train and easier to interpret.

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   
   # Use XGBoost (default)
   model_xgb = train_model_pipeline(
       pj=prediction_job,
       input_data=data,
       model="xgb"
   )
   
   # Use linear quantile regression
   model_linear = train_model_pipeline(
       pj=prediction_job,
       input_data=data,
       model="linear_quantile"
   )

How expensive is it to run OpenSTEF?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF is designed to be computationally efficient. Typical resource requirements:

**Training**: A single model trains in minutes on a standard laptop (4 CPU cores, 8GB RAM). Training 100+ models for different grid locations can be done overnight on modest infrastructure.

**Forecasting**: Generating forecasts is very fast—milliseconds to seconds per location. You can easily run thousands of forecasts on a single machine.

**Infrastructure**: Many users run OpenSTEF on:

- Simple cron jobs on a single server
- Lightweight orchestration (Dagster, Airflow) on cloud VMs
- Serverless functions for smaller deployments

You don't need expensive GPU clusters or specialized hardware. The main cost is data storage and weather data subscriptions if you're not using free sources.

Practical Questions
-------------------

Can I use OpenSTEF for my specific situation?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF works for any situation where you have:

- Historical timeseries data of energy consumption or generation
- A need to forecast hours to days ahead
- Access to weather data (or ability to integrate your own predictors)

Common applications include congestion forecasting, capacity planning, grid loss prediction, district heating, and renewable generation forecasting. See :doc:`use_cases` for detailed examples of different applications.

How do I get started?
^^^^^^^^^^^^^^^^^^^^^^

1. Install OpenSTEF: ``pip install openstef``
2. Prepare your data: Historical load and weather in pandas DataFrames
3. Train a model: Use ``train_model_pipeline()`` with your data
4. Generate forecasts: Use ``create_forecast_pipeline()`` with the trained model

See :doc:`../getting_started/quickstart` for a complete minimal example.

What if my forecasts are poor quality?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Common issues and solutions:

**Insufficient training data**: OpenSTEF needs at least several months of data, ideally a full year to capture seasonal patterns.

**Missing weather data**: Temperature and solar radiation are critical predictors. Ensure your weather data covers your location and time period.

**Wrong model type**: Try different models (XGBoost vs. linear) for your specific use case.

**Data quality issues**: Check for gaps, outliers, or incorrect timestamps in your input data.

**Wrong forecast type**: Ensure you're using the correct forecast type (demand, solar, wind) for your data.

The library includes diagnostic tools to identify these issues. See :doc:`../getting_started/tutorials` for examples of evaluating and improving forecast quality.

Where can I get help?
^^^^^^^^^^^^^^^^^^^^^

- **Documentation**: Start with :doc:`../getting_started/quickstart` and :doc:`../getting_started/tutorials`
- **GitHub Issues**: Report bugs or request features at https://github.com/OpenSTEF/openstef
- **Community**: Join discussions on the LFEnergy Slack workspace
- **Examples**: Check the examples directory in the GitHub repository