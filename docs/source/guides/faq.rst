Frequently Asked Questions
==========================

This page answers common questions from new users and conference attendees about OpenSTEF, the Python library for short-term energy forecasting.

What do you mean by "short-term" forecasting?
----------------------------------------------

Short-term forecasting in OpenSTEF means predicting energy load hours to days ahead - typically from 15 minutes up to 47 hours into the future. This is different from long-term planning (months to years) or real-time control (seconds to minutes).

The time horizon depends on your use case:

- **Congestion management**: 2-47 hours ahead to identify peak moments
- **Grid operations**: 15 minutes to 24 hours for operational decisions  
- **Market participation**: Day-ahead and intraday forecasting

.. code-block:: python

   # Example: Train models for multiple horizons
   training_horizons = [0.25, 1.0, 24.0, 47.0]  # 15 min, 1h, 24h, 47h
   forecast, model, train_data, validation_data, test_data = openstef.pipeline.train_model(
       input_data=data,
       training_horizons=training_horizons
   )

Do I need grid topology data?
-----------------------------

No, OpenSTEF works without grid topology. It forecasts each grid point independently based on historical load patterns and weather data.

However, you can combine OpenSTEF with topology-aware approaches:

- Use OpenSTEF forecasts as input to power flow calculations
- Combine with `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for network analysis
- Apply forecasts to specific use cases like MV route congestion management

This point-based approach makes OpenSTEF practical for most grid operators who may not have detailed topology models readily available.

What makes OpenSTEF special compared to other forecasting frameworks?
----------------------------------------------------------------------

OpenSTEF is specifically designed for energy forecasting with several unique characteristics:

**Domain-specific features:**

- Built-in energy feature engineering (solar radiation → PV generation estimates)
- Weather dependency modeling for renewable generation
- Energy-specific data validation and preprocessing

**Probabilistic forecasting:**

- Generates uncertainty bands, not just point predictions
- Multiple quantile levels (P10, P30, P50, P70, P90)
- Critical for operational decisions where uncertainty matters

**Production-ready reliability:**

- Multiple fallback strategies ensure forecasts are always available
- Fallback forecasts are clearly labeled for decision traceability
- Designed for 24/7 operational environments

**Complete pipeline:**

- Data preprocessing, feature engineering, training, forecasting, and evaluation
- Model-agnostic (works with XGBoost, LightGBM, linear models, etc.)
- Scikit-learn compatible interface

What accuracy can I expect?
---------------------------

Forecast accuracy depends heavily on your data quality, use case, and local conditions. OpenSTEF provides comprehensive metrics to evaluate performance:

.. code-block:: python

   from openstef.metrics import rmse, mae, r_mae
   
   # Calculate common accuracy metrics
   rmse_score = rmse(realized_values, forecast_values)
   mae_score = mae(realized_values, forecast_values)
   relative_mae = r_mae(realized_values, forecast_values)

Typical performance varies by:

- **Data availability**: More historical data generally improves accuracy
- **Weather dependency**: Solar/wind-heavy areas may have higher uncertainty
- **Aggregation level**: Substation-level forecasts often more accurate than individual connections
- **Forecast horizon**: Shorter horizons typically more accurate than longer ones

For detailed evaluation, see the `Alliander 2021 Energy Forecasting Benchmark <https://github.com/alliander-opensource/energy-forecasting-benchmark>`_ dataset.

How expensive is OpenSTEF to run?
---------------------------------

OpenSTEF is designed to be computationally efficient:

**Training costs:**
- Classical ML models (XGBoost, LightGBM) train quickly on standard hardware
- Most models train in minutes, not hours
- Can run on modest cloud instances or on-premises servers

**Inference costs:**
- Generating forecasts is very fast (seconds)
- Minimal computational requirements for operational forecasting
- Scales well for hundreds of grid points

**Deployment options:**
- Simple cron job deployment for small installations
- Container-based deployment for larger operations
- Cloud-native with auto-scaling capabilities

The library itself is open source with no licensing costs. Main expenses are infrastructure and data (weather data subscriptions, if needed).

What about deep learning and neural networks?
----------------------------------------------

OpenSTEF currently focuses on classical machine learning models (XGBoost, LightGBM, linear models) combined with sophisticated feature engineering. This approach delivers excellent results for most energy forecasting use cases.

**Why classical ML works well:**
- Energy data often has strong seasonal and weather patterns that tree-based models capture effectively
- Domain-specific feature engineering (built into OpenSTEF) provides the "intelligence"
- Faster training and inference than deep learning
- More interpretable for operational decisions

**Deep learning development:**
- Deep learning module is in development for future releases
- Will be optional - classical models remain the default
- Targeted at specific use cases where deep learning provides clear benefits

For most users, the current classical ML approach provides the best balance of accuracy, speed, and reliability.

How do I get started?
---------------------

1. **Quick start**: Follow the :doc:`../getting_started/quickstart` guide for your first forecast in minutes
2. **Learn by example**: Work through the :doc:`../getting_started/tutorials` for comprehensive examples
3. **Find your use case**: Check :doc:`use_cases` to identify which approach fits your needs
4. **Join the community**: Connect with other users on the OpenSTEF Slack workspace

The fastest way to evaluate OpenSTEF is to try it with your own data using the quickstart guide.