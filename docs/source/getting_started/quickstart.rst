Quickstart
==========

This page gets you from a fresh install to a working energy forecast in minutes. You will
configure a prediction job, generate synthetic load data, train a model, and produce a
forecast — all without a database or external data source.

If you have not installed OpenSTEF yet, see the :doc:`installation` page first.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Overview
--------

Every OpenSTEF workflow revolves around two lightweight data classes:

- **PredictionJobDataClass** — describes *what* to forecast (location, model type, forecast horizon, quantiles, etc.).
- **ModelSpecificationDataClass** — describes *how* to model it (algorithm hyper-parameters, feature names, feature modules).

The core pipeline functions accept these objects together with a plain
``pandas.DataFrame`` of historical load measurements and return a trained model or a
forecast DataFrame. No database connection is required when calling the ``_core``
variants of the pipelines.

Your First Forecast
-------------------

The complete example below runs end-to-end. Copy it into a script or notebook and
execute it directly.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta, timezone

    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.data_classes.model_specifications import ModelSpecificationDataClass
    from openstef.pipeline.train_model import train_model_pipeline_core
    from openstef.pipeline.create_forecast import create_forecast_pipeline_core

    # ── 1. Configure the prediction job ──────────────────────────────────────
    pj = PredictionJobDataClass(
        id=1,
        model="xgb",                  # XGBoost regressor
        forecast_type="demand",
        horizon_minutes=2880,          # 48-hour forecast horizon
        resolution_minutes=15,         # 15-minute intervals
        lat=52.1,
        lon=5.1,
        quantiles=[0.10, 0.50, 0.90],  # probabilistic output
    )

    model_specs = ModelSpecificationDataClass(id=pj["id"])

    # ── 2. Generate synthetic load data ──────────────────────────────────────
    # Real usage: replace this block with your own measured load time series.
    rng = np.random.default_rng(42)
    periods = 4 * 24 * 90          # 90 days at 15-minute resolution
    index = pd.date_range(
        end=datetime.now(tz=timezone.utc),
        periods=periods,
        freq="15min",
        tz="UTC",
    )
    # Simulate a daily load pattern with noise
    hour_of_day = index.hour + index.minute / 60
    base_load = 200 + 80 * np.sin(np.pi * (hour_of_day - 6) / 12)
    noise = rng.normal(scale=10, size=periods)
    input_data = pd.DataFrame({"load": base_load + noise}, index=index)

    # ── 3. Train the model ────────────────────────────────────────────────────
    model, report, model_specs, data_sets = train_model_pipeline_core(
        pj=pj,
        model_specs=model_specs,
        input_data=input_data,
        horizons=[0.25, 24.0, 47.0],  # hours ahead
    )

    print("Training complete.")
    print(f"  Model type : {type(model).__name__}")
    print(f"  Features   : {len(model_specs.feature_names)} features used")

    # ── 4. Produce a forecast ─────────────────────────────────────────────────
    # For forecasting, provide recent history so features can be computed.
    recent_data = input_data.iloc[-4 * 24 * 7 :]   # last 7 days

    forecast = create_forecast_pipeline_core(
        pj=pj,
        input_data=recent_data,
        model=model,
        model_specs=model_specs,
    )

    print("\nForecast (first 5 rows):")
    print(forecast.head())

.. note:: [VISUALIZATION: Line chart showing synthetic load time series (training data) alongside the 48-hour probabilistic forecast with 10th/50th/90th percentile bands]

Understanding the Output
------------------------

``create_forecast_pipeline_core`` returns a ``pandas.DataFrame`` indexed by timestamp.
The columns you will typically see are:

- ``forecast`` — the point forecast (median by default).
- ``forecast_other`` — an alternative model's forecast when configured.
- ``stdev`` — standard deviation of the forecast distribution.
- One column per quantile requested in ``pj.quantiles``, e.g. ``quantile_P10``,
  ``quantile_P50``, ``quantile_P90``.

The ``report`` object returned by ``train_model_pipeline_core`` contains feature
importance scores, train/validation/test split metrics, and figures. It is used
internally by the MLflow serializer when you persist models to disk.

Input Data Requirements
-----------------------

The ``input_data`` DataFrame passed to both pipelines must satisfy a few constraints:

- The index must be a timezone-aware ``DatetimeIndex``.
- A column named ``load`` must be present and must be the **first** column when
  additional feature columns are included.
- Gaps and outliers are handled automatically by the built-in validation step, but
  very sparse data (fewer than a few weeks of 15-minute readings) will raise an
  ``InputDataInsufficientError``.

.. note::

   OpenSTEF automatically engineers lag features, calendar features, and trend
   features from the raw load column. You do not need to add these manually.

Choosing a Model Type
---------------------

Set ``pj["model"]`` to any of the supported regressor keys:

- ``"xgb"`` — XGBoost (default, good general-purpose choice).
- ``"xgb_quantile"`` — XGBoost with native quantile regression.
- ``"lgb"`` — LightGBM.
- ``"linear"`` — Lasso/Ridge linear model.
- ``"linear_quantile"`` — Quantile linear regression.

All model types share the same pipeline interface, so switching is a one-line change.

Persisting a Trained Model
--------------------------

The quickstart above keeps the model in memory. In production you will want to save it
with the MLflow serializer so that ``create_forecast_pipeline`` (the database-aware
variant) can reload it by prediction job ID:

.. code-block:: python

    from openstef.model.serializer import MLflowSerializer

    serializer = MLflowSerializer(mlflow_tracking_uri="./mlruns")

    serializer.save_model(
        model=model,
        experiment_name=str(pj["id"]),
        model_type=pj["model"],
        model_specs=model_specs,
        report=report,
    )

    # Later — reload and forecast without retraining:
    loaded_model, loaded_specs = serializer.load_model(
        experiment_name=str(pj["id"])
    )

    forecast = create_forecast_pipeline_core(
        pj=pj,
        input_data=recent_data,
        model=loaded_model,
        model_specs=loaded_specs,
    )

The ``mlflow_tracking_uri`` can point to a local directory (as above), a remote
MLflow tracking server, or an Azure ML workspace URI.

Next Steps
----------

Now that you have a working forecast, explore the rest of the documentation:

- **Installation** — system requirements, optional dependencies, and GPU support:
  :doc:`installation`.
- **Concepts** — deeper explanation of prediction jobs, model specs, and the pipeline
  architecture.
- **Pipelines reference** — all pipeline functions and their parameters.
- **Custom features** — how to add domain-specific feature modules to
  ``ModelSpecificationDataClass.feature_modules``.
- **Backtesting** — evaluate forecast accuracy over historical periods using
  ``train_model_pipeline_core`` with ``backtest=True``.