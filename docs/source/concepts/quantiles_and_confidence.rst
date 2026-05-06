Probabilistic Forecasts and Quantiles
=====================================

Probabilistic forecasting goes beyond predicting a single value. Instead of
asking "what will the load be at 14:00 tomorrow?", it asks "what is the
*distribution* of likely loads at 14:00 tomorrow?" OpenSTEF answers this
question through **quantile forecasts** — a set of percentile values that
together describe the uncertainty around every prediction.

This page explains what quantiles are, how OpenSTEF produces them, and how to
use them in operational decision-making. For background on the forecasting
process itself, see :doc:`forecasting_basics`.

What Is a Quantile?
-------------------

A quantile at level *p* is the value below which a fraction *p* of outcomes
are expected to fall. In energy forecasting:

- ``Q(0.10)`` — there is a 10 % chance the actual load will be *below* this
  value (and a 90 % chance it will be *above*).
- ``Q(0.50)`` — the median; equally likely to be above or below.
- ``Q(0.90)`` — there is a 90 % chance the actual load will be *below* this
  value.

A set of quantiles together forms a **predictive distribution**. The interval
between ``Q(0.10)`` and ``Q(0.90)`` is an 80 % prediction interval: on
average, 80 % of observed values should fall inside it.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd

OpenSTEF uses the ``Quantile`` type from ``openstef_core`` to represent
quantile levels throughout the library. Column names in output DataFrames
follow the pattern ``quantile_P10``, ``quantile_P50``, ``quantile_P90``, and
so on.

Configuring Quantiles
---------------------

You declare which quantiles a model should produce when you build a
``ForecastingWorkflowConfig``. The library then ensures every downstream
component — training, inference, and postprocessing — is consistent with that
declaration.

.. code-block:: python

    from openstef_core.types import LeadTime, Quantile
    from openstef_models.workflows.forecasting import ForecastingWorkflowConfig

    Q = Quantile

    # A typical set covering the central 90 % of the distribution
    QUANTILES = [
        Q(0.05), Q(0.10), Q(0.30),
        Q(0.50),           # median — always include this
        Q(0.70), Q(0.90), Q(0.95),
    ]

    config = ForecastingWorkflowConfig(
        model_id="substation_a",
        model="gblinear",
        horizons=[LeadTime.from_string("P1D")],
        quantiles=QUANTILES,
    )

The ``Q(0.50)`` entry is the point forecast. All other quantiles describe the
spread around it. You can use as few as three quantiles (P10, P50, P90) for a
lightweight setup, or a denser grid when downstream consumers need finer
resolution.

How OpenSTEF Generates Quantiles
---------------------------------

OpenSTEF uses two complementary mechanisms depending on the model type.

**Native quantile regression**

Gradient-boosted models such as ``gblinear`` support quantile loss functions
directly. Each quantile is trained as a separate regression target, so the
model learns the full conditional distribution from the data rather than
assuming any particular shape.

**Confidence interval applicator**

For models that produce only a point forecast, the
``ConfidenceIntervalApplicator`` postprocessing transform adds quantile bands
after prediction. It learns hour-of-day uncertainty patterns from validation
errors and converts them to quantiles by assuming a normal distribution:

.. code-block:: text

    Q(p) = median + z(p) × σ(hour)

where ``z(p)`` is the standard normal z-score for quantile *p* and ``σ(hour)``
is the standard deviation of validation residuals for that hour of the day.
For multi-horizon forecasts, uncertainty grows with lead time following an
exponential saturation curve:

.. code-block:: text

    σ(t) = a × (1 − exp(−t / τ)) + b

This reflects the physical reality that uncertainty accumulates quickly in the
first few hours and then levels off as the forecast approaches its maximum
horizon.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
        ConfidenceIntervalApplicator,
    )

    applicator = ConfidenceIntervalApplicator(
        quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
    )

    # fit on a ForecastDataset that contains validation-period predictions
    applicator.fit(validation_forecast_dataset)

    # transform applies the learned σ(hour) to new predictions
    probabilistic_forecast = applicator.transform(point_forecast_dataset)

After the transform, ``probabilistic_forecast.data`` contains columns
``quantile_P10``, ``quantile_P50``, and ``quantile_P90``.

**Isotonic calibration**

Raw quantile outputs can violate the monotonicity constraint — for example,
``Q(0.30)`` might exceed ``Q(0.70)`` for a specific timestamp due to model
noise. The ``IsotonicQuantileCalibrator`` postprocessing step corrects this by
fitting isotonic regression across quantile levels, guaranteeing that
``Q(p₁) ≤ Q(p₂)`` whenever ``p₁ < p₂``.

Reading the Output
------------------

A ``ForecastDataset`` exposes quantile columns directly through its
``.data`` DataFrame and provides convenience properties for common access
patterns:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import ForecastDataset

    # Inspect available quantiles
    print(forecast.quantiles)          # [0.1, 0.5, 0.9]

    # Access the median series directly
    median = forecast.median_series    # pd.Series

    # Access the full DataFrame (columns: quantile_P10, quantile_P50, quantile_P90, ...)
    df = forecast.data

    # Derive an 80 % prediction interval manually
    lower = df["quantile_P10"]
    upper = df["quantile_P90"]
    interval_width = upper - lower

.. note:: [VISUALIZATION: Time-series plot of quantile_P10, quantile_P50, quantile_P90 columns from a ForecastDataset, with the actual load overlaid]

Prediction Intervals vs. Confidence Intervals
----------------------------------------------

These two terms are often confused, and the distinction matters operationally.

A **confidence interval** describes uncertainty about a *model parameter* —
for example, the true mean load at a given hour. It narrows as you collect
more data.

A **prediction interval** describes uncertainty about a *single future
observation*. Even with a perfect model and infinite training data, a
prediction interval remains wide because individual observations are noisy.

OpenSTEF produces **prediction intervals**. The bands around a forecast
represent the expected spread of *actual measured load*, not uncertainty about
the model's average behaviour. This is the correct framing for operational
decisions: you want to know the range of outcomes you might actually face, not
the range of possible model means.

.. note::

   The term "confidence interval" appears in OpenSTEF's internal module names
   (``confidence_interval_applicator``) for historical reasons. Operationally,
   treat all quantile bands as prediction intervals.

Why Quantiles Matter for Operations
-------------------------------------

A point forecast alone is insufficient for many grid management tasks. Here
are three concrete examples where quantile information changes the decision:

**Congestion management**

A substation has a thermal limit of 120 MW. The median forecast is 110 MW —
apparently safe. But if ``Q(0.95)`` is 128 MW, there is a 5 % chance of
exceeding the limit. An operator using only the median would miss this risk.
Using ``Q(0.90)`` or ``Q(0.95)`` as a conservative planning value directly
incorporates that tail risk.

**Battery dispatch scheduling**

Charging a battery when load is low and discharging when load is high requires
knowing *how confident* you are in the forecast. A narrow interval
(``Q(0.90) − Q(0.10)`` is small) justifies an aggressive dispatch schedule. A
wide interval suggests holding reserve capacity.

**Imbalance cost estimation**

Energy markets penalise deviations from nominated volumes. The expected
imbalance cost depends on the full distribution of forecast errors, not just
the median. Integrating over the quantile bands gives a direct estimate of
expected penalty costs, enabling better nomination strategies.

Baseline Comparison
-------------------

When evaluating a new model, it is useful to compare its quantile forecasts
against a naive baseline. The ``ConstantMedianForecaster`` provides exactly
this: it predicts the historical quantile values from the training set as
constant forecasts for all future timestamps.

.. code-block:: python

    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    # Import path derived from the forecaster's location in openstef-models
    from openstef_models.forecasters.constant_median import ConstantMedianForecaster

    baseline = ConstantMedianForecaster(
        quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
        horizons=[LeadTime(timedelta(hours=1))],
    )
    baseline.fit(train_dataset)
    baseline_forecast = baseline.predict(test_dataset)

A well-calibrated probabilistic model should produce narrower prediction
intervals than this baseline while maintaining the correct coverage — meaning
the stated fraction of observations actually falls within each interval.

Calibration: Are the Quantiles Trustworthy?
--------------------------------------------

A quantile forecast is **calibrated** if, over many forecasts, the empirical
coverage matches the nominal level. For example, 90 % of actual observations
should fall below ``Q(0.90)``.

Poor calibration takes two forms:

- **Overconfident** — intervals are too narrow; more observations fall outside
  them than expected. This is dangerous in operational settings.
- **Underconfident** — intervals are too wide; they provide little useful
  information about the likely range.

The ``IsotonicQuantileCalibrator`` addresses systematic bias in quantile
ordering. Broader calibration assessment — checking empirical coverage across
the full quantile grid — should be part of any model evaluation workflow.

.. note:: [VISUALIZATION: Reliability diagram (calibration plot) showing nominal quantile levels on the x-axis against empirical coverage on the y-axis, with a diagonal reference line]

Related Topics
--------------

- :doc:`forecasting_basics` — how the overall forecasting pipeline works and
  what inputs it requires.
- :doc:`reliability_and_fallback` — what happens to quantile outputs when a
  model fails and a fallback is activated.
- :doc:`meta_ensembles` — how ensemble methods combine multiple quantile
  forecasts from different base models.
- :doc:`component_splitting` — how quantile forecasts are produced for
  individual energy components (solar, wind, base load) before being
  recombined.