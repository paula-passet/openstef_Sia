Frequently Asked Questions
==========================

This page answers common questions from new users about OpenSTEF's scope, capabilities, and design choices.

What is short-term forecasting?
--------------------------------

Short-term forecasting predicts energy values from minutes to several days ahead. OpenSTEF typically forecasts horizons from 15 minutes up to 47 hours, though this is configurable based on your needs.

This differs from:

- **Ultra-short-term forecasting**: Seconds to minutes ahead, often used for real-time control
- **Medium-term forecasting**: Weeks to months ahead, used for maintenance planning
- **Long-term forecasting**: Years ahead, used for infrastructure investment decisions

Short-term forecasts are essential for operational decisions like grid congestion management, balancing supply and demand, and optimizing energy storage.

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_core.types import LeadTime
   
   # Configure forecaster for 47-hour horizon
   forecaster = XGBoostForecaster(
       horizons=[LeadTime.from_string("PT47H")]
   )

See :doc:`../reference/concepts` for more details on forecast horizons and lead times.


Do I need network topology data?
---------------------------------

**No, topology is optional.** Most OpenSTEF use cases work without any network topology information.

OpenSTEF primarily uses historical load data and weather forecasts to create predictions. For most applications—congestion forecasts, grid loss estimation, transport forecasts—you only need time series data.

**When topology helps:**

Topology becomes useful when you want to aggregate or disaggregate forecasts across network structures. For example:

- Forecasting MV routes by combining substation forecasts
- Splitting HV/MV transformer forecasts to downstream components
- Understanding how load flows through network hierarchies

The ``power-grid-model`` integration enables these topology-aware workflows, but it's not required for basic forecasting.

.. code-block:: python

   # Standard forecasting without topology
   from openstef_models.models import ForecastingModel
   
   model = ForecastingModel(forecaster=forecaster)
   model.fit(historical_data)  # Only needs load and weather data
   forecast = model.predict(future_weather)

See :doc:`use_cases` for examples of when topology adds value, particularly the MV route congestion management use case.


What makes OpenSTEF special?
-----------------------------

OpenSTEF is purpose-built for energy sector forecasting with several distinctive features:

**Probabilistic forecasting by default**

OpenSTEF produces quantile forecasts (e.g., P10, P50, P90) rather than single point predictions. This gives you confidence intervals essential for risk management and operational planning.

**Energy-domain features**

The library includes specialized feature engineering for energy applications: wind power curves, temperature-load relationships, holiday effects, and energy split decomposition. These aren't generic ML features—they're designed specifically for grid operations.

**Multi-horizon single-shot forecasts**

One model training produces forecasts for all horizons simultaneously, from 15 minutes to 47 hours ahead. This is more efficient than training separate models for each horizon.

**Production-tested at scale**

OpenSTEF has been running in production at Dutch grid operators since 2018, generating thousands of forecasts daily. The library encodes years of operational experience.

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_core.types import Quantile
   
   # Probabilistic forecasts with confidence intervals
   forecaster = XGBoostForecaster(
       horizons=[LeadTime.from_string("PT47H")],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

The :doc:`../getting_started/quickstart` demonstrates these features in a minimal example.


Why not deep learning?
-----------------------

OpenSTEF uses XGBoost (gradient boosted trees) as its primary algorithm rather than neural networks. This is a deliberate choice based on practical experience:

**Data efficiency**

Tree-based models perform well with hundreds or thousands of training examples. Deep learning typically requires orders of magnitude more data to achieve comparable performance. Most grid operators don't have millions of historical data points per forecast location.

**Interpretability**

XGBoost provides feature importance scores and SHAP values that help explain predictions. This is crucial for operational trust and debugging. Neural networks are much harder to interpret.

**Training speed and resource requirements**

XGBoost trains in minutes on standard hardware. Deep learning often requires hours or days on GPUs. For operational forecasting systems that retrain models regularly, this matters.

**Proven performance**

In benchmarks on energy forecasting tasks, XGBoost consistently matches or exceeds deep learning performance while being simpler to deploy and maintain.

That said, OpenSTEF's architecture is extensible. If you have use cases where deep learning excels—such as very large datasets or complex spatial-temporal patterns—you can implement custom forecasters. The library provides the infrastructure; you choose the algorithm.

.. note::

   OpenSTEF's XGBoost implementation includes specialized quantile regression with magnitude-weighted pinball loss, optimized specifically for probabilistic energy forecasting.

See :doc:`../reference/concepts` for more on model selection and the trade-offs between different approaches.


Can I use OpenSTEF for my use case?
------------------------------------

OpenSTEF is designed for short-term energy forecasting but adapts to many scenarios:

**Typical applications:**

- Electricity grid congestion forecasting
- Substation load prediction
- Renewable generation forecasting (solar, wind)
- District heating demand forecasting
- Grid loss estimation
- Free capacity calculation

**What OpenSTEF is NOT designed for:**

- Long-term capacity planning (years ahead)
- Real-time control (sub-second response)
- Price forecasting (different feature requirements)
- Non-energy time series (lacks domain-specific features)

If your use case involves predicting energy-related quantities hours to days ahead, OpenSTEF likely fits. The library is flexible enough to handle various prediction targets as long as they follow similar temporal patterns.

.. code-block:: python

   # OpenSTEF works for different energy quantities
   # Just change your target column in the training data
   
   # For load forecasting
   load_data = data[["datetime", "load", "temperature", "windspeed"]]
   
   # For solar generation forecasting
   solar_data = data[["datetime", "solar_generation", "radiation", "cloudcover"]]
   
   # Same model architecture, different target
   model.fit(load_data)  # or model.fit(solar_data)

See :doc:`use_cases` for detailed examples of different applications and how to configure OpenSTEF for each.


How do I get started?
----------------------

The fastest path to your first forecast:

1. **Install OpenSTEF**: ``pip install openstef``
2. **Follow the quickstart**: :doc:`../getting_started/quickstart` shows a complete example in ~20 lines of code
3. **Try the tutorials**: :doc:`../getting_started/tutorials` covers data preparation, training, and evaluation in detail
4. **Explore use cases**: :doc:`use_cases` helps identify which approach fits your needs

Most users can generate their first forecast within an hour of installation.


Where can I get help?
---------------------

- **GitHub Issues**: Report bugs or request features at https://github.com/OpenSTEF/openstef
- **Discussions**: Ask questions and share experiences in GitHub Discussions
- **LF Energy Community**: Join the broader community at https://www.lfenergy.org/projects/openstef/

The OpenSTEF community includes grid operators, researchers, and developers who actively support new users.