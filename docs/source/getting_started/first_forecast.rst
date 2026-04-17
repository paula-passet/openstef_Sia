Your First Forecast
===================

This tutorial walks you through producing a real short-term energy forecast with OpenSTEF from scratch. By the end you will have loaded data, configured a feature-engineering pipeline, trained a model, generated predictions, and evaluated the result — with a clear explanation of *why* each step exists, not just *how* to run it.

If you just want the shortest possible working script, see :doc:`quickstart`. Come back here when you want to understand what is actually happening inside the library.

.. note:: [DIAGRAM: Step-by-step flowchart showing the five stages of a forecast run — (1) Data Preparation → (2) Feature Engineering → (3) Model Training → (4) Prediction → (5) Evaluation — connected by arrows. Decision points include: after Data Preparation, a check for sufficient coverage and consistent sample interval; after Model Training, a check on fit result status (success / flatliner detected / skip); after Prediction, a branch for whether evaluation data is available.]

Overview
--------

OpenSTEF structures every forecast run around three objects that work together:

- A **dataset** (``TimeSeriesDataset`` or ``VersionedTimeSeriesDataset``) that holds your time series and any exogenous features.
- A **workflow configuration** (``ForecastingWorkflowConfig``) that describes the model type, forecast horizons, quantiles, and feature-engineering settings.
- A **workflow** (``CustomForecastingWorkflow``) that orchestrates preprocessing → training → prediction as a single, reproducible pipeline.

Understanding this separation makes it much easier to swap in your own data, change models, or extend the pipeline later.


Step 1 — Prepare Your Data
---------------------------

OpenSTEF expects time series data as a ``TimeSeriesDataset``: a thin wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex`` and a known sample interval. The library ships a helper, ``create_synthetic_forecasting_dataset``, that generates realistic load data with configurable weather influences. It is ideal for following this tutorial without needing a live data feed.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.testing import create_synthetic_forecasting_dataset

    # Nine months of hourly data — enough history for lag features and
    # a meaningful train/test split.
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=270),
        sample_interval=timedelta(hours=1),
        wind_influence=-10.0,
        temp_influence=5.0,
        radiation_influence=-7.0,
        stochastic_influence=2.0,
    )

    print(dataset.feature_names)   # ['load', 'wind_speed', 'temperature', ...]
    print(dataset.sample_interval) # 0:01:00

The resulting ``TimeSeriesDataset`` contains a ``load`` column (the forecast target) alongside weather features. When you bring your own data, construct the dataset the same way:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    df = pd.read_csv("my_load_data.csv", index_col="timestamp", parse_dates=True)
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Two things matter most at this stage: the index must be a ``DatetimeIndex`` with a consistent frequency, and every feature column you want the model to use must already be present. OpenSTEF does not fetch weather data for you — it engineers *derived* features (lags, cyclic encodings, holiday flags) from whatever you provide.


Step 2 — Configure the Workflow
--------------------------------

Rather than constructing a model object by hand, you describe what you want through ``ForecastingWorkflowConfig`` and let the library build the pipeline. This keeps configuration declarative and serialisable.

.. code-block:: python

    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    config = ForecastingWorkflowConfig(
        model_id="my_first_forecast_v1",
        model="xgboost",
        horizons=[LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
    )

    workflow = create_forecasting_workflow(config=config)

A few decisions worth understanding here:

**Model type.** ``"xgboost"`` is a good default for energy load forecasting — it handles non-linear weather interactions well and is robust to missing features. Other options include ``"lgbm"``, ``"gblinear"``, ``"flatliner"``, and ``"median"``.

**Horizons.** ``LeadTime`` values specify how far ahead you want to forecast. The pipeline will engineer lag features that are consistent with each horizon, so you never accidentally leak future information into training.

**Quantiles.** Requesting ``Q(0.1)`` and ``Q(0.9)`` alongside the median ``Q(0.5)`` gives you a prediction interval — useful for grid planning where you need to know the range of plausible outcomes, not just the point estimate.

``create_forecasting_workflow`` assembles the full preprocessing pipeline behind the scenes: lag transforms, cyclic time features, holiday indicators, and data-quality checks are all wired up automatically based on the config.

.. note::

   If you need fine-grained control over which features are added or want to inject custom transforms, see :doc:`advanced_customization`.


Step 3 — Train the Model
-------------------------

Training is a single call. The workflow fits the preprocessing pipeline and the underlying forecaster on the same dataset:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.INFO)

    fit_result = workflow.fit(dataset)

    if fit_result is not None:
        print("Training complete.")
        print(fit_result)

``workflow.fit`` returns a ``ModelFitResult`` that summarises what happened — including whether a flatliner was detected (a common data-quality issue where the load signal is constant) or whether training was skipped because a recent model already exists in storage. Checking this result is good practice before proceeding to prediction.

Internally, the workflow runs through several sub-steps automatically:

1. **Data validation** — checks completeness and detects flatliners.
2. **Feature engineering** — adds lag features, cyclic encodings, holiday flags, and derived meteorological features.
3. **Forecaster training** — fits the XGBoost (or other) model on the engineered feature matrix.
4. **Postprocessing** — stores metadata and, if configured, persists the model to storage.

You do not need to call these steps individually; the workflow handles sequencing and error propagation.


Step 4 — Generate Forecasts
----------------------------

Once the model is fitted, call ``predict`` with the same (or newer) dataset. The workflow re-runs preprocessing on the prediction data and returns a ``ForecastDataset``:

.. code-block:: python

    forecasts = workflow.predict(dataset)

    # ForecastDataset wraps a DataFrame with columns for each quantile
    print(forecasts.data.head())

The ``forecast_start`` parameter lets you pin the start of the forecast window if you want predictions from a specific point in time rather than the end of the dataset:

.. code-block:: python

    from datetime import datetime, timezone

    forecasts = workflow.predict(
        dataset,
        forecast_start=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )

The returned ``ForecastDataset`` contains one column per requested quantile (e.g. ``q0.1``, ``q0.5``, ``q0.9``) indexed by timestamp. Each row represents a single forecast step at the lead time the model was trained for.

.. note::

   ``predict`` applies the *same* preprocessing transforms that were fitted during training, so there is no risk of inconsistent feature scaling or lag computation between training and inference.


Step 5 — Evaluate the Result
------------------------------

The workflow exposes a ``score`` method that computes performance metrics against observed values. Because ``score`` uses the same preprocessing pipeline as ``predict``, the metrics reflect real-world performance rather than in-sample training accuracy:

.. code-block:: python

    metrics = workflow.score(dataset)
    print(metrics)

The returned ``SubsetMetric`` object breaks down performance by horizon and quantile. For a quick sanity check, look at the R² score for the median quantile at your primary horizon — values above 0.85 are typical for well-configured energy load models with good weather data.

To visualise the forecasts alongside actuals, use the built-in plotter:

.. code-block:: python

    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

    plotter = ForecastTimeSeriesPlotter()
    plotter.plot(forecasts)

This renders an interactive time series chart with the median forecast and shaded quantile bands, without requiring any manual matplotlib configuration.


Putting It All Together
------------------------

Here is the complete script for reference:

.. code-block:: python

    import logging
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")

    # 1. Prepare data
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=270),
        sample_interval=timedelta(hours=1),
        wind_influence=-10.0,
        temp_influence=5.0,
        radiation_influence=-7.0,
        stochastic_influence=2.0,
    )

    # 2. Configure the workflow
    config = ForecastingWorkflowConfig(
        model_id="my_first_forecast_v1",
        model="xgboost",
        horizons=[LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
    )
    workflow = create_forecasting_workflow(config=config)

    # 3. Train
    fit_result = workflow.fit(dataset)

    # 4. Predict
    forecasts = workflow.predict(dataset)
    print(forecasts.data.tail())

    # 5. Evaluate
    metrics = workflow.score(dataset)
    print(metrics)

    # 6. Visualise
    plotter = ForecastTimeSeriesPlotter()
    plotter.plot(forecasts)


Common Issues
--------------

**Insufficient history for lag features.** If your dataset covers fewer days than the longest lag in the preprocessing pipeline, the first rows of the feature matrix will contain NaN values and training will fail or produce poor results. Aim for at least 90 days of history when using default lag settings.

**Inconsistent sample interval.** ``TimeSeriesDataset`` validates that the index frequency matches the declared ``sample_interval``. If your data has gaps or irregular timestamps, resample it to a regular grid before constructing the dataset.

**Flatliner detection.** If the load column is constant for a sustained period, the workflow will log a warning and may skip training. This is intentional — a flatliner usually indicates a data-quality problem rather than a genuine flat load profile.


Next Steps
-----------

Now that you have a working forecast, you can explore:

- :doc:`backtesting` — evaluate your model rigorously across multiple historical windows to get unbiased performance estimates.
- :doc:`advanced_customization` — replace the default preprocessing pipeline, add custom feature transforms, or plug in your own forecaster implementation.