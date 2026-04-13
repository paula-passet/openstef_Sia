Advanced Customization
======================

Once you are comfortable with the basics covered in :doc:`first_forecast` and :doc:`quickstart`,
OpenSTEF exposes a set of well-defined extension points that let you adapt the library to
your own data sources, feature sets, and operational requirements. This page walks through
the three main areas where customization is most commonly needed:

- **Custom data preparation** — shaping your raw data into the structures OpenSTEF expects
- **Custom feature engineering** — adding domain-specific transformations to the preprocessing pipeline
- **Custom workflow orchestration** — hooking into the training and prediction lifecycle with callbacks

.. note::

   This page assumes you have OpenSTEF installed and have successfully run a basic forecast.
   If you have not done that yet, start with :doc:`quickstart` and :doc:`first_forecast`.

----

Custom Data Preparation
-----------------------

OpenSTEF operates on ``TimeSeriesDataset`` objects. Before any model sees your data, it
must be wrapped in this structure. The dataset is a thin, typed container around a
``pandas.DataFrame`` with a ``DatetimeIndex``; creating one is straightforward:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   # Load raw data from any source — CSV, database, API, etc.
   raw_df = pd.read_csv("my_measurements.csv", index_col="timestamp", parse_dates=True)
   raw_df = raw_df.sort_index().asfreq("15min")  # ensure regular frequency

   dataset = TimeSeriesDataset(data=raw_df, target_column="load_mw")

The ``target_column`` argument tells OpenSTEF which column holds the quantity you want
to forecast. All other columns are treated as potential features.

**Handling missing values and irregular timestamps**

Real-world energy data often contains gaps. OpenSTEF's built-in preprocessing pipeline
includes imputation steps, but you can also pre-clean your data before wrapping it:

.. code-block:: python

   # Forward-fill short gaps (e.g. up to 1 hour), then drop any remaining NaNs
   raw_df = raw_df.ffill(limit=4).dropna(subset=["load_mw"])

   dataset = TimeSeriesDataset(data=raw_df, target_column="load_mw")

**Versioned datasets**

When you need to track which version of the data was used for a particular training run
(useful for reproducibility and auditing), OpenSTEF provides ``VersionedTimeSeriesDataset``:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   versioned = VersionedTimeSeriesDataset(
       data=raw_df,
       target_column="load_mw",
       version="2024-06-01",
   )

The workflow callbacks (described below) receive either type, so you can introduce
versioning incrementally without changing your model code.

----

Custom Feature Engineering
--------------------------

OpenSTEF's preprocessing layer is built around the ``Transform`` protocol and the
``TransformPipeline`` class. A transform has two methods — ``fit`` and ``transform`` —
and pipelines compose them sequentially. This is the primary extension point for
domain-specific feature engineering.

**Implementing a custom transform**

Subclass the abstract ``Transform`` base class and implement ``fit`` and ``transform``:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import Transform

   class HolidayFlagTransform(Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Adds a boolean 'is_holiday' column based on a user-supplied holiday list."""

       def __init__(self, holidays: list[str]) -> None:
           self._holidays = pd.to_datetime(holidays).normalize()
           self._fitted = False

       @property
       def is_fitted(self) -> bool:
           return self._fitted

       def fit(self, data: TimeSeriesDataset) -> None:
           # No parameters to learn from data — mark as fitted immediately.
           self._fitted = True

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           df["is_holiday"] = df.index.normalize().isin(self._holidays).astype(float)
           return data.copy_with(df)

The ``copy_with`` method returns a new ``TimeSeriesDataset`` with the same metadata but
updated data — always prefer it over mutating the input in place.

**Inserting your transform into a pipeline**

Transforms are composed using ``TransformPipeline``. You can prepend or append your
custom step to any existing pipeline:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline

   holiday_transform = HolidayFlagTransform(
       holidays=["2024-01-01", "2024-12-25", "2025-01-01"]
   )

   # Build a pipeline that runs your transform first, then the rest of your steps
   pipeline = TransformPipeline(transforms=[holiday_transform, ...other_transforms...])

   # Fit on training data and transform
   pipeline.fit(data=train_dataset)
   train_features = pipeline.transform(data=train_dataset)

When you use the high-level ``EnsembleForecastingModel``, the ``preprocessing`` attribute
is itself a ``TransformPipeline``. You can supply your own pipeline at construction time
via the workflow factory functions (see the next section).

**Per-model preprocessing**

The ensemble model supports a ``model_specific_preprocessing`` dictionary that maps
forecaster names to their own ``TransformPipeline``. This is useful when different base
models benefit from different feature representations — for example, a neural network
may need scaled inputs while a gradient-boosted tree does not:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_core.transforms.standard import Scaler

   model_specific_preprocessing = {
       "lgbm": TransformPipeline(transforms=[]),          # no extra scaling
       "xgb":  TransformPipeline(transforms=[Scaler(method="standard")]),
   }

Per-model transforms are fitted on the *already-transformed* output of the common
preprocessing pipeline, not on raw data. Keep this in mind when designing transforms
that depend on column statistics.

----

Custom Workflow Orchestration
------------------------------

OpenSTEF's ``CustomForecastingWorkflow`` and ``CustomComponentSplitWorkflow`` expose a
callback system based on the observer pattern. Callbacks let you inject logic at key
lifecycle events without subclassing or monkey-patching the workflow itself.

**The callback interface**

All callbacks inherit from ``PredictorCallback`` and override the hooks they care about:

.. code-block:: python

   from openstef_models.mixins.callbacks import PredictorCallback, WorkflowContext
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   class MetricsLogger(PredictorCallback):
       """Logs fit and predict events to a monitoring backend."""

       def on_fit_start(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
       ) -> None:
           print(f"[{context.workflow.model_id}] Training started on {len(data.data)} rows.")

       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result,
       ) -> None:
           print(f"[{context.workflow.model_id}] Training complete. Metrics: {result}")

       def on_predict_start(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
       ) -> None:
           print(f"[{context.workflow.model_id}] Prediction started.")

       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
           result,
       ) -> None:
           print(f"[{context.workflow.model_id}] Prediction complete. Shape: {result.data.shape}")

The four hooks are:

- ``on_fit_start`` — called immediately before model training begins
- ``on_fit_end`` — called after training completes successfully, receives the ``ModelFitResult``
- ``on_predict_start`` — called before prediction generation
- ``on_predict_end`` — called after predictions are generated, receives the input data and the forecast

**Attaching callbacks to a workflow**

Pass a list of callback instances when constructing the workflow:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(
       model=my_model,
       model_id="substation_42",
       callbacks=[MetricsLogger()],
   )

   # Training and prediction now trigger your callback hooks automatically
   workflow.fit(data=train_dataset)
   forecast = workflow.predict(data=live_dataset)

The ``WorkflowContext`` object passed to each hook carries the workflow instance itself
(``context.workflow``) and a free-form ``data`` dictionary you can use to pass state
between hooks within a single run:

.. code-block:: python

   class TimingCallback(PredictorCallback):
       def on_fit_start(self, context, data):
           import time
           context.data["fit_start_time"] = time.monotonic()

       def on_fit_end(self, context, result):
           import time
           elapsed = time.monotonic() - context.data["fit_start_time"]
           print(f"Training took {elapsed:.1f}s")

**Common callback use cases**

- Pushing metrics to MLflow, Prometheus, or a custom monitoring dashboard
- Saving model artefacts to object storage after each successful training run
- Sending alerts when prediction quality drops below a threshold
- Logging data lineage information for compliance purposes

----

Putting It All Together
-----------------------

A typical advanced setup combines all three extension points: custom data loading,
a domain-specific transform in the preprocessing pipeline, and a callback for
operational monitoring.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TransformPipeline
   from openstef_models.mixins.callbacks import PredictorCallback, WorkflowContext
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   # 1. Prepare data
   raw_df = pd.read_csv("substation_42.csv", index_col="timestamp", parse_dates=True)
   raw_df = raw_df.sort_index().asfreq("15min").ffill(limit=4)
   dataset = TimeSeriesDataset(data=raw_df, target_column="load_mw")

   # 2. Build a preprocessing pipeline with a custom transform
   pipeline = TransformPipeline(transforms=[HolidayFlagTransform(holidays=[...])])

   # 3. Attach a monitoring callback
   class SimpleLogger(PredictorCallback):
       def on_fit_end(self, context, result):
           print(f"Model {context.workflow.model_id} trained successfully.")

   # 4. Construct and run the workflow
   workflow = CustomForecastingWorkflow(
       model=my_model,          # EnsembleForecastingModel with pipeline attached
       model_id="substation_42",
       callbacks=[SimpleLogger()],
   )
   workflow.fit(data=dataset)

.. note::

   Model persistence is handled separately via the ``ModelSerializer`` mixin. Search
   the API reference for ``ModelSerializer`` to see how to save and reload fitted
   workflows between runs.

----

Next Steps
----------

- :doc:`backtesting` — once your custom pipeline is working, use backtesting to
  rigorously evaluate whether your feature engineering actually improves forecast accuracy.
- :doc:`first_forecast` — revisit the step-by-step tutorial if you want a refresher on
  the standard (non-customised) workflow before extending it.
- For a full reference of all transform classes available out of the box, see the
  **API Reference** section under ``openstef_core.transforms``.