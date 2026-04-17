Advanced Customization
======================

OpenSTEF is designed to be extended. While the built-in presets and workflow defaults cover the most common forecasting scenarios, power users often need to tailor data preparation, feature engineering, or pipeline composition to their specific grid topology, data sources, or business constraints. This page walks through the three main extension points: custom preprocessing transforms, custom feature engineering pipelines, and custom workflow assembly.

If you are new to OpenSTEF, work through :doc:`first_forecast` and :doc:`quickstart` before reading this page. Backtesting your customized model is covered in :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Understanding the Pipeline Architecture
----------------------------------------

Every forecasting model in OpenSTEF is assembled from three composable stages, all wired together inside a ``ForecastingModel``:

- **preprocessing** — a ``TransformPipeline`` that turns raw ``TimeSeriesDataset`` objects into model-ready feature matrices. This is where feature engineering lives.
- **forecaster** — the core estimator (e.g. an XGBoost or LightGBM regressor wrapped in an OpenSTEF forecaster class).
- **postprocessing** — a second ``TransformPipeline`` that operates on ``ForecastDataset`` outputs, applying calibration, quantile sorting, or confidence intervals.

Each stage is independently replaceable. You can swap in a custom transform at any point without touching the rest of the pipeline.

Custom Feature Engineering
---------------------------

The ``TransformPipeline`` accepts any list of transform objects that implement ``fit`` and ``transform`` (and optionally ``fit_transform``). OpenSTEF ships a rich set of built-in transforms under ``openstef_models.transforms``, organised by domain:

.. code-block:: python

    from openstef_models.transforms import (
        energy_domain,
        general,
        time_domain,
        validation,
        weather_domain,
    )

The most common preprocessing building blocks are lag features, holiday indicators, and data scaling. The example below assembles a preprocessing pipeline explicitly rather than relying on a preset:

.. code-block:: python

    from openstef_models.transforms.time_domain import LagTransform, HolidayFeatures
    from openstef_models.transforms.general import StandardScaler
    from openstef_models.pipeline import TransformPipeline

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatures(country="NL"),   # adds is_holiday, holiday_name columns
            LagTransform(lags=[1, 2, 3, 24, 48, 168]),  # hourly lags up to one week
            StandardScaler(),
        ]
    )

To add domain-specific logic — for example, a feature that encodes grid topology or a custom weather aggregation — write a class with ``fit`` / ``transform`` methods and drop it into the list:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    class PeakHourIndicator:
        """Adds a binary column that flags morning and evening peak hours."""

        def fit(self, data: TimeSeriesDataset, **kwargs) -> "PeakHourIndicator":
            return self  # stateless transform — nothing to learn

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            hour = data.data.index.hour
            data.data["is_peak_hour"] = ((hour >= 7) & (hour <= 9)) | (
                (hour >= 17) & (hour <= 20)
            )
            return data

        def fit_transform(self, data: TimeSeriesDataset, **kwargs) -> TimeSeriesDataset:
            return self.fit(data, **kwargs).transform(data)

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatures(country="NL"),
            PeakHourIndicator(),
            LagTransform(lags=[1, 2, 3, 24, 48, 168]),
            StandardScaler(),
        ]
    )

.. note::

    Transforms are applied in list order during both ``fit`` and ``transform``. Stateful transforms (e.g. ``StandardScaler``) learn their parameters on the training split and replay them on validation and test data automatically — you do not need to manage this manually.

Custom Postprocessing
----------------------

Postprocessing transforms operate on ``ForecastDataset`` objects after the forecaster has produced raw predictions. OpenSTEF provides three built-in postprocessors:

.. code-block:: python

    from openstef_models.transforms.postprocessing import (
        ConfidenceIntervalApplicator,
        IsotonicQuantileCalibrator,
        QuantileSorter,
    )

A typical postprocessing pipeline for probabilistic forecasting looks like this:

.. code-block:: python

    from openstef_models.pipeline import TransformPipeline

    postprocessing = TransformPipeline(
        transforms=[
            IsotonicQuantileCalibrator(),   # recalibrates raw quantile estimates
            QuantileSorter(),               # enforces monotonicity across quantiles
            ConfidenceIntervalApplicator(
                quantiles=[0.05, 0.25, 0.50, 0.75, 0.95],
                add_quantiles_from_std=False,
            ),
        ]
    )

You can write custom postprocessors using the same interface — implement ``fit`` and ``transform`` on ``ForecastDataset`` and insert them at the appropriate position in the list.

Assembling a Custom ForecastingModel
--------------------------------------

Once you have your preprocessing and postprocessing pipelines, wire them into a ``ForecastingModel`` together with your chosen forecaster:

.. code-block:: python

    from openstef_models.models import ForecastingModel
    from openstef_models.forecasters import XGBQuantileForecaster
    from openstef_models.pipeline import TransformPipeline
    from openstef_models.transforms.time_domain import LagTransform, HolidayFeatures
    from openstef_models.transforms.general import StandardScaler
    from openstef_models.transforms.postprocessing import (
        ConfidenceIntervalApplicator,
        IsotonicQuantileCalibrator,
        QuantileSorter,
    )

    model = ForecastingModel(
        preprocessing=TransformPipeline(
            transforms=[
                HolidayFeatures(country="NL"),
                PeakHourIndicator(),          # custom transform from above
                LagTransform(lags=[1, 2, 3, 24, 48, 168]),
                StandardScaler(),
            ]
        ),
        forecaster=XGBQuantileForecaster(
            quantiles=[0.05, 0.25, 0.50, 0.75, 0.95],
        ),
        postprocessing=TransformPipeline(
            transforms=[
                IsotonicQuantileCalibrator(),
                QuantileSorter(),
                ConfidenceIntervalApplicator(
                    quantiles=[0.05, 0.25, 0.50, 0.75, 0.95],
                    add_quantiles_from_std=False,
                ),
            ]
        ),
        target_column="load",
    )

Custom Workflow Orchestration
------------------------------

The ``CustomForecastingWorkflow`` class wraps a ``ForecastingModel`` and handles the train/predict loop, model storage, and optional callbacks (e.g. MLflow logging). Use it directly when you need full control over orchestration:

.. code-block:: python

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.storage import LocalModelStorage
    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from pathlib import Path

    # Wrap the model in a workflow
    workflow = CustomForecastingWorkflow(
        model=model,           # ForecastingModel assembled above
        model_id="my_substation_A",
        run_name="peak_hour_experiment",
    )

    # Load or create your dataset
    dataset: VersionedTimeSeriesDataset = create_synthetic_forecasting_dataset()

    # Train
    workflow.train(data=dataset)

    # Persist to disk
    storage = LocalModelStorage(base_path=Path("./models"))
    storage.save(workflow.model, model_id="my_substation_A")

    # Predict
    forecast = workflow.predict(data=dataset)

.. note:: [VISUALIZATION: Side-by-side plot of actual load vs. probabilistic forecast bands produced by the custom pipeline above]

The workflow separates orchestration concerns (storage, callbacks, run naming) from modelling concerns (transforms, forecaster). This means you can reuse the same ``ForecastingModel`` across different workflows — for example, a ``CustomForecastingWorkflow`` in production and a backtesting workflow during evaluation.

Custom Data Preparation
------------------------

Data preparation happens *before* the pipeline sees any data. The typical pattern is to produce a ``TimeSeriesDataset`` (or ``VersionedTimeSeriesDataset``) from whatever raw source you have — a database query, a CSV file, or a REST API — and pass it to the workflow.

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    def load_from_database(connection, substation_id: str) -> TimeSeriesDataset:
        query = f"""
            SELECT timestamp, load_mw, temperature_c, wind_speed_ms
            FROM measurements
            WHERE substation_id = '{substation_id}'
            ORDER BY timestamp
        """
        df = pd.read_sql(query, connection, index_col="timestamp", parse_dates=True)
        df.index = df.index.tz_localize("Europe/Amsterdam")
        return TimeSeriesDataset(data=df)

    raw = load_from_database(conn, substation_id="A123")

.. note::

    OpenSTEF expects a timezone-aware ``DatetimeIndex``. If your source data is in UTC, convert it to the local grid timezone before constructing the dataset — this ensures holiday and peak-hour features resolve correctly.

For recurring data ingestion, keep the preparation logic in a dedicated function or class and keep it separate from the pipeline. The pipeline's preprocessing transforms should be stateless with respect to data *sourcing* — they only reshape and enrich data that is already loaded.

Putting It All Together
------------------------

The full customization pattern follows this sequence:

1. **Prepare data** — load from your source, align the index, add any raw columns the transforms will need (e.g. weather variables).
2. **Define preprocessing transforms** — combine built-in transforms with any custom ones.
3. **Choose a forecaster** — pick from the built-in forecasters or wrap your own estimator.
4. **Define postprocessing transforms** — apply calibration and confidence intervals.
5. **Assemble a** ``ForecastingModel`` — wire the three stages together.
6. **Wrap in a workflow** — use ``CustomForecastingWorkflow`` for orchestration and storage.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_2.mmd

Once your custom pipeline is working, evaluate it rigorously before deploying. See :doc:`backtesting` for how to run a walk-forward evaluation on historical data using the same ``ForecastingModel`` you assembled here.