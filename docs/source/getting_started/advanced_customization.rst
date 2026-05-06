Advanced Customization
======================

This page covers the main extension points in OpenSTEF for power users who need to go beyond the defaults: writing custom transforms, assembling bespoke feature pipelines, and composing custom forecasting workflows. If you haven't yet run a basic forecast, start with :doc:`first_forecast` first.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Custom Transforms
-----------------

Every preprocessing and postprocessing step in OpenSTEF is a ``TimeSeriesTransform``. A transform is a small, composable unit with three responsibilities: fitting any learned state, applying the transformation, and reporting whether it has been fitted. Implementing your own transform means subclassing ``TimeSeriesTransform`` (and ``BaseConfig`` for Pydantic-based configuration) and overriding ``fit``, ``transform``, and the ``is_fitted`` property.

The example below adds a rolling-mean smoothing feature to a ``TimeSeriesDataset``:

.. code-block:: python

    from datetime import timedelta
    from typing import override

    import pandas as pd
    from pydantic import Field

    from openstef_core.base_model import BaseConfig
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform


    class RollingMeanAdder(BaseConfig, TimeSeriesTransform):
        """Adds a rolling-mean feature for a given column and window."""

        feature: str = Field(description="Column to smooth.")
        window: timedelta = Field(
            default=timedelta(hours=24),
            description="Rolling window size.",
        )

        @property
        @override
        def is_fitted(self) -> bool:
            return True  # Stateless — no learned parameters

        @override
        def fit(self, data: TimeSeriesDataset) -> None:
            pass  # Nothing to learn

        @override
        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            df = data.data.copy()
            periods = int(self.window / data.resolution)
            col_name = f"{self.feature}_rolling_{periods}"
            df[col_name] = df[self.feature].rolling(periods, min_periods=1).mean()
            return TimeSeriesDataset(data=df)

A few conventions to keep in mind:

- **Stateless transforms** (no learned parameters) should return ``True`` from ``is_fitted`` unconditionally and leave ``fit`` as a no-op.
- **Stateful transforms** (e.g., a scaler that learns mean and variance) must store their learned state as Pydantic fields and return ``False`` from ``is_fitted`` until ``fit`` has been called.
- The ``transform`` method must return a new dataset object — do not mutate the input in place.

Built-in transforms such as ``HolidayFeatureAdder``, ``LagsAdder``, ``WindPowerFeatureAdder``, and ``DimensionalityReducer`` follow the same contract and are good references when building your own.

.. code-block:: python

    from datetime import timedelta
    from pydantic_extra_types.country import CountryAlpha2

    from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
    from openstef_models.transforms.time_domain.lags_adder import LagsAdder
    from openstef_models.transforms.energy_domain.wind_power_feature_adder import WindPowerFeatureAdder

    holiday_transform = HolidayFeatureAdder(country=CountryAlpha2("NL"))

    lag_transform = LagsAdder(
        feature="load",
        lags=[timedelta(hours=-1), timedelta(hours=-24), timedelta(hours=-168)],
    )

    wind_transform = WindPowerFeatureAdder()

Assembling a Custom Feature Pipeline
-------------------------------------

Individual transforms are composed into a ``TransformPipeline``. The pipeline applies each transform in sequence: during ``fit_transform`` every transform is fitted on the running output of the previous one, and during ``transform`` the fitted transforms are applied in the same order.

.. code-block:: python

    from openstef_core.transforms import TransformPipeline
    from openstef_core.datasets import TimeSeriesDataset

    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            HolidayFeatureAdder(country=CountryAlpha2("NL")),
            LagsAdder(
                feature="load",
                lags=[timedelta(hours=-1), timedelta(hours=-24), timedelta(hours=-168)],
            ),
            RollingMeanAdder(feature="load", window=timedelta(hours=48)),
        ]
    )

    # Fit and transform training data in one step
    train_features = preprocessing.fit_transform(data=train_dataset)

    # Transform held-out data with the already-fitted pipeline
    val_features = preprocessing.transform(data=val_dataset)

The pipeline is generic over the dataset type (``TransformPipeline[TimeSeriesDataset]`` vs ``TransformPipeline[EnergyComponentDataset]``), so the same pattern applies to postprocessing steps that operate on model outputs.

.. note::

    Order matters. Lag transforms must come *after* any imputation or resampling step, because they reference specific column names that must already exist in the dataset.

Custom Forecasting Workflows
-----------------------------

A ``ForecastingModel`` bundles a preprocessing pipeline, a core estimator, and a postprocessing pipeline into a single trainable and serialisable object. You pass your custom ``TransformPipeline`` instances directly to the constructor:

.. code-block:: python

    from openstef_models.forecasting_model import ForecastingModel
    from openstef_models.estimators.constant_median import ConstantMedianForecaster

    model = ForecastingModel(
        preprocessing=preprocessing,          # your custom TransformPipeline
        estimator=ConstantMedianForecaster(),  # swap in any compatible estimator
        # postprocessing defaults to an empty pipeline if omitted
    )

For higher-level orchestration — handling model versioning, storage, and the train/predict loop — wrap the model in a ``CustomForecastingWorkflow``:

.. code-block:: python

    from datetime import timedelta
    from pathlib import Path

    import numpy as np
    import pandas as pd

    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_core.testing import generate_time_series
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.storage.local_model_storage import LocalModelStorage

    # --- Synthetic data ---
    raw = generate_time_series(n_periods=8760, resolution=timedelta(hours=1))
    dataset = VersionedTimeSeriesDataset.from_dataframe(raw)

    # --- Storage backend ---
    storage = LocalModelStorage(base_path=Path("./models"))

    # --- Workflow ---
    workflow = CustomForecastingWorkflow(
        model=model,
        model_storage=storage,
        forecast_horizon=timedelta(hours=24),
    )

    workflow.train(data=dataset)
    forecast = workflow.predict(data=dataset)

.. note:: [VISUALIZATION: Example forecast plot showing predicted vs. actual load over a 24-hour horizon, produced by ForecastTimeSeriesPlotter.]

The workflow handles serialisation automatically: after ``train`` completes, the fitted model (including all pipeline state) is written to the storage backend and can be reloaded in a separate process.

Using the Preset as a Starting Point
--------------------------------------

If you want a fully configured workflow without assembling every piece by hand, ``create_forecasting_workflow`` from ``openstef_models.presets.forecasting_workflow`` returns a ``CustomForecastingWorkflow`` built from a ``ForecastingWorkflowConfig``. This is a convenient baseline to diff against when debugging a custom setup:

.. code-block:: python

    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )

    config = ForecastingWorkflowConfig(
        location=LocationConfig(name="Amsterdam", country="NL"),
        forecast_horizon=timedelta(hours=48),
    )

    workflow = create_forecasting_workflow(config)

Inspect ``workflow.model.preprocessing.transforms`` to see which transforms the preset installs, then copy and modify that list as the starting point for your own pipeline.

Patterns and Tips
------------------

- **Reuse fitted pipelines.** Call ``fit_transform`` once on training data, then call ``transform`` on validation and test data. Never refit on held-out data.
- **Keep transforms small.** A transform that does one thing is easier to test and reorder. Compose complexity in the pipeline, not inside a single transform.
- **Validate column names early.** Use ``validate_required_columns`` (from ``openstef_core``) at the top of ``transform`` to surface missing columns with a clear error rather than a cryptic ``KeyError`` later.
- **Stateful transforms and serialisation.** Because ``ForecastingModel`` is Pydantic-based, all transform state must be stored in Pydantic fields. Avoid storing learned state in plain Python attributes — it will not survive serialisation.
- **Dimensionality reduction.** When your feature set grows large, add a ``DimensionalityReducer`` (from ``openstef_models.transforms.general``) near the end of the preprocessing pipeline to keep training times manageable.

Next Steps
----------

- :doc:`backtesting` — evaluate your custom pipeline on historical data before deploying it.
- :doc:`quickstart` — a minimal end-to-end example if you want a clean reference to compare against.
- :doc:`first_forecast` — step-by-step walkthrough of the core concepts used on this page.