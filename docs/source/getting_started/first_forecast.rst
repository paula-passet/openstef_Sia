Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with OpenSTEF from scratch. By the end you will have loaded time series data, configured a preprocessing pipeline, trained a model, generated predictions, and evaluated the result — with a clear understanding of *why* each step exists.

If you just want the shortest possible working script, see :doc:`quickstart` instead. This page goes deeper, explaining the reasoning behind each decision so you can adapt the pattern to your own data.

.. note:: [DIAGRAM: Step-by-step flowchart showing the five stages of an OpenSTEF forecast: (1) Data Preparation — load and validate a ``VersionedTimeSeriesDataset``; (2) Feature Engineering — apply ``FeaturePipeline`` with holiday features, lag transforms, and scaling; (3) Model Training — call ``ForecastingModel.fit()``, with a decision point for whether ``cutoff_history`` is needed to trim lag-induced NaNs; (4) Prediction — call ``ForecastingModel.predict()`` to produce a ``ForecastDataset`` with quantile outputs; (5) Evaluation — compute MAE / R² against held-out actuals, with a decision point to retrain if quality is insufficient.]

Overview
--------

OpenSTEF is a Python library that treats forecasting as a composable pipeline. Rather than hiding the machinery inside a single black-box function, it lets you wire together the pieces — data structures, feature transforms, a forecaster, and postprocessing — into a ``ForecastingModel`` that you own and can inspect. The five stages covered here map directly onto that architecture:

1. **Data preparation** — wrap your pandas DataFrame in a ``VersionedTimeSeriesDataset``
2. **Feature engineering** — configure a ``FeaturePipeline`` with the transforms your model needs
3. **Model training** — call ``ForecastingModel.fit()``
4. **Forecasting** — call ``ForecastingModel.predict()``
5. **Evaluation** — inspect the returned ``ForecastDataset`` and compute error metrics

Each stage is a distinct object you configure explicitly. This makes the pipeline transparent, testable, and easy to extend — topics covered in :doc:`advanced_customization`.


Step 1: Prepare Your Data
--------------------------

OpenSTEF expects time series data wrapped in a ``VersionedTimeSeriesDataset``. The "versioned" part matters for production use: it tracks *when* each observation became available, enabling realistic backtesting where you never accidentally train on data that would not have existed at prediction time. For a first forecast you can ignore that complexity and use the convenience constructor ``from_dataframe``.

Your DataFrame needs a ``DatetimeIndex`` named ``timestamp`` and at least one target column (typically ``load``). Weather covariates such as ``temperature`` or ``wind_speed`` are optional but improve accuracy significantly.

.. code-block:: python

    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta, timezone

    # Build a simple synthetic dataset: 90 days of hourly load data
    n_hours = 90 * 24
    index = pd.date_range(
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        periods=n_hours,
        freq="h",
        name="timestamp",
    )

    rng = np.random.default_rng(42)
    # Simulate a daily load cycle with some noise and a temperature covariate
    hour_of_day = index.hour
    day_of_week = index.dayofweek
    temperature = 10 + 5 * np.sin(2 * np.pi * index.dayofyear / 365) + rng.normal(0, 1, n_hours)
    load = (
        200
        + 50 * np.sin(2 * np.pi * (hour_of_day - 8) / 24)   # daily cycle
        - 20 * (day_of_week >= 5).astype(float)              # weekend dip
        - 1.5 * temperature                                   # temperature effect
        + rng.normal(0, 5, n_hours)                          # noise
    )

    energy_data = pd.DataFrame(
        {"load": load, "temperature": temperature},
        index=index,
    )

    print(energy_data.head())
    print(f"Shape: {energy_data.shape}, range: {energy_data.index[0]} → {energy_data.index[-1]}")

Now wrap it in a ``VersionedTimeSeriesDataset``:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    sample_interval = timedelta(hours=1)
    dataset = VersionedTimeSeriesDataset.from_dataframe(energy_data, sample_interval)

The ``sample_interval`` tells the library the expected spacing between observations. OpenSTEF uses this to detect gaps, align lag features correctly, and validate that your data is consistent before training begins.

.. note::

   For real data, use ``create_synthetic_forecasting_dataset`` from ``openstef_core.testing`` to generate a realistic multi-feature dataset during development. It produces load, wind, temperature, and radiation columns with configurable influence weights — useful for validating your pipeline before connecting live data.


Step 2: Configure Feature Engineering
---------------------------------------

Raw load measurements alone are rarely sufficient. A model needs to understand *context*: what time of day is it, is today a public holiday, what was the load 24 hours ago? The ``FeaturePipeline`` is where you encode that domain knowledge.

OpenSTEF provides ready-made transforms you compose in order:

- ``HolidayFeatures`` — adds binary flags for public holidays by country
- ``LagTransform`` — creates lagged copies of target and covariate columns
- ``StandardScaler`` — normalises features to zero mean and unit variance before passing them to the model

.. code-block:: python

    from openstef_models.preprocessing.feature_pipeline import FeaturePipeline
    from openstef_models.preprocessing.transforms import (
        HolidayFeatures,
        LagTransform,
        StandardScaler,
    )

    preprocessing = FeaturePipeline(
        transforms=[
            HolidayFeatures(country_code="NL"),
            LagTransform(
                lags=[timedelta(hours=24), timedelta(hours=48), timedelta(days=7)],
                columns=["load"],
            ),
            StandardScaler(),
        ]
    )

The lag choices above encode three common patterns in energy data: yesterday's load at the same hour (``24h``), the day before (``48h``), and the same hour last week (``7d``). The 7-day lag is especially powerful for capturing weekly seasonality.

.. warning::

   Lag transforms introduce ``NaN`` rows at the start of your dataset — a 7-day lag means the first 168 rows cannot be used for training. You **must** account for this by setting ``cutoff_history`` on the ``ForecastingModel`` (see Step 3). Failing to do so will silently degrade model quality.


Step 3: Train the Model
------------------------

``ForecastingModel`` is the central class that wires preprocessing, a forecaster, and optional postprocessing into a single ``fit`` / ``predict`` interface. For this tutorial we use ``XGBoostForecaster``, which is the recommended default for energy forecasting.

.. code-block:: python

    from openstef_models.models import ForecastingModel
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Configure the underlying XGBoost model
    hparams = XGBoostHyperParams(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
    )
    forecaster = XGBoostForecaster(hparams=hparams)

    # Assemble the full pipeline
    model = ForecastingModel(
        forecaster=forecaster,
        preprocessing=preprocessing,
        cutoff_history=timedelta(days=7),   # skip the first 7 days of NaN-padded lags
    )

The ``cutoff_history`` parameter is critical. It tells ``ForecastingModel.fit()`` to exclude the first 7 days of training data — exactly the window made unusable by the 7-day lag transform. Set this to match the longest lag in your ``FeaturePipeline``.

Now split your data and train:

.. code-block:: python

    # Use the first 75 days for training, hold out the last 15 for evaluation
    split_time = energy_data.index[-1] - timedelta(days=15)

    train_data = VersionedTimeSeriesDataset.from_dataframe(
        energy_data[energy_data.index <= split_time],
        sample_interval,
    )
    test_data = VersionedTimeSeriesDataset.from_dataframe(
        energy_data[energy_data.index > split_time],
        sample_interval,
    )

    model.fit(train_data)
    print("Training complete.")

``fit()`` runs the full pipeline: it fits the ``FeaturePipeline`` transforms on the training data, applies them, trims the ``cutoff_history`` rows, and trains the underlying ``XGBoostForecaster``. The fitted transforms are stored inside the model so that ``predict()`` applies exactly the same transformations at inference time — no leakage, no manual bookkeeping.


Step 4: Generate a Forecast
----------------------------

With a fitted model, generating predictions is a single call:

.. code-block:: python

    forecast_dataset = model.predict(test_data)

    # The result is a ForecastDataset containing quantile predictions
    forecast_df = forecast_dataset.to_dataframe()
    print(forecast_df.head())
    print(f"Columns: {forecast_df.columns.tolist()}")

The returned ``ForecastDataset`` contains predictions for multiple quantiles (e.g., ``q0.1``, ``q0.5``, ``q0.9``) by default. The median quantile (``q0.5``) is your point forecast; the outer quantiles give you a probabilistic uncertainty band. This is important for grid operators who need to plan for both optimistic and pessimistic scenarios.

.. note::

   ``predict()`` applies the *fitted* preprocessing transforms from training — it does not refit them. This ensures that the scaling and lag computation are consistent between training and inference, which is a common source of subtle bugs when building pipelines manually.

You can also request only a specific forecast horizon by passing a ``forecast_start`` timestamp:

.. code-block:: python

    from datetime import timezone

    forecast_start = energy_data.index[-15 * 24]  # start of the held-out period
    forecast_dataset = model.predict(test_data, forecast_start=forecast_start)


Step 5: Evaluate the Forecast
------------------------------

A forecast is only useful if you know how good it is. OpenSTEF's ``ForecastDataset`` makes it straightforward to extract actuals and predictions for comparison:

.. code-block:: python

    import numpy as np

    forecast_df = forecast_dataset.to_dataframe()

    # Extract point forecast (median) and actuals
    y_pred = forecast_df["q0.5"].values
    y_true = energy_data.loc[forecast_df.index, "load"].values

    # Basic error metrics
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - ss_res / ss_tot

    print(f"MAE:  {mae:.2f} MW")
    print(f"RMSE: {rmse:.2f} MW")
    print(f"R²:   {r2:.4f}")

A good short-term energy forecast typically achieves R² > 0.95 on hourly data with adequate weather covariates. If your score is lower, common causes are:

- **Too few lags** — add lags at 48h and 168h if not already present
- **Missing covariates** — temperature and irradiance are the strongest predictors for most grid connections
- **Insufficient training data** — XGBoost benefits from at least 60–90 days of history
- **Data quality issues** — check for gaps, outliers, or unit inconsistencies in your source data

To evaluate the uncertainty bands, check that the fraction of actuals falling inside the ``[q0.1, q0.9]`` interval is close to 80 %:

.. code-block:: python

    lower = forecast_df["q0.1"].values
    upper = forecast_df["q0.9"].values
    coverage = np.mean((y_true >= lower) & (y_true <= upper))
    print(f"80% interval coverage: {coverage:.1%}  (target ≈ 80%)")


Persisting the Model
---------------------

Once you are satisfied with the evaluation, save the model so it can be reloaded for inference without retraining:

.. code-block:: python

    from pathlib import Path
    from openstef_models.storage import LocalModelStorage

    storage = LocalModelStorage(base_path=Path("./models"))
    model_id = "my_first_forecast_model"

    storage.save(model, model_id)
    print(f"Model saved to {storage.base_path / model_id}")

    # Later, in a separate process:
    loaded_model = storage.load(model_id)
    new_forecast = loaded_model.predict(test_data)

``LocalModelStorage`` serialises the entire pipeline — preprocessing transforms, fitted scaler state, and the trained forecaster — into a single versioned artefact. For production deployments, ``MLFlowStorage`` provides the same interface backed by an MLflow tracking server.


Putting It All Together
------------------------

Here is the complete script without the explanatory breaks:

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_models.models import ForecastingModel
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )
    from openstef_models.preprocessing.feature_pipeline import FeaturePipeline
    from openstef_models.preprocessing.transforms import (
        HolidayFeatures,
        LagTransform,
        StandardScaler,
    )
    from openstef_models.storage import LocalModelStorage

    # --- 1. Data ---
    n_hours = 90 * 24
    index = pd.date_range(
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        periods=n_hours, freq="h", name="timestamp",
    )
    rng = np.random.default_rng(42)
    temperature = 10 + 5 * np.sin(2 * np.pi * index.dayofyear / 365) + rng.normal(0, 1, n_hours)
    load = (
        200 + 50 * np.sin(2 * np.pi * (index.hour - 8) / 24)
        - 20 * (index.dayofweek >= 5).astype(float)
        - 1.5 * temperature + rng.normal(0, 5, n_hours)
    )
    energy_data = pd.DataFrame({"load": load, "temperature": temperature}, index=index)
    sample_interval = timedelta(hours=1)
    split_time = energy_data.index[-15 * 24]
    train_data = VersionedTimeSeriesDataset.from_dataframe(
        energy_data[energy_data.index <= split_time], sample_interval
    )
    test_data = VersionedTimeSeriesDataset.from_dataframe(
        energy_data[energy_data.index > split_time], sample_interval
    )

    # --- 2. Feature engineering ---
    preprocessing = FeaturePipeline(
        transforms=[
            HolidayFeatures(country_code="NL"),
            LagTransform(
                lags=[timedelta(hours=24), timedelta(hours=48), timedelta(days=7)],
                columns=["load"],
            ),
            StandardScaler(),
        ]
    )

    # --- 3. Model ---
    model = ForecastingModel(
        forecaster=XGBoostForecaster(hparams=XGBoostHyperParams(n_estimators=200)),
        preprocessing=preprocessing,
        cutoff_history=timedelta(days=7),
    )
    model.fit(train_data)

    # --- 4. Forecast ---
    forecast_df = model.predict(test_data).to_dataframe()

    # --- 5. Evaluate ---
    y_true = energy_data.loc[forecast_df.index, "load"].values
    y_pred = forecast_df["q0.5"].values
    mae = np.mean(np.abs(y_true - y_pred))
    r2 = 1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2)
    print(f"MAE: {mae:.2f}  R²: {r2:.4f}")

    # --- Persist ---
    storage = LocalModelStorage(base_path=Path("./models"))
    storage.save(model, "my_first_forecast_model")


Next Steps
-----------

You now have a working forecast pipeline. From here, the natural next steps are:

- :doc:`backtesting` — learn how to rigorously compare models using walk-forward validation so your evaluation reflects real operational conditions rather than a single held-out split.
- :doc:`advanced_customization` — replace the ``XGBoostForecaster`` with a custom model, add bespoke feature transforms, or integrate a probabilistic postprocessor.
- :doc:`quickstart` — if you want a minimal reference script to copy-paste into a notebook.