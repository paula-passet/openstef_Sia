Quantiles and Confidence Intervals
===================================

Probabilistic forecasting is central to how OpenSTEF communicates uncertainty. Rather than producing a single number, a probabilistic forecast expresses a *range* of plausible outcomes, each associated with a probability. This page explains what quantile forecasts are, how OpenSTEF constructs them, and why they matter for grid operations.

For background on the forecasting process itself, see :doc:`forecasting_basics`. For details on the models that produce these outputs, see :doc:`model_selection`.

What Is a Quantile Forecast?
-----------------------------

A **quantile** is a threshold value below which a given fraction of outcomes are expected to fall. In energy forecasting, three quantiles are used most often:

- **P10** (the 10th percentile) — the forecast is expected to exceed this value 90% of the time. It represents a low-load or low-generation scenario.
- **P50** (the 50th percentile, or median) — the central estimate. Half of all outcomes are expected to fall above and half below this value.
- **P90** (the 90th percentile) — the forecast is expected to stay below this value 90% of the time. It represents a high-load or high-generation scenario.

Together, P10 and P90 form a **prediction interval** that covers 80% of expected outcomes. The width of this band is a direct measure of forecast uncertainty: a narrow band means the model is confident; a wide band signals high variability in the underlying conditions.

.. note:: [DIAGRAM: Time-series plot showing 24–48 hours of forecasted load. Three shaded bands represent the P10–P90 prediction interval (light shading), the P25–P75 interquartile range (medium shading), and the P50 median forecast (solid line). Actual measured load is overlaid as a dashed line. Annotations highlight moments where actuals fall outside the P10–P90 band (a calibration failure) and periods where the band widens due to uncertain weather inputs.]

Confidence Intervals vs. Prediction Intervals
----------------------------------------------

These two terms are often used interchangeably in practice, but they mean different things:

- A **confidence interval** describes uncertainty about a *model parameter* — for example, the true mean load at a given hour. It narrows as you collect more data.
- A **prediction interval** describes uncertainty about a *single future observation*. Even with a perfect model and infinite data, a prediction interval remains wide because individual outcomes are inherently variable.

OpenSTEF produces **prediction intervals**, not confidence intervals. The P10–P90 band tells you where the next observed value is likely to land, not where the model's internal estimate of the mean sits. This distinction matters operationally: grid operators need to know whether the *actual* load will fit within a safe operating range, not whether the model's average estimate is accurate.

How OpenSTEF Builds Quantile Forecasts
----------------------------------------

OpenSTEF uses the :class:`~openstef_models.transforms.postprocessing.confidence_interval_applicator.ConfidenceIntervalApplicator` transform to attach quantile bands to a point forecast. The process has two phases:

**Fitting (learning uncertainty from history)**

During training, the applicator computes forecast errors on a held-out validation set and groups them by hour of day (0–23). For each hour it calculates the standard deviation of the errors. When multi-horizon forecasts are involved, a separate standard deviation is stored per forecast horizon.

**Transforming (applying uncertainty to new forecasts)**

At inference time, the applicator looks up the appropriate standard deviation for each prediction timestamp and converts it into quantile values by assuming normally distributed errors:

.. code-block:: python

    # P10 = median - 1.28 * std
    # P90 = median + 1.28 * std

For multi-horizon forecasts, uncertainty is not constant — it grows quickly in the first few hours ahead and then levels off. OpenSTEF models this with an exponential decay function:

.. math::

    \sigma(t) = a \cdot (1 - e^{-t/\tau}) + b

where *t* is hours ahead and *τ = far\_horizon / 4*. This captures the intuitive pattern that a one-hour-ahead forecast is far more certain than a 24-hour-ahead forecast, but the marginal increase in uncertainty diminishes over time.

Using the ConfidenceIntervalApplicator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.types import Quantile
    from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
        ConfidenceIntervalApplicator,
    )

    # Define the quantiles you want in your output
    applicator = ConfidenceIntervalApplicator(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
    )

    # Fit on validation data: learn hour-specific uncertainty
    # validation_data and validation_predictions are ForecastDataset objects
    applicator.fit((validation_data, validation_predictions))

    # Apply to new forecasts: adds quantile_P10, quantile_P50, quantile_P90 columns
    result = applicator.transform((new_input_data, new_predictions))

    # The result dataset now carries probabilistic columns
    print(result.data.columns.tolist())
    # ['quantile_P10', 'quantile_P50', 'quantile_P90']

The output ``ForecastDataset`` contains one column per requested quantile, named using the ``quantile_P{nn}`` convention (e.g., ``quantile_P10``, ``quantile_P50``, ``quantile_P90``). The ordering guarantee ``P10 ≤ P50 ≤ P90`` is enforced by the transform.

.. note::

   The applicator assumes that forecast errors follow a normal distribution. This assumption holds well for aggregated energy loads but may be less accurate for highly intermittent sources such as small-scale solar. Validation data must span multiple days to produce reliable hourly statistics.

Calibration: Are the Quantiles Trustworthy?
--------------------------------------------

A quantile forecast is **calibrated** when the stated probabilities match observed frequencies. If your P90 forecast is well-calibrated, actual load should exceed it roughly 10% of the time — no more, no less. Systematic over- or under-coverage indicates that the model is mis-estimating uncertainty.

OpenSTEF provides the :class:`~openstef_beam.analysis.plots.quantile_probability_plotter.QuantileProbabilityPlotter` for visualising calibration. It compares the *forecasted* probability of exceedance against the *observed* frequency, producing a reliability diagram:

.. code-block:: python

    from openstef_beam.analysis.plots.quantile_probability_plotter import (
        QuantileProbabilityPlotter,
    )
    import pandas as pd
    from openstef_core.types import Quantile

    plotter = QuantileProbabilityPlotter()

    # observed_probs: fraction of actuals that fell below each quantile threshold
    # forecasted_probs: the nominal quantile levels [0.1, 0.5, 0.9, ...]
    fig = plotter.plot(
        observed_probs=observed_probs,
        forecasted_probs=forecasted_probs,
    )
    fig.show()

A perfectly calibrated model produces a diagonal line on this chart. Points above the diagonal mean the model is *overconfident* (intervals are too narrow); points below mean it is *underconfident* (intervals are unnecessarily wide).

Why Quantiles Matter for Grid Operations
-----------------------------------------

A point forecast tells an operator what load to *expect*. A quantile forecast tells them what load to *prepare for*. This distinction drives several operational decisions:

**Reserve capacity planning**
Grid operators use the P90 forecast to size upward reserves. If the P90 load is 450 MW, they need sufficient generation headroom to cover that scenario even when the median forecast is only 420 MW.

**Congestion risk assessment**
Transmission constraints are binary: a line is either within limits or it is not. The probability that load exceeds a thermal limit can be read directly from the quantile forecast — if the P90 is below the limit, the risk of congestion is below 10%.

**Renewable integration**
Solar and wind generation are highly variable. Quantile forecasts for net load (demand minus renewables) allow operators to plan for both surplus and deficit scenarios simultaneously, rather than committing to a single deterministic trajectory.

**Communicating uncertainty to stakeholders**
A confidence band is far more informative than a point estimate when briefing decision-makers. The width of the P10–P90 interval is an immediately interpretable signal: "we are less certain today than yesterday."

Interpreting Forecast Width Over Time
---------------------------------------

The width of the prediction interval is not constant. Several factors cause it to vary:

- **Forecast horizon**: Uncertainty grows with lead time. A 1-hour-ahead forecast is much tighter than a 48-hour-ahead forecast, reflecting the exponential decay model described above.
- **Time of day**: Some hours are inherently more predictable than others. Morning ramp periods and evening peaks tend to have higher variance than stable overnight periods.
- **Weather uncertainty**: When the input weather forecast itself is uncertain (e.g., cloud cover near a solar installation), the load forecast uncertainty propagates and widens the quantile bands.

Operators should treat a sudden widening of the prediction interval as a signal to increase situational awareness, even if the median forecast looks unremarkable.

.. note::

   For information on what happens when a model fails to produce a forecast at all — and how OpenSTEF falls back gracefully — see :doc:`reliability_and_fallback`.