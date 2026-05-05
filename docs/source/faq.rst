FAQ
===

This page answers the most common questions from new OpenSTEF users — from understanding what the library does, to setting it up, choosing models, and running your first forecast. If you don't find your answer here, check the :doc:`getting_started` guide or open a discussion on GitHub.

.. mermaid:: /diagrams/root/faq_diagram_1.mmd

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is a Python library for training machine learning models that predict energy load and generation over short time horizons — typically up to 48 hours ahead. It provides end-to-end pipelines covering feature engineering, model training, hyperparameter optimisation, forecast generation, and confidence interval estimation.

   The library is built around the concept of a **prediction job** — a configuration object that describes what to forecast, at what resolution, and with which model. This makes it straightforward to manage many forecasting locations in a single system.

.. dropdown:: What does "short-term" mean in this context?
   :icon: question

   Short-term forecasting in OpenSTEF refers to horizons ranging from a few minutes up to roughly 48 hours ahead. The library is designed for operational use cases where forecasts need to be refreshed frequently — for example, every 15 minutes — to support grid balancing, congestion management, and energy trading decisions.

   Forecast horizons are configured per prediction job via the ``horizon_minutes`` field. The training pipelines automatically generate lag features and other time-series features appropriate for the chosen horizon.

.. dropdown:: What makes OpenSTEF different from a general ML library?
   :icon: question

   General ML libraries (scikit-learn, XGBoost, etc.) provide model building blocks but leave the energy-specific work to you. OpenSTEF adds:

   - **Domain-specific feature engineering** — automatic lag features, calendar features, weather-derived features (wind power curves, solar irradiance), and electricity price features.
   - **Prediction job abstraction** — a single configuration object drives training, forecasting, and backtesting consistently across many locations.
   - **Confidence intervals** — every forecast includes quantile estimates out of the box.
   - **Fallback strategies** — if a model cannot produce a forecast, configurable fallback logic prevents silent failures.
   - **MLflow integration** — trained models are versioned and stored automatically via ``MLflowSerializer``.

   You bring your load and weather data; OpenSTEF handles the rest of the ML pipeline.

.. dropdown:: Is OpenSTEF an application or a library?
   :icon: question

   OpenSTEF is a **library**. It exposes Python functions and classes that you call from your own code, scripts, or pipelines. There is no standalone server or GUI. You integrate it into your existing infrastructure — whether that is a cron job, an Airflow DAG, a Kubernetes workload, or a Jupyter notebook.

   The companion package ``openstef-dbc`` provides database connectivity helpers used in production deployments, but it is not required to use the core library.

Installation & Requirements
---------------------------

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

   Python 3.9 or later is required.

.. dropdown:: What are the main dependencies?
   :icon: info

   OpenSTEF's core dependencies include:

   - **pandas** and **numpy** — data manipulation and numerical operations.
   - **scikit-learn** — base classes, preprocessing, and model evaluation utilities.
   - **XGBoost**, **LightGBM**, and **scikit-learn regressors** — the supported model backends.
   - **optuna** — hyperparameter optimisation.
   - **MLflow** — model serialisation and experiment tracking.
   - **networkx** — dependency graph resolution between prediction jobs.

   All of these are declared in ``pyproject.toml`` and installed automatically with ``pip install openstef``.

.. dropdown:: Do I need MLflow running to use OpenSTEF?
   :icon: question

   You need an MLflow tracking URI to save and load models via the standard pipelines. For local development, a local file-system URI is sufficient — no separate MLflow server is required:

   .. code-block:: python

      mlflow_tracking_uri = "sqlite:///mlflow.db"
      artifact_folder = "./models"

   Pass these values to ``train_model_pipeline`` and ``create_forecast_pipeline``. In production you would point to a shared MLflow server so that models are accessible across services.

.. dropdown:: Can I use OpenSTEF without a database?
   :icon: question

   Yes. The core pipelines in ``openstef.pipeline`` accept plain ``pandas.DataFrame`` objects as input. You are responsible for loading your data from wherever it lives — a CSV file, a time-series database, a data warehouse — and passing it to the pipeline functions. No database connection is needed for the library itself.

   The ``openstef-dbc`` package provides ready-made connectors for specific database backends used in some production deployments, but it is entirely optional.

Models & Forecasting
--------------------

.. dropdown:: Which ML models does OpenSTEF support?
   :icon: question

   OpenSTEF supports several model types, selectable via the ``model`` field of a prediction job:

   - ``xgb`` — XGBoost gradient boosting (default for most use cases).
   - ``xgb_quantile`` — XGBoost with native quantile regression for richer uncertainty estimates.
   - ``lgbm`` — LightGBM, often faster to train on large datasets.
   - ``linear`` — regularised linear regression, useful as a baseline.
   - ``linear_quantile`` — quantile linear regression.
   - ``sklearn`` — generic scikit-learn regressor wrapper.

   All models implement the ``OpenstfRegressor`` interface, so they are interchangeable within the same pipeline.

.. dropdown:: How do I choose which model to use?
   :icon: light-bulb

   Start with ``xgb`` — it is the most battle-tested option in OpenSTEF and handles non-linear patterns and missing values well. Switch to ``lgbm`` if training time is a bottleneck on large datasets. Use ``xgb_quantile`` or ``linear_quantile`` when you need well-calibrated prediction intervals rather than just point forecasts.

   You can compare models systematically using the backtest pipeline:

   .. code-block:: python

      from openstef.pipeline.train_create_forecast_backtest import (
          train_model_and_forecast_back_test,
      )
      from openstef.data_classes.prediction_job import PredictionJobDataClass
      from openstef.data_classes.model_specifications import ModelSpecificationDataClass

      pj = PredictionJobDataClass(
          id=1,
          model="xgb",
          forecast_type="demand",
          name="My location",
          lat=52.0,
          lon=4.0,
          resolution_minutes=15,
          horizon_minutes=2880,
          train_components=False,
      )
      model_specs = ModelSpecificationDataClass(id=1)

      forecast_df, models, train_sets, val_sets, test_sets = (
          train_model_and_forecast_back_test(pj, model_specs, input_data)
      )

   Run this for each candidate model type and compare the resulting error metrics.

.. dropdown:: What is a prediction job?
   :icon: question

   A prediction job (``PredictionJobDataClass``) is the central configuration object in OpenSTEF. It tells the pipelines everything they need to know about a single forecasting task:

   .. code-block:: python

      from openstef.data_classes.prediction_job import PredictionJobDataClass

      pj = PredictionJobDataClass(
          id=42,
          model="xgb",
          forecast_type="demand",
          name="Substation Noord",
          lat=52.37,
          lon=4.89,
          resolution_minutes=15,
          horizon_minutes=2880,   # 48 hours
          train_components=False,
      )

   The same ``pj`` object is passed to the training pipeline, the forecast pipeline, and the backtest pipeline, ensuring consistency. In production systems, prediction jobs are typically stored in a database and iterated over with ``PredictionJobLoop``.

.. dropdown:: How does OpenSTEF generate confidence intervals?
   :icon: question

   After a point-forecast model produces its predictions, ``ConfidenceIntervalApplicator`` adds quantile estimates based on the residual distribution observed during training. This means even models that do not natively support quantile regression (such as standard XGBoost) still produce uncertainty bands.

   For tighter probabilistic guarantees, use ``xgb_quantile`` or ``linear_quantile``, which optimise quantile loss directly during training. The forecast output DataFrame always includes quantile columns (e.g., ``quantile_P10``, ``quantile_P90``) regardless of the model type.

Data & Features
---------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   The training pipeline expects a ``pandas.DataFrame`` with a ``DatetimeIndex`` and at least one target column (the load or generation values you want to forecast). Weather features — such as wind speed, solar irradiance, and temperature — can be included as additional columns and will be used automatically by the feature engineering step.

   For forecast generation, you supply a DataFrame covering the forecast horizon with weather forecast values filled in and the target column set to ``NaN`` for the future timestamps.

.. dropdown:: Does OpenSTEF handle missing data?
   :icon: question

   Yes. The validation module (``openstef.validation``) detects and flags flatliners, outliers, and gaps before training. XGBoost and LightGBM handle ``NaN`` values natively, so moderate amounts of missing input data do not require manual imputation. If the target series is entirely flat or missing, the training pipeline raises a descriptive error rather than producing a silently broken model.

.. dropdown:: Can I add my own custom features?
   :icon: light-bulb

   Yes. The feature applicator classes (``OperationalPredictFeatureApplicator``) are extensible. You can also pre-compute custom columns in your input DataFrame before passing it to the pipeline — any extra columns present in both the training data and the forecast input data will be picked up as features automatically.

   For more details on the feature engineering system, see :doc:`feature_engineering`.

Troubleshooting
---------------

.. dropdown:: Training fails with "Please specify a config object and/or database connection object"
   :icon: alert

   This error comes from the **task-level** wrappers in ``openstef.tasks`` (e.g., ``create_forecast.py``, ``train_model.py``). These wrappers are designed for production deployments that use ``openstef-dbc`` for database connectivity.

   If you are using OpenSTEF as a standalone library, call the **pipeline-level** functions directly instead:

   .. code-block:: python

      from openstef.pipeline.train_model import train_model_pipeline

      train_model_pipeline(
          pj=pj,
          input_data=input_data,
          check_old_model_age=False,
          mlflow_tracking_uri="sqlite:///mlflow.db",
          artifact_folder="./models",
      )

   The pipeline functions have no database dependency and accept plain DataFrames.

.. dropdown:: My forecast is all NaN — what went wrong?
   :icon: alert

   The most common cause is that no trained model exists for the given prediction job ID at the specified ``mlflow_tracking_uri``. Run the training pipeline first, then run the forecast pipeline pointing to the same tracking URI and artifact folder.

   A second common cause is that the forecast input DataFrame does not cover the expected future timestamps — ``create_forecast_pipeline`` infers the forecast window from the last cluster of ``NaN`` values in the target column. Make sure your input DataFrame extends far enough into the future with ``NaN`` in the target column and valid weather forecast values in the feature columns.

.. dropdown:: How do I run a quick end-to-end test without real data?
   :icon: light-bulb

   OpenSTEF ships with built-in example data you can use to verify your installation:

   .. code-block:: python

      import openstef
      from pathlib import Path
      import pandas as pd

      data_path = Path(openstef.__file__).parent / "data" / "dutch_energy_load.csv"
      input_data = pd.read_csv(data_path, index_col=0, parse_dates=True)
      print(input_data.head())

   From there, construct a ``PredictionJobDataClass`` and pass ``input_data`` to ``train_model_pipeline``. See :doc:`getting_started` for a complete walkthrough.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - **GitHub Issues** — `github.com/OpenSTEF/openstef/issues <https://github.com/OpenSTEF/openstef/issues>`_ for bug reports and feature requests.
   - **GitHub Discussions** — for usage questions and community support.
   - **LF Energy Slack** — the ``#openstef`` channel on the LF Energy Slack workspace.

   When reporting a bug, include your OpenSTEF version (``import openstef; print(openstef.__version__)``), a minimal reproducible example, and the full traceback.