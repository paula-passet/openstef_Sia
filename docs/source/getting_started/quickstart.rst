Quickstart
==========

Get from zero to a working energy forecast in under five minutes. This page is a single, copy-paste-ready example — no background theory, no configuration deep-dives. If you want explanations of *why* things work the way they do, see :doc:`first_forecast`. For installation help, see :doc:`installation`.

.. note:: [DIAGRAM: Linear workflow — (1) Load data → (2) Build model → (3) Train → (4) Forecast → (5) Inspect output. Each step maps directly to one code block below.]

Prerequisites
-------------

OpenSTEF installed and importable. If not, follow :doc:`installation` first, then come back here.

.. code-block:: python

   import openstef_core
   import openstef_models

If those lines run without error, you are ready.

The Complete Example
--------------------

The five blocks below form one continuous script. You can paste them together and run the file as-is.

Step 1 — Load sample data
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF ships a synthetic dataset generator so you can start without any real data files.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   # Nine months of hourly load data with weather features
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       random_seed=42,
   )

   print(dataset.data.shape)        # e.g. (6480, N)
   print(dataset.data.columns.tolist())

``create_synthetic_forecasting_dataset`` returns a :class:`~openstef_core.datasets.TimeSeriesDataset` — the standard data container used throughout the library.

Step 2 — Build the model
^^^^^^^^^^^^^^^^^^^^^^^^^

Assemble a :class:`~openstef_models.models.forecasting_model.ForecastingModel`: a preprocessing pipeline, a forecaster, and a postprocessing pipeline.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.types import Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.transforms.feature_pipeline import FeaturePipeline
   from openstef_models.transforms.lags_adder import LagsAdder
   from openstef_models.transforms.transform_pipeline import TransformPipeline

   horizons = [timedelta(hours=h) for h in range(1, 25)]   # 1-hour to 24-hour ahead
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   preprocessing = FeaturePipeline(
       transforms=[
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=horizons,
               target_column="load",
           ),
       ]
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=timedelta(days=14),   # matches the lag window above
   )

.. note::

   ``cutoff_history`` must match the longest lag in your preprocessing pipeline.
   Here ``LagsAdder`` uses up to 14 days of history, so the first 14 days of
   training data are excluded to avoid NaN-filled rows.

Step 3 — Train
^^^^^^^^^^^^^^^

Wrap the model in a :class:`~openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow` and call ``fit``.

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="quickstart-model",
   )

   fit_result = workflow.fit(dataset)
   print("Training complete. Metrics:", fit_result)

Step 4 — Forecast
^^^^^^^^^^^^^^^^^^

Pass the same (or newer) dataset to ``predict``. The workflow returns a :class:`~openstef_core.datasets.ForecastDataset` containing point forecasts and quantile bands.

.. code-block:: python

   forecasts = workflow.predict(dataset)

   print(type(forecasts))           # ForecastDataset
   print(forecasts.data.head())

Step 5 — Inspect the output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the built-in :class:`~openstef_beam.analysis.plots.ForecastTimeSeriesPlotter` to visualise the result interactively.

.. code-block:: python

   import pandas as pd
   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   # Separate the median forecast and the actual load
   median_forecast = forecasts.data["quantile_P50"]
   measurements = dataset.data["load"]

   plotter = ForecastTimeSeriesPlotter()
   plotter.add_measurements(measurements)
   plotter.add_model("quickstart-model", forecast=median_forecast)

   fig = plotter.plot(title="Quickstart Forecast")
   fig.show()   # opens an interactive Plotly chart

All Five Steps Together
-----------------------

Here is the complete script with no interruptions:

.. code-block:: python

   from datetime import timedelta

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.transforms.feature_pipeline import FeaturePipeline
   from openstef_models.transforms.lags_adder import LagsAdder
   from openstef_models.transforms.transform_pipeline import TransformPipeline
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   # --- Data ---
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       random_seed=42,
   )

   # --- Model ---
   horizons = [timedelta(hours=h) for h in range(1, 25)]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       preprocessing=FeaturePipeline(
           transforms=[
               LagsAdder(
                   history_available=timedelta(days=14),
                   horizons=horizons,
                   target_column="load",
               ),
           ]
       ),
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=timedelta(days=14),
   )

   # --- Train ---
   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart-model")
   workflow.fit(dataset)

   # --- Forecast ---
   forecasts = workflow.predict(dataset)

   # --- Visualise ---
   plotter = ForecastTimeSeriesPlotter()
   plotter.add_measurements(dataset.data["load"])
   plotter.add_model("quickstart-model", forecast=forecasts.data["quantile_P50"])
   plotter.plot(title="Quickstart Forecast").show()

What You Just Built
-------------------

Running the script above exercises the core OpenSTEF library pattern:

- **Data** — a ``TimeSeriesDataset`` holding load and weather features at a fixed sample interval.
- **Model** — a ``ForecastingModel`` composing preprocessing, a forecaster, and postprocessing into a single object.
- **Workflow** — a ``CustomForecastingWorkflow`` that manages the fit/predict lifecycle and can be extended with callbacks (logging, MLflow, model selection).
- **Output** — a ``ForecastDataset`` with probabilistic forecasts (quantiles) ready for downstream use.

Next Steps
----------

- :doc:`first_forecast` — the same workflow explained step by step, with real data and weather features.
- :doc:`backtesting` — evaluate your model honestly by replaying it over historical data.
- :doc:`advanced_customization` — swap in your own forecaster, add custom transforms, or wire up MLflow tracking.