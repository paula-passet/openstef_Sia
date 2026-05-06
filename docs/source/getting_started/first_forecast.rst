Your First Forecast
===================

This page walks you through building a complete short-term energy forecast using
OpenSTEF's custom pipeline approach. You will prepare a dataset, configure a
:class:`ForecastingModel` with preprocessing and postprocessing transforms, train
it, generate predictions, and inspect the results. Each step is explained so you
understand *why* it exists, not just *what* to type.

If you only need a minimal working example to verify your installation, see
:doc:`quickstart` first. For evaluating a trained model on historical data, see
:doc:`backtesting`. To build your own transforms and forecasters from scratch, see
:doc:`advanced_customization`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

----

Preparing Your Data
-------------------

OpenSTEF expects time series data wrapped in a
:class:`~openstef_core.datasets.VersionedTimeSeriesDataset`. This structure tracks
*when* each observation became available, which matters for realistic training and
backtesting — the model only sees data that would have been available at prediction
time.

The quickest way to get started is with the built-in synthetic dataset generator:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.datasets import VersionedTimeSeriesDataset

    # 9 months of hourly data with wind, temperature, and radiation features
    raw = create_synthetic_forecasting_dataset(
        sample_interval=timedelta(hours=1),
        include_atmosphere=True,
    )

    # Wrap in a VersionedTimeSeriesDataset so the pipeline can reason about
    # data availability at each horizon
    dataset = VersionedTimeSeriesDataset.from_dataframe(
        raw.data,
        sample_interval=timedelta(hours=1),
    )

    print(dataset.feature_names)   # ['load', 'wind_speed', 'temperature', ...]

For real data, replace ``raw.data`` with your own :class:`pandas.DataFrame` that
has a :class:`~pandas.DatetimeIndex` and at least a ``load`` column (the
forecasting target).

.. note::

   ``VersionedTimeSeriesDataset.from_dataframe`` is a convenience constructor.
   For multi-source datasets where different columns arrive at different times,
   compose multiple :class:`~openstef_core.datasets.TimeSeriesDataset` parts
   directly — see the API reference for details.

----

Configuring the Preprocessing Pipeline
---------------------------------------

Raw time series data is rarely ready for a model. OpenSTEF uses a
:class:`~openstef_core.transforms.TransformPipeline` — an ordered list of
transforms that are fitted and applied sequentially. Each transform has a single
responsibility, making the pipeline easy to reason about and extend.

A typical preprocessing pipeline for energy forecasting includes:

- **Feature selection** — drop columns the model should not see.
- **Lag features** — add historical load values at relevant offsets (e.g. 1 h, 24 h, 168 h).
- **Calendar features** — encode holidays, time-of-day, and day-of-week.
- **Scaling** — normalise inputs so gradient-based models converge reliably.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.transforms import TransformPipeline
    from openstef_models.transforms import (
        LagsAdder,
        HolidayAdder,
        StandardScalerTransform,
        Selector,
    )

    horizons = [timedelta(hours=h) for h in range(1, 25)]  # 1–24 h ahead

    preprocessing = TransformPipeline(
        transforms=[
            # Keep only the columns the model needs
            Selector(selection=["load", "wind_speed", "temperature", "radiation"]),
            # Add lag features: 1 h, 24 h, and 168 h (one week) back
            LagsAdder(
                history_available=timedelta(days=7),
                horizons=horizons,
                target_column="load",
            ),
            # Encode public holidays for the Netherlands
            HolidayAdder(country="NL"),
            # Zero-mean, unit-variance scaling fitted on training data only
            StandardScalerTransform(),
        ]
    )

The pipeline's ``fit`` method is called once on training data; ``transform`` is
then applied to both training and prediction data. OpenSTEF handles this split
automatically when you use :class:`~openstef_models.workflows.CustomForecastingWorkflow`.

----

Choosing a Forecaster
---------------------

The forecaster sits at the heart of the pipeline. It receives the preprocessed
feature matrix and returns probabilistic predictions. For this tutorial, use
:class:`~openstef_models.models.ConstantMedianForecaster` — a simple baseline that
predicts the historical median load for each horizon. It trains instantly and
produces sensible output, making it ideal for verifying your pipeline before
switching to a gradient-boosted or neural-network model.

.. code-block:: python

    from openstef_models.models import ConstantMedianForecaster

    forecaster = ConstantMedianForecaster()

To swap in a more powerful model later, replace this line with, for example,
``XGBForecaster()`` or ``LightGBMForecaster()`` — the rest of the pipeline stays
identical.

----

Assembling the ForecastingModel
--------------------------------

:class:`~openstef_models.models.ForecastingModel` is the container that binds
preprocessing, the forecaster, and postprocessing together. It also owns the
train/validation split logic and optional evaluation metrics.

.. code-block:: python

    from openstef_models.models import ForecastingModel
    from openstef_models.transforms import (
        QuantileSorter,
        ConfidenceIntervalApplicator,
        TransformPipeline,
    )

    quantiles = [0.05, 0.25, 0.50, 0.75, 0.95]

    postprocessing = TransformPipeline(
        transforms=[
            # Guarantee quantile monotonicity (q05 ≤ q25 ≤ … ≤ q95)
            QuantileSorter(),
            # Convert standard-deviation output to named quantile columns
            ConfidenceIntervalApplicator(quantiles=quantiles),
        ]
    )

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=forecaster,
        postprocessing=postprocessing,
        target_column="load",
        horizons=horizons,
    )

The postprocessing step is where raw model output is shaped into the
:class:`~openstef_core.datasets.ForecastDataset` that downstream consumers expect.
:class:`~openstef_models.transforms.QuantileSorter` prevents quantile crossing —
a common artefact when quantiles are predicted independently.

----

Training with CustomForecastingWorkflow
----------------------------------------

:class:`~openstef_models.workflows.CustomForecastingWorkflow` wraps the model with
lifecycle management: it calls ``fit``, optionally persists the trained model, and
fires callbacks (e.g. for MLflow logging). For a first forecast you can use it
without any callbacks or storage.

.. code-block:: python

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.storage import LocalModelStorage
    from pathlib import Path

    storage = LocalModelStorage(path=Path("./models"))

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=storage,
    )

    # fit() trains the model and saves it to ./models/my_first_forecast/
    fit_result = workflow.fit(dataset)

    print(f"Training MAE: {fit_result.metrics['mae']:.3f} MW")

``fit_result`` contains training and validation metrics so you can immediately
check whether the model learned anything useful before generating predictions.

.. note::

   ``LocalModelStorage`` saves the serialised model to disk. On the next call to
   ``workflow.fit``, the workflow can optionally reload the previous model and
   compare metrics before deciding whether to replace it — controlled by the
   ``model_reuse_enable`` flag. This is covered in :doc:`advanced_customization`.

----

Generating Predictions
-----------------------

Once the workflow is fitted, call ``predict`` with a dataset that covers the
prediction window. The dataset must include the same feature columns used during
training, but the ``load`` column can be ``NaN`` for future timestamps — the model
will fill it in.

.. code-block:: python

    from datetime import datetime, timezone

    # Slice the last 48 hours of the dataset as the prediction input
    # (in production this would be live feature data)
    prediction_input = dataset  # workflow internally selects the relevant window

    forecast: ForecastDataset = workflow.predict(prediction_input)

    # forecast.data is a DataFrame with columns:
    #   quantile_p05, quantile_p25, quantile_p50, quantile_p75, quantile_p95
    print(forecast.data.head())

.. note:: [VISUALIZATION: Line chart showing the 24-hour ahead probabilistic forecast: median line (p50) with shaded bands for the p25–p75 and p05–p95 intervals, plotted against actual load values]

The returned :class:`~openstef_core.datasets.ForecastDataset` is a validated
wrapper around a :class:`~pandas.DataFrame`. Its index is a
:class:`~pandas.DatetimeIndex` and each quantile column is guaranteed to be
monotonically ordered.

----

Evaluating the Forecast
------------------------

A quick sanity check compares the median prediction against actuals using mean
absolute error (MAE):

.. code-block:: python

    import pandas as pd

    actuals = dataset.data["load"]
    predicted_median = forecast.data["quantile_p50"]

    # Align on the shared index
    aligned = pd.concat([actuals, predicted_median], axis=1).dropna()
    aligned.columns = ["actual", "predicted"]

    mae = (aligned["actual"] - aligned["predicted"]).abs().mean()
    print(f"MAE: {mae:.3f} MW")

For a rigorous evaluation across multiple time windows and lead times, use the
dedicated backtesting workflow described in :doc:`backtesting`. That approach
avoids data leakage by ensuring the model is never evaluated on data it was
trained on.

----

Putting It All Together
------------------------

Here is the complete script from this tutorial, ready to run:

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    import pandas as pd

    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.transforms import TransformPipeline
    from openstef_models.models import ConstantMedianForecaster, ForecastingModel
    from openstef_models.storage import LocalModelStorage
    from openstef_models.transforms import (
        ConfidenceIntervalApplicator,
        HolidayAdder,
        LagsAdder,
        QuantileSorter,
        Selector,
        StandardScalerTransform,
    )
    from openstef_models.workflows import CustomForecastingWorkflow

    logging.basicConfig(level=logging.INFO)

    # --- 1. Data ---
    horizons = [timedelta(hours=h) for h in range(1, 25)]
    raw = create_synthetic_forecasting_dataset(
        sample_interval=timedelta(hours=1),
        include_atmosphere=True,
    )
    dataset = VersionedTimeSeriesDataset.from_dataframe(
        raw.data, sample_interval=timedelta(hours=1)
    )

    # --- 2. Preprocessing ---
    preprocessing = TransformPipeline(
        transforms=[
            Selector(selection=["load", "wind_speed", "temperature", "radiation"]),
            LagsAdder(
                history_available=timedelta(days=7),
                horizons=horizons,
                target_column="load",
            ),
            HolidayAdder(country="NL"),
            StandardScalerTransform(),
        ]
    )

    # --- 3. Postprocessing ---
    quantiles = [0.05, 0.25, 0.50, 0.75, 0.95]
    postprocessing = TransformPipeline(
        transforms=[
            QuantileSorter(),
            ConfidenceIntervalApplicator(quantiles=quantiles),
        ]
    )

    # --- 4. Model ---
    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(),
        postprocessing=postprocessing,
        target_column="load",
        horizons=horizons,
    )

    # --- 5. Workflow ---
    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=LocalModelStorage(path=Path("./models")),
    )

    fit_result = workflow.fit(dataset)
    print(f"Training MAE: {fit_result.metrics['mae']:.3f} MW")

    # --- 6. Predict ---
    forecast = workflow.predict(dataset)
    print(forecast.data.head())

----

Next Steps
----------

You now have a working forecast pipeline. From here you can:

- **Improve accuracy** — swap :class:`~openstef_models.models.ConstantMedianForecaster`
  for ``XGBForecaster`` or ``LightGBMForecaster`` and tune hyperparameters.
- **Evaluate rigorously** — run the backtesting workflow to measure performance
  across multiple historical periods without data leakage. See :doc:`backtesting`.
- **Customise transforms** — write your own preprocessing steps by subclassing
  :class:`~openstef_core.transforms.TimeSeriesTransform`. See
  :doc:`advanced_customization`.
- **Scale up** — the same ``ForecastingModel`` can be embedded in an
  ``openstef_beam`` distributed pipeline for forecasting hundreds of assets in
  parallel.