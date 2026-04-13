Advanced Customization
======================

Once you are comfortable with the basics covered in :doc:`first_forecast`, OpenSTEF exposes
several well-defined extension points that let you adapt the library to your own data
sources, feature sets, and workflow requirements. This page walks through the three main
areas of customization: data preparation, feature engineering, and pipeline composition.

.. note::

   This page assumes familiarity with the core forecasting workflow. If you have not yet
   produced your first forecast, start with :doc:`first_forecast` before continuing here.

.. contents:: On this page
   :local:
   :depth: 2


Custom Data Preparation
-----------------------

OpenSTEF operates on ``TimeSeriesDataset`` objects. Before any model sees your data, you
need to bring it into this format. The library does not prescribe how you load raw data —
that is intentionally left to you — but it does provide a clean boundary at which your
data enters the pipeline.

The minimal requirement is a pandas ``DataFrame`` with a ``DatetimeIndex`` and at least
one target column (typically ``"load"``). Wrap it in a ``TimeSeriesDataset`` to make it
compatible with all downstream components:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Load from any source — database, CSV, API, etc.
   raw_df = pd.read_csv("my_measurements.csv", index_col="timestamp", parse_dates=True)

   # Ensure the index is timezone-aware
   raw_df.index = raw_df.index.tz_localize("UTC")

   dataset = TimeSeriesDataset(
       data=raw_df,
       sample_interval=timedelta(minutes=15),
   )

If your data arrives in multiple versions (e.g., successive SCADA revisions of the same
measurement), use ``VersionedTimeSeriesDataset`` instead. This preserves the
``available_at`` dimension that OpenSTEF uses to prevent data leakage during backtesting.
See :doc:`backtesting` for details on why this matters.

When your raw data requires cleaning before it reaches the model, write the logic as a
reusable function or class rather than embedding it in a notebook. This makes it easy to
apply the same cleaning consistently across training and inference:

.. code-block:: python

   def load_and_clean(path: str, sample_interval: timedelta) -> TimeSeriesDataset:
       df = pd.read_csv(path, index_col="timestamp", parse_dates=True)
       df.index = df.index.tz_localize("UTC")

       # Remove obvious sensor errors
       df = df[df["load"] > 0]
       df = df[df["load"] < df["load"].quantile(0.999)]

       # Resample to a uniform grid, forward-filling short gaps
       df = df.resample(sample_interval).mean().ffill(limit=4)

       return TimeSeriesDataset(data=df, sample_interval=sample_interval)


Custom Feature Engineering
--------------------------

Feature engineering in OpenSTEF is expressed through the ``Transform`` protocol and
composed into ``TransformPipeline`` objects. Every transform implements two methods:
``fit(data)`` to learn parameters from training data, and ``transform(data)`` to apply
them. Stateless transforms (those that need no fitting) simply leave ``fit`` as a no-op
and return ``True`` from the ``is_fitted`` property.

Writing a custom transform
^^^^^^^^^^^^^^^^^^^^^^^^^^

Subclass ``Transform`` from ``openstef_core.transforms`` and implement the abstract
interface:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import Transform

   class CalendarFeatures(Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Adds hour-of-day, day-of-week, and month features to the dataset."""

       @property
       def is_fitted(self) -> bool:
           return True  # Stateless — no parameters to learn

       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # Nothing to fit

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           df["hour"] = df.index.hour
           df["day_of_week"] = df.index.dayofweek
           df["month"] = df.index.month
           return TimeSeriesDataset(
               data=df,
               sample_interval=data.sample_interval,
               available_at_column=data.available_at_column,
           )

For transforms that *do* need to learn from data — for example, a scaler that computes
mean and standard deviation on the training set — store the fitted parameters as instance
attributes and guard ``transform`` with a check on ``is_fitted``:

.. code-block:: python

   from openstef_core.exceptions import NotFittedError

   class LoadNormalizer(Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Normalizes the load column using training-set statistics."""

       _mean: float | None = None
       _std: float | None = None

       @property
       def is_fitted(self) -> bool:
           return self._mean is not None and self._std is not None

       def fit(self, data: TimeSeriesDataset) -> None:
           self._mean = float(data.data["load"].mean())
           self._std = float(data.data["load"].std())

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           if not self.is_fitted:
               raise NotFittedError("LoadNormalizer has not been fitted yet.")
           df = data.data.copy()
           df["load"] = (df["load"] - self._mean) / self._std
           return TimeSeriesDataset(
               data=df,
               sample_interval=data.sample_interval,
               available_at_column=data.available_at_column,
           )

Using built-in transforms
^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF ships with several ready-made transforms. The ``VersionedLagsAdder`` is
particularly useful for creating lag features without data leakage:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms import VersionedLagsAdder

   lag_transform = VersionedLagsAdder(
       feature="load",
       lags=[timedelta(hours=-1), timedelta(hours=-2), timedelta(hours=-24)],
   )

.. note::

   When using lag-based features, set ``cutoff_history`` on your ``ForecastingModel``
   to match the longest lag. For example, a 24-hour lag requires
   ``cutoff_history=timedelta(hours=24)`` so that rows with incomplete lag history are
   excluded from training. See the ``ForecastingModel`` API reference for details.

Composing a pipeline
^^^^^^^^^^^^^^^^^^^^

Chain multiple transforms into a ``TransformPipeline``. The pipeline fits each transform
sequentially on the *output* of the previous one, so the order matters:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline

   preprocessing = TransformPipeline(
       transforms=[
           CalendarFeatures(),
           VersionedLagsAdder(
               feature="load",
               lags=[timedelta(hours=-1), timedelta(hours=-24)],
           ),
           LoadNormalizer(),
       ]
   )

   # Fit on training data, then reuse the fitted pipeline for inference
   preprocessing.fit(training_dataset)
   transformed = preprocessing.transform(new_dataset)

   # Or fit and transform in one step
   transformed = preprocessing.fit_transform(training_dataset)


Custom Pipeline Workflows
-------------------------

The highest-level extension point is the workflow layer. OpenSTEF provides
``ForecastingModel`` as the standard single-forecaster pipeline
(preprocessing → forecaster → postprocessing), and ``CustomForecastingWorkflow`` for
production systems that need model persistence, callbacks, and lifecycle management.

Assembling a ForecastingModel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ForecastingModel`` wires together your preprocessing pipeline, a forecaster, and an
optional postprocessing pipeline. You supply the components; the model handles the
orchestration:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
       ConstantMedianForecasterConfig,
   )
   from openstef_core.transforms import TransformPipeline

   forecaster_config = ConstantMedianForecasterConfig(
       horizons=[timedelta(hours=h) for h in range(1, 49)],
   )
   forecaster = ConstantMedianForecaster(config=forecaster_config)

   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=TransformPipeline(
           transforms=[CalendarFeatures(), LoadNormalizer()]
       ),
       cutoff_history=timedelta(days=1),  # Exclude first day (incomplete lags)
   )

   fit_result = model.fit(training_dataset)
   forecasts = model.predict(new_dataset)

Implementing a custom forecaster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the built-in forecasters do not fit your needs, you can implement your own by
subclassing ``Forecaster`` and providing ``fit`` and ``predict`` methods. The forecaster
operates on preprocessed data and is responsible only for the statistical modelling step
— data cleaning and feature engineering belong in the preprocessing pipeline:

.. code-block:: python

   from openstef_models.models.forecasting.base import Forecaster, ForecasterConfig
   from openstef_core.datasets import ForecastInputDataset, ForecastDataset

   class MyForecasterConfig(ForecasterConfig):
       window_size: int = 48  # Number of historical steps to use

   class MyForecaster(Forecaster[MyForecasterConfig]):
       """Rolling-window mean forecaster as a minimal custom example."""

       def fit(self, data: ForecastInputDataset, **kwargs) -> None:
           # Store any parameters learned from training data
           self._fitted = True

       def _predict(self, data: ForecastInputDataset) -> ForecastDataset:
           # Implement your prediction logic here
           # Return a ForecastDataset with the required quantile columns
           ...

Using workflow callbacks
^^^^^^^^^^^^^^^^^^^^^^^^

For production deployments, ``CustomForecastingWorkflow`` adds lifecycle callbacks that
let you hook into model loading, saving, and prediction events without modifying the core
logic. Subclass ``ForecastCallback`` and override only the events you care about:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.mixins.callbacks import ForecastCallback, WorkflowContext
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset

   class LoggingCallback(ForecastCallback):
       """Logs forecast requests and results to a monitoring system."""

       def on_predict_start(
           self,
           workflow: WorkflowContext,
           data: TimeSeriesDataset,
       ) -> None:
           print(f"Forecast requested for {len(data.data)} rows")

       def on_predict_end(
           self,
           workflow: WorkflowContext,
           result: ForecastDataset,
       ) -> None:
           print(f"Forecast produced {len(result.data)} predictions")

   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[LoggingCallback()],
   )

   forecasts = workflow.predict(new_dataset)

.. note:: [DIAGRAM: Extension point hierarchy — Transform → TransformPipeline → ForecastingModel → CustomForecastingWorkflow, showing where each customization layer sits]


Patterns and Best Practices
----------------------------

A few patterns that emerge consistently when extending OpenSTEF:

- **Keep transforms stateless when possible.** Stateless transforms are simpler to
  serialize, test, and reuse across training and inference. Reserve stateful transforms
  for cases where the transform genuinely needs to learn from data (e.g., scalers,
  encoders).

- **Match ``cutoff_history`` to your longest lag.** If your preprocessing creates a
  24-hour lag feature, the first 24 hours of any dataset will contain NaN values. Setting
  ``cutoff_history=timedelta(hours=24)`` on ``ForecastingModel`` ensures these rows are
  excluded from training automatically.

- **Separate data loading from feature engineering.** Write your data loading logic as
  plain functions that return ``TimeSeriesDataset`` objects, and express all feature
  engineering as ``Transform`` subclasses. This makes each piece independently testable.

- **Use ``fit_transform`` during training, ``transform`` during inference.** Calling
  ``fit`` on a pipeline that was already fitted on training data will overwrite the
  learned parameters. Always call only ``transform`` when processing new data at
  inference time.

- **Test transforms in isolation.** Because each transform has a clean
  ``fit`` / ``transform`` interface, you can unit-test them independently before
  assembling them into a pipeline.


Next Steps
----------

- :doc:`backtesting` — Once you have a custom pipeline, use backtesting to measure how
  much your customizations improve forecast accuracy compared to a baseline.
- :doc:`quickstart` — Review the minimal working example if you want a reference point
  for what a default (non-customized) pipeline looks like.