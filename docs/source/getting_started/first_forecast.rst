Your First Forecast
===================

This page walks you through building a short-term energy forecast from scratch using
OpenSTEF's custom pipeline approach. You will prepare data, assemble a
``ForecastingModel`` with explicit preprocessing and postprocessing steps, persist it
with ``LocalModelStorage``, and run training and prediction through a
``CustomForecastingWorkflow``.

If you just want the shortest possible path to a working forecast, see
:doc:`quickstart` first. For evaluating a trained model on historical data, see
:doc:`backtesting`. For writing your own transforms and forecasters, see
:doc:`advanced_customization`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

The custom pipeline approach gives you explicit control over every stage of the
forecast. Rather than accepting a preset configuration, you construct each piece
yourself and wire them together. The main objects involved are:

- ``TimeSeriesDataset`` / ``VersionedTimeSeriesDataset`` — the data containers
- ``TransformPipeline`` — an ordered sequence of feature engineering steps
- ``ForecastingModel`` — combines preprocessing, a forecaster, and postprocessing
- ``LocalModelStorage`` — saves and loads versioned model artefacts to disk
- ``CustomForecastingWorkflow`` — the top-level entry point that calls ``fit`` and
  ``predict`` and coordinates storage callbacks

Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects time series data in a ``TimeSeriesDataset``. For this tutorial we
use the built-in synthetic data generator so you can run the code without any
external files.

.. code-block:: python

    import logging
    from pathlib import Path
    from datetime import timedelta

    import numpy as np
    import pandas as pd
    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset

    logging.basicConfig(level=logging.INFO)

    # Create a synthetic dataset covering ~90 days at 15-minute resolution
    dataset: VersionedTimeSeriesDataset = create_synthetic_forecasting_dataset()

    # Inspect what was created
    print(dataset)

``create_synthetic_forecasting_dataset`` returns a ``VersionedTimeSeriesDataset``
that already contains a ``train``, ``validation``, and ``test`` split. When you work
with real data you construct a ``TimeSeriesDataset`` directly from a
``pandas.DataFrame`` with a ``DatetimeIndex`` and pass it to the workflow — the
splitting logic is handled internally.

.. note::

   ``VersionedTimeSeriesDataset`` is the preferred container when you want explicit
   train/val/test splits. For a single contiguous block of data, use
   ``TimeSeriesDataset`` and let the workflow's ``data_splitter`` handle the split.

Step 2 — Build the Preprocessing Pipeline
------------------------------------------

Preprocessing is expressed as a ``TransformPipeline`` — an ordered list of
``Transform`` objects. Each transform is fitted on the output of the previous one,
so the order matters.

.. code-block:: python

    from openstef_core.transforms import TransformPipeline
    from openstef_core.transforms.feature_adders import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
    )
    from openstef_core.transforms.lag import LagTransformer
    from openstef_core.transforms.scaling import StandardScaler

    country_code: CountryAlpha2 = "NL"

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country_code=country_code),  # adds is_holiday column
            DatetimeFeaturesAdder(onehot_encode=False),       # hour, day-of-week, etc.
            LagTransformer(lags=[1, 2, 4, 96]),               # lag features in samples
            StandardScaler(),                                  # zero-mean, unit-variance
        ]
    )

Each transform implements ``fit(data)`` and ``transform(data)``. When the pipeline
is fitted, transforms are applied sequentially and each one sees the already-
transformed output of its predecessor. You never need to call ``fit`` on the
pipeline directly — the ``ForecastingModel`` does that for you during training.

Step 3 — Choose a Forecaster and Postprocessing
------------------------------------------------

The forecaster sits between the preprocessing and postprocessing pipelines inside a
``ForecastingModel``. For this tutorial we use ``ConstantMedianForecaster``, a
simple baseline that predicts the historical median for each time-of-day slot. It
requires no hyperparameter tuning and is a good sanity-check before switching to a
gradient-boosted or neural model.

.. code-block:: python

    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.forecasters.constant import ConstantMedianForecaster
    from openstef_core.transforms import TransformPipeline
    from openstef_core.transforms.postprocessing import QuantileSorter
    from openstef_core.types import Q

    QUANTILES = [Q(0.1), Q(0.5), Q(0.9)]
    TARGET_COLUMN = "load"

    postprocessing = TransformPipeline(
        transforms=[
            QuantileSorter(),  # ensures quantile order is monotone
        ]
    )

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(quantiles=QUANTILES),
        postprocessing=postprocessing,
        target_column=TARGET_COLUMN,
    )

``ForecastingModel`` is the single object you train and call ``predict`` on. Its
``fit`` method runs the preprocessing pipeline, trains the forecaster, and stores
the fitted state. Its ``predict`` method applies the same preprocessing to new data
and then runs the forecaster followed by postprocessing.

Step 4 — Configure Storage and the Workflow
--------------------------------------------

``CustomForecastingWorkflow`` wraps the model and handles persistence. You attach a
``LocalModelStorage`` so that the fitted model is saved to disk after training and
reloaded automatically before prediction.

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )
    from openstef_models.storage import LocalModelStorage

    storage_path = Path("./models")
    storage_path.mkdir(exist_ok=True)

    storage = LocalModelStorage(base_path=storage_path)

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=storage,
    )

The ``model_id`` is used as the key when saving and loading. If you run the workflow
a second time with the same ``model_id``, the stored model is loaded and compared
against the newly trained one before the update is committed — this guards against
accidentally overwriting a better model with a worse one.

Step 5 — Train the Model
------------------------

Call ``fit`` on the workflow, passing the dataset. The workflow splits the data,
runs the full preprocessing pipeline, trains the forecaster, evaluates on the
validation split, and saves the model.

.. code-block:: python

    fit_result = workflow.fit(data=dataset)

    print("Training metrics:", fit_result.metrics)
    print("Model version:  ", fit_result.model_version)

``fit_result`` is a ``ModelFitResult`` dataclass. Its ``metrics`` dictionary
contains evaluation scores (e.g. MAE, RMSE) computed on the held-out validation
set. These are the numbers to watch when you iterate on your pipeline configuration.

.. note::

   If the dataset you pass is a plain ``TimeSeriesDataset`` rather than a
   ``VersionedTimeSeriesDataset``, the workflow uses the ``data_splitter`` attached
   to the ``ForecastingModel`` to create the train/val/test splits automatically.

Step 6 — Generate a Forecast
-----------------------------

Once the model is trained (or loaded from storage), call ``predict``. You pass the
same kind of dataset — the workflow applies preprocessing and returns a
``ForecastDataset`` containing point forecasts and quantile intervals.

.. code-block:: python

    from openstef_core.datasets import ForecastDataset

    forecast: ForecastDataset = workflow.predict(data=dataset)

    # The result is a structured dataset — access the underlying DataFrame:
    print(forecast.data.head())

The ``ForecastDataset`` contains one column per quantile (e.g. ``q0.1``, ``q0.5``,
``q0.9``) plus a ``forecast`` column for the point prediction. The index is a
``DatetimeIndex`` aligned to the original input.

Step 7 — Evaluate and Visualise
--------------------------------

Use the ``score`` method on the model for a quick numeric evaluation, or plot the
forecast against actuals with ``ForecastTimeSeriesPlotter``.

.. code-block:: python

    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

    # Numeric evaluation on the test split
    metrics = workflow.model.score(data=dataset.test)
    print("Test metrics:", metrics)

    # Visual evaluation
    plotter = ForecastTimeSeriesPlotter()
    fig = plotter.plot(forecast=forecast, actuals=dataset.test)
    fig.show()

.. note:: [VISUALIZATION: Line chart showing actual load (solid line) versus the point forecast (dashed line) with a shaded band between the 10th and 90th quantile intervals, over a 48-hour prediction window]

Putting It All Together
-----------------------

Here is the complete script with all steps in one place:

.. code-block:: python

    import logging
    from pathlib import Path

    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.transforms import TransformPipeline
    from openstef_core.transforms.feature_adders import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
    )
    from openstef_core.transforms.lag import LagTransformer
    from openstef_core.transforms.scaling import StandardScaler
    from openstef_core.transforms.postprocessing import QuantileSorter
    from openstef_core.types import Q

    from openstef_models.forecasters.constant import ConstantMedianForecaster
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.storage import LocalModelStorage
    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )
    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

    logging.basicConfig(level=logging.INFO)

    # --- Data ---
    dataset: VersionedTimeSeriesDataset = create_synthetic_forecasting_dataset()

    # --- Pipeline ---
    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            DatetimeFeaturesAdder(onehot_encode=False),
            LagTransformer(lags=[1, 2, 4, 96]),
            StandardScaler(),
        ]
    )
    postprocessing = TransformPipeline(transforms=[QuantileSorter()])

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(quantiles=[Q(0.1), Q(0.5), Q(0.9)]),
        postprocessing=postprocessing,
        target_column="load",
    )

    # --- Workflow ---
    storage = LocalModelStorage(base_path=Path("./models"))
    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=storage,
    )

    # --- Train ---
    fit_result = workflow.fit(data=dataset)
    print("Validation metrics:", fit_result.metrics)

    # --- Predict ---
    forecast = workflow.predict(data=dataset)
    print(forecast.data.head())

    # --- Plot ---
    fig = ForecastTimeSeriesPlotter().plot(forecast=forecast, actuals=dataset.test)
    fig.show()

Next Steps
----------

You now have a working forecast pipeline. A few natural directions from here:

- **Swap the forecaster** — replace ``ConstantMedianForecaster`` with a gradient-
  boosted or neural model. The rest of the pipeline stays the same.
- **Tune the transforms** — add more lag features, try different scalers, or
  include weather covariates as additional columns in your dataset.
- **Evaluate rigorously** — run the pipeline over a rolling historical window using
  the backtesting utilities described in :doc:`backtesting`.
- **Write custom transforms** — if the built-in transforms do not cover your
  preprocessing needs, see :doc:`advanced_customization` for the ``Transform``
  interface.