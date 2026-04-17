First Forecast Tutorial
=======================

This page walks you through building a complete short-term energy forecast using
OpenSTEF's custom pipeline approach. You will prepare data, assemble a
``ForecastingModel`` from individual components, train it, generate predictions,
and inspect the results. Each step is explained so you understand *why* it exists,
not just *what* to type.

If you only need a working example in the fewest possible lines, see
:doc:`quickstart` first. Come back here when you want to understand the pieces.

.. note:: [DIAGRAM: Step-by-step flowchart showing the pipeline stages: raw dataset → TransformPipeline (preprocessing transforms: holiday features, lag features, scaling) → ForecastingModel (forecaster) → TransformPipeline (postprocessing transforms: quantile sorting, confidence intervals) → CustomForecastingWorkflow (fit / predict) → ForecastDataset output]

----

Preparing Your Data
-------------------

OpenSTEF works with :class:`~openstef_core.datasets.TimeSeriesDataset` and its
versioned counterpart :class:`~openstef_core.datasets.VersionedTimeSeriesDataset`.
For this tutorial, the built-in synthetic data generator gives you a ready-made
dataset so you can focus on the pipeline itself rather than data wrangling.

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    import numpy as np
    import pandas as pd
    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import LeadTime, Q

    logging.basicConfig(level=logging.INFO)

    # Create a synthetic dataset: 90 days of 15-minute load measurements
    dataset = create_synthetic_forecasting_dataset(
        n_periods=90 * 24 * 4,   # 15-min intervals over 90 days
        freq="15min",
        target_column="load",
    )

    # Split into training and a held-out forecast window
    split_date = dataset.index[-24 * 4]          # last 24 hours for forecasting
    data_train = dataset.loc[:split_date]
    data_forecast = dataset.loc[split_date:]

``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` with a
``DatetimeIndex`` and a ``load`` target column. When working with real data, wrap
your ``pandas.DataFrame`` in a ``TimeSeriesDataset`` directly:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset

    df = pd.read_csv("my_load_data.csv", index_col=0, parse_dates=True)
    dataset = TimeSeriesDataset(df)

.. note::

    OpenSTEF expects the index to be a timezone-aware ``DatetimeIndex`` with a
    consistent frequency. Missing timestamps should be filled or flagged before
    passing data to the pipeline.

----

Building the Preprocessing Pipeline
------------------------------------

The preprocessing pipeline is a :class:`~openstef_core.transforms.TransformPipeline`
— an ordered sequence of :class:`~openstef_core.transforms.Transform` objects.
Each transform is fitted on the training data and then applied consistently at
prediction time. This guarantees that the model never sees information it would
not have in production.

For a typical energy forecast you need at least:

- **Holiday features** — public holidays shift load patterns significantly.
- **Lag features** — yesterday's load at the same hour is a strong predictor.
- **Datetime features** — hour-of-day, day-of-week, and month encode seasonality.
- **Scaling** — many gradient-boosted and linear models converge faster on
  normalised inputs.

.. code-block:: python

    from openstef_core.transforms import TransformPipeline
    from openstef_models.transforms import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
        LagFeatureAdder,
        StandardScaler,
    )

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            DatetimeFeaturesAdder(onehot_encode=False),
            LagFeatureAdder(lags=[timedelta(days=1), timedelta(days=7)]),
            StandardScaler(target_column="load"),
        ]
    )

Transforms are applied **in order**: each one receives the output of the previous
one. The pipeline's ``fit`` method calls ``fit_transform`` on each transform
sequentially, so later transforms can depend on columns added by earlier ones.

----

Choosing a Forecaster
----------------------

The forecaster sits at the heart of the pipeline. It receives the preprocessed
dataset and produces point or probabilistic predictions. OpenSTEF ships several
built-in forecasters; this tutorial uses ``ConstantMedianForecaster`` because it
has no hyperparameters to tune, making it ideal for verifying that the plumbing
works before swapping in a more powerful model.

.. code-block:: python

    from openstef_models.models import ConstantMedianForecaster

    forecaster = ConstantMedianForecaster(target_column="load")

To use a gradient-boosted tree model instead, replace this line with:

.. code-block:: python

    from openstef_models.models import XGBForecaster

    forecaster = XGBForecaster(target_column="load", quantiles=[Q(0.1), Q(0.5), Q(0.9)])

----

Adding Postprocessing
----------------------

Postprocessing transforms run on the raw ``ForecastDataset`` that the forecaster
returns. Common steps include sorting quantile columns so they never cross and
attaching confidence intervals derived from the forecast standard deviation.

.. code-block:: python

    from openstef_models.transforms import QuantileSorter, ConfidenceIntervalApplicator

    postprocessing = TransformPipeline(
        transforms=[
            QuantileSorter(),
            ConfidenceIntervalApplicator(
                quantiles=[Q(0.1), Q(0.5), Q(0.9)],
                add_quantiles_from_std=False,
            ),
        ]
    )

----

Assembling the ForecastingModel
--------------------------------

:class:`~openstef_models.models.ForecastingModel` combines preprocessing,
forecaster, and postprocessing into a single object that exposes ``fit`` and
``predict``. This is the unit you store, version, and deploy.

.. code-block:: python

    from openstef_models.models.forecasting_model import ForecastingModel

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=forecaster,
        postprocessing=postprocessing,
        target_column="load",
    )

``ForecastingModel`` is intentionally thin: it delegates all logic to the
transforms and forecaster you provide. This makes it straightforward to swap
components without rewriting orchestration code.

----

Wrapping in a Workflow
-----------------------

:class:`~openstef_models.workflows.CustomForecastingWorkflow` adds model
persistence and lifecycle callbacks on top of ``ForecastingModel``. It is the
recommended entry point for training and prediction because it handles saving the
fitted model to disk (or MLflow) automatically.

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )
    from openstef_models.storage import LocalModelStorage

    storage = LocalModelStorage(path=Path("./models"))

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        run_name="tutorial_run",
        storage=storage,
    )

``LocalModelStorage`` serialises the fitted workflow to a directory on disk.
After training you can reload it with ``storage.load("my_first_forecast")`` and
call ``predict`` without re-fitting.

----

Training the Model
-------------------

Call ``fit`` with your training dataset. The workflow fits the preprocessing
pipeline, trains the forecaster, and then saves the fitted model via the storage
backend.

.. code-block:: python

    fit_result = workflow.fit(data=data_train)

    print(f"Training complete. Metrics: {fit_result.metrics}")

``fit`` returns a :class:`~openstef_models.models.ModelFitResult` that contains
training and validation metrics. Inspect these to confirm the model learned
something reasonable before moving on to prediction.

.. note::

    ``ForecastingModel.fit`` accepts optional ``data_val`` and ``data_test``
    arguments. Passing a validation split enables early stopping for tree-based
    models and populates the ``val_metrics`` field of ``ModelFitResult``.

----

Generating a Forecast
----------------------

Once the workflow is fitted, call ``predict`` with the forecast window. The
preprocessing transforms are applied using their *fitted* parameters (e.g., the
scaler uses statistics from the training data), so no data leakage occurs.

.. code-block:: python

    forecast: ForecastDataset = workflow.predict(data=data_forecast)

    print(forecast.head())

``predict`` returns a ``ForecastDataset`` — a ``TimeSeriesDataset`` subclass that
always contains at least a ``forecast`` column and, when quantiles were requested,
columns named ``p10``, ``p50``, ``p90`` (or whatever quantiles you configured).

.. note:: [VISUALIZATION: Line chart showing actual load vs. forecast median with shaded quantile band (p10–p90) over the 24-hour forecast horizon]

----

Evaluating the Forecast
------------------------

``ForecastingModel`` exposes a ``score`` method that computes evaluation metrics
on any labelled dataset. Pass the same held-out window you used for prediction:

.. code-block:: python

    metrics = model.score(data=data_forecast)

    print(f"MAE:  {metrics.mae:.3f}")
    print(f"RMSE: {metrics.rmse:.3f}")
    print(f"MAPE: {metrics.mape:.1f}%")

For a more rigorous evaluation across multiple historical periods, see
:doc:`backtesting`. That tutorial shows how to run a rolling-window backtest so
that reported metrics reflect realistic out-of-sample performance rather than a
single held-out window.

----

Putting It All Together
------------------------

The complete script, ready to run:

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.datasets import ForecastDataset, TimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.transforms import TransformPipeline
    from openstef_core.types import LeadTime, Q
    from openstef_models.models import ConstantMedianForecaster
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.storage import LocalModelStorage
    from openstef_models.transforms import (
        ConfidenceIntervalApplicator,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        LagFeatureAdder,
        QuantileSorter,
        StandardScaler,
    )
    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )

    logging.basicConfig(level=logging.INFO)

    # 1. Data
    dataset = create_synthetic_forecasting_dataset(
        n_periods=90 * 24 * 4, freq="15min", target_column="load"
    )
    split_date = dataset.index[-24 * 4]
    data_train, data_forecast = dataset.loc[:split_date], dataset.loc[split_date:]

    # 2. Preprocessing
    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            DatetimeFeaturesAdder(onehot_encode=False),
            LagFeatureAdder(lags=[timedelta(days=1), timedelta(days=7)]),
            StandardScaler(target_column="load"),
        ]
    )

    # 3. Postprocessing
    postprocessing = TransformPipeline(
        transforms=[
            QuantileSorter(),
            ConfidenceIntervalApplicator(
                quantiles=[Q(0.1), Q(0.5), Q(0.9)],
                add_quantiles_from_std=False,
            ),
        ]
    )

    # 4. Model
    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(target_column="load"),
        postprocessing=postprocessing,
        target_column="load",
    )

    # 5. Workflow with local storage
    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        run_name="tutorial_run",
        storage=LocalModelStorage(path=Path("./models")),
    )

    # 6. Train
    fit_result = workflow.fit(data=data_train)
    print("Fit metrics:", fit_result.metrics)

    # 7. Predict
    forecast: ForecastDataset = workflow.predict(data=data_forecast)
    print(forecast.head())

    # 8. Evaluate
    metrics = model.score(data=data_forecast)
    print(f"RMSE: {metrics.rmse:.3f}  MAPE: {metrics.mape:.1f}%")

----

Next Steps
----------

- **Backtesting** — evaluate your model across many historical windows rather
  than a single split: :doc:`backtesting`.
- **Advanced customisation** — write your own transforms, forecasters, and
  callbacks: :doc:`advanced_customization`.
- **Installation** — if you haven't set up your environment yet: :doc:`installation`.