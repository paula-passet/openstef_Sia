Frequently Asked Questions
==========================

This page answers common questions about OpenSTEF from new users and conference attendees.

What is "short-term" forecasting?
---------------------------------

Short-term forecasting means predicting energy load hours to days ahead. OpenSTEF typically forecasts 2-48 hours into the future, which is the critical time horizon for operational grid management decisions like congestion management and peak shaving.

This is different from:

- **Ultra-short-term** (minutes to hours): Used for real-time control
- **Medium-term** (days to weeks): Used for maintenance planning  
- **Long-term** (months to years): Used for grid expansion planning

Do you need grid topology data?
-------------------------------

**No, OpenSTEF works without grid topology.** The library operates on a point-based approach, forecasting each grid location independently using only:

- Historical load measurements at that point
- Weather data
- Calendar features (time of day, day of week, holidays)

However, OpenSTEF can be combined with topology-aware tools like `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for more sophisticated grid analysis. Research has shown this combination can improve accuracy for certain use cases.

What makes OpenSTEF special compared to other forecasting frameworks?
---------------------------------------------------------------------

OpenSTEF's key differentiators:

**Built for energy forecasting**: Unlike general-purpose forecasting libraries, OpenSTEF includes domain-specific features like solar radiation to PV generation conversion, energy-specific data preprocessing, and grid-aware evaluation metrics.

**Probabilistic by design**: Provides uncertainty estimates and confidence intervals, not just point forecasts. This is crucial for risk management in grid operations.

**Production-ready**: Currently running 10,000+ daily forecasts at Alliander. The library includes robust data validation, fallback strategies, and operational monitoring.

**Complete pipeline**: Handles the entire ML workflow from data preprocessing to model deployment, not just model training.

What accuracy can I expect?
---------------------------

Accuracy depends heavily on your specific use case and data quality. Key factors:

- **Data completeness**: Missing or poor-quality measurements significantly impact performance
- **Forecast horizon**: Accuracy decreases with longer horizons (2-hour forecasts are more accurate than 48-hour)
- **Load characteristics**: Predictable industrial loads forecast better than volatile residential solar
- **Weather dependency**: Locations with strong weather correlation achieve better results

.. note::
   The best approach is to test OpenSTEF with your own data using the benchmark dataset functionality. Evaluate metrics relevant to your specific use case rather than relying on generic accuracy numbers.

How expensive is it to run?
---------------------------

OpenSTEF is designed to be computationally efficient:

**Hardware requirements**: Runs on standard hardware - no GPUs required. Python 3.12+ with typical scientific computing libraries.

**Scalability**: The modular architecture allows you to install only needed components. For production forecasting, `openstef-models` provides lightweight core functionality.

**Training costs**: Models train quickly (minutes to hours) using classical ML algorithms like XGBoost and LightGBM, not computationally expensive deep learning.

**Operational costs**: Once trained, generating forecasts is very fast - suitable for high-frequency operational use.

What about deep learning?
-------------------------

OpenSTEF currently focuses on classical machine learning (XGBoost, LightGBM, linear models) combined with smart feature engineering. This approach delivers excellent performance while being:

- Faster to train and deploy
- More interpretable for operational staff
- Less computationally expensive
- More robust with limited data

A deep learning module is in development for future releases, but the current classical ML approach often outperforms complex neural networks when combined with domain-specific feature engineering.

Can multiple organizations use OpenSTEF?
----------------------------------------

Yes, OpenSTEF is open source and designed for broad adoption:

**Current users**: Alliander (operational), RTE and RTE International (transmission operators), Sigholm (consultancy for Swedish DSOs)

**Community**: Active community with bi-weekly meetings, Slack workspace, and co-coding sessions

**Flexibility**: The modular design supports different organizational needs and deployment patterns

.. note::
   While multiple organizations are involved in development, Alliander is currently the only DSO using OpenSTEF operationally at scale.

How do I get started?
---------------------

1. **Quick evaluation**: Try the :doc:`../getting_started/quickstart` to create your first forecast in minutes
2. **Learn the concepts**: Read :doc:`../reference/concepts` to understand energy forecasting fundamentals  
3. **Identify your use case**: Review :doc:`use_cases` to find the approach that matches your needs
4. **Join the community**: Connect via our `Slack workspace <https://lfenergy.slack.com/channels/openstef>`_ for support and discussions

For more detailed guidance, see our :doc:`../getting_started/tutorials` and :doc:`how_to_guides`.