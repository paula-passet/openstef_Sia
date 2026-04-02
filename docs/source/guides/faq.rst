Frequently Asked Questions
==========================

This page answers common questions from new users exploring OpenSTEF for the first time. If you're looking for implementation details, see the :doc:`../getting_started/quickstart` or :doc:`../getting_started/tutorials`.

What is short-term forecasting?
--------------------------------

Short-term forecasting predicts energy demand or supply for the next few hours to several days ahead. This differs from long-term forecasting (years ahead for infrastructure planning) or real-time control (seconds to minutes).

Typical short-term forecasting horizons:

- **0-48 hours**: Operational planning, congestion management, grid balancing
- **1-7 days**: Maintenance scheduling, resource allocation
- **1-14 days**: Market participation, capacity planning

OpenSTEF focuses on these operational timescales where weather, calendar patterns, and recent trends drive predictions. The library generates forecasts at 15-minute resolution, which is standard for European energy markets.

What is OpenSTEF?
-----------------

OpenSTEF is a Python machine learning library for short-term energy forecasting. It's not an application or platform—it's a toolkit you integrate into your own systems.

The library provides:

- Pre-built feature engineering for time series and weather data
- Automated model training with hyperparameter optimization
- Quantile forecasting for uncertainty estimation
- Backtesting and validation tools
- Production-ready prediction pipelines

You use OpenSTEF by importing it into your Python code, similar to how you'd use scikit-learn or pandas. See :doc:`../getting_started/quickstart` for a minimal working example.

What makes OpenSTEF special?
-----------------------------

OpenSTEF emerged from real-world operational experience at Dutch grid operators. Several characteristics distinguish it:

**Operational focus**: The library handles practical concerns like missing data, model fallbacks, and confidence intervals—not just point predictions. It's designed for systems that run continuously in production.

**Quantile forecasting**: OpenSTEF generates probabilistic forecasts (e.g., P10, P50, P90 quantiles) by default. This lets you estimate not just the expected load, but the range of likely outcomes. Critical for congestion management where you need to know worst-case scenarios.

**Proven in production**: The codebase powers forecasts for millions of grid connections across multiple European grid operators. The algorithms have been refined through years of operational feedback.

**Energy domain expertise**: Feature engineering and model architecture incorporate domain knowledge about energy consumption patterns, weather dependencies, and grid behavior. You don't start from scratch.

See :doc:`concepts` for deeper explanations of these design choices.

Do I need network topology data?
---------------------------------

Usually no. Most OpenSTEF use cases work with simple time series data—historical load measurements and weather forecasts.

**When you don't need topology**:

- Forecasting individual substations or feeders
- Aggregated regional forecasts
- District heating demand
- Most congestion management scenarios

You provide historical measurements (e.g., 15-minute load data) and weather features. OpenSTEF learns temporal patterns and weather correlations. This covers the majority of use cases.

**When topology helps**:

- Medium voltage (MV) route forecasting where you need to aggregate multiple substations
- Complex grid structures where load flows through multiple paths
- Scenarios requiring power flow calculations

For these cases, OpenSTEF integrates with `power-grid-model <https://power-grid-model.readthedocs.io/>`_ to incorporate network structure. See the MV route example in :doc:`use_cases` for details.

Starting without topology is simpler and works well for most applications. Add topology later if your use case requires it.

Why doesn't OpenSTEF use deep learning?
----------------------------------------

OpenSTEF uses gradient boosted trees (XGBoost) as its primary model. This choice reflects practical experience with production forecasting systems.

**Advantages of gradient boosting for this domain**:

- **Training efficiency**: Models train in minutes on typical datasets (years of 15-minute data). Deep learning often requires hours or days.
- **Data efficiency**: Works well with limited training data. Energy datasets are often small by deep learning standards.
- **Interpretability**: Feature importance analysis shows which predictors drive forecasts. Essential for debugging and building trust with operators.
- **Robustness**: Handles missing data and outliers gracefully without extensive preprocessing.
- **Proven accuracy**: Extensive backtesting shows XGBoost performs as well or better than deep learning for short-term energy forecasting.

Deep learning excels with massive datasets and complex patterns (images, language). Short-term energy forecasting has strong seasonal and weather-driven patterns that gradient boosting captures efficiently.

That said, OpenSTEF's architecture is modular. If your use case benefits from deep learning (e.g., very high-resolution spatial forecasting), you can implement custom models. See the custom workflow examples in :doc:`../getting_started/tutorials`.

How do I get started?
----------------------

Three paths depending on your needs:

1. **Quick experiment** (5 minutes): Follow :doc:`../getting_started/quickstart` to train a model and generate a forecast with minimal code.

2. **Production implementation** (1-2 hours): Work through :doc:`../getting_started/tutorials` to understand data preparation, backtesting, and customization.

3. **Evaluate use cases** (15 minutes): Review :doc:`use_cases` to identify which forecasting scenario matches your needs.

All paths assume you have Python 3.9+ and basic familiarity with pandas and scikit-learn.

What data do I need?
--------------------

Minimum requirements:

- **Historical load measurements**: At least 1 year of data at 15-minute resolution (or your target resolution)
- **Weather forecasts**: Temperature, wind speed, radiation, and cloud cover for your forecast horizon
- **Weather history**: Historical weather matching your load measurements

Optional but helpful:

- **Additional predictors**: Holiday calendars, tariff schedules, or domain-specific features
- **Multiple years**: More history improves model quality, especially for capturing seasonal patterns

The library expects data as pandas DataFrames with datetime indices. See :doc:`../getting_started/tutorials` for detailed data preparation examples.

Can I use OpenSTEF for X?
--------------------------

Common questions about scope:

**Supported use cases**:

- Substation and feeder load forecasting
- Congestion prediction and capacity management
- Grid loss estimation
- District heating demand
- Solar and wind generation forecasting (with appropriate training data)

**Outside OpenSTEF's scope**:

- Long-term forecasting (years ahead)—use capacity planning tools instead
- Real-time control (sub-minute)—use state estimation systems
- Price forecasting—while technically possible, the library is optimized for physical load/generation
- Individual household forecasting—patterns are too noisy at this scale

See :doc:`use_cases` for detailed descriptions of supported scenarios.

How do I get help?
------------------

If your question isn't answered here:

- **Technical issues**: Open an issue on `GitHub <https://github.com/OpenSTEF/openstef>`_
- **Implementation questions**: Join the community Slack (link on project homepage)
- **Conceptual questions**: Review :doc:`concepts` for deeper explanations
- **Migration help**: See the V3 to V4 migration guide in :doc:`how_to_guides`

The OpenSTEF community includes grid operators, researchers, and developers who've implemented production forecasting systems. Don't hesitate to ask.