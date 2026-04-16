Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with OpenSTEF from scratch. By the end, you will have loaded time series data, configured a preprocessing pipeline, trained a model, generated predictions, and evaluated the results — with a clear explanation of *why* each step exists, not just *how* to do it.

If you just want the shortest possible working example, see :doc:`quickstart`. For comparing multiple models against each other, see :doc:`backtesting`. For customising the pipeline beyond what is shown here, see :doc:`advanced_customization`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF is a library that structures the forecasting workflow as a pipeline of composable objects. The central class is ``ForecastingModel``, which wires together three stages:

- **Preprocessing** — a ``TransformPipeline`` that turns raw time series into model-ready features.
- **Forecasting** — a fitted estimator that maps features to predictions.
- **Postprocessing** — a second ``TransformPipeline`` that refines raw model output into a final ``ForecastDataset``.

All data flows through ``TimeSeriesDataset``, a thin wrapper around a pandas ``DataFrame`` that enforces a timestamp index, tracks the sample interval, and carries optional versioning metadata (availability times and forecast horizons). Understanding this object is the key to using the library fluently.

Step 1 — Prepare Your Data
--------------------------

Every OpenSTEF pipeline starts with a ``TimeSeriesDataset``. The simplest way to create one is to build a pandas ``DataFrame`` with a ``DatetimeIndex`` and pass it to the constructor.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Simulate two years of hourly load measurements plus a weather feature
    index = pd.date_range("2023-01-01", periods=17_520, freq="1h")

    rng = pd.np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "load": 200 + 50 * pd.np.sin(2 * pd.np.pi * index.hour / 24)
            + rng.normal(0, 10, len(index)),
            "temperature": 10 + 8 * pd.np.sin(2 * pd.np.pi * index.dayofyear / 365)
            + rng.normal(0, 2, len(index)),
        },
        index=index,
    )
    df.index.name = "timestamp"

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(hours=1))
    print(dataset)

The ``sample_interval`` argument tells the library how far apart consecutive rows are. OpenSTEF uses this to validate lag features and to align multi-horizon predictions correctly. If your data has gaps or irregular spacing, set ``check_frequency=True`` to surface problems early rather than silently producing incorrect features.

.. note::

   The target column defaults to ``"load"``. If your measurement column has a different name, you will configure ``target_column`` on the model in Step 3.

Step 2 — Configure Feature Engineering
---------------------------------------

Raw load measurements alone are rarely sufficient for accurate forecasting. OpenSTEF's preprocessing stage is a ``TransformPipeline`` — an ordered list of transforms applied sequentially to the dataset before training or prediction.

The most important transform for energy forecasting is the lag transform. Energy consumption has strong temporal autocorrelation: yesterday's peak is a strong predictor of today's, and the load from the same hour last week is even more informative. OpenSTEF's lag implementation is *availability-aware*: it shifts timestamps forward so that a lag feature only uses data that would genuinely have been available at prediction time, preventing data leakage.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.transforms import LagTransform, CalendarFeatureTransform
    from openstef_core.pipelines import TransformPipeline

    preprocessing = TransformPipeline(
        transforms=[
            LagTransform(
                columns=["load"],
                lags=[
                    timedelta(hours=24),   # same hour yesterday
                    timedelta(hours=48),   # same hour two days ago
                    timedelta(days=7),     # same hour last week
                ],
            ),
            CalendarFeatureTransform(),    # hour-of-day, day-of-week, month
        ]
    )

.. warning::

   Lag transforms introduce ``NaN`` values at the start of the dataset — a 7-day lag leaves the first 168 rows incomplete. You *must* set ``cutoff_history`` on the model (Step 3) to exclude these rows from training. Failing to do so will silently corrupt your training data.

Step 3 — Build and Configure the Model
----------------------------------------

``ForecastingModel`` is the main entry point for training and prediction. It accepts a forecaster (the underlying estimator), the preprocessing pipeline you built above, and a handful of configuration parameters.

.. code-block:: python

    from openstef_models.models.forecasting import ForecastingModel
    from openstef_models.models.forecasting.xgb_forecaster import XGBForecaster
    from openstef_core.types import LeadTime

    forecaster = XGBForecaster(
        horizons=[LeadTime.from_string("PT36H")],  # forecast up to 36 hours ahead
    )

    model = ForecastingModel(
        forecaster=forecaster,
        preprocessing=preprocessing,
        target_column="load",
        cutoff_history=timedelta(days=7),  # matches the longest lag above
    )

The ``cutoff_history`` parameter is critical. It tells the model to discard the first 7 days of training data — exactly the period where the 7-day lag feature would be ``NaN``. Set this to match the longest lag in your preprocessing pipeline.

``LeadTime.from_string("PT36H")`` uses ISO 8601 duration notation. A 36-hour lead time means the model will produce predictions for every hour from now up to 36 hours into the future.

Step 4 — Train the Model
------------------------

Call ``fit()`` with your dataset. Optionally pass separate validation and test datasets; if you omit them, the library's built-in ``DataSplitter`` handles the split automatically.

.. code-block:: python

    # Use the first 80 % of data for training, hold out the rest for evaluation
    split_point = int(len(df) * 0.8)
    train_df = df.iloc[:split_point]
    test_df  = df.iloc[split_point:]

    train_dataset = TimeSeriesDataset(train_df, sample_interval=timedelta(hours=1))
    test_dataset  = TimeSeriesDataset(test_df,  sample_interval=timedelta(hours=1))

    fit_result = model.fit(data=train_dataset, data_test=test_dataset)

``fit()`` returns a ``ModelFitResult`` that bundles the training, validation, and test metrics alongside the processed input datasets. You can inspect it immediately to check whether training went well before moving on to prediction.

.. code-block:: python

    print("Training metrics:", fit_result.metrics_train)
    print("Test metrics:    ", fit_result.metrics_test)

Step 5 — Generate a Forecast
-----------------------------

Once the model is fitted, call ``predict()`` with the data the model needs to construct its lag features. The ``forecast_start`` argument sets the boundary between historical context (used to build features) and the future horizon (what the model predicts).

.. code-block:: python

    from datetime import datetime, timezone

    # Predict from the end of the test period onward
    forecast_start = test_df.index[-1]

    forecast = model.predict(data=test_dataset, forecast_start=forecast_start)

    # forecast is a ForecastDataset — access predictions as a DataFrame
    print(forecast.data.head())

``predict()`` runs the full pipeline internally: it calls ``prepare_input()`` to apply preprocessing, passes the result to the underlying forecaster, and then applies postprocessing. The returned ``ForecastDataset`` contains the point predictions together with any quantile estimates the forecaster produces.

.. note::

   ``predict()`` raises ``NotFittedError`` if called before ``fit()``. The ``model.is_fitted`` property lets you check this programmatically.

Step 6 — Evaluate the Results
------------------------------

``score()`` computes evaluation metrics by running prediction over a dataset that contains ground-truth target values and comparing the output against them. It returns a ``SubsetMetric`` object that breaks performance down by lead time, availability time, and rolling window.

.. code-block:: python

    metrics = model.score(data=test_dataset)
    print(metrics)

For a deeper look at how to compare models systematically over historical periods, see :doc:`backtesting`. That tutorial builds directly on the workflow shown here and introduces the ``EvaluationPipeline`` and ``EvaluationConfig`` classes.

Understanding Feature Contributions
-------------------------------------

One of the most useful diagnostic tools in OpenSTEF is ``predict_contributions()``. It returns a ``TimeSeriesDataset`` where each column corresponds to a feature and each value is that feature's contribution to the prediction at that timestep. This is invaluable for understanding *why* the model produced a particular forecast.

.. code-block:: python

    contributions = model.predict_contributions(
        data=test_dataset,
        forecast_start=forecast_start,
    )
    # Each column is a feature; values are additive contributions to the prediction
    print(contributions.data.head())

.. note::

   ``predict_contributions()`` is only available when the underlying forecaster implements ``ContributionsMixin``. Check ``model.get_explainable_components()`` to see which parts of the model support this.

Putting It All Together
------------------------

The complete workflow in one block:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import LagTransform, CalendarFeatureTransform
    from openstef_core.pipelines import TransformPipeline
    from openstef_models.models.forecasting import ForecastingModel
    from openstef_models.models.forecasting.xgb_forecaster import XGBForecaster
    from openstef_core.types import LeadTime

    # 1. Load data
    index = pd.date_range("2023-01-01", periods=17_520, freq="1h")
    df = pd.DataFrame({"load": 200.0, "temperature": 10.0}, index=index)
    df.index.name = "timestamp"

    # 2. Feature engineering pipeline
    preprocessing = TransformPipeline(
        transforms=[
            LagTransform(columns=["load"], lags=[timedelta(hours=24), timedelta(days=7)]),
            CalendarFeatureTransform(),
        ]
    )

    # 3. Configure model
    model = ForecastingModel(
        forecaster=XGBForecaster(horizons=[LeadTime.from_string("PT36H")]),
        preprocessing=preprocessing,
        target_column="load",
        cutoff_history=timedelta(days=7),
    )

    # 4. Split and train
    split = int(len(df) * 0.8)
    train_ds = TimeSeriesDataset(df.iloc[:split], sample_interval=timedelta(hours=1))
    test_ds  = TimeSeriesDataset(df.iloc[split:],  sample_interval=timedelta(hours=1))
    fit_result = model.fit(data=train_ds, data_test=test_ds)

    # 5. Predict
    forecast = model.predict(data=test_ds)

    # 6. Evaluate
    metrics = model.score(data=test_ds)
    print(metrics)

Next Steps
----------

You now have a working end-to-end forecast. From here:

- **Backtesting** — evaluate your model over a long historical window to get statistically robust performance estimates: :doc:`backtesting`.
- **Advanced customisation** — write your own transforms, swap in a different forecaster, or configure postprocessing: :doc:`advanced_customization`.
- **Installation** — if you hit import errors while following this tutorial, revisit the dependency setup: :doc:`installation`.