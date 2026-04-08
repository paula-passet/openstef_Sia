FAQ
===

This page answers common questions from new users about OpenSTEF, covering what the library does, how to get started, and how to choose the right model for your forecasting needs.

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: info

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for creating short-term energy forecasts. It's a complete machine learning framework that provides pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing.

   Key characteristics:

   - **Model-agnostic framework** — not just a single model, but a complete forecasting pipeline
   - **Probabilistic forecasts** — generates multiple quantile forecasts with uncertainty estimates, not just point predictions
   - **Domain knowledge included** — built-in feature engineering specific to energy forecasting (e.g., solar radiation to PV generation estimates)
   - **Production-ready** — used by Alliander and other utilities for real-world congestion management

.. dropdown:: What is short-term forecasting?
   :icon: question

   Short-term forecasting means predicting energy load or generation hours to days ahead (typically up to 48 hours). This is different from:

   - **Very short-term forecasting** — minutes to hours ahead
   - **Medium-term forecasting** — days to weeks ahead
   - **Long-term forecasting** — months to years ahead

   Short-term forecasts are essential for operational decisions like congestion management, grid balancing, and capacity planning.

.. dropdown:: What makes OpenSTEF special compared to other forecasting libraries?
   :icon: light-bulb

   OpenSTEF is purpose-built for energy forecasting with domain-specific features:

   - **Energy-specific feature engineering** — automatic handling of weather data, solar radiation, wind power curves, and atmospheric features
   - **Probabilistic by default** — multi-quantile forecasting built into the core, not an afterthought
   - **Complete pipeline** — from raw data to production forecasts, including validation and post-processing
   - **Battle-tested** — used in production by utilities managing real grid congestion
   - **Modular architecture** — install only the components you need

   Generic forecasting libraries require you to build these capabilities yourself.

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

   The simplest way is using pip:

   .. code-block:: bash

      pip install openstef

   OpenSTEF 4.0 has a modular architecture. The base package includes the core forecasting models. For additional components, you can install:

   .. code-block:: bash

      pip install openstef-beam  # For Apache Beam pipelines
      pip install openstef-dbc   # For database connectivity

   For detailed installation instructions, see :doc:`user_guide/installation`.

.. dropdown:: Do I need to install uv or can I use pip?
   :icon: question

   You can use **any Python package manager** you prefer — pip, uv, conda, poetry, or pixi all work fine. OpenSTEF is a standard Python library.

   The documentation mentions uv because it's the tool used for OpenSTEF's own development, but it's not required for users. Use whatever fits your workflow.

Model Selection
---------------

.. dropdown:: Which model should I use for my forecasting task?
   :icon: question

   OpenSTEF provides several model types:

   - **XGBoostForecaster** — the default and most widely used. Gradient boosting trees handle non-linear relationships well and work for most energy forecasting tasks.
   - **LightGBMForecaster** — faster alternative to XGBoost, good for very large datasets.
   - **LinearForecaster** — simple linear regression, useful for baseline comparisons or when interpretability is critical.
   - **GBLinearForecaster** — linear model using XGBoost's linear booster.

   Start with XGBoostForecaster unless you have a specific reason to choose another model. See :doc:`user_guide/models` for detailed comparisons.

.. dropdown:: Can I use my own custom model with OpenSTEF?
   :icon: light-bulb

   Yes! OpenSTEF is model-agnostic. The framework provides the data preprocessing, feature engineering, and evaluation pipeline. You can integrate your own model by implementing the forecaster interface.

   The pipeline components (feature adders, scalers, validators) work independently of the model choice, so you get all the energy-specific feature engineering even with custom models.

.. dropdown:: Does OpenSTEF only do point forecasts or can it provide uncertainty estimates?
   :icon: info

   OpenSTEF is **probabilistic by default**. All forecasters generate multi-quantile predictions that provide uncertainty estimates, not just single-point predictions.

   For example, you can request forecasts at the 10th, 50th (median), and 90th percentiles to understand the range of possible outcomes. This is essential for risk management in grid operations.

Data and Features
-----------------

.. dropdown:: What input data does OpenSTEF need?
   :icon: question

   At minimum, you need:

   - **Historical load data** — the target variable you want to forecast
   - **Timestamps** — datetime index for your data
   - **Weather forecasts** — temperature, wind speed, solar radiation, etc.

   Optional but recommended:

   - **Location coordinates** — for solar position calculations
   - **Holiday calendars** — for modeling day-type effects
   - **Energy prices** — if relevant to your use case

   OpenSTEF's feature engineering pipeline automatically creates hundreds of derived features from this basic input data.

.. dropdown:: How does OpenSTEF handle missing data?
   :icon: question

   OpenSTEF includes built-in data quality checks and preprocessing steps:

   - **Validation** — checks for missing values, outliers, and data quality issues
   - **Imputation** — can fill gaps using various strategies
   - **Feature removal** — automatically removes features with too many missing values

   The preprocessing pipeline is configurable, so you can adjust the handling based on your data quality requirements. See :doc:`user_guide/data_preparation` for details.

Getting Started
---------------

.. dropdown:: I'm new to OpenSTEF. Where should I start?
   :icon: light-bulb

   Follow this learning path:

   1. **Read the quickstart** — :doc:`user_guide/quickstart` shows a complete forecasting example in a few lines of code
   2. **Understand the pipeline** — :doc:`user_guide/pipeline` explains how the components fit together
   3. **Try the examples** — :doc:`examples` provides real-world use cases
   4. **Explore the API** — :doc:`api/index` for detailed reference documentation

   Most users can create their first forecast within an hour of installation.

.. dropdown:: Can I use OpenSTEF for forecasting outside the energy sector?
   :icon: question

   While OpenSTEF is optimized for energy forecasting, the core machine learning pipeline works for any time series forecasting task. However, some features are energy-specific:

   - Solar radiation to PV generation conversion
   - Wind power curve calculations
   - Energy price features

   If your use case involves weather-dependent time series forecasting (e.g., water demand, traffic), OpenSTEF's feature engineering may still be valuable. For general time series forecasting, you might find simpler libraries more appropriate.

Troubleshooting
---------------

.. dropdown:: I get a "Python version error" during installation. What should I do?
   :icon: alert

   OpenSTEF 4.0 requires Python 3.12 or higher. If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade Python. We recommend using `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions.

   Alternatively, use OpenSTEF 3.x if you cannot upgrade Python.

.. dropdown:: Where can I get help if I'm stuck?
   :icon: question

   Several resources are available:

   - **Documentation** — this site covers most common scenarios
   - **GitHub Issues** — report bugs or request features at the `OpenSTEF repository <https://github.com/OpenSTEF/openstef>`_
   - **Community** — see :doc:`project/index` for community channels and contribution guidelines

   When asking for help, include your Python version, OpenSTEF version, and a minimal code example that reproduces the issue.