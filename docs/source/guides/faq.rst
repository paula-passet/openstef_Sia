Frequently Asked Questions
==========================

This page answers common questions about OpenSTEF that come up at conferences and from new users getting started with the library.

What is OpenSTEF exactly?
--------------------------

OpenSTEF is a **Python machine learning library** for short-term energy forecasting. It's not an application with a user interface - it's a software package that you integrate into your own systems. Think of it like scikit-learn, but specifically designed for energy forecasting with domain-specific features and preprocessing built in.

The library provides complete machine learning pipelines for data preprocessing, feature engineering, model training, forecasting, and evaluation. You can use it to forecast energy loads, congestion, grid losses, and other energy-related time series.

What do you mean by "short-term"?
----------------------------------

Short-term forecasting means predicting energy loads **hours to days ahead**, with a practical maximum of about 7 days. This time horizon is constrained by weather forecast availability - beyond 7 days, weather forecasts lack the 15-minute resolution needed for accurate energy forecasting, and solar/wind patterns become too unpredictable.

OpenSTEF is optimized for this specific time range where operational decisions matter most: congestion management, peak load planning, and grid operations.

Do I need grid topology information?
-------------------------------------

**No, grid topology is not required.** OpenSTEF works with point-based forecasting - it forecasts each grid location independently without needing to know how they're connected.

However, if you have topology information and want to use it, OpenSTEF can be combined with `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for topology-aware forecasting. This approach has been demonstrated in published research, but most users successfully deploy OpenSTEF without any topology data.

What makes OpenSTEF special compared to other forecasting frameworks?
----------------------------------------------------------------------

OpenSTEF's key differentiator is **energy-specific domain knowledge** built into the feature engineering:

- Automatic solar radiation and temperature transformations for PV generation estimation
- Energy-specific lag features and rolling aggregations
- Weather dependency modeling optimized for energy patterns
- Built-in handling of energy data quirks (missing values, seasonal patterns, peak detection)

This domain knowledge allows classical ML models (XGBoost, LightGBM) with smart features to achieve high performance without requiring deep learning or massive datasets.

What accuracy can I expect?
----------------------------

Forecast accuracy depends heavily on your specific use case, data quality, and chosen metrics:

- **Use case matters**: Congestion management cares about peak detection accuracy, not nighttime precision
- **Data quality is critical**: "Garbage in, garbage out" applies strongly to forecasting
- **Metrics vary by application**: RMSE, MAPE, and peak detection rates tell different stories

**Recommendation**: Run the `Alliander 2021 benchmark <https://github.com/alliander-opensource/energy-forecasting-benchmark>`_ with your own data to see realistic performance metrics and evaluation plots for your specific situation.

How expensive is OpenSTEF to run?
----------------------------------

OpenSTEF is designed to be **computationally lightweight**:

- Uses classical ML models (XGBoost, LightGBM) that train quickly on standard hardware
- No GPU requirements for most use cases
- Can run on modest infrastructure - even scheduled cron jobs work for many deployments
- Single-shot, multi-horizon forecasting reduces computational overhead

The main costs are typically data storage and weather data subscriptions, not compute resources. Many users deploy OpenSTEF successfully on standard cloud instances or on-premises servers.

What about deep learning and neural networks?
----------------------------------------------

OpenSTEF currently focuses on **classical machine learning** models (XGBoost, LightGBM, linear models) combined with sophisticated feature engineering. This approach often outperforms deep learning for energy forecasting because:

- Energy forecasting benefits more from domain-specific features than raw pattern recognition
- Classical models are more interpretable and easier to debug
- Training is faster and requires less data
- Performance is typically comparable or better for short-term horizons

That said, a **deep learning module is in development** for OpenSTEF V4, and **foundation models** (pre-trained models for energy forecasting) are being explored for future releases.

How do I get started?
----------------------

1. **Install OpenSTEF**: ``pip install openstef``
2. **Try the quickstart**: Follow the quickstart guide to train your first model
3. **Run a tutorial**: Work through the comprehensive tutorials for production-ready examples
4. **Join the community**: Connect with other users on the `OpenSTEF Slack workspace <https://openstef.org>`_

The quickstart guide will have you creating forecasts in just a few lines of code, while the tutorials provide production-ready examples.