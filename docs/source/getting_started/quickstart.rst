Quickstart
==========

This page walks you through producing your first energy forecast with OpenSTEF in under a minute of reading. You will generate synthetic load data, configure a preset forecasting workflow, train a model, and inspect predictions — all in a single self-contained script.

Before running the examples, make sure OpenSTEF is installed. See :doc:`installation` if you have not done that yet.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

The five-step pattern
---------------------

Every OpenSTEF forecast follows the same five steps:

1. **Create data** — a :class:`~openstef_core.datasets.timeseries_dataset.TimeSeriesDataset` containing your load series and any covariates.
2. **Configure** — a :class:`~openstef_models.presets.forecasting_workflow.ForecastingWorkflowConfig` that names the model, horizons, and quantiles you want.
3. **Build the workflow** — :func:`~openstef_models.presets.forecasting_workflow.create_forecasting_workflow` wires together feature engineering, training, and post-processing for you.
4. **Fit** — call ``workflow.fit(dataset)`` to train the model.
5. **Predict** — call ``workflow.predict(dataset)`` to generate forecasts.

Minimal working example
-----------------------

The script below is copy-paste ready. It uses ``create_synthetic_forecasting_dataset`` so you do not need any real data files.

.. code-block:: python

    from datetime import timedelta

    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    # 1. Generate 90 days of synthetic hourly load data
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=90),
        sample_interval=timedelta(hours=1),
        wind_influence=-10.0,
        temp_influence=5.0,
        radiation_influence=-7.0,
        stochastic_influence=2.0,
    )

    # 2. Configure the preset workflow
    config = ForecastingWorkflowConfig(
        model_id="my_first_forecaster",
        model="gblinear",
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
    )

    # 3. Build the workflow
    workflow = create_forecasting_workflow(config=config)

    # 4. Fit
    workflow.fit(dataset)

    # 5. Predict
    forecast = workflow.predict(dataset)
    print(forecast)

Running this script trains a gradient-boosted linear model to forecast 36 hours ahead and returns a point forecast alongside 10th and 90th percentile prediction intervals.

.. note:: [VISUALIZATION: Example forecast output — time series plot showing observed load, median forecast line, and shaded 10–90 % prediction interval band]

Understanding the configuration
--------------------------------

:class:`~openstef_models.presets.ForecastingWorkflowConfig` is the single place where you control the most important knobs:

- **model** — the underlying algorithm. ``"gblinear"`` (gradient-boosted linear) is a solid default for load forecasting. Other values such as ``"xgb"`` or ``"lgbm"`` are also available.
- **horizons** — a list of :class:`~openstef_core.types.LeadTime` values expressed as ISO 8601 duration strings (e.g. ``"PT1H"``, ``"PT36H"``). The workflow trains one model per horizon.
- **quantiles** — a list of :class:`~openstef_core.types.Q` values between 0 and 1. ``Q(0.5)`` is the median (point forecast); adding ``Q(0.1)`` and ``Q(0.9)`` gives you an 80 % prediction interval.
- **model_id** — a human-readable identifier used when persisting the model to storage.

Persisting the trained model
-----------------------------

By default the workflow keeps the trained model in memory. To save it for later use, add an ``mlflow_storage`` entry to the configuration:

.. code-block:: python

    from pathlib import Path

    from openstef_models.integrations.mlflow import MLFlowStorage
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    config = ForecastingWorkflowConfig(
        model_id="my_first_forecaster",
        model="gblinear",
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        mlflow_storage=MLFlowStorage(
            tracking_uri="mlflow_tracking",
            local_artifacts_path=Path("mlflow_tracking_artifacts"),
        ),
    )

    workflow = create_forecasting_workflow(config=config)
    workflow.fit(dataset)

After fitting, the model artefacts are written to the local MLflow tracking directory. You can open the MLflow UI with ``mlflow ui --backend-store-uri mlflow_tracking`` to inspect metrics and artefacts.

Inspecting training metrics
----------------------------

``workflow.fit()`` returns a result object that contains train, validation, and test metrics:

.. code-block:: python

    prediction_train, prediction_val, prediction_test, result = workflow.fit(dataset)

    # result.metrics_train, result.metrics_val, result.metrics_test
    print(result.metrics_val)

The metrics include standard regression scores (R², MAE, RMSE) computed on the held-out validation split that the workflow creates automatically — you do not need to split the data yourself.

Synthetic data parameters
--------------------------

:func:`~openstef_core.testing.create_synthetic_forecasting_dataset` generates a realistic load series by combining several configurable physical influences:

.. code-block:: python

    dataset = create_synthetic_forecasting_dataset(
        start="2025-01-01T00:00:00+00:00",   # series start (ISO 8601)
        length=timedelta(days=90),            # total length
        sample_interval=timedelta(hours=1),   # resolution
        random_seed=42,                       # reproducibility
        wind_influence=-10.0,                 # MW per normalised wind speed unit
        temp_influence=5.0,                   # MW per degree Celsius
        radiation_influence=-7.0,             # MW per normalised radiation unit
        stochastic_influence=2.0,             # MW standard deviation of noise
        include_atmosphere=False,             # add atmospheric pressure feature
        include_price=False,                  # add electricity price feature
    )

Setting ``include_atmosphere=True`` or ``include_price=True`` adds the corresponding columns to the dataset, which the workflow will automatically use as additional features during training.

.. note::

   ``create_synthetic_forecasting_dataset`` is intended for testing and experimentation. When you are ready to use real data, replace it with a :class:`~openstef_core.datasets.timeseries_dataset.TimeSeriesDataset` built from your own ``pandas.DataFrame``. See the data loading guides for details.

Next steps
----------

- **Ensemble models** — combine multiple base forecasters using ``openstef_meta``; see the ensemble workflow page.
- **Custom feature engineering** — add domain-specific transforms via the ``TransformPipeline`` API.
- **Backtesting** — evaluate forecast skill over a historical window with ``openstef_beam``'s backtesting pipeline.
- **Production deployment** — schedule periodic retraining and live prediction using the pipeline runner.