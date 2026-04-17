Your First Forecast
===================

This tutorial walks you through producing a real short-term energy forecast with OpenSTEF from scratch. By the end you will have loaded data, configured a feature-engineering pipeline, trained a model, generated predictions, and evaluated the result — with a clear explanation of *why* each step exists.

If you just want the shortest possible working script, see :doc:`quickstart` first. Come back here when you want to understand what is actually happening.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF structures every forecast around three composable objects:

- **ForecastingModel** — the end-to-end pipeline (preprocessing → forecaster → postprocessing).
- **TimeSeriesDataset** — the data contract that carries your time series through every stage.
- **ForecastDataset** — the output of ``predict()``, containing point forecasts and optional quantile bands.

Understanding these three objects makes the rest of the library straightforward.


Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects data as a ``TimeSeriesDataset``. This object enforces a regular time index and a named target column, which allows every downstream transform to make safe assumptions about the data it receives.

For this tutorial we use the built-in synthetic dataset generator so you can run the code without any external data source:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   # Nine months of hourly data with weather covariates
   data = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       include_atmosphere=True,   # adds temperature, radiation, wind columns
       random_seed=42,
   )

   print(data.sample_interval)   # datetime.timedelta(seconds=3600)
   print(data.data.columns.tolist())

When you bring your own data, construct a ``TimeSeriesDataset`` directly:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.read_csv("my_load_data.csv", index_col=0, parse_dates=True)
   df.index = df.index.tz_localize("UTC")   # index must be timezone-aware

   data = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
   )

.. note::

   The time index **must** be timezone-aware and at a consistent frequency.
   ``TimeSeriesDataset`` will raise an error on construction if the frequency
   is irregular, saving you from silent failures later in the pipeline.


Step 2 — Configure Feature Engineering
---------------------------------------

Raw load measurements alone are rarely enough for a good forecast. OpenSTEF's preprocessing pipeline enriches the dataset with derived features before the model ever sees it.

The two most important transforms for energy forecasting are:

- **HolidayFeatureAdder** — adds binary flags for public holidays in a given country, capturing the demand patterns that differ from normal weekdays.
- **LagsAdder** — creates lag features (e.g. load 24 h ago, 48 h ago, 168 h ago) so the model can learn autocorrelation structure.

You compose these into a ``TransformPipeline``:

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.types import LeadTime
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_core.transforms.pipeline import TransformPipeline

   HORIZONS = [LeadTime(timedelta(hours=h)) for h in [1, 6, 24, 48]]

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=HORIZONS,
               target_column="load",
           ),
       ]
   )

.. note::

   The ``cutoff_history`` parameter on ``ForecastingModel`` (set in Step 3)
   works hand-in-hand with ``LagsAdder``. If your longest lag is 14 days,
   the first 14 days of training data will contain NaN lag values. Setting
   ``cutoff_history=timedelta(days=14)`` tells the model to exclude those
   rows from training automatically.


Step 3 — Build and Train the Model
------------------------------------

``ForecastingModel`` is the central object in OpenSTEF. It wraps your preprocessing pipeline, a forecaster (the actual ML algorithm), and optional postprocessing into a single ``fit()`` / ``predict()`` / ``score()`` interface.

.. code-block:: python

   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_core.transforms.pipeline import TransformPipeline
   from openstef_core.types import Q

   forecaster = XGBoostForecaster(
       horizons=HORIZONS,
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=forecaster,
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=timedelta(days=14),
   )

   # Split data manually: use the last 30 days as a held-out test set
   split_point = data.data.index[-1] - timedelta(days=30)
   data_train = TimeSeriesDataset(
       data=data.data.loc[:split_point],
       sample_interval=data.sample_interval,
   )
   data_test = TimeSeriesDataset(
       data=data.data.loc[split_point:],
       sample_interval=data.sample_interval,
   )

   fit_result = model.fit(data=data_train, data_test=data_test)

``fit()`` returns a ``ModelFitResult`` that contains the training, validation, and test metrics alongside the transformed input datasets. It is worth inspecting before moving on:

.. code-block:: python

   # ModelFitResult carries metrics for each data split
   print(fit_result.metrics_train)
   print(fit_result.metrics_test)

If the test metrics look unreasonable, revisit your feature configuration or check for data quality issues before generating production forecasts. See :doc:`backtesting` for a systematic approach to model comparison.


Step 4 — Generate a Forecast
------------------------------

Once the model is fitted, call ``predict()`` with the data covering the forecast window. The method internally re-applies all preprocessing transforms (using the parameters learned during ``fit()``) before passing the data to the underlying forecaster.

.. code-block:: python

   forecast: ForecastDataset = model.predict(data=data_test)

   # The median forecast is available as a pandas Series
   print(forecast.data[["load_q0.5"]].head())

``ForecastDataset`` contains one column per requested quantile. The 0.5 quantile is the point forecast; the 0.1 and 0.9 quantiles form a prediction interval that captures forecast uncertainty.

.. note::

   ``predict()`` requires that ``fit()`` has been called first. Attempting to
   call ``predict()`` on an unfitted model raises a ``NotFittedError``.


Step 5 — Evaluate the Result
------------------------------

OpenSTEF provides two complementary evaluation paths: programmatic metrics via ``score()`` and visual inspection via ``ForecastTimeSeriesPlotter``.

**Programmatic evaluation**

.. code-block:: python

   metrics = model.score(data=data_test)
   print(metrics)

``score()`` runs ``predict()`` internally and computes the configured evaluation metrics (MAE, RMSE, etc.) at the model's maximum forecast horizon. The returned ``SubsetMetric`` object gives you a structured view of model performance.

**Visual evaluation**

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()

   # Add the ground truth
   _ = plotter.add_measurements(data_test.data["load"])

   # Add the model's median forecast
   _ = plotter.add_model(
       "XGBoost",
       forecast=forecast.data["load_q0.5"],
   )

   fig = plotter.plot(title="First Forecast — Load")
   fig.show()

The resulting interactive plot overlays the actual load against the forecast, with shaded quantile bands showing uncertainty. This makes it immediately obvious whether the model is tracking the right patterns or systematically over- or under-predicting.


Persisting the Model
---------------------

A trained model is only useful if you can reload it later. OpenSTEF's ``LocalModelStorage`` handles serialisation to disk:

.. code-block:: python

   from pathlib import Path
   from openstef_core.storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model=model, model_id="my_first_forecast_model")

   # Later, in a separate process:
   loaded_model = storage.load(model_id="my_first_forecast_model")
   new_forecast = loaded_model.predict(data=data_test)

For production deployments with experiment tracking, ``MLFlowStorage`` is the recommended alternative — see :doc:`advanced_customization` for details.


Putting It All Together
------------------------

Here is the complete, self-contained script combining every step above:

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.transforms.pipeline import TransformPipeline
   from openstef_core.types import LeadTime, Q
   from openstef_core.storage import LocalModelStorage

   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   logging.basicConfig(level=logging.INFO)

   # --- 1. Data ---
   data = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       include_atmosphere=True,
       random_seed=42,
   )

   split_point = data.data.index[-1] - timedelta(days=30)
   data_train = TimeSeriesDataset(
       data=data.data.loc[:split_point],
       sample_interval=data.sample_interval,
   )
   data_test = TimeSeriesDataset(
       data=data.data.loc[split_point:],
       sample_interval=data.sample_interval,
   )

   # --- 2. Feature engineering ---
   HORIZONS = [LeadTime(timedelta(hours=h)) for h in [1, 6, 24, 48]]

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=HORIZONS,
               target_column="load",
           ),
       ]
   )

   # --- 3. Model ---
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=XGBoostForecaster(
           horizons=HORIZONS,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       ),
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=timedelta(days=14),
   )

   fit_result = model.fit(data=data_train, data_test=data_test)
   print("Test metrics:", fit_result.metrics_test)

   # --- 4. Forecast ---
   forecast = model.predict(data=data_test)

   # --- 5. Evaluate ---
   metrics = model.score(data=data_test)
   print("Score:", metrics)

   plotter = ForecastTimeSeriesPlotter()
   _ = plotter.add_measurements(data_test.data["load"])
   _ = plotter.add_model("XGBoost", forecast=forecast.data["load_q0.5"])
   fig = plotter.plot(title="First Forecast")
   fig.show()

   # --- Persist ---
   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model=model, model_id="my_first_forecast_model")


Next Steps
----------

Now that you have a working forecast, the natural next questions are:

- **Is this model actually good?** Use systematic backtesting to measure performance across many time windows — see :doc:`backtesting`.
- **Can I improve accuracy?** Explore custom transforms, alternative model types, and hyperparameter tuning in :doc:`advanced_customization`.
- **How do I integrate this into a production system?** The :doc:`../index` section covers workflow orchestration and model storage options.