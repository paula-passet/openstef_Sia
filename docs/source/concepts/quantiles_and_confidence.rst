Quantiles and Confidence Intervals
===================================

Short-term energy forecasting is not just about predicting a single number. Grid operators, traders, and asset managers need to know *how confident* a model is in its prediction — and that confidence varies by hour, season, and how far ahead you are looking. OpenSTEF expresses this uncertainty through **probabilistic forecasts**: instead of one point estimate, the library produces a range of quantile predictions that together describe the full distribution of likely outcomes.

This page explains what quantiles are, how OpenSTEF generates and represents them, and how to use them in practice. For background on the forecasting process itself, see :doc:`forecasting_basics`. For information on what happens when a model cannot produce a reliable forecast at all, see :doc:`reliability_and_fallback`.

.. note:: [DIAGRAM: A time-series chart showing a central P50 forecast line with progressively wider shaded bands for P30–P70 (dark) and P10–P90 (light), illustrating how uncertainty widens with forecast horizon.]

What Is a Quantile Forecast?
-----------------------------

A **quantile** at level *q* is a threshold value such that the model believes the true outcome will fall below that value with probability *q*. In energy forecasting:

- **P10** (10th percentile) — the model expects actual load to exceed this value 90 % of the time. It represents a low-load scenario.
- **P50** (50th percentile, the median) — the model's best single-number estimate. Half of outcomes are expected to fall above and half below.
- **P90** (90th percentile) — the model expects actual load to fall below this value 90 % of the time. It represents a high-load scenario.

Together, P10 and P90 form a **prediction interval** that should contain the true value 80 % of the time. Narrower intervals mean the model is confident; wider intervals signal high uncertainty.

OpenSTEF uses the ``Quantile`` type from ``openstef_core.types`` to represent these levels throughout the library. A typical configuration includes seven quantiles to give a detailed picture of the distribution:

.. code-block:: python

   from openstef_core.types import Quantile

   PREDICTION_QUANTILES = [
       Quantile(0.05),
       Quantile(0.10),
       Quantile(0.30),
       Quantile(0.50),
       Quantile(0.70),
       Quantile(0.90),
       Quantile(0.95),
   ]

The resulting forecast dataset will contain columns named ``quantile_P05``, ``quantile_P10``, …, ``quantile_P95``.

Confidence Intervals vs. Prediction Intervals
----------------------------------------------

These two terms are often used interchangeably in practice, but they mean different things:

- A **prediction interval** covers where the *next individual observation* is expected to fall. This is what OpenSTEF produces: a range that should contain the actual measured load with a stated probability.
- A **confidence interval** covers where the *model's mean estimate* lies. It reflects uncertainty about the model parameters, not about future observations.

For operational use — deciding whether to dispatch a reserve, schedule a battery, or flag a congestion risk — prediction intervals are almost always what you want. OpenSTEF's ``ConfidenceIntervalApplicator`` is named for historical reasons but produces prediction intervals in the statistical sense.

How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF uses two complementary mechanisms to attach quantile predictions to a point forecast.

**Hour-specific uncertainty learning**

The ``ConfidenceIntervalApplicator`` transform learns from validation errors. During fitting it computes the standard deviation of forecast errors for each hour of the day (0–23). At prediction time it looks up the appropriate standard deviation for each forecast timestamp and converts it to quantiles by assuming normally distributed errors:

.. code-block:: python

   # quantile_value = median + z_score * std
   # e.g. P10 = median - 1.28 * std
   #      P90 = median + 1.28 * std

For multi-horizon forecasts, uncertainty grows with lead time. The applicator interpolates standard deviations using an exponential saturation curve:

.. code-block:: python

   # sigma(t) = a * (1 - exp(-t / tau)) + b
   # where t is hours ahead, tau = far_horizon / 4

This reflects the physical reality that uncertainty grows quickly in the first few hours and then levels off as the forecast approaches climatological variability.

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # fit expects a (validation_data, validation_predictions) tuple
   applicator.fit((validation_data, validation_predictions))

   # transform adds quantile_P10, quantile_P50, quantile_P90 columns
   probabilistic_forecast = applicator.transform((input_data, point_predictions))
   print(probabilistic_forecast.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

**Isotonic quantile calibration**

After the initial quantile estimates are produced, the ``IsotonicQuantileCalibrator`` can correct systematic biases using isotonic regression. This is particularly useful when the normality assumption of the ``ConfidenceIntervalApplicator`` does not hold perfectly — for example, during extreme weather events or periods of unusual demand.

Configuring Quantiles in a Workflow
-------------------------------------

When using the high-level ``ForecastingWorkflowConfig``, you declare the desired quantiles once and the library handles the rest:

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.config import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_id="substation_amsterdam_west",
       model="gblinear",
       horizons=[LeadTime.from_string("P2D")],
       quantiles=[
           Quantile(0.05),
           Quantile(0.10),
           Quantile(0.30),
           Quantile(0.50),
           Quantile(0.70),
           Quantile(0.90),
           Quantile(0.95),
       ],
   )

The workflow trains the model, fits the ``ConfidenceIntervalApplicator`` on the validation split, and ensures every call to ``predict`` returns a ``ForecastDataset`` with all requested quantile columns populated.

Visualising Probabilistic Forecasts
-------------------------------------

OpenSTEF ships with built-in plotting utilities so you do not need to reach for matplotlib or plotly directly.

**Time-series view**

``ForecastTimeSeriesPlotter`` renders the median forecast as a line and the quantile bands as shaded areas. Darker shading corresponds to higher-confidence inner bands (e.g., P30–P70); lighter shading shows the outer bands (P10–P90 or P05–P95).

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=forecast_dataset.data["load"])
       .add_model(
           model_name="GBLinear",
           forecast=forecast.median_series,      # P50 line
           quantiles=forecast.quantiles_data,    # shaded bands
       )
       .plot(title="Load Forecast with Uncertainty Bands")
   )
   fig.show()

.. note:: [DIAGRAM: Screenshot of ForecastTimeSeriesPlotter output — a Plotly interactive chart with a blue measurement line, an orange P50 forecast line, and two shaded bands representing P30–P70 and P10–P90.]

**Calibration view**

A well-formed 90 % prediction interval should contain the true value exactly 90 % of the time. If it contains the true value only 70 % of the time, the model is *overconfident*; if it contains it 98 % of the time, the model is *underconfident* (intervals are too wide). The ``QuantileProbabilityPlotter`` makes this easy to diagnose:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter

   fig = QuantileProbabilityPlotter().plot(
       observed_probs=evaluation_report.observed_probabilities,
       forecasted_probs=evaluation_report.forecasted_probabilities,
   )
   fig.show()

The resulting chart plots observed frequency against forecasted probability for each quantile level. A perfectly calibrated model produces points along the diagonal. Systematic deviation above the diagonal means the intervals are too wide; deviation below means they are too narrow.

.. note:: [DIAGRAM: Calibration scatter plot — x-axis "Forecasted probability", y-axis "Observed frequency", with a dashed diagonal reference line and model-specific scatter points.]

Why Quantiles Matter for Operations
--------------------------------------

Point forecasts answer "what do we expect?" Quantile forecasts answer "what should we prepare for?" The distinction is critical in several operational contexts:

- **Reserve scheduling** — a transmission system operator sizing spinning reserve needs to know the P90 upward deviation, not just the median. Using only the median systematically under-provisions reserve.
- **Congestion management** — a distribution operator deciding whether to issue a congestion warning benefits from knowing the probability that load exceeds a cable's thermal limit, which can be read directly from the quantile distribution.
- **Battery dispatch** — an energy storage operator maximising revenue needs to know the spread of likely prices or loads to decide when to charge and discharge. A narrow P10–P90 band justifies an aggressive dispatch strategy; a wide band calls for caution.
- **Imbalance cost reduction** — in markets where imbalance is penalised, a trader can use the asymmetry between P10 and P90 to bias their nomination in the direction that minimises expected penalty.

In each case, the value of the probabilistic forecast comes from its *calibration*: the stated probabilities must match observed frequencies. An uncalibrated 90 % interval that actually contains the true value only 60 % of the time is worse than useless — it creates false confidence. Use the ``QuantileProbabilityPlotter`` regularly as part of your model evaluation workflow to verify that calibration is maintained over time.

.. note::

   Calibration can degrade silently. Structural changes in the grid — new large consumers, solar installations, demand-response programmes — shift the error distribution that the ``ConfidenceIntervalApplicator`` learned during training. Periodic retraining is essential. See :doc:`reliability_and_fallback` for strategies to detect and respond to model degradation.

Summary
--------

- OpenSTEF produces **probabilistic forecasts** as a set of quantile columns (e.g., ``quantile_P10`` through ``quantile_P90``) alongside the median prediction.
- Quantiles are generated by the ``ConfidenceIntervalApplicator``, which learns hour-specific uncertainty from validation errors and applies exponential-decay interpolation across forecast horizons.
- The ``QuantileProbabilityPlotter`` and ``ForecastTimeSeriesPlotter`` provide built-in tools for visualising and validating probabilistic output.
- Operational value depends entirely on calibration: stated probabilities must match observed frequencies.