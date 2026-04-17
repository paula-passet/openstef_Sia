Reliability and Fallback Strategies
====================================

In production energy forecasting, models encounter conditions they were never designed to handle: sensors go silent, data pipelines stall, weather feeds arrive late, or a model trained weeks ago drifts out of alignment with current grid behaviour. This page covers how OpenSTEF's library components help you detect these conditions early and degrade gracefully rather than silently producing bad forecasts.

.. note::

   This page focuses on production reliability patterns. For an introduction to
   how forecasts are generated in the first place, see :doc:`forecasting_basics`.
   For understanding the uncertainty bounds that accompany forecasts, see
   :doc:`quantiles_and_confidence`.


Why Graceful Degradation Matters
---------------------------------

A forecast that fails loudly is far easier to manage than one that silently returns plausible-looking but wrong numbers. In practice, the most dangerous failure modes are not crashes — they are:

- A sensor stuck at a constant value that gets fed into a model as real data.
- A feature column that is 80 % NaN because an upstream pipeline is degraded.
- A model trained three weeks ago that has never been retrained since a major load shift.
- A primary data source that is unavailable, leaving the model with no recent history.

OpenSTEF provides built-in transforms and fallback models that address each of these scenarios explicitly.


Detecting Bad Input Data
-------------------------

Before a forecast is produced, the input data should be validated. OpenSTEF ships three validation transforms in ``openstef_models.transforms.validation`` that can be composed into any preprocessing pipeline.

**Completeness checking**

:class:`~openstef_models.transforms.validation.CompletenessChecker` measures the ratio of non-missing values across the input columns and raises ``InsufficientlyCompleteError`` if the dataset falls below a configurable threshold. You can weight individual columns to reflect their relative importance — for example, the load target column might carry more weight than an optional weather feature.

.. code-block:: python

   from datetime import timedelta
   import numpy as np
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker
   from openstef_core.exceptions import InsufficientlyCompleteError

   data = pd.DataFrame(
       {
           "load": [100.0, np.nan, 105.0, np.nan],
           "temperature": [15.0, 16.0, np.nan, 18.0],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min"),
   )
   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   checker = CompletenessChecker(
       columns=["load", "temperature"],
       weights={"load": 2.0, "temperature": 1.0},  # load matters more
       completeness_threshold=0.6,
   )

   try:
       checker.transform(dataset)
   except InsufficientlyCompleteError as exc:
       # Route to fallback logic here
       print(f"Data too sparse to forecast reliably: {exc}")

The transform returns the dataset unchanged when the threshold is met, making it safe to place inline in a pipeline without altering the data.

**Flatline detection**

A sensor that has stopped reporting real measurements often produces a perfectly constant stream of values rather than going fully silent. This is a particularly insidious failure because the data *looks* complete. :class:`~openstef_models.transforms.validation.FlatlineChecker` detects this pattern by checking whether the load column has remained constant (within a configurable tolerance) for longer than a specified duration.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import FlatlineChecker
   from openstef_core.exceptions import FlatlinerDetectedError

   # Simulate a stuck sensor: load frozen at 110 for 3 hours
   data = pd.DataFrame(
       {"load": [100.0, 110.0, 110.0, 110.0, 110.0]},
       index=pd.date_range("2025-01-01", periods=5, freq="1h"),
   )
   dataset = TimeSeriesDataset(data, timedelta(hours=1))

   checker = FlatlineChecker(
       load_column="load",
       flatliner_threshold=timedelta(hours=2),
       detect_non_zero_flatliner=True,  # catch non-zero stuck values
       relative_tolerance=1e-5,
       error_on_flatliner=True,
   )

   try:
       checker.transform(dataset)
   except FlatlinerDetectedError:
       print("Sensor appears stuck — switching to fallback forecast")

Setting ``detect_non_zero_flatliner=True`` is important in practice: a load frozen at 500 kW is just as suspicious as one frozen at zero, but the default behaviour only flags zero-value flatlines.

**Input consistency checking**

When a model is retrained, the set of feature columns it expects may change. :class:`~openstef_models.transforms.validation.InputConsistencyChecker` validates at inference time that the incoming data contains all features the model was fitted on, logging warnings for unexpected extra columns and raising an error for missing ones. This catches silent schema drift between training and serving.

.. code-block:: python

   from openstef_models.transforms.validation import InputConsistencyChecker

   consistency_checker = InputConsistencyChecker()
   # Fit on training data to record expected feature names
   consistency_checker.fit(training_dataset)
   # At inference time, validate incoming data
   consistency_checker.transform(inference_dataset)


The Base-Case Fallback Model
-----------------------------

When validation checks fail — or when a primary model is unavailable — you need a fallback that can still produce a reasonable forecast. OpenSTEF provides :class:`~openstef_models.models.forecasting.BaseCaseForecaster` for exactly this purpose.

The base-case forecaster is a deliberately simple model: it repeats the most recent week of historical load data as the forecast, on the assumption that energy consumption follows a weekly periodic pattern. This assumption is crude but surprisingly robust as a last resort. It also produces confidence intervals by computing hourly standard deviations from the repeated pattern.

The model implements a two-tier lag strategy:

- **Primary lag** (default: 7 days) — uses last week's data directly.
- **Fallback lag** (default: 14 days) — used automatically when primary lag data is not available, for example when the primary data source has been down for several days.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

The base-case forecaster is not intended to replace a well-trained ML model under normal conditions. Its role is to ensure that *something sensible* is always returned even when the primary model cannot be used.

.. note::

   The base-case forecaster serves as a useful benchmark as well as a fallback.
   If your primary model cannot consistently outperform it, that is a signal
   worth investigating.


Handling Missing Features at Inference Time
--------------------------------------------

Even when the model itself is healthy, individual feature columns may be missing or partially NaN at inference time — for example, a weather provider may be temporarily unavailable. OpenSTEF's imputation transforms handle this within the pipeline.

The ``Imputer`` transform supports both simple strategies (mean, median, most-frequent, constant) and an iterative Bayesian strategy that uses other features as predictors for imputation. For production use, the iterative strategy is more accurate but slower; the simple strategies are more robust under heavy data loss.

A key configuration decision is ``fill_future_values``: by default, the imputer does *not* fill future missing values in order to preserve time series integrity. You should only enable this for features where forward-filling is genuinely appropriate (for example, a slowly varying temperature forecast that arrives with a short delay).

.. note::

   .. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd


Composing a Robust Inference Pipeline
---------------------------------------

In practice, these components are most useful when composed into a single pipeline that runs before every forecast. A typical production pattern looks like this:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.exceptions import (
       InsufficientlyCompleteError,
       FlatlinerDetectedError,
   )
   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker,
   )

   def produce_forecast(dataset, primary_model, fallback_model):
       """Attempt primary forecast with validation; fall back gracefully."""

       # Step 1: Check for stuck sensors
       flatline_checker = FlatlineChecker(
           flatliner_threshold=timedelta(hours=3),
           detect_non_zero_flatliner=True,
           error_on_flatliner=True,
       )

       # Step 2: Check data completeness
       completeness_checker = CompletenessChecker(
           completeness_threshold=0.7,
       )

       try:
           flatline_checker.transform(dataset)
           completeness_checker.transform(dataset)
           # Data looks healthy — use the primary model
           return primary_model.predict(dataset)

       except FlatlinerDetectedError:
           # Sensor is stuck; primary data is untrustworthy
           import logging
           logging.warning("Flatline detected — using base-case fallback")
           return fallback_model.predict(dataset)

       except InsufficientlyCompleteError:
           # Too many NaNs to trust the primary model
           import logging
           logging.warning("Insufficient data completeness — using base-case fallback")
           return fallback_model.predict(dataset)

This pattern keeps the fallback logic explicit and auditable. Every time the fallback is invoked, a warning is logged with a reason, making it straightforward to monitor fallback rates in production dashboards.


Model Staleness
----------------

A model that was accurate when trained may become stale as load patterns shift — due to new large consumers connecting to the grid, seasonal changes, or structural changes in consumption behaviour. OpenSTEF does not automatically detect staleness, but the library gives you the tools to build detection into your workflow:

- **Track forecast error over time.** Compare the model's predictions against actuals as they arrive. A sustained increase in mean absolute error is a reliable staleness signal.
- **Monitor feature drift.** If the distribution of input features (particularly load history) shifts significantly from the training distribution, model performance will degrade. The ``InputConsistencyChecker`` catches schema changes; statistical drift requires separate monitoring.
- **Set a maximum model age policy.** For most grid applications, retraining weekly or fortnightly is sufficient. Models older than a month should be treated with suspicion regardless of observed error metrics.

.. warning::

   A stale model will not raise an exception — it will silently produce forecasts
   that look plausible but are systematically biased. Monitoring forecast error
   against actuals is the only reliable way to detect this condition.


Summary
--------

OpenSTEF provides a layered approach to production reliability:

- :class:`~openstef_models.transforms.validation.FlatlineChecker` — detects stuck sensors before bad data enters the model.
- :class:`~openstef_models.transforms.validation.CompletenessChecker` — rejects datasets that are too sparse to forecast reliably.
- :class:`~openstef_models.transforms.validation.InputConsistencyChecker` — catches feature schema drift between training and serving.
- :class:`~openstef_models.models.forecasting.BaseCaseForecaster` — provides a robust weekly-pattern fallback when the primary model cannot be used.

Used together, these components allow you to build forecasting services that fail loudly when something is wrong, fall back gracefully when possible, and give operators clear signals about what went wrong and why.

For background on the features that feed into these models, see :doc:`feature_engineering`. For details on how uncertainty is expressed in fallback forecasts, see :doc:`quantiles_and_confidence`.