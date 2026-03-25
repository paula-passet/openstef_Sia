Frequently Asked Questions
==========================

This page answers common questions from new users and conference attendees about OpenSTEF's capabilities, requirements, and unique features.

What is "short-term" forecasting?
----------------------------------

Short-term forecasting means predicting energy load hours to days ahead, typically up to 48 hours. This is distinct from:

- **Real-time forecasting** (minutes ahead) for immediate grid control
- **Long-term forecasting** (weeks to years ahead) for capacity planning

The short-term horizon is critical for congestion management, where grid operators need advance warning of peak load periods to coordinate with customers and prevent equipment overload.

Do I need grid topology data?
------------------------------

No, OpenSTEF works without grid topology information. It forecasts each grid point independently based on historical load patterns and weather data.

However, you can combine OpenSTEF with topology-aware tools like `power-grid-model` for advanced use cases. Research has shown this combination can improve accuracy for certain applications, particularly in medium-voltage networks.

.. note::
   For most use cases, the point-based approach provides excellent results without the complexity of topology modeling.

What makes OpenSTEF special compared to other forecasting frameworks?
----------------------------------------------------------------------

OpenSTEF is purpose-built for energy forecasting with several unique characteristics:

**Domain-specific intelligence**
   Built-in feature engineering transforms weather data into energy-relevant predictors (e.g., solar radiation → PV generation estimates). This embedded domain knowledge often outperforms generic time series tools.

**Probabilistic forecasts with uncertainty**
   Generates multiple quantile forecasts, not just point predictions. This uncertainty information is crucial for risk-based decision making in grid operations.

**Complete ML pipeline**
   Includes data validation, feature engineering, model training, forecasting, and evaluation in a single framework. No need to piece together separate tools.

**Model-agnostic design**
   Works with any scikit-learn compatible model. Currently optimized for classical ML (XGBoost, LightGBM) but supports custom implementations.

**Production-ready resilience**
   Multiple fallback strategies ensure forecasts are always available, even when data sources fail.

What about deep learning models?
--------------------------------

OpenSTEF currently focuses on classical machine learning models (XGBoost, LightGBM, linear models) combined with smart feature engineering. This approach often matches or exceeds deep learning performance while being more interpretable and computationally efficient.

A deep learning module is in development for future releases, but the current classical ML approach has proven highly effective in production environments.

What accuracy can I expect?
----------------------------

Forecast accuracy depends heavily on your specific use case and data quality:

- **Highly aggregated points** (substations, regions): Generally higher accuracy due to smoothed patterns
- **Individual customers**: More challenging due to behavioral variability
- **Weather-dependent loads**: Accuracy varies with weather forecast quality

The best approach is to test OpenSTEF with your own data using the benchmark evaluation tools. Different use cases optimize for different metrics (peak accuracy vs. overall accuracy vs. cost-weighted errors).

How expensive is it to run?
----------------------------

OpenSTEF is designed for efficiency:

**Computational requirements**
   Classical ML models train quickly and require minimal compute resources. A typical forecast runs in seconds to minutes on standard hardware.

**Infrastructure needs**
   As a Python library, OpenSTEF can run anywhere Python runs - from laptops to cloud platforms. No specialized hardware required.

**Operational costs**
   Currently handles 10,000+ daily forecasts in production at Alliander. Scales efficiently with standard orchestration tools (cron jobs, Dagster, Kubernetes).

The main costs are typically data storage and weather data subscriptions, not the forecasting computation itself.

Can I use OpenSTEF outside the Netherlands?
--------------------------------------------

Yes, OpenSTEF v4 is designed for international use. While v3 had some Netherlands-specific assumptions (holidays, energy market structure), v4 introduces:

- Configurable holiday calendars
- Flexible energy pricing models  
- Customizable feature engineering
- Support for different data formats and availability patterns

Several international organizations are already involved in development and testing.

Is OpenSTEF an application I can deploy?
----------------------------------------

No, OpenSTEF is a **Python library**, not a deployable application. You integrate it into your own systems and workflows.

For a complete forecasting system, you'll also need:

- Data fetchers (weather, load measurements)
- Database or data storage
- Orchestration (scheduling, monitoring)
- APIs or interfaces for accessing forecasts

See the how-to guides for deployment examples and the architecture reference for system design patterns.