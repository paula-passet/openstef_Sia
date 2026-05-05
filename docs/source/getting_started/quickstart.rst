Quickstart
==========

This page walks you through producing your first short-term energy forecast with
OpenSTEF. In about 30 lines of Python you will define a prediction job, generate
synthetic training data, train a model, and produce a forecast — no database or
MLflow server required.

Before continuing, make sure OpenSTEF is installed. See the
:doc:`installation` page if you have not done that yet.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

The concept
-----------

Every OpenSTEF workflow revolves around two lightweight data-class objects:

- **PredictionJobDataClass** — describes *what* to forecast (location, model
  type, quantiles, horizon, etc.).
- **ModelSpecificationDataClass** — carries model hyper-parameters and, after
  training, the list of feature names the model expects.

These objects are passed through pipeline functions that handle feature
engineering, training, and inference. Because the pipeline functions are
ordinary Python callables, you can call them directly without any surrounding
infrastructure.

Step 1 — Define the prediction job
-----------------------------------

.. code-block:: python

    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.data_classes.model_specifications import ModelSpecificationDataClass

    pj = PredictionJobDataClass(
        id=1,
        model="xgb",           # gradient-boosted trees
        quantiles=[0.10, 0.50, 0.90],
        horizon_minutes=2880,  # 48-hour forecast horizon
        resolution_minutes=15, # 15-minute intervals
        lat=52.0,
        lon=5.0,
        name="quickstart-demo",
        pipelines_to_run=["train", "forecast"],
    )

    model_specs = ModelSpecificationDataClass(id="quickstart-demo")

``PredictionJobDataClass`` validates its fields on construction, so typos in
model names or impossible horizon values are caught immediately.

Step 2 — Create a synthetic dataset
-------------------------------------

OpenSTEF expects a ``pandas.DataFrame`` whose **first column is the target
load** (MW or similar unit) and whose remaining columns are predictor features
such as weather variables. The index must be a timezone-aware
``DatetimeIndex``.

The snippet below builds a minimal dataset with a sinusoidal load profile and
two synthetic weather features:

.. code-block:: python

    import numpy as np
    import pandas as pd

    # Two years of 15-minute data
    index = pd.date_range(
        start="2022-01-01",
        end="2023-12-31 23:45",
        freq="15min",
        tz="UTC",
    )
    rng = np.random.default_rng(42)

    load = (
        50                                                               # base load (MW)
        + 20 * np.sin(2 * np.pi * np.arange(len(index)) / (4 * 24))    # daily cycle
        + rng.normal(0, 2, len(index))                                   # noise
    )

    data = pd.DataFrame(
        {
            "load":        load,
            "temperature": 10 + 5 * np.sin(2 * np.pi * np.arange(len(index)) / (4 * 24 * 365)),
            "wind_speed":  rng.uniform(0, 10, len(index)),
        },
        index=index,
    )

    # The last 48 hours become the forecast window — set target to NaN there
    forecast_cutoff = data.index[-1] - pd.Timedelta(hours=48)
    forecast_data = data.copy()
    forecast_data.loc[forecast_cutoff:, "load"] = np.nan

.. note:: [VISUALIZATION: Time-series plot of the synthetic load column showing the sinusoidal daily pattern and the NaN forecast window at the end]

The NaN values in the target column tell ``create_forecast_pipeline_core``
which timestamps need a prediction.

Step 3 — Train a model
-----------------------

``train_model_pipeline_core`` handles feature engineering, train/validation
splitting, and model fitting in one call:

.. code-block:: python

    from openstef.pipeline.train_model import train_model_pipeline_core

    model, report, model_specs, (train_df, val_df, test_df, _) = (
        train_model_pipeline_core(
            pj=pj,
            model_specs=model_specs,
            input_data=data,          # full dataset including target
            horizons=[0.25, 24.0],    # feature horizons in hours
        )
    )

    print(f"Trained model type : {type(model).__name__}")
    print(f"Validation MAE     : {report.metrics.get('mae', 'n/a'):.2f} MW")

The returned ``model`` is an ``OpenstfRegressor`` — a scikit-learn-compatible
estimator. ``report`` contains training metrics and feature importances.
``model_specs.feature_names`` is now populated with the exact columns the model
was trained on; this list is required in the next step.

Step 4 — Produce a forecast
-----------------------------

Pass the trained model and the forecast-window data (target column set to NaN)
to ``create_forecast_pipeline_core``:

.. code-block:: python

    from openstef.pipeline.create_forecast import create_forecast_pipeline_core

    forecast = create_forecast_pipeline_core(
        pj=pj,
        input_data=forecast_data,
        model=model,
        model_specs=model_specs,
    )

    print(forecast[["forecast", "forecast_wind_power_quantile_P10",
                     "forecast_wind_power_quantile_P90"]].head())

The result is a ``DataFrame`` indexed by timestamp. The ``forecast`` column
holds the point prediction; additional columns carry the quantile bounds you
specified in ``pj.quantiles``.

.. note:: [VISUALIZATION: Line chart of the 48-hour forecast with shaded P10–P90 confidence band overlaid on the known load values]

.. note::

   ``create_forecast_pipeline_core`` does not load or save models from disk.
   It operates entirely in memory, which makes it straightforward to embed in
   unit tests or notebooks.

Complete copy-paste example
----------------------------

The following block combines all four steps into a single, self-contained
script:

.. code-block:: python

    import numpy as np
    import pandas as pd

    from openstef.data_classes.prediction_job import PredictionJobDataClass
    from openstef.data_classes.model_specifications import ModelSpecificationDataClass
    from openstef.pipeline.train_model import train_model_pipeline_core
    from openstef.pipeline.create_forecast import create_forecast_pipeline_core

    # --- 1. Prediction job ---
    pj = PredictionJobDataClass(
        id=1,
        model="xgb",
        quantiles=[0.10, 0.50, 0.90],
        horizon_minutes=2880,
        resolution_minutes=15,
        lat=52.0,
        lon=5.0,
        name="quickstart-demo",
        pipelines_to_run=["train", "forecast"],
    )
    model_specs = ModelSpecificationDataClass(id="quickstart-demo")

    # --- 2. Synthetic data ---
    index = pd.date_range("2022-01-01", "2023-12-31 23:45", freq="15min", tz="UTC")
    rng   = np.random.default_rng(42)
    t     = np.arange(len(index))
    data  = pd.DataFrame(
        {
            "load":        50 + 20 * np.sin(2 * np.pi * t / 96) + rng.normal(0, 2, len(t)),
            "temperature": 10 + 5  * np.sin(2 * np.pi * t / (96 * 365)),
            "wind_speed":  rng.uniform(0, 10, len(t)),
        },
        index=index,
    )

    # --- 3. Train ---
    model, report, model_specs, _ = train_model_pipeline_core(
        pj=pj,
        model_specs=model_specs,
        input_data=data,
        horizons=[0.25, 24.0],
    )

    # --- 4. Forecast ---
    forecast_data = data.copy()
    forecast_data.loc[data.index[-1] - pd.Timedelta(hours=48):, "load"] = np.nan

    forecast = create_forecast_pipeline_core(
        pj=pj,
        input_data=forecast_data,
        model=model,
        model_specs=model_specs,
    )

    print(forecast["forecast"].describe())

Run this script from any Python environment where OpenSTEF is installed and you
will see a statistical summary of the 48-hour point forecast printed to the
terminal.

Next steps
----------

- **Persist models** — learn how to save and reload trained models with
  ``MLflowSerializer`` so you can separate training from inference jobs.
- **Real data** — replace the synthetic ``DataFrame`` with your own metered
  load and weather observations; the pipeline functions accept any
  ``DatetimeIndex``-ed DataFrame that follows the column convention above.
- **Hyperparameter tuning** — ``optimize_hyperparameters_pipeline_core`` in
  ``openstef.pipeline.optimize_hyperparameters`` runs an Optuna study to find
  better model parameters before training.
- **Component forecasts** — ``create_components_forecast_pipeline`` in
  ``openstef.pipeline.create_component_forecast`` decomposes a net load
  forecast into wind, solar, and base-load components.