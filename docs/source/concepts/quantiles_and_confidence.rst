Quantiles and Confidence in Probabilistic Forecasts
====================================================

Energy grid operators rarely need to know *only* the most likely load or generation value — they need to know the *range* of plausible outcomes. A single-point forecast that says "demand will be 450 MW at 09:00" gives no indication of whether the real outcome could just as easily be 420 MW or 480 MW. Probabilistic forecasts address this by expressing uncertainty explicitly, and OpenSTEF is designed from the ground up to produce them.

This page explains what quantile forecasts are, how OpenSTEF generates them, and how to interpret and use them in practice.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd


What Is a Quantile Forecast?
-----------------------------

A quantile forecast assigns a probability to the statement "the true value will be *at or below* this level." The most common quantiles in energy forecasting are:

- **P10 (10th percentile)** — there is a 10% chance the actual value falls at or below this level; it represents the low end of the expected range.
- **P50 (50th percentile, the median)** — the central estimate; actual outcomes are equally likely to be above or below this value.
- **P90 (90th percentile)** — there is a 90% chance the actual value falls at or below this level; it represents the high end of the expected range.

Together, P10 and P90 form an **80% prediction interval**: if the model is well-calibrated, roughly 80 out of every 100 actual observations should fall inside this band. Narrower intervals (e.g., P25–P75) express higher confidence; wider intervals (e.g., P05–P95) express lower confidence.

.. note::

   A **prediction interval** describes where future *observations* are expected to fall. This is different from a **confidence interval**, which describes uncertainty about a model *parameter* (such as the mean). In operational forecasting, prediction intervals are almost always what you want.


How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF uses the ``ConfidenceIntervalApplicator`` transform to attach quantile columns to a point forecast. The process has two stages:

**Fitting (learning uncertainty from history)**
   The applicator is trained on validation-set errors. For each hour of the day (0–23), it computes the standard deviation of forecast residuals. This captures the fact that uncertainty is typically higher during morning ramp-up hours than during stable overnight periods.

**Transforming (applying uncertainty to new forecasts)**
   At inference time, the learned per-hour standard deviation is looked up for each prediction timestamp. Assuming normally distributed errors, quantile values are derived as:

   .. code-block:: text

      quantile_value = median + z_score × σ_hour

   For example, P10 uses z = −1.28 and P90 uses z = +1.28, so the 80% interval is ±1.28 standard deviations around the median.

For multi-horizon forecasts (where uncertainty grows with lead time), the applicator interpolates standard deviations using an exponential saturation curve:

.. code-block:: text

   σ(t) = a × (1 − exp(−t / τ)) + b

Here *t* is hours ahead and *τ* = far_horizon / 4. This reflects the physical reality that forecast uncertainty grows quickly in the first few hours and then levels off as the dominant uncertainty sources (weather, demand patterns) become fully expressed.

A practical example of fitting and applying the confidence interval transform:

.. code-block:: python

   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )
   from openstef_core.types import Quantile

   # Define which quantiles you want in the output
   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # Fit on a (ForecastDataset, predictions) tuple from your validation set
   applicator.fit((validation_dataset, validation_predictions))

   # Apply to new data — output columns include quantile_P10, quantile_P50, quantile_P90
   result = applicator.transform((new_input_dataset, new_predictions))

   print(result.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

After transformation, each row in ``result.data`` carries a full probabilistic forecast. The ``quantile_P50`` column is the point estimate; the flanking columns bound the prediction interval.


Calibration: Are the Intervals Trustworthy?
--------------------------------------------

Generating quantile columns is only half the story — those quantiles must be *calibrated* to be useful. A well-calibrated P90 should be exceeded by actual observations roughly 10% of the time. If actuals exceed P90 only 2% of the time, the intervals are too wide (over-confident in uncertainty); if they exceed it 25% of the time, the intervals are too narrow (under-confident).

OpenSTEF provides ``QuantileProbabilityPlotter`` and ``QuantileProbabilityVisualization`` specifically for this diagnostic:

.. code-block:: python

   from openstef_beam.analysis.plots.quantile_probability_plotter import (
       QuantileProbabilityPlotter,
   )

   plotter = QuantileProbabilityPlotter()

   # observed_probs: fraction of actuals that fell below each quantile threshold
   # forecasted_probs: the nominal quantile levels [0.1, 0.5, 0.9, ...]
   fig = plotter.plot(
       observed_probs=observed_probs,
       forecasted_probs=forecasted_probs,
       title="P10/P50/P90 Calibration Check",
   )
   fig.show()

A perfectly calibrated model produces a diagonal line on this plot. Deviations reveal systematic bias in the uncertainty estimates — for example, a model that consistently underestimates night-time variability will show the observed curve bowing above the diagonal for low quantiles.

OpenSTEF also includes ``IsotonicQuantileCalibrator``, a post-processing transform that corrects miscalibration by fitting isotonic regression to the empirical quantile–probability relationship. Applying it after ``ConfidenceIntervalApplicator`` can substantially improve reliability without retraining the underlying model.

.. code-block:: python

   from openstef_models.transforms.postprocessing.isotonic_quantile_calibrator import (
       IsotonicQuantileCalibrator,
   )

   calibrator = IsotonicQuantileCalibrator()
   calibrator.fit((validation_dataset, validation_predictions))
   result_calibrated = calibrator.transform(result)

Finally, ``QuantileSorter`` enforces the monotonicity constraint — that P10 ≤ P25 ≤ P50 ≤ P75 ≤ P90 — which can occasionally be violated by independent quantile models:

.. code-block:: python

   from openstef_models.transforms.postprocessing.quantile_sorter import QuantileSorter

   sorter = QuantileSorter()
   result_sorted = sorter.transform(result_calibrated)


Why Quantiles Matter for Grid Operations
-----------------------------------------

The operational value of probabilistic forecasts is concrete:

**Congestion management**
   A transmission operator scheduling redispatch actions needs to know the *worst plausible* load, not just the expected load. Using P90 as the planning value provides a defensible safety margin without the excessive conservatism of always planning for the absolute maximum.

**Reserve procurement**
   Balancing responsible parties size their reserve capacity based on forecast uncertainty. A narrow P10–P90 band on a calm, predictable day justifies procuring less reserve; a wide band on a stormy day with high renewable penetration signals the need for more.

**Renewable integration**
   Solar and wind generation are inherently variable. Quantile forecasts let grid operators distinguish between "this wind farm will almost certainly produce between 80–120 MW" and "this wind farm could produce anywhere from 20–160 MW" — two situations that demand very different operational responses.

**Risk-aware dispatch**
   Economic dispatch algorithms can incorporate quantile forecasts directly as stochastic constraints, optimising expected cost while bounding the probability of constraint violations.

.. note::

   The P50 forecast minimises mean absolute error. If your loss function is asymmetric — for example, under-forecasting load is more costly than over-forecasting — you should use a quantile other than P50 as your operational point estimate. A P65 or P70 forecast, for instance, builds in a systematic upward bias that may be economically justified.


Interpreting the Forecast Bands in Practice
--------------------------------------------

A few common misinterpretations are worth addressing directly:

- **The P50 is not a guarantee.** By definition, actual outcomes will fall below P50 roughly half the time. Do not treat it as a lower bound.
- **Wider bands are not worse forecasts.** A wide P10–P90 interval on a genuinely uncertain day is *correct*. Artificially narrow intervals that miss actuals frequently are far more dangerous operationally.
- **Quantile bands are not symmetric.** Although the normal-distribution assumption in ``ConfidenceIntervalApplicator`` produces symmetric intervals, real forecast error distributions are often skewed — particularly for renewable generation near zero or capacity limits. The ``IsotonicQuantileCalibrator`` can correct for this asymmetry.
- **Exceedances are expected.** If your P90 is never exceeded, your intervals are too wide. Healthy calibration means roughly 10% of observations exceed P90 over a long evaluation window.


Related Topics
--------------

- :doc:`forecasting_basics` — introduces the overall short-term forecasting workflow that produces the point forecasts to which quantiles are attached.
- :doc:`model_selection` — discusses which model types natively support quantile outputs versus those that rely on post-processing transforms.
- :doc:`feature_engineering` — covers the input features (weather, calendar, historical load) that drive both the point forecast and the uncertainty estimates.
- :doc:`reliability_and_fallback` — explains how OpenSTEF handles degraded-mode operation when quantile generation fails, ensuring a point forecast is always available even if probabilistic output is not.