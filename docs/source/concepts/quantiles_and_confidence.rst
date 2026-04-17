Probabilistic Forecasts and Quantiles
=====================================

Short-term energy forecasts in OpenSTEF are *probabilistic*: rather than
producing a single number, the library outputs a set of quantile predictions
that together describe the full range of plausible outcomes. This page explains
what those quantiles mean, how OpenSTEF computes them, and why they matter for
day-to-day grid operations.

For background on what is being forecast and over what horizons, see
:doc:`forecasting_basics`. For details on how model reliability is maintained
in production, see :doc:`reliability_and_fallback`.

What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What load value will not be
exceeded X% of the time?"* The 10th percentile (P10) is a value that the
actual load will fall below only 10% of the time; the 90th percentile (P90)
is a value the actual load will exceed only 10% of the time. The 50th
percentile (P50) is the median — the most likely single outcome.

Together, a set of quantiles traces out the *predictive distribution* of the
forecast. A well-calibrated model means that, over many forecasts, the
fraction of observations that fall below the P10 line is genuinely close to
10%, the fraction below P50 is close to 50%, and so on.

OpenSTEF uses the ``Quantile`` type from ``openstef_core.types`` to represent
these levels. A typical configuration covers seven quantiles:

.. code-block:: python

    from openstef_core.types import Quantile as Q

    PREDICTION_QUANTILES = [
        Q(0.05),   # P05 — very low load scenario
        Q(0.10),   # P10 — lower bound of typical band
        Q(0.30),   # P30
        Q(0.50),   # P50 — median (point forecast)
        Q(0.70),   # P70
        Q(0.90),   # P90 — upper bound of typical band
        Q(0.95),   # P95 — very high load scenario
    ]

The resulting forecast ``DataFrame`` contains one column per quantile, named
``quantile_P05``, ``quantile_P10``, …, ``quantile_P95``.

Confidence Intervals vs. Prediction Intervals
----------------------------------------------

These two terms are often confused, and the distinction matters when
communicating uncertainty to operators.

A **confidence interval** describes uncertainty about a *model parameter* —
for example, the estimated mean load at 08:00 on a Monday. It shrinks as more
training data is collected.

A **prediction interval** describes uncertainty about a *single future
observation*. Even with a perfect model and infinite data, tomorrow's load
will still vary due to unpredictable factors (unexpected industrial activity,
measurement noise, atypical weather). Prediction intervals do not shrink to
zero.

OpenSTEF produces **prediction intervals**. The P10–P90 band shown in a
forecast visualisation is not a statement about model parameter uncertainty;
it is a statement about the range within which the actual measured load is
expected to fall 80% of the time.

.. note:: [VISUALIZATION: Time-series plot showing P50 median forecast as a solid line, P10–P90 shaded band as the 80% prediction interval, and actual measurements overlaid as points]

How OpenSTEF Computes Quantiles
--------------------------------

Quantile generation happens in the postprocessing stage of the forecasting
pipeline. The primary mechanism is the ``ConfidenceIntervalApplicator``,
which learns hour-specific uncertainty from validation errors and then applies
that learned uncertainty to new predictions.

**Learning phase.** During training, the applicator computes forecast errors
on held-out validation data for each hour of the day (0–23). It calculates
the standard deviation of those errors per hour, and — for multi-horizon
forecasts — stores a separate standard deviation per forecast horizon.

**Prediction phase.** When generating a new forecast, the applicator looks up
the standard deviation for the relevant hour and horizon, then converts it to
quantile offsets by assuming a normal distribution:

.. code-block:: text

    quantile_value = median + z_score × std

    e.g.  P10 = median − 1.28 × std
          P90 = median + 1.28 × std

For multi-horizon forecasts, uncertainty grows with lead time. OpenSTEF
models this with an exponential saturation curve:

.. code-block:: text

    σ(t) = a × (1 − exp(−t / τ)) + b

    where t = hours ahead, τ = far_horizon / 4

This reflects the physical reality that uncertainty grows quickly in the first
few hours and then levels off as the dominant uncertainty source shifts from
weather variability to structural load patterns.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd

Using the ``ConfidenceIntervalApplicator`` directly:

.. code-block:: python

    from openstef_core.types import Quantile
    from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
        ConfidenceIntervalApplicator,
    )

    applicator = ConfidenceIntervalApplicator(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
    )

    # fit expects (validation_input_data, validation_predictions)
    applicator.fit((validation_data, validation_predictions))

    # transform adds quantile_P10, quantile_P50, quantile_P90 columns
    forecast_with_intervals = applicator.transform((new_input_data, new_predictions))
    print(forecast_with_intervals.data.columns)
    # Index(['quantile_P10', 'quantile_P50', 'quantile_P90'], ...)

Calibration: Are the Quantiles Reliable?
------------------------------------------

A model can produce quantile columns without those quantiles being
*calibrated* — that is, the stated P90 might actually be exceeded 20% of the
time rather than 10%. OpenSTEF addresses this with the
``IsotonicQuantileCalibrator``, which learns a monotonic correction mapping
from predicted quantile values to empirically correct values.

The calibrator uses isotonic regression (a shape-constrained regression that
enforces monotonicity) to ensure that the corrected quantiles remain properly
ordered: P10 ≤ P30 ≤ P50 ≤ P70 ≤ P90.

.. code-block:: python

    from openstef_core.datasets import ForecastDataset, TimeSeriesDataset
    from openstef_core.mixins import TransformPipeline
    from openstef_core.types import LeadTime, Q
    from openstef_models.transforms.postprocessing import IsotonicQuantileCalibrator
    from openstef_models.workflows import CustomForecastingWorkflow

    quantiles = [Q(0.1), Q(0.5), Q(0.9)]

    # Build a workflow that includes isotonic calibration as a postprocessing step
    workflow = CustomForecastingWorkflow(
        postprocessing=TransformPipeline([
            IsotonicQuantileCalibrator(quantiles=quantiles),
        ])
    )

A calibration quality check compares *expected coverage* (the stated quantile
level) against *observed coverage* (the fraction of validation observations
that actually fell below each quantile). A perfectly calibrated model
produces a diagonal line on this plot.

.. note:: [VISUALIZATION: Calibration reliability diagram (expected coverage on x-axis, observed coverage on y-axis) showing a diagonal reference line and the model's calibration curve]

Interpreting Quantiles in Operations
--------------------------------------

Grid operators and energy traders use quantile forecasts differently from a
plain point forecast. Some common operational patterns:

- **Congestion management.** Use P90 as a conservative upper-bound estimate
  when deciding whether to pre-emptively curtail generation or activate
  flexibility. Acting on P90 rather than P50 reduces the risk of unexpected
  overloads.

- **Reserve sizing.** The width of the P10–P90 band is a direct measure of
  forecast uncertainty. A wide band on a particular day (e.g., due to
  uncertain wind conditions) signals that larger operating reserves may be
  needed.

- **Asymmetric costs.** When the cost of under-forecasting (e.g., failing to
  procure enough capacity) differs from the cost of over-forecasting (e.g.,
  holding excess reserve), the optimal decision is not the median but a
  quantile that reflects the cost ratio. If under-forecasting is twice as
  costly, the P67 quantile is the theoretically optimal bid.

- **Anomaly detection.** Observations that consistently fall outside the
  P05–P95 band may indicate metering errors, unreported load changes, or
  model degradation — a signal to trigger retraining.

Accessing Quantile Output
--------------------------

After calling ``workflow.predict()``, the returned ``ForecastDataset``
exposes both the raw quantile columns and convenience accessors:

.. code-block:: python

    from openstef_core.datasets import ForecastDataset

    forecast: ForecastDataset = workflow.predict(forecast_dataset)

    # All quantile levels present in this forecast
    print(forecast.quantiles)          # e.g. [0.1, 0.5, 0.9]

    # Median series as a plain pd.Series
    median = forecast.median_series

    # Full quantile DataFrame (one column per quantile)
    bands = forecast.quantiles_data

    print(bands.head())
    # quantile_P10  quantile_P50  quantile_P90
    # 2024-01-01 00:00    142.3         158.7         174.1
    # 2024-01-01 01:00    138.9         154.2         169.5
    # ...

Visualising the output with the built-in plotter:

.. code-block:: python

    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

    fig = (
        ForecastTimeSeriesPlotter()
        .add_measurements(measurements=forecast_dataset.data["load"])
        .add_model(
            model_name="GBLinear",
            forecast=forecast.median_series,
            quantiles=forecast.quantiles_data,
        )
        .plot()
    )
    fig.show()

.. note:: [VISUALIZATION: Interactive time-series plot with actual load measurements as a line, P50 median forecast as a second line, and P10–P90 shaded prediction band]

Summary
--------

- OpenSTEF forecasts are probabilistic: each prediction is a set of quantile
  values, not a single number.
- Quantile columns are named ``quantile_P<level>``, where ``<level>`` is the
  percentile (e.g., ``quantile_P90``).
- The P10–P90 band is an **80% prediction interval** — it covers the range
  within which the actual value is expected to fall 80% of the time.
- ``ConfidenceIntervalApplicator`` derives quantiles from hour-specific
  validation error statistics; uncertainty grows with lead time following an
  exponential saturation curve.
- ``IsotonicQuantileCalibrator`` corrects systematic miscalibration so that
  stated quantile levels match observed empirical coverage.
- Operational decisions (reserve sizing, congestion management, bidding)
  should be based on the quantile that matches the cost structure of the
  decision, not always the median.

For related topics, see :doc:`forecasting_basics` for an introduction to the
forecasting problem itself, :doc:`reliability_and_fallback` for how OpenSTEF
handles model failures in production, and :doc:`meta_ensembles` for how
multiple models can be combined to produce more robust uncertainty estimates.