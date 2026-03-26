Frequently Asked Questions
==========================

Common questions about OpenSTEF, answered concisely for conference attendees and new users.

What is OpenSTEF?
-----------------

OpenSTEF is a **Python machine learning library** for short-term energy forecasting. It's not an application you download and run - it's a toolkit you integrate into your own systems. The library provides complete pipelines for training models, generating forecasts, and evaluating results.

Short-term means predicting energy loads hours to days ahead, typically up to 48 hours. This is different from long-term planning forecasts that look months or years ahead.

Do I need grid topology data?
-----------------------------

No, OpenSTEF works with time series data only. You don't need network topology, impedance matrices, or detailed grid models. The library focuses on statistical patterns in historical load data combined with weather forecasts.

This makes OpenSTEF much simpler to deploy than power flow analysis tools. You just need:

- Historical load measurements (15-minute intervals recommended)
- Weather forecast data (temperature, solar radiation, wind speed)
- Optional: calendar information for holidays and special events

What makes OpenSTEF special?
----------------------------

OpenSTEF combines several unique features that aren't found together in other forecasting frameworks:

**Energy-specific domain knowledge**: Built-in feature engineering that understands energy patterns - how solar radiation translates to PV generation, temperature effects on heating/cooling demand, and weekly/seasonal cycles.

**Probabilistic forecasts with uncertainty**: Not just point predictions, but confidence intervals and quantiles. Critical for grid operators who need to know "how wrong could this forecast be?"

**Production-proven at scale**: Currently running 10,000+ forecasts daily at Alliander. The library handles real-world challenges like missing data, model drift, and operational constraints.

**Model-agnostic framework**: Supports XGBoost, linear models, and other algorithms through a consistent interface. Easy to experiment with different approaches.

What's the forecast accuracy?
-----------------------------

Accuracy depends heavily on your specific use case and data quality. Typical performance ranges:

- **Highly aggregated points** (substations): 2-5% mean absolute error
- **Medium aggregation** (neighborhoods): 5-15% mean absolute error  
- **Individual customers**: 15-50% mean absolute error (high variability)

Peak period accuracy is often better than average periods due to more predictable patterns. Weather-dependent loads (heating/cooling) are generally more predictable than behavioral loads.

.. note::
   Test with your own data using the benchmark datasets in our tutorials. Accuracy varies significantly based on aggregation level, weather dependency, and data quality.

How expensive is it to run?
---------------------------

OpenSTEF is designed to be computationally efficient:

**Training**: Most models train in minutes on standard hardware. A typical XGBoost model for one location uses <1 GB RAM and trains in 2-10 minutes.

**Forecasting**: Very fast - generating a 48-hour forecast takes seconds. Suitable for real-time applications.

**Infrastructure**: Can run on modest hardware. Alliander's production system handles 10,000+ forecasts on standard cloud infrastructure.

**Scaling**: Linear scaling - 10x more forecast points needs roughly 10x more compute time.

What about deep learning and neural networks?
----------------------------------------------

OpenSTEF currently focuses on tree-based models (XGBoost) and linear models, which work very well for energy forecasting. These models are:

- Fast to train and deploy
- Interpretable for operational staff
- Robust with limited data
- Easy to debug when things go wrong

Deep learning support is planned for future releases, particularly for:

- Very large datasets with complex patterns
- Multi-modal inputs (satellite imagery, text data)
- Transfer learning across similar grid points

For most energy forecasting use cases, traditional ML approaches in OpenSTEF provide excellent results with lower complexity.

Can I use this for my country/region?
-------------------------------------

Yes, OpenSTEF 4.0 is designed to work globally. Earlier versions had some Netherlands-specific assumptions, but V4 supports:

- Custom holiday calendars for any country
- Different time zones and daylight saving rules
- Various data formats and measurement intervals
- Flexible weather data sources

The core forecasting algorithms work anywhere - energy consumption patterns are surprisingly similar across regions when you account for climate and cultural differences.

How do I get started?
---------------------

1. **Install the library**: ``pip install openstef``
2. **Try the quickstart**: Follow our quickstart guide
3. **Run tutorials**: Work through our tutorials with sample data
4. **Check use cases**: See our use cases guide to find your specific application

The fastest path is starting with our benchmark datasets, then gradually replacing with your own data.

Where can I get help?
---------------------

- **Documentation**: Start with our tutorials
- **GitHub Issues**: Report bugs and ask technical questions
- **Community**: Email openstef@lfenergy.org for general questions
- **Examples**: Check the tutorials for working code examples

OpenSTEF has an active community of grid operators, researchers, and developers who contribute to the project and help new users get started.