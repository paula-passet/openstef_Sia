Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with OpenSTEF from scratch. By the end, you will have loaded data, configured a feature pipeline, trained a model, generated predictions, and evaluated the results — with a clear understanding of what each step does and why it matters.

If you just want the shortest possible working example, see :doc:`quickstart` first. This page goes deeper: it explains the reasoning behind each step and prepares you to adapt the workflow for your own data.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF is a library built around a composable pipeline pattern. Rather than hiding complexity behind a single magic function, it gives you explicit control over each stage:

- **Data preparation** — structure your time series into a ``TimeSeriesDataset``
- **Feature engineering** — attach a ``FeaturePipeline`` that derives lag features, calendar features, and scaling
- **Model configuration** — wrap a forecaster in a ``ForecastingModel`` that handles pre- and post-processing
- **Training** — call ``fit()`` with optional validation and test splits
- **Prediction** — call ``predict()`` to generate a ``ForecastDataset``
- **Evaluation** — call ``score()`` to obtain structured metrics

Each of these objects is independently importable and testable, which makes the library straightforward to integrate into larger systems.

Step 1: Prepare Your Data
--------------------------

OpenSTEF works with ``TimeSeriesDataset``, a thin wrapper around a ``pandas.DataFrame`` that enforces a datetime index, a known sample interval, and a ``load`` target column. For this tutorial, use the built-in synthetic data generator so you can run everything without external data:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   # Nine months of hourly data — enough history for robust lag features
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=30 * 9),
       sample_interval=timedelta(hours=1),
       include_atmosphere=True,   # adds wind, temperature, radiation columns
       random_seed=42,
   )

   print(dataset.data.shape)          # (6552, 4) — rows × columns
   print(dataset.data.columns.tolist())

The ``include_atmosphere=True`` flag adds weather-like covariates. In production you would replace this call with your own data loading logic, as long as the result is a ``TimeSeriesDataset`` with a regular datetime index and a ``load`` column.

.. note::

   OpenSTEF expects a **consistent sample interval** throughout the dataset. Gaps or duplicate timestamps will raise a validation error early, which is intentional — silent interpolation of missing data can silently degrade forecast quality.

Step 2: Split Into Train and Test Sets
---------------------------------------

Before touching the model, set aside a held-out test window. A common convention for energy forecasting is to reserve the final few weeks as the test set, because recent data best reflects current system behaviour:

.. code-block:: python

   from datetime import datetime, timezone

   # Use the last 14 days as a test set
   split_point = dataset.data.index[-1] - timedelta(days=14)

   train_data = dataset.slice_time(end=split_point)
   test_data  = dataset.slice_time(start=split_point)

   print(f"Training samples : {len(train_data.data)}")
   print(f"Test samples     : {len(test_data.data)}")

Keeping the test set completely separate from training — including from any feature-engineering statistics like scaling parameters — is what makes the later evaluation trustworthy.

Step 3: Configure the Feature Pipeline
----------------------------------------

The ``FeaturePipeline`` defines how raw time series columns are transformed into model-ready features. OpenSTEF ships with composable transform blocks. A typical starting configuration includes holiday indicators, lag transforms, and standard scaling:

.. code-block:: python

   from openstef_core.pipeline import FeaturePipeline
   from openstef_core.transforms import HolidayFeatures, LagTransform, StandardScaler
   from pydantic_extra_types.country import CountryAlpha2

   feature_pipeline = FeaturePipeline(
       transforms=[
           # Calendar and public-holiday flags for the Netherlands
           HolidayFeatures(country=CountryAlpha2("NL")),

           # Lag features: load values from 1 h, 24 h, and 168 h (1 week) ago
           LagTransform(lags=[1, 24, 168]),

           # Zero-mean, unit-variance scaling applied per column
           StandardScaler(),
       ]
   )

**Why these transforms?**

- *Holiday features* capture demand anomalies on public holidays that calendar day-of-week features alone cannot explain.
- *Lag transforms* give the model direct access to recent history. The 168-hour lag encodes the weekly seasonal pattern, which is dominant in most electricity load profiles.
- *Standard scaling* keeps gradient-based and distance-based learners numerically stable and speeds up convergence.

The pipeline is stateful: ``fit_transform()`` learns scaling parameters from training data, and ``transform()`` applies the same parameters to new data — exactly the same contract as scikit-learn transformers.

Step 4: Configure and Train the Model
---------------------------------------

``ForecastingModel`` is the central object in OpenSTEF. It composes a forecaster (the core ML algorithm) with the feature pipeline and optional post-processing into a single, serialisable unit:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.models import ForecastingModel
   from openstef_core.forecasters import XGBForecaster
   from openstef_core.types import LeadTime, Q

   model = ForecastingModel(
       forecaster=XGBForecaster(),
       feature_pipeline=feature_pipeline,
       max_horizon=LeadTime(timedelta(hours=48)),   # forecast up to 48 h ahead
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],         # median + 80 % interval
   )

Now train it. Pass the training set; optionally provide a validation set so the underlying learner can apply early stopping:

.. code-block:: python

   # Reserve the last 10 % of training data for in-training validation
   val_split = int(len(train_data.data) * 0.9)
   fit_train = train_data.slice_time(end=train_data.data.index[val_split])
   fit_val   = train_data.slice_time(start=train_data.data.index[val_split])

   fit_result = model.fit(
       data=fit_train,
       data_val=fit_val,
   )

   print(f"Model fitted: {model.is_fitted}")

``fit()`` returns a ``ModelFitResult`` that records training diagnostics. The model is now ready to generate forecasts.

.. note::

   ``ForecastingModel`` is designed to be **stateless between calls to** ``predict()``. You can call ``predict()`` repeatedly with different input windows without re-training. Only ``fit()`` mutates the model's internal state.

Step 5: Generate a Forecast
-----------------------------

With a fitted model, call ``predict()`` on any ``TimeSeriesDataset`` that covers the features the model needs. The library handles feature construction internally using the fitted pipeline:

.. code-block:: python

   forecast_dataset = model.predict(data=test_data)

   # forecast_dataset is a ForecastDataset — a TimeSeriesDataset subclass
   # with additional forecast-specific columns
   print(forecast_dataset.data.columns.tolist())
   # e.g. ['forecast_0.1', 'forecast_0.5', 'forecast_0.9', 'load', ...]

The returned ``ForecastDataset`` contains one column per quantile. The ``forecast_0.5`` column is the median (point) forecast; ``forecast_0.1`` and ``forecast_0.9`` form the 80 % prediction interval.

You can also request a specific forecast start time, which is useful when replaying historical windows:

.. code-block:: python

   from datetime import datetime, timezone

   t0 = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
   forecast_at_t0 = model.predict(data=test_data, forecast_start=t0)

Step 6: Evaluate the Forecast
-------------------------------

``score()`` computes structured evaluation metrics against the ground-truth ``load`` column in the dataset. It returns a ``SubsetMetric`` object containing the configured metrics evaluated at the model's maximum horizon:

.. code-block:: python

   metrics = model.score(data=test_data)

   print(metrics.metrics)
   # e.g. {'mae': 12.4, 'rmse': 18.7, 'skill_score': 0.83, ...}

For a visual inspection, OpenSTEF provides ``ForecastTimeSeriesPlotter`` — a built-in plotting utility that renders the forecast alongside actuals and the prediction interval:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(forecast_dataset)
   fig.show()

The plot overlays the median forecast, the shaded uncertainty band, and the observed load, making it easy to spot systematic biases or horizon-dependent degradation at a glance.

.. note::

   Prefer ``model.score()`` over computing metrics manually from the raw arrays. The ``SubsetMetric`` structure is consistent with the output of the backtesting workflow, so you can compare single-run evaluation results directly with backtesting results. See :doc:`backtesting` for details.

Step 7: Persist the Model
--------------------------

A trained model is only useful if you can reload it later. Use ``LocalModelStorage`` for file-based persistence:

.. code-block:: python

   from pathlib import Path
   from openstef_core.storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model, name="my_first_forecast_model")

   # Later, in a separate process:
   loaded_model = storage.load(name="my_first_forecast_model")
   new_forecast = loaded_model.predict(data=test_data)

The storage layer serialises the entire ``ForecastingModel`` — including the fitted feature pipeline and all scaling parameters — so the loaded model produces identical output to the original.

Putting It All Together
------------------------

Here is the complete, self-contained script combining every step above:

.. code-block:: python

   import logging
   from datetime import datetime, timedelta, timezone
   from pathlib import Path

   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.forecasters import XGBForecaster
   from openstef_core.models import ForecastingModel
   from openstef_core.pipeline import FeaturePipeline
   from openstef_core.storage import LocalModelStorage
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.transforms import HolidayFeatures, LagTransform, StandardScaler
   from openstef_core.types import LeadTime, Q
   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   logging.basicConfig(level=logging.INFO)

   # 1. Data
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=30 * 9),
       sample_interval=timedelta(hours=1),
       include_atmosphere=True,
       random_seed=42,
   )

   split_point = dataset.data.index[-1] - timedelta(days=14)
   train_data = dataset.slice_time(end=split_point)
   test_data  = dataset.slice_time(start=split_point)

   # 2. Feature pipeline
   feature_pipeline = FeaturePipeline(
       transforms=[
           HolidayFeatures(country=CountryAlpha2("NL")),
           LagTransform(lags=[1, 24, 168]),
           StandardScaler(),
       ]
   )

   # 3. Model
   model = ForecastingModel(
       forecaster=XGBForecaster(),
       feature_pipeline=feature_pipeline,
       max_horizon=LeadTime(timedelta(hours=48)),
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

   # 4. Train
   val_split = int(len(train_data.data) * 0.9)
   model.fit(
       data=train_data.slice_time(end=train_data.data.index[val_split]),
       data_val=train_data.slice_time(start=train_data.data.index[val_split]),
   )

   # 5. Predict
   forecast = model.predict(data=test_data)

   # 6. Evaluate
   metrics = model.score(data=test_data)
   print(metrics.metrics)

   plotter = ForecastTimeSeriesPlotter()
   plotter.plot(forecast).show()

   # 7. Persist
   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model, name="my_first_forecast_model")

Common Issues
--------------

**Missing columns after feature engineering**
   If ``predict()`` raises a ``KeyError`` about a missing column, the test dataset is likely missing a covariate that was present during training (e.g. ``temperature``). Ensure your inference data has the same columns as your training data before calling ``predict()``.

**Flat or constant forecasts**
   A ``ConstantMedianForecaster`` is useful as a baseline but will produce flat predictions by design. Switch to ``XGBForecaster`` or another learner if you need a model that responds to input features.

**Scaling mismatch**
   Never fit the ``FeaturePipeline`` separately on test data. The pipeline is fitted once inside ``model.fit()`` and the same parameters are applied automatically during ``predict()``.

Next Steps
-----------

Now that you have a working forecast, the natural next steps are:

- :doc:`backtesting` — evaluate your model rigorously across multiple historical windows rather than a single test split
- :doc:`advanced_customization` — replace built-in components with custom forecasters, transforms, or evaluation metrics
- :doc:`../api/index` — full API reference for all classes used in this tutorial