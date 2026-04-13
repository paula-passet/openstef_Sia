Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with
OpenSTEF from scratch. By the end, you will have prepared time series data, configured
a preprocessing pipeline with feature engineering, trained a model, generated
predictions, and evaluated the results — with a clear understanding of *why* each step
exists.

If you just want the shortest possible working example, see :doc:`quickstart` first.
This page goes deeper, explaining the reasoning behind each decision so you can adapt
the pattern to your own data.

.. note:: [DIAGRAM: Step-by-step flowchart showing the forecasting workflow: (1) Data Preparation → validates index, sample interval, feature columns; (2) Feature Engineering → holiday flags, lag transforms, scaling; decision point: "Enough history for lags?" → if no, extend lookback window; (3) Model Training → fit on train split, validate on held-out split; decision point: "Metrics acceptable?" → if no, adjust pipeline or forecaster; (4) Prediction → transform new data, generate point forecast + quantiles; (5) Evaluation → compute MAE/RMSE/MAPE, inspect residuals by horizon]


Overview
--------

OpenSTEF is structured around a pipeline abstraction. Rather than calling a sequence
of standalone functions, you compose a :class:`ForecastingModel` from three
building blocks:

- **Preprocessing** — a :class:`TransformPipeline` of feature-engineering transforms
  applied before the forecaster sees any data.
- **Forecaster** — the model that maps features to target values.
- **Postprocessing** — a second :class:`TransformPipeline` applied to raw predictions
  (e.g. adding confidence intervals).

This separation keeps each concern isolated and makes it straightforward to swap one
component without touching the others. The sections below build up each piece in turn.


Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects time series data wrapped in a :class:`VersionedTimeSeriesDataset`.
The "versioned" part is important: it tracks *when* each observation became available,
which lets the library simulate realistic data availability during training and avoid
look-ahead bias when creating lag features.

The simplest way to create one is from a :class:`pandas.DataFrame` with a
:class:`~pandas.DatetimeIndex`:

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    from openstef_models.data.versioned_time_series_dataset import VersionedTimeSeriesDataset

    # Build 90 days of synthetic 15-minute load data with a temperature covariate
    rng = np.random.default_rng(42)
    n_samples = 90 * 24 * 4  # 90 days at 15-minute resolution

    timestamps = pd.date_range(
        start=datetime(2024, 1, 1),
        periods=n_samples,
        freq="15min",
        name="timestamp",
    )

    # Simulate a daily load profile with noise and a temperature signal
    hour_of_day = timestamps.hour + timestamps.minute / 60
    daily_pattern = 200 + 80 * np.sin(np.pi * (hour_of_day - 6) / 12)
    load = daily_pattern + rng.normal(scale=15, size=n_samples)
    temperature = 10 + 8 * np.sin(2 * np.pi * timestamps.dayofyear / 365)

    raw_data = pd.DataFrame(
        {"load": load, "temperature": temperature},
        index=timestamps,
    )

    dataset = VersionedTimeSeriesDataset.from_dataframe(
        raw_data,
        sample_interval=timedelta(minutes=15),
    )

    print(f"Dataset covers {dataset.data_parts[0].data.index.min()} "
          f"to {dataset.data_parts[0].data.index.max()}")

A few things to keep in mind when preparing real data:

- The index must be a :class:`~pandas.DatetimeIndex` with a consistent frequency.
  Gaps or duplicate timestamps will cause validation errors downstream.
- The target column (``load`` here) must be present in the DataFrame.
  Covariate columns such as ``temperature`` are carried through automatically.
- You need enough history to satisfy your lag configuration. A lag of 14 days requires
  at least 14 days of data *before* the first training sample you want to use. The
  ``cutoff_history`` parameter on :class:`ForecastingModel` trims the leading rows
  that contain NaN-filled lag features.


Step 2 — Configure Feature Engineering
---------------------------------------

Raw timestamps and load values are rarely sufficient inputs for a good forecast.
OpenSTEF provides a library of transforms you compose into a :class:`TransformPipeline`.
The pipeline is fitted once on training data and then applied identically to any new
data at prediction time, preventing data leakage.

A typical preprocessing pipeline for energy forecasting includes:

- **Holiday features** — binary flags for public holidays, which strongly influence
  load patterns.
- **Lag transforms** — historical load values at fixed offsets (e.g. 24 h ago, 48 h
  ago, one week ago) give the model direct access to recent patterns.
- **Scaling** — standardising features to zero mean and unit variance helps many
  gradient-boosted and neural forecasters converge faster.

.. code-block:: python

    from openstef_models.transforms.pipeline import TransformPipeline
    from openstef_models.transforms.time_domain.holiday_transformer import HolidayTransformer
    from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder
    from openstef_models.transforms.scaling.standard_scaler import StandardScalerTransformer

    preprocessing = TransformPipeline(
        transforms=[
            HolidayTransformer(country="NL"),
            VersionedLagsAdder(
                lags=[
                    timedelta(hours=24),
                    timedelta(hours=48),
                    timedelta(days=7),
                ]
            ),
            StandardScalerTransformer(target_column="load"),
        ]
    )

.. note::

   ``VersionedLagsAdder`` is aware of data availability. When creating a lag of 24 h,
   it only uses values that would have been *available* at the time of each prediction,
   not values that arrived later. This is what makes OpenSTEF safe for realistic
   backtesting.

The ``cutoff_history`` on the model (configured in the next step) should match the
longest lag you add. With a 7-day lag, set ``cutoff_history=timedelta(days=7)`` so
that the first training row the model sees already has all lag features populated.


Step 3 — Assemble and Train the Model
--------------------------------------

With data and preprocessing in hand, you can assemble a :class:`ForecastingModel` and
call ``fit()``. The model orchestrates the full training workflow: it fits the
preprocessing pipeline, transforms the data, splits it into training and validation
sets, trains the forecaster, and records evaluation metrics.

.. code-block:: python

    from openstef_models.models.forecasting.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.constant_median_forecaster import (
        ConstantMedianForecaster,
    )
    from openstef_models.transforms.pipeline import TransformPipeline

    # A minimal postprocessing pipeline (no-op for this tutorial)
    postprocessing = TransformPipeline(transforms=[])

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(),
        postprocessing=postprocessing,
        target_column="load",
        cutoff_history=timedelta(days=7),
    )

    # Split: use the first 80 days for training, hold out the last 10 for evaluation
    split_time = timestamps[int(n_samples * 0.89)]
    train_dataset, eval_dataset = dataset.split_at(split_time)

    fit_result = model.fit(train_dataset)
    print("Training complete. Metrics:", fit_result.metrics)

:class:`ConstantMedianForecaster` is a simple baseline that predicts the median of
historical values. It is a good starting point because it is fast, interpretable, and
provides a meaningful floor for comparison. Once you have the pipeline working
end-to-end, replace it with a gradient-boosted or neural forecaster — see
:doc:`advanced_customization` for guidance on swapping forecasters.

.. note::

   ``fit()`` must always be called before ``predict()``. The :class:`ForecastingModel`
   enforces this invariant and will raise a clear error if you attempt to predict with
   an unfitted model.


Step 4 — Generate a Forecast
-----------------------------

Once the model is trained, call ``predict()`` with new (unseen) data. In production
this would be a DataFrame containing the latest observations and any available
covariate forecasts (e.g. weather predictions). In this tutorial, we use the held-out
evaluation slice:

.. code-block:: python

    forecast_result = model.predict(eval_dataset)

    # forecast_result.forecast is a pd.DataFrame with columns:
    #   - 'forecast'  : point prediction
    #   - 'horizon'   : lead time in hours
    #   - plus quantile columns if postprocessing adds them
    print(forecast_result.forecast.head())

The ``predict()`` call runs the same preprocessing transforms that were fitted during
training, so the evaluation data is transformed consistently. You never need to
manually re-apply scaling or lag computation — the pipeline handles it.

.. note::

   The ``forecast_start`` parameter on ``predict()`` lets you anchor the forecast to a
   specific point in time. This is useful when your evaluation dataset spans multiple
   days and you want predictions for a single operational window.


Step 5 — Evaluate the Results
------------------------------

OpenSTEF's ``openstef_beam.metrics`` module provides energy-domain metrics that go
beyond generic regression scores. For a first forecast, the most useful are:

- **MAE** (mean absolute error) — average absolute deviation in the same unit as load
  (e.g. MW). Easy to communicate to stakeholders.
- **MAPE** (mean absolute percentage error) — scale-independent, but unreliable near
  zero load.
- **RMSE** (root mean squared error) — penalises large errors more heavily, relevant
  when peak errors are costly.

.. code-block:: python

    import numpy as np
    from openstef_beam.metrics import mae, rmse, mape

    forecast_df = forecast_result.forecast

    # Align predictions with ground truth from the evaluation dataset
    eval_data = eval_dataset.data_parts[0].data
    aligned = forecast_df.join(eval_data[["load"]], how="inner")

    y_true = aligned["load"].to_numpy()
    y_pred = aligned["forecast"].to_numpy()

    print(f"MAE  : {mae(y_true, y_pred):.2f} MW")
    print(f"RMSE : {np.sqrt(np.mean((y_true - y_pred) ** 2)):.2f} MW")
    print(f"MAPE : {mape(y_true, y_pred):.2%}")

A high MAE or MAPE at this stage is expected — the :class:`ConstantMedianForecaster`
is intentionally simple. The purpose of this step is to confirm that the pipeline
produces sensible output and that the evaluation harness is working correctly before
you invest time tuning a more complex model.

For a systematic comparison of multiple models and hyperparameter settings, see
:doc:`backtesting`.


Putting It All Together
------------------------

The five steps above can be combined into a single script. The pattern below is the
canonical OpenSTEF workflow for a self-contained training and evaluation run:

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    from pathlib import Path

    from openstef_models.data.versioned_time_series_dataset import VersionedTimeSeriesDataset
    from openstef_models.models.forecasting.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.constant_median_forecaster import (
        ConstantMedianForecaster,
    )
    from openstef_models.transforms.pipeline import TransformPipeline
    from openstef_models.transforms.time_domain.holiday_transformer import HolidayTransformer
    from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder
    from openstef_models.transforms.scaling.standard_scaler import StandardScalerTransformer
    from openstef_beam.metrics import mae, mape

    # --- 1. Data ---
    rng = np.random.default_rng(42)
    n_samples = 90 * 24 * 4
    timestamps = pd.date_range(
        start=datetime(2024, 1, 1), periods=n_samples, freq="15min", name="timestamp"
    )
    hour_of_day = timestamps.hour + timestamps.minute / 60
    load = 200 + 80 * np.sin(np.pi * (hour_of_day - 6) / 12) + rng.normal(scale=15, size=n_samples)
    temperature = 10 + 8 * np.sin(2 * np.pi * timestamps.dayofyear / 365)
    raw_data = pd.DataFrame({"load": load, "temperature": temperature}, index=timestamps)
    dataset = VersionedTimeSeriesDataset.from_dataframe(raw_data, timedelta(minutes=15))

    # --- 2. Pipeline ---
    preprocessing = TransformPipeline(
        transforms=[
            HolidayTransformer(country="NL"),
            VersionedLagsAdder(lags=[timedelta(hours=24), timedelta(hours=48), timedelta(days=7)]),
            StandardScalerTransformer(target_column="load"),
        ]
    )
    postprocessing = TransformPipeline(transforms=[])

    # --- 3. Model ---
    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(),
        postprocessing=postprocessing,
        target_column="load",
        cutoff_history=timedelta(days=7),
    )

    # --- 4. Train / Predict ---
    split_time = timestamps[int(n_samples * 0.89)]
    train_dataset, eval_dataset = dataset.split_at(split_time)
    model.fit(train_dataset)
    forecast_result = model.predict(eval_dataset)

    # --- 5. Evaluate ---
    eval_data = eval_dataset.data_parts[0].data
    aligned = forecast_result.forecast.join(eval_data[["load"]], how="inner")
    y_true = aligned["load"].to_numpy()
    y_pred = aligned["forecast"].to_numpy()
    print(f"MAE : {mae(y_true, y_pred):.2f}  |  MAPE : {mape(y_true, y_pred):.2%}")


Common Pitfalls
---------------

**Insufficient history for lag features**
   If your dataset is shorter than the longest lag, the lag columns will be entirely
   NaN and the model will train on empty features. Always ensure your dataset spans at
   least ``max_lag + cutoff_history`` before the first prediction timestamp.

**Mismatched sample intervals**
   ``VersionedTimeSeriesDataset.from_dataframe`` requires a ``sample_interval`` that
   matches the actual frequency of your data. A mismatch causes incorrect lag offsets.
   Verify with ``pd.infer_freq(raw_data.index)`` before constructing the dataset.

**Fitting the pipeline on evaluation data**
   Never call ``model.fit()`` on data that overlaps with your evaluation window.
   The :class:`ForecastingModel` does not enforce this automatically — it is your
   responsibility to split before fitting.

**Forgetting ``cutoff_history``**
   Omitting ``cutoff_history`` when using long lags means the model trains on rows
   where lag features are NaN-filled, which degrades accuracy and can cause silent
   errors in some forecasters.


Next Steps
----------

Now that you have a working pipeline, consider:

- **Swap the forecaster** — replace :class:`ConstantMedianForecaster` with a
  gradient-boosted or neural model. See :doc:`advanced_customization` for how to
  configure and register custom forecasters.
- **Benchmark systematically** — use the backtesting utilities to compare models
  across multiple time windows rather than a single train/test split. See
  :doc:`backtesting`.
- **Persist the model** — wrap your :class:`ForecastingModel` in a
  :class:`CustomForecastingWorkflow` with a :class:`LocalModelStorage` backend to
  save and reload trained models between runs.