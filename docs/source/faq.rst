FAQ
===

This page answers the most common questions from new and experienced users of OpenSTEF.
If you can't find what you're looking for here, check the :doc:`user_guide/index` or
reach out on `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_.

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is a **Python library** for creating
   short-term forecasts in the energy sector. It is not a standalone application or
   platform — it is a set of composable building blocks you import into your own Python
   code to build, train, and run energy forecasting models.

   OpenSTEF is an open-source project hosted under the `LF Energy <https://www.lfenergy.org/projects/openstef/>`_
   foundation and is licensed under the Mozilla Public License 2.0.

.. dropdown:: What is "short-term energy forecasting" exactly?
   :icon: question

   Short-term energy forecasting predicts electricity load or generation over horizons
   ranging from minutes to several days ahead. These forecasts are critical for:

   - **Grid operators** balancing supply and demand in real time
   - **Energy traders** making market decisions
   - **Renewable energy producers** anticipating solar and wind output
   - **Distribution system operators** managing congestion

   OpenSTEF focuses on automated, multi-horizon probabilistic forecasting — meaning it
   produces not just a single point forecast, but confidence intervals (quantiles) that
   express forecast uncertainty.

.. dropdown:: What makes OpenSTEF different from other forecasting libraries?
   :icon: question

   Several things set OpenSTEF apart:

   - **Domain-specific**: Purpose-built for energy forecasting with features like weather-derived
     variables, solar position calculations, holiday awareness, and wind power transformations.
   - **Probabilistic by default**: Every forecast includes configurable quantile predictions
     (e.g., P10, P50, P90) for uncertainty quantification.
   - **Automated pipelines**: Feature engineering, model training, and prediction are orchestrated
     through composable pipelines — not manual scripting.
   - **Production-proven**: Originally developed at Alliander (a major Dutch grid operator) and
     used in real-world grid operations.
   - **Modular architecture**: Install only what you need — core utilities, forecasting models,
     or backtesting tools — as separate packages.

.. dropdown:: Is OpenSTEF an application I can deploy, or a library I import?
   :icon: question

   OpenSTEF is a **library**. You ``pip install`` it and import its modules into your own
   Python scripts, notebooks, or applications. It does not include a web interface, REST API,
   or database — those are concerns of your application layer.

   A typical usage pattern looks like this:

   .. code-block:: python

      from openstef_models.forecasting import ForecastingModel

      # Build your model, train it on your data, and generate forecasts
      model = ForecastingModel(...)
      model.fit(training_data)
      predictions = model.predict(input_data)

   You are responsible for data ingestion, storage, scheduling, and serving — OpenSTEF
   handles the forecasting logic.

Installation & Setup
--------------------

.. dropdown:: What Python version do I need?
   :icon: question

   OpenSTEF 4.0 requires **Python 3.12 or higher** (Python 3.13 is also supported).
   You need a 64-bit operating system (Windows, macOS, or Linux).

   If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest installation uses pip:

   .. code-block:: bash

      pip install openstef

   This installs the ``openstef`` meta-package, which includes ``openstef-core`` and
   ``openstef-models``. For the full toolkit including backtesting:

   .. code-block:: bash

      pip install "openstef[all]"

   OpenSTEF also supports ``uv``, ``conda``, and ``pixi``. See :doc:`user_guide/installation`
   for the complete guide.

.. dropdown:: What are the different OpenSTEF packages?
   :icon: question

   OpenSTEF 4.0 follows a modular design:

   - **openstef-core**: Core utilities, data types, and feature engineering primitives.
   - **openstef-models**: Forecasting models (XGBoost, LightGBM, etc.) and prediction pipelines.
   - **openstef-beam**: Backtesting and model evaluation tools.
   - **openstef** (meta-package): Installs ``openstef-core`` and ``openstef-models`` together.

   Install only what you need:

   .. code-block:: bash

      # Production forecasting (lightweight)
      pip install openstef-models

      # Full research toolkit
      pip install "openstef[all]"

      # Just evaluation tools
      pip install "openstef[beam]"

.. dropdown:: I'm getting an import error. What's wrong?
   :icon: question

   The most common cause is using the wrong import path. OpenSTEF packages use
   **underscores** in their Python module names:

   .. code-block:: python

      # Correct
      from openstef_models.forecasting import ForecastingModel
      from openstef_core.datasets import VersionedTimeSeriesDataset

      # Wrong — will raise ImportError
      from openstef.models import ForecastingModel

   If you installed a subset of packages, make sure the module you're importing is
   actually included. For example, ``openstef_beam`` is only available if you installed
   ``openstef-beam`` or ``openstef[all]``.

Models & Forecasting
--------------------

.. dropdown:: What machine learning models does OpenSTEF support?
   :icon: question

   OpenSTEF includes several forecasting model types:

   - **XGBoost** (``XGBoostForecaster``): Gradient boosted trees — a strong general-purpose choice.
   - **LightGBM** (``LGBMForecaster``): Fast gradient boosting, often preferred for larger datasets.
     Supports CPU and GPU computation.
   - **Base Case** (``BaseCaseForecaster``): A simple repeated-weekly-pattern baseline that requires
     no training. Useful as a benchmark.

   All models produce **multi-quantile probabilistic forecasts** by default. You configure
   which quantiles to predict (e.g., P10, P50, P90) through the model configuration.

.. dropdown:: What features does OpenSTEF engineer automatically?
   :icon: question

   OpenSTEF's preprocessing pipelines can automatically derive a rich set of features from
   your input data, including:

   - **Lag features**: Historical values of the target variable at configurable offsets
   - **Rolling aggregates**: Moving averages and other window statistics
   - **Calendar features**: Hour of day, day of week, month (with cyclic encoding)
   - **Holiday indicators**: Country-specific public holidays
   - **Daylight features**: Sunrise/sunset-based features from geographic coordinates
   - **Weather-derived features**: Wind power estimates, atmospheric calculations, radiation-derived features
   - **Solar features**: Based on radiation data and geographic position

   These are implemented as composable pipeline steps that you can mix, match, and extend.

.. dropdown:: What are quantile forecasts and why should I care?
   :icon: question

   A quantile forecast doesn't just tell you "we expect 150 MW" — it tells you the range
   of likely outcomes. For example:

   - **P10**: There's a 10% chance the actual value will be below this
   - **P50**: The median forecast (50% chance of being above or below)
   - **P90**: There's a 90% chance the actual value will be below this

   This uncertainty information is essential for risk-aware decision making in energy
   operations — for example, sizing reserve capacity or setting trading positions.

   In OpenSTEF, you configure quantiles in your model setup:

   .. code-block:: python

      from openstef_core.types import Quantile

      quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

.. dropdown:: How do I choose between XGBoost and LightGBM?
   :icon: question

   Both are excellent choices. Some rules of thumb:

   - **XGBoost**: Well-tested, widely used, good default. Works well for most energy
     forecasting tasks.
   - **LightGBM**: Often faster to train, especially on larger datasets. Supports GPU
     acceleration natively. Can be more memory-efficient.

   If you're unsure, start with XGBoost. You can always switch later — OpenSTEF's
   pipeline architecture makes it straightforward to swap model backends while keeping
   the same preprocessing and postprocessing steps.

Data & Input
------------

.. dropdown:: What input data does OpenSTEF need?
   :icon: question

   At minimum, you need:

   - **Historical target values**: The time series you want to forecast (e.g., load in MW),
     indexed by datetime.
   - **Forecast horizons**: How far ahead you want to predict.

   For better accuracy, you can also provide:

   - **Weather forecasts**: Temperature, wind speed, radiation, pressure, humidity
   - **Energy prices**: Day-ahead market prices
   - **Geographic coordinates**: For solar position and daylight calculations

   Data is passed to OpenSTEF as ``VersionedTimeSeriesDataset`` objects built on pandas
   DataFrames.

.. dropdown:: What time resolution does OpenSTEF expect?
   :icon: question

   OpenSTEF works with regular time series data, typically at **15-minute** or **hourly**
   resolution. The resolution should be consistent across your target and predictor
   variables.

Evaluation & Backtesting
------------------------

.. dropdown:: How do I evaluate my forecast quality?
   :icon: question

   OpenSTEF provides the ``openstef-beam`` package for backtesting and evaluation. A
   backtest simulates how your model would have performed historically by repeatedly
   training and predicting on rolling windows of data:

   .. code-block:: python

      from openstef_beam.backtesting import BacktestPipeline

      pipeline = BacktestPipeline(...)
      results = pipeline.run(
          ground_truth=historical_data,
          predictors=feature_data,
      )

   The BEAM package also includes visualization tools for calibration plots and
   probability analysis. See :doc:`user_guide/tutorials` for detailed examples.

.. dropdown:: What metrics should I use for energy forecasts?
   :icon: question

   For **point forecasts** (P50), common metrics include MAE (Mean Absolute Error) and
   RMSE (Root Mean Squared Error).

   For **probabilistic forecasts**, you should also evaluate:

   - **Calibration**: Do your P90 intervals actually contain 90% of observations?
   - **Sharpness**: How narrow are your prediction intervals? (Narrower is better, if calibrated.)
   - **Quantile loss** (pinball loss): A proper scoring rule for quantile predictions.

   OpenSTEF BEAM includes plotting tools like ``QuantileProbabilityPlotter`` to visualize
   calibration.

Getting Help
------------

.. dropdown:: Where can I get help or report bugs?
   :icon: info

   - **GitHub Issues**: `github.com/OpenSTEF/openstef/issues <https://github.com/OpenSTEF/openstef/issues>`_
   - **Email**: openstef@lfenergy.org
   - **LF Energy community**: `lfenergy.org/projects/openstef <https://www.lfenergy.org/projects/openstef/>`_

   Before opening an issue, check the :doc:`user_guide/installation` troubleshooting
   section and search existing issues for similar problems.

.. dropdown:: How can I contribute to OpenSTEF?
   :icon: light-bulb

   OpenSTEF welcomes contributions! To get started:

   1. Clone the repository and install in development mode using ``uv``:

      .. code-block:: bash

         git clone https://github.com/OpenSTEF/openstef.git
         cd openstef
         uv sync --all-extras --dev

   2. Run the test suite to verify your setup:

      .. code-block:: bash

         uv run pytest

   3. Read the :doc:`contribute/index` guide for coding standards and PR workflow.