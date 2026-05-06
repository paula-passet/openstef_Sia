Probabilistic Forecasts and Quantiles
=====================================

Probabilistic forecasting is one of OpenSTEF's core capabilities. Rather than producing a single
"best guess" for future load, OpenSTEF generates a full set of quantile forecasts that describe
the *distribution* of likely outcomes. This page explains what quantiles are, how OpenSTEF
produces them, and why they matter for grid operations.

For a broader introduction to short-term forecasting, see :doc:`forecasting_basics`.

What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What value will not be exceeded with probability p?"*
The 90th percentile (Q0.90) means the actual load will be at or below that value 90 % of the time.
The 10th percentile (Q0.10) means the actual load will be at or below that value only 10 % of the
time — in other words, it is a pessimistic lower bound.

Together, a set of quantiles traces out the forecast distribution without assuming any particular
shape for it. OpenSTEF typically produces seven quantiles by default:

.. code-block:: python

    from openstef_core.types import Quantile

    # Standard set used across OpenSTEF workflows
    PREDICTION_QUANTILES = [
        Quantile(0.05),
        Quantile(0.10),
        Quantile(0.30),
        Quantile(0.50),  # median — the "point forecast"
        Quantile(0.70),
        Quantile(0.90),
        Quantile(0.95),
    ]

The median (Q0.50) is the conventional point forecast. The symmetric pairs around it —
(Q0.10, Q0.90) and (Q0.05, Q0.95) — form 80 % and 90 % prediction intervals respectively.

.. note:: [VISUALIZATION: Fan chart showing seven quantile bands around a 24-hour load forecast, with the median as a solid line and shaded bands widening toward the tails]

How OpenSTEF Produces Quantiles
---------------------------------

OpenSTEF uses two complementary mechanisms depending on the model type.

**Native quantile regression**

Gradient-boosted tree models (``gblinear``, ``xgb``, ``lgbm``) support quantile loss functions
directly. Each quantile is trained as a separate regression target, so the model learns the
conditional distribution from the data rather than assuming a parametric form. This is the
preferred approach because it captures asymmetric and non-Gaussian uncertainty.

**Post-hoc confidence interval applicator**

When a model produces only a median forecast, the
``ConfidenceIntervalApplicator`` transform adds quantile bands by learning hour-specific
uncertainty from validation errors:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
        ConfidenceIntervalApplicator,
    )

    quantiles = [Quantile(0.10), Quantile(0.50), Quantile(0.90)]

    applicator = ConfidenceIntervalApplicator(
        quantiles=quantiles,
        horizons=[LeadTime(timedelta(hours=24))],
    )

    # fit on a ForecastDataset that contains validation-period predictions
    applicator.fit(validation_forecast_dataset)

    # transform new predictions to add quantile columns
    probabilistic_forecast = applicator.transform(point_forecast_dataset)

The applicator computes the standard deviation of validation errors for each hour of the day
(0–23). During prediction it converts those standard deviations to quantile offsets using the
normal z-score mapping — for example, Q0.10 = median − 1.28 × σ and Q0.90 = median + 1.28 × σ.
For multi-horizon forecasts, uncertainty grows with lead time following an exponential saturation
curve:

.. math::

    \sigma(t) = a \cdot (1 - e^{-t/\tau}) + b

where *t* is hours ahead and *τ* = far_horizon / 4. This reflects the empirical observation that
forecast uncertainty grows quickly in the first few hours and then levels off.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd

Reading the ``ForecastDataset`` Output
----------------------------------------

All quantile forecasts are stored in a ``ForecastDataset``. Each quantile occupies a column named
with the ``Quantile.format()`` convention — ``quantile_P10``, ``quantile_P50``, ``quantile_P90``,
and so on:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import ForecastDataset

    # Construct a minimal ForecastDataset manually (e.g. for testing)
    data = pd.DataFrame(
        {
            "quantile_P10": [95.0, 98.0],
            "quantile_P50": [105.0, 109.0],
            "quantile_P90": [115.0, 121.0],
        },
        index=pd.date_range("2025-06-01 00:00", periods=2, freq="h"),
    )

    dataset = ForecastDataset(data, sample_interval=timedelta(hours=1))

    print(dataset.quantiles)          # [0.1, 0.5, 0.9]
    print(dataset.median_series)      # pd.Series of Q0.50 values

The ``quantiles`` property returns the parsed ``Quantile`` objects in ascending order, and
``median_series`` is a convenience accessor for the Q0.50 column. You can also filter the dataset
to a subset of quantiles without copying the underlying data:

.. code-block:: python

    from openstef_core.types import Quantile

    # Keep only the 80 % interval and the median
    narrow = dataset.select_quantiles([Quantile(0.10), Quantile(0.50), Quantile(0.90)])

Configuring Quantiles in a Workflow
-------------------------------------

When running a full forecasting workflow, quantiles are declared once in the
``ForecastingWorkflowConfig`` and propagated automatically to the model and any post-processing
transforms:

.. code-block:: python

    from openstef_core.types import LeadTime, Quantile
    from openstef_models.workflows.config import ForecastingWorkflowConfig

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

.. note::

   At least one quantile must be provided and the list must include ``Quantile(0.50)`` if you
   intend to use ``ConfidenceIntervalApplicator``, which requires a median column as its
   starting point.

Prediction Intervals vs. Confidence Intervals
-----------------------------------------------

These two terms are often confused, and the distinction matters for how you use the output.

A **prediction interval** covers where a *single future observation* will fall with a given
probability. This is what OpenSTEF's quantile forecasts represent: "the actual load at 14:00
tomorrow will be between Q0.10 and Q0.90 with 80 % probability."

A **confidence interval** covers where the *true mean* of the process lies. Confidence intervals
are narrower than prediction intervals because averaging reduces variance. They are appropriate
when you want to characterise the model's uncertainty about the underlying trend, not the
variability of individual readings.

For grid operations — congestion management, reserve scheduling, imbalance settlement — you almost
always want **prediction intervals**. The grid must physically accommodate the actual load, not
just the expected average.

.. note::

   OpenSTEF's ``ConfidenceIntervalApplicator`` is named for historical reasons but produces
   **prediction intervals** in the statistical sense described above.

Calibration: Are the Quantiles Trustworthy?
--------------------------------------------

A well-calibrated Q0.90 forecast should be exceeded by the actual load roughly 10 % of the time.
If it is exceeded 25 % of the time the model is *overconfident* (intervals too narrow); if it is
exceeded only 2 % of the time the model is *underconfident* (intervals too wide).

OpenSTEF includes an ``IsotonicQuantileCalibrator`` post-processing transform that corrects
systematic calibration errors using isotonic regression on held-out validation data:

.. code-block:: python

    from openstef_models.transforms.postprocessing.isotonic_quantile_calibrator import (
        IsotonicQuantileCalibrator,
    )

    calibrator = IsotonicQuantileCalibrator()
    calibrator.fit(validation_forecast_dataset)
    calibrated_forecast = calibrator.transform(raw_forecast_dataset)

Calibration should be evaluated periodically — model drift, seasonal shifts, and changes in the
load profile can all degrade calibration over time. See :doc:`reliability_and_fallback` for how
OpenSTEF handles degraded model performance in production.

Why Quantiles Matter for Operations
-------------------------------------

Point forecasts hide uncertainty. A single number gives no indication of whether the forecast
could plausibly be 10 MW higher or 100 MW higher. Quantile forecasts make that uncertainty
explicit and actionable:

- **Congestion management** — use Q0.95 as a conservative upper bound when assessing whether a
  cable or transformer will be overloaded. Acting on the median alone risks missing high-load
  events.

- **Reserve scheduling** — the width of the prediction interval (e.g. Q0.90 − Q0.10) directly
  informs how much upward and downward reserve capacity to procure.

- **Imbalance cost reduction** — asymmetric cost structures (buying imbalance is cheaper than
  selling) mean the optimal bid is not the median but a quantile that minimises expected cost.
  Quantile forecasts let you choose the right operating point.

- **Anomaly detection** — an actual measurement that falls outside the Q0.01–Q0.99 band is a
  strong signal of a sensor fault or an unusual event, independent of the point forecast error.

A Baseline for Comparison
---------------------------

When evaluating a new model it is useful to compare against a naive probabilistic baseline.
OpenSTEF provides ``ConstantMedianForecaster``, which predicts the historical quantile values
from the training set as flat lines for all future time steps:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.forecasters.constant_median import ConstantMedianForecaster

    baseline = ConstantMedianForecaster(
        quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
        horizons=[LeadTime(timedelta(hours=24))],
    )
    baseline.fit(training_dataset)
    baseline_forecast = baseline.predict(forecast_input_dataset)

Any production model should substantially outperform this baseline on both point-forecast accuracy
and interval calibration before being deployed.

Related Topics
---------------

- :doc:`forecasting_basics` — introduction to the forecasting problem and lead times
- :doc:`feature_engineering` — how weather and calendar features drive forecast uncertainty
- :doc:`reliability_and_fallback` — what happens when a model's quantile forecasts degrade
- :doc:`meta_ensembles` — combining multiple models to improve both accuracy and calibration
- :doc:`component_splitting` — how quantile forecasts extend to decomposed load components