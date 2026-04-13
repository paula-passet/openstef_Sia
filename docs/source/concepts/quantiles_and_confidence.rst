Quantiles and Confidence in Probabilistic Forecasts
====================================================

Short-term energy forecasting rarely benefits from a single predicted value. Grid operators, traders, and asset managers all need to know not just *what* load or generation is expected, but *how certain* that expectation is. OpenSTEF addresses this through **probabilistic forecasting**: instead of one number per time step, the library produces a distribution of outcomes expressed as quantile forecasts.

This page explains what quantiles are, how OpenSTEF computes and represents them, how to interpret confidence bands, and how probabilistic outputs translate into better operational decisions.

.. note::

   This page focuses on uncertainty quantification. For an introduction to the
   forecasting workflow itself, see :doc:`forecasting_basics`. For guidance on
   which model to choose, see :doc:`model_selection`.


What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"Below what value will the actual outcome fall X% of the time?"*

- **P10** (10th percentile) — the actual outcome is expected to be *above* this value 90% of the time. It represents a low-load or low-generation scenario.
- **P50** (50th percentile) — the median forecast. Half of outcomes are expected above, half below. This is the central estimate.
- **P90** (90th percentile) — the actual outcome is expected to be *below* this value 90% of the time. It represents a high-load or high-generation scenario.

Together, P10 and P90 form a **prediction interval** that should contain the true outcome roughly 80% of the time. The width of this band is a direct measure of forecast uncertainty: a narrow band means the model is confident; a wide band signals high uncertainty, perhaps due to volatile weather or an unusual demand pattern.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd


How OpenSTEF Computes Quantiles
--------------------------------

OpenSTEF generates quantile forecasts through a post-processing step applied after the point forecast is produced. The core component is the ``ConfidenceIntervalApplicator``, which learns **hour-specific uncertainty** from historical validation errors and then converts that uncertainty into quantile values.

The process has two phases:

1. **Fit phase** — the applicator computes the standard deviation of validation errors for each hour of the day (hours 0–23). For multi-horizon forecasts it stores a separate standard deviation per horizon, capturing the fact that uncertainty grows as the forecast looks further ahead.

2. **Transform phase** — for each prediction, the applicator looks up the appropriate standard deviation (interpolating across horizons using exponential decay) and derives quantile values by assuming a normal distribution:

   .. code-block:: python

      # Internally: quantile_value = median + z_score * std
      # e.g. P10 = median - 1.28 * std
      #      P90 = median + 1.28 * std

The exponential decay model for multi-horizon uncertainty follows:

.. code-block:: text

   sigma(t) = a * (1 - exp(-t / tau)) + b

where ``t`` is hours ahead and ``tau = far_horizon / 4``. This reflects a well-known pattern in energy forecasting: uncertainty grows quickly in the first few hours and then levels off as the dominant source of error (weather uncertainty) saturates.

After the quantiles are generated, the ``IsotonicQuantileCalibrator`` can optionally recalibrate them using isotonic regression to ensure that stated probabilities match observed frequencies. The ``QuantileSorter`` enforces monotonic ordering (P10 ≤ P25 ≤ P50 ≤ P75 ≤ P90) to prevent quantile crossing, which can otherwise occur when quantiles are estimated independently.


The Output Format
------------------

A completed probabilistic forecast is represented as a ``ForecastDataset``. Its underlying ``DataFrame`` contains one column per quantile, named using the convention ``quantile_P<percentile>``:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import ForecastDataset

   # Example: a ForecastDataset with three quantile columns
   data = pd.DataFrame(
       {
           "load": [105.0, 112.0],          # actual / target (if available)
           "quantile_P10": [88.0, 94.0],
           "quantile_P50": [100.0, 110.0],
           "quantile_P90": [115.0, 125.0],
       },
       index=pd.date_range("2025-06-01", periods=2, freq="h"),
   )

   dataset = ForecastDataset(data, sample_interval=timedelta(hours=1))

   # Convenient accessors on ForecastDataset
   print(dataset.quantiles)          # [0.1, 0.5, 0.9]
   print(dataset.median_series)      # pd.Series of P50 values
   print(dataset.quantiles_data)     # DataFrame of all quantile columns

The ``ForecastDataset`` exposes several properties that make it straightforward to extract exactly the slice you need without manually parsing column names:

- ``median_series`` — the P50 point forecast as a ``pd.Series``
- ``quantiles_data`` — a ``DataFrame`` containing only the quantile columns
- ``filter_quantiles(quantiles)`` — returns a new ``ForecastDataset`` restricted to a chosen subset of quantiles
- ``standard_deviation_series`` — the per-step standard deviation, if stored


Confidence Intervals vs. Prediction Intervals
----------------------------------------------

These two terms are often confused in practice. In the context of OpenSTEF's output:

- A **prediction interval** (e.g., P10–P90) describes the range within which a *single future observation* is expected to fall with a given probability. This is what OpenSTEF produces and what operators use day-to-day.
- A **confidence interval** in the statistical sense describes uncertainty about a *model parameter*, not about a future observation. This distinction matters when communicating results to stakeholders: the P10–P90 band does **not** mean "we are 80% confident the mean load will be in this range." It means "80% of individual hourly outcomes are expected to fall within this band."

.. note::

   OpenSTEF's documentation and codebase use the term "confidence interval" colloquially
   to refer to prediction intervals. When integrating with external systems or reporting
   to risk teams, be precise: these are **prediction intervals** on individual outcomes.


Calibration: Are the Quantiles Trustworthy?
--------------------------------------------

A probabilistic forecast is only useful if it is **calibrated** — meaning that events predicted to occur 10% of the time actually occur about 10% of the time. A P90 band that contains the actual outcome 99% of the time is over-confident in the wrong direction (too wide); one that contains it only 60% of the time is dangerously overconfident (too narrow).

OpenSTEF includes ``QuantileProbabilityPlotter`` in the ``openstef-beam`` analysis package, which produces calibration plots comparing predicted probabilities against observed frequencies. These plots directly answer:

- Are my 90% prediction intervals correct 90% of the time?
- Does the model over- or under-estimate uncertainty at specific hours of the day?
- Which model variant provides the most reliable uncertainty quantification?

.. code-block:: python

   from openstef_beam.analysis.plots.quantile_probability_plotter import (
       QuantileProbabilityPlotter,
   )

   plotter = QuantileProbabilityPlotter()

   # `forecast_df` is a DataFrame with quantile columns and an actuals column
   fig = plotter.plot(forecast_df)
   fig.show()

A well-calibrated model produces a calibration curve that lies close to the diagonal. Systematic deviations indicate that the ``IsotonicQuantileCalibrator`` should be (re-)fitted on more recent validation data.


Why Quantiles Matter for Grid Operations
-----------------------------------------

A point forecast tells an operator what to *expect*. Quantile forecasts tell them what to *prepare for*. Several operational decisions depend directly on the width and shape of the prediction interval:

**Congestion management**
   A transmission system operator scheduling redispatch actions needs to know whether peak load might exceed a line's thermal limit. Using P90 rather than P50 as the planning value adds a safety margin proportional to actual forecast uncertainty — not an arbitrary fixed buffer.

**Reserve capacity procurement**
   Balancing responsible parties size their upward and downward reserve bids based on forecast uncertainty. Narrow bands on a calm, predictable day allow smaller (cheaper) reserve positions; wide bands on a stormy day with high renewable variability justify larger positions.

**Risk-aware trading**
   Energy traders using OpenSTEF forecasts can construct asymmetric bid strategies: bid closer to P50 when the band is tight, shift toward P10 or P90 when uncertainty is high and the cost of imbalance is asymmetric.

**Anomaly detection**
   When a measured value falls outside the P10–P90 band, it is a strong signal that something unexpected has occurred — a sensor fault, an unplanned outage, or a demand event not captured by the model's features. See :doc:`reliability_and_fallback` for how OpenSTEF handles such situations.


Configuring Which Quantiles Are Produced
-----------------------------------------

The set of quantiles generated is configurable. A typical production setup uses five quantiles to balance resolution against storage cost:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   applicator = ConfidenceIntervalApplicator(
       quantiles=[
           Quantile(0.05),
           Quantile(0.10),
           Quantile(0.50),
           Quantile(0.90),
           Quantile(0.95),
       ]
   )

Requesting more quantiles increases the resolution of the forecast distribution but has no effect on model training — quantiles are derived analytically from the learned standard deviation, so adding quantiles is computationally cheap.

.. note::

   The ``QuantileSorter`` post-processor enforces that quantile columns are
   monotonically ordered at every time step. If you add custom quantiles, ensure
   they are passed consistently through the full post-processing pipeline so that
   the sorter can enforce the correct ordering constraint.


Summary
--------

Probabilistic forecasts expressed as quantiles are a first-class output of OpenSTEF. The P10–P50–P90 triplet (or any configurable set of quantiles) gives operators a complete picture of forecast uncertainty rather than a false sense of precision from a single number. OpenSTEF computes quantiles through a principled post-processing pipeline — learning hour-specific uncertainty from validation data, modelling its growth over the forecast horizon, and optionally recalibrating against observed outcomes — so that the stated probabilities are meaningful in practice.

For the feature inputs that drive forecast accuracy (and therefore band width), see :doc:`feature_engineering`. For strategies when the model itself is unavailable or degraded, see :doc:`reliability_and_fallback`.