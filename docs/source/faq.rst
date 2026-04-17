FAQ
===

This page answers the most common questions from new OpenSTEF users — covering what the library does, how to install it, which models to use, and how to get your first forecast running. If you are looking for step-by-step guidance, see :doc:`getting_started`.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building accurate short-term load forecasts in the power grid domain. It provides complete machine learning pipelines — from data preprocessing and feature engineering through model training, probabilistic forecasting, evaluation, and post-processing — so you can focus on your forecasting problem rather than boilerplate infrastructure.

   OpenSTEF is **not** a single model or a standalone application. It is a modular framework you import and use in your own Python code or notebooks.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load **hours to days ahead** — typically up to 48 hours into the future. This time horizon is critical for operational decisions such as congestion management, EV charging capacity planning, transport forecasts, and grid loss prediction.

   OpenSTEF was originally developed at Alliander, a Dutch grid operator, to forecast load at individual grid points two days ahead. This allows operators to identify peak moments and coordinate demand reduction with customers before equipment limits are exceeded.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Several things set OpenSTEF apart from a bare ML library:

   - **Domain knowledge built in** — feature engineering specific to energy forecasting is included out of the box, such as converting solar radiation data into PV generation estimates using ``pvlib``.
   - **Probabilistic forecasts** — instead of a single point prediction, OpenSTEF produces multiple quantiles so you get uncertainty bandwidths alongside the forecast.
   - **Model-agnostic pipelines** — swap between XGBoost, LightGBM, GBLinear, and other models without rewriting your pipeline.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides structured backtesting, scoring, and visualisation utilities designed for time series.
   - **Production-ready structure** — pipelines are configured via validated ``pydantic`` config objects, making them reproducible and easy to version.

.. dropdown:: Who develops and maintains OpenSTEF?
   :icon: info

   OpenSTEF is developed by data science software engineers at **Alliander**, a major Dutch electricity grid operator. It is released as open-source software under the MPL-2.0 licence. The project is actively maintained and was presented at FOSDEM 2026 as part of the V4 alpha release.

----

Installation & Requirements
----------------------------

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (``>=3.12,<4.0``). Make sure your environment meets this requirement before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the meta-package, which pulls in all sub-packages:

   .. code-block:: bash

      pip install openstef

   This installs four packages:

   - ``openstef-core`` — core data structures, preprocessing, and utilities
   - ``openstef-models`` — forecasting models (XGBoost, LightGBM, GBLinear, etc.)
   - ``openstef-beam`` — backtesting, evaluation, analysis, and metrics
   - ``openstef-meta`` — meta-models that combine multiple forecasters

   If you only need specific functionality, install individual packages instead:

   .. code-block:: bash

      pip install openstef-core          # core only
      pip install openstef-models        # models + core
      pip install openstef-beam          # evaluation + core

.. dropdown:: How do I install XGBoost or LightGBM support?
   :icon: checklist

   These are optional extras on ``openstef-models``. Install the one you need:

   .. code-block:: bash

      # LightGBM
      pip install "openstef-models[lgbm]"

      # XGBoost (CPU)
      pip install "openstef-models[xgb-cpu]"

      # XGBoost (GPU)
      pip install "openstef-models[xgb-gpu]"

   If you install the top-level ``openstef`` meta-package, LightGBM is included by default. XGBoost must be added explicitly if you need it.

.. dropdown:: How do I verify my installation?
   :icon: checklist

   Run the following in Python to confirm the packages are importable and check their versions:

   .. code-block:: python

      import openstef_core
      import openstef_models
      import openstef_beam

      print(openstef_core.__version__)
      print(openstef_models.__version__)
      print(openstef_beam.__version__)

   If any import fails, check that you are in the correct virtual environment and that the package was installed successfully.

----

Models & Configuration
-----------------------

.. dropdown:: Which model should I use?
   :icon: light-bulb

   OpenSTEF supports several model types. Here is a practical guide:

   - **GBLinear** — a gradient-boosted linear model. A good default choice for energy forecasting because it can extrapolate beyond the training range (important for rare peak events), trains quickly, and produces interpretable feature importances.
   - **XGBoost** — a powerful gradient-boosted tree model. Well-suited when you have large datasets and want strong predictive performance. Requires the ``xgb-cpu`` or ``xgb-gpu`` extra.
   - **LightGBM** — similar to XGBoost but often faster to train, especially on larger datasets. Requires the ``lgbm`` extra.

   If you are unsure, start with GBLinear and benchmark against LightGBM using the backtesting tools in ``openstef-beam``.

.. dropdown:: What are quantiles and why does OpenSTEF use them?
   :icon: question

   A quantile forecast expresses **uncertainty** around a prediction. Instead of returning a single number, OpenSTEF returns multiple quantiles — for example, the 10th, 50th, and 90th percentiles of the predicted load.

   This is more useful than a point forecast for operational decisions: you can see not just the expected load, but also a plausible worst-case (high quantile) and best-case (low quantile). Grid operators use these bands to decide when to intervene.

   You specify which quantiles you want in the workflow configuration:

   .. code-block:: python

      from openstef_core.types import Q

      quantiles = [Q(0.1), Q(0.5), Q(0.9)]  # 10th, median, 90th percentile

.. dropdown:: How do I configure a forecasting workflow?
   :icon: question

   Use ``ForecastingWorkflowConfig`` and ``create_forecasting_workflow`` from ``openstef_models.presets``:

   .. code-block:: python

      from openstef_core.types import LeadTime, Q
      from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

      workflow = create_forecasting_workflow(
          config=ForecastingWorkflowConfig(
              model="gblinear",                        # model type
              forecast_horizons=[LeadTime(hours=h) for h in range(1, 37)],  # 1–36 h ahead
              quantiles=[Q(0.1), Q(0.5), Q(0.9)],     # prediction intervals
              feature_columns=["temperature", "irradiance", "wind_speed"],
          )
      )

   See :doc:`getting_started` for a complete end-to-end example.

.. dropdown:: Can I tune hyperparameters?
   :icon: question

   Yes. Each model exposes a typed ``HyperParams`` class (backed by ``pydantic``) that you can customise. For example, to configure LightGBM:

   .. code-block:: python

      from openstef_models.models.forecasting.lgbm_forecaster import LGBMHyperParams

      hyperparams = LGBMHyperParams(
          n_estimators=200,
          max_depth=8,
          learning_rate=0.1,
          reg_alpha=0.1,
          reg_lambda=1.0,
      )

   Pass the ``hyperparams`` object when constructing your forecaster. All fields are validated at instantiation time, so misconfigured values are caught early.

----

Data & Features
----------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   At minimum you need a time-indexed ``pandas.DataFrame`` with a ``load`` column (energy consumption in MW or a consistent unit). Weather features such as ``temperature``, ``irradiance``, and ``wind_speed`` are strongly recommended — they are the most important drivers of short-term load variation.

   OpenSTEF wraps your data in typed dataset objects (``TimeSeriesDataset``, ``ForecastInputDataset``) from ``openstef_core.datasets``. These enforce the expected structure and make pipelines self-documenting.

   .. code-block:: python

      import pandas as pd
      from openstef_core.datasets import TimeSeriesDataset

      df = pd.read_parquet("my_load_data.parquet")  # must have DatetimeIndex + 'load' column
      dataset = TimeSeriesDataset(data=df)

.. dropdown:: Does OpenSTEF handle solar PV generation automatically?
   :icon: light-bulb

   Yes. OpenSTEF includes built-in feature engineering that converts raw solar irradiance data into estimated PV generation using ``pvlib``. This domain-specific knowledge is one of the reasons OpenSTEF outperforms generic ML pipelines on net-load forecasting tasks where rooftop solar is a significant factor.

   You do not need to pre-process irradiance yourself — provide it as a feature column and the pipeline handles the conversion.

.. dropdown:: Can I use my own custom features?
   :icon: question

   Yes. You can pass any additional columns in your input ``DataFrame`` and list them in ``feature_columns`` when configuring the workflow. OpenSTEF will include them alongside its built-in engineered features. Custom features should be available at forecast time (i.e., they must be forecastable themselves, such as NWP weather variables).

----

Evaluation & Backtesting
-------------------------

.. dropdown:: How do I evaluate forecast quality?
   :icon: question

   The ``openstef-beam`` package provides structured backtesting and scoring utilities. A backtest replays the training and forecasting process over historical periods so you get realistic out-of-sample performance metrics.

   .. code-block:: python

      pip install openstef-beam

   See the backtesting documentation for details on running a backtest and interpreting the resulting skill scores and reliability diagrams.

.. dropdown:: What metrics does OpenSTEF report?
   :icon: question

   OpenSTEF reports standard regression metrics (MAE, RMSE, R²) as well as probabilistic scoring rules appropriate for quantile forecasts, such as the **Continuous Ranked Probability Score (CRPS)**. These are provided by ``openstef-beam`` via the ``scoringrules`` dependency.

   Probabilistic metrics are important because they reward forecasters that are both accurate *and* well-calibrated — a narrow uncertainty band that is always wrong is penalised more than a wider, honest band.

----

Troubleshooting
---------------

.. dropdown:: I get an ImportError for xgboost or lightgbm — what do I do?
   :icon: alert

   These are optional dependencies. Install the relevant extra:

   .. code-block:: bash

      pip install "openstef-models[lgbm]"      # for LightGBM
      pip install "openstef-models[xgb-cpu]"   # for XGBoost on CPU

   If you installed the base ``openstef`` meta-package without extras, LightGBM is already included. XGBoost is not — you must add it explicitly.

.. dropdown:: My forecast looks flat or unrealistic — what should I check?
   :icon: alert

   A few common causes:

   - **Missing weather features** — without temperature and irradiance, the model has little signal to work with. Ensure your input data includes relevant meteorological variables.
   - **Insufficient training data** — gradient boosting models need enough historical data to learn seasonal and daily patterns. Aim for at least one full year of training data.
   - **Wrong time zone or index alignment** — make sure your load data and weather features share the same ``DatetimeIndex`` with consistent time zone handling. Misaligned timestamps are a frequent source of poor forecasts.
   - **Data leakage** — check that future information is not accidentally included in your feature set during backtesting.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - Browse the rest of this documentation, starting with :doc:`getting_started`.
   - Check the project's GitHub repository for open issues and discussions.
   - For bugs or feature requests, open an issue on GitHub with a minimal reproducible example and the output of your version check (see the installation verification question above).