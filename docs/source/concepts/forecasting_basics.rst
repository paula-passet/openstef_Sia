Short-Term Forecasting Basics
==============================

This page explains what short-term forecasting is, why it matters for energy systems, and how it differs from other types of forecasting. Understanding these fundamentals will help you use OpenSTEF effectively for operational energy predictions.

What is Short-Term Forecasting?
--------------------------------

Short-term forecasting predicts energy consumption or generation from minutes to a few days ahead. Unlike long-term forecasting (which might predict annual energy demand for infrastructure planning), short-term forecasts support immediate operational decisions: balancing the grid, dispatching generators, managing storage, and trading energy in real-time markets.

OpenSTEF specializes in this operational forecasting domain, where predictions must be:

- **Frequent**: Updated every 15 minutes to an hour as new data arrives
- **Fast**: Generated quickly enough to support real-time decisions
- **Accurate at short horizons**: Most valuable for the next few hours
- **Probabilistic**: Capturing uncertainty for risk management

The library handles time series data at resolutions from 15 minutes to daily intervals, with 15-minute sampling being the most common for grid operations.

Key Concepts
------------

Understanding Horizons
^^^^^^^^^^^^^^^^^^^^^^

The **horizon** (or lead time) is how far ahead you're predicting. In OpenSTEF, horizons are specified as ``timedelta`` objects representing the gap between when a forecast is made and when it applies.

For example, if you make a forecast at 10:00 AM for 2:00 PM the same day, your horizon is 4 hours. Energy forecasting typically requires multiple horizons simultaneously—you might need predictions for 15 minutes, 1 hour, 6 hours, and 24 hours ahead, all at once.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.model_configurations import XGBForecasterConfig
   from openstef_core.model_configurations.types import LeadTime
   
   # Configure a forecaster for multiple horizons
   config = XGBForecasterConfig(
       horizons=[
           LeadTime(timedelta(minutes=15)),  # Very short-term
           LeadTime(timedelta(hours=1)),     # Short-term
           LeadTime(timedelta(hours=6)),     # Medium-term
           LeadTime(timedelta(hours=24)),    # Day-ahead
       ]
   )

Each horizon may require different features or model behavior. Very short-term forecasts (15-60 minutes) rely heavily on recent measurements and autocorrelation. Longer horizons (6-48 hours) depend more on weather forecasts, calendar patterns, and historical trends.

Forecast Frequency and Resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Resolution** is the time step between consecutive predictions—typically 15 minutes for distribution grid operations. **Frequency** is how often you generate new forecasts—often matching the resolution, so every 15 minutes you produce a new set of predictions.

OpenSTEF datasets use the ``sample_interval`` parameter to specify resolution:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import ForecastInputDataset
   import pandas as pd
   
   # Prepare input data with 15-minute resolution
   data = pd.DataFrame({
       'load': [100.5, 102.3, 98.7, 101.2],
       'temperature': [15.2, 15.5, 15.8, 16.0],
   }, index=pd.date_range('2024-01-01', periods=4, freq='15min'))
   
   dataset = ForecastInputDataset(
       data=data,
       sample_interval=timedelta(minutes=15),
       target_column='load'
   )

Higher resolution (shorter intervals) provides more granular predictions but requires more computational resources and careful feature engineering. Lower resolution (hourly or daily) may be sufficient for slower-changing systems like district heating.

Why Short-Term Forecasting Matters
-----------------------------------

Energy systems operate in real-time with limited storage capacity. Grid operators must continuously balance supply and demand within tight tolerances. Short-term forecasts enable:

**Grid Balancing**: Predict load 15 minutes to 1 hour ahead to schedule generation and avoid frequency deviations.

**Energy Trading**: Submit bids to day-ahead and intraday markets based on 24-48 hour forecasts of consumption or renewable generation.

**Congestion Management**: Anticipate grid bottlenecks hours ahead to reroute power or curtail generation.

**Demand Response**: Trigger load shedding or flexible consumption based on near-term predictions.

The value of accuracy decreases rapidly with horizon—a 1% improvement in the 1-hour forecast is often worth more than a 5% improvement at 24 hours, because short-term decisions have immediate financial and operational impact.

Differences from Long-Term Forecasting
---------------------------------------

Long-term forecasting (months to years ahead) and short-term forecasting serve different purposes and use different methods:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Aspect
     - Short-Term (OpenSTEF)
     - Long-Term
   * - Horizon
     - Minutes to days
     - Months to years
   * - Purpose
     - Operational decisions
     - Planning and investment
   * - Update frequency
     - Every 15-60 minutes
     - Monthly or quarterly
   * - Key predictors
     - Weather, recent load, time of day
     - Economic growth, population, policy
   * - Accuracy priority
     - Next few hours critical
     - Annual totals matter most
   * - Uncertainty
     - Quantified with prediction intervals
     - Scenario-based analysis

OpenSTEF focuses exclusively on the operational short-term domain. If you need long-term capacity planning forecasts, you'll need different tools and methodologies.

Practical Implications
----------------------

When building short-term forecasts with OpenSTEF, keep these principles in mind:

**Recent data matters most**: The most recent measurements (last 15 minutes to 1 hour) strongly influence short-term predictions. Ensure your data pipeline delivers fresh inputs quickly.

**Weather forecasts are essential**: For horizons beyond 1-2 hours, weather predictions (temperature, wind speed, solar irradiance) become critical features. See :doc:`feature_engineering` for details.

**Multiple models may be needed**: A single model configuration may not perform optimally across all horizons. Consider training separate models for very short-term (< 1 hour) and longer horizons (> 6 hours). See :doc:`model_selection` for guidance.

**Probabilistic forecasts reduce risk**: Point predictions alone don't capture uncertainty. OpenSTEF generates quantile forecasts that provide confidence intervals, helping operators make risk-aware decisions. Learn more in :doc:`quantiles_and_confidence`.

**Production reliability is critical**: Operational systems can't tolerate forecast failures. Implement fallback strategies as described in :doc:`reliability_and_fallback`.

Next Steps
----------

Now that you understand short-term forecasting fundamentals, explore:

- :doc:`quantiles_and_confidence` - How probabilistic forecasts work
- :doc:`feature_engineering` - Building effective predictors
- :doc:`model_selection` - Choosing the right algorithm
- :doc:`reliability_and_fallback` - Ensuring production robustness