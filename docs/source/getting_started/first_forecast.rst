Your First Forecast
===================

This tutorial walks through building a short-term energy forecast from scratch using
OpenSTEF's custom pipeline approach. You will prepare a dataset, configure a
:class:`ForecastingModel` with preprocessing and a forecaster, train it, generate
predictions, and inspect evaluation metrics. Each step explains *what* is happening
and *why* it matters for energy time series.

.. note::

   If you just want the shortest possible working example, see :doc:`quickstart` first.
   This page goes deeper: it explains every component so you can adapt the pipeline to
   your own data. For evaluating a trained model on historical data, see
   :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Prerequisites
-------------

Make sure OpenSTEF is installed before continuing. See :doc:`installation` for
instructions. All imports used below come from the ``openstef_core``,
``openstef_models``, and ``openstef_beam`` packages that are installed as part of the
library.


Step 1 — Prepare Your Data
---------------------------

OpenSTEF expects time series data wrapped in a :class:`~openstef_core.datasets.TimeSeriesDataset`.
The dataset holds a :class:`pandas.DataFrame` indexed by UTC timestamps together with
a ``sample_interval`` that describes the measurement cadence.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Three months of synthetic hourly load data with one exogenous feature
   rng = np.random.default_rng(42)
   n_samples = 24 * 31 * 3          # ~2 232 hourly observations
   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h", tz="UTC")

   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {
               "load":    rng.standard_normal(n_samples) * 10 + 50,
               "weather": rng.standard_normal(n_samples),
           },
           index=timestamps,
       ),
       sample_interval=timedelta(hours=1),
   )

**Why this matters.** The ``sample_interval`` is used downstream by lag transforms and
lead-time calculations to convert human-readable durations (e.g. ``"PT1H"``) into
integer row offsets. Getting it right avoids silent misalignments between features and
targets.

For real data, load your measurements from a database or CSV and pass the resulting
DataFrame directly. The only hard requirements are a timezone-aware
:class:`~pandas.DatetimeIndex` and a consistent sampling frequency.


Step 2 — Configure the Preprocessing Pipeline
----------------------------------------------

Raw time series rarely contain all the features a model needs. OpenSTEF's
:class:`~openstef_core.transforms.TransformPipeline` chains transforms that are fitted
and applied in sequence. Each transform receives the output of the previous one, so
order matters.

A typical preprocessing pipeline for energy forecasting adds:

- **Holiday features** — captures demand patterns around public holidays.
- **Lag features** — gives the model access to recent historical load values.
- **A scaler** — normalises inputs so gradient-based models converge reliably.

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain import LagAdder
   from openstef_models.transforms.calendar import HolidayFeatures
   from openstef_models.transforms.scaling import StandardScaler
   from pydantic_extra_types.country import CountryAlpha2

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatures(country=CountryAlpha2("NL")),
           LagAdder(lags=[timedelta(hours=1), timedelta(hours=24), timedelta(hours=168)]),
           StandardScaler(),
       ]
   )

The ``LagAdder`` lags shown here capture the load from one hour ago, yesterday at the
same hour, and one week ago — three of the strongest predictors in most grid datasets.
Adjust the list to match the autocorrelation structure of your own series.

.. note::

   ``TransformPipeline`` is generic: the same class is used for both preprocessing
   (input is a :class:`~openstef_core.datasets.TimeSeriesDataset`) and postprocessing
   (input is a :class:`~openstef_core.datasets.ForecastDataset`). The type parameter
   keeps the two pipelines type-safe.


Step 3 — Choose a Forecaster and Configure the Model
-----------------------------------------------------

The :class:`~openstef_models.forecasters.ForecastingModel` is the central object. It
owns the preprocessing pipeline, the forecaster, and an optional postprocessing
pipeline. Separating these three concerns makes it straightforward to swap the
forecaster without touching feature engineering.

.. code-block:: python

   from openstef_models.forecasters import ForecastingModel
   from openstef_models.forecasters.gb_linear import GBLinearForecaster, GBLinearHyperParams
   from openstef_core.lead_time import LeadTime
   from openstef_core.quantiles import Q
   from openstef_models.transforms.postprocessing import QuantileSorter

   forecaster = GBLinearForecaster(
       horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("PT24H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       hyperparams=GBLinearHyperParams(n_steps=200),
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=forecaster,
       postprocessing=TransformPipeline(transforms=[QuantileSorter()]),
       target_column="load",
   )

A few decisions to note:

- **Horizons** define which lead times the model is trained to predict. ``"PT1H"``
  means one hour ahead; ``"PT24H"`` means 24 hours ahead. You can add as many as your
  use case requires.
- **Quantiles** turn the forecast into a probabilistic range. ``Q(0.5)`` is the median
  (point forecast); ``Q(0.1)`` and ``Q(0.9)`` form an 80 % prediction interval.
- **QuantileSorter** in postprocessing guarantees that quantile curves never cross —
  a common artefact when quantiles are predicted independently.

For a full list of available forecasters and their hyperparameters, see
:doc:`advanced_customization`.


Step 4 — Wrap in a Workflow and Train
--------------------------------------

:class:`~openstef_beam.workflows.CustomForecastingWorkflow` orchestrates training and
inference. It also handles model persistence through an optional storage backend. For
this tutorial, storage is omitted to keep things self-contained.

.. code-block:: python

   from openstef_beam.workflows import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(
       model_id="my_first_forecast",
       model=model,
   )

   workflow.fit(dataset)

Calling ``fit`` triggers the full training sequence:

1. The preprocessing pipeline is fitted on the training split and transforms the data.
2. The forecaster is trained on the transformed features for every configured horizon.
3. The postprocessing pipeline is fitted (if any transforms require it).

The ``model_id`` is used as a key when persisting models to storage. Even without
storage configured, it appears in log output and evaluation reports, so choose
something descriptive.


Step 5 — Generate a Forecast
-----------------------------

Once trained, call ``predict`` with a dataset that covers the period you want to
forecast. The dataset must contain the same feature columns used during training so
that the fitted preprocessing pipeline can transform it correctly.

.. code-block:: python

   # In practice this would be fresh data; here we reuse the training set
   # to verify the pipeline runs end-to-end.
   forecast = workflow.predict(dataset)

   print(forecast.data.head())

``predict`` returns a :class:`~openstef_core.datasets.ForecastDataset` whose
``.data`` attribute is a DataFrame indexed by timestamp. Each row contains the
predicted quantiles for every configured lead time.

.. note:: [VISUALIZATION: Line chart showing the Q(0.1), Q(0.5), and Q(0.9) forecast quantiles plotted against the actual load time series for a 48-hour window, illustrating the probabilistic forecast envelope.]


Step 6 — Evaluate the Forecast
--------------------------------

:class:`~openstef_models.forecasters.ForecastingModel` exposes a ``score`` method that
runs prediction and computes evaluation metrics in one call. By default it reports
metrics at the maximum configured horizon.

.. code-block:: python

   from openstef_beam.evaluation.metric_providers import MAEMetricProvider, RMSEMetricProvider
   from openstef_models.forecasters import ForecastingModel
   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.postprocessing import QuantileSorter

   # Rebuild model with explicit evaluation metrics
   model_with_metrics = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=forecaster,
       postprocessing=TransformPipeline(transforms=[QuantileSorter()]),
       target_column="load",
       evaluation_metrics=[MAEMetricProvider(), RMSEMetricProvider()],
   )

   workflow_eval = CustomForecastingWorkflow(
       model_id="my_first_forecast_eval",
       model=model_with_metrics,
   )
   workflow_eval.fit(dataset)

   metrics = workflow_eval.model.score(dataset)
   print(metrics)

The returned :class:`~openstef_beam.evaluation.models.SubsetMetric` object contains
the metric values keyed by name. A low MAE on the training set confirms the pipeline
ran correctly; for a realistic performance estimate, always evaluate on held-out data
— see :doc:`backtesting` for the proper approach.

.. note::

   Evaluating on the same data used for training will produce optimistically low
   error figures. The :doc:`backtesting` tutorial shows how to use
   ``openstef_beam``'s backtesting pipeline to measure out-of-sample performance
   across a rolling window of historical periods.


Putting It All Together
------------------------

Here is the complete, self-contained script combining every step above:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.lead_time import LeadTime
   from openstef_core.quantiles import Q
   from openstef_core.transforms import TransformPipeline

   from openstef_models.forecasters import ForecastingModel
   from openstef_models.forecasters.gb_linear import GBLinearForecaster, GBLinearHyperParams
   from openstef_models.transforms.calendar import HolidayFeatures
   from openstef_models.transforms.time_domain import LagAdder
   from openstef_models.transforms.scaling import StandardScaler
   from openstef_models.transforms.postprocessing import QuantileSorter

   from openstef_beam.workflows import CustomForecastingWorkflow
   from openstef_beam.evaluation.metric_providers import MAEMetricProvider, RMSEMetricProvider

   # --- Data ---
   rng = np.random.default_rng(42)
   n_samples = 24 * 31 * 3
   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h", tz="UTC")
   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {"load": rng.standard_normal(n_samples) * 10 + 50,
            "weather": rng.standard_normal(n_samples)},
           index=timestamps,
       ),
       sample_interval=timedelta(hours=1),
   )

   # --- Pipeline ---
   preprocessing = TransformPipeline(transforms=[
       HolidayFeatures(country=CountryAlpha2("NL")),
       LagAdder(lags=[timedelta(hours=1), timedelta(hours=24), timedelta(hours=168)]),
       StandardScaler(),
   ])

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=GBLinearForecaster(
           horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("PT24H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           hyperparams=GBLinearHyperParams(n_steps=200),
       ),
       postprocessing=TransformPipeline(transforms=[QuantileSorter()]),
       target_column="load",
       evaluation_metrics=[MAEMetricProvider(), RMSEMetricProvider()],
   )

   # --- Train ---
   workflow = CustomForecastingWorkflow(model_id="my_first_forecast", model=model)
   workflow.fit(dataset)

   # --- Predict ---
   forecast = workflow.predict(dataset)
   print(forecast.data.head())

   # --- Evaluate ---
   metrics = workflow.model.score(dataset)
   print(metrics)


Next Steps
----------

You now have a working forecast pipeline. From here you can:

- **Measure real performance** — :doc:`backtesting` shows how to evaluate the model
  on historical data it has never seen.
- **Customise transforms and forecasters** — :doc:`advanced_customization` covers
  writing your own transforms, swapping forecasters, and tuning hyperparameters.
- **Persist models** — replace the default in-memory storage with
  :class:`~openstef_beam.storage.LocalModelStorage` or an MLflow backend so trained
  models survive between runs.