Quickstart
==========

This page gets you to a working short-term energy forecast in the shortest possible
time. You will define a prediction job, generate synthetic load data, train a model,
and produce a forecast — all in a single self-contained script. No database, no MLflow
server, and no external data sources are required.

Before continuing, make sure OpenSTEF is installed. See :doc:`installation` if you
have not done that yet.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

-----------

The core objects
----------------

Every OpenSTEF workflow revolves around two small data-class objects:

- **PredictionJobDataClass** — describes *what* you want to forecast: the asset
  identifier, model type, forecast horizon, and a handful of operational settings.
- **ModelSpecificationDataClass** — describes *how* the model is built: which
  algorithm to use, hyper-parameters, and (after training) the list of feature names
  the model expects.

Both are plain Python dataclasses, so you construct them directly in code with no
configuration files needed.

.. code-block:: python

    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.data_classes.model_specifications import ModelSpecificationDataClass

    pj = PredictionJobDataClass(
        id=1,
        model="xgb",           # gradient-boosted trees via XGBoost
        forecast_type="demand",
        horizon_minutes=2880,  # 48-hour horizon
        resolution_minutes=15, # 15-minute resolution
        lat=52.1,
        lon=5.1,
        name="quickstart-asset",
    )

    model_specs = ModelSpecificationDataClass(feature_names=None)

-----------

Generating synthetic input data
--------------------------------

OpenSTEF pipelines expect a :class:`pandas.DataFrame` whose **first column** is the
target (measured load in MW) and whose remaining columns are predictor features such
as weather variables. The index must be a timezone-aware :class:`pandas.DatetimeIndex`.

The snippet below creates two years of synthetic 15-minute load data with a simple
daily pattern plus noise — enough history for the training pipeline to work with.

.. code-block:: python

    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)

    # Two years of 15-minute timestamps, UTC-aware
    index = pd.date_range(
        start="2022-01-01",
        end="2023-12-31 23:45",
        freq="15min",
        tz="UTC",
    )

    # Synthetic load: daily sinusoid + small Gaussian noise
    hours = index.hour + index.minute / 60
    load = 50 + 20 * np.sin(2 * np.pi * (hours - 6) / 24) + rng.normal(0, 2, len(index))

    # A simple temperature proxy as an extra feature
    temperature = 10 + 5 * np.sin(2 * np.pi * index.dayofyear / 365) + rng.normal(0, 1, len(index))

    input_data = pd.DataFrame(
        {"load_mw": load, "temperature": temperature},
        index=index,
    )

.. note:: [VISUALIZATION: Line plot of the synthetic load time series showing the daily sinusoidal pattern over a two-week window]

-----------

Training the model
------------------

Use ``train_model_pipeline_core`` to fit a model directly from your DataFrame. This
function handles feature engineering, train/validation splitting, and model fitting
internally. It returns the trained model, a training report, and the split data sets.

.. code-block:: python

    from openstef.pipeline.train_model import train_model_pipeline_core

    model, report, model_specs, (train_data, val_data, test_data, _) = (
        train_model_pipeline_core(
            pj=pj,
            model_specs=model_specs,
            input_data=input_data,
        )
    )

    # model_specs.feature_names is now populated by the pipeline
    print("Trained features:", model_specs.feature_names[:5])

The returned ``model`` is an :class:`~openstef.model.regressors.regressor.OpenstfRegressor`
instance. The ``report`` object contains training metrics and feature importances that
you can inspect or log separately.

-----------

Producing a forecast
--------------------

To forecast, you need a DataFrame that covers the historical context window **plus**
the future period you want to predict. Mark the future rows by setting the target
column to ``NaN`` — the pipeline uses the first contiguous block of ``NaN`` values to
determine the forecast horizon automatically.

.. code-block:: python

    from openstef.pipeline.create_forecast import create_forecast_pipeline_core

    # Append 48 hours of future rows with NaN target
    future_index = pd.date_range(
        start=input_data.index[-1] + pd.Timedelta("15min"),
        periods=192,  # 48 h × 4 per hour
        freq="15min",
        tz="UTC",
    )
    future_temperature = 10 + rng.normal(0, 1, len(future_index))

    future_rows = pd.DataFrame(
        {"load_mw": np.nan, "temperature": future_temperature},
        index=future_index,
    )

    forecast_input = pd.concat([input_data.tail(672), future_rows])  # ~7 days context

    # Run the forecast pipeline
    forecast = create_forecast_pipeline_core(
        pj=pj,
        input_data=forecast_input,
        model=model,
        model_specs=model_specs,
    )

    print(forecast[["forecast", "quantile_P10", "quantile_P50", "quantile_P90"]].head())

The result is a DataFrame indexed by timestamp. The ``forecast`` column holds the
point prediction; ``quantile_P10`` through ``quantile_P90`` provide the confidence
interval.

.. note:: [VISUALIZATION: Plot of the 48-hour forecast with shaded confidence interval band (P10–P90) and the point forecast line]

-----------

Complete script
---------------

The following is the full copy-paste-ready version of everything above:

.. code-block:: python

    import numpy as np
    import pandas as pd

    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.data_classes.model_specifications import ModelSpecificationDataClass
    from openstef.pipeline.train_model import train_model_pipeline_core
    from openstef.pipeline.create_forecast import create_forecast_pipeline_core

    # ── 1. Configure ──────────────────────────────────────────────────────────
    pj = PredictionJobDataClass(
        id=1,
        model="xgb",
        forecast_type="demand",
        horizon_minutes=2880,
        resolution_minutes=15,
        lat=52.1,
        lon=5.1,
        name="quickstart-asset",
    )
    model_specs = ModelSpecificationDataClass(feature_names=None)

    # ── 2. Synthetic data ─────────────────────────────────────────────────────
    rng = np.random.default_rng(42)
    index = pd.date_range("2022-01-01", "2023-12-31 23:45", freq="15min", tz="UTC")
    hours = index.hour + index.minute / 60
    load = 50 + 20 * np.sin(2 * np.pi * (hours - 6) / 24) + rng.normal(0, 2, len(index))
    temperature = 10 + 5 * np.sin(2 * np.pi * index.dayofyear / 365) + rng.normal(0, 1, len(index))
    input_data = pd.DataFrame({"load_mw": load, "temperature": temperature}, index=index)

    # ── 3. Train ──────────────────────────────────────────────────────────────
    model, report, model_specs, _ = train_model_pipeline_core(
        pj=pj,
        model_specs=model_specs,
        input_data=input_data,
    )

    # ── 4. Forecast ───────────────────────────────────────────────────────────
    future_index = pd.date_range(
        start=input_data.index[-1] + pd.Timedelta("15min"),
        periods=192,
        freq="15min",
        tz="UTC",
    )
    future_rows = pd.DataFrame(
        {"load_mw": np.nan, "temperature": rng.normal(10, 1, 192)},
        index=future_index,
    )
    forecast_input = pd.concat([input_data.tail(672), future_rows])

    forecast = create_forecast_pipeline_core(
        pj=pj,
        input_data=forecast_input,
        model=model,
        model_specs=model_specs,
    )

    # ── 5. Inspect output ─────────────────────────────────────────────────────
    print(forecast[["forecast", "quantile_P10", "quantile_P50", "quantile_P90"]].head(8))

-----------

What to do next
---------------

This example uses the ``_core`` pipeline variants, which keep all state in memory and
require no external services. When you move toward production you will typically want:

- **Persistent model storage** — swap ``train_model_pipeline_core`` for
  ``train_model_pipeline``, which serialises the trained model to MLflow.
- **Real input data** — replace the synthetic DataFrame with your own time-series
  data, ensuring the index is UTC-aware and the target column is first.
- **Hyperparameter tuning** — use
  ``openstef.pipeline.optimize_hyperparameters.optimize_hyperparameters_pipeline_core``
  before training to search for better model settings.

.. note::

   The ``_core`` functions used here bypass MLflow and any database layer entirely.
   They are the right choice for experimentation and unit testing. The non-``_core``
   counterparts add persistence and are intended for scheduled operational workflows.