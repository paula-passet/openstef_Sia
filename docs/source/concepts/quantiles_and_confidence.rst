Quantiles and Confidence Intervals
===================================

Probabilistic forecasting is one of OpenSTEF's most operationally valuable capabilities. Rather than producing a single point estimate of future energy load, OpenSTEF generates a *distribution* of plausible outcomes expressed as quantiles. This page explains what quantiles are, how OpenSTEF represents them, how to interpret prediction intervals, and why this matters for real-world grid operations.

For background on how forecasts are generated in the first place, see :doc:`forecasting_basics`. For information on what happens when a model cannot produce a reliable forecast, see :doc:`reliability_and_fallback`.

What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What value will not be exceeded with probability p?"* The 90th percentile (P90) of a load forecast, for example, means there is a 90% probability that the actual load will fall at or below that value. Equivalently, there is only a 10% chance the actual load will exceed it.

OpenSTEF produces forecasts at three standard quantile levels:

- **P10** (``quantile_P10``) — the 10th percentile, a lower bound. Actual load will exceed this value 90% of the time.
- **P50** (``quantile_P50``) — the median forecast. This is the central estimate, not the mean.
- **P90** (``quantile_P90``) — the 90th percentile, an upper bound. Actual load will fall below this value 90% of the time.

Together, P10 and P90 form an **80% prediction interval**: the band within which you expect the actual outcome to land 80% of the time. The P50 sits in the middle as the best single-point estimate.

.. note::

   .. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd

How OpenSTEF Represents Quantiles
-----------------------------------

The output of an OpenSTEF forecast is a ``ForecastDataset``. Its underlying DataFrame contains one column per quantile, named using the convention ``quantile_P<percentile>``. A typical forecast DataFrame looks like this:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import ForecastDataset

   # Example: inspect the structure of a ForecastDataset
   data = pd.DataFrame(
       {
           "quantile_P10": [92.0, 95.5, 88.0],
           "quantile_P50": [100.0, 104.0, 97.0],
           "quantile_P90": [108.0, 113.5, 106.5],
       },
       index=pd.date_range("2025-06-01 08:00", periods=3, freq="h"),
   )

   forecast = ForecastDataset(data, sample_interval=timedelta(hours=1))

   # Inspect available quantiles
   print(forecast.quantiles)   # [0.1, 0.5, 0.9]

   # Access the median series directly
   print(forecast.median_series.head())

   # Access all quantile columns at once
   print(forecast.quantiles_data.head())

The ``ForecastDataset`` exposes convenience properties — ``median_series`` for the P50 and ``quantiles_data`` for the full quantile DataFrame — so you rarely need to slice columns by hand.

How Quantiles Are Learned
--------------------------

OpenSTEF does not simply add a fixed margin around the point forecast. Instead, it learns uncertainty from historical validation errors using the ``ConfidenceIntervalApplicator``. The process works in two phases:

1. **Fit phase**: For each hour of the day (0–23), the applicator computes the standard deviation of past forecast errors on held-out validation data. For multi-horizon forecasts, a separate standard deviation is stored per forecast horizon, capturing the well-known effect that uncertainty grows as the horizon extends.

2. **Transform phase**: At inference time, the learned hour- and horizon-specific standard deviations are used to place the quantile bands symmetrically around the P50 prediction, assuming a Gaussian error distribution.

After this initial placement, an ``IsotonicQuantileCalibrator`` can further refine the quantile estimates using isotonic regression, correcting for any systematic over- or under-confidence that the Gaussian assumption may introduce.

.. note::

   Uncertainty is not uniform across the day. Load forecasts are typically more uncertain during morning ramp-up and evening peak hours than during stable overnight periods. The hour-specific standard deviations capture this structure automatically.

Confidence Intervals vs. Prediction Intervals
-----------------------------------------------

These two terms are often used interchangeably in practice, but they mean different things:

- A **confidence interval** quantifies uncertainty about a *model parameter* (e.g., the true mean load at a given hour). It is a statement about the model, not about a single future observation.
- A **prediction interval** quantifies uncertainty about a *single future observation*. It must be wider than a confidence interval because it accounts for both model uncertainty and the inherent randomness of the outcome.

OpenSTEF's P10–P90 band is a **prediction interval**. When you see the shaded region on a forecast chart, it is telling you where a single future measurement is likely to fall — not where the average of many measurements would fall. This distinction matters when sizing reserves or setting operational thresholds.

Visualizing Probabilistic Forecasts
-------------------------------------

OpenSTEF ships with built-in plotting utilities in ``openstef_beam.analysis.plots``. The ``ForecastTimeSeriesPlotter`` renders an interactive Plotly figure with the median forecast, the shaded prediction interval, and actual measurements overlaid:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=forecast_dataset.data["load"])
       .add_model(
           model_name="GBLinear",
           forecast=forecast.median_series,       # P50 line
           quantiles=forecast.quantiles_data,     # P10–P90 shaded band
       )
       .plot()
   )

   fig.update_layout(
       title="Energy Load Forecast with Prediction Interval",
       yaxis_title="Load (MW)",
   )
   fig.show()

.. note::

   .. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_2.mmd

Checking Calibration
---------------------

A prediction interval is only useful if it is *calibrated* — that is, if the 80% interval actually contains the true value 80% of the time. OpenSTEF provides two dedicated plotters for calibration validation.

The ``QuantileProbabilityPlotter`` creates a scatter plot of forecasted probability vs. observed frequency. A perfectly calibrated model produces points that lie on the diagonal. Points above the diagonal indicate the model is over-confident (intervals are too narrow); points below indicate under-confidence (intervals are too wide).

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter
   from openstef_core.types import Quantile

   plotter = QuantileProbabilityPlotter()
   fig = plotter.plot(
       forecasts={"GBLinear": forecast},
       actuals=actuals_series,
   )
   fig.show()

The ``QuantileCalibrationBoxPlotter`` extends this to multiple targets, showing the *distribution* of calibration errors per quantile level as box plots. Well-calibrated forecasts produce boxes centered near zero with tight spreads.

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileCalibrationBoxPlotter

   plotter = QuantileCalibrationBoxPlotter()
   fig = plotter.plot(
       forecasts_per_target={"SubstationA": forecast_a, "SubstationB": forecast_b},
       actuals_per_target={"SubstationA": actuals_a, "SubstationB": actuals_b},
   )
   fig.show()

.. note::

   .. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_3.mmd

Why Quantiles Matter for Operations
-------------------------------------

Point forecasts answer "what will the load be?" Quantile forecasts answer "what range should I plan for?" This distinction has direct operational consequences:

**Reserve sizing**
   Grid operators must hold spinning reserves to cover unexpected demand spikes. Using P90 rather than P50 as the planning value ensures reserves are sufficient even in high-demand scenarios, without over-procuring based on worst-case assumptions.

**Congestion management**
   When a line is near its thermal limit, the P90 forecast tells operators the probability that the limit will be breached. A P90 value below the limit provides much stronger assurance than a P50 value below the limit.

**Imbalance cost reduction**
   Energy traders use the full quantile distribution to optimise bid strategies. Bidding at P50 minimises expected imbalance volume; bidding at a higher quantile shifts the risk profile toward avoiding costly short positions.

**Anomaly detection**
   When an actual measurement falls outside the P10–P90 band, that is a statistically meaningful signal — not just noise. Operators can use interval violations as triggers for investigation, rather than reacting to every deviation from the point forecast.

.. note::

   The value of a probabilistic forecast degrades quickly if it is poorly calibrated. Always validate calibration on held-out data before using quantile outputs for operational decisions. See the calibration plotting examples above.