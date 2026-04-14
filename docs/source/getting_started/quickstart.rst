Quickstart
==========

Get your first OpenSTEF forecast running in under five minutes. This page is intentionally minimal — copy the code, run it, and see output. For explanations of what each component does, see :doc:`first_forecast`. For backtesting and model comparison, see :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF must be installed before running any of the examples below. If you haven't done that yet, see :doc:`installation`.

.. code-block:: python

   pip install openstef-models

Minimal Working Example
-----------------------

The following script is self-contained. It generates synthetic hourly load data, trains a model, produces a 24-hour-ahead forecast, and prints the result.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef_core.datasets.validated_datasets import TimeSeriesDataset
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # ── 1. Create synthetic data ──────────────────────────────────────────────
   rng = np.random.default_rng(42)
   n_samples = 24 * 30  # 30 days of hourly data

   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h")
   load = rng.standard_normal(size=n_samples) * 10 + 50   # MW, centred on 50

   dataset = TimeSeriesDataset(
       data=pd.DataFrame({"load": load}, index=timestamps),
       sample_interval=timedelta(hours=1),
   )

   # ── 2. Create the model ───────────────────────────────────────────────────
   horizons = [LeadTime.from_string("PT24H")]

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       ),
       target_column="load",
   )

   # ── 3. Train ──────────────────────────────────────────────────────────────
   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart-model")
   workflow.fit(dataset)

   # ── 4. Forecast ───────────────────────────────────────────────────────────
   forecasts = workflow.predict(dataset)

   # ── 5. Inspect output ─────────────────────────────────────────────────────
   print(forecasts.data.head())

Running this script prints a DataFrame whose columns are the requested quantiles (``q0.1``, ``q0.5``, ``q0.9``) and whose index contains the forecast timestamps 24 hours ahead.

What You Just Did
-----------------

Each numbered step in the script maps to one stage of the workflow shown in the diagram above:

- **Data loading** — ``TimeSeriesDataset`` wraps a plain ``pandas.DataFrame`` with a declared ``sample_interval``.
- **Model creation** — ``ForecastingModel`` composes a forecaster (and optionally preprocessing/postprocessing pipelines) into a single object.
- **Training** — ``CustomForecastingWorkflow.fit()`` trains the model against the dataset.
- **Forecasting** — ``CustomForecastingWorkflow.predict()`` returns a ``ForecastDataset`` containing quantile predictions.
- **Output** — ``forecasts.data`` is a standard ``pandas.DataFrame`` you can use immediately.

.. note::

   ``ConstantMedianForecaster`` is a baseline model that predicts historical quantile values. It is ideal for getting the pipeline running quickly. Swap it for ``GBLinearForecaster`` or another model when you need real predictive power — see :doc:`first_forecast` for that step.

Adding Weather Features
-----------------------

Real energy forecasts almost always include weather covariates. Adding them requires only a larger input DataFrame and a preprocessing pipeline:

.. code-block:: python

   from openstef_models.preprocessing.transforms import (
       TransformPipeline,
       Scaler,
       FeatureSelection,
   )

   # Extend the dataset with weather columns
   temp       = rng.standard_normal(size=n_samples) * 5 + 15
   wind       = rng.standard_normal(size=n_samples).clip(0)
   radiation  = rng.standard_normal(size=n_samples).clip(0)

   dataset_weather = TimeSeriesDataset(
       data=pd.DataFrame(
           {
               "load":      load,
               "temp":      temp,
               "wind":      wind,
               "radiation": radiation,
           },
           index=timestamps,
       ),
       sample_interval=timedelta(hours=1),
   )

   # Add a scaling step for the weather features
   preprocessing = TransformPipeline(
       transforms=[
           Scaler(
               method="standard",
               selection=FeatureSelection(include={"temp", "wind", "radiation"}),
           ),
       ]
   )

   model_weather = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       ),
       target_column="load",
   )

   workflow_weather = CustomForecastingWorkflow(
       model=model_weather, model_id="quickstart-weather"
   )
   workflow_weather.fit(dataset_weather)
   forecasts_weather = workflow_weather.predict(dataset_weather)
   print(forecasts_weather.data.head())

Persisting a Model
------------------

To save and reload a trained model, pass a ``LocalModelStorage`` instance to the workflow:

.. code-block:: python

   from pathlib import Path
   from openstef_models.storage.local_model_storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))

   workflow_persistent = CustomForecastingWorkflow(
       model=model,
       model_id="quickstart-persistent",
       storage=storage,
   )
   workflow_persistent.fit(dataset)    # model is saved automatically after fit
   forecasts = workflow_persistent.predict(dataset)

The model is serialised under ``./models/quickstart-persistent/``. Pass the same ``storage`` and ``model_id`` to ``ForecastingWorkflow.from_storage()`` to reload it in a later session.

.. note::

   Model persistence is optional for the quickstart but becomes important in production. See :doc:`advanced_customization` for storage backends beyond the local filesystem.

Next Steps
----------

Now that you have a working forecast, the natural next steps are:

- :doc:`first_forecast` — the same pipeline explained step by step, with a production-grade model and real data patterns.
- :doc:`backtesting` — evaluate how well your model would have performed on historical data.
- :doc:`advanced_customization` — custom forecasters, alternative storage backends, and callback hooks.