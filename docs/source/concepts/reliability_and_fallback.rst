Reliability and Fallback Strategies
====================================

In production energy forecasting, models will occasionally fail — data pipelines break,
sensors go offline, and models trained on historical patterns encounter conditions they
have never seen. This page covers how OpenSTEF is designed to handle these situations
gracefully, from built-in data quality checks to fallback forecasting strategies and
model staleness detection.

For background on the forecasting models themselves, see :doc:`model_selection`. For
details on probabilistic outputs and confidence intervals, see
:doc:`quantiles_and_confidence`.

.. mermaid:: diagrams/concepts/reliability_and_fallback_diagram_1.mmd

----

Data Quality Validation
------------------------

Before a forecast is ever generated, OpenSTEF applies a pipeline of validation
transforms to incoming data. These checks catch the most common failure modes in
real-world time series feeds: missing values, stuck sensors, and feature drift.

**Completeness checking**

The ``CompletenessChecker`` transform measures what fraction of expected values are
present in the dataset. If the data falls below an acceptable completeness threshold,
it raises ``InsufficientlyCompleteError`` rather than silently producing a forecast
from sparse or misleading inputs.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker

    # Simulate a feed with heavy dropout — only 25% of values present
    data = pd.DataFrame(
        {
            "radiation":    [100, np.nan, np.nan, np.nan],
            "temperature":  [20,  np.nan, 24,     np.nan],
            "wind_speed":   [np.nan, np.nan, np.nan, np.nan],
        },
        index=pd.date_range("2025-01-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    checker = CompletenessChecker()
    try:
        checker.transform(dataset)
    except Exception as e:
        # InsufficientlyCompleteError: The dataset is not sufficiently complete.
        # Completeness: 0.25
        print(f"Validation failed: {e}")
        # → trigger fallback logic here

You can scope the check to specific columns and assign weights to reflect which
features are most critical for your application.

**Flatline detection**

A stuck sensor often looks like valid data — values are present but unchanging. The
``FlatlineChecker`` transform detects these "flatliner" patterns in the target load
column. In the default workflow configuration, a detected flatline logs a warning but
does not halt the pipeline (``error_on_flatliner=False``), giving operators visibility
without causing a hard failure during inference.

.. code-block:: python

    from openstef_models.transforms.validation import FlatlineChecker

    flatline_checker = FlatlineChecker(
        load_column="load",
        flatliner_threshold=6,       # consecutive identical readings
        detect_non_zero_flatliner=True,
        error_on_flatliner=False,    # warn, don't raise
    )

**Input consistency checking**

When a model is deployed, the feature set it was trained on must match what arrives at
inference time. ``InputConsistencyChecker`` validates that column names and ordering are
consistent between training and serving. Extra columns are removed with a warning;
missing expected columns will surface as an error before any prediction is attempted.

These three validators — ``CompletenessChecker``, ``FlatlineChecker``, and
``InputConsistencyChecker`` — are composed automatically inside the
``EnsembleForecastingWorkflow``, so you get this protection without extra wiring.

----

The Base Case Forecaster: A Built-In Fallback
----------------------------------------------

When a primary model cannot produce a forecast — because validation has failed, the
model has not yet been trained, or an unexpected error has occurred — OpenSTEF provides
a purpose-built fallback: the ``BaseCaseForecaster``.

This model implements the well-established observation that energy load follows a weekly
periodicity. It takes the most recent week of historical target data and repeats it
forward to cover the forecast horizon. If the primary lag window (default: 7 days) is
itself unavailable, it falls back to a secondary window (default: 14 days). Confidence
intervals are derived from hourly standard deviations computed over the repeated
pattern.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    # Standard fallback: repeat last 7 days, fall back to 14 days if unavailable
    fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
    )

    # Custom lag windows — useful when your load pattern has a different periodicity
    fallback_custom = BaseCaseForecaster(
        quantiles=[Quantile(0.5)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

The ``BaseCaseForecaster`` is intentionally simple. Its value in production is not
accuracy — it is *availability*. A forecast that repeats last week's pattern is almost
always more useful to grid operators than no forecast at all, and it provides a
meaningful baseline against which the primary model's skill can be measured. See
:doc:`model_selection` for how OpenSTEF uses this baseline in model comparison.

.. note::

   The ``BaseCaseForecaster`` also produces quantile outputs, so downstream systems
   consuming probabilistic forecasts do not need special handling when the fallback is
   active. See :doc:`quantiles_and_confidence` for details on probabilistic outputs.

----

Model Staleness Detection
--------------------------

A model that was accurate when trained can become unreliable as the underlying system
changes — new generation assets come online, demand patterns shift, or data pipeline
schemas evolve. OpenSTEF addresses this through configurable model age limits and
performance-based model selection.

The ``EnsembleForecastingWorkflowConfig`` exposes a ``model_max_age`` parameter that
sets a hard upper bound on how old a persisted model can be before it is considered
stale and must be retrained rather than reused:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.workflows.ensemble_forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
    )

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        base_models=["lgbm", "xgboost"],
        horizons=[...],
        quantiles=[...],
        # Refuse to reuse any model older than 30 days
        model_max_age=timedelta(days=30),
        # Allow reuse of younger models when performance is acceptable
        model_reuse_enable=True,
        # Bias selection toward newer models even if the old model scores slightly better
        model_selection_old_model_penalty=1.2,
        model_selection_metric=("Q0.5", "R2", "higher_is_better"),
    )

The ``model_selection_old_model_penalty`` parameter is worth highlighting. Setting it
above 1.0 means that when comparing a newly trained model against a stored one, the
stored model's metric is penalised by that factor before comparison. This implements a
deliberate bias toward freshness: a model must be meaningfully *better* than a new
candidate to justify reuse, rather than merely equivalent.

.. note::

   Model age tracking relies on timestamps stored alongside the model artifact. If you
   are integrating OpenSTEF into a custom MLflow or storage backend, ensure that
   training timestamps are persisted correctly so that ``model_max_age`` enforcement
   works as expected.

----

Graceful Degradation in Practice
----------------------------------

The reliability mechanisms described above compose into a natural degradation hierarchy
that mirrors how experienced operators think about forecast availability:

1. **Primary model with validated data** — the normal operating mode. All validation
   transforms pass, the trained ensemble model produces a probabilistic forecast.

2. **Primary model with degraded data** — some features are missing or incomplete, but
   the model can still produce a forecast. ``InputConsistencyChecker`` removes
   unexpected columns; the model runs on the reduced feature set with a warning logged.

3. **Validation failure** — ``InsufficientlyCompleteError`` is raised. The calling
   application catches this and invokes the ``BaseCaseForecaster`` on whatever
   historical data is available.

4. **No trained model available** — the model is absent, too old (``model_max_age``
   exceeded), or has never been trained. The workflow triggers retraining if a training
   dataset is available, or falls back to the base case forecaster in the interim.

A minimal pattern for implementing this hierarchy in application code:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_models.models.forecasting.base_case import BaseCaseForecaster
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    QUANTILES = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
    HORIZONS  = [LeadTime(timedelta(hours=h)) for h in range(1, 49)]

    def get_forecast(primary_model, forecast_dataset, history_dataset):
        """Attempt primary forecast, fall back to base case on failure."""
        try:
            return primary_model.predict(forecast_dataset)
        except InsufficientlyCompleteError as e:
            import logging
            logging.warning("Primary forecast failed due to data quality: %s. "
                            "Activating base case fallback.", e)
            fallback = BaseCaseForecaster(quantiles=QUANTILES, horizons=HORIZONS)
            fallback.fit(history_dataset)
            return fallback.predict(forecast_dataset)

.. warning::

   The ``BaseCaseForecaster`` requires sufficient historical data to cover at least the
   primary lag window (7 days by default). If your history dataset is also incomplete,
   ensure the fallback lag (14 days) window is available, or configure shorter lag
   windows appropriate to your data retention policy.

----

Operational Recommendations
-----------------------------

Drawing from production deployments, a few practices consistently improve reliability:

- **Monitor completeness metrics continuously.** Log the completeness score returned
  by ``CompletenessChecker`` as a time series metric. Gradual degradation in data
  quality is often visible days before it causes a forecast failure.

- **Set ``model_max_age`` conservatively at first.** A 30-day maximum is a reasonable
  starting point for most grid assets. Tighten it for assets with rapidly changing
  behaviour (e.g., substations serving new EV charging infrastructure).

- **Treat flatline warnings as actionable alerts.** A ``FlatlineChecker`` warning
  during inference almost always indicates a sensor or SCADA issue upstream. Route
  these warnings to your monitoring system rather than only to application logs.

- **Keep base case forecasts in your output store.** Even when the primary model is
  healthy, periodically computing and storing base case forecasts gives you an
  immediate fallback without a cold-start fitting step during an incident.

- **Test your fallback path.** Deliberately inject incomplete data in a staging
  environment to verify that ``InsufficientlyCompleteError`` is caught and the
  ``BaseCaseForecaster`` activates correctly. Fallback paths that are never exercised
  tend to break silently.

For details on the features that feed into the primary model — and which features are
most critical to preserve when data is degraded — see :doc:`feature_engineering`.