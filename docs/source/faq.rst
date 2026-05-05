FAQ
===

This FAQ covers the most common questions from new OpenSTEF users — from understanding what the library does, to setting it up and making your first forecast. If you don't find your answer here, check the :doc:`getting_started` guide or the :doc:`api/index`.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is a Python library for training and running machine learning models that predict energy load and generation over short time horizons — typically from 15 minutes up to 48 hours ahead.

   It provides end-to-end pipelines for feature engineering, model training, hyperparameter optimisation, backtesting, and generating operational forecasts. The library is designed to be embedded in your own application or scheduling infrastructure; it does not run as a standalone service.

.. dropdown:: What does "short-term" mean in this context?
   :icon: question

   Short-term forecasting in OpenSTEF refers to horizons ranging from a single 15-minute interval up to roughly 48 hours into the future. The library is optimised for this window because it is the most operationally relevant range for grid operators, energy traders, and balance-responsible parties who need to act on near-future load or generation values.

   Longer-horizon (day-ahead, week-ahead) and very-short-term (seconds) forecasting are outside the library's primary design scope.

.. dropdown:: Who is OpenSTEF built for?
   :icon: question

   OpenSTEF is aimed at:

   - **Data scientists and ML engineers** who want a production-ready forecasting framework without building feature pipelines from scratch.
   - **Energy companies and grid operators** that need repeatable, auditable forecasts for multiple assets (substations, wind farms, solar parks, etc.).
   - **Researchers** who want a well-structured baseline for energy forecasting experiments.

   The library is part of the LF Energy ecosystem and is used in production by energy network operators.

.. dropdown:: What makes OpenSTEF different from a generic ML library?
   :icon: light-bulb

   Several things are specific to the energy-forecasting domain:

   - **Domain-aware feature engineering** — automatic generation of lag features, calendar features (hour-of-day, day-of-week, holidays), and weather-derived features (wind power curves, irradiance corrections).
   - **Prediction jobs** — a ``PredictionJobDataClass`` captures everything about a forecasting asset (location, resolution, horizon, model type) so pipelines are fully reproducible and asset-agnostic.
   - **Confidence intervals** — every forecast includes upper and lower bounds, not just a point estimate.
   - **Energy splitting** — the library can decompose a net load signal into its constituent components (solar, wind, base load).
   - **MLflow integration** — trained models are versioned and stored via MLflow out of the box.

----

Installation and Requirements
------------------------------

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   Install from PyPI with pip:

   .. code-block:: python

      pip install openstef

   For development or to run the example notebooks, clone the repository and install with the optional extras:

   .. code-block:: python

      pip install "openstef[dev]"

   Python 3.9 or later is required.

.. dropdown:: What are the main dependencies?
   :icon: checklist

   OpenSTEF's core runtime dependencies include:

   - **pandas** and **numpy** — data manipulation and numerical computation.
   - **scikit-learn** — base classes, preprocessing, and model selection utilities.
   - **XGBoost**, **LightGBM**, and **scikit-learn regressors** — the supported model backends.
   - **optuna** — automated hyperparameter optimisation.
   - **MLflow** — model serialisation and experiment tracking.
   - **networkx** — dependency graph resolution between prediction jobs.

   You do not need to install these individually; they are declared as package dependencies and installed automatically.

.. dropdown:: Do I need a database to use OpenSTEF?
   :icon: question

   No. The core library works entirely with ``pandas`` DataFrames passed directly to pipeline functions. A database connector (``openstef-dbc``) exists as a separate package for production deployments where you want to read input data and write forecasts to a persistent store, but it is not required to train a model or generate a forecast.

   .. note::

      If you are evaluating the library, start with the pipeline functions directly and supply your own DataFrames. Introduce ``openstef-dbc`` only when you are ready to operationalise.

----

Models and Forecasting
-----------------------

.. dropdown:: Which ML models does OpenSTEF support?
   :icon: question

   OpenSTEF supports several model types, selected via the ``model`` field of a ``PredictionJobDataClass``:

   - ``"xgb"`` — XGBoost gradient-boosted trees (default and most widely used).
   - ``"lgb"`` — LightGBM gradient-boosted trees.
   - ``"xgb_quantile"`` — XGBoost with quantile regression for native probabilistic output.
   - ``"linear"`` — regularised linear regression (useful as a baseline).
   - ``"linear_quantile"`` — quantile linear regression.

   All models share the same pipeline interface, so switching between them requires only changing the ``model`` field in your prediction job.

.. dropdown:: How do I define a forecasting asset (prediction job)?
   :icon: question

   A prediction job is a ``PredictionJobDataClass`` that describes a single asset and its forecasting configuration:

   .. code-block:: python

      from openstef.data_classes.prediction_job import PredictionJobDataClass
      from openstef.data_classes.model_specifications import ModelSpecificationDataClass

      pj = PredictionJobDataClass(
          id=1,
          name="Substation Amsterdam Noord",
          model="xgb",
          forecast_type="demand",
          train_components=False,
          lat=52.39,
          lon=4.91,
          resolution_minutes=15,
          horizon_minutes=2880,  # 48 hours
      )

      model_specs = ModelSpecificationDataClass(id=1)

   The ``id`` is used to associate stored models and forecasts with this asset.

.. dropdown:: How do I train a model?
   :icon: question

   Use ``train_model_pipeline_core`` for a self-contained training run that does not require a database:

   .. code-block:: python

      from openstef.pipeline.train_model import train_model_pipeline_core
      from openstef.data_classes.prediction_job import PredictionJobDataClass
      from openstef.data_classes.model_specifications import ModelSpecificationDataClass

      pj = PredictionJobDataClass(
          id=1,
          name="My asset",
          model="xgb",
          forecast_type="demand",
          train_components=False,
          lat=52.0,
          lon=5.0,
          resolution_minutes=15,
          horizon_minutes=2880,
      )
      model_specs = ModelSpecificationDataClass(id=1)

      # input_data: DataFrame with a DatetimeIndex and at least a "load" column
      model, report, model_specs, datasets = train_model_pipeline_core(
          pj=pj,
          model_specs=model_specs,
          input_data=input_data,
      )

   ``input_data`` must be a ``pandas.DataFrame`` with a timezone-aware ``DatetimeIndex``. See :doc:`getting_started` for a full worked example including the expected column layout.

.. dropdown:: How do I generate a forecast from a trained model?
   :icon: question

   After training, pass the model and fresh input data to the forecast pipeline:

   .. code-block:: python

      from openstef.pipeline.create_forecast import create_forecast_pipeline_core

      forecast = create_forecast_pipeline_core(
          pj=pj,
          input_data=forecast_input_data,
          model=model,
          model_specs=model_specs,
      )

   The returned ``forecast`` is a ``pandas.DataFrame`` containing point predictions and confidence-interval columns for each forecast horizon.

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   At minimum, ``input_data`` must be a ``pandas.DataFrame`` with:

   - A **timezone-aware DatetimeIndex** at a consistent resolution (e.g. 15 minutes).
   - A **``load`` column** containing the historical target values (in MW).

   For best results, include weather features such as ``radiation``, ``windspeed_100m``, and ``temperature``. OpenSTEF's feature engineering step will automatically derive lag features, calendar features, and weather-based features from whatever columns you provide.

   .. note::

      Missing values in the target column are handled internally, but large continuous gaps in recent history will degrade forecast quality.

.. dropdown:: How does hyperparameter optimisation work?
   :icon: light-bulb

   OpenSTEF uses `optuna <https://optuna.org>`_ to search for optimal hyperparameters during training. The search is triggered automatically inside the training pipeline when no existing model is found or when ``ignore_existing_models=True`` is set.

   You can control the number of trials via the prediction job or model specification. The best parameters found by optuna are stored alongside the model in MLflow so that subsequent training runs can warm-start from a good configuration.

----

Backtesting and Evaluation
---------------------------

.. dropdown:: How do I run a backtest?
   :icon: question

   Use ``train_model_and_forecast_back_test`` to evaluate model performance on historical data using cross-validation folds:

   .. code-block:: python

      from openstef.pipeline.train_create_forecast_backtest import (
          train_model_and_forecast_back_test,
      )
      from openstef.data_classes.model_specifications import ModelSpecificationDataClass

      forecast_df, models, train_sets, val_sets, test_sets = (
          train_model_and_forecast_back_test(
              pj=pj,
              modelspecs=ModelSpecificationDataClass(id=1),
              input_data=input_data,
              training_horizons=[0.25, 24.0],
              n_folds=4,
          )
      )

   The function returns the backtest forecast DataFrame alongside the trained models and the data splits used for each fold, making it straightforward to compute your own error metrics.

.. dropdown:: What forecast horizons should I use for training?
   :icon: light-bulb

   The default training horizons are ``[0.25, 24.0]`` hours (15 minutes and 24 hours). These represent the shortest and longest horizons for which separate feature sets are constructed. You can customise this list to match your operational requirements — for example, adding ``48.0`` if you need a 48-hour-ahead forecast.

   Shorter horizons benefit most from recent lag features, while longer horizons rely more heavily on weather forecasts and calendar patterns.

----

Common Setup Issues
--------------------

.. dropdown:: My forecast DataFrame has NaN values — what's wrong?
   :icon: alert

   NaN values in the forecast output usually indicate one of the following:

   - **Insufficient history** — the feature engineering step requires enough historical rows to compute lag features. Ensure your ``input_data`` covers at least the maximum lag window (typically several days).
   - **Missing weather columns** — if your prediction job is configured to use weather features but the input data does not contain them, those feature columns will be NaN.
   - **Timezone mismatch** — make sure your ``DatetimeIndex`` is timezone-aware and consistent between training and inference data.

   Check the log output for warnings from the feature engineering step; OpenSTEF logs which columns were dropped or imputed.

.. dropdown:: Can I use OpenSTEF without MLflow?
   :icon: question

   Yes. The ``_core`` variants of the pipeline functions (e.g. ``train_model_pipeline_core``, ``create_forecast_pipeline_core``) operate entirely in memory and do not interact with MLflow or any other persistent storage. MLflow is only required when using the higher-level ``train_model_pipeline`` function, which handles loading and saving models to a tracking server.

   For experimentation and testing, always use the ``_core`` functions.

.. dropdown:: How do I add custom features to the model?
   :icon: light-bulb

   You can extend the feature set by adding extra columns to your ``input_data`` DataFrame before passing it to the pipeline. OpenSTEF's feature engineering step will include any additional numeric columns it finds alongside its own automatically generated features.

   For more structured customisation — such as registering a custom feature transformer — see :doc:`feature_engineering`.

.. dropdown:: Where can I find more examples?
   :icon: info

   - :doc:`getting_started` — a step-by-step walkthrough of training and forecasting.
   - :doc:`examples/index` — runnable Jupyter notebooks covering common use cases.
   - :doc:`api/index` — full API reference for all public modules and functions.
   - The `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_ contains additional example scripts under the ``examples/`` directory.