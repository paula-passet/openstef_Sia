FAQ
===

This FAQ covers the most common questions from new users of OpenSTEF — from understanding what the library does and how to install it, to choosing models and structuring your first forecast. If you are looking for step-by-step guidance, see :doc:`getting_started` and the :doc:`user_guide/index`.

----

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for training and running machine learning models that predict energy load and generation over short time horizons — typically from 15 minutes up to 48 hours ahead.

   It is developed under the LF Energy umbrella and is used in production by energy grid operators. The library handles the full forecasting workflow: feature engineering, model training, hyperparameter optimisation, confidence intervals, and forecast generation — all driven by a ``PredictionJobDataClass`` configuration object.

.. dropdown:: What does "short-term" mean in this context?
   :icon: question

   Short-term forecasting in OpenSTEF refers to horizons ranging from a single 15-minute interval up to roughly 48 hours ahead. The default training horizons used internally are ``[0.25, 24.0]`` hours. This distinguishes it from medium-term (days to weeks) or long-term (months to years) energy planning tools.

.. dropdown:: Who is OpenSTEF designed for?
   :icon: question

   OpenSTEF is aimed at:

   - **Data scientists and ML engineers** at energy companies who want a production-ready forecasting framework without building everything from scratch.
   - **Grid operators and DSOs** who need reliable, automated load and generation forecasts.
   - **Researchers** who want a well-structured baseline for experimenting with energy forecasting models.

   You do not need deep expertise in energy systems to get started — familiarity with pandas DataFrames and basic ML concepts is sufficient.

.. dropdown:: What makes OpenSTEF different from a generic ML library?
   :icon: question

   Several things set OpenSTEF apart from using scikit-learn or XGBoost directly:

   - **Energy-domain feature engineering** — automatic generation of lag features, weather-derived features (wind power curves, solar irradiance), calendar features, and more.
   - **Prediction jobs** — a single ``PredictionJobDataClass`` object captures everything needed to train and run a forecast (location, resolution, horizon, model type), making it easy to manage many forecasting points.
   - **Built-in confidence intervals** — forecasts include uncertainty bounds out of the box.
   - **Backtesting pipeline** — ``train_model_and_forecast_back_test`` provides walk-forward validation with minimal boilerplate.
   - **MLflow integration** — models are serialised and tracked via MLflow automatically.

----

Installation & Requirements
----------------------------

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   Install from PyPI using pip:

   .. code-block:: python

      pip install openstef

   For development or to run the examples, clone the repository and install in editable mode:

   .. code-block:: python

      git clone https://github.com/OpenSTEF/openstef.git
      cd openstef
      pip install -e ".[dev]"

   See :doc:`getting_started` for a full walkthrough of the first steps after installation.

.. dropdown:: What are the main dependencies?
   :icon: info

   OpenSTEF's core runtime dependencies include:

   - **pandas** and **numpy** — data manipulation and numerical operations.
   - **scikit-learn** — base classes, preprocessing, and model selection utilities.
   - **XGBoost** and **LightGBM** — the primary gradient-boosting backends.
   - **MLflow** — model serialisation and experiment tracking.
   - **Optuna** — hyperparameter optimisation.
   - **networkx** — dependency graph resolution between prediction jobs.

   All of these are installed automatically when you run ``pip install openstef``.

.. dropdown:: What Python version does OpenSTEF support?
   :icon: info

   OpenSTEF supports **Python 3.9 and above**. Using the latest stable Python 3.x release is recommended for the best compatibility with its dependencies.

.. dropdown:: Do I need a database to use OpenSTEF?
   :icon: question

   No. The core library works entirely with pandas DataFrames — you supply input data and receive forecast DataFrames back. There is no mandatory database dependency in ``openstef`` itself.

   A companion package, ``openstef-dbc``, provides database connectors and a ``TaskContext`` used in production CRON-style deployments. That package is optional and only needed if you want to integrate with an existing operational data infrastructure.

----

Models & Configuration
-----------------------

.. dropdown:: Which model types does OpenSTEF support?
   :icon: question

   OpenSTEF supports several model types, selectable via the ``model`` field of ``PredictionJobDataClass``. The most commonly used are:

   - ``"xgb"`` — XGBoost regressor (default choice for most use cases).
   - ``"lgbm"`` — LightGBM regressor (faster training on large datasets).
   - ``"xgb_quantile"`` — XGBoost with quantile regression for probabilistic forecasts.
   - ``"linear"`` — regularised linear model, useful as a baseline.

   .. code-block:: python

      from openstef.data_classes.prediction_job import PredictionJobDataClass

      pj = PredictionJobDataClass(
          id=1,
          model="xgb",          # choose your model type here
          forecast_type="demand",
          name="my_substation",
          lat=52.3,
          lon=4.9,
          resolution_minutes=15,
          horizon_minutes=2880,  # 48 hours
          train_components=False,
      )

.. dropdown:: How do I choose between XGBoost and LightGBM?
   :icon: light-bulb

   Both are strong gradient-boosting implementations. As a rule of thumb:

   - Use **XGBoost** (``"xgb"``) when you have moderate-sized datasets and want well-tested defaults. It is the most widely validated option within OpenSTEF.
   - Use **LightGBM** (``"lgbm"``) when training speed matters — for example, when retraining many prediction jobs frequently or when your dataset has millions of rows.

   In practice, the difference in forecast accuracy is often small. Run a backtest with both and compare MAE or RMSE on your specific data.

.. dropdown:: What is a PredictionJobDataClass and why do I need one?
   :icon: question

   ``PredictionJobDataClass`` is the central configuration object in OpenSTEF. Every pipeline function — training, forecasting, backtesting — accepts one as its first argument. It encodes:

   - **What** to forecast (``forecast_type``: demand, wind, solar, …).
   - **Where** (``lat``, ``lon`` — used for weather feature alignment).
   - **How often** (``resolution_minutes``) and **how far ahead** (``horizon_minutes``).
   - **Which model** to use and any model-specific hyperparameter overrides.

   Think of it as a typed configuration dictionary that makes it easy to manage dozens of forecasting locations in a loop.

.. dropdown:: Can I bring my own custom model?
   :icon: light-bulb

   Yes. OpenSTEF defines an ``OpenstfRegressor`` base class that your custom model must subclass. Once it implements the required interface (``fit``, ``predict``, and a few metadata properties), it can be passed through the same training and forecasting pipelines as the built-in models.

   See :doc:`user_guide/models` for details on implementing a custom regressor.

----

Training & Forecasting
-----------------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   Training data should be a ``pd.DataFrame`` with:

   - A ``DatetimeIndex`` (timezone-aware, UTC recommended).
   - A ``load`` column containing the target variable (historical energy load or generation in MW).
   - Optionally, weather columns such as ``radiation``, ``windspeed_100m``, ``temperature`` — OpenSTEF will derive additional features from these automatically.

   For forecasting, the same structure is expected but the ``load`` column will contain ``NaN`` values for the future timestamps you want to predict.

.. dropdown:: How do I run a backtest to evaluate my model?
   :icon: question

   Use the ``train_model_and_forecast_back_test`` pipeline:

   .. code-block:: python

      from openstef.data_classes.prediction_job import PredictionJobDataClass
      from openstef.data_classes.model_specifications import ModelSpecificationDataClass
      from openstef.pipeline.train_create_forecast_backtest import (
          train_model_and_forecast_back_test,
      )

      pj = PredictionJobDataClass(
          id=1,
          model="xgb",
          forecast_type="demand",
          name="my_substation",
          lat=52.3,
          lon=4.9,
          resolution_minutes=15,
          horizon_minutes=2880,
          train_components=False,
      )
      model_specs = ModelSpecificationDataClass(id=1)

      forecast_df, models, train_sets, val_sets, test_sets = (
          train_model_and_forecast_back_test(
              pj=pj,
              modelspecs=model_specs,
              input_data=your_dataframe,
              n_folds=3,
          )
      )

   ``forecast_df`` contains the back-test predictions alongside the actuals, ready for error metric calculation.

   .. note:: [VISUALIZATION: Back-test forecast vs. actuals time-series plot with confidence interval bands]

.. dropdown:: How does hyperparameter optimisation work?
   :icon: question

   OpenSTEF uses **Optuna** under the hood. When you call the training pipeline, it runs a search over the hyperparameter space defined for the chosen model type. The number of trials and early-stopping behaviour can be influenced via ``ModelSpecificationDataClass``. The best parameters found are stored alongside the serialised model in MLflow so that subsequent forecasting runs use them automatically.

   You do not need to configure Optuna directly for standard use — it runs transparently as part of ``train_model_pipeline``.

.. dropdown:: Where are trained models stored?
   :icon: question

   Models are serialised using **MLflow**. The ``train_model_pipeline`` function requires an ``mlflow_tracking_uri`` (a local path or a remote MLflow server URI) and an ``artifact_folder``. After training, the model, its hyperparameters, and a training report are all logged to that MLflow run.

   .. code-block:: python

      from openstef.pipeline.train_model import train_model_pipeline

      train_model_pipeline(
          pj=pj,
          input_data=your_dataframe,
          check_old_model_age=False,
          mlflow_tracking_uri="./mlruns",
          artifact_folder="./artifacts",
      )

   You can then browse results with ``mlflow ui`` from the same directory.

----

Common Issues
-------------

.. dropdown:: My forecast is all NaN — what went wrong?
   :icon: alert

   The most common causes are:

   - **No trained model found** — ensure you have run the training pipeline before calling the forecast pipeline, and that ``mlflow_tracking_uri`` and ``artifact_folder`` point to the same location used during training.
   - **Insufficient future data** — the forecast pipeline detects the range to predict from the last cluster of ``NaN`` values in the ``load`` column. If there are no ``NaN`` rows, no forecast range is generated.
   - **Timezone mismatch** — make sure your DataFrame index is timezone-aware and consistent between training and forecasting data.

.. dropdown:: Training fails with "not enough data" or a flatliner error — what does that mean?
   :icon: alert

   OpenSTEF checks input data quality before training. A **flatliner** is a time series where the load values are constant (or near-constant) for an extended period, which makes it impossible to train a meaningful model. This can happen when:

   - The measurement device was offline and the database was filled with a default value.
   - You are passing a very short slice of data that happens to be flat.

   Ensure your training data spans at least several weeks of varied load, and check for long runs of identical values before passing data to the pipeline.

.. dropdown:: Can I use OpenSTEF without MLflow?
   :icon: question

   The high-level ``train_model_pipeline`` function requires MLflow for model persistence. However, the **core** pipeline function ``train_model_pipeline_core`` returns the trained ``OpenstfRegressor`` object directly as a Python object, so you can serialise it yourself (e.g., with ``joblib`` or ``pickle``) if you prefer not to use MLflow in early experimentation.

   For production use, MLflow is strongly recommended because it keeps hyperparameters, metrics, and model artefacts together in a reproducible way.

.. dropdown:: How do I contribute or report a bug?
   :icon: info

   OpenSTEF is an LF Energy project hosted on GitHub. To report a bug or request a feature, open an issue at `https://github.com/OpenSTEF/openstef/issues <https://github.com/OpenSTEF/openstef/issues>`_. Pull requests are welcome — see the contributing guide in the repository root for coding standards and the review process.