Quickstart
==========

This page walks you through producing your first energy forecast with OpenSTEF in under five minutes. You will generate synthetic load data, configure a preset forecasting workflow, train a model, and retrieve probabilistic predictions — all in a single script.

Before continuing, make sure OpenSTEF is installed. See the :doc:`installation` page if you have not done that yet.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

The Minimal Example
-------------------

The script below is complete and copy-paste ready. It uses only OpenSTEF built-ins: a synthetic dataset generator and the ``openstef_models`` preset workflow.

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.integrations.mlflow import MLFlowStorage
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")

    # 1. Generate synthetic hourly load data (90 days)
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=90),
        wind_influence=-10.0,
        temp_influence=5.0,
        radiation_influence=-7.0,
        stochastic_influence=2.0,
        sample_interval=timedelta(hours=1),
    )

    # 2. Configure the preset workflow
    workflow = create_forecasting_workflow(
        config=ForecastingWorkflowConfig(
            model_id="my_first_forecaster",
            model="gblinear",
            horizons=[LeadTime.from_string("PT36H")],
            quantiles=[Q(0.1), Q(0.5), Q(0.9)],
            mlflow_storage=MLFlowStorage(
                tracking_uri="mlflow_tracking",
                local_artifacts_path=Path("mlflow_tracking_artifacts"),
            ),
        )
    )

    # 3. Train
    result = workflow.fit(dataset)
    if result is not None:
        print(result.metrics_full.to_dataframe())

    # 4. Predict
    forecast = workflow.predict(dataset)
    print(forecast.data.tail())

Running this script trains a gradient-boosted linear model on the synthetic series and prints the last few rows of the forecast, including the 10th, 50th, and 90th percentile predictions.

.. note:: [VISUALIZATION: Example forecast output table showing timestamp index with columns for p10, p50, p90 quantile predictions]

Step-by-Step Breakdown
----------------------

Generating data
^^^^^^^^^^^^^^^

``create_synthetic_forecasting_dataset`` produces a :class:`~openstef_core.datasets.timeseries_dataset.TimeSeriesDataset` with a ``load`` target column and weather-like feature columns (wind, temperature, radiation). The influence parameters control how strongly each feature drives the synthetic load signal. For real projects you would replace this call with your own ``TimeSeriesDataset``, but the synthetic generator is useful for experimenting without needing live data.

Configuring the workflow
^^^^^^^^^^^^^^^^^^^^^^^^

``ForecastingWorkflowConfig`` is a Pydantic model that bundles everything the preset needs:

- **model_id** — a unique string identifier stored alongside the trained artefacts in MLflow.
- **model** — the underlying booster. Supported values include ``"xgboost"``, ``"gblinear"``, and ``"lgbm"``.
- **horizons** — a list of :class:`~openstef_core.types.LeadTime` values expressed as ISO 8601 duration strings (e.g. ``"PT36H"`` for 36 hours ahead). The workflow trains one sub-model per horizon.
- **quantiles** — probability levels for uncertainty estimation. ``Q(0.5)`` is the median; adding ``Q(0.1)`` and ``Q(0.9)`` gives you an 80 % prediction interval.
- **mlflow_storage** — tells the workflow where to persist model artefacts and metrics. The paths above write to the current working directory.

``create_forecasting_workflow`` returns a ``CustomForecastingWorkflow`` instance wired up with the feature engineering pipeline, the chosen model, and the MLflow backend.

Training
^^^^^^^^

``workflow.fit(dataset)`` runs the full training pipeline: feature engineering, train/validation splitting, model fitting, and evaluation. The returned ``result`` object exposes ``metrics_full`` and ``metrics_test`` DataFrames so you can inspect R² and other scores immediately after training.

.. note::

   ``fit`` returns ``None`` when the workflow determines there is insufficient data to evaluate. This is normal for very short datasets; the model is still trained.

Predicting
^^^^^^^^^^

``workflow.predict(dataset)`` generates forecasts for all configured horizons and quantiles. The return value is a :class:`~openstef_core.datasets.ForecastDataset`. Its most useful attributes are:

- ``forecast.data`` — the full DataFrame of quantile predictions indexed by timestamp.
- ``forecast.median_series`` — a convenience accessor for the ``Q(0.5)`` column.
- ``forecast.quantiles_data`` — a dict mapping each quantile to its prediction series.

Visualising the Result
----------------------

OpenSTEF ships a Plotly-based plotter in ``openstef_beam`` for interactive HTML charts. Append the following lines to the script above:

.. code-block:: python

    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

    fig = (
        ForecastTimeSeriesPlotter()
        .add_measurements(measurements=dataset.select_version().data["load"])
        .add_model(
            model_name="gblinear",
            forecast=forecast.median_series,
            quantiles=forecast.quantiles_data,
        )
        .plot()
    )
    fig.write_html("forecast_plot.html")

Open ``forecast_plot.html`` in any browser to see the observed load overlaid with the median forecast and the shaded uncertainty band.

.. note:: [VISUALIZATION: Interactive Plotly chart showing observed load (grey line), median forecast (blue line), and shaded 10th–90th percentile band over a 36-hour horizon]

What to Do Next
---------------

This example uses all default hyperparameters and a single horizon. Once you are comfortable with the basic loop, you can:

- **Add more horizons** — pass multiple ``LeadTime`` values to ``horizons`` to train a multi-horizon model in one call.
- **Tune hyperparameters** — ``ForecastingWorkflowConfig`` exposes ``xgboost_hyperparams``, ``gblinear_hyperparams``, and ``lgbm_hyperparams`` fields for fine-grained control.
- **Use real data** — construct a ``TimeSeriesDataset`` from a pandas DataFrame with your own load and weather columns.
- **Switch to an ensemble** — ``openstef_meta`` provides ``create_ensemble_forecasting_workflow`` and ``EnsembleForecastingWorkflowConfig`` for combining multiple base models.

Refer to the other pages in this section for installation details and deeper configuration options.