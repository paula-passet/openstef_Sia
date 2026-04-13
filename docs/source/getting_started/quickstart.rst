Quickstart
==========

Get your first OpenSTEF forecast running in under five minutes. This page is intentionally minimal — copy the code, run it, see results. For explanations of what each piece does and why, see :doc:`first_forecast`.

.. note:: [DIAGRAM: Simple workflow — data loading → model creation → training → forecasting → output]

Prerequisites
-------------

OpenSTEF must be installed before running the examples below. If you haven't done that yet, see :doc:`installation`.

.. code-block:: python

   pip install openstef-models

The Minimal Example
-------------------

The following self-contained script generates synthetic hourly load data, trains a baseline forecaster, and produces a 24-hour-ahead forecast with confidence intervals. Nothing external is required — no database, no files, no API keys.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.types import LeadTime
   from openstef_core.types import Quantile as Q
   from openstef_core.datasets.validated_datasets import TimeSeriesDataset
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # ── 1. Load data ──────────────────────────────────────────────────────────
   rng = np.random.default_rng(42)
   n_samples = 24 * 90  # 90 days of hourly data

   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h")
   load = rng.standard_normal(size=n_samples) * 10 + 50   # synthetic load (MW)
   temp = rng.standard_normal(size=n_samples) * 5 + 10    # synthetic temperature

   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {"load": load, "temperature": temp},
           index=timestamps,
       ),
       sample_interval=timedelta(hours=1),
   )

   # ── 2. Create model ───────────────────────────────────────────────────────
   horizons = [LeadTime.from_string("PT24H")]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
       target_column="load",
   )

   # ── 3. Train ──────────────────────────────────────────────────────────────
   workflow = CustomForecastingWorkflow(model=model, model_id="my_first_forecast")
   workflow.fit(dataset)

   # ── 4. Forecast ───────────────────────────────────────────────────────────
   forecasts = workflow.predict(dataset)

   # ── 5. Inspect output ─────────────────────────────────────────────────────
   print(forecasts.data.head())

Running this script prints a DataFrame whose columns are the requested quantiles (``q0.1``, ``q0.5``, ``q0.9``) and whose index contains the forecast timestamps 24 hours ahead of the last training observation.

Understanding the Output
------------------------

The ``forecasts.data`` object is a standard ``pandas.DataFrame``:

.. code-block:: python

   # Each column is one quantile; each row is one forecast timestamp
   #                        q0.1       q0.5       q0.9
   # 2025-04-01 00:00:00   46.23      50.11      53.98
   # 2025-04-01 01:00:00   46.23      50.11      53.98
   # ...

- **q0.5** is the median (point) forecast.
- **q0.1 / q0.9** are the lower and upper bounds of the 80 % prediction interval.

.. note::

   ``ConstantMedianForecaster`` is a baseline model that returns the same quantile
   values for every horizon. It is ideal for verifying your pipeline is wired
   correctly before swapping in a more powerful forecaster such as
   ``GBLinearForecaster``. See :doc:`first_forecast` for that next step.

Swapping to a Real Forecaster
------------------------------

Replace the ``forecaster=`` argument to use a production-grade model. The rest of
the pipeline stays identical:

.. code-block:: python

   from openstef_models.models.forecasting.gb_linear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )

   model = ForecastingModel(
       forecaster=GBLinearForecaster(
           horizons=horizons,
           quantiles=quantiles,
           hyperparams=GBLinearHyperParams(
               n_steps=500,
               learning_rate=0.1,
           ),
       ),
       target_column="load",
   )

   workflow = CustomForecastingWorkflow(model=model, model_id="my_gblinear_forecast")
   workflow.fit(dataset)
   forecasts = workflow.predict(dataset)

Adding Feature Engineering
---------------------------

Preprocessing transforms slot into ``ForecastingModel`` without changing the
training or prediction calls:

.. code-block:: python

   from openstef_models.preprocessing.transform_pipeline import TransformPipeline
   from openstef_models.preprocessing.transforms.scaler import Scaler
   from openstef_models.preprocessing.transforms.holiday_feature_adder import (
       HolidayFeatureAdder,
   )
   from openstef_core.types import FeatureSelection, CountryAlpha2

   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(
                   method="standard",
                   selection=FeatureSelection(include={"temperature"}),
               ),
               HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           ]
       ),
       forecaster=GBLinearForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
       target_column="load",
   )

   workflow = CustomForecastingWorkflow(model=model, model_id="my_featured_forecast")
   workflow.fit(dataset)
   forecasts = workflow.predict(dataset)

.. note::

   When using lag-based transforms, set ``cutoff_history`` on ``ForecastingModel``
   to exclude the initial NaN-filled rows from training. For example, a 14-day lag
   requires ``cutoff_history=timedelta(days=14)``.

Persisting a Trained Model
---------------------------

Save the workflow to disk so you can reload it later without retraining:

.. code-block:: python

   from openstef_models.storage.local_model_storage import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(base_path=Path("./models"))

   # Save after training
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_forecast",
       storage=storage,
   )
   workflow.fit(dataset)   # model is automatically persisted

   # Reload and predict later
   loaded_workflow = CustomForecastingWorkflow.from_storage(
       model_id="my_forecast",
       storage=storage,
   )
   forecasts = loaded_workflow.predict(dataset)

Common Errors
-------------

``NotFittedError``
   You called ``predict()`` before ``fit()``. Always call ``workflow.fit(dataset)``
   first.

``ValueError: Unsupported model type``
   The forecaster and preprocessing horizons do not match. Ensure the same
   ``horizons`` list is passed to both.

``KeyError`` on target column
   The column name passed to ``target_column=`` does not exist in your DataFrame.
   Check ``dataset.feature_names`` to see what columns are available.

Next Steps
----------

This page showed the fastest path to a working forecast. To go further:

- :doc:`first_forecast` — step-by-step walkthrough explaining every decision above.
- :doc:`backtesting` — evaluate how well your model would have performed historically.
- :doc:`advanced_customization` — write custom forecasters, transforms, and callbacks.