FAQ
===

This FAQ answers the most common questions from new users of OpenSTEF — covering what the library does, how to install it, which models to use, and how to get started quickly. If you don't find your answer here, check the :doc:`user_guide/index` or open a discussion on GitHub.

.. note::
   OpenSTEF is currently in **V4 Alpha**. Some APIs may change before the stable release.

---

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building and running short-term energy load forecasts. It provides complete machine learning pipelines — data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing — all in one framework.

   It is **not** a single model or a standalone application. You import it as a library and integrate it into your own code or data infrastructure.

   OpenSTEF is developed and used in production at Alliander, a Dutch grid operator, where it generates forecasts for over 10,000 grid locations.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term means predicting energy load **hours to days ahead** — typically up to 48 hours into the future. This is the horizon relevant for operational decisions such as congestion management, EV charging capacity planning, and grid loss prediction.

   OpenSTEF is not designed for long-term capacity planning (months or years ahead). For that horizon, different modelling approaches apply.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a gradient boosting model directly gives you a point prediction. OpenSTEF adds several layers on top of that:

   - **Probabilistic forecasts** — outputs quantile-based uncertainty bands, not just a single value.
   - **Energy-domain feature engineering** — built-in features like solar radiation estimates, PV generation proxies, calendar effects, and lag features tuned for energy time series.
   - **Complete pipelines** — training, backtesting, evaluation, and scoring are all handled by the library, not assembled by hand.
   - **Model-agnostic design** — swap between XGBoost, LightGBM, or custom models without rewriting your pipeline.

   In short, OpenSTEF handles the energy-specific boilerplate so you can focus on your forecasting problem.

.. dropdown:: Who uses OpenSTEF?
   :icon: question

   OpenSTEF was created by data scientists at Alliander, a major Dutch electricity grid operator. It is used in production for congestion management: forecasting load at grid points two days ahead to identify peak moments and coordinate demand reduction with customers.

   The library is open-source under the Mozilla Public License 2.0 and is part of the LF Energy ecosystem, making it available to any organisation working on energy forecasting.

---

Installation & Requirements
----------------------------

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or higher** (but below 4.0). If you are on an older Python version, you will need to upgrade before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the meta-package, which pulls in all sub-packages:

   .. code-block:: python

      # From your terminal:
      # pip install openstef

   This installs ``openstef-beam``, ``openstef-core``, ``openstef-meta``, and ``openstef-models``.

   If you only need specific functionality, install individual packages:

   .. code-block:: bash

      pip install openstef-core        # Core data structures and utilities
      pip install openstef-models      # Forecasting models (XGBoost, LightGBM)
      pip install openstef-beam        # Backtesting, evaluation, and metrics

   See :doc:`installation` for the full guide including optional extras.

.. dropdown:: What are the optional extras for model backends?
   :icon: checklist

   The ``openstef-models`` package supports optional model backends:

   .. code-block:: bash

      pip install openstef-models[lgbm]       # LightGBM support
      pip install openstef-models[xgb-cpu]    # XGBoost (CPU-only, Linux/Windows/macOS)
      pip install openstef-models[xgb-gpu]    # XGBoost with GPU support

   If you install the top-level ``openstef`` meta-package, LightGBM is included by default via ``openstef-meta``.

.. dropdown:: How do I verify my installation is working?
   :icon: checklist

   Run this in a Python session after installing:

   .. code-block:: python

      import openstef_beam
      import openstef_core

      print(openstef_beam.__version__)
      print(openstef_core.__version__)

   If both print version strings without errors, your installation is healthy.

.. dropdown:: Does OpenSTEF work on Windows?
   :icon: question

   Yes. The XGBoost CPU extra uses a platform-specific wheel (``xgboost-cpu`` on Linux/Windows, standard ``xgboost`` on macOS), but this is handled automatically by pip. Install with:

   .. code-block:: bash

      pip install openstef-models[xgb-cpu]

   GPU support is available cross-platform via ``openstef-models[xgb-gpu]``.

---

Models & Forecasting
--------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with gradient boosting tree models out of the box:

   - **XGBoost** — ``XGBoostForecaster``, available via ``openstef-models[xgb-cpu]`` or ``[xgb-gpu]``
   - **LightGBM** — ``LGBMForecaster``, available via ``openstef-models[lgbm]``
   - **LightGBM Linear** — ``LGBMLinearForecaster``, a LightGBM variant with linear tree leaves

   All models support **multi-quantile regression**, meaning they produce probabilistic forecasts (e.g., the 10th, 50th, and 90th percentile of the load distribution) rather than a single point estimate.

   The library is model-agnostic by design — you can integrate custom models by implementing the ``Forecaster`` interface from ``openstef_models``.

.. dropdown:: What are probabilistic forecasts and why do they matter?
   :icon: light-bulb

   A probabilistic forecast gives you a **range of likely outcomes** rather than a single predicted value. For example, instead of "load will be 150 MW at 14:00", you get "there is a 90% chance load will be between 130 MW and 170 MW".

   This matters for energy grid operations because decisions like whether to call a customer to reduce consumption depend on the *risk* of exceeding a limit, not just the expected value. Uncertainty bands let operators make risk-aware decisions.

   OpenSTEF produces these bands using quantile regression — each model is trained to predict a specific quantile of the target distribution simultaneously.

.. dropdown:: How do I choose between XGBoost and LightGBM?
   :icon: light-bulb

   Both are strong gradient boosting implementations and will perform similarly on most energy forecasting tasks. Practical guidance:

   - **LightGBM** tends to train faster on large datasets and uses less memory. It is a good default choice.
   - **XGBoost** is often more familiar to practitioners and has mature GPU support. Use ``[xgb-gpu]`` if you have a CUDA-capable GPU and large training sets.
   - **LightGBM Linear** is worth trying when your target has strong linear relationships with some features (e.g., temperature-driven heating load).

   When in doubt, start with LightGBM and benchmark against XGBoost using ``openstef-beam``'s backtesting utilities.

.. dropdown:: Can I use my own custom model with OpenSTEF?
   :icon: question

   Yes. OpenSTEF is model-agnostic. Implement the ``Forecaster`` base class from ``openstef_models`` and your model will work with the rest of the pipeline — feature engineering, evaluation, and backtesting included.

   .. code-block:: python

      from openstef_models.models.forecasting.forecaster import Forecaster

      class MyCustomForecaster(Forecaster):
          # Implement required methods: fit(), predict(), etc.
          ...

   See :doc:`user_guide/custom_models` for a full walkthrough.

---

Data & Features
---------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   At minimum, OpenSTEF needs a **time-indexed pandas DataFrame** with a target column (the load or generation value you want to forecast) and a datetime index. Weather data (temperature, solar irradiance, wind speed) is strongly recommended as it significantly improves forecast accuracy.

   OpenSTEF's feature engineering layer automatically derives additional features from your timestamps (hour of day, day of week, public holidays) and from weather inputs (e.g., estimated PV generation from solar irradiance).

   See :doc:`user_guide/data_preparation` for expected formats and column naming conventions.

.. dropdown:: Do I need weather data to use OpenSTEF?
   :icon: question

   No, but it helps significantly. OpenSTEF will work with only historical load data, using calendar and lag features. However, for solar parks, wind assets, or any load with strong weather dependence, providing weather forecasts as input features will substantially improve accuracy.

   OpenSTEF includes built-in feature engineering for solar radiation (converting irradiance to estimated PV output using ``pvlib`` under the hood), so you don't need to pre-process weather data yourself.

.. dropdown:: What is openstef-beam and when do I need it?
   :icon: question

   ``openstef-beam`` stands for **Backtesting, Evaluation, Analysis and Metrics**. It is the sub-package you use to:

   - Run backtests to evaluate how well a model would have performed historically
   - Compute scoring metrics (e.g., CRPS for probabilistic forecasts)
   - Analyse forecast errors and model behaviour
   - Compare models or configurations systematically

   You don't need it to make forecasts — ``openstef-core`` and ``openstef-models`` are sufficient for that. Add ``openstef-beam`` when you want to rigorously evaluate or compare models.

   .. code-block:: python

      from openstef_beam.backtesting import BacktestPipeline

---

Common Setup Questions
----------------------

.. dropdown:: I get an import error after installing. What should I check?
   :icon: alert

   The most common causes are:

   1. **Wrong Python version** — OpenSTEF requires Python >=3.12. Check with ``python --version``.
   2. **Missing optional extra** — if you see ``MissingExtraError``, you need to install an optional dependency. For example, ``import lightgbm`` failing means you need ``pip install openstef-models[lgbm]``.
   3. **Virtual environment not activated** — make sure you installed into the same environment you are running from.

   .. code-block:: bash

      python --version          # Should be 3.12+
      pip show openstef-core    # Confirms the package is installed

.. dropdown:: How do I configure OpenSTEF using YAML files?
   :icon: question

   OpenSTEF uses Pydantic-based configuration models that can be read from and written to YAML files. This is useful for reproducible experiments and production deployments.

   .. code-block:: python

      from openstef_core.base_model import read_yaml_config, write_yaml_config
      from openstef_models.config import ForecastingConfig  # example config class

      # Load config from file
      config = read_yaml_config("my_config.yaml", ForecastingConfig)

      # Save config to file
      write_yaml_config(config, "my_config.yaml")

   See :doc:`user_guide/configuration` for available configuration options per pipeline.

.. dropdown:: Where can I find example datasets to try OpenSTEF?
   :icon: light-bulb

   OpenSTEF includes built-in datasets via ``openstef_core.datasets`` for testing and experimentation:

   .. code-block:: python

      from openstef_core.datasets import load_example_dataset

      df = load_example_dataset()
      print(df.head())

   For realistic benchmarking, the **Alliander 2021 Energy Forecasting Benchmark** is publicly available on GitHub. It contains 50+ real energy signals (solar parks, wind parks, MV feeders, district heating) and is designed to be run out-of-the-box with OpenSTEF.

.. dropdown:: Where do I go if I have more questions?
   :icon: info

   - **Documentation** — browse the :doc:`user_guide/index` for tutorials and how-to guides.
   - **GitHub Issues** — report bugs or request features on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_.
   - **Community Slack** — join the LF Energy Slack workspace for discussion with maintainers and other users.
   - **Bi-weekly community meetings** — open to all; check the GitHub repository for the schedule.