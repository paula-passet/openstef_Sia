Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with OpenSTEF, from raw time series data to evaluated predictions. Each step explains not just *how* to do something, but *why* it matters for forecasting accuracy.

If you just want the shortest possible working example, see :doc:`quickstart` first. This page goes deeper — covering data preparation, feature engineering choices, model configuration, and evaluation in detail. Once you're comfortable here, :doc:`advanced_customization` shows how to extend and replace individual pipeline components.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF is a **library** — it provides composable building blocks that you assemble into a forecasting pipeline suited to your data and use case. The core workflow always follows the same pattern:

1. Wrap your data in a ``VersionedTimeSeriesDataset``
2. Configure a ``ForecastingModel`` with preprocessing and a forecaster
3. Train with ``CustomForecastingWorkflow.fit()``
4. Generate forecasts with ``workflow.predict()``
5. Evaluate the results

The sections below work through each step with a concrete electricity load forecasting example.

Step 1: Preparing Your Data
---------------------------

OpenSTEF expects time series data as a ``VersionedTimeSeriesDataset``. This structure carries your observations alongside metadata that the pipeline uses to reason about forecast horizons and feature alignment.

At minimum you need a **target column** (the quantity you want to forecast — typically electrical load in MW) and a **datetime index** at a consistent sample interval. Weather covariates such as temperature, wind speed, and solar radiation are optional but significantly improve accuracy for most energy applications.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Build a synthetic dataset: two years of hourly load + temperature
    rng = np.random.default_rng(42)
    n_hours = 24 * 365 * 2  # two years

    index = pd.date_range("2023-01-01", periods=n_hours, freq="h")

    # Simulate a realistic load profile: daily and weekly seasonality + noise
    hour_of_day = index.hour
    day_of_week = index.dayofweek
    base_load = (
        50.0
        + 20.0 * np.sin(2 * np.pi * hour_of_day / 24)   # daily cycle
        - 10.0 * (day_of_week >= 5).astype(float)         # weekend dip
        + rng.normal(scale=3.0, size=n_hours)              # noise
    )
    temperature = 10.0 + 8.0 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 365)) + rng.normal(scale=2.0, size=n_hours)

    data = pd.DataFrame(
        {"load": base_load, "temperature": temperature},
        index=index,
    )

    dataset = VersionedTimeSeriesDataset(
        data=data,
        sample_interval=timedelta(hours=1),
    )

A few things to check before moving on:

- **No gaps in the index.** Missing timestamps confuse lag-based features. Resample and fill short gaps before wrapping in a dataset.
- **Consistent units.** Load in MW, temperature in °C — mixing units silently degrades model quality.
- **Enough history.** Lag features look back days or weeks. Two or more weeks of history is a practical minimum; months to years gives the model seasonal context.

Step 2: Configuring the Model
------------------------------

OpenSTEF's ``ForecastingModel`` is a pipeline: preprocessing transforms run first, then the forecaster, then optional postprocessing. You configure each layer explicitly, which makes it easy to swap components without rewriting the rest of your code.

The example below uses a ``ConstantMedianForecaster`` — a simple but useful baseline that predicts the historical median for each horizon. It is a good starting point because it is fast to train and its accuracy sets a floor that a more complex model should beat.

.. code-block:: python

    from openstef_core.types import LeadTime, Q
    from openstef_models.models.forecasting.constant_median_forecaster import (
        ConstantMedianForecaster,
    )
    from openstef_models.models.forecasting_model import ForecastingModel

    # Define the forecast horizons you care about
    # Here: predict 24 h and 48 h ahead
    horizons = [
        LeadTime.from_string("PT24H"),
        LeadTime.from_string("PT48H"),
    ]

    # Quantiles determine the probabilistic output bands
    quantiles = [Q(0.1), Q(0.5), Q(0.9)]

    forecaster = ConstantMedianForecaster(
        horizons=horizons,
        quantiles=quantiles,
    )

    model = ForecastingModel(forecaster=forecaster)

**Why probabilistic forecasts?** Energy system operators need uncertainty bands, not just point estimates. The 10th and 90th percentile outputs let downstream systems reason about best- and worst-case scenarios. The median (Q(0.5)) is your point forecast.

**Choosing horizons.** Set horizons to match your operational need. Day-ahead scheduling typically requires a 24 h horizon; intra-day balancing might need 1–6 h. Each horizon is trained and evaluated independently within the same model.

Step 3: Adding Feature Engineering
------------------------------------

Raw load and temperature values alone are rarely sufficient. OpenSTEF's preprocessing pipeline adds derived features that capture the patterns most predictive of energy demand: lag values, cyclic time encodings, and weather-derived quantities.

Wrap your preprocessing steps in a ``FeaturePipeline`` and pass it to the model. The pipeline is fitted on training data and applied consistently at prediction time — preventing data leakage.

.. code-block:: python

    from openstef_models.pipeline.feature_pipeline import FeaturePipeline
    from openstef_models.transforms.lags import LagsAdder
    from openstef_models.transforms.cyclic import CyclicFeaturesAdder
    from openstef_models.transforms.scaling import StandardScaler

    preprocessing = FeaturePipeline(
        transforms=[
            LagsAdder(
                history_available=timedelta(days=14),
                horizons=horizons,
                target_column="load",
            ),
            CyclicFeaturesAdder(),   # encodes hour-of-day, day-of-week as sin/cos
            StandardScaler(),
        ]
    )

    model = ForecastingModel(
        forecaster=forecaster,
        preprocessing=preprocessing,
        cutoff_history=timedelta(days=14),  # exclude rows where lags are NaN
    )

.. note::

   The ``cutoff_history`` parameter is important when using lag features. A 14-day lag transform produces ``NaN`` values for the first 14 days of your dataset. Setting ``cutoff_history=timedelta(days=14)`` tells the model to skip those rows during training so they do not corrupt the fit.

**What each transform does:**

- ``LagsAdder`` — creates columns for the target value at previous time steps (e.g., load 24 h ago, 48 h ago, 7 days ago). These are typically the strongest predictors for energy load.
- ``CyclicFeaturesAdder`` — encodes periodic time features (hour of day, day of week) as sine/cosine pairs so the model sees that hour 23 and hour 0 are adjacent, not distant.
- ``StandardScaler`` — zero-centres and scales each feature to unit variance, which helps gradient-based and distance-based learners converge faster.

Step 4: Training the Model
---------------------------

Training is orchestrated by ``CustomForecastingWorkflow``, which handles the fit/predict lifecycle and provides hooks for logging, monitoring, and model persistence.

.. code-block:: python

    from openstef_models.workflows.forecasting_workflow import CustomForecastingWorkflow

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="load_forecast_tutorial",
    )

    # Split: use the first 20 months for training, last 4 for validation
    cutoff = pd.Timestamp("2024-09-01")
    train_data = VersionedTimeSeriesDataset(
        data=data.loc[data.index < cutoff],
        sample_interval=timedelta(hours=1),
    )
    val_data = VersionedTimeSeriesDataset(
        data=data.loc[data.index >= cutoff],
        sample_interval=timedelta(hours=1),
    )

    fit_result = workflow.fit(
        data=train_data,
        data_val=val_data,
    )

    print(fit_result)

The ``fit_result`` object contains training diagnostics including in-sample predictions and any validation metrics computed during the fit. Inspect it to confirm the model converged and that validation error is in a sensible range before proceeding to production forecasting.

**Validation split strategy.** For time series, always split chronologically — never randomly. A random split leaks future information into training via lag features, producing optimistically biased metrics that will not hold in production.

Step 5: Generating Forecasts
-----------------------------

Once trained, call ``workflow.predict()`` with a dataset that covers the history window the model needs (for lag computation) plus the future period you want to forecast.

.. code-block:: python

    # Predict over the validation period
    forecasts = workflow.predict(data=val_data)

    # forecasts.data is a DataFrame indexed by (available_at, lead_time, timestamp)
    # with one column per quantile
    print(forecasts.data.head(10))

The returned ``ForecastDataset`` contains probabilistic forecasts for every requested horizon and quantile. The multi-level index records:

- ``available_at`` — when this forecast would have been generated (useful for backtesting)
- ``lead_time`` — how far ahead the forecast looks
- ``timestamp`` — the target datetime being forecast

Step 6: Evaluating Accuracy
----------------------------

Evaluation compares your forecasts against the observed values in the validation dataset. OpenSTEF's built-in scoring computes metrics at each forecast horizon so you can see whether accuracy degrades as you look further ahead — which is expected, but the rate of degradation matters.

.. code-block:: python

    # Score the model directly — no need for external metric libraries
    score = model.score(data=val_data)

    print(score)
    # SubsetMetric with MAE, RMSE, and calibration metrics per horizon

The ``score()`` method runs prediction internally and computes metrics including MAE, RMSE, and observed probability (a calibration measure for probabilistic forecasts). A well-calibrated model should have roughly 80% of observations fall within the 10th–90th percentile band.

**Interpreting results.** For a baseline ``ConstantMedianForecaster``:

- MAE in the range of 5–15% of mean load is typical for a simple baseline on clean data.
- A gradient-boosted model with full weather features will typically halve this error.
- If validation error is much higher than training error, the model is overfitting — consider reducing feature complexity or increasing training data.

Putting It All Together
-----------------------

Here is the complete, self-contained script combining all steps above:

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta

    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.models.forecasting.constant_median_forecaster import (
        ConstantMedianForecaster,
    )
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.pipeline.feature_pipeline import FeaturePipeline
    from openstef_models.transforms.lags import LagsAdder
    from openstef_models.transforms.cyclic import CyclicFeaturesAdder
    from openstef_models.transforms.scaling import StandardScaler
    from openstef_models.workflows.forecasting_workflow import CustomForecastingWorkflow

    # --- Data ---
    rng = np.random.default_rng(42)
    n_hours = 24 * 365 * 2
    index = pd.date_range("2023-01-01", periods=n_hours, freq="h")
    load = (
        50.0
        + 20.0 * np.sin(2 * np.pi * index.hour / 24)
        - 10.0 * (index.dayofweek >= 5).astype(float)
        + rng.normal(scale=3.0, size=n_hours)
    )
    data = pd.DataFrame({"load": load}, index=index)

    cutoff = pd.Timestamp("2024-09-01")
    train_dataset = VersionedTimeSeriesDataset(
        data=data.loc[data.index < cutoff], sample_interval=timedelta(hours=1)
    )
    val_dataset = VersionedTimeSeriesDataset(
        data=data.loc[data.index >= cutoff], sample_interval=timedelta(hours=1)
    )

    # --- Model ---
    horizons = [LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")]
    quantiles = [Q(0.1), Q(0.5), Q(0.9)]

    model = ForecastingModel(
        forecaster=ConstantMedianForecaster(horizons=horizons, quantiles=quantiles),
        preprocessing=FeaturePipeline(
            transforms=[
                LagsAdder(
                    history_available=timedelta(days=14),
                    horizons=horizons,
                    target_column="load",
                ),
                CyclicFeaturesAdder(),
                StandardScaler(),
            ]
        ),
        cutoff_history=timedelta(days=14),
    )

    # --- Train ---
    workflow = CustomForecastingWorkflow(model=model, model_id="my_first_forecast")
    workflow.fit(data=train_dataset, data_val=val_dataset)

    # --- Predict ---
    forecasts = workflow.predict(data=val_dataset)

    # --- Evaluate ---
    score = model.score(data=val_dataset)
    print(score)

Next Steps
----------

You now have a working forecast pipeline. A few directions to explore from here:

- **Persist the trained model** — pass a ``LocalModelStorage`` instance to ``CustomForecastingWorkflow`` so the fitted model survives process restarts. See :doc:`advanced_customization` for storage configuration.
- **Compare models rigorously** — the :doc:`backtesting` tutorial shows how to evaluate multiple model configurations over a rolling time window, which gives a much more reliable accuracy estimate than a single train/test split.
- **Replace the baseline forecaster** — swap ``ConstantMedianForecaster`` for a gradient-boosted or neural model. The rest of the pipeline stays identical. See :doc:`advanced_customization` for guidance on forecaster selection and hyperparameter tuning.
- **Add weather features** — ``WindPowerFeatureAdder``, ``AtmosphereDerivedFeaturesAdder``, and ``RadiationDerivedFeaturesAdder`` are drop-in additions to the ``FeaturePipeline`` that typically reduce forecast error substantially for weather-sensitive loads.