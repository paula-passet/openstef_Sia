Frequently Asked Questions
==========================

This page answers the most common questions about OpenSTEF asked by new users and at conferences. For detailed technical information, see the linked documentation pages.

What is OpenSTEF?
-----------------

OpenSTEF is a Python machine learning library for short-term energy forecasting. It's **not an application** you install and run - it's a library you integrate into your own systems and workflows.

Short-term forecasting means predicting energy loads hours to days ahead, typically used for congestion management, transport forecasting, and grid operations.

What makes OpenSTEF special compared to other forecasting frameworks?
---------------------------------------------------------------------

OpenSTEF combines several unique characteristics:

- **Domain knowledge built-in**: Features like solar radiation to PV generation conversion, energy-specific transformations, and weather dependency handling are included out of the box
- **Probabilistic forecasts**: Provides uncertainty bands and confidence intervals, not just point predictions
- **Model-agnostic framework**: Works with any scikit-learn compatible model, from linear regression to XGBoost
- **Complete ML pipeline**: Handles data validation, feature engineering, training, forecasting, and evaluation in one integrated system
- **Resilient by design**: Multiple fallback strategies ensure forecasts are always available, even when primary models fail

The "magic" is in the energy-specific feature engineering and the combination of classical ML models with smart domain features, which often outperforms more complex approaches.

Do I need grid topology information?
------------------------------------

No, OpenSTEF works with point-based forecasting - each grid point is forecasted independently without requiring network topology data.

However, if you have topology information and want to use it, OpenSTEF can be combined with `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for topology-aware forecasting. This approach has been documented in published research.

What about deep learning models?
--------------------------------

OpenSTEF currently focuses on classical machine learning models (XGBoost, LightGBM, linear models) combined with sophisticated feature engineering. This approach often achieves excellent performance with lower computational requirements and better interpretability.

A deep learning module is in development for future releases, but the current classical ML approach with domain-specific features frequently outperforms deep learning approaches for energy forecasting tasks.

What accuracy can I expect?
---------------------------

Forecast accuracy depends heavily on your specific use case and data quality. Key factors include:

- **Aggregation level**: Higher aggregation (more customers) typically means better accuracy
- **Data availability**: More historical data and weather predictors improve performance  
- **Use case**: Peak detection (congestion management) vs. overall accuracy (transport forecasts) have different requirements

The best approach is to test OpenSTEF with your own data using benchmark datasets. See :doc:`../getting_started/quickstart` to get started with evaluation.

How expensive is it to run?
---------------------------

OpenSTEF is designed to be computationally efficient:

- **Lightweight models**: Classical ML models require less computational power than deep learning
- **Containerized deployment**: Runs on any container platform with minimal infrastructure
- **Modular architecture**: Use only the components you need
- **Production proven**: Alliander runs 10,000+ forecasts daily in production

For small deployments, a basic cloud instance or even local machine is sufficient. Enterprise deployments can scale using standard container orchestration platforms.

Is OpenSTEF only for Dutch grid operators?
------------------------------------------

No, while OpenSTEF was developed by Alliander (Netherlands), it's designed for international use:

- **Configurable features**: Holiday calendars, energy pricing, and other regional aspects can be customized
- **Multiple organizations involved**: RTE (France), Sigholm (Sweden), and others contribute to development
- **Flexible data formats**: Supports various input data structures and availability scenarios
- **Open source**: Available for any organization to use and adapt

See :doc:`use_cases` for examples of different applications beyond Dutch grid operations.

How do I get started?
---------------------

1. **Quick start**: Follow :doc:`../getting_started/quickstart` for your first forecast in minutes
2. **Learn the concepts**: Read :doc:`../reference/concepts` to understand key forecasting principles  
3. **Explore use cases**: Check :doc:`use_cases` to find applications similar to yours
4. **Join the community**: Connect with other users on our `Slack workspace <https://lfenergy.slack.com/>`_

For production deployment, see :doc:`how_to_guides` for integration examples with common infrastructure components.