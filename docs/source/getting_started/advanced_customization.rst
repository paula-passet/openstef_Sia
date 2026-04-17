Advanced Customization
======================

OpenSTEF is designed to be extended. While the built-in presets cover common forecasting scenarios out of the box, most production deployments eventually need to tailor some part of the pipeline — whether that means adding domain-specific features, swapping out a preprocessing step, or wiring together a completely custom workflow. This page walks through the three main extension points: data preparation, feature engineering, and pipeline composition.

If you haven't run a basic forecast yet, start with :doc:`first_forecast` first. The patterns here build on that foundation.

.. note:: [DIAGRAM: Extension points in the OpenSTEF pipeline — raw data → custom preprocessing (TransformPipeline) → ForecastingModel → custom postprocessing (TransformPipeline) → forecast output]

Custom Feature Engineering
--------------------------

Feature engineering in OpenSTEF is handled by a ``TransformPipeline`` — an ordered list of transform objects applied sequentially to a ``TimeSeriesDataset``. The library ships with transforms covering the most common energy-domain needs: lag features, holiday indicators, weather-derived features, and scaling. You compose them explicitly, which means you can add, remove, or reorder steps without touching any other part of the pipeline.

The built-in transforms live under ``openstef_models.transforms``, organised into subpackages by domain:

- ``openstef_models.transforms.time_domain`` — lag features, calendar features
- ``openstef_models.transforms.weather_domain`` — irradiance, temperature derivatives
- ``openstef_models.transforms.energy_domain`` — load-specific transformations
- ``openstef_models.transforms.general`` — scaling, clipping, general-purpose steps
- ``openstef_models.transforms.validation`` — data quality checks

A typical preprocessing pipeline for a load forecasting task might look like this:

.. code-block:: python

    from openstef_models.transforms.time_domain import LagTransform, HolidayFeatures
    from openstef_models.transforms.general import StandardScaler
    from openstef_models.pipeline import TransformPipeline

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatures(country="NL"),
            LagTransform(lags=[1, 2, 3, 24, 48]),
            StandardScaler(),
        ]
    )

Each transform in the list must implement ``fit``, ``transform``, and ``fit_transform``. The pipeline calls ``fit_transform`` on the training data and ``transform`` only on validation and prediction data, so stateful transforms (like scalers) learn their parameters from training data alone.

Writing a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^

To add a feature that isn't covered by the built-ins, subclass the base transform interface and implement the three methods. The following example adds a rolling mean feature:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    class RollingMeanTransform:
        """Adds a rolling mean of the target column as a feature."""

        def __init__(self, window: int = 24, column: str = "load"):
            self.window = window
            self.column = column

        def fit(self, data: TimeSeriesDataset) -> "RollingMeanTransform":
            # Stateless transform — nothing to learn from training data.
            return self

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            df = data.data.copy()
            df[f"rolling_mean_{self.window}h"] = (
                df[self.column].rolling(window=self.window, min_periods=1).mean()
            )
            return TimeSeriesDataset(data=df)

        def fit_transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            return self.fit(data).transform(data)

Drop it into a ``TransformPipeline`` alongside the built-in transforms:

.. code-block:: python

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatures(country="NL"),
            LagTransform(lags=[1, 2, 3, 24, 48]),
            RollingMeanTransform(window=24),
            StandardScaler(),
        ]
    )

.. note::

    Keep transforms stateless where possible. If a transform does learn state (e.g., mean and variance for scaling), make sure that state is only set inside ``fit`` and never inside ``transform``. This prevents data leakage when the same transform object is reused across train/validation/test splits.

Custom Postprocessing
---------------------

The same ``TransformPipeline`` mechanism applies after prediction. Postprocessing transforms receive a ``ForecastDataset`` and can enforce business constraints, calibrate quantiles, or apply confidence intervals. The built-in postprocessing transforms are in ``openstef_models.transforms.postprocessing``:

.. code-block:: python

    from openstef_models.transforms.postprocessing import (
        QuantileSorter,
        ConfidenceIntervalApplicator,
        IsotonicQuantileCalibrator,
    )
    from openstef_models.pipeline import TransformPipeline

    postprocessing = TransformPipeline(
        transforms=[
            IsotonicQuantileCalibrator(),
            QuantileSorter(),
            ConfidenceIntervalApplicator(
                quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],
                add_quantiles_from_std=False,
            ),
        ]
    )

A custom postprocessing step follows the same interface, but operates on ``ForecastDataset`` instead of ``TimeSeriesDataset``. For example, to clip forecasts to a physical minimum:

.. code-block:: python

    from openstef_core.datasets import ForecastDataset

    class NonNegativeClip:
        """Ensures forecast values never go below zero."""

        def fit(self, data: ForecastDataset) -> "NonNegativeClip":
            return self

        def transform(self, data: ForecastDataset) -> ForecastDataset:
            df = data.data.copy()
            forecast_cols = [c for c in df.columns if "forecast" in c]
            df[forecast_cols] = df[forecast_cols].clip(lower=0.0)
            return ForecastDataset(data=df)

        def fit_transform(self, data: ForecastDataset) -> ForecastDataset:
            return self.fit(data).transform(data)

Assembling a Custom ForecastingModel
-------------------------------------

``ForecastingModel`` is the central object that binds preprocessing, a forecaster, and postprocessing together. You construct it directly when you need full control over each stage:

.. code-block:: python

    from openstef_models.models import ForecastingModel
    from openstef_models.pipeline import TransformPipeline
    from openstef_models.transforms.time_domain import LagTransform, HolidayFeatures
    from openstef_models.transforms.general import StandardScaler
    from openstef_models.transforms.postprocessing import QuantileSorter
    from openstef_models.forecasters import XGBForecaster  # example forecaster

    model = ForecastingModel(
        preprocessing=TransformPipeline(
            transforms=[
                HolidayFeatures(country="NL"),
                LagTransform(lags=[1, 2, 3, 24, 48]),
                RollingMeanTransform(window=24),  # custom transform from above
                StandardScaler(),
            ]
        ),
        forecaster=XGBForecaster(),
        postprocessing=TransformPipeline(
            transforms=[
                NonNegativeClip(),  # custom postprocessing from above
                QuantileSorter(),
            ]
        ),
        target_column="load",
    )

.. note:: [DIAGRAM: ForecastingModel composition — preprocessing TransformPipeline feeds into forecaster, forecaster output feeds into postprocessing TransformPipeline]

Custom Workflow Orchestration
------------------------------

For training and prediction, OpenSTEF provides ``CustomForecastingWorkflow`` — a high-level orchestrator that handles model storage, versioning, and the train/predict lifecycle. You pass it a configured ``ForecastingModel`` and a storage backend:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.storage import LocalModelStorage

    storage = LocalModelStorage(base_path=Path("./models"))

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_substation_forecast",
        run_name="experiment_v1",
    )

    # Train on historical data
    workflow.train(data=train_dataset, model_storage=storage)

    # Generate a forecast
    forecast = workflow.predict(data=forecast_dataset, model_storage=storage)

The workflow separates the *what* (your model configuration) from the *how* (storage, versioning, callbacks). This makes it straightforward to swap storage backends — for example, replacing ``LocalModelStorage`` with an MLflow-backed store — without changing the model definition.

Persisting and Reloading Custom Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because ``ForecastingModel`` is a Pydantic model, serialisation is built in. Custom transforms are included as long as they are importable from your project:

.. code-block:: python

    # Save
    storage.save_model(model=model, model_id="my_substation_forecast")

    # Load in a separate process
    loaded_model = storage.load_model(model_id="my_substation_forecast")
    forecast = loaded_model.predict(data=forecast_dataset)

.. warning::

    Custom transform classes must be importable at load time. If you move or rename a class after saving a model, deserialisation will fail. Keep custom transforms in a stable, versioned module within your project.

Custom Data Preparation
------------------------

Before data reaches the pipeline, it typically needs to be shaped into a ``TimeSeriesDataset`` or ``VersionedTimeSeriesDataset``. These are thin wrappers around a ``pandas.DataFrame`` with a ``DatetimeIndex``. The main requirement is that the index is timezone-aware and the target column is present:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    # Load from any source — database, CSV, API
    raw_df = pd.read_csv("meter_data.csv", index_col="timestamp", parse_dates=True)
    raw_df.index = raw_df.index.tz_localize("Europe/Amsterdam")

    # Rename to match the expected target column name
    raw_df = raw_df.rename(columns={"measured_load_mw": "load"})

    dataset = TimeSeriesDataset(data=raw_df)

If your source data has gaps or outliers, add a validation transform at the start of your preprocessing pipeline (from ``openstef_models.transforms.validation``) rather than cleaning data outside the pipeline. This keeps the cleaning logic reproducible and applied consistently during both training and inference.

For forecasting, you need a ``ForecastDataset`` that contains the feature columns but not the target (since that is what you are predicting). The workflow handles this split automatically when you call ``workflow.predict``, but if you are calling the model directly:

.. code-block:: python

    from openstef_core.datasets import ForecastDataset

    # Future timestamps with weather and calendar features, no target column
    future_df = pd.DataFrame(
        index=pd.date_range("2024-01-15", periods=48, freq="1h", tz="Europe/Amsterdam")
    )
    forecast_input = ForecastDataset(data=future_df)

    forecast = model.predict(data=forecast_input)

Putting It All Together
------------------------

The following sketch combines all three extension points into a single, self-contained setup:

.. code-block:: python

    from pathlib import Path
    from openstef_models.models import ForecastingModel
    from openstef_models.pipeline import TransformPipeline
    from openstef_models.transforms.time_domain import LagTransform, HolidayFeatures
    from openstef_models.transforms.general import StandardScaler
    from openstef_models.transforms.postprocessing import QuantileSorter, ConfidenceIntervalApplicator
    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.storage import LocalModelStorage
    from openstef_core.datasets import TimeSeriesDataset
    import pandas as pd

    # --- 1. Prepare data ---
    raw_df = pd.read_csv("meter_data.csv", index_col="timestamp", parse_dates=True)
    raw_df.index = raw_df.index.tz_localize("Europe/Amsterdam")
    raw_df = raw_df.rename(columns={"measured_load_mw": "load"})
    dataset = TimeSeriesDataset(data=raw_df)

    # --- 2. Build model with custom transforms ---
    model = ForecastingModel(
        preprocessing=TransformPipeline(
            transforms=[
                HolidayFeatures(country="NL"),
                LagTransform(lags=[1, 2, 3, 24, 48]),
                RollingMeanTransform(window=24),
                StandardScaler(),
            ]
        ),
        forecaster=XGBForecaster(),
        postprocessing=TransformPipeline(
            transforms=[
                NonNegativeClip(),
                QuantileSorter(),
                ConfidenceIntervalApplicator(quantiles=[0.1, 0.5, 0.9]),
            ]
        ),
        target_column="load",
    )

    # --- 3. Train and forecast via workflow ---
    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="substation_a",
        run_name="custom_pipeline_v1",
    )
    storage = LocalModelStorage(base_path=Path("./models"))
    workflow.train(data=dataset, model_storage=storage)

.. note:: [VISUALIZATION: Side-by-side plot of forecast with and without the custom RollingMeanTransform, showing improved smoothness]

Next Steps
----------

- :doc:`backtesting` — evaluate your custom pipeline on historical data before deploying it
- :doc:`first_forecast` — revisit the end-to-end walkthrough if any step here was unclear
- :doc:`quickstart` — a minimal working example if you want a clean starting point