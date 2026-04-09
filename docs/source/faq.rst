FAQ
===

This FAQ covers common questions from new users about OpenSTEF, including what short-term forecasting is, system requirements, model selection, and getting started with the library.

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: info

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term forecasts in the energy sector. It provides a complete machine learning pipeline for forecasting load, generation, and other energy-related metrics hours to days ahead.

   Key characteristics:

   - **Model-agnostic framework** — not just a single model, but a complete pipeline for data preprocessing, feature engineering, training, forecasting, and evaluation
   - **Probabilistic forecasts** — generates multiple quantile forecasts with uncertainty bands, not just point predictions
   - **Domain knowledge included** — built-in feature engineering specific to energy forecasting (e.g., solar radiation to PV generation estimates)
   - **Production-ready** — used by Alliander and other utilities for congestion management and grid operations

.. dropdown:: What is short-term forecasting?
   :icon: question

   Short-term forecasting means predicting energy load or generation hours to days ahead (typically 1-48 hours). This is different from:

   - **Very short-term forecasting** — minutes to hours ahead (intraday trading, real-time operations)
   - **Medium-term forecasting** — weeks to months ahead (maintenance planning, resource allocation)
   - **Long-term forecasting** — years ahead (infrastructure investment, capacity planning)

   Short-term forecasts are essential for congestion management, transport forecasts, EV charging capacity estimation, and grid loss prediction.

.. dropdown:: What makes OpenSTEF special compared to other forecasting libraries?
   :icon: light-bulb

   OpenSTEF is purpose-built for energy forecasting with domain-specific features:

   - **Energy-specific feature engineering** — automatic handling of solar radiation, temperature effects, holiday patterns, and other energy-relevant features
   - **Quantile forecasting by default** — probabilistic forecasts help grid operators understand uncertainty and make better decisions
   - **Battle-tested in production** — developed and used by Alliander for real-world grid operations
   - **Complete pipeline** — not just models, but preprocessing, postprocessing, evaluation, and visualization tools
   - **Modular architecture** — install only the components you need

   While libraries like scikit-learn or Prophet are general-purpose, OpenSTEF focuses specifically on the challenges of energy forecasting.

Installation and Setup
----------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF 4.0 requires:

   - **Python 3.12 or higher** (Python 3.13 supported)
   - **64-bit operating system** (Windows, macOS, or Linux)

   You can check your Python version with:

   .. code-block:: bash

      python --version

   If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   OpenSTEF has a modular architecture. For most users, install the main package:

   .. code-block:: bash

      pip install openstef

   For specific use cases:

   .. code-block:: bash

      # For model training and forecasting
      pip install openstef-models

      # For Apache Beam workflows (large-scale processing)
      pip install openstef-beam

   See the :doc:`user_guide/installation` guide for detailed instructions including conda, uv, and pixi installation methods.

.. dropdown:: Do I need to install XGBoost separately?
   :icon: question

   XGBoost is an optional dependency. If you want to use XGBoost-based models (like ``XGBoostForecaster`` or ``GBLinearForecaster``), install it separately:

   .. code-block:: bash

      pip install xgboost

   OpenSTEF includes other forecasting models that don't require XGBoost, so you can start without it and add it later if needed.

Models and Forecasting
----------------------

.. dropdown:: What forecasting models are available?
   :icon: question

   OpenSTEF provides several forecasting models:

   - **XGBoostForecaster** — gradient boosting trees, excellent for complex patterns (requires xgboost package)
   - **GBLinearForecaster** — linear model using XGBoost's linear booster (requires xgboost package)
   - **ConstantMedianForecaster** — simple baseline that predicts the median value
   - **Custom models** — you can implement your own by extending the ``Forecaster`` interface

   Most production deployments use XGBoostForecaster for its accuracy and ability to handle non-linear relationships.

.. dropdown:: How do I choose which model to use?
   :icon: light-bulb

   Start with these guidelines:

   - **XGBoostForecaster** — best for most use cases, handles complex patterns, automatically captures interactions between features
   - **GBLinearForecaster** — when you need interpretability or have limited training data
   - **ConstantMedianForecaster** — for baseline comparisons or when you have very little historical data

   The best approach is to train multiple models and compare their performance using OpenSTEF's evaluation tools. See :doc:`user_guide/model_selection` for detailed guidance.

.. dropdown:: What are quantile forecasts and why should I use them?
   :icon: info

   Quantile forecasts provide multiple predictions representing different probability levels. For example, quantiles [0.1, 0.5, 0.9] give you:

   - **0.1 quantile** — 10% chance actual load will be below this (pessimistic scenario)
   - **0.5 quantile** — median prediction (50% probability)
   - **0.9 quantile** — 90% chance actual load will be below this (optimistic scenario)

   This is crucial for grid operations because:

   - **Risk management** — understand the range of possible outcomes
   - **Decision making** — choose conservative or aggressive strategies based on uncertainty
   - **Congestion management** — plan for worst-case scenarios to prevent overloads

   Example configuration:

   .. code-block:: python

      from openstef_models.forecaster import XGBoostForecaster
      from openstef_models.forecaster.config import Quantile, LeadTime
      from datetime import timedelta

      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
          horizons=[LeadTime(timedelta(hours=1))],
      )

Getting Started
---------------

.. dropdown:: How do I make my first forecast?
   :icon: question

   Here's a minimal example to get started:

   .. code-block:: python

      from openstef_models.forecaster import XGBoostForecaster
      from openstef_models.forecaster.config import Quantile, LeadTime
      from datetime import timedelta
      import pandas as pd

      # Configure the forecaster
      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.5)],  # Median prediction
          horizons=[LeadTime(timedelta(hours=1))],
      )

      # Prepare your training data (pandas DataFrame)
      # Must include 'load' column and datetime index
      training_data = pd.read_csv("historical_load.csv", index_col=0, parse_dates=True)

      # Train the model
      forecaster.fit(training_data)

      # Make predictions
      predictions = forecaster.predict(test_data)

   For complete examples, see the :doc:`examples` section.

.. dropdown:: Where can I find example code and tutorials?
   :icon: question

   OpenSTEF provides several learning resources:

   - **Examples** — short, focused code snippets demonstrating specific features
   - **Tutorials** — step-by-step guides for common workflows
   - **API documentation** — detailed reference for all classes and functions

   Start with the :doc:`examples` page to browse available examples. The ``forecasting_preset_example.py`` is a good starting point showing a complete forecasting pipeline.

.. dropdown:: What data format does OpenSTEF expect?
   :icon: question

   OpenSTEF works with pandas DataFrames with a datetime index. The basic requirements:

   - **Datetime index** — timestamps for your observations
   - **Target column** — the value you want to forecast (e.g., 'load', 'generation')
   - **Feature columns** (optional) — weather data, calendar features, etc.

   Example structure:

   .. code-block:: python

      import pandas as pd

      data = pd.DataFrame({
          'load': [100, 105, 110, 95],
          'temperature': [15, 16, 17, 14],
          'hour': [0, 1, 2, 3],
      }, index=pd.date_range('2024-01-01', periods=4, freq='h'))

   OpenSTEF can automatically generate many features from just the datetime index and target variable, so you don't need extensive external data to get started.

Troubleshooting
---------------

.. dropdown:: I'm getting a Python version error during installation
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. We recommend using `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions:

   .. code-block:: bash

      # Using pyenv
      pyenv install 3.12
      pyenv local 3.12

      # Using conda
      conda create -n openstef python=3.12
      conda activate openstef

   If upgrading isn't possible, consider using OpenSTEF 3.x which supports Python 3.10+.

.. dropdown:: Where can I get help if my question isn't answered here?
   :icon: question

   Several resources are available:

   - **Documentation** — search the :doc:`user_guide/index` and :doc:`api/index` sections
   - **GitHub Issues** — report bugs or request features at https://github.com/OpenSTEF/openstef
   - **Community** — join discussions with other users (see :doc:`project/index` for community links)

   When asking for help, include:

   - Your OpenSTEF version (``import openstef; print(openstef.__version__)``)
   - Python version (``python --version``)
   - Minimal code example that reproduces the issue
   - Full error message and traceback