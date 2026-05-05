Quickstart
==========

This page walks you through producing your first short-term energy forecast with
OpenSTEF. By the end you will have trained a model on synthetic load data and
generated a probabilistic forecast — all in a single Python script you can run
immediately after :doc:`installation`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Overview
--------

OpenSTEF organises every forecasting task around a **PredictionJob**: a plain
dictionary (or dataclass) that describes *what* you want to forecast and *how*.
You pass that job to a pipeline, which handles data preprocessing, feature
engineering, model training, and prediction in one call. You do not need to wire
those steps together yourself.

The minimal path to a forecast is:

1. Define a ``PredictionJob`` with a model type and resolution.
2. Build a synthetic training dataset.
3. Call the training pipeline to fit a model.
4. Call the prediction pipeline to produce a forecast.

Step 1 — Define a PredictionJob
--------------------------------

A ``PredictionJob`` is the single configuration object that every OpenSTEF
pipeline reads. At minimum it needs an identifier, a model type, and the
temporal resolution of your data in minutes.

.. code-block:: python

    from openstef.data_classes.prediction_job import PredictionJobDataClass

    pj = PredictionJobDataClass(
        id=1,
        name="quickstart-transformer",
        model="xgb",          # XGBoost — fast and reliable default
        resolution_minutes=15,
        horizon_minutes=2880, # 48-hour forecast horizon
        lat=52.1,
        lon=5.1,
    )

``model="xgb"`` selects the built-in XGBoost regressor. Other supported values
include ``"lgb"`` (LightGBM) and ``"linear"``; see :doc:`../user_guide/models`
for the full list.

Step 2 — Create Synthetic Training Data
----------------------------------------

OpenSTEF pipelines expect a ``pandas.DataFrame`` with a ``DatetimeIndex`` and at
least one column named ``load`` (the target variable, in MW). Weather features
and other covariates can be added as additional columns; the library will
automatically engineer lag features, calendar features, and — when coordinates
are provided — solar-irradiance proxies.

The snippet below generates two months of synthetic 15-minute load data with a
realistic daily profile and some added noise:

.. code-block:: python

    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)

    # 15-minute timestamps over ~60 days
    index = pd.date_range(
        start="2024-01-01", periods=60 * 24 * 4, freq="15min", tz="UTC"
    )

    # Simple daily sinusoidal load profile (MW) + noise
    hours = index.hour + index.minute / 60
    load = 50 + 20 * np.sin(2 * np.pi * (hours - 6) / 24) + rng.normal(0, 2, len(index))

    data = pd.DataFrame({"load": load}, index=index)

.. note:: [VISUALIZATION: Time-series plot of the synthetic load profile showing the daily sinusoidal pattern over several days]

Step 3 — Train the Model
-------------------------

Pass the ``PredictionJob`` and the historical ``DataFrame`` to
``train_model_pipeline``. The pipeline splits the data into train/validation
sets, engineers features, fits the model, and returns a trained model object
together with evaluation metrics.

.. code-block:: python

    from openstef.pipeline.train_model import train_model_pipeline

    model, model_specs, train_data, validation_data, test_data = train_model_pipeline(
        pj=pj,
        input_data=data,
    )

    print(f"Model type : {type(model).__name__}")
    print(f"Features   : {model_specs.feature_names[:5]} ...")

The pipeline prints progress to the standard logger. If you want to suppress
output during experimentation, configure Python's ``logging`` module before
calling the pipeline.

.. note::

   ``train_model_pipeline`` performs an automatic train/test split based on the
   ``horizon_minutes`` setting. No manual splitting is required.

Step 4 — Generate a Forecast
------------------------------

With a trained model in hand, call ``create_forecast_pipeline`` to produce
predictions. You supply the same ``PredictionJob``, the trained model, and a
``DataFrame`` that covers the period you want to forecast (it must include the
same feature columns that were present during training, or at least the ``load``
column so that lag features can be computed).

.. code-block:: python

    from openstef.pipeline.create_forecast import create_forecast_pipeline

    # Use the last 48 hours of data as the "live" input window
    forecast_input = data.iloc[-48 * 4 :]

    forecast = create_forecast_pipeline(
        pj=pj,
        input_data=forecast_input,
        model=model,
        model_specs=model_specs,
    )

    print(forecast.head())

The returned ``DataFrame`` contains:

- ``forecast`` — the point prediction (MW).
- ``quantile_Pxx`` columns — probabilistic bounds at configured quantiles (e.g.
  ``quantile_P10``, ``quantile_P90``), giving you an uncertainty bandwidth out
  of the box.

.. note:: [VISUALIZATION: Fan chart showing the point forecast with P10/P90 uncertainty bands over the 48-hour horizon]

Putting It All Together
------------------------

Here is the complete, self-contained script:

.. code-block:: python

    import numpy as np
    import pandas as pd

    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.pipeline.create_forecast import create_forecast_pipeline

    # --- 1. Configure ---
    pj = PredictionJobDataClass(
        id=1,
        name="quickstart-transformer",
        model="xgb",
        resolution_minutes=15,
        horizon_minutes=2880,
        lat=52.1,
        lon=5.1,
    )

    # --- 2. Synthetic data ---
    rng = np.random.default_rng(42)
    index = pd.date_range(
        start="2024-01-01", periods=60 * 24 * 4, freq="15min", tz="UTC"
    )
    hours = index.hour + index.minute / 60
    load = 50 + 20 * np.sin(2 * np.pi * (hours - 6) / 24) + rng.normal(0, 2, len(index))
    data = pd.DataFrame({"load": load}, index=index)

    # --- 3. Train ---
    model, model_specs, train_data, validation_data, test_data = train_model_pipeline(
        pj=pj,
        input_data=data,
    )

    # --- 4. Forecast ---
    forecast_input = data.iloc[-48 * 4 :]
    forecast = create_forecast_pipeline(
        pj=pj,
        input_data=forecast_input,
        model=model,
        model_specs=model_specs,
    )

    print(forecast[["forecast", "quantile_P10", "quantile_P90"]].head(10))

Save this as ``quickstart.py`` and run it with ``python quickstart.py``. No
external data sources, no database connections, and no configuration files are
needed.

What Just Happened
-------------------

Under the hood, the two pipeline calls performed the following steps
automatically:

- **Feature engineering** — lag features (e.g. load 24 h ago, 48 h ago),
  calendar features (hour-of-day, day-of-week, month), and solar-irradiance
  proxies derived from the latitude/longitude you supplied.
- **Train/validation split** — a time-aware split that respects the forecast
  horizon so that no future information leaks into training.
- **Model fitting** — XGBoost trained with early stopping on the validation set.
- **Probabilistic output** — quantile estimates produced alongside the point
  forecast, giving you a built-in uncertainty bandwidth.

.. note::

   OpenSTEF's probabilistic forecasts are not post-hoc confidence intervals —
   they are trained directly as part of the model. The width of the band reflects
   genuine model uncertainty, not just historical residual spread.

Next Steps
----------

This example uses the simplest possible setup. Once you are comfortable with the
basic flow, the following pages cover the natural next topics:

- **Adding real weather data** — enrich your ``DataFrame`` with temperature,
  wind speed, and irradiance columns to improve accuracy on solar and wind
  assets. See :doc:`../user_guide/feature_engineering`.
- **Persisting models** — save and reload trained models so you can separate
  training jobs from forecasting jobs. See :doc:`../user_guide/models`.
- **Evaluating forecast quality** — interpret the metrics returned by
  ``train_model_pipeline`` and run backtests. See
  :doc:`../user_guide/evaluation`.
- **Scheduling forecasts** — integrate OpenSTEF into a cron job or workflow
  orchestrator. See :doc:`../deployment/scheduling`.