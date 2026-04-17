Quantiles and Confidence Intervals
===================================

Energy forecasting is inherently uncertain. A grid operator asking "how much load will this substation carry at 14:00 tomorrow?" deserves more than a single number — they need to know *how confident* the model is in that number. OpenSTEF addresses this through **probabilistic forecasting**: rather than producing one point estimate, the library generates a full set of quantile predictions that describe the likely range of outcomes.

This page explains what quantiles are, how OpenSTEF computes and represents them, and how to use them effectively in operational decision-making.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd

What Is a Quantile Forecast?
-----------------------------

A **quantile** is a threshold value below which a given fraction of outcomes are expected to fall. In the context of energy forecasting:

- The **P10 quantile** (10th percentile) means the model expects actual load to be *above* this value 90% of the time.
- The **P50 quantile** (50th percentile, the median) is the model's central estimate — actual load is equally likely to be above or below it.
- The **P90 quantile** (90th percentile) means the model expects actual load to be *below* this value 90% of the time.

Together, P10 and P90 form an **80% prediction interval**: the model asserts that 80% of future observations should fall within this band. Wider bands indicate greater uncertainty; narrower bands indicate higher confidence.

OpenSTEF uses the ``Quantile`` type from ``openstef_core.types`` to represent these values throughout the library. A standard set of quantiles used in practice looks like this:

.. code-block:: python

   from openstef_core.types import Quantile

   # A typical set of quantiles for probabilistic energy forecasting
   PREDICTION_QUANTILES = [
       Quantile(0.05),  # P05 — outer lower bound
       Quantile(0.10),  # P10 — inner lower bound
       Quantile(0.30),  # P30
       Quantile(0.50),  # P50 — median (central forecast)
       Quantile(0.70),  # P70
       Quantile(0.90),  # P90 — inner upper bound
       Quantile(0.95),  # P95 — outer upper bound
   ]

The resulting forecast columns in a ``ForecastDataset`` are named ``quantile_P05``, ``quantile_P10``, ..., ``quantile_P95``, following a consistent naming convention across the library.

How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF's ``ConfidenceIntervalApplicator`` is the core component responsible for turning a point forecast into a probabilistic one. It works in two phases:

**Fitting (learning uncertainty from validation data)**
   The applicator examines historical forecast errors on a validation set, computing the standard deviation of errors for each hour of the day (hours 0–23). For multi-horizon forecasts, it stores a separate standard deviation per horizon, capturing the well-known pattern that uncertainty grows with lead time.

**Transforming (applying uncertainty to new forecasts)**
   At prediction time, the applicator looks up the appropriate standard deviation for each forecast timestamp's hour and horizon. It then derives quantile values by assuming a normal distribution of errors:

   .. code-block:: text

      quantile_value = median + z_score × std
      e.g., P10 = median − 1.28 × std
            P90 = median + 1.28 × std

   For multi-horizon forecasts, the standard deviation is interpolated using an exponential decay model:

   .. code-block:: text

      σ(t) = a × (1 − exp(−t / τ)) + b

   where ``t`` is hours ahead and ``τ = far_horizon / 4``. This reflects the physical reality that uncertainty grows quickly in the near term and then levels off.

Here is how you use ``ConfidenceIntervalApplicator`` directly:

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   # Define the quantiles you want in the output
   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # Fit on validation data: learns hour-specific uncertainty
   applicator.fit(validation_forecast_dataset)

   # Transform new predictions: adds quantile_P10, quantile_P50, quantile_P90 columns
   probabilistic_forecast = applicator.transform(new_forecast_dataset)

   # Inspect the resulting columns
   print(probabilistic_forecast.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

.. note::

   The ``ConfidenceIntervalApplicator`` assumes normally distributed forecast errors. This assumption holds well for energy load forecasting but may not be appropriate for all domains or highly skewed distributions.

Prediction Intervals vs. Confidence Intervals
-----------------------------------------------

These two terms are often confused, and the distinction matters operationally:

- A **confidence interval** describes uncertainty about a *model parameter* — for example, how precisely the model has estimated the average load at a given hour. It narrows as you collect more training data.
- A **prediction interval** describes uncertainty about a *future individual observation* — it accounts for both model uncertainty and the inherent randomness in the system being forecast. It does not vanish with more data.

OpenSTEF produces **prediction intervals**. The P10–P90 band around a forecast tells you where a single future measurement is likely to land, not where the true mean lies. For grid operations, prediction intervals are the operationally relevant quantity: you need to know whether a *specific* 15-minute interval might exceed a cable's thermal limit, not whether the *average* load over many days will.

Calibration: Are the Intervals Trustworthy?
--------------------------------------------

A probabilistic forecast is only useful if it is **calibrated** — meaning that stated probabilities match observed frequencies. If a model claims P90 is the upper bound, then actual load should exceed that bound roughly 10% of the time. If it exceeds it 30% of the time, the intervals are too narrow (overconfident). If it exceeds it only 2% of the time, the intervals are too wide (underconfident).

OpenSTEF provides ``QuantileProbabilityPlotter`` to visualise calibration directly:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter
   from openstef_core.types import Quantile

   plotter = QuantileProbabilityPlotter()

   fig = plotter.plot(
       observed_probs=[Quantile(0.08), Quantile(0.28), Quantile(0.51), Quantile(0.72), Quantile(0.91)],
       forecasted_probs=[Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.7), Quantile(0.9)],
       model_name="GBLinear",
   )
   fig.show()

The resulting plot shows forecasted probabilities on the x-axis and observed frequencies on the y-axis. A perfectly calibrated model produces points along the diagonal. Systematic deviation above the diagonal means the model is underconfident (intervals too wide); deviation below means overconfident (intervals too narrow).

For evaluating calibration across many substations or targets simultaneously, ``QuantileCalibrationBoxPlotter`` shows the distribution of calibration errors per quantile level as boxplots:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileCalibrationBoxPlotter
   import pandas as pd
   from openstef_core.types import Quantile

   plotter = QuantileCalibrationBoxPlotter()

   # calibration_errors is a DataFrame with quantile levels as columns
   # and one row per target/substation
   fig = plotter.plot(calibration_errors_df)
   fig.show()

Well-calibrated forecasts produce boxplots centred near zero with tight distributions. Systematic offsets identify quantiles that need recalibration.

.. note::

   OpenSTEF also provides ``IsotonicQuantileCalibrator`` (in ``openstef_models.transforms.postprocessing``) to post-process and correct miscalibrated quantile outputs using isotonic regression.

Visualising Probabilistic Forecasts
-------------------------------------

The most direct way to communicate a probabilistic forecast is to plot the quantile bands as shaded areas around the median. OpenSTEF's ``ForecastTimeSeriesPlotter`` handles this out of the box:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=forecast_dataset.data["load"])
       .add_model(
           model_name="GBLinear",
           forecast=forecast.median_series,      # P50 central line
           quantiles=forecast.quantiles_data,    # shaded P10–P90 band
       )
       .plot()
   )

   fig.update_layout(
       title="Energy Load Forecast with Prediction Intervals",
       yaxis_title="Load (MW)",
   )
   fig.show()

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_2.mmd

The plotter layers traces in a deliberate order: quantile bands in the background, forecast lines in the middle, and actual measurements in the foreground, so that deviations from the forecast are immediately visible.

Why Quantiles Matter for Grid Operations
-----------------------------------------

A single point forecast forces operators to make implicit, unexamined assumptions about uncertainty. Quantile forecasts make those assumptions explicit and actionable:

- **Congestion management**: An operator can use P90 as a conservative upper bound when deciding whether to pre-emptively curtail generation or activate flexibility. Using P50 alone would underestimate risk half the time.
- **Reserve scheduling**: The width of the prediction interval directly informs how much balancing reserve to procure. Narrow intervals on a calm weekday require less reserve than wide intervals during a storm.
- **Alarm thresholds**: Rather than triggering an alarm when the point forecast exceeds a limit, operators can trigger when P70 or P90 exceeds the limit — tuning the false-alarm rate to operational tolerance.
- **Asymmetric costs**: In many grid situations, the cost of under-forecasting (unexpected overload) is much higher than over-forecasting. Quantiles let operators choose the percentile that minimises their specific cost function.

.. note::

   The choice of which quantile to act on is a business decision, not a modelling decision. OpenSTEF provides the full distribution; your operational logic determines which part of it to use.

Related Topics
---------------

- :doc:`forecasting_basics` — Introduction to short-term energy forecasting and how point forecasts are produced before quantiles are added.
- :doc:`feature_engineering` — How weather variables and other predictors influence both the central forecast and the width of prediction intervals.
- :doc:`reliability_and_fallback` — What happens to quantile outputs when a model fails and fallback strategies are activated.