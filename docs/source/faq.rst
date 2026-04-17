FAQ
===

This page answers the most common questions from new users of OpenSTEF. Whether you are evaluating the library, setting it up for the first time, or trying to understand how it fits into your workflow, you should find a clear answer here. For deeper dives into specific topics, each answer links to the relevant documentation.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building accurate short-term load forecasts in the power grid domain. It provides complete machine learning pipelines — from data preprocessing and feature engineering through model training, probabilistic forecasting, evaluation, and post-processing — so you do not have to assemble these pieces yourself.

   "Short-term" means predicting energy load hours to a couple of days ahead. OpenSTEF is used in practice for congestion management, transport forecasts, EV charging capacity estimation, and grid loss prediction.

   See :doc:`getting_started` for a hands-on introduction.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   OpenSTEF is model-agnostic and sits *above* individual ML libraries. Three things set it apart:

   - **Domain knowledge baked in.** Feature engineering specific to energy forecasting is included out of the box — for example, converting solar radiation data into PV generation estimates using ``pvlib``, and handling energy-specific temporal patterns.
   - **Probabilistic forecasts by default.** Rather than a single point prediction, OpenSTEF produces multiple quantiles so you get uncertainty bandwidths alongside the forecast.
   - **End-to-end pipelines.** Training, backtesting, evaluation, and metrics are all part of the library. You configure a workflow rather than wiring together individual steps.

   Using XGBoost or LightGBM directly gives you a model. OpenSTEF gives you a forecasting system.

.. dropdown:: What is short-term energy forecasting, and why does it matter?
   :icon: question

   Short-term energy forecasting predicts electricity load at a specific grid point — typically 15-minute or hourly intervals — from a few hours up to roughly two days ahead. These forecasts are essential for:

   - **Congestion management** — identifying peak moments when load will exceed equipment limits, so grid operators can act in advance.
   - **Grid planning** — deciding where and when to reinforce infrastructure.
   - **Flexibility markets** — scheduling demand response or battery dispatch based on expected load.

   Accurate short-term forecasts allow grid operators to connect more customers and manage capacity constraints without waiting years for physical grid upgrades.

.. dropdown:: Who develops and maintains OpenSTEF?
   :icon: info

   OpenSTEF was created and is maintained by data science software engineers at **Alliander**, a Dutch distribution system operator. It is open-source under the MPL-2.0 licence and developed in the open. The library is used in production at Alliander for congestion management across the Dutch electricity grid.

----

Installation and Requirements
------------------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   - **Python** 3.12 or newer (Python < 3.12 is not supported)
   - A standard pip-compatible environment (virtualenv, conda, etc.)

   No special hardware is required for CPU-based models. GPU support for XGBoost is available as an optional extra (see below).

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest approach installs the complete framework in one command:

   .. code-block:: bash

      pip install openstef

   This pulls in all four sub-packages: ``openstef-beam``, ``openstef-core``, ``openstef-meta``, and ``openstef-models``.

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
      import openstef_core
      import openstef_models

   See :doc:`installation` for the full installation guide.

.. dropdown:: How do I install LightGBM or XGBoost support?
   :icon: question

   These model backends are optional extras. Install them alongside ``openstef-models``:

   .. code-block:: bash

      # LightGBM support
      pip install "openstef-models[lgbm]"

      # XGBoost (CPU)
      pip install "openstef-models[xgb-cpu]"

      # XGBoost (GPU)
      pip install "openstef-models[xgb-gpu]"

   If you try to use a model backend that is not installed, OpenSTEF raises a ``MissingExtraError`` with a clear message telling you which extra to install.

.. dropdown:: Can I install only the backtesting and evaluation tools without the models?
   :icon: question

   Yes. ``openstef-beam`` (Backtesting, Evaluation, Analysis and Metrics) is a standalone package:

   .. code-block:: bash

      pip install openstef-beam

   To also include baseline model comparisons, add the ``baselines`` extra:

   .. code-block:: bash

      pip install "openstef-beam[baselines]"

   This is useful if you want to evaluate forecasts produced by an external system using OpenSTEF's metrics and scoring infrastructure.

----

Models and Forecasting
-----------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several model backends in ``openstef-models``:

   - **XGBoost** — gradient boosted trees; robust general-purpose choice, available in CPU and GPU variants.
   - **LightGBM** — faster gradient boosting, often preferred for large datasets or frequent retraining.
   - **GBLinear** — gradient boosted linear model; extrapolates beyond training data, highly interpretable, fast to train. Particularly well-suited to energy forecasting.

   All models produce **probabilistic (quantile) forecasts** by default, not just point predictions.

.. dropdown:: Which model should I start with?
   :icon: light-bulb

   Start with **GBLinear** if you are new to the library or want interpretable results quickly. It trains fast, handles rare events better than tree-based models (because it can extrapolate), and its feature importances are straightforward to explain.

   Switch to **LightGBM** or **XGBoost** when you need to capture non-linear patterns or when you have enough historical data to benefit from deeper tree models.

   .. code-block:: python

      from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
      from openstef_models.presets.forecasting_workflow import GBLinearForecaster

      workflow = create_forecasting_workflow(
          config=ForecastingWorkflowConfig(
              model=GBLinearForecaster,
              # ... other config
          )
      )

.. dropdown:: What are quantile forecasts, and why does OpenSTEF use them?
   :icon: info

   A quantile forecast gives you a range of plausible outcomes rather than a single number. For example, the 10th and 90th percentile forecasts form an 80 % prediction interval — you can be reasonably confident the actual load will fall within that band.

   OpenSTEF produces quantile forecasts because grid operators need to know not just *what* the expected load is, but *how uncertain* that estimate is. A narrow band means high confidence; a wide band signals that conditions are volatile and more caution is warranted. This is especially important for congestion management decisions.

.. dropdown:: Does OpenSTEF handle weather data and solar generation automatically?
   :icon: question

   Yes. OpenSTEF's feature engineering pipeline includes domain-specific transformations for energy forecasting. Solar radiation inputs are converted to PV generation estimates using ``pvlib``, and the library understands energy-relevant temporal features such as time-of-day, day-of-week, and public holidays (via the ``holidays`` package).

   You provide the raw weather variables as input columns; OpenSTEF handles the domain-specific transformations as part of the pipeline.

----

Common Setup Questions
-----------------------

.. dropdown:: What data format does OpenSTEF expect?
   :icon: question

   OpenSTEF works with **pandas DataFrames** with a ``DatetimeIndex``. Your training data should include a ``load`` column (the target variable, in MW or a consistent unit) and any feature columns such as weather variables.

   .. code-block:: python

      import pandas as pd
      from openstef_core.datasets import TimeSeriesDataset

      # Load your data — must have a DatetimeIndex and a 'load' column
      df = pd.read_parquet("my_load_data.parquet")
      dataset = TimeSeriesDataset(data=df)

   See :doc:`getting_started` for a complete worked example with a real dataset.

.. dropdown:: Do I need MLflow or a database to use OpenSTEF?
   :icon: question

   No. ``mlflow-skinny`` is a dependency of ``openstef-models`` for experiment tracking, but you do not need to run an MLflow server to use the library. OpenSTEF can train and generate forecasts entirely in-memory without any external services.

   If you want to track experiments, compare model runs, or store artefacts, you can point MLflow at a local directory or a remote tracking server — but this is optional.

.. dropdown:: How do I run a backtest to evaluate forecast quality?
   :icon: question

   Use ``openstef-beam``, which provides backtesting pipelines and scoring utilities:

   .. code-block:: bash

      pip install "openstef-beam[baselines]"

   .. code-block:: python

      from openstef_beam.backtesting import Pipeline

      # Configure and run a backtesting pipeline
      pipeline = Pipeline(...)
      results = pipeline.run()

   Backtesting re-trains the model on rolling windows of historical data and scores each out-of-sample forecast, giving you a realistic picture of production performance. See :doc:`backtesting` for details.

.. dropdown:: Where can I find example notebooks and datasets?
   :icon: info

   The OpenSTEF documentation includes tutorial notebooks that use the **Liander 2024 Energy Forecasting Benchmark** dataset, which is freely available on HuggingFace Hub. The tutorials walk through the full workflow: downloading data, configuring a forecasting pipeline, training a model, and visualising results including feature importance.

   Start with :doc:`getting_started` for the guided tutorial, or browse :doc:`tutorials/index` for topic-specific examples.

.. dropdown:: I'm getting a MissingExtraError — what does that mean?
   :icon: alert

   This error means you are trying to use a model backend (such as LightGBM or XGBoost) that requires an optional dependency which is not installed. The error message will tell you exactly which extra to add.

   For example, if you see a ``MissingExtraError`` mentioning ``xgboost``:

   .. code-block:: bash

      pip install "openstef-models[xgb-cpu]"

   If it mentions ``lightgbm``:

   .. code-block:: bash

      pip install "openstef-models[lgbm]"

   After installing the extra, restart your Python session and try again.