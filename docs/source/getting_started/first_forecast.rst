Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with OpenSTEF from scratch. You will load time series data, configure a preprocessing pipeline, train a model, generate predictions, and evaluate the results — with an explanation of *why* each step matters, not just *how* to do it.

If you want the fastest possible path to a running forecast without the explanations, see :doc:`quickstart`. For comparing multiple models against each other, see :doc:`backtesting`.

.. mermaid:: diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF is a library, meaning you compose its components to build forecasting pipelines that fit your data and requirements. The central class you will work with is ``ForecastingModel``, which orchestrates three stages:

- **Preprocessing** — a sequence of transforms that engineer features from raw time series data.
- **Forecaster** — the underlying machine learning model (e.g. LightGBM, XGBoost).
- **Postprocessing** — optional transforms applied to raw predictions (e.g. quantile sorting, confidence interval widening).

Understanding this structure makes it easy to swap components later. For now, you will use a straightforward LightGBM-based setup.

Step 1: Prepare Your Data
--------------------------

OpenSTEF works with ``TimeSeriesDataset``, a thin wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex``. The minimum requirement is a column containing your target variable (by default named ``"load"``).

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Build a minimal DataFrame: DatetimeIndex + target column + at least one feature
    raw_df = pd.DataFrame(
        {
            "load": energy_measurements,   # your target: e.g. MW consumed
            "temperature": temperature_values,
        },
        index=pd.date_range(start="2024-01-01", periods=len(energy_measurements), freq="1h"),
    )
    raw_df.index.name = "timestamp"

    dataset = TimeSeriesDataset(
        data=raw_df,
        sample_interval=timedelta(hours=1),
        target_column="load",
    )

A few things to keep in mind at this stage:

- The index must be a ``DatetimeIndex`` with a consistent frequency. Gaps or duplicates will cause validation errors downstream.
- The ``sample_interval`` you declare must match the actual frequency of your data. OpenSTEF uses this to derive lag windows and horizon offsets.
- You do not need to add lag features or datetime encodings by hand — the preprocessing pipeline handles that in the next step.

.. note::

   ``TimeSeriesDataset`` validates that the target column is present on construction. If your column is named something other than ``"load"``, pass ``target_column="your_column_name"`` explicitly.

Step 2: Configure the Preprocessing Pipeline
---------------------------------------------

Feature engineering is where most of the forecasting signal comes from. OpenSTEF provides composable transform classes that you chain into a preprocessing list. A typical configuration for an hourly energy series looks like this:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.preprocessing import (
        LagsAdder,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        Imputer,
    )

    horizons = [timedelta(hours=h) for h in range(1, 25)]  # forecast up to 24 h ahead

    preprocessing = [
        LagsAdder(
            history_available=timedelta(days=14),
            horizons=horizons,
            target_column="load",
        ),
        DatetimeFeaturesAdder(onehot_encode=False),
        HolidayFeatureAdder(country_code="NL"),
        Imputer(imputation_strategy="mean"),
    ]

What each transform does:

- ``LagsAdder`` creates columns like ``load_lag_P1D`` (load 24 hours ago) and ``load_lag_P7D`` (load one week ago). These are the strongest predictors for energy consumption.
- ``DatetimeFeaturesAdder`` encodes hour-of-day, day-of-week, and month as numeric features so the model can learn daily and weekly seasonality.
- ``HolidayFeatureAdder`` marks public holidays for a given country, which strongly affect consumption patterns.
- ``Imputer`` fills any remaining ``NaN`` values so the model receives a complete feature matrix.

.. warning::

   The ``LagsAdder`` with a 14-day history creates ``NaN`` rows for the first 14 days of your dataset. You must account for this by setting ``cutoff_history=timedelta(days=14)`` on the ``ForecastingModel`` (shown in the next step). Without this, those incomplete rows will be included in training and degrade model quality.

Step 3: Train the Model
------------------------

With data and preprocessing in place, you instantiate a forecaster and wrap everything in a ``ForecastingModel``:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.models.forecasting import ForecastingModel
    from openstef_models.models.forecasters.lgbm_forecaster import LGBMForecaster
    from openstef_models.postprocessing import QuantileSorter

    forecaster = LGBMForecaster(
        quantiles=[0.1, 0.5, 0.9],   # predict median + 80% prediction interval
        horizons=horizons,
        random_state=42,
    )

    model = ForecastingModel(
        forecaster=forecaster,
        preprocessing=preprocessing,
        postprocessing=[QuantileSorter()],
        cutoff_history=timedelta(days=14),  # exclude lag-incomplete rows from training
    )

    fit_result = model.fit(dataset)

Calling ``model.fit()`` does two things in sequence: it fits the preprocessing pipeline (so transforms like ``Imputer`` learn column statistics from training data) and then fits the underlying LightGBM model on the engineered feature matrix. The ``ModelFitResult`` returned by ``fit()`` contains training diagnostics you can inspect.

You can optionally pass separate validation and test splits:

.. code-block:: python

    fit_result = model.fit(
        data=train_dataset,
        data_val=val_dataset,
        data_test=test_dataset,
    )

Providing a validation set enables early stopping in gradient-boosted models, which prevents overfitting without manual tuning of the number of estimators.

Step 4: Generate Forecasts
---------------------------

Once the model is fitted, call ``predict()`` with data that covers the period you want to forecast. The input must include the same feature columns as the training data (excluding the target, which is not available for future timestamps):

.. code-block:: python

    # new_data: a TimeSeriesDataset covering the forecast period
    # It must include weather features and have a DatetimeIndex
    forecast: ForecastDataset = model.predict(new_data)

    # Access the median forecast as a pandas Series
    median_forecast = forecast.data["load_quantile_0.5"]

    # Access the full forecast DataFrame (all quantiles + horizon column)
    print(forecast.data.head())

The ``predict()`` method applies the *fitted* preprocessing pipeline to the new data (using the statistics learned during training, not recomputed), runs inference through the LightGBM model, and applies postprocessing. The result is a ``ForecastDataset`` containing one column per quantile.

.. note::

   If you need to forecast from a specific point in time rather than the end of the input data, pass ``forecast_start`` explicitly::

       from datetime import datetime, timezone
       forecast = model.predict(new_data, forecast_start=datetime(2024-06-01, tzinfo=timezone.utc))

Step 5: Evaluate the Results
-----------------------------

If your evaluation data includes ground truth values (i.e. the ``"load"`` column is populated), you can score the model directly:

.. code-block:: python

    metrics: SubsetMetric = model.score(eval_dataset)
    print(metrics.metrics)
    # Example output:
    # {'MAE': 12.4, 'RMSE': 18.7, 'skill_score': 0.83}

``score()`` internally calls ``predict()`` and then compares the predictions against the target column using the configured evaluation metrics. The result is a ``SubsetMetric`` object keyed by metric name.

For a more thorough comparison across multiple horizons or model variants, see :doc:`backtesting`, which covers rolling-window evaluation and model comparison workflows.

Putting It All Together
------------------------

Here is the complete workflow in one block, ready to adapt to your own data:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.models.forecasting import ForecastingModel
    from openstef_models.models.forecasters.lgbm_forecaster import LGBMForecaster
    from openstef_models.preprocessing import (
        LagsAdder,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        Imputer,
    )
    from openstef_models.postprocessing import QuantileSorter

    # --- 1. Load data ---
    raw_df = pd.read_csv("energy_data.csv", index_col="timestamp", parse_dates=True)
    raw_df.index.name = "timestamp"

    dataset = TimeSeriesDataset(
        data=raw_df,
        sample_interval=timedelta(hours=1),
        target_column="load",
    )

    # --- 2. Split into train / evaluation ---
    split_date = "2024-10-01"
    train_data = TimeSeriesDataset(
        data=raw_df.loc[:split_date],
        sample_interval=timedelta(hours=1),
    )
    eval_data = TimeSeriesDataset(
        data=raw_df.loc[split_date:],
        sample_interval=timedelta(hours=1),
    )

    # --- 3. Configure preprocessing ---
    horizons = [timedelta(hours=h) for h in range(1, 25)]

    preprocessing = [
        LagsAdder(
            history_available=timedelta(days=14),
            horizons=horizons,
            target_column="load",
        ),
        DatetimeFeaturesAdder(onehot_encode=False),
        HolidayFeatureAdder(country_code="NL"),
        Imputer(imputation_strategy="mean"),
    ]

    # --- 4. Build and train model ---
    model = ForecastingModel(
        forecaster=LGBMForecaster(
            quantiles=[0.1, 0.5, 0.9],
            horizons=horizons,
            random_state=42,
        ),
        preprocessing=preprocessing,
        postprocessing=[QuantileSorter()],
        cutoff_history=timedelta(days=14),
    )

    model.fit(train_data)

    # --- 5. Forecast and evaluate ---
    forecast = model.predict(eval_data)
    metrics = model.score(eval_data)
    print(metrics.metrics)

Next Steps
----------

You now have a working forecast pipeline. From here, consider:

- **Customising the pipeline** — swap the forecaster, add custom transforms, or tune hyperparameters. See :doc:`advanced_customization`.
- **Rigorous evaluation** — use rolling-window backtesting to get unbiased performance estimates across many forecast origins. See :doc:`backtesting`.
- **Installation issues** — if any imports above failed, check your environment against :doc:`installation`.