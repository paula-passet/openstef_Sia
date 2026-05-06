Probabilistic Forecasts and Quantiles
=====================================

Short-term energy forecasts from OpenSTEF are *probabilistic*: rather than
producing a single number for each future timestep, the library outputs a
family of quantile predictions that together describe the full uncertainty
distribution of the forecast. This page explains what those quantiles mean,
how OpenSTEF generates them, and how to use them in practice.

For a broader introduction to what short-term forecasting is and why it is
needed, see :doc:`forecasting_basics`.

What a Quantile Forecast Is
----------------------------

A quantile forecast answers the question: *"What value will not be exceeded
with probability p?"* The 10th-percentile forecast (P10) is the value that
the actual load is expected to stay above 90 % of the time; the 90th-percentile
forecast (P90) is the value the actual load is expected to stay below 90 % of
the time. The 50th-percentile forecast (P50) is the median — the model's best
single-point estimate.

Together, a set of quantiles traces out the *predictive distribution* at each
future timestep without assuming any particular shape for that distribution.
A typical OpenSTEF configuration uses seven quantiles:

.. code-block:: python

    from openstef_core.types import Quantile as Q

    PREDICTION_QUANTILES = [
        Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)
    ]

The resulting forecast DataFrame contains one column per quantile, named
``quantile_P05``, ``quantile_P10``, …, ``quantile_P95``. The P50 column is
the point forecast; the remaining columns describe how wide or narrow the
uncertainty band is around it.

.. note:: [VISUALIZATION: Fan chart showing quantile bands (P05–P95) around a P50 point forecast over a 48-hour horizon, with actual load overlaid]

How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF uses two complementary mechanisms to attach uncertainty estimates to
a forecast.

**Direct quantile regression.** Gradient-boosted models (e.g. ``gblinear``,
``xgb``) can be trained with a quantile loss function so that each quantile
is learned directly from the data. The model sees the same input features for
every quantile but optimises a different asymmetric loss, producing outputs
that are calibrated to the requested probability levels.

**Post-hoc confidence interval applicator.** When a model produces only a
point forecast (or a median), the
``ConfidenceIntervalApplicator`` transform adds quantile columns by learning
the *hour-specific* forecast error distribution from a held-out validation
set and then applying it at prediction time:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
        ConfidenceIntervalApplicator,
    )

    quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

    applicator = ConfidenceIntervalApplicator(
        quantiles=quantiles,
        horizons=[LeadTime(timedelta(hours=24))],
    )

    # fit on a ForecastDataset that contains validation-period predictions
    applicator.fit(validation_forecast_dataset)

    # transform adds quantile_P10, quantile_P50, quantile_P90 columns
    probabilistic_forecast = applicator.transform(point_forecast_dataset)

Internally the applicator computes the standard deviation of validation errors
for each hour of the day (0–23). At prediction time it looks up the
appropriate standard deviation and converts it to quantile offsets assuming a
normal distribution:

.. code-block:: text

    quantile_value = median + z_score × σ_hour

    e.g.  P10 = median − 1.28 × σ_hour
          P90 = median + 1.28 × σ_hour

For multi-horizon forecasts, uncertainty grows with lead time. The applicator
models this with an exponential saturation curve:

.. code-block:: text

    σ(t) = a × (1 − exp(−t / τ)) + b,   τ = far_horizon / 4

This reflects the physical reality that forecast skill degrades quickly in the
first few hours and then levels off as the forecast horizon extends.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd

Calibration
^^^^^^^^^^^^

Raw quantile outputs are not always perfectly calibrated — P90 may not
actually contain the true value 90 % of the time. OpenSTEF provides an
``IsotonicQuantileCalibrator`` post-processing transform that corrects
systematic over- or under-confidence using isotonic regression on a
held-out calibration set:

.. code-block:: python

    from openstef_models.transforms.postprocessing.isotonic_quantile_calibrator import (
        IsotonicQuantileCalibrator,
    )

    calibrator = IsotonicQuantileCalibrator(quantiles=quantiles)
    calibrator.fit(calibration_forecast_dataset)
    calibrated_forecast = calibrator.transform(probabilistic_forecast)

After calibration, the quantile ordering guarantee is preserved:
P10 ≤ P30 ≤ P50 ≤ P70 ≤ P90 for every timestep.

Reading a ``ForecastDataset``
------------------------------

All probabilistic output is wrapped in a ``ForecastDataset``. The
``.quantiles`` property returns the list of ``Quantile`` objects present, and
individual quantile columns follow the ``quantile_P<NN>`` naming convention:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import ForecastDataset

    # Construct a minimal example from a DataFrame
    df = pd.DataFrame(
        {
            "quantile_P10": [95, 98],
            "quantile_P50": [100, 110],
            "quantile_P90": [115, 125],
        },
        index=pd.date_range("2025-01-01", periods=2, freq="h"),
    )
    dataset = ForecastDataset(df, sample_interval=timedelta(hours=1))

    print(dataset.quantiles)          # [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
    print(dataset.data["quantile_P50"])  # point forecast series

To work with a subset of quantiles — for example, to pass only P10 and P90
to a downstream system — use ``ForecastDataset.select_quantiles()``:

.. code-block:: python

    from openstef_core.types import Quantile

    narrow_dataset = dataset.select_quantiles(
        [Quantile(0.1), Quantile(0.9)]
    )

Confidence vs. Prediction Intervals
-------------------------------------

These two terms are often confused, and the distinction matters for
operational use:

- A **prediction interval** (what OpenSTEF produces) covers the *actual
  future observation* with a stated probability. A 90 % prediction interval
  ``[P05, P95]`` should contain the true load value in 90 out of 100
  forecasting instances.

- A **confidence interval** covers an *estimated parameter* (e.g. the mean
  of the load distribution). Confidence intervals are narrower because they
  do not account for irreducible observation noise.

When you use OpenSTEF quantiles for operational decisions — scheduling
reserves, checking congestion risk, setting alert thresholds — you are working
with prediction intervals. The correct interpretation is: *"There is a 5 %
chance the actual load will exceed the P95 forecast."*

.. note::

   The ``ConfidenceIntervalApplicator`` is named for historical reasons; the
   intervals it produces are prediction intervals in the statistical sense.

Why Quantiles Matter for Grid Operations
-----------------------------------------

A single point forecast is insufficient for risk-aware decisions. Consider
two scenarios that produce the same P50 forecast of 100 MW:

- **Scenario A**: P10 = 95 MW, P90 = 105 MW — a narrow band, high
  confidence.
- **Scenario B**: P10 = 70 MW, P90 = 130 MW — a wide band, high uncertainty.

An operator managing a 120 MW line limit would treat these very differently.
In Scenario A the P90 is comfortably below the limit; in Scenario B there is
a meaningful probability of congestion. Quantile forecasts make this
distinction explicit.

Common operational uses of quantile forecasts include:

- **Congestion risk assessment**: check whether P90 (or P95) exceeds a
  thermal or voltage limit.
- **Reserve sizing**: use the spread between P10 and P90 to determine how
  much upward and downward flexibility to procure.
- **Imbalance cost reduction**: bid the P50 on energy markets and use the
  quantile spread to size balancing bids.
- **Alarm thresholds**: trigger alerts only when the P90 forecast exceeds a
  threshold, reducing false positives compared to point-forecast alarms.

.. note:: [VISUALIZATION: Side-by-side bar chart comparing narrow vs. wide quantile bands against a line limit, illustrating different congestion risk levels]

Baseline Comparison
--------------------

When evaluating a new model it is useful to compare against a simple
probabilistic baseline. The ``ConstantMedianForecaster`` provides exactly
this — it computes historical quantile values from the training set and
returns them as constant predictions for all future timesteps:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.forecasters.constant_median import ConstantMedianForecaster

    baseline = ConstantMedianForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
    )
    baseline.fit(train_dataset)
    baseline_forecast = baseline.predict(test_dataset)

A well-trained model should produce sharper (narrower) quantile bands than
this baseline while maintaining calibration — that is, the actual coverage
rates should match the nominal probability levels.

Related Topics
---------------

- :doc:`forecasting_basics` — what short-term forecasting is and how the
  overall prediction workflow fits together.
- :doc:`reliability_and_fallback` — how OpenSTEF handles model failures,
  including fallback strategies that still produce valid quantile output.
- :doc:`meta_ensembles` — how ensemble methods combine multiple base
  forecasters and propagate uncertainty through the combination step.
- :doc:`component_splitting` — decomposing aggregate load into components;
  quantile forecasts can be generated at the component level and
  recombined.