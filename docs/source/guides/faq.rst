Frequently Asked Questions
==========================

This page answers common questions about OpenSTEF from conferences and new users. For detailed implementation guidance, see our :doc:`../getting_started/quickstart` and :doc:`../getting_started/tutorials`.

What is OpenSTEF?
-----------------

OpenSTEF is a Python machine learning library for short-term energy forecasting. It's not an application with a GUI - it's a library that you integrate into your own systems to create energy forecasts.

The library provides complete pipelines for data preprocessing, feature engineering, model training, forecasting, and evaluation. It generates probabilistic forecasts (with uncertainty bands), not just single-point predictions.

What do you mean by "short-term"?
----------------------------------

Short-term forecasting means predicting load from 15 minutes up to several days ahead. The specific horizon depends on your use case:

- **15 minutes ahead** (horizon 0.25): Real-time operational decisions
- **2-48 hours ahead**: Day-ahead planning and congestion management
- **Several days ahead**: Medium-term grid planning

.. code-block:: python

   # Example: forecast 15 minutes and 47 hours ahead
   training_horizons = [0.25, 47.0]
   forecast, model, train_data, validation_data, test_data = openstef.pipeline.train_model(
       input_data=data,
       training_horizons=training_horizons
   )

Do I need grid topology data?
-----------------------------

No, OpenSTEF works without grid topology. It forecasts each grid point independently based on historical load and weather data.

However, you *can* combine OpenSTEF with topology-aware approaches. For example, integrate with `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for topology-aware forecasting. See our :doc:`use_cases` guide for MV route congestion management examples.

What makes OpenSTEF special compared to other forecasting frameworks?
----------------------------------------------------------------------

OpenSTEF's "magic" comes from domain-specific intelligence built into the library:

**Energy-specific feature engineering:**

- Automatically converts solar radiation + temperature into PV generation estimates
- Handles energy market price correlations
- Includes seasonal and weather-dependent transformations

**Model-agnostic design:**

.. code-block:: python

   # Easy to switch between models
   modelspecs_xgb = ModelSpecs(model_type="xgb")
   modelspecs_linear = ModelSpecs(model_type="linear_quantile")

**Probabilistic forecasts with fallback strategies:**

The library always provides a forecast, even when primary models fail. Fallback forecasts are clearly labeled so you know which forecasts informed your decisions.

What accuracy can I expect?
---------------------------

Accuracy depends heavily on your use case and data quality. Factors that affect performance:

- **Data quality**: Clean, consistent historical data improves accuracy
- **Forecast horizon**: Shorter horizons (15 minutes) are more accurate than longer ones (48 hours)
- **Load characteristics**: Predictable industrial loads forecast better than volatile residential loads
- **Weather dependency**: Solar/wind generation forecasts depend on weather forecast quality

For realistic expectations, try the `Alliander 2021 Energy Forecasting Benchmark <https://github.com/alliander-opensource/short-term-forecasting-benchmark>`_ dataset with your own evaluation metrics.

How expensive is it to run?
---------------------------

OpenSTEF is designed to be computationally efficient:

**Training costs:**
- Classical ML models (XGBoost, LightGBM) train quickly on standard hardware
- Most models train in minutes to hours, not days
- Memory requirements are modest for typical grid datasets

**Operational costs:**
- Forecasting is fast - typically seconds per prediction
- Can run on modest cloud instances or on-premises servers
- No GPU required for current model types

**Deployment options:**
- Simple cron job scheduling for basic deployments
- Container-based deployment for production systems
- See our :doc:`how_to_guides` for deployment examples

What about deep learning?
-------------------------

OpenSTEF currently focuses on classical ML models (XGBoost, LightGBM, linear models) because they:

- Train faster and require less data
- Are more interpretable for grid operators
- Perform well with smart feature engineering
- Have lower computational requirements

A deep learning module is in development for users who need it, but classical ML + domain-specific features often outperforms deep learning for energy forecasting tasks.

Which model should I choose?
----------------------------

Model choice depends on your priorities:

**XGBoost (default):**
- Good all-around performance
- Handles complex patterns well
- Fast training and prediction

**Linear quantile regression:**
- Better at predicting extreme peaks
- More interpretable coefficients
- Faster training on large datasets

**LightGBM:**
- Similar to XGBoost but often faster
- Good for very large datasets

Start with XGBoost and experiment with others based on your specific needs. See :doc:`../reference/concepts` for detailed model guidance.

Can I use OpenSTEF for my specific use case?
--------------------------------------------

OpenSTEF supports many energy forecasting scenarios:

- Grid congestion forecasting
- Renewable generation forecasting
- Load forecasting for different voltage levels
- District heating demand forecasting
- Free capacity estimation

Check our :doc:`use_cases` guide to see if your scenario matches existing patterns, or adapt the library for custom applications.

How do I get started?
---------------------

1. **Quick start**: Follow our :doc:`../getting_started/quickstart` to create your first forecast in minutes
2. **Learn the concepts**: Read :doc:`../reference/concepts` to understand forecasting fundamentals
3. **Try tutorials**: Work through :doc:`../getting_started/tutorials` for comprehensive examples
4. **Join the community**: Connect with other users on our Slack workspace

For production deployment, see :doc:`how_to_guides` for integration patterns with your existing systems.