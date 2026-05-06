Quickstart
==========

This page walks you through producing your first forecast with OpenSTEF in under five minutes. You will configure a preset workflow, train it on synthetic data, and generate predictions — all in a single self-contained script.

If you haven't installed OpenSTEF yet, see the :doc:`installation` page first.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Overview
--------

OpenSTEF organises forecasting logic into *workflows*. A workflow bundles preprocessing, a trained model, and postprocessing into one object. The ``openstef_models.presets`` module provides ``create_forecasting_workflow``, a factory function that builds a ready-to-use workflow from a single configuration object. You only need to:

1. Describe your setup in a ``ForecastingWorkflowConfig``.
2. Call ``create_forecasting_workflow`` to get a workflow instance.
3. Call ``workflow.fit`` with historical data.
4. Call ``workflow.predict`` with a context window to get forecasts.

Generating Synthetic Data
-------------------------

The example below creates a simple sinusoidal load signal with 15-minute resolution — enough to demonstrate the full fit/predict cycle without needing a real dataset.

.. code-block:: python

    import numpy as np
    import pandas as pd

    # Two years of 15-minute data for training, one day for prediction
    freq = "15min"
    train_index = pd.date_range("2022-01-01", periods=70080, freq=freq, tz="UTC")
    predict_index = pd.date_range("2024-01-01", periods=96, freq=freq, tz="UTC")

    rng = np.random.default_rng(42)

    def make_load(index: pd.DatetimeIndex) -> pd.DataFrame:
        t = np.arange(len(index))
        # Daily cycle + weekly cycle + noise
        signal = (
            50.0
            + 20.0 * np.sin(2 * np.pi * t / (96))          # daily
            + 5.0  * np.sin(2 * np.pi * t / (96 * 7))      # weekly
            + rng.normal(scale=2.0, size=len(index))
        )
        return pd.DataFrame({"load": signal}, index=index)

    train_df = make_load(train_index)
    predict_df = make_load(predict_index)

The ``load`` column is the target variable. OpenSTEF's feature engineering will automatically derive lag features, cyclic time features, and more from the index and this single column.

Configuring the Workflow
------------------------

``ForecastingWorkflowConfig`` is a Pydantic model that captures everything the workflow factory needs: which model to use, the forecast horizons, quantiles, location metadata, and column names.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.presets import ForecastingWorkflowConfig
    from openstef_models.presets.forecasting_workflow import LocationConfig

    config = ForecastingWorkflowConfig(
        model_id="quickstart_model",
        model="xgboost",                          # xgboost | lgbm | gblinear | lgbmlinear
        horizons=[timedelta(hours=24)],           # forecast 24 h ahead
        quantiles=[0.1, 0.5, 0.9],               # median + 80 % interval
        sample_interval=timedelta(minutes=15),
        target_column="load",
        location=LocationConfig(
            name="synthetic_site",
            description="Quickstart synthetic load site",
        ),
    )

.. note::

   ``model_id`` must be unique across your project — it is used as the key when persisting model artefacts to MLflow or a local store. For this quickstart, any string works.

Creating and Training the Workflow
----------------------------------

Pass the config to ``create_forecasting_workflow`` to get a ``CustomForecastingWorkflow`` instance, then call ``fit`` with a ``TimeSeriesDataset`` wrapping your training data.

.. code-block:: python

    from openstef_models.presets import create_forecasting_workflow
    from openstef_core.datasets import TimeSeriesDataset

    workflow = create_forecasting_workflow(config)

    # Wrap the DataFrame in a TimeSeriesDataset
    train_dataset = TimeSeriesDataset(data=train_df)

    workflow.fit(train_dataset)

``fit`` runs the full preprocessing pipeline — consistency checks, lag feature construction, cyclic encoding — before handing the prepared data to the underlying model. Training a small XGBoost model on two years of 15-minute data typically completes in a few seconds.

Generating a Forecast
---------------------

After training, pass a context window to ``predict``. The context window must be long enough to compute the lag features the model was trained on (at minimum ``predict_history`` worth of history preceding the forecast horizon).

.. code-block:: python

    # Include enough history before the prediction window for lag features
    context_start = predict_index[0] - timedelta(days=14)
    context_index = pd.date_range(context_start, predict_index[-1], freq=freq, tz="UTC")
    context_df = make_load(context_index)

    predict_dataset = TimeSeriesDataset(data=context_df)

    forecast = workflow.predict(predict_dataset)
    print(forecast)

``predict`` returns a ``TimeSeriesDataset`` containing one column per requested quantile (e.g. ``q0.10``, ``q0.50``, ``q0.90``) aligned to the forecast horizon timestamps.

.. note:: [VISUALIZATION: Line chart showing the synthetic load signal (actuals) overlaid with the median forecast and a shaded 80 % prediction interval for a 24-hour horizon]

Complete Script
---------------

Here is the entire example as a single copy-paste-ready script:

.. code-block:: python

    from datetime import timedelta

    import numpy as np
    import pandas as pd

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
    from openstef_models.presets.forecasting_workflow import LocationConfig

    # ── Synthetic data ────────────────────────────────────────────────────────
    freq = "15min"
    rng = np.random.default_rng(42)

    def make_load(index: pd.DatetimeIndex) -> pd.DataFrame:
        t = np.arange(len(index))
        signal = (
            50.0
            + 20.0 * np.sin(2 * np.pi * t / 96)
            + 5.0  * np.sin(2 * np.pi * t / (96 * 7))
            + rng.normal(scale=2.0, size=len(index))
        )
        return pd.DataFrame({"load": signal}, index=index)

    train_index   = pd.date_range("2022-01-01", periods=70080, freq=freq, tz="UTC")
    predict_index = pd.date_range("2024-01-01", periods=96,    freq=freq, tz="UTC")
    train_df      = make_load(train_index)

    # ── Configure ─────────────────────────────────────────────────────────────
    config = ForecastingWorkflowConfig(
        model_id="quickstart_model",
        model="xgboost",
        horizons=[timedelta(hours=24)],
        quantiles=[0.1, 0.5, 0.9],
        sample_interval=timedelta(minutes=15),
        target_column="load",
        location=LocationConfig(name="synthetic_site", description="Quickstart"),
    )

    # ── Train ─────────────────────────────────────────────────────────────────
    workflow = create_forecasting_workflow(config)
    workflow.fit(TimeSeriesDataset(data=train_df))

    # ── Predict ───────────────────────────────────────────────────────────────
    context_start = predict_index[0] - timedelta(days=14)
    context_index = pd.date_range(context_start, predict_index[-1], freq=freq, tz="UTC")
    forecast = workflow.predict(TimeSeriesDataset(data=make_load(context_index)))

    print(forecast)

What to Try Next
----------------

Now that you have a working forecast, a few natural next steps:

- **Swap the model** — change ``model="xgboost"`` to ``"lgbm"`` or ``"gblinear"`` and rerun to compare.
- **Add weather features** — ``ForecastingWorkflowConfig`` accepts ``wind_speed_column``, ``temperature_column``, ``radiation_column``, and others. Pass matching columns in your DataFrame and the workflow will build the corresponding derived features automatically.
- **Enable probabilistic output** — extend the ``quantiles`` list (e.g. ``[0.05, 0.25, 0.5, 0.75, 0.95]``) to get a full prediction interval.
- **Persist with MLflow** — pass an ``mlflow_storage`` object to the config to log models and metrics automatically on each ``fit`` call.