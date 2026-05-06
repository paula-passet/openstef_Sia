Short-Term Forecasting Basics
=============================

This page explains what short-term energy forecasting is, why it matters for grid
operations, and how the key concepts of **horizons**, **lead times**, and **forecast
frequency** shape the way OpenSTEF models are configured and evaluated.

For probabilistic output (quantiles and confidence intervals), see
:doc:`quantiles_and_confidence`. For the features that drive forecast accuracy, see
:doc:`feature_engineering`.

What Is Short-Term Forecasting?
--------------------------------

Short-term energy forecasting predicts electricity load or generation over a window
ranging from a few minutes to a few days ahead. Unlike long-term forecasting — which
projects annual demand growth or capacity needs over years — short-term forecasting
operates at the resolution of grid control: every 15 minutes, every hour, or every
few hours.

The distinction matters because the two problems require fundamentally different
approaches:

- **Long-term forecasting** relies on economic models, demographic trends, and
  climate scenarios. Uncertainty is large and precision at any single timestamp is
  not the goal.
- **Short-term forecasting** relies on recent measurements, weather forecasts, and
  calendar patterns. Precision at each individual timestamp is critical because
  operators act on individual values.

OpenSTEF is designed exclusively for the short-term problem. Its data structures,
feature pipelines, and evaluation tooling all assume that forecasts are generated
repeatedly at high frequency and compared against real measurements shortly after.

Why Short-Term Forecasts Are Needed
-------------------------------------

Grid operators and energy traders need short-term forecasts for several overlapping
reasons:

- **Balancing supply and demand.** Electricity cannot be stored at scale. Operators
  must schedule generation and activate reserves based on expected load minutes to
  hours in advance.
- **Congestion management.** Distribution system operators (DSOs) need to know
  whether a cable or transformer will be overloaded in the next few hours so they
  can re-route flows or curtail loads.
- **Intraday trading.** Energy traders update positions on intraday markets using
  the latest forecasts. A forecast generated six hours ago may already be stale
  when weather conditions change.
- **Renewable integration.** Solar and wind output is highly variable. Short-term
  forecasts of net load (consumption minus local generation) are essential for
  managing the residual that must be covered by dispatchable sources.

Each of these use cases has a different tolerance for error and a different required
lead time, which is why OpenSTEF supports multiple simultaneous horizons rather than
a single fixed prediction window.

Horizons and Lead Times
------------------------

A **horizon** (also called a *lead time*) is the gap between the moment a forecast
is generated and the timestamp it predicts. A forecast made at 09:00 for 10:00 has
a one-hour horizon. The same forecast made at 06:00 for 10:00 has a four-hour
horizon.

In OpenSTEF, horizons are represented by the ``LeadTime`` type, which wraps a
``timedelta``. A single trained model can cover multiple horizons simultaneously,
or separate models can be trained per horizon depending on the forecaster type.

Common operational horizons in energy forecasting are:

- **15 minutes** — ultra-short, used for frequency regulation and real-time
  balancing. Relies almost entirely on recent measurements; weather has little
  influence at this scale.
- **1 hour** — short, used for intraday dispatch decisions. Weather forecasts begin
  to contribute meaningfully.
- **24 hours** — day-ahead, the most common planning horizon. Weather forecasts
  dominate; calendar features (day of week, holidays) are important.
- **48 hours** — extended day-ahead, used for unit commitment and maintenance
  scheduling. Forecast uncertainty is substantially higher.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

The ``available_at`` concept is central to how OpenSTEF tracks forecasts. Every
prediction carries a timestamp indicating *when it became available*, not just what
it predicts. This allows the evaluation pipeline to correctly measure accuracy as a
function of lead time — a 48-hour-ahead forecast should not be judged by the same
standard as a 15-minute-ahead forecast.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.models.forecasting.forecaster import LeadTime

    # Define the horizons your model should cover
    short_horizon  = LeadTime(timedelta(minutes=15))
    medium_horizon = LeadTime(timedelta(hours=1))
    day_ahead      = LeadTime(timedelta(hours=24))
    extended       = LeadTime(timedelta(hours=48))

    horizons = [short_horizon, medium_horizon, day_ahead, extended]

Forecast Frequency and the ``available_at`` Dimension
-------------------------------------------------------

Forecast **frequency** is how often a new forecast is generated, independent of
what it predicts. A system might generate a fresh 24-hour-ahead forecast every six
hours, updating as new weather model runs become available. The same system might
generate 15-minute-ahead forecasts every 15 minutes.

This creates a two-dimensional structure for any forecast dataset:

- The **target timestamp** — the moment being predicted.
- The **available_at timestamp** — when the forecast was published.

OpenSTEF's ``TimeSeriesDataset`` carries both dimensions explicitly. When you filter
or evaluate predictions, you can slice by either axis:

.. code-block:: python

    from openstef_models.data.time_series_dataset import TimeSeriesDataset

    # Load a dataset that contains predictions at multiple lead times
    dataset = TimeSeriesDataset.read_parquet("predictions.parquet")

    # Inspect which horizons are present
    print(dataset.horizons())

    # Select only the 24-hour-ahead predictions for analysis
    day_ahead_preds = dataset.select_horizon(LeadTime(timedelta(hours=24)))

    # Filter to predictions that were available before a specific cutoff
    from datetime import datetime, timezone
    cutoff = datetime(2024, 6, 1, 6, 0, tzinfo=timezone.utc)
    early_preds = dataset.filter_by_available_before(cutoff)

The separation between target time and available_at time also matters during
backtesting. The ``BacktestPipeline`` simulates realistic operational conditions by
generating forecasts at a configurable ``predict_interval`` (how often new forecasts
are issued) while retraining the model at a separate ``train_interval``:

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting.pipeline import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),  # resolution of output
        predict_interval=timedelta(hours=6),               # how often forecasts are issued
        train_interval=timedelta(days=7),                  # how often the model retrains
        align_time=time.fromisoformat("00:00+00"),
    )

Here ``prediction_sample_interval`` controls the granularity of each individual
forecast (one value every 15 minutes), while ``predict_interval`` controls how
often the whole forecast is regenerated. These are independent settings that reflect
real operational practice: a day-ahead forecast is typically issued once or twice
per day, but it covers 96 quarter-hourly intervals.

How Horizon Affects Model Design
----------------------------------

The choice of horizon is not just a configuration detail — it shapes which features
are useful and which model architectures are appropriate.

At very short horizons (under 30 minutes), the most recent measurement is by far
the strongest predictor. Autoregressive features — lags of the target variable —
dominate. Weather forecasts add little because conditions change slowly relative to
the prediction window.

At medium horizons (1–6 hours), weather forecasts become relevant, particularly for
solar irradiance and wind speed. Lag features remain useful but their predictive
power decays as the horizon grows.

At day-ahead and longer horizons, calendar structure (hour of day, day of week,
public holidays) and weather forecasts are the primary drivers. Lag features from
the same time of day on previous days (e.g., a 24-hour lag) are more informative
than short lags.

This is why OpenSTEF supports multi-horizon models: a single model trained across
multiple lead times can learn these horizon-dependent patterns jointly, rather than
requiring a separate model for each horizon. However, some model types — particularly
those sensitive to missing values or conditional features — are better suited to
single-horizon training. The ``ForecastingModel`` pipeline handles both cases
transparently.

.. note::

   The ``cutoff_history`` parameter in ``ForecastingModel`` is important when using
   lag-based features. A 14-day lag, for example, makes the first 14 days of
   training data unusable. Set ``cutoff_history`` to exclude these incomplete rows
   and avoid training on NaN-filled rows.

Evaluating Across Horizons
---------------------------

Because forecast skill degrades with lead time, evaluation results should always be
broken down by horizon. OpenSTEF's ``EvaluationPipeline`` does this automatically
when you configure multiple ``lead_times`` and ``available_ats``:

.. code-block:: python

    from openstef_models.evaluation.pipeline import EvaluationPipeline, EvaluationConfig
    from openstef_models.data.types import AvailableAt, LeadTime, Window
    from datetime import timedelta

    eval_config = EvaluationConfig(
        available_ats=[
            AvailableAt.from_string("D-1T06:00"),   # day-ahead forecast issued at 06:00
            AvailableAt.from_string("D-1T18:00"),   # updated forecast issued at 18:00
        ],
        lead_times=[
            LeadTime.from_string("PT1H"),
            LeadTime.from_string("PT24H"),
            LeadTime.from_string("PT48H"),
        ],
        windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
    )

Separating results by ``available_at`` and ``lead_time`` reveals whether accuracy
degrades gracefully with horizon (expected) or drops sharply at a particular lead
time (a signal that a feature or data source is missing for that window).

For a deeper look at how uncertainty is quantified across horizons using quantile
forecasts, see :doc:`quantiles_and_confidence`. For the features that matter most at
each horizon, see :doc:`feature_engineering`. For what happens when a forecast
cannot be generated at all, see :doc:`reliability_and_fallback`.