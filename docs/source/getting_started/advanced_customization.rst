Advanced Customization
======================

OpenSTEF is designed as an extensible library. While the built-in workflows and models cover the most common short-term energy forecasting scenarios out of the box, the library exposes well-defined extension points so you can adapt its behaviour to your specific data, infrastructure, and modelling requirements. This page covers the three main areas where power users typically need to go beyond the defaults: custom data preparation, custom feature engineering, and custom pipeline workflows with callbacks.

If you haven't yet run your first forecast, start with :doc:`first_forecast` before reading this page. For comparing customized models against baselines, see :doc:`backtesting`.

.. note::
   [DIAGRAM: Extension points overview — showing the three layers (data preparation → preprocessing/feature pipeline → workflow/callbacks) and where user code plugs in]

Custom Data Preparation
-----------------------

Before OpenSTEF can train or predict, your raw data must be wrapped in a ``TimeSeriesDataset``. The library does not impose a rigid ingestion format, but it does expect a well-formed dataset at the boundary. Custom data preparation is therefore the first place to extend the library.

A common pattern is to write a thin adapter that fetches data from your source (a database, an API, flat files) and produces a ``TimeSeriesDataset``:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   def load_grid_data(connection_string: str, start: str, end: str) -> TimeSeriesDataset:
       """Fetch metered load and weather features from a database and wrap them
       in a TimeSeriesDataset ready for OpenSTEF."""
       raw = pd.read_sql(
           "SELECT timestamp, load_mw, temp_c, wind_ms FROM grid_measurements "
           "WHERE timestamp BETWEEN %(start)s AND %(end)s",
           con=connection_string,
           params={"start": start, "end": end},
           index_col="timestamp",
           parse_dates=["timestamp"],
       )
       raw.index = pd.DatetimeIndex(raw.index, freq="infer")
       return TimeSeriesDataset(data=raw)

The key points here are:

- The DataFrame index must be a ``DatetimeIndex`` with a consistent frequency.
- Column names are arbitrary, but the column you intend to forecast must be declared as the ``target_column`` when you build the model.
- Additional columns become candidate features; the preprocessing pipeline decides which ones to keep.

For versioned or split datasets (train / validation / test), use ``VersionedTimeSeriesDataset``, which the workflow's ``fit`` method also accepts.

Custom Feature Engineering
--------------------------

Feature engineering in OpenSTEF is expressed through the ``Transform`` interface. Every transform implements two methods — ``fit`` and ``transform`` — and transforms are composed into a ``TransformPipeline`` that applies them sequentially. This is the primary extension point for adding domain-specific features.

Implementing a custom transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Subclass ``Transform`` from ``openstef_core.transforms`` and implement the abstract methods:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import Transform

   class SolarIrradianceAdder(Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Adds a simple clear-sky solar irradiance proxy based on hour-of-day
       and day-of-year, derived from the dataset's DatetimeIndex."""

       _fitted: bool = False

       @property
       def is_fitted(self) -> bool:
           return self._fitted

       def fit(self, data: TimeSeriesDataset) -> None:
           # This transform has no learnable parameters, so fitting is a no-op.
           self._fitted = True

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           idx = data.data.index
           hour_angle = (idx.hour + idx.minute / 60 - 12) * 15  # degrees
           declination = 23.45 * (idx.day_of_year / 365 * 360 - 80).map(
               lambda d: __import__("math").sin(__import__("math").radians(d))
           )
           # Simplified proxy — replace with a proper solar model in production
           irradiance = (hour_angle.map(abs) < 90).astype(float) * (1 - hour_angle.map(abs) / 90)
           new_data = data.data.copy()
           new_data["solar_proxy"] = irradiance.values
           return TimeSeriesDataset(data=new_data)

.. note::

   Transforms that learn parameters from training data (e.g. scalers, lag statistics) must store those parameters during ``fit`` and apply them without re-learning during ``transform``. This ensures that validation and test data are transformed consistently with the training distribution.

Composing transforms into a pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you have one or more custom transforms, compose them with built-in transforms using ``TransformPipeline``:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms import LagsAdder, HolidayFeatureAdder, Scaler
   from openstef_core.feature_selection import Exclude

   preprocessing = TransformPipeline(
       transforms=[
           SolarIrradianceAdder(),                          # your custom transform
           LagsAdder(history_available=48, horizons=[1, 24]),
           HolidayFeatureAdder(country_code="NL"),
           Scaler(selection=Exclude("load_mw"), method="standard"),
       ]
   )

The pipeline calls ``fit_transform`` on each step in sequence during training, passing the intermediate output of one transform as the input to the next. During inference it calls only ``transform``, using the parameters learned at fit time.

Per-forecaster preprocessing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you build an ensemble model, you can attach different preprocessing pipelines to individual forecasters via ``model_specific_preprocessing``. This is useful when one base model (e.g. a linear model) needs feature selection or de-correlation steps that would hurt a tree-based model:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms import Selector
   from openstef_core.feature_selection import FeatureSelection, Exclude

   # Only the linear forecaster gets a column-dropping step
   model_specific_preprocessing = {
       "gblinear": TransformPipeline(
           transforms=[
               Selector(selection=FeatureSelection(exclude={"solar_proxy", "load_mw_lag_P1H"})),
           ]
       ),
   }

Custom Pipeline Workflows
-------------------------

The ``CustomForecastingWorkflow`` class is the top-level orchestrator. It wraps a ``ForecastingModel`` (or ``EnsembleForecastingModel``) and adds lifecycle hooks, optional model persistence, and a clean interface for production systems.

Wiring up a custom workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_core.types import LeadTime, Q

   forecaster = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(h) for h in range(1, 25)],
   )

   model = ForecastingModel(
       forecasters={"lgbm": forecaster},
       preprocessing=preprocessing,          # TransformPipeline from above
       target_column="load_mw",
   )

   workflow = CustomForecastingWorkflow(model=model)

   # Training
   fit_result = workflow.fit(training_dataset)

   # Inference
   forecasts = workflow.predict(live_dataset)

Using callbacks for monitoring and integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks follow the observer pattern and are invoked at four points in the workflow lifecycle: ``on_fit_start``, ``on_fit_end``, ``on_predict_start``, and ``on_predict_end``. Each hook receives a ``WorkflowContext`` carrying the workflow instance and an arbitrary ``data`` dictionary you can use to pass state between hooks.

Implement a callback by subclassing ``PredictorCallback``:

.. code-block:: python

   import logging
   from openstef_models.mixins.callbacks import PredictorCallback, WorkflowContext
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.model_fit_result import ModelFitResult
   from openstef_core.datasets import ForecastDataset

   logger = logging.getLogger(__name__)

   class MetricsCallback(
       PredictorCallback[
           CustomForecastingWorkflow,
           TimeSeriesDataset,
           ModelFitResult,
           ForecastDataset,
       ]
   ):
       """Logs training metrics and forecast statistics to your observability stack."""

       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult,
       ) -> None:
           logger.info("Training complete. Metrics: %s", result)
           # Push to Prometheus, MLflow, etc.

       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           n_rows = len(result.data)
           logger.info("Forecast generated: %d horizon steps.", n_rows)

   # Attach the callback when constructing the workflow
   workflow = CustomForecastingWorkflow(model=model, callbacks=MetricsCallback())

Callbacks are the recommended way to integrate OpenSTEF with external systems (MLflow experiment tracking, Prometheus metrics, alerting pipelines) without modifying library code.

Model persistence
^^^^^^^^^^^^^^^^^

``CustomForecastingWorkflow`` accepts an optional ``model_serializer`` argument that implements the ``ModelSerializer`` interface. Providing one causes the workflow to automatically save the model after fitting and load it before prediction. This is the standard pattern for production deployments where training and inference run in separate processes:

.. code-block:: python

   from openstef_models.mixins.model_serializer import ModelSerializer

   class FileSystemSerializer(ModelSerializer):
       def __init__(self, path: str):
           self.path = path

       def save(self, model, identifier: str) -> None:
           import pickle, os
           os.makedirs(self.path, exist_ok=True)
           with open(f"{self.path}/{identifier}.pkl", "wb") as f:
               pickle.dump(model, f)

       def load(self, identifier: str):
           import pickle
           with open(f"{self.path}/{identifier}.pkl", "rb") as f:
               return pickle.load(f)

   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=MetricsCallback(),
       model_serializer=FileSystemSerializer("/models/grid_a"),
   )

.. note::

   For production use, prefer a serializer backed by object storage (S3, Azure Blob, GCS) rather than the local filesystem. The ``ModelSerializer`` interface is deliberately minimal so you can wrap any storage backend.

Putting It All Together
-----------------------

The three extension points compose cleanly. A fully customized setup looks like this:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_core.types import LeadTime, Q

   # 1. Data preparation — your adapter produces a TimeSeriesDataset
   dataset = load_grid_data(connection_string, start="2024-01-01", end="2024-12-31")

   # 2. Feature engineering — custom + built-in transforms in a pipeline
   preprocessing = TransformPipeline(
       transforms=[
           SolarIrradianceAdder(),
           LagsAdder(history_available=48, horizons=[1, 24]),
           HolidayFeatureAdder(country_code="NL"),
           Scaler(selection=Exclude("load_mw"), method="standard"),
       ]
   )

   # 3. Model and workflow — wired together with a callback
   model = ForecastingModel(
       forecasters={
           "lgbm": LGBMForecaster(
               quantiles=[Q(0.1), Q(0.5), Q(0.9)],
               horizons=[LeadTime(h) for h in range(1, 25)],
           )
       },
       preprocessing=preprocessing,
       target_column="load_mw",
   )

   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=MetricsCallback(),
       model_serializer=FileSystemSerializer("/models/grid_a"),
   )

   workflow.fit(dataset)
   forecasts = workflow.predict(load_grid_data(connection_string, start="2025-01-01", end="2025-01-07"))

Next Steps
----------

- Use :doc:`backtesting` to evaluate whether your customizations improve forecast accuracy compared to the default configuration.
- If you are building a new base forecaster (rather than customizing preprocessing), refer to the API reference for the ``Forecaster`` abstract base class.
- For component splitting workflows (solar/wind decomposition), the same callback and pipeline patterns apply via ``CustomComponentSplitWorkflow`` — see the API reference for details.