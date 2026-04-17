Reliability and Fallback in Production Forecasting
===================================================

In a production energy forecasting system, things go wrong. Sensors drop out,
upstream data feeds arrive late, models trained on historical patterns encounter
conditions they have never seen, and infrastructure failures can leave a
forecasting service without a freshly trained model for hours or days at a time.
This page explains how OpenSTEF is designed to handle these situations gracefully,
covering the built-in fallback mechanisms, data quality handling, and the patterns
you should adopt when integrating the library into a production pipeline.

For background on what forecasts contain and how uncertainty is represented, see
:doc:`quantiles_and_confidence`. For details on the features that feed into
models, see :doc:`feature_engineering`.

.. note:: [DIAGRAM: Decision tree showing the path from a forecast request through data validation, model availability check, primary forecast attempt, and fallback cascade to the base-case forecaster]

The Fallback Cascade
--------------------

OpenSTEF's reliability strategy is built around a *fallback cascade*: a
sequence of increasingly simple forecasting strategies that activate when the
preferred approach cannot produce a result. Rather than returning an error or
a null forecast, the library degrades gracefully, always producing *something*
useful while signalling that the result is lower quality than normal.

The cascade has three broad levels:

- **Primary model** — a trained ML model (gradient boosting, neural network,
  etc.) with full feature engineering. This is the normal operating mode.
- **Median forecaster** — a simpler statistical model that relies on lag
  features derived from recent observations. It requires less data and fewer
  features than the primary model but still captures recent trends.
- **Base-case forecaster** — a naive model that repeats the most recent weekly
  pattern. It requires only historical target values and no external features
  at all.

The base-case forecaster is the last line of defence. It is intentionally
simple so that it can operate even when weather data, grid topology features,
or other external inputs are completely unavailable.

The Base-Case Forecaster
------------------------

``BaseCaseForecaster`` implements the assumption that energy load follows a
weekly cycle. It takes the last week of historical target data (the
``primary_lag``, defaulting to seven days) and repeats that pattern forward
across the forecast horizon. When even that window is unavailable, it falls
back to data from two weeks ago (``fallback_lag``, defaulting to fourteen
days).

Confidence intervals are derived from the hourly standard deviation of the
repeated base pattern, so the output is still a full probabilistic forecast
with quantiles — not just a point estimate.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case_forecaster import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    # Default: repeat last 7 days, fall back to 14 days if unavailable
    fallback_model = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
    )

    # Tighter fallback window for assets with less stable weekly patterns
    fallback_model_custom = BaseCaseForecaster(
        quantiles=[Quantile(0.5)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

Because ``BaseCaseForecaster`` shares the same ``Forecaster`` interface as
every other model in OpenSTEF, you can slot it into any pipeline that accepts
a forecaster without changing surrounding code.

Handling Missing and Bad Input Data
------------------------------------

Missing data is the most common reliability problem in operational forecasting.
Sensors report stale values, weather API calls time out, and metering data
arrives with gaps. OpenSTEF addresses this at two levels: imputation during
preprocessing and validation at the pipeline boundary.

**Imputation**

The ``Imputer`` transform (from ``openstef_models``) fills gaps in feature
columns before they reach the model. It supports several strategies:

- ``"mean"`` / ``"median"`` / ``"most_frequent"`` — simple column-level statistics
- ``"constant"`` — fill with a fixed value
- ``"iterative"`` — a ``BayesianRidge``-backed iterative imputer that uses
  correlations between features to estimate missing values

.. code-block:: python

    from openstef_models.preprocessing.imputer import Imputer
    from openstef_models.utils.feature_selection import FeatureSelection

    # Impute all features using the mean, but do not fill future (post-forecast-horizon) values
    imputer = Imputer(
        imputation_strategy="mean",
        selection=FeatureSelection.ALL,
        fill_future_values=FeatureSelection.NONE,
    )

The ``fill_future_values`` parameter is important for production integrity.
Setting it to ``NONE`` (the default) prevents the imputer from forward-filling
values beyond the last known observation, which would silently introduce
look-ahead bias or mask the fact that a data feed has gone silent.

.. warning::

   Iterative imputation with only a single feature will automatically fall
   back to the ``initial_strategy`` (default: ``"mean"``). A warning is logged
   when this happens. Monitor your logs for this message — it often indicates
   that a feature feed has failed entirely, leaving only one column with valid
   data.

**Pipeline-level validation**

Before training, OpenSTEF's pipeline validates that enough target data remains
after NaN rows are dropped. If the training set is empty after this step, an
``InsufficientlyCompleteError`` is raised rather than silently fitting a model
on no data:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_models.pipelines.forecast_pipeline import ForecastPipeline

    pipeline = ForecastPipeline(forecaster=my_model)

    try:
        pipeline.fit(training_data)
    except InsufficientlyCompleteError as exc:
        # Log the failure, then activate the fallback model
        logger.error("Training aborted — insufficient data: %s", exc)
        pipeline = ForecastPipeline(forecaster=fallback_model)

Catching ``InsufficientlyCompleteError`` is the recommended hook for
programmatically switching to a simpler model when training data quality is
too poor to trust the result.

Model Staleness Detection
--------------------------

A model that was trained weeks ago on summer data should not be trusted to
forecast winter peak demand without retraining. Staleness is a subtler failure
mode than a hard error — the model still runs and produces numbers, but those
numbers may be systematically wrong.

OpenSTEF does not enforce a hard staleness cutoff, because the right threshold
depends on the asset and the rate of concept drift in your data. Instead, the
library gives you the tools to detect and act on staleness in your own
orchestration layer.

The recommended approach is to track the training timestamp alongside each
deployed model and compare it against the current time at forecast generation:

.. code-block:: python

    from datetime import datetime, timedelta, timezone

    MAX_MODEL_AGE = timedelta(days=7)

    def is_model_stale(trained_at: datetime, threshold: timedelta = MAX_MODEL_AGE) -> bool:
        """Return True if the model was trained more than `threshold` ago."""
        age = datetime.now(tz=timezone.utc) - trained_at
        return age > threshold

    def get_forecaster(model_registry, asset_id: str, fallback_model):
        record = model_registry.load(asset_id)
        if is_model_stale(record.trained_at):
            logger.warning(
                "Model for asset %s is stale (trained %s). Using fallback.",
                asset_id,
                record.trained_at.isoformat(),
            )
            return fallback_model
        return record.model

In addition to age-based staleness, consider monitoring model performance
metrics over time using the evaluation pipeline (``openstef_beam.evaluation``).
A sudden increase in forecast error — even from a recently trained model — can
indicate that the underlying data distribution has shifted and retraining is
needed sooner than scheduled.

Frequency Mismatch and Feature Drift
--------------------------------------

Two runtime errors that commonly surface in production deserve special
attention because they are easy to miss during development.

**Frequency mismatch** occurs when the time series passed to a fitted model
has a different sample interval than the data the model was trained on. The
``MedianForecaster`` raises a ``ValueError`` explicitly in this case:

.. code-block:: python

    # ValueError: Input data frequency does not match model frequency (0:15:00).
    # Please ensure the input data index has the correct frequency set.

Always set the ``freq`` attribute on your ``DatetimeIndex`` before passing
data to a fitted model. If your upstream data source does not guarantee a
regular cadence, resample or reindex explicitly before forecasting.

**Missing lag features** occur when the feature engineering pipeline that was
used at training time produces a different set of columns than the one used at
inference time. The ``MedianForecaster`` raises a ``ValueError`` listing the
missing columns:

.. code-block:: python

    # ValueError: The input data is missing the following lag features: {'load_lag_96', 'load_lag_192'}

This typically happens when a data feed goes silent long enough that the lag
window cannot be computed. The correct response is to either impute the missing
lag values (using ``Imputer``) or activate the base-case forecaster, which
does not depend on lag features at all.

Graceful Degradation in Practice
----------------------------------

Putting the pieces together, a robust production forecast function looks
roughly like this:

.. code-block:: python

    import logging
    from datetime import timedelta, timezone, datetime
    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case_forecaster import BaseCaseForecaster

    logger = logging.getLogger(__name__)

    QUANTILES = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
    HORIZONS = [LeadTime(timedelta(hours=h)) for h in range(1, 49)]

    base_case = BaseCaseForecaster(quantiles=QUANTILES, horizons=HORIZONS)

    def produce_forecast(pipeline, data, trained_at: datetime):
        """Attempt a primary forecast; fall back gracefully on failure."""

        # 1. Staleness check
        if is_model_stale(trained_at, threshold=timedelta(days=7)):
            logger.warning("Primary model is stale; using base-case forecaster.")
            return base_case.predict(data)

        # 2. Attempt primary forecast
        try:
            return pipeline.predict(data)
        except (ValueError, AttributeError) as exc:
            # Covers frequency mismatch, missing features, unfitted model
            logger.error("Primary forecast failed (%s); using base-case forecaster.", exc)
            return base_case.predict(data)

.. note::

   The base-case forecaster still requires a minimum of ``primary_lag`` worth
   of historical target data (seven days by default). If even that is
   unavailable — for example, on a brand-new asset — you will need to handle
   the ``InsufficientlyCompleteError`` from the base-case forecaster itself
   and decide on a domain-appropriate default (e.g., a flat forecast at
   installed capacity or zero).

Summary
-------

OpenSTEF's reliability model rests on three pillars:

- **Layered fallback** — ``BaseCaseForecaster`` provides a last-resort
  forecast that requires only historical target values, no external features.
- **Explicit data validation** — ``InsufficientlyCompleteError`` and
  ``ValueError`` surface data quality problems as catchable exceptions rather
  than silent bad outputs.
- **Imputation as a first-class transform** — the ``Imputer`` preprocessor
  handles gaps in feature data before they reach the model, with configurable
  strategies and explicit control over whether future values are filled.

Combining these tools with staleness checks in your orchestration layer gives
you a forecasting service that degrades predictably rather than failing
silently — which, in an operational grid context, is often more valuable than
marginal accuracy improvements in the happy path.