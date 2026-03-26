Frequently Asked Questions
==========================

Common questions about OpenSTEF from conferences and new users.

What is "short-term" forecasting?
----------------------------------

Short-term forecasting means predicting energy load hours to days ahead, typically from 15 minutes up to 48 hours. This differs from:

- **Ultra-short-term**: seconds to minutes (grid stability)
- **Medium-term**: weeks to months (maintenance planning) 
- **Long-term**: years (infrastructure investment)

OpenSTEF focuses on the operational timeframe where grid operators need to anticipate congestion and take preventive actions.

Do I need grid topology data?
------------------------------

No, OpenSTEF works without detailed grid topology. The library currently forecasts each grid point independently using:

- Historical load measurements
- Weather data (temperature, solar radiation, wind)
- Calendar features (time of day, day of week, holidays)
- Energy market prices (optional)

For topology-aware forecasting, OpenSTEF can be combined with `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for advanced use cases like MV route congestion management. See our use cases guide for examples.

What makes OpenSTEF special?
-----------------------------

OpenSTEF differs from generic forecasting frameworks through:

**Energy-specific features**: Built-in domain knowledge like solar radiation to PV generation conversion, temperature-driven heating/cooling demand, and energy market price integration.

**Probabilistic forecasts**: Not just point predictions, but uncertainty bands that help operators understand forecast confidence and plan accordingly.

**Complete pipeline**: Data validation, feature engineering, model training, forecasting, and evaluation in one integrated library.

**Operational focus**: Designed for production use with fallback strategies, model validation, and performance monitoring.

**Model-agnostic**: Works with any scikit-learn compatible model, from linear regression to XGBoost to custom forecasters.

What accuracy can I expect?
----------------------------

Forecast accuracy depends heavily on your specific use case and data quality. Factors that influence performance:

- **Data completeness**: Missing measurements reduce accuracy
- **Seasonal patterns**: Regular consumption patterns forecast better
- **Weather dependency**: Solar/heating loads are more predictable
- **Forecast horizon**: Accuracy decreases with longer horizons

The best approach is testing with your own data. Use our benchmark dataset from the `Alliander 2021 Energy Forecasting Benchmark <https://github.com/alliander-opensource/short-term-forecasting-benchmark>`_ to compare against established baselines.

How expensive is it to run?
----------------------------

OpenSTEF is designed to be computationally efficient:

**Training**: Most models train in minutes on standard hardware. A typical XGBoost model for one location uses <1GB RAM and trains in 2-5 minutes.

**Forecasting**: Generating forecasts is very fast - hundreds of forecasts per second on a single CPU core.

**Hardware requirements**: 
- Minimum: 4GB RAM, 2 CPU cores
- Recommended: 8GB+ RAM for multiple concurrent forecasts
- No GPU required (though some models can benefit)

At Alliander, we generate 10,000+ forecasts daily on modest cloud infrastructure.

What about deep learning?
--------------------------

OpenSTEF currently focuses on classical machine learning (XGBoost, LightGBM, linear models) combined with smart feature engineering. This approach often outperforms deep learning for energy forecasting because:

- **Limited data**: Energy time series are often too short for deep learning
- **Interpretability**: Classical models are easier to understand and debug
- **Computational efficiency**: Faster training and inference
- **Domain features**: Hand-crafted energy features often beat learned representations

A deep learning module is in development for use cases with large datasets and complex patterns.

Can I use my own models?
------------------------

Yes! OpenSTEF is model-agnostic. Any scikit-learn compatible model works:

.. code-block:: python

   from sklearn.ensemble import RandomForestRegressor
   from openstef_models.models.forecasting import SklearnForecaster
   
   # Use any sklearn model
   forecaster = SklearnForecaster(
       model=RandomForestRegressor(n_estimators=100),
       horizons=["PT1H", "PT6H", "PT24H"]
   )

You can also implement custom forecasters by inheriting from the base `Forecaster` class.

How do I get started?
---------------------

1. **Install**: ``pip install openstef``
2. **Quick start**: Follow our quickstart guide
3. **Learn**: Work through our tutorials
4. **Explore**: Check use cases to find your scenario

For production deployment, see our how-to guides for integration patterns.

Where can I get help?
---------------------

- **Documentation**: This site covers most use cases
- **GitHub Issues**: `Report bugs or request features <https://github.com/OpenSTEF/openstef/issues>`_
- **Community**: Join our Slack workspace (link on project homepage)
- **Email**: openstef@lfenergy.org for general questions

We also hold bi-weekly community meetings open to all users.