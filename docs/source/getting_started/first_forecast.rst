Your First Forecast
===================

This tutorial walks through building a short-term energy forecast from scratch using
OpenSTEF's custom pipeline approach. You will prepare a dataset, configure a
:class:`ForecastingModel` with preprocessing and a forecaster, train it, generate
predictions, and inspect the results. Each step explains *what* is happening and *why*
it matters for energy forecasting.

.. note::

   If you just want the shortest possible working example, see :doc:`quickstart` first.
   This page goes deeper: it explains every component so you can adapt the pipeline to
   your own data. For evaluating a trained model on historical data, see
   :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

----

Preparing Your Data
-------------------

OpenSTEF expects time series data wrapped in a :class:`~openstef_core.datasets.TimeSeriesDataset`.
The dataset holds a :class:`pandas.DataFrame` indexed by UTC-aware timestamps, plus
metadata such as the measurement interval.

The target column (the quantity you want to forecast, typically electrical load in MW)
must be present alongside any exogenous features you want the model to learn from.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Three months of synthetic hourly load data
   rng = np.random.default_rng(42)
   n_samples = 24 * 31 * 3          # ~2 232 hourly observations
   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h", tz="UTC")

   df = pd.DataFrame(
       {
           "load": rng.standard_normal(n_samples) * 10 + 50,   # MW, centred on 50
           "temperature": rng.standard_normal(n_samples) * 5 + 10,  # °C
       },
       index=timestamps,
   )

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1),
   )

.. note::

   In production you would load real meter data here — for example from a database or
   a CSV file — and convert the index to UTC before constructing the dataset.
   OpenSTEF does not impose a particular data-loading strategy; bring your own I/O.

----

Configuring the Preprocessing Pipeline
---------------------------------------

Raw time series rarely contain the features a model needs. OpenSTEF's
:class:`~openstef_core.transforms.TransformPipeline` chains a sequence of
:class:`~openstef_core.transforms.Transform` objects, each fitted on the output of the
previous one. This keeps feature engineering reproducible and serialisable alongside
the model.

For a typical energy forecast you want at minimum:

- **Holiday features** — public holidays shift load profiles significantly.
- **Lag transforms** — yesterday's load at the same hour is a strong predictor.
- **A scaler** — gradient-boosting models are scale-invariant, but linear components
  benefit from normalised inputs.

.. code-block:: python

   from openstef_models.transforms.time_domain import LagTransform
   from openstef_models.transforms.calendar import HolidayFeatures
   from openstef_models.transforms.scaling import StandardScaler
   from openstef_core.transforms import TransformPipeline

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatures(country="NL"),   # adds binary holiday indicator columns
           LagTransform(
               lags=[
                   timedelta(hours=1),
                   timedelta(hours=24),
                   timedelta(hours=168),    # one week
               ],
               target_column="load",
           ),
           StandardScaler(),
       ]
   )

Each transform exposes ``fit``, ``transform``, and ``fit_transform``. The pipeline
calls them in order during training and replays only ``transform`` at inference time,
so the scaler statistics learned on training data are applied consistently to new
observations.

----

Choosing a Forecaster
----------------------

The forecaster sits at the heart of :class:`~openstef_core.models.ForecastingModel`.
It receives the preprocessed dataset and produces probabilistic forecasts expressed as
quantiles. Here we use :class:`~openstef_models.forecasters.GBLinearForecaster`, which
combines gradient-boosted trees with a linear residual layer and supports multiple
forecast horizons in a single model.

.. code-block:: python

   from openstef_models.forecasters import GBLinearForecaster
   from openstef_models.forecasters.gb_linear import GBLinearHyperParams
   from openstef_core.models import LeadTime, Q

   forecaster = GBLinearForecaster(
       horizons=[
           LeadTime.from_string("PT1H"),    # 1-hour-ahead
           LeadTime.from_string("PT24H"),   # day-ahead
           LeadTime.from_string("PT48H"),   # two-day-ahead
       ],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)], # 10th, median, 90th percentile
       hyperparams=GBLinearHyperParams(n_steps=200),
       verbosity=0,
   )

``LeadTime`` objects encode the ISO 8601 duration of each forecast horizon.
``Q(0.5)`` is the median (point forecast); adding ``Q(0.1)`` and ``Q(0.9)`` gives you
an 80 % prediction interval at no extra training cost.

----

Assembling the ForecastingModel
--------------------------------

:class:`~openstef_core.models.ForecastingModel` is the container that binds
preprocessing, the forecaster, and optional postprocessing into a single object that
can be fitted, serialised, and reloaded.

.. code-block:: python

   from openstef_core.models import ForecastingModel
   from openstef_models.transforms.postprocessing import QuantileSorter, ConfidenceIntervalApplicator

   postprocessing = TransformPipeline(
       transforms=[
           QuantileSorter(),                        # ensures q10 ≤ q50 ≤ q90
           ConfidenceIntervalApplicator(
               quantiles=[Q(0.1), Q(0.5), Q(0.9)],
               add_quantiles_from_std=False,
           ),
       ]
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=forecaster,
       postprocessing=postprocessing,
       target_column="load",
   )

The postprocessing step is optional but recommended. ``QuantileSorter`` corrects
quantile crossings that can occur when quantiles are predicted independently.
``ConfidenceIntervalApplicator`` formats the output into the standard OpenSTEF
forecast schema.

----

Training with CustomForecastingWorkflow
----------------------------------------

:class:`~openstef_core.workflows.CustomForecastingWorkflow` wraps a
:class:`~openstef_core.models.ForecastingModel` and adds model persistence, optional
callbacks (e.g. MLflow logging), and a consistent ``fit`` / ``predict`` interface.

.. code-block:: python

   from openstef_core.workflows import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(
       model_id="my_first_forecast",
       model=model,
   )

   workflow.fit(dataset)

Calling ``fit`` triggers the following sequence internally:

1. The preprocessing pipeline is fitted and applied to the dataset.
2. The forecaster is trained on the transformed features.
3. The fitted pipeline and model weights are stored inside the workflow object,
   ready for serialisation.

.. note::

   ``model_id`` is used as the key when saving and loading models. If you add an
   MLflow callback, this string becomes the registered model name. Keep it
   descriptive and unique per forecasting location or asset.

----

Generating a Forecast
----------------------

Once fitted, call ``predict`` with a dataset that covers the horizon you want to
forecast. The dataset must include the same feature columns used during training; the
target column may be absent (or ``NaN``) for future timestamps.

.. code-block:: python

   # Predict over the same dataset (in practice, use a future window)
   forecast = workflow.predict(dataset)

   # forecast is a ForecastDataset; access the underlying DataFrame:
   print(forecast.data.head())

.. note:: [VISUALIZATION: Time series plot showing the median forecast (q50) as a solid line with a shaded 80% prediction interval (q10–q90) band over a 48-hour window, produced by ForecastTimeSeriesPlotter]

OpenSTEF ships a built-in plotter for exactly this output:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(forecast)
   fig.show()

----

Evaluating the Forecast
------------------------

:class:`~openstef_core.models.ForecastingModel` exposes a ``score`` method that runs
``predict`` internally and computes evaluation metrics against the ground-truth target
column in the same dataset. This is useful for a quick sanity check on held-out data.

.. code-block:: python

   # Split: use the last month as a hold-out set
   cutoff = pd.Timestamp("2025-03-01", tz="UTC")
   train_data = TimeSeriesDataset(
       data=df[df.index < cutoff],
       sample_interval=timedelta(hours=1),
   )
   test_data = TimeSeriesDataset(
       data=df[df.index >= cutoff],
       sample_interval=timedelta(hours=1),
   )

   workflow.fit(train_data)
   metrics = workflow.model.score(test_data)

   print(metrics)

The returned :class:`~openstef_beam.evaluation.models.SubsetMetric` object contains
standard regression metrics (MAE, RMSE, skill score) broken down by forecast horizon.

.. note::

   ``score`` is a convenience method for quick checks. For rigorous walk-forward
   evaluation across multiple training windows, use the backtesting pipeline described
   in :doc:`backtesting`.

----

Saving and Reloading the Model
-------------------------------

Use :class:`~openstef_core.storage.LocalModelStorage` to persist the fitted workflow to
disk and reload it later without retraining.

.. code-block:: python

   from pathlib import Path
   from openstef_core.storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))

   # Save
   storage.save(model_id="my_first_forecast", workflow=workflow)

   # Reload
   loaded_workflow = storage.load(model_id="my_first_forecast")
   new_forecast = loaded_workflow.predict(test_data)

The storage layer serialises the entire workflow — preprocessing statistics, model
weights, and postprocessing configuration — into a single artefact. Swapping
``LocalModelStorage`` for ``MLFlowStorageCallback`` gives you experiment tracking and
model versioning with no changes to the training code; see
:doc:`advanced_customization` for details.

----

Putting It All Together
------------------------

Below is the complete, self-contained script combining every step above:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from pathlib import Path

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.models import ForecastingModel, LeadTime, Q
   from openstef_core.transforms import TransformPipeline
   from openstef_core.workflows import CustomForecastingWorkflow
   from openstef_core.storage import LocalModelStorage

   from openstef_models.forecasters import GBLinearForecaster
   from openstef_models.forecasters.gb_linear import GBLinearHyperParams
   from openstef_models.transforms.time_domain import LagTransform
   from openstef_models.transforms.calendar import HolidayFeatures
   from openstef_models.transforms.scaling import StandardScaler
   from openstef_models.transforms.postprocessing import (
       QuantileSorter,
       ConfidenceIntervalApplicator,
   )

   # --- Data ---
   rng = np.random.default_rng(42)
   n_samples = 24 * 31 * 3
   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h", tz="UTC")
   df = pd.DataFrame(
       {
           "load": rng.standard_normal(n_samples) * 10 + 50,
           "temperature": rng.standard_normal(n_samples) * 5 + 10,
       },
       index=timestamps,
   )
   cutoff = pd.Timestamp("2025-03-01", tz="UTC")
   train_ds = TimeSeriesDataset(data=df[df.index < cutoff], sample_interval=timedelta(hours=1))
   test_ds  = TimeSeriesDataset(data=df[df.index >= cutoff], sample_interval=timedelta(hours=1))

   # --- Pipeline ---
   preprocessing = TransformPipeline(transforms=[
       HolidayFeatures(country="NL"),
       LagTransform(lags=[timedelta(hours=1), timedelta(hours=24), timedelta(hours=168)],
                    target_column="load"),
       StandardScaler(),
   ])
   postprocessing = TransformPipeline(transforms=[
       QuantileSorter(),
       ConfidenceIntervalApplicator(quantiles=[Q(0.1), Q(0.5), Q(0.9)],
                                    add_quantiles_from_std=False),
   ])
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=GBLinearForecaster(
           horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("PT24H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           hyperparams=GBLinearHyperParams(n_steps=200),
           verbosity=0,
       ),
       postprocessing=postprocessing,
       target_column="load",
   )

   # --- Train ---
   workflow = CustomForecastingWorkflow(model_id="my_first_forecast", model=model)
   workflow.fit(train_ds)

   # --- Evaluate ---
   metrics = workflow.model.score(test_ds)
   print(metrics)

   # --- Forecast ---
   forecast = workflow.predict(test_ds)
   print(forecast.data.head())

   # --- Persist ---
   LocalModelStorage(base_path=Path("./models")).save(
       model_id="my_first_forecast", workflow=workflow
   )

----

Next Steps
----------

You now have a working forecast pipeline. From here you can:

- **Tune the model** — explore alternative forecasters, add more lag horizons, or
  write a custom transform. See :doc:`advanced_customization`.
- **Evaluate rigorously** — run a walk-forward backtest over months of history to
  measure real-world accuracy. See :doc:`backtesting`.
- **Revisit the basics** — if anything above felt unfamiliar, the :doc:`quickstart`
  page provides a minimal reference example with no configuration overhead.