Advanced Customization
======================

This page is for power users who want to go beyond the built-in defaults and tailor
OpenSTEF's behaviour to their specific forecasting problem. It covers three main
extension points: custom data preparation, custom feature engineering via transforms,
and custom pipeline and workflow composition. If you are still working through the
basics, start with :doc:`first_forecast` before continuing here.

.. note::

   All examples on this page assume you have already installed OpenSTEF and its
   dependencies. See :doc:`installation` for setup instructions.


Introduction
------------

OpenSTEF is designed as a library of composable building blocks rather than a
monolithic application. Almost every stage of the forecasting pipeline — data
ingestion, preprocessing, feature engineering, model training, postprocessing, and
result delivery — is expressed as a replaceable component that you can subclass or
swap out entirely. The three primary extension points are:

- **Transforms** – stateful or stateless data transformations that slot into a
  ``TransformPipeline`` at the preprocessing or postprocessing stage.
- **ForecastingModel** – the central pipeline object that wires together a
  preprocessing pipeline, a forecaster, and a postprocessing pipeline.
- **CustomForecastingWorkflow** – the outermost orchestration layer that adds
  lifecycle callbacks, model persistence, and experiment tracking on top of a
  ``ForecastingModel``.

Understanding how these three layers relate to each other is the key to effective
customization.

.. note:: [DIAGRAM: Three-layer architecture — CustomForecastingWorkflow wraps ForecastingModel which contains TransformPipeline (pre) → Forecaster → TransformPipeline (post)]


Custom Data Preparation
-----------------------

Before any model sees your data it must be packaged as a ``TimeSeriesDataset``.
This is a thin wrapper around a ``pandas.DataFrame`` that carries the sample
interval alongside the data, allowing downstream transforms to reason about time
gaps without inspecting the index directly.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef_core.datasets import TimeSeriesDataset

   # Build a DataFrame with a DatetimeIndex and at least a target column
   index = pd.date_range("2024-01-01", periods=672, freq="15min")
   df = pd.DataFrame(
       {
           "load": np.random.default_rng(0).standard_normal(672),
           "temperature": np.random.default_rng(1).standard_normal(672),
           "irradiance": np.clip(np.random.default_rng(2).standard_normal(672), 0, None),
       },
       index=index,
   )

   dataset = TimeSeriesDataset(data=df, sample_interval=pd.Timedelta("15min"))

The ``sample_interval`` argument is important: transforms that create lag features
or rolling statistics rely on it to express time offsets in a unit-agnostic way.
If your raw data arrives at irregular intervals, resample it to a fixed frequency
before wrapping it in a ``TimeSeriesDataset``.

For training workflows that need a validation split you can pass a separate
``data_val`` argument to ``fit()``. OpenSTEF does not enforce a particular
train/validation split strategy — you are free to use any windowing logic that
suits your data.

.. note::

   The ``cutoff_history`` parameter on ``ForecastingModel`` lets you exclude the
   leading rows that lag-based transforms render unusable (NaN-filled). For
   example, if your preprocessing pipeline includes a 14-day lag feature, set
   ``cutoff_history=pd.Timedelta(days=14)`` so those rows are never presented to
   the forecaster during training.


Custom Feature Engineering
--------------------------

Feature engineering in OpenSTEF is implemented through the ``Transform`` abstract
base class and its time-series-specific subclass ``TimeSeriesTransform``. A
transform follows the familiar scikit-learn ``fit`` / ``transform`` pattern:
``fit`` learns any parameters from training data, and ``transform`` applies the
learned (or stateless) operation to any dataset.

Implementing a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To add a new feature, subclass ``TimeSeriesTransform`` and implement three members:

- ``is_fitted`` – a property returning ``True`` once ``fit`` has been called.
- ``fit`` – learn parameters from the training data (omit if stateless).
- ``transform`` – apply the transformation and return a new ``TimeSeriesDataset``.
- ``features_added`` – list the column names your transform introduces.

.. code-block:: python

   from typing import override
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class RollingMeanTransform(TimeSeriesTransform):
       """Adds a rolling mean of the target column as a new feature."""

       def __init__(self, window: int = 4, target_col: str = "load") -> None:
           self.window = window
           self.target_col = target_col

       @property
       @override
       def is_fitted(self) -> bool:
           # Stateless transform — always ready
           return True

       @override
       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # Nothing to learn

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           col_name = f"{self.target_col}_rolling_{self.window}"
           df[col_name] = df[self.target_col].rolling(self.window).mean()
           return TimeSeriesDataset(data=df, sample_interval=data.sample_interval)

       @override
       def features_added(self) -> list[str]:
           return [f"{self.target_col}_rolling_{self.window}"]

For stateful transforms — for example, a scaler that must learn the training-set
mean and standard deviation — store the learned values as instance attributes and
gate ``is_fitted`` on their presence:

.. code-block:: python

   class ZScoreTransform(TimeSeriesTransform):
       """Standardises all numeric columns using training-set statistics."""

       def __init__(self) -> None:
           self._mean: pd.Series | None = None
           self._std: pd.Series | None = None

       @property
       @override
       def is_fitted(self) -> bool:
           return self._mean is not None

       @override
       def fit(self, data: TimeSeriesDataset) -> None:
           self._mean = data.data.mean()
           self._std = data.data.std().replace(0, 1)  # avoid division by zero

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           if not self.is_fitted:
               raise RuntimeError("Call fit() before transform().")
           scaled = (data.data - self._mean) / self._std
           return TimeSeriesDataset(data=scaled, sample_interval=data.sample_interval)

       @override
       def features_added(self) -> list[str]:
           return []  # modifies existing columns, adds none


Composing Transforms with TransformPipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual transforms are composed into a ``TransformPipeline``, which applies
them sequentially. During ``fit`` each transform is fitted on the *output* of the
previous one, so the order matters.

.. code-block:: python

   from openstef_core.transforms.pipeline import TransformPipeline

   preprocessing = TransformPipeline(
       transforms=[
           RollingMeanTransform(window=4, target_col="load"),
           ZScoreTransform(),
       ]
   )

   # fit_transform on training data, then transform-only on new data
   train_processed = preprocessing.fit_transform(data=train_dataset)
   val_processed = preprocessing.transform(data=val_dataset)

.. warning::

   Never call ``fit`` on validation or test data. Always call ``fit_transform``
   on training data and ``transform`` on held-out sets. ``ForecastingModel``
   enforces this internally, but if you call pipeline methods directly you are
   responsible for maintaining this discipline.


Custom Pipeline Workflows
--------------------------

Assembling a ForecastingModel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ForecastingModel`` is the central pipeline object. It accepts a preprocessing
``TransformPipeline``, a forecaster, and an optional postprocessing
``TransformPipeline``, and orchestrates the full fit/predict lifecycle.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms.pipeline import TransformPipeline
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )

   # Build datasets
   index = pd.date_range("2024-01-01", periods=672, freq="15min")
   df = pd.DataFrame(
       {"load": np.random.default_rng(42).standard_normal(672)},
       index=index,
   )
   train_dataset = TimeSeriesDataset(data=df, sample_interval=pd.Timedelta("15min"))

   # Assemble the pipeline
   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[RollingMeanTransform(window=4, target_col="load")]
       ),
       forecaster=ConstantMedianForecaster(),
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=pd.Timedelta(hours=1),
   )

   model.fit(data=train_dataset)

   # Predict on new data
   future_index = pd.date_range("2024-01-08", periods=96, freq="15min")
   future_df = pd.DataFrame(
       {"load": np.random.default_rng(99).standard_normal(96)},
       index=future_index,
   )
   future_dataset = TimeSeriesDataset(
       data=future_df, sample_interval=pd.Timedelta("15min")
   )
   forecasts = model.predict(data=future_dataset)


Adding Lifecycle Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^

``CustomForecastingWorkflow`` wraps a ``ForecastingModel`` and exposes a callback
system that fires at key lifecycle events: ``on_fit_start``, ``on_fit_end``,
``on_predict_start``, and ``on_predict_end``. Callbacks are the recommended way
to add cross-cutting concerns — logging, metrics emission, alerting — without
modifying the core pipeline logic.

To create a callback, subclass ``ForecastingCallback`` and override only the
hooks you need:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )


   class MetricsCallback(ForecastingCallback):
       """Logs the number of training samples and generated forecasts."""

       def on_fit_start(self, pipeline, dataset):
           print(f"[fit] Training on {len(dataset.data)} rows.")

       def on_fit_end(self, pipeline, dataset, result):
           print(f"[fit] Training complete. Result: {result}")

       def on_predict_end(self, pipeline, dataset, forecasts):
           print(f"[predict] Generated {len(forecasts.data)} forecast rows.")


   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[MetricsCallback()],
   )

   workflow.fit(data=train_dataset)
   forecasts = workflow.predict(data=future_dataset)

Because all methods have default no-op implementations you only need to override
the events that are relevant to your use case. Multiple callbacks can be supplied
as a list and they are executed in order.

.. note::

   If you need model persistence or experiment tracking with MLflow, OpenSTEF
   provides a built-in ``MLFlowStorageCallback`` that you can add to the
   ``callbacks`` list alongside your own callbacks. See the API reference for
   details.


Putting It All Together
-----------------------

A typical customization follows this pattern:

1. **Prepare data** – load your raw data, resample to a fixed frequency, and
   wrap it in ``TimeSeriesDataset``.
2. **Write transforms** – subclass ``TimeSeriesTransform`` for each feature
   engineering step and compose them into a ``TransformPipeline``.
3. **Assemble the model** – pass your preprocessing pipeline, your chosen
   forecaster, and an optional postprocessing pipeline to ``ForecastingModel``.
   Set ``cutoff_history`` to match the longest lag in your preprocessing.
4. **Wrap in a workflow** – create a ``CustomForecastingWorkflow`` with any
   callbacks you need for observability or persistence.
5. **Fit and predict** – call ``workflow.fit()`` on training data and
   ``workflow.predict()`` on new data.

This layered design means you can customize any single layer independently. You
might keep the default preprocessing transforms but swap in a different forecaster,
or keep the default forecaster but add domain-specific postprocessing — OpenSTEF
does not force you to touch layers you do not need to change.

For guidance on evaluating the quality of a customized pipeline against a
baseline, see :doc:`backtesting`.