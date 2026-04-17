Your First Forecast
===================

This tutorial walks through every step of producing a short-term energy forecast with OpenSTEF: loading data, configuring a pipeline, training a model, generating predictions, and evaluating the result. Each step explains not just *how* to call the API but *why* that step exists and what it contributes to the overall workflow.

If you want the absolute shortest path to a working forecast without the explanations, see :doc:`quickstart`. For comparing multiple models against each other, see :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

A complete OpenSTEF forecast involves five stages:

- **Data preparation** — assemble a :class:`~openstef_core.datasets.TimeSeriesDataset` with your target load series and any exogenous features (weather, price, etc.).
- **Feature engineering** — a :class:`~openstef_models.models.forecasting_model.ForecastingModel` wraps a preprocessing pipeline that adds lag features, holiday indicators, cyclic time encodings, and domain-derived signals automatically during ``fit`` and ``predict``.
- **Model training** — call ``fit()`` on the workflow; the model learns from historical patterns in the engineered features.
- **Prediction** — call ``predict()`` with fresh input data to obtain a :class:`~openstef_core.datasets.ForecastDataset` containing probabilistic quantile forecasts.
- **Evaluation** — call ``score()`` to compute metrics against held-out actuals, or visualise the forecast directly.

OpenSTEF is a *library*: each of these stages is a composable Python object you instantiate and wire together yourself. The sections below show exactly how.


Step 1 — Prepare Your Data
--------------------------

OpenSTEF's core data structure is :class:`~openstef_core.datasets.TimeSeriesDataset`, a thin wrapper around a ``pandas.DataFrame`` with a :class:`~pandas.DatetimeIndex` and a fixed ``sample_interval``. Every column except the target (``load`` by default) is treated as a feature.

For this tutorial we use the built-in synthetic dataset generator so you can run the code without external data:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.testing import create_synthetic_forecasting_dataset

    # Nine months of hourly data — enough history for lag features
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=270),
        sample_interval=timedelta(hours=1),
        include_atmosphere=True,   # adds temperature, pressure, humidity
        random_seed=42,
    )

    print(dataset.data.columns.tolist())
    # ['load', 'wind_speed', 'temperature', ...]
    print(f"Dataset spans {dataset.data.index.min()} → {dataset.data.index.max()}")

When using your own data, construct the dataset from a DataFrame:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    df = pd.read_csv("my_load_data.csv", index_col="timestamp", parse_dates=True)
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

.. note::

   The index must be a timezone-aware :class:`~pandas.DatetimeIndex` with a consistent frequency. Gaps in the index are allowed but will produce ``NaN`` values in lag features — the preprocessing pipeline handles this gracefully.

Split the dataset into a training portion and a held-out test portion before touching the model:

.. code-block:: python

    from datetime import timezone

    split_point = dataset.data.index[-1] - timedelta(days=14)

    train_data = TimeSeriesDataset(
        data=dataset.data.loc[:split_point],
        sample_interval=timedelta(hours=1),
    )
    test_data = TimeSeriesDataset(
        data=dataset.data.loc[split_point:],
        sample_interval=timedelta(hours=1),
    )

Keeping the test set completely separate from training is essential for honest evaluation. The last two weeks make a reasonable test window for a 24-hour ahead forecast.


Step 2 — Configure the Model Pipeline
--------------------------------------

OpenSTEF separates *what* you want to forecast from *how* the model is built. The :class:`~openstef_models.presets.forecasting_workflow.ForecastingWorkflowConfig` dataclass captures both concerns in one place, and the :func:`~openstef_models.presets.forecasting_workflow.create_forecasting_workflow` factory assembles the full pipeline — preprocessing, forecaster, and postprocessing — from that configuration.

.. code-block:: python

    from datetime import timedelta
    from pydantic_extra_types.country import CountryAlpha2
    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )
    from openstef_core.types import Q

    config = ForecastingWorkflowConfig(
        model_id="my_first_forecast",
        model="xgboost",                        # xgboost | lgbm | gblinear | median
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],    # predict 10th, median, 90th percentile
        sample_interval=timedelta(hours=1),
        location=LocationConfig(
            name="Amsterdam",
            country_code=CountryAlpha2("NL"),
        ),
    )

    workflow = create_forecasting_workflow(config)

A few configuration choices deserve explanation:

- **model** — ``"xgboost"`` is a solid default for most energy time series. It handles non-linear patterns and missing values well. Use ``"lgbm"`` for faster training on large datasets.
- **quantiles** — specifying multiple quantiles gives you a *probabilistic* forecast (a prediction interval), not just a point estimate. The ``Q(0.5)`` quantile is the median.
- **location** — the country code is used to inject public holiday indicators as features. Getting this right meaningfully improves forecast accuracy around holiday periods.

.. note::

   ``create_forecasting_workflow`` returns a :class:`~openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow`, which wraps a :class:`~openstef_models.models.forecasting_model.ForecastingModel` together with lifecycle callbacks. You can also construct a ``ForecastingModel`` directly for lower-level control — see :doc:`advanced_customization`.


Step 3 — Train the Model
------------------------

Training is a single ``fit()`` call. Internally, the preprocessing pipeline fits its transforms (lag windows, scalers, holiday encoders) on the training data first, then the underlying forecaster trains on the engineered feature matrix.

.. code-block:: python

    fit_result = workflow.fit(data=train_data)

    print(f"Training complete. Fitted: {workflow.model.is_fitted}")

Optionally pass a validation set to enable early stopping and in-training metric logging:

.. code-block:: python

    # Use the last 10% of training data as a validation split
    val_split = int(len(train_data.data) * 0.9)
    train_part = TimeSeriesDataset(
        data=train_data.data.iloc[:val_split],
        sample_interval=timedelta(hours=1),
    )
    val_part = TimeSeriesDataset(
        data=train_data.data.iloc[val_split:],
        sample_interval=timedelta(hours=1),
    )

    fit_result = workflow.fit(data=train_part, data_val=val_part)

.. note::

   The ``cutoff_history`` parameter on ``ForecastingModel`` controls how many rows at the start of the training data are excluded from the loss calculation. This matters when using lag features: a 7-day lag creates ``NaN`` values for the first 168 hourly rows, and including those rows in training would bias the model. The preset factory sets a sensible default, but you can override it when constructing the model directly.


Step 4 — Generate a Forecast
-----------------------------

Once the model is fitted, call ``predict()`` with any :class:`~openstef_core.datasets.TimeSeriesDataset` that covers the forecast horizon. The dataset must include the same feature columns used during training (weather forecasts, for example) for the period you want to predict.

.. code-block:: python

    forecast: ForecastDataset = workflow.predict(data=test_data)

    # The median forecast series
    print(forecast.median_series.head())

    # Access a specific quantile
    print(forecast.data[["quantile_P10", "quantile_P50", "quantile_P90"]].head())

The returned :class:`~openstef_core.datasets.ForecastDataset` contains one column per requested quantile. The ``median_series`` property is a convenience accessor for the ``Q(0.5)`` column.

You can also pass an explicit ``forecast_start`` to anchor the prediction window:

.. code-block:: python

    from datetime import datetime, timezone

    forecast = workflow.predict(
        data=test_data,
        forecast_start=datetime(2025, 9, 1, tzinfo=timezone.utc),
    )


Step 5 — Evaluate the Forecast
--------------------------------

The ``score()`` method computes evaluation metrics by running ``predict()`` internally and comparing the output against the target column present in the dataset. It returns a :class:`~openstef_core.datasets.SubsetMetric` containing the configured metrics at the model's maximum horizon.

.. code-block:: python

    metrics = workflow.model.score(data=test_data)

    print(metrics.metrics)
    # {'mae': 12.4, 'rmse': 18.7, 'skill_score': 0.83, ...}

For a visual check, OpenSTEF ships a dedicated plotter in ``openstef_beam``:

.. code-block:: python

    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

    plotter = ForecastTimeSeriesPlotter()
    fig = plotter.plot(forecast=forecast)
    fig.show()

.. note::

   ``ForecastTimeSeriesPlotter`` understands the probabilistic structure of a ``ForecastDataset`` and automatically renders the median line with shaded prediction intervals. Prefer this over building a custom matplotlib plot from scratch.

Interpreting the metrics:

- **MAE** (Mean Absolute Error) — average absolute deviation in the same units as your load column (e.g. MW). This is the most intuitive single-number summary.
- **RMSE** (Root Mean Squared Error) — penalises large errors more heavily than MAE. A significantly higher RMSE than MAE suggests occasional large spikes worth investigating.
- **Skill score** — compares your model against a naïve baseline (typically persistence or climatology). A value above 0 means the model beats the baseline; 1.0 is a perfect forecast.

If the skill score is low, common causes are insufficient training history (try extending ``length`` in the synthetic example), missing exogenous features, or a model type that is a poor fit for the data distribution. See :doc:`advanced_customization` for guidance on tuning the pipeline.


Putting It All Together
-----------------------

The following self-contained script runs every step above end-to-end:

.. code-block:: python

    import logging
    from datetime import datetime, timedelta, timezone

    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import Q
    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )
    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

    logging.basicConfig(level=logging.INFO)

    # --- 1. Data preparation ---
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=270),
        sample_interval=timedelta(hours=1),
        include_atmosphere=True,
        random_seed=42,
    )

    split_point = dataset.data.index[-1] - timedelta(days=14)
    train_data = TimeSeriesDataset(
        data=dataset.data.loc[:split_point],
        sample_interval=timedelta(hours=1),
    )
    test_data = TimeSeriesDataset(
        data=dataset.data.loc[split_point:],
        sample_interval=timedelta(hours=1),
    )

    # --- 2. Model configuration ---
    config = ForecastingWorkflowConfig(
        model_id="my_first_forecast",
        model="xgboost",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        sample_interval=timedelta(hours=1),
        location=LocationConfig(
            name="Amsterdam",
            country_code=CountryAlpha2("NL"),
        ),
    )
    workflow = create_forecasting_workflow(config)

    # --- 3. Training ---
    workflow.fit(data=train_data)

    # --- 4. Prediction ---
    forecast = workflow.predict(data=test_data)
    print(forecast.median_series.describe())

    # --- 5. Evaluation ---
    metrics = workflow.model.score(data=test_data)
    print(metrics.metrics)

    plotter = ForecastTimeSeriesPlotter()
    fig = plotter.plot(forecast=forecast)
    fig.show()


Next Steps
----------

Now that you have a working forecast, you can explore:

- :doc:`backtesting` — rigorously compare this model against alternatives using historical walk-forward evaluation.
- :doc:`advanced_customization` — replace the preset pipeline with hand-crafted preprocessing transforms, custom forecasters, or ensemble configurations.