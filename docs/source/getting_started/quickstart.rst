Quickstart
==========

This page gets you from a fresh install to a working forecast in under five minutes. There are no explanations of *why* things work the way they do — just the minimal, copy-paste-ready code you need. For deeper understanding, see :doc:`first_forecast`.

.. mermaid:: diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

Make sure OpenSTEF is installed before continuing. If you haven't done that yet, see :doc:`installation`.

.. code-block:: python

   # Verify your installation
   import openstef_core
   import openstef_models

The Complete Example
--------------------

The following script is self-contained. It uses OpenSTEF's built-in synthetic data generator so you don't need any external data files to run it.

.. code-block:: python

   # SPDX-License-Identifier: MPL-2.0
   import logging
   from datetime import timedelta
   from pathlib import Path

   from openstef_core.data_classes.dataset import TimeSeriesDataset
   from openstef_core.testing.synthetic import create_synthetic_forecasting_dataset
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.lead_time import LeadTime
   from openstef_models.models.quantile import Q
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage

   logging.basicConfig(level=logging.INFO)

   # ------------------------------------------------------------------
   # Step 1: Load data
   # ------------------------------------------------------------------
   # create_synthetic_forecasting_dataset returns a TimeSeriesDataset
   # with a 'load' target column and weather features (wind, temperature,
   # radiation) sampled at hourly intervals over nine months.
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=30 * 9),
       sample_interval=timedelta(hours=1),
   )

   # ------------------------------------------------------------------
   # Step 2: Create the model
   # ------------------------------------------------------------------
   # Define the forecast horizons you want — here, 24 hours ahead.
   horizons = [LeadTime.from_string("PT24H")]

   # ForecastingModel wraps a forecaster in a preprocessing → forecaster
   # → postprocessing pipeline. ConstantMedianForecaster is a simple
   # baseline that predicts the historical median for each horizon.
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       )
   )

   # ------------------------------------------------------------------
   # Step 3: Train
   # ------------------------------------------------------------------
   # CustomForecastingWorkflow manages the fit/predict lifecycle and
   # optionally persists the model to storage.
   storage = LocalModelStorage(base_path=Path("./models"))

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_first_forecast",
   )

   # fit() trains the model and returns prediction results on training data
   _, _, _, fit_result = workflow.fit(dataset)
   print("Training metrics:", fit_result.metrics_train)

   # ------------------------------------------------------------------
   # Step 4: Forecast
   # ------------------------------------------------------------------
   forecasts = workflow.predict(dataset)

   # ------------------------------------------------------------------
   # Step 5: Inspect output
   # ------------------------------------------------------------------
   print(forecasts.data.head())

Running the script produces console output similar to::

   Training metrics: SubsetMetric(mae=..., rmse=..., r2=...)
              load_q0.1  load_q0.5  load_q0.9
   2025-09-01 00:00:00       ...        ...        ...
   2025-09-01 01:00:00       ...        ...        ...
   ...

Step-by-Step Breakdown
-----------------------

If you want to understand what each step does before moving on, here is the short version:

- **Data** — ``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` with hourly load, wind, temperature, and radiation columns. Replace this with your own ``TimeSeriesDataset`` when you have real data.
- **Model** — ``ForecastingModel`` is the central pipeline object. ``ConstantMedianForecaster`` is a fast baseline; swap it for any other forecaster from ``openstef_models`` once you're comfortable.
- **Horizons** — ``LeadTime.from_string("PT24H")`` uses ISO 8601 duration strings. Common values are ``"PT1H"``, ``"PT6H"``, ``"PT24H"``, ``"PT48H"``.
- **Workflow** — ``CustomForecastingWorkflow`` handles the train/predict loop. Pass a ``LocalModelStorage`` instance to persist trained models to disk.
- **Output** — ``workflow.predict()`` returns a ``ForecastDataset`` whose ``.data`` attribute is a ``pandas.DataFrame`` indexed by timestamp.

.. note::

   ``ConstantMedianForecaster`` is intentionally simple — it is a useful baseline but not suitable for production. See :doc:`first_forecast` for a pipeline with feature engineering and a gradient-boosting forecaster.

Using Your Own Data
--------------------

Replace the synthetic dataset with a ``TimeSeriesDataset`` built from your own ``pandas.DataFrame``:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.data_classes.dataset import TimeSeriesDataset

   df = pd.read_csv("my_load_data.csv", index_col=0, parse_dates=True)
   # DataFrame must have a DatetimeIndex and at minimum a 'load' target column.

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1),
   )

The rest of the quickstart script works unchanged from this point.

.. note::

   The ``TimeSeriesDataset`` constructor validates that the index is a regular, gap-free ``DatetimeIndex`` at the specified ``sample_interval``. If your data has gaps, fill or resample it before constructing the dataset.

Saving and Reloading a Model
-----------------------------

Pass a ``LocalModelStorage`` to the workflow to persist your trained model:

.. code-block:: python

   from pathlib import Path
   from openstef_models.storage.local_model_storage import LocalModelStorage
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   storage = LocalModelStorage(base_path=Path("./models"))

   # Train and save
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_first_forecast",
       callbacks=[],   # add MLFlowStorageCallback here for experiment tracking
   )
   workflow.fit(dataset)

   # Reload later
   loaded_workflow = CustomForecastingWorkflow.from_storage(
       model_id="my_first_forecast",
       storage=storage,
   )
   forecasts = loaded_workflow.predict(dataset)

Next Steps
----------

Now that you have a working forecast, explore the rest of the getting-started material:

- :doc:`first_forecast` — the same workflow explained in detail, with feature engineering, lag transforms, and holiday features added.
- :doc:`backtesting` — evaluate your model on historical data to understand real-world performance before deploying.
- :doc:`advanced_customization` — build custom forecasters, preprocessing transforms, and postprocessing steps.