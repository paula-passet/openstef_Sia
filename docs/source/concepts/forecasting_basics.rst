Short-Term Forecasting Basics
=============================

This page explains the core concepts behind short-term energy forecasting: what it is, why energy systems depend on it, and how it differs from longer-term planning forecasts. Understanding these fundamentals will help you make better use of OpenSTEF's forecasting capabilities.

What Is Short-Term Energy Forecasting?
--------------------------------------

Short-term energy forecasting predicts electricity load, generation, or net demand over a time window ranging from minutes to several days ahead. Grid operators, energy traders, and distribution system operators rely on these forecasts to balance supply and demand in near-real-time, schedule generation assets, and manage congestion on the network.

Unlike long-term forecasts used for infrastructure planning (which look months or years ahead and focus on peak capacity and growth trends), short-term forecasts must capture the rapid fluctuations driven by weather, human behavior, and renewable generation variability. The accuracy requirements are also different: a long-term planner can tolerate broad uncertainty bands, but an intraday market participant needs tight, reliable predictions updated frequently.

.. note::

   OpenSTEF is a library, not a turnkey application. It provides the building blocks—models, feature engineering, and evaluation tools—that you integrate into your own forecasting pipeline and operational systems.

Key Concepts
------------

Three concepts define any forecasting setup: the **forecast horizon**, the **lead time**, and the **forecast frequency**. Getting these right is essential before writing any code.

Forecast Horizon
^^^^^^^^^^^^^^^^

The forecast horizon is *how far into the future* a prediction extends. In energy systems, common horizons include:

- **Intraday** (15 minutes to several hours): used for real-time balancing, intraday trading, and congestion management.
- **Day-ahead** (12–36 hours): used for day-ahead market bidding and unit commitment.
- **Multi-day** (2–7 days): used for maintenance scheduling and reserve planning.

OpenSTEF represents horizons using ``LeadTime`` objects, which wrap Python ``timedelta`` values. A single model can be trained to produce forecasts at multiple horizons simultaneously:

.. code-block:: python

   from datetime import timedelta

   # Define the horizons you need predictions for
   horizons = [
       timedelta(hours=1),
       timedelta(hours=6),
       timedelta(hours=24),
       timedelta(hours=47),
   ]

Choosing the right set of horizons depends on your operational needs. Shorter horizons benefit from recent measurements (the latest load reading is highly predictive of the next 15 minutes), while longer horizons rely more heavily on weather forecasts and calendar patterns.

Lead Time
^^^^^^^^^

Lead time is the gap between when a forecast is *produced* (or *available*) and the moment it predicts. For example, if you generate a forecast at 10:00 for the period 11:00–11:15, the lead time is one hour.

Lead time matters because it determines which input data is available. A forecast with a 1-hour lead time can use weather observations up to the current moment, while a 24-hour lead time must rely on weather *forecasts* that carry their own uncertainty.

In OpenSTEF, datasets track this relationship explicitly. The ``ForecastInputDataset`` class stores both the target timestamp and the ``available_at`` timestamp, so the library knows exactly which features were available when the forecast was made:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import ForecastInputDataset

   # Filter a dataset to a specific lead time
   dataset_1h = dataset.filter_by_lead_time(lead_time=timedelta(hours=1))

   # Or select a single horizon from a multi-horizon dataset
   dataset_dayahead = dataset.select_horizon(horizon=timedelta(hours=24))

This design prevents a common and dangerous mistake in forecasting: **data leakage**. By explicitly modeling when each piece of information becomes available, OpenSTEF ensures that a day-ahead model never accidentally trains on data that wouldn't exist at prediction time.

.. warning::

   Data leakage—using future information during training—is the most common cause of models that look excellent in backtests but fail in production. OpenSTEF's ``available_at`` tracking helps prevent this, but you must ensure your own data pipelines respect the same constraints.

Forecast Frequency
^^^^^^^^^^^^^^^^^^

Forecast frequency is *how often* new predictions are generated. This is distinct from the time resolution of the predictions themselves. You might produce 15-minute resolution forecasts, but regenerate them every hour as new weather data arrives.

Higher forecast frequency generally improves accuracy for near-term horizons because each new run incorporates the latest observations. However, it also increases computational cost. A common pattern in energy forecasting is:

- **Every 15 minutes**: update intraday forecasts (horizons up to ~6 hours)
- **Every hour**: update day-ahead forecasts
- **Every 6 hours**: update multi-day forecasts (aligned with major weather model runs)

OpenSTEF does not enforce a particular scheduling cadence—as a library, it leaves orchestration to your infrastructure. You call the ``predict`` method whenever you need a new forecast.

How Short-Term Differs from Long-Term Forecasting
--------------------------------------------------

The table below summarizes the key differences:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Aspect
     - Short-term (minutes to days)
     - Long-term (months to years)
   * - Primary drivers
     - Weather, time-of-day, recent load
     - Economic growth, policy, infrastructure
   * - Update frequency
     - Minutes to hours
     - Monthly or quarterly
   * - Resolution
     - 15-min to hourly
     - Monthly or annual peaks
   * - Accuracy needs
     - Tight (MWh-level)
     - Broad (capacity planning ranges)
   * - Uncertainty handling
     - Quantile forecasts, prediction intervals
     - Scenario analysis
   * - Typical models
     - Gradient boosting, neural networks
     - Regression, trend extrapolation

OpenSTEF focuses exclusively on the short-term domain. Its model architectures, feature engineering, and evaluation metrics are all designed for this regime.

The Forecasting Pipeline at a Glance
-------------------------------------

A typical short-term forecasting workflow in OpenSTEF follows this sequence:

.. note:: [DIAGRAM: Linear pipeline showing Data Collection → Feature Engineering → Model Training → Prediction → Post-processing → Output forecasts, with a feedback loop from evaluation back to training]

1. **Data collection**: Gather historical load/generation data, weather forecasts, and calendar information into a ``TimeSeriesDataset``.

2. **Feature engineering**: Add derived features—lag values, wind power curves, atmospheric variables, and radiation-based features. See :doc:`feature_engineering` for details.

3. **Model training**: Fit a ``ForecastingModel`` on historical data. The model wraps preprocessing, a forecaster, and postprocessing into a single pipeline.

4. **Prediction**: Call ``predict()`` with recent data to generate forecasts at the configured horizons.

5. **Post-processing**: Apply confidence intervals and quantile estimates. See :doc:`quantiles_and_confidence` for how probabilistic forecasts work.

Here is a minimal example showing the training and prediction flow:

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.preprocessing import TransformPipeline

   # Build the model with your chosen components
   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=preprocessing_steps),
       forecaster=forecaster,
       postprocessing=TransformPipeline(transforms=postprocessing_steps),
       target_column="load",
       cutoff_history=cutoff_history,
   )

   # Train on historical data
   fit_result = model.fit(data=training_data)

   # Generate forecasts
   forecasts = model.predict(data=recent_data)

.. note::

   The ``cutoff_history`` parameter is important when using lag-based features. For example, if your preprocessing includes a 14-day lag, the first 14 days of training data will contain NaN values. Set ``cutoff_history`` accordingly to exclude these incomplete rows.

For guidance on choosing the right forecaster for your use case, see :doc:`model_selection`. For strategies to keep your forecasting system reliable in production, see :doc:`reliability_and_fallback`.

Practical Considerations
------------------------

**Start simple, then refine.** Begin with a single horizon (e.g., day-ahead) and a standard model like XGBoost. Once your pipeline is working end-to-end, add more horizons and experiment with feature engineering.

**Match your resolution to your use case.** 15-minute resolution is standard for grid operations in many European markets, but hourly resolution may suffice for day-ahead trading. Higher resolution means more data and longer training times.

**Weather forecast quality dominates beyond a few hours.** For horizons longer than about 4–6 hours, the accuracy of your weather input data matters more than the choice of ML model. Invest in good weather forecast sources before tuning hyperparameters.

**Evaluate at each horizon separately.** A model that performs well at the 1-hour horizon may struggle at 24 hours, and vice versa. OpenSTEF supports multi-horizon training and evaluation so you can assess performance across the full range of lead times.

Further Reading
---------------

- :doc:`feature_engineering` — Weather, calendar, and lag features that drive forecast accuracy
- :doc:`quantiles_and_confidence` — Probabilistic forecasts and prediction intervals
- :doc:`model_selection` — Comparing available model types and choosing the right one
- :doc:`reliability_and_fallback` — Fallback strategies for production systems