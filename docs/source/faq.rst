FAQ
===

This FAQ answers the most common questions from new users of OpenSTEF — covering what the library does, how to install it, which models to use, and how to get started quickly. If you have a question not covered here, check the :doc:`user_guide/index` or open a discussion on GitHub.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building, training, and deploying machine learning models that forecast energy load hours to days ahead. It is not a single model — it is a model-agnostic framework that provides complete pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing.

   OpenSTEF is developed and maintained by Alliander, a Dutch grid operator, and is used in production to generate forecasts for over 10,000 grid locations.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load from a few hours up to roughly two days ahead. This horizon is long enough to take operational decisions (such as calling customers to reduce consumption during a predicted peak) but short enough that machine learning models trained on recent patterns remain accurate.

   Typical use cases include:

   - Congestion management on electricity distribution grids
   - Transport capacity forecasting
   - EV charging capacity estimation
   - Grid loss prediction
   - Solar park and wind park output forecasting

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a gradient boosting library directly requires you to build all the surrounding infrastructure yourself: time-aware train/test splits, energy-specific feature engineering, quantile regression for uncertainty bands, backtesting pipelines, and evaluation metrics. OpenSTEF provides all of this out of the box.

   Key differentiators:

   - **Probabilistic forecasts** — produces uncertainty bandwidths (quantiles), not just a single point prediction.
   - **Domain knowledge built in** — features like solar radiation estimates, holiday calendars, and lag features are included automatically.
   - **End-to-end pipelines** — from raw time series data to a trained, evaluated, and versioned model in a few lines of code.
   - **Model-agnostic** — swap between XGBoost, LightGBM, and other backends without changing your pipeline code.

.. dropdown:: Is OpenSTEF only useful for grid operators?
   :icon: question

   No. While OpenSTEF was built to solve grid congestion problems at Alliander, the library is general-purpose for any energy time series forecasting task. If you have a time series of energy measurements (a solar park, a building, a substation, a wind farm) and want accurate short-term forecasts with uncertainty estimates, OpenSTEF is applicable.

----

Installation and Requirements
------------------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (up to, but not including, Python 4.0). It runs on Linux, macOS, and Windows.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   Install the complete framework with a single command:

   .. code-block:: bash

      pip install openstef

   This installs four packages: ``openstef-beam``, ``openstef-core``, ``openstef-meta``, and ``openstef-models``.

   If you only need specific functionality, install individual packages:

   .. code-block:: bash

      # Core data structures and utilities only
      pip install openstef-core

      # Backtesting, evaluation, and metrics
      pip install openstef-beam

      # Forecasting models (LightGBM, XGBoost, etc.)
      pip install openstef-models

   Verify your installation:

   .. code-block:: python

      import openstef_beam
      print(openstef_beam.__version__)

      import openstef_core
      print(openstef_core.__version__)

.. dropdown:: How do I install optional model backends like LightGBM or XGBoost?
   :icon: question

   The ``openstef-models`` package has optional extras for each backend:

   .. code-block:: bash

      # LightGBM support
      pip install openstef-models[lgbm]

      # XGBoost on CPU (Linux/Windows)
      pip install openstef-models[xgb-cpu]

      # XGBoost with GPU support
      pip install openstef-models[xgb-gpu]

   If you installed the top-level ``openstef`` meta-package, LightGBM is included by default. XGBoost must be added explicitly if you need it.

.. dropdown:: What are the core dependencies?
   :icon: info

   The main runtime dependencies across the OpenSTEF packages are:

   - ``numpy``, ``pandas``, ``pyarrow`` — data handling
   - ``pydantic`` — configuration and data validation
   - ``joblib`` — parallel processing
   - ``pvlib`` — solar irradiance calculations for PV feature engineering
   - ``holidays`` — public holiday calendars for feature engineering
   - ``mlflow-skinny`` — model tracking and versioning
   - ``plotly`` — interactive evaluation plots
   - ``scoringrules`` — probabilistic forecast scoring
   - ``pyyaml`` — configuration file support

----

Models and Forecasting
----------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several gradient boosting models in the ``openstef-models`` package:

   - **LGBMForecaster** — LightGBM-based multi-quantile forecaster, the recommended default for most use cases.
   - **LGBMLinearForecaster** — LightGBM with a linear tree structure, useful when interpretability matters.
   - **XGBoostForecaster** — XGBoost-based multi-quantile forecaster, a strong alternative with GPU support.

   All models produce probabilistic (quantile) forecasts rather than single-point predictions, giving you uncertainty estimates alongside the central forecast.

.. dropdown:: Which model should I start with?
   :icon: light-bulb

   Start with **LightGBM** (``LGBMForecaster``). It trains faster than XGBoost on CPU, handles missing values gracefully, and performs well across a wide range of energy forecasting tasks. Switch to XGBoost if you have GPU hardware available or if benchmarking shows it performs better on your specific data.

   .. code-block:: python

      from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

      model = LGBMForecaster()

.. dropdown:: What are probabilistic forecasts and why does OpenSTEF produce them?
   :icon: question

   A probabilistic forecast produces a range of possible outcomes rather than a single number. OpenSTEF uses **quantile regression** to estimate, for example, the 10th, 50th, and 90th percentiles of future load. This means you get a central forecast (the median) plus lower and upper bounds that represent uncertainty.

   For grid operations, this matters: knowing that load will be between 80 MW and 120 MW is far more actionable than knowing the point estimate is 100 MW. Operators can make risk-aware decisions about when to intervene.

.. dropdown:: Can I use my own custom model?
   :icon: question

   Yes. OpenSTEF is model-agnostic by design. You can implement the ``Forecaster`` base class from ``openstef_models`` to wrap any model — scikit-learn compatible estimators, PyTorch models, or anything else — and use it within OpenSTEF pipelines. See :doc:`user_guide/index` for details on extending the framework.

----

Data and Configuration
----------------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   OpenSTEF works with time series data as pandas ``DataFrame`` objects with a ``DatetimeIndex``. The target column is the energy load measurement you want to forecast. Additional columns (weather data, calendar features) can be included and OpenSTEF will incorporate them into feature engineering automatically.

   Configuration for models and pipelines is handled through Pydantic models, which can be loaded from YAML files:

   .. code-block:: python

      from openstef_core.base_model import read_yaml_config

      config = read_yaml_config("my_config.yaml", MyConfigClass)

.. dropdown:: Does OpenSTEF handle missing data?
   :icon: question

   Yes. Data preprocessing — including handling of missing values — is part of the built-in pipeline. The underlying gradient boosting models (LightGBM in particular) also have native support for missing values, so gaps in your input data do not require manual imputation before training.

.. dropdown:: How does OpenSTEF handle solar and weather features?
   :icon: info

   OpenSTEF includes domain-specific feature engineering for energy forecasting. This includes using ``pvlib`` to estimate solar irradiance and PV generation potential from location and time, as well as calendar features (hour of day, day of week, public holidays by country). These features are generated automatically as part of the pipeline, so you do not need to construct them manually.

----

Backtesting and Evaluation
--------------------------

.. dropdown:: How do I evaluate forecast quality?
   :icon: question

   The ``openstef-beam`` package (Backtesting, Evaluation, Analysis and Metrics) provides tools for running backtests and computing forecast skill scores. It supports proper time-series cross-validation (no data leakage) and probabilistic scoring rules via the ``scoringrules`` library.

   .. code-block:: bash

      pip install openstef-beam[baselines]

   See :doc:`user_guide/index` for a full backtesting walkthrough.

.. dropdown:: Is there a benchmark dataset I can use to test my setup?
   :icon: light-bulb

   Yes. Alliander publishes the **2021 Energy Forecasting Benchmark**, an open-source dataset with 50+ energy signals covering solar parks, wind parks, MV feeders, transformers, and district heating. It is designed to be runnable out of the box with ``openstef-beam`` and is the same benchmark used internally to detect regressions in the library.

   The benchmark is available on GitHub alongside the OpenSTEF project.

----

Project and Community
---------------------

.. dropdown:: Is OpenSTEF production-ready?
   :icon: question

   The current release is **V4 Alpha**. It is already running in production at Alliander for congestion management across 10,000+ grid locations, so the core functionality is battle-tested. However, the V4 API is still stabilising and breaking changes may occur before the stable release. V3 remains available if you need a stable API today.

.. dropdown:: How do I get help or contribute?
   :icon: info

   The OpenSTEF community is active and welcoming to new contributors:

   - **Slack** — for questions and discussion
   - **GitHub** — public backlog with issues, stories, and milestones; look for "good first issues" to get started
   - **Bi-weekly community meetings** — open to all
   - **Co-coding sessions** — held every 8 weeks

   The project follows the Linux Foundation Energy governance model and is open to contributions from anyone.

.. dropdown:: What licence does OpenSTEF use?
   :icon: info

   OpenSTEF is released under the **Mozilla Public License 2.0 (MPL-2.0)**. This is a weak copyleft licence: you can use OpenSTEF in proprietary applications, but modifications to OpenSTEF source files themselves must be shared under the same licence.