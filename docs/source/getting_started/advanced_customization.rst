Advanced Customization
======================

This page covers the main extension points in OpenSTEF for power users who need to go beyond the default configuration: writing custom transforms, composing bespoke preprocessing and postprocessing pipelines, and assembling a fully custom forecasting workflow. If you haven't yet run your first forecast, start with :doc:`first_forecast` before reading this page.

.. note::

   OpenSTEF is a library. Every component described here — transforms, pipelines, workflows — is a Python class you instantiate and compose in your own code. There is no configuration file to edit and no application to extend.

Overview
--------

The library is built around three layered extension points:

- **Transforms** – stateless or stateful data transformations that follow a ``fit`` / ``transform`` pattern.
- **Pipelines** – ordered sequences of transforms, applied as a unit to a ``TimeSeriesDataset``.
- **Workflows** – high-level orchestrators that wire together a model (preprocessing + forecaster + postprocessing) with optional callbacks for storage, logging, and monitoring.

You can customise at any of these layers independently. A common pattern is to keep the built-in workflow but swap in a custom preprocessing pipeline; a more advanced pattern is to compose an entirely custom ``ForecastingModel`` and wrap it in a ``CustomForecastingWorkflow``.

.. mermaid:: diagrams/getting_started/advanced_customization_diagram_1.mmd

Custom Transforms
-----------------

All data transformations in OpenSTEF implement ``TimeSeriesTransform``, an abstract base class from ``openstef_core``. Subclass it to create your own transform:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class PeakNormalizer(TimeSeriesTransform):
       """Normalise every numeric column by the peak value seen during fit."""

       def __init__(self, target_column: str = "load"):
           self.target_column = target_column
           self._peak: float | None = None

       @property
       def is_fitted(self) -> bool:
           return self._peak is not None

       def fit(self, data: TimeSeriesDataset) -> None:
           self._peak = float(data.data[self.target_column].max())

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           if not self.is_fitted:
               raise RuntimeError("Call fit() before transform().")
           normalised = data.data.copy()
           normalised[self.target_column] = normalised[self.target_column] / self._peak
           return TimeSeriesDataset(normalised, data.sample_interval)

       def features_added(self) -> list[str]:
           # This transform modifies an existing column rather than adding new ones.
           return []

A few rules to follow when implementing a transform:

- ``fit`` must be idempotent — calling it twice on the same data should produce the same result.
- ``transform`` must not mutate the input ``TimeSeriesDataset``; always work on a copy.
- ``features_added`` should return the names of any *new* columns your transform appends to the dataset. Return an empty list if you only modify existing columns.
- If your transform is stateless (no parameters learned from data), you can omit ``fit`` entirely — the base class provides a no-op default, and ``is_fitted`` returns ``True`` by default.

Built-in transforms such as ``LagsAdder``, ``HolidayFeatureAdder``, ``WindPowerFeatureAdder``, and ``Clipper`` all follow this same contract and are good references when writing your own.

Custom Preprocessing Pipelines
-------------------------------

A ``TransformPipeline`` is an ordered list of transforms applied sequentially. It exposes the same ``fit`` / ``transform`` / ``fit_transform`` interface as a single transform, making it composable.

.. code-block:: python

   from openstef_core.transforms.pipeline import TransformPipeline
   from openstef_models.transforms.general.clipper import Clipper
   from openstef_models.transforms.energy_domain.wind_power_feature_adder import (
       WindPowerFeatureAdder,
   )

   preprocessing = TransformPipeline(
       transforms=[
           WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
           PeakNormalizer(target_column="load"),   # our custom transform from above
           Clipper(),
       ]
   )

   # During training:
   preprocessing.fit(train_dataset)
   train_ready = preprocessing.transform(train_dataset)

   # During inference (uses parameters learned in fit):
   inference_ready = preprocessing.transform(live_dataset)

The pipeline calls ``fit`` and ``transform`` on each step in order. Steps that are stateless (``is_fitted`` always returns ``True``) are skipped during the ``fit`` phase without error.

.. note::

   ``TransformPipeline`` is generic over the dataset type. Use
   ``TransformPipeline[TimeSeriesDataset]`` for preprocessing and
   ``TransformPipeline[ForecastDataset]`` for postprocessing. The type
   parameter is enforced at runtime when transforms are added.

Custom Postprocessing Pipelines
--------------------------------

Postprocessing transforms operate on a ``ForecastDataset`` — the output of the forecaster — rather than on raw input data. The pattern is identical to preprocessing:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_models.transforms.general.quantile_sorter import QuantileSorter
   from openstef_models.transforms.general.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   postprocessing = TransformPipeline(
       transforms=[
           QuantileSorter(),
           ConfidenceIntervalApplicator(
               quantiles=[0.1, 0.5, 0.9],
               add_quantiles_from_std=False,
           ),
       ]
   )

The built-in ``QuantileSorter`` ensures quantile columns are monotonically ordered, and ``ConfidenceIntervalApplicator`` derives symmetric confidence bounds. You can append your own postprocessing step — for example to clip forecasts to physical limits or to apply a business-rule correction — by subclassing ``TimeSeriesTransform`` and adding it to the pipeline.

Assembling a Custom ForecastingModel
-------------------------------------

``ForecastingModel`` is the central model object. It holds a preprocessing pipeline, a forecaster, and a postprocessing pipeline, and it exposes ``fit`` and ``predict`` methods that route data through all three in the correct order.

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.forecasters.xgb_forecaster import XGBForecaster
   from openstef_models.transforms.general.lags_adder import LagsAdder
   from openstef_models.transforms.general.holiday_feature_adder import HolidayFeatureAdder
   from openstef_models.transforms.general.datetime_features_adder import DatetimeFeaturesAdder
   from openstef_models.transforms.general.nan_dropper import NaNDropper
   from openstef_models.transforms.general.quantile_sorter import QuantileSorter
   from datetime import timedelta

   QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9]
   HORIZONS = [timedelta(hours=h) for h in range(1, 49)]

   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               HolidayFeatureAdder(country_code="NL"),
               DatetimeFeaturesAdder(onehot_encode=False),
               LagsAdder(
                   history_available=timedelta(days=14),
                   horizons=HORIZONS,
                   add_trivial_lags=True,
                   target_column="load",
               ),
               PeakNormalizer(target_column="load"),   # custom transform
               NaNDropper(selection=None),
           ]
       ),
       forecaster=XGBForecaster(quantiles=QUANTILES, horizons=HORIZONS),
       postprocessing=TransformPipeline(
           transforms=[QuantileSorter()]
       ),
       target_column="load",
   )

   model.fit(train_dataset)
   forecast = model.predict(live_dataset)

This is the lowest-level way to use OpenSTEF: you own the full composition and can swap any component independently. The ``forecaster`` argument accepts any object that implements the ``Forecaster`` interface, so you can plug in a custom statistical model, a neural network wrapper, or a third-party estimator as long as it exposes ``fit`` and ``predict``.

Wrapping the Model in a Workflow
---------------------------------

For production use you will typically want model persistence, lifecycle callbacks, and reproducible run tracking. ``CustomForecastingWorkflow`` provides all of this around a ``ForecastingModel``:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage
   from openstef_models.workflows.callbacks.mlflow_storage import MLFlowStorageCallback

   storage = LocalModelStorage(base_path="/models/my_forecast")

   workflow = CustomForecastingWorkflow(
       model=model,           # the ForecastingModel assembled above
       model_id="my_site_xgb",
       run_name="custom_pipeline_v1",
       callbacks=[],          # add MLFlowStorageCallback here for experiment tracking
   )

   # Training
   fit_result = workflow.fit(train_dataset)

   # Inference
   forecast_dataset = workflow.predict(live_dataset)

Callbacks implement the ``ForecastingCallback`` interface and receive ``on_fit_start``, ``on_fit_end``, and ``on_predict_end`` events. You can write a custom callback — for example to publish forecasts to a message bus — by subclassing ``ForecastingCallback`` and overriding the relevant hooks.

.. note::

   The ``DataSaveCallback`` (``openstef_models.workflows.callbacks.data_save``) is a
   useful built-in callback that saves intermediate datasets to Parquet files at each
   workflow stage. It is particularly helpful during development for inspecting what
   data flows through each pipeline step.

Custom Data Preparation
------------------------

Before data reaches the preprocessing pipeline it must be in a ``TimeSeriesDataset`` (or ``VersionedTimeSeriesDataset`` for backtesting). If your raw data comes from a non-standard source you will need to construct this object yourself:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from datetime import timedelta

   # Load from any source — database, CSV, REST API, etc.
   raw_df = pd.read_csv("my_data.csv", index_col="datetime", parse_dates=True)

   # Ensure the index is a timezone-aware DatetimeIndex
   raw_df.index = raw_df.index.tz_localize("Europe/Amsterdam")

   # Rename columns to match what your transforms expect
   raw_df = raw_df.rename(columns={"power_kw": "load", "ws_10m": "wind_speed"})

   # Wrap in a TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=raw_df,
       sample_interval=timedelta(minutes=15),
   )

The ``sample_interval`` tells the library the expected cadence of your data. Transforms such as ``LagsAdder`` use this value to compute correct lag offsets, so it is important to set it accurately.

For backtesting and model-selection scenarios, ``VersionedTimeSeriesDataset`` adds a time-point axis that simulates real-world data availability. See :doc:`backtesting` for details on how to use versioned datasets in evaluation workflows.

.. warning::

   OpenSTEF transforms assume a regular, gap-free time index. If your raw data
   contains missing timestamps, resample or forward-fill before constructing the
   dataset. The built-in ``Imputer`` transform handles missing *values* within
   existing rows, but it does not insert missing rows.

Summary of Extension Points
-----------------------------

The table below summarises where to intervene depending on what you want to customise:

- **Add a new input feature** — implement ``TimeSeriesTransform`` and add it to the preprocessing ``TransformPipeline``.
- **Change how forecasts are post-processed** — add or replace transforms in the postprocessing ``TransformPipeline``.
- **Use a different forecasting algorithm** — implement the ``Forecaster`` interface and pass it as the ``forecaster`` argument to ``ForecastingModel``.
- **React to training or prediction events** — implement ``ForecastingCallback`` and pass it to ``CustomForecastingWorkflow``.
- **Load data from a custom source** — construct a ``TimeSeriesDataset`` from any ``pandas.DataFrame`` before passing it to the workflow.

Next Steps
----------

- :doc:`backtesting` — use ``VersionedTimeSeriesDataset`` and the backtesting workflow to evaluate your custom pipeline against historical data.
- :doc:`quickstart` — a minimal end-to-end example if you want to see a working pipeline before customising it.
- :doc:`first_forecast` — a step-by-step walkthrough of the default pipeline, which provides useful context for understanding which parts to replace.