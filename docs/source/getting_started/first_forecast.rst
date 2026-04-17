Your First Forecast
===================

This tutorial walks you through building a short-term energy forecast from scratch using
OpenSTEF's custom pipeline approach. You will prepare a dataset, configure preprocessing
transforms and a forecasting model, train the pipeline, generate predictions, and inspect
the results. Each step explains not just *how* but *why*, so you leave with a mental model
you can adapt to your own data.

If you only need a minimal working example to verify your installation, see
:doc:`quickstart` first. For evaluating a trained model on historical data, see
:doc:`backtesting`. Advanced customisation of transforms and forecasters is covered in
:doc:`advanced_customization`.

.. note:: [DIAGRAM: Step-by-step flowchart showing the full pipeline: raw dataset → TransformPipeline (HolidayFeatureAdder, LagTransform, StandardScaler) → ForecastingModel (preprocessing → forecaster → postprocessing) → CustomForecastingWorkflow → fit() / predict() → ForecastDataset]


Overview
--------

The custom pipeline approach gives you explicit control over every stage of the forecast:

- **Dataset** – a ``TimeSeriesDataset`` wrapping your pandas DataFrame.
- **Transforms** – a ``TransformPipeline`` that adds features and scales data before the
  model sees it.
- **Model** – a ``ForecastingModel`` that wires preprocessing, a forecaster, and
  postprocessing together.
- **Workflow** – a ``CustomForecastingWorkflow`` that handles model persistence, callbacks,
  and the fit/predict lifecycle.

These four layers are composable: you can swap any piece without touching the others.


Step 1 – Prepare Your Data
--------------------------

OpenSTEF expects time series data wrapped in a ``TimeSeriesDataset``. The dataset holds a
pandas ``DataFrame`` with a ``DatetimeIndex`` and at minimum a target column (the quantity
you want to forecast, e.g. ``"load"``).

For this tutorial, use the built-in synthetic data generator so you can run the code
immediately without external data:

.. code-block:: python

    import pandas as pd
    import numpy as np
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset

    # Create a synthetic dataset: 90 days of 15-minute load measurements
    versioned = create_synthetic_forecasting_dataset(
        n_periods=90 * 24 * 4,   # 15-min resolution
        target_column="load",
    )
    dataset: TimeSeriesDataset = versioned.dataset

    print(dataset.dataframe.head())

``create_synthetic_forecasting_dataset`` returns a ``VersionedTimeSeriesDataset`` that
bundles the raw data with metadata such as the target column name. Calling ``.dataset``
gives you the underlying ``TimeSeriesDataset``.

When working with real data, construct the dataset directly:

.. code-block:: python

    df = pd.read_csv("my_load_data.csv", index_col=0, parse_dates=True)
    dataset = TimeSeriesDataset(dataframe=df, target_column="load")

.. note::

    The index must be timezone-aware for holiday detection to work correctly. If your
    timestamps are naive, convert them with ``df.index = df.index.tz_localize("Europe/Amsterdam")``
    before wrapping in a ``TimeSeriesDataset``.


Step 2 – Configure the Preprocessing Pipeline
----------------------------------------------

Raw time series data rarely contains the features a model needs. OpenSTEF's
``TransformPipeline`` chains a sequence of ``Transform`` objects, each of which either
adds columns to the dataset or modifies existing ones. Transforms are fitted on training
data and then applied identically to new data at prediction time.

A typical preprocessing pipeline for energy load forecasting includes:

- **HolidayFeatureAdder** – adds a binary flag for public holidays in a given country.
  Holiday patterns are a strong driver of load anomalies.
- **DatetimeFeaturesAdder** – encodes hour-of-day, day-of-week, and month as numeric or
  one-hot features.
- **LagTransform** – adds lagged copies of the target (e.g. load 24 h ago), capturing
  daily periodicity without the model having to learn it implicitly.
- **StandardScaler** – normalises features to zero mean and unit variance, which
  stabilises gradient-based optimisers.

.. code-block:: python

    from pydantic_extra_types.country import CountryAlpha2
    from openstef_core.transforms import TransformPipeline
    from openstef_core.transforms.feature_adders import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
    )
    from openstef_core.transforms.lag import LagTransform
    from openstef_core.transforms.scaling import StandardScaler

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            DatetimeFeaturesAdder(onehot_encode=False),
            LagTransform(lags=[96, 672]),   # 1-day and 1-week lags at 15-min resolution
            StandardScaler(),
        ]
    )

The pipeline is stateful: ``fit()`` learns parameters (e.g. scaler means) from training
data, and ``transform()`` applies them. You never call these methods directly on the
pipeline — the ``ForecastingModel`` in the next step manages that for you.


Step 3 – Build the Forecasting Model
-------------------------------------

``ForecastingModel`` is the central object. It owns three sub-pipelines:

- ``preprocessing`` – the ``TransformPipeline`` from Step 2.
- ``forecaster`` – the actual predictive model (e.g. XGBoost, a linear model, or a
  simple baseline).
- ``postprocessing`` – transforms applied to the raw forecast output, such as sorting
  quantiles or clipping negative values.

.. code-block:: python

    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.forecasters.constant import ConstantMedianForecaster
    from openstef_core.transforms import TransformPipeline
    from openstef_core.transforms.postprocessing import QuantileSorter

    model = ForecastingModel(
        preprocessing=preprocessing,          # from Step 2
        forecaster=ConstantMedianForecaster(),
        postprocessing=TransformPipeline(
            transforms=[QuantileSorter()]
        ),
        target_column="load",
    )

``ConstantMedianForecaster`` is a simple baseline that always predicts the median of the
training target. It is a good sanity-check model: if your real model cannot beat it, your
features or data likely have a problem. Replace it with a more powerful forecaster (e.g.
``XGBForecaster``) once the pipeline is working end-to-end.

.. note::

    ``ForecastingModel`` is not fitted yet at this point. Calling ``model.is_fitted``
    returns ``False``. Fitting happens through the workflow in Step 4.


Step 4 – Set Up the Workflow and Model Storage
----------------------------------------------

``CustomForecastingWorkflow`` wraps the model and adds:

- **Model persistence** via a ``ModelStorage`` backend (local filesystem or MLflow).
- **Callbacks** for logging, metrics, and custom hooks.
- A unified ``fit`` / ``predict`` interface that handles versioning automatically.

For this tutorial, use ``LocalModelStorage`` to save the trained model to disk:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.storage.local import LocalModelStorage

    storage = LocalModelStorage(base_path=Path("./models"))

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=storage,
    )

The ``model_id`` is a string that identifies this forecasting target. The storage backend
uses it to organise saved artefacts on disk.


Step 5 – Train the Model
------------------------

Call ``workflow.fit()`` with your dataset. The workflow splits the data into training,
validation, and test sets internally (using the ``data_splitter`` configured on the
model), fits the preprocessing pipeline, trains the forecaster, and saves the result.

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Wrap the dataset with version metadata required by the workflow
    versioned_dataset = VersionedTimeSeriesDataset(
        dataset=dataset,
        target_column="load",
    )

    fit_result = workflow.fit(data=versioned_dataset)
    print(f"Training MAE: {fit_result.metrics}")

``fit()`` returns a ``ModelFitResult`` containing training and validation metrics. Inspect
these to confirm the model learned something reasonable before proceeding to prediction.

.. note::

    If you see a ``SkipFitting`` exception, the workflow detected that a recently trained
    model already exists in storage and skipped retraining. This is intentional behaviour
    for production pipelines. Pass ``force_refit=True`` to override it during development.


Step 6 – Generate a Forecast
-----------------------------

Once the model is fitted, call ``workflow.predict()`` with a dataset covering the
forecast horizon. The input data must include the same feature columns that were present
during training (excluding the target, which is unknown for future timestamps).

.. code-block:: python

    from datetime import datetime, timezone

    # In practice, supply real future feature data here.
    # For demonstration, reuse the last 48 hours of the training dataset.
    forecast_input = TimeSeriesDataset(
        dataframe=dataset.dataframe.iloc[-48 * 4 :],
        target_column="load",
    )

    forecast: ForecastDataset = workflow.predict(data=forecast_input)
    print(forecast.dataframe.head())

The returned ``ForecastDataset`` contains the predicted values alongside any quantile
columns produced by the postprocessing pipeline. The ``p50`` column holds the median
(point) forecast; ``p10`` and ``p90`` (if configured) give the prediction interval.

.. note:: [VISUALIZATION: Line chart showing actual load vs. p50 forecast with p10–p90 shaded confidence band over a 48-hour horizon]


Step 7 – Evaluate the Forecast
-------------------------------

Use the ``score()`` method to compute evaluation metrics on a labelled dataset — one
where the true target values are known:

.. code-block:: python

    metrics = workflow.model.score(data=forecast_input)
    print(metrics)

For a more thorough evaluation across multiple historical periods, see :doc:`backtesting`.
Backtesting re-runs the full train/predict cycle over a rolling window, giving a
statistically robust picture of model performance.


Putting It All Together
-----------------------

Here is the complete script without the explanatory breaks:

.. code-block:: python

    import logging
    from pathlib import Path
    from datetime import timedelta

    import numpy as np
    import pandas as pd
    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.transforms import TransformPipeline
    from openstef_core.transforms.feature_adders import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
    )
    from openstef_core.transforms.lag import LagTransform
    from openstef_core.transforms.scaling import StandardScaler
    from openstef_core.transforms.postprocessing import QuantileSorter
    from openstef_models.forecasters.constant import ConstantMedianForecaster
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.storage.local import LocalModelStorage

    logging.basicConfig(level=logging.INFO)

    # 1. Data
    versioned = create_synthetic_forecasting_dataset(
        n_periods=90 * 24 * 4,
        target_column="load",
    )

    # 2. Preprocessing
    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            DatetimeFeaturesAdder(onehot_encode=False),
            LagTransform(lags=[96, 672]),
            StandardScaler(),
        ]
    )

    # 3. Model
    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(),
        postprocessing=TransformPipeline(transforms=[QuantileSorter()]),
        target_column="load",
    )

    # 4. Workflow
    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my_first_forecast",
        storage=LocalModelStorage(base_path=Path("./models")),
    )

    # 5. Train
    fit_result = workflow.fit(data=versioned)
    print("Fit metrics:", fit_result.metrics)

    # 6. Predict
    forecast_input = TimeSeriesDataset(
        dataframe=versioned.dataset.dataframe.iloc[-48 * 4 :],
        target_column="load",
    )
    forecast = workflow.predict(data=forecast_input)
    print(forecast.dataframe.head())

    # 7. Evaluate
    metrics = workflow.model.score(data=forecast_input)
    print("Score:", metrics)


Next Steps
----------

- **Swap the forecaster** – replace ``ConstantMedianForecaster`` with ``XGBForecaster``
  or another model from ``openstef_models.forecasters`` to improve accuracy.
- **Add more transforms** – explore the full transform catalogue in
  :doc:`advanced_customization` to add weather features, outlier removal, or custom
  feature engineering.
- **Evaluate rigorously** – run a rolling backtest over months of historical data using
  the workflow described in :doc:`backtesting`.
- **Scale up** – the same ``CustomForecastingWorkflow`` runs inside Apache Beam pipelines
  for large-scale parallel forecasting across many grid assets.