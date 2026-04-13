Quantiles and Confidence Intervals
===================================

Probabilistic forecasting is one of OpenSTEF's most practically valuable capabilities. Rather than
producing a single "best guess" for future load, OpenSTEF can generate a full distribution of likely
outcomes expressed as quantiles. This page explains what quantiles are, how OpenSTEF computes them,
and why they matter for real-world grid operations.

.. mermaid:: diagrams/concepts/quantiles_and_confidence_diagram_1.mmd

What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What load level will not be exceeded with probability p?"*
The P50 quantile (the median) is the value that the actual outcome is equally likely to fall above or
below. The P10 quantile is the value that the actual outcome will exceed 90% of the time — a
conservative lower bound. The P90 quantile is exceeded only 10% of the time — a conservative upper
bound.

Together, a set of quantiles describes the **predictive distribution** of future load without assuming
any particular statistical shape. In OpenSTEF, quantiles are expressed as floats between 0 and 1 using
the ``Quantile`` type, and the corresponding output columns are named ``quantile_P10``, ``quantile_P50``,
``quantile_P90``, and so on.

.. code-block:: python

    from openstef_core.types import Quantile

    # Quantiles are typed floats — this gives you named columns like quantile_P10
    quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

A forecast ``DataFrame`` with quantile output looks like this:

.. code-block:: python

    import pandas as pd

    # Example structure of a ForecastDataset with quantile columns
    forecast_df = pd.DataFrame(
        {
            "quantile_P10": [92.3, 88.1, 95.0],
            "quantile_P50": [105.0, 101.4, 109.2],
            "quantile_P90": [117.8, 114.9, 123.5],
        },
        index=pd.date_range("2025-06-01 08:00", periods=3, freq="h"),
    )
    print(forecast_df)

The P50 column is the point forecast you would use if forced to commit to a single number. The P10 and
P90 columns bracket an 80% prediction interval — the range within which the actual outcome is expected
to fall eight times out of ten.

How OpenSTEF Computes Quantiles
--------------------------------

OpenSTEF uses two complementary mechanisms to generate quantile forecasts.

**Quantile regression** is the primary approach for models that support it natively. Rather than
minimising mean squared error, the model is trained with a pinball (quantile) loss function for each
target quantile. This means the model directly learns to predict, say, the 90th percentile of the
outcome distribution from the input features. The ``GBLinearForecaster`` and gradient-boosted tree
models in OpenSTEF support multi-quantile output this way:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.forecasters.gblinear import GBLinearForecaster, GBLinearHyperParams

    forecaster = GBLinearForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
        hyperparams=GBLinearHyperParams(
            learning_rate=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
        ),
    )
    forecaster.fit(training_data)       # doctest: +SKIP
    predictions = forecaster.predict(test_data)  # doctest: +SKIP

**Post-hoc confidence interval application** is used when a model produces only a point forecast. The
``ConfidenceIntervalApplicator`` transform learns the hour-specific uncertainty of the model from
validation errors, then applies it to new predictions. It computes the standard deviation of residuals
for each hour of the day (0–23), and converts that standard deviation to quantile values by assuming a
normal distribution:

.. math::

    \hat{q}_p(t) = \hat{y}(t) + z_p \cdot \sigma_h

where :math:`\hat{y}(t)` is the point forecast, :math:`z_p` is the standard normal quantile
corresponding to probability *p* (e.g., −1.28 for P10, +1.28 for P90), and :math:`\sigma_h` is the
learned standard deviation for hour *h*.

For multi-horizon forecasts, uncertainty grows with lead time following an exponential saturation curve:

.. math::

    \sigma(t) = a \cdot (1 - e^{-t/\tau}) + b

where *t* is hours ahead and :math:`\tau = \text{far\_horizon} / 4`. This reflects the practical
observation that uncertainty grows quickly in the first few hours and then levels off as the forecast
horizon extends.

.. code-block:: python

    from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
        ConfidenceIntervalApplicator,
    )
    from openstef_core.types import Quantile

    applicator = ConfidenceIntervalApplicator(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
    )
    applicator.fit(validation_dataset)   # doctest: +SKIP
    forecast_with_intervals = applicator.transform(forecast_dataset)  # doctest: +SKIP

Confidence Intervals vs. Prediction Intervals
----------------------------------------------

These two terms are often confused, and the distinction matters in practice.

A **confidence interval** describes uncertainty about a *model parameter* — for example, how precisely
the model has estimated the mean load at a given hour. It narrows as you collect more training data,
because the parameter estimate becomes more certain.

A **prediction interval** describes uncertainty about a *future individual observation*. Even a
perfectly calibrated model cannot eliminate the inherent variability of the system being forecast. A
prediction interval stays wide because it must account for both parameter uncertainty *and* the
irreducible noise in the outcome.

OpenSTEF's quantile forecasts are **prediction intervals**. The P10–P90 band is not telling you how
uncertain the model is about its own parameters; it is telling you the range within which the actual
measured load is expected to fall. This is the operationally relevant quantity for grid management.

.. note::

   A well-calibrated P90 forecast should be exceeded by actual outcomes approximately 10% of the time.
   If your P90 is exceeded 30% of the time, the model is under-estimating uncertainty. OpenSTEF
   provides calibration tooling (see :ref:`Validating Calibration` below) to diagnose this.

Why Quantiles Matter for Grid Operations
-----------------------------------------

A point forecast alone is rarely sufficient for operational decisions. Consider three common scenarios:

**Congestion management.** A grid operator needs to know whether load at a substation will exceed a
thermal limit. The P90 forecast answers: *"What is the load level I should plan for if I want to be
safe 90% of the time?"* Using only the P50 would mean being caught out half the time.

**Imbalance and energy trading.** Energy traders need to balance the cost of over-procurement against
the cost of under-procurement. These costs are asymmetric. Quantile forecasts allow the trader to
select the quantile that minimises expected cost given their specific penalty structure — not
necessarily the median.

**Reserve capacity planning.** Transmission system operators communicating planned usage to upstream
operators (for example, Alliander reporting to TenneT) benefit from interval forecasts that convey
the range of plausible demand, enabling coordinated capacity decisions.

In each case, the actionable quantity is not "what is the most likely outcome" but "what is the
distribution of outcomes, and what decision minimises my expected cost or risk?"

Validating Calibration
-----------------------

A quantile forecast is only useful if it is **calibrated** — meaning that stated probabilities match
observed frequencies. OpenSTEF provides the ``QuantileProbabilityPlotter`` for this purpose. It
compares the fraction of actual outcomes that fell below each predicted quantile against the nominal
probability, producing a calibration curve.

.. code-block:: python

    from openstef_beam.analysis.plots.quantile_probability_plotter import (
        QuantileProbabilityPlotter,
    )

    plotter = QuantileProbabilityPlotter()
    fig = plotter.plot(
        observed_probabilities=observed_probs,   # doctest: +SKIP
        forecasted_probabilities=forecasted_probs,  # doctest: +SKIP
    )
    fig.show()  # doctest: +SKIP

A perfectly calibrated model produces a calibration curve that lies on the diagonal. Curves bowing
above the diagonal indicate that the model's intervals are too wide (over-confident uncertainty
estimates); curves bowing below indicate intervals that are too narrow (under-confident).

Key questions the calibration plot helps answer:

- Are 90% prediction intervals correct 90% of the time?
- Does the model systematically over- or under-estimate uncertainty at specific hours of the day?
- Which of two competing models provides more reliable uncertainty quantification?

Interpreting Quantile Output in Practice
-----------------------------------------

When reading a quantile forecast, keep the following in mind:

- **P50 is not the "expected" load in the mean-squared-error sense.** For skewed distributions (common
  near zero or at capacity limits), the mean and median diverge. The P50 minimises mean absolute error;
  the mean minimises mean squared error.

- **Band width is informative.** A wide P10–P90 band signals a genuinely uncertain period — perhaps
  because of uncertain weather, an unusual day type, or a long lead time. A narrow band signals high
  confidence. Operators should treat wide bands as a prompt to prepare contingency actions.

- **Quantile ordering is guaranteed.** OpenSTEF enforces the invariant P10 ≤ P50 ≤ P90 in its output.
  Quantile crossing — where a lower quantile exceeds a higher one — is a known pathology of some
  quantile regression approaches, and OpenSTEF's post-processing corrects for it.

- **The choice of quantiles is configurable.** You are not limited to P10/P50/P90. Any set of quantiles
  between 0 and 1 can be requested, and the output columns are named accordingly (e.g.,
  ``quantile_P05``, ``quantile_P95``).

.. code-block:: python

    from openstef_core.types import Quantile

    # Request a finer-grained set of quantiles for a risk-sensitive application
    fine_quantiles = [Quantile(q) for q in [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]]

Related Topics
---------------

- :doc:`forecasting_basics` — Introduction to short-term forecasting and the overall prediction
  pipeline that produces the point forecast underlying quantile output.
- :doc:`feature_engineering` — How weather predictors and other features influence both the point
  forecast and the width of prediction intervals.
- :doc:`model_selection` — Comparing models by their quantile accuracy metrics (pinball loss, CRPS)
  rather than mean squared error alone.
- :doc:`reliability_and_fallback` — What happens to quantile output when the primary model is
  unavailable and a fallback strategy is activated.