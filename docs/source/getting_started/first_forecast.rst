Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with OpenSTEF from scratch. By the end you will have loaded time series data into OpenSTEF's data structures, configured a preprocessing pipeline with feature engineering, trained a forecasting model, generated predictions, and inspected the results. Each step explains not just *how* but *why*, so you understand the design choices you are making.

If you just want the shortest possible working script, see :doc:`quickstart` instead. For comparing multiple models against each other, see :doc:`backtesting`. For customising transforms and forecasters beyond what is shown here, see :doc:`advanced_customization`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF is a Python *library*. It does not run as a service or manage a database — it provides composable building blocks that you wire together in your own code. The central abstraction is the ``ForecastingModel``, which bundles a preprocessing pipeline, a forecaster, and an optional postprocessing pipeline into a single object that exposes ``fit()`` and ``predict()``. Wrapping that in a ``CustomForecastingWorkflow`` adds lifecycle management such as model persistence and callbacks.

The five stages you will follow are:

1. **Data preparation** — structure your time series as a ``VersionedTimeSeriesDataset``
2. **Feature engineering** — configure a ``TransformPipeline`` that enriches the raw data
3. **Model configuration** — assemble a ``ForecastingModel`` with the pipeline and a forecaster
4. **Training** — call ``workflow.fit()`` to train and evaluate
5. **Prediction and evaluation** — call ``workflow.predict()`` and inspect the output

Step 1 — Preparing Your Data
-----------------------------

OpenSTEF expects time series data as a ``VersionedTimeSeriesDataset``. The "versioned" part matters for production use: it tracks when each data point became *available*, which prevents look-ahead bias during backtesting. For a first forecast you can ignore that detail and use the convenience constructor ``from_dataframe()``.

Your DataFrame must have a ``pd.DatetimeIndex`` and at least one column for the target variable (by default ``"load"``). Additional columns become exogenous features — weather measurements, calendar flags, and so on.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from openstef_models.data.versioned_time_series_dataset import VersionedTimeSeriesDataset

    # Build 90 days of synthetic 15-minute load data with a temperature covariate.
    rng = np.random.default_rng(42)
    n_samples = 90 * 24 * 4  # 15-minute intervals

    index = pd.date_range("2024-01-01", periods=n_samples, freq="15min")
    load = (
        50.0
        + 10.0 * np.sin(2 * np.pi * index.hour / 24)   # daily cycle
        + 5.0 * np.sin(2 * np.pi * index.dayofweek / 7) # weekly cycle
        + rng.standard_normal(n_samples)                 # noise
    )
    temperature = 10.0 + 5.0 * np.sin(2 * np.pi * index.dayofyear / 365) + rng.standard_normal(n_samples)

    raw_df = pd.DataFrame({"load": load, "temperature": temperature}, index=index)

    dataset = VersionedTimeSeriesDataset.from_dataframe(
        data=raw_df,
        sample_interval=timedelta(minutes=15),
    )

    print(f"Dataset covers {dataset.data_parts[0].data.index.min()} "
          f"to {dataset.data_parts[0].data.index.max()}")
    print(f"Features: {dataset.feature_names}")

The ``sample_interval`` argument tells OpenSTEF the expected cadence of your data. It is used downstream when computing lag offsets and validating completeness.

.. note::

   Real-world data often has gaps, duplicate timestamps, or misaligned covariates. OpenSTEF provides ``CompletenessChecker`` and other validation transforms you can add to your pipeline to catch these issues early. See :doc:`advanced_customization` for details.

Step 2 — Configuring Feature Engineering
-----------------------------------------

Raw load and temperature values alone are rarely sufficient for a good forecast. OpenSTEF's ``TransformPipeline`` lets you chain transforms that add derived features before the model ever sees the data. Three transforms cover the most common needs:

- ``HolidayFeatureAdder`` — adds binary flags for public holidays in a given country, which strongly influence load patterns.
- ``LagTransformer`` (``LagAdder``) — adds lagged copies of the target column at specified offsets, giving the model access to recent history.
- ``StandardScalerTransform`` — normalises features to zero mean and unit variance, which benefits many gradient-boosted and linear models.

.. code-block:: python

    from openstef_core.mixins import TransformPipeline
    from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
    from openstef_models.transforms.time_domain.lags_adder import LagAdder
    from openstef_models.transforms.scaling.standard_scaler import StandardScalerTransform

    # Lag offsets expressed as timedeltas.
    # Here we look back 1 day (96 × 15 min) and 1 week (672 × 15 min).
    lag_1d  = timedelta(days=1)
    lag_1w  = timedelta(days=7)

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country="NL"),
            LagAdder(lags=[lag_1d, lag_1w], target_column="load"),
            StandardScalerTransform(),
        ]
    )

The order of transforms matters. Holiday flags are added first so that the scaler can normalise them along with everything else. The lag transforms introduce ``NaN`` values at the start of the series — the first ``lag_1w`` worth of rows will be incomplete. You must account for this when configuring the model (see Step 3).

Step 3 — Configuring the Model
--------------------------------

``ForecastingModel`` is the core pipeline object. It holds the preprocessing pipeline, the forecaster itself, and an optional postprocessing pipeline. It also controls how data is split into training, validation, and test sets via ``DataSplitter``, and how much historical data to discard due to incomplete lag features via ``cutoff_history``.

.. code-block:: python

    from openstef_models.models.forecasting.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.constant_median_forecaster import ConstantMedianForecaster
    from openstef_core.types import LeadTime, Q

    # Forecast horizon: predict 24 hours ahead.
    horizons = [LeadTime.from_string("PT24H")]
    quantiles = [Q(0.1), Q(0.5), Q(0.9)]

    forecaster = ConstantMedianForecaster(
        horizons=horizons,
        quantiles=quantiles,
    )

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=forecaster,
        target_column="load",
        # Discard the first 7 days where lag features are NaN.
        cutoff_history=timedelta(days=7),
    )

``ConstantMedianForecaster`` is a simple but instructive baseline: it predicts the median of the training target for each horizon. It is a good sanity check before moving to gradient-boosted models. To switch to XGBoost, replace it with the appropriate forecaster class — the rest of the pipeline stays identical. See :doc:`advanced_customization` for guidance on choosing and tuning forecasters.

.. note::

   ``cutoff_history`` must be set manually. OpenSTEF cannot automatically infer the lag window from your pipeline because transforms are composable and may be arbitrarily nested. A good rule of thumb: set ``cutoff_history`` to the longest lag offset in your ``LagAdder``.

Step 4 — Training the Model
-----------------------------

``CustomForecastingWorkflow`` wraps ``ForecastingModel`` and adds model persistence, callbacks, and a clean ``fit`` / ``predict`` interface. For local development, ``LocalModelStorage`` saves and loads models from disk.

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.storage.local_model_storage import LocalModelStorage

    storage = LocalModelStorage(base_path=Path("./models"))

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=storage,
    )

    # Split the dataset: the last 24 hours are held out as a test set.
    fit_result = workflow.fit(dataset)

    print("Training complete.")
    print(f"Evaluation metrics: {fit_result}")

Calling ``workflow.fit()`` triggers the full training sequence: the preprocessing pipeline is fitted on the training split, lag features and holiday flags are computed, the forecaster is trained, and the model is serialised to ``./models/my_first_forecast``. The returned ``fit_result`` contains evaluation metrics computed on the validation split.

.. note::

   ``DataSplitter`` defaults to a chronological split — the most recent data becomes the validation set. This is the correct choice for time series: random splits would leak future information into training. See :doc:`backtesting` for how to evaluate across multiple time windows.

Step 5 — Generating and Evaluating Forecasts
----------------------------------------------

Once the workflow is fitted, call ``predict()`` with the same dataset (or a new one containing the features needed to compute lags). The result is a ``ForecastDataset`` containing point forecasts and, if quantiles were configured, prediction intervals.

.. code-block:: python

    forecast_dataset = workflow.predict(dataset)

    # ForecastDataset exposes its contents as a DataFrame.
    forecasts_df = forecast_dataset.data
    print(forecasts_df.head())
    print(f"\nColumns: {list(forecasts_df.columns)}")

The output DataFrame is indexed by ``(timestamp, horizon)`` and contains one column per quantile plus a ``"forecast"`` column for the point prediction. The ``Q(0.1)`` and ``Q(0.9)`` columns give you an 80 % prediction interval.

To evaluate forecast quality against known actuals, align the forecast timestamps with the ground-truth load values and compute your preferred metric:

.. code-block:: python

    import numpy as np

    # Align forecasts with actuals on the test portion of the dataset.
    actuals = raw_df["load"]
    point_forecasts = forecasts_df["forecast"]

    # Inner join on timestamp to handle any index misalignment.
    comparison = point_forecasts.to_frame().join(actuals.rename("actual"), how="inner")
    comparison = comparison.dropna()

    mae  = np.mean(np.abs(comparison["forecast"] - comparison["actual"]))
    rmse = np.sqrt(np.mean((comparison["forecast"] - comparison["actual"]) ** 2))

    print(f"MAE:  {mae:.3f}")
    print(f"RMSE: {rmse:.3f}")

A ``ConstantMedianForecaster`` will produce a flat forecast, so the numbers here serve as a baseline to beat. Once you replace it with a gradient-boosted model and richer features, you should see both metrics drop substantially.

Putting It All Together
------------------------

The complete script for reference:

.. code-block:: python

    import logging
    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from pathlib import Path

    from openstef_models.data.versioned_time_series_dataset import VersionedTimeSeriesDataset
    from openstef_core.mixins import TransformPipeline
    from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
    from openstef_models.transforms.time_domain.lags_adder import LagAdder
    from openstef_models.transforms.scaling.standard_scaler import StandardScalerTransform
    from openstef_models.models.forecasting.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.constant_median_forecaster import ConstantMedianForecaster
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.storage.local_model_storage import LocalModelStorage
    from openstef_core.types import LeadTime, Q

    logging.basicConfig(level=logging.INFO)

    # --- 1. Data ---
    rng = np.random.default_rng(42)
    n_samples = 90 * 24 * 4
    index = pd.date_range("2024-01-01", periods=n_samples, freq="15min")
    load = 50.0 + 10.0 * np.sin(2 * np.pi * index.hour / 24) + rng.standard_normal(n_samples)
    temperature = 10.0 + rng.standard_normal(n_samples)
    raw_df = pd.DataFrame({"load": load, "temperature": temperature}, index=index)
    dataset = VersionedTimeSeriesDataset.from_dataframe(raw_df, timedelta(minutes=15))

    # --- 2. Preprocessing pipeline ---
    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country="NL"),
            LagAdder(lags=[timedelta(days=1), timedelta(days=7)], target_column="load"),
            StandardScalerTransform(),
        ]
    )

    # --- 3. Model ---
    horizons = [LeadTime.from_string("PT24H")]
    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(horizons=horizons, quantiles=[Q(0.1), Q(0.5), Q(0.9)]),
        target_column="load",
        cutoff_history=timedelta(days=7),
    )

    # --- 4. Train ---
    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=LocalModelStorage(base_path=Path("./models")),
    )
    fit_result = workflow.fit(dataset)
    print(f"Fit result: {fit_result}")

    # --- 5. Predict and evaluate ---
    forecast_dataset = workflow.predict(dataset)
    forecasts_df = forecast_dataset.data
    comparison = forecasts_df[["forecast"]].join(raw_df["load"].rename("actual"), how="inner").dropna()
    mae = np.mean(np.abs(comparison["forecast"] - comparison["actual"]))
    print(f"MAE: {mae:.3f}")

Common Issues
--------------

**NaN values in training data**
   If ``fit()`` raises an error about NaN values, your ``cutoff_history`` is too short. Increase it to cover the longest lag in your ``LagAdder``.

**Index not recognised as DatetimeIndex**
   ``VersionedTimeSeriesDataset.from_dataframe()`` requires the DataFrame index to be a ``pd.DatetimeIndex``. Call ``df.index = pd.to_datetime(df.index)`` if needed.

**Empty forecast output**
   ``predict()`` requires the input dataset to contain enough history to compute lag features. Ensure the dataset spans at least ``cutoff_history`` before the first desired forecast timestamp.

**Model not found on load**
   ``LocalModelStorage`` looks for a serialised model at ``base_path / model_id``. If you change ``model_id`` between ``fit()`` and a subsequent ``predict()`` call, the workflow will not find the saved model. Keep the ID consistent or call ``fit()`` again.

Next Steps
----------

You now have a working forecast pipeline. From here:

- **Improve accuracy** — swap ``ConstantMedianForecaster`` for an XGBoost or gradient-boosted linear model and tune the feature pipeline. See :doc:`advanced_customization`.
- **Validate rigorously** — use walk-forward backtesting to measure performance across many time windows rather than a single train/test split. See :doc:`backtesting`.
- **Go to production** — replace ``LocalModelStorage`` with ``MLFlowStorage`` to version models and track experiments at scale.