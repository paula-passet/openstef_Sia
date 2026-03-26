Frequently Asked Questions
==========================

Common questions from conferences and new users about OpenSTEF, the Python machine learning library for short-term energy forecasting.

What does "short-term" mean?
----------------------------

Short-term forecasting means predicting energy load hours to days ahead. OpenSTEF focuses on horizons from 15 minutes up to approximately 48 hours, which is the critical timeframe for operational grid management and congestion prevention.

This differs from:

- **Ultra-short-term**: seconds to minutes (real-time control)
- **Medium-term**: weeks to months (maintenance planning)
- **Long-term**: years (infrastructure investment)

Do I need grid topology data?
------------------------------

No, OpenSTEF works without detailed grid topology. The library operates on a point-based approach, forecasting each measurement location independently. You only need:

- Historical load/generation measurements at your grid points
- Weather data for the forecast locations
- Optional: additional predictors like energy prices

However, OpenSTEF can be combined with topology-aware tools like `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for more advanced use cases. Research has shown this combination can improve accuracy for certain applications.

What makes OpenSTEF special?
-----------------------------

OpenSTEF combines several unique characteristics that set it apart from generic forecasting frameworks:

**Energy-specific domain knowledge**: Built-in feature engineering transforms weather data into energy-relevant predictors (solar radiation → PV generation estimates, temperature → heating/cooling demand).

**Probabilistic forecasts**: Generates uncertainty bands, not just point predictions. This is crucial for grid operators who need to understand forecast confidence.

**Complete ML pipeline**: Handles data validation, preprocessing, feature engineering, model training, forecasting, and evaluation in one integrated framework.

**Operational reliability**: Multiple fallback strategies ensure forecasts are always available, with clear labeling when fallbacks are used.

**Model-agnostic**: Works with any scikit-learn compatible model, allowing you to choose the best approach for your data.

What accuracy can I expect?
----------------------------

Forecast accuracy depends heavily on your specific use case and data quality. Typical performance ranges:

- **High-quality substations**: 5-15% MAPE for day-ahead forecasts
- **Volatile renewable sources**: 15-30% MAPE depending on weather predictability
- **Aggregated regional forecasts**: Often better than individual point forecasts

Key factors affecting accuracy:

- Data completeness and quality
- Weather dependency of your load
- Seasonal patterns and trends
- Forecast horizon (shorter = more accurate)

The library includes comprehensive evaluation metrics (MAPE, MAE, CRPS, peak detection scores) to assess performance for your specific application.

How expensive is OpenSTEF to run?
----------------------------------

OpenSTEF is designed to be computationally efficient:

**System requirements**:

- Python 3.12+ on 64-bit systems
- Minimal hardware: standard laptop/server
- Memory: depends on data size, typically modest requirements

**Computational cost**:

- Training: minutes to hours depending on data size and model complexity
- Forecasting: seconds to minutes for operational predictions
- Primarily uses classical ML models (XGBoost, LightGBM) which are much faster than deep learning

**Deployment options**:

- Simple cron jobs for basic setups
- Container-based deployment for production
- Cloud-native with auto-scaling capabilities

The library's modular design lets you install only needed components, keeping resource usage minimal.

What about deep learning models?
---------------------------------

OpenSTEF currently focuses on classical machine learning approaches (XGBoost, LightGBM, linear models) combined with smart feature engineering. This approach often outperforms deep learning for energy forecasting because:

- **Tabular data**: Energy forecasting typically involves structured time series, where tree-based models excel
- **Limited training data**: Classical ML works better with smaller datasets
- **Interpretability**: Grid operators need to understand forecast drivers
- **Computational efficiency**: Much faster training and inference

However, deep learning capabilities are under development for future releases, particularly for:

- Complex multi-variate relationships
- Image-based weather data integration
- Large-scale multi-location forecasting

The model-agnostic design means you can already integrate custom deep learning models if needed.

Can I use OpenSTEF for my specific application?
------------------------------------------------

OpenSTEF supports many energy forecasting use cases:

- **Grid congestion management**: Predict peak loads to prevent overloading
- **Renewable integration**: Forecast solar/wind generation
- **EV charging planning**: Estimate charging demand
- **District heating**: Predict thermal demand
- **Energy trading**: Support market participation decisions

See our :doc:`use_cases` guide for detailed examples of different applications and when to use each approach.

The library's flexibility allows adaptation to most short-term energy forecasting needs. If you're unsure whether OpenSTEF fits your use case, check the tutorials or reach out to the community.

How do I get started?
----------------------

1. **Install**: ``pip install openstef`` for core functionality
2. **Quick start**: Follow the :doc:`../getting_started/quickstart` for your first forecast in minutes
3. **Learn more**: Work through the :doc:`../getting_started/tutorials` for comprehensive examples
4. **Get help**: Join our community Slack or GitHub discussions

The modular design means you can start simple and add complexity as needed.