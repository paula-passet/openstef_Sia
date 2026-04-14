Advanced Customization
======================

OpenSTEF is designed as an extensible library. While the built-in workflows cover the most common short-term energy forecasting scenarios, the library exposes clean extension points so you can adapt it to your own data, domain knowledge, and operational requirements. This page covers the three main customization patterns: writing custom transforms for data preparation and feature engineering, assembling custom pipeline workflows, and hooking into the workflow lifecycle with callbacks.

If you haven't yet run a basic forecast, start with :doc:`first_forecast` before reading this page. For comparing custom models against baselines, see :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Custom Transforms
-----------------

Every preprocessing and postprocessing step in OpenSTEF is a ``TimeSeriesTransform``. Transforms are the primary extension point for injecting domain knowledge — whether that means adding wind-power features, clipping outliers, or encoding calendar effects specific to your grid.

A transform subclasses ``TimeSeriesTransform`` (from ``openstef_models``) and implements two methods:

- ``transform(data: TimeSeriesDataset) -> TimeSeriesDataset`` — the core logic, always required.
- ``fit(data: TimeSeriesDataset) -> None`` — optional; override when the transform must learn parameters from training data (e.g. scaling factors, observed min/max values).
- ``features_added() -> list[str]`` — declare which new columns your transform introduces.

Stateless transforms (those that don't learn from data) are fitted by default and require no ``fit`` override. The base class ``is_fitted`` property returns ``True`` automatically for stateless transforms.

The following example adds a simple "solar elevation proxy" feature from a timestamp column:

.. code-block:: python

    import numpy as np
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.base import TimeSeriesTransform


    class SolarElevationTransform(TimeSeriesTransform):
        """Add a rough solar elevation proxy (sine of hour angle) as a feature."""

        def features_added(self) -> list[str]:
            return ["solar_elevation_proxy"]

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            df = data.data.copy()
            # Hour of day mapped to [0, 2π]
            hour_angle = 2 * np.pi * df.index.hour / 24
            df["solar_elevation_proxy"] = np.sin(hour_angle)
            return TimeSeriesDataset(df, data.sample_interval)

Because this transform has no learnable parameters, it is stateless and the default ``is_fitted = True`` applies. No ``fit`` override is needed.

For transforms that *do* learn from data — for example, a scaler that records the training-set mean and standard deviation — override ``fit`` and track a flag:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.base import TimeSeriesTransform


    class MeanNormalizer(TimeSeriesTransform):
        """Normalize a target column by its training-set mean."""

        def __init__(self, column: str):
            self.column = column
            self._mean: float | None = None

        @property
        def is_fitted(self) -> bool:
            return self._mean is not None

        def features_added(self) -> list[str]:
            return []

        def fit(self, data: TimeSeriesDataset) -> None:
            self._mean = float(data.data[self.column].mean())

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            if not self.is_fitted:
                raise RuntimeError("Call fit() before transform().")
            df = data.data.copy()
            df[self.column] = df[self.column] / self._mean
            return TimeSeriesDataset(df, data.sample_interval)

.. note::

   OpenSTEF ships several ready-made transforms under ``openstef_models.transforms``, including ``Clipper``, ``Scaler``, ``Imputer``, ``NaNDropper``, ``LagsAdder``, and domain-specific ones like ``WindPowerFeatureAdder``. Check these before writing your own — they are composable and cover most common needs.

Composing Transforms into a Pipeline
-------------------------------------

Individual transforms are assembled into a ``TransformPipeline``, which applies them in sequence. Each transform receives the output of the previous one, and ``fit_transform`` fits each step on the intermediate result of the steps before it.

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.pipeline import TransformPipeline
    from openstef_models.transforms.general.clipper import Clipper
    from openstef_models.transforms.general.imputer import Imputer
    from openstef_core.selection import Exclude

    # Combine built-in and custom transforms
    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            SolarElevationTransform(),          # custom transform defined above
            Clipper(selection=Exclude("load")), # clip all features except target
            Imputer(
                selection=Exclude("load"),
                imputation_strategy="mean",
            ),
        ]
    )

    # Fit on training data and transform in one step
    processed_train = preprocessing.fit_transform(data=train_dataset)

    # Transform new data using the fitted parameters (no re-fitting)
    processed_predict = preprocessing.transform(data=predict_dataset)

An empty ``TransformPipeline`` is a no-op, so you can start with an empty list and add transforms incrementally.

Custom Pipeline Workflows
--------------------------

The ``ForecastingModel`` class wires together a preprocessing pipeline, a forecaster, and a postprocessing pipeline into a single trainable and predictable unit. You construct one explicitly when the built-in workflow configurations don't match your requirements.

.. code-block:: python

    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.transforms.pipeline import TransformPipeline
    from openstef_models.transforms.general.imputer import Imputer
    from openstef_models.transforms.general.nan_dropper import NaNDropper
    from openstef_models.transforms.general.quantile_sorter import QuantileSorter
    from openstef_models.forecasters.lgbm import LGBMForecaster
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.selection import Exclude

    QUANTILES = [0.05, 0.25, 0.50, 0.75, 0.95]
    HORIZONS = [0.25, 1.0, 4.0, 24.0]  # hours ahead

    model = ForecastingModel(
        preprocessing=TransformPipeline[TimeSeriesDataset](
            transforms=[
                SolarElevationTransform(),      # custom feature
                Imputer(
                    selection=Exclude("load"),
                    imputation_strategy="mean",
                ),
                NaNDropper(selection=Exclude("load")),
            ]
        ),
        forecaster=LGBMForecaster(
            quantiles=QUANTILES,
            horizons=HORIZONS,
        ),
        postprocessing=TransformPipeline(
            transforms=[QuantileSorter()]
        ),
        target_column="load",
    )

    fit_result = model.fit(data=train_dataset, data_val=val_dataset)
    forecast = model.predict(data=predict_dataset)

The ``ForecastingModel`` is then wrapped in a ``CustomForecastingWorkflow`` to gain callback support, model identity tracking, and optional MLflow integration:

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my-solar-site-001",
        run_name="solar-lgbm-v1",
    )

    workflow.fit(data=train_dataset)
    forecast_dataset = workflow.predict(data=predict_dataset)

Workflow Callbacks
------------------

Callbacks let you inject logic at four points in the workflow lifecycle without modifying the workflow or model code:

- ``on_fit_start`` — before training begins
- ``on_fit_end`` — after training completes
- ``on_predict_start`` — before prediction
- ``on_predict_end`` — after prediction

Subclass ``ForecastingCallback`` and override only the hooks you need. All methods have default no-op implementations.

.. code-block:: python

    import logging
    from openstef_models.workflows.callbacks import ForecastingCallback
    from openstef_models.mixins.callbacks import WorkflowContext
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.models.forecasting_model import ModelFitResult
    from openstef_core.datasets.validated_datasets import ForecastDataset

    logger = logging.getLogger(__name__)


    class MetricsLoggingCallback(ForecastingCallback):
        """Log training metrics and forecast statistics after each stage."""

        def on_fit_end(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            result: ModelFitResult,
        ) -> None:
            logger.info(
                "Training complete for model '%s'. Metrics: %s",
                context.workflow.model_id,
                result.metrics,
            )

        def on_predict_end(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            data: TimeSeriesDataset,
            result: ForecastDataset,
        ) -> None:
            logger.info(
                "Forecast generated: %d rows, horizon range %s–%s",
                len(result.data),
                result.data.index.min(),
                result.data.index.max(),
            )

Attach one or more callbacks when constructing the workflow:

.. code-block:: python

    from openstef_models.workflows.callbacks.data_save import DataSaveCallback

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my-solar-site-001",
        run_name="solar-lgbm-v1",
        callbacks=[
            MetricsLoggingCallback(),
            DataSaveCallback(output_dir="/tmp/openstef_debug"),  # built-in: saves parquet snapshots
        ],
    )

The built-in ``DataSaveCallback`` is particularly useful during development — it writes intermediate datasets to Parquet files at each lifecycle stage, letting you inspect exactly what data the model sees.

Putting It All Together
------------------------

A complete customization typically follows this pattern:

1. **Define custom transforms** for any domain-specific feature engineering.
2. **Assemble a preprocessing pipeline** combining your transforms with built-in ones (clipping, imputation, lag generation).
3. **Choose a forecaster** (``LGBMForecaster``, ``GBLinearForecaster``, ``MedianForecaster``, etc.) and configure quantiles and horizons.
4. **Define a postprocessing pipeline** (at minimum, a ``QuantileSorter`` to enforce monotonic quantiles).
5. **Wrap everything in a** ``ForecastingModel`` and then a ``CustomForecastingWorkflow``.
6. **Attach callbacks** for logging, persistence, or monitoring.

.. code-block:: python

    workflow = CustomForecastingWorkflow(
        model=ForecastingModel(
            preprocessing=TransformPipeline[TimeSeriesDataset](
                transforms=[
                    SolarElevationTransform(),
                    Imputer(selection=Exclude("load"), imputation_strategy="mean"),
                    NaNDropper(selection=Exclude("load")),
                ]
            ),
            forecaster=LGBMForecaster(quantiles=QUANTILES, horizons=HORIZONS),
            postprocessing=TransformPipeline(transforms=[QuantileSorter()]),
            target_column="load",
        ),
        model_id="solar-site-001",
        run_name="custom-pipeline-v1",
        callbacks=[MetricsLoggingCallback()],
    )

    workflow.fit(data=train_dataset, data_val=val_dataset)
    forecast = workflow.predict(data=predict_dataset)

.. note::

   For ensemble workflows (multiple base models combined), OpenSTEF provides ``EnsembleForecastingWorkflow``, which supports per-forecaster preprocessing pipelines on top of a shared common preprocessing stage. The same ``TimeSeriesTransform`` interface applies throughout.

Once you have a custom workflow, use :doc:`backtesting` to evaluate it rigorously against historical data before deploying to production.