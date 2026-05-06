FAQ
===

This FAQ answers the most common questions from new users of OpenSTEF — covering what the library does, how to install it, which models to use, and how to get started quickly. If you don't find your answer here, check the :doc:`user_guide/index` or open a discussion on GitHub.

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building and running short-term energy load forecasts. It provides complete machine learning pipelines — data preprocessing, feature engineering, model training, prediction, evaluation, and post-processing — all tuned for energy time series data.

   OpenSTEF is **model-agnostic**: it is not tied to a single algorithm. It ships with gradient boosting models (XGBoost, LightGBM) out of the box, but the framework is designed so you can plug in your own models.

   It is developed and maintained by Alliander, a Dutch grid operator, and is used in production to make forecasts for over 10,000 grid locations.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term means predicting energy load **hours to days ahead** — typically up to 48 hours into the future. This horizon is long enough to be useful for operational decisions (congestion management, scheduling, dispatch) but short enough that weather forecasts and historical patterns are still reliable predictors.

   OpenSTEF is not designed for long-term capacity planning (months or years ahead). For that horizon, different modelling approaches apply.

.. dropdown:: What can I use OpenSTEF for?
   :icon: light-bulb

   OpenSTEF was built for grid operators, but the library is general-purpose for any energy time series forecasting task. Common use cases include:

   - **Congestion management** — forecast load at grid points to identify when equipment limits will be exceeded
   - **Transport forecasts** — predict how much energy will flow through a cable or transformer
   - **EV charging capacity estimation** — anticipate demand from electric vehicle charging
   - **Grid loss prediction** — estimate technical losses across the network
   - **Solar and wind generation forecasting** — built-in feature engineering converts weather data into generation estimates

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using XGBoost directly gives you a model. OpenSTEF gives you a **complete forecasting system**:

   - **Domain-specific feature engineering** — built-in transformations for energy data, including solar radiation to PV generation estimates, calendar features, and lag features tuned for load patterns
   - **Probabilistic forecasts** — every prediction comes with uncertainty bandwidths (quantile regression), not just a single point estimate
   - **Backtesting and evaluation** — the ``openstef-beam`` package (Backtesting, Evaluation, Analysis and Metrics) provides structured pipelines for measuring forecast accuracy
   - **Production-ready pipelines** — preprocessing, training, and inference are packaged as reusable components, not loose scripts

   If you only need a quick model, scikit-learn is fine. If you need reliable, maintainable energy forecasts in production, OpenSTEF handles the hard parts.

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or higher** (up to, but not including, Python 4.0).

   .. code-block:: python

      import sys
      print(sys.version)  # Should show 3.12.x or higher

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   Install the full framework with a single command:

   .. code-block:: bash

      pip install openstef

   This installs four packages: ``openstef-beam``, ``openstef-core``, ``openstef-meta``, and ``openstef-models``.

   If you only need specific functionality, install individual packages:

   .. code-block:: bash

      # Core data structures and utilities only
      pip install openstef-core

      # Models (XGBoost, LightGBM) — includes openstef-core
      pip install openstef-models

      # Backtesting and evaluation — includes openstef-core
      pip install openstef-beam

   Verify your installation:

   .. code-block:: python

      import openstef_beam
      import openstef_core
      print(openstef_beam.__version__)
      print(openstef_core.__version__)

   See :doc:`installation` for the full installation guide including optional extras.

.. dropdown:: What are the optional install extras?
   :icon: info

   Some model backends are optional to keep the base install lightweight:

   .. code-block:: bash

      # LightGBM support
      pip install "openstef-models[lgbm]"

      # XGBoost (CPU-optimised build on Linux/Windows/macOS)
      pip install "openstef-models[xgb-cpu]"

      # XGBoost with GPU support
      pip install "openstef-models[xgb-gpu]"

      # openstef-beam with S3 support and baseline models
      pip install "openstef-beam[all]"

   If you installed the top-level ``openstef`` meta-package, LightGBM is already included.

.. dropdown:: Which model should I use — XGBoost or LightGBM?
   :icon: question

   Both are gradient boosting tree models and produce probabilistic (multi-quantile) forecasts. In practice:

   - **LightGBM** (``LGBMForecaster``) trains faster and uses less memory, which makes it a good default for large datasets or frequent retraining.
   - **XGBoost** (``XGBoostForecaster``) is well-established and may perform better on some datasets after hyperparameter tuning.

   The best approach is to benchmark both on your data using ``openstef-beam``. OpenSTEF's model-agnostic design means switching between them requires changing only the model class — the rest of the pipeline stays the same.

   .. code-block:: python

      from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
      from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

      # Swap the model class — everything else is identical
      model = LGBMForecaster()
      # model = XGBoostForecaster()

.. dropdown:: What does a probabilistic forecast mean?
   :icon: info

   Instead of predicting a single value ("load will be 150 MW at 14:00"), OpenSTEF predicts **a range of outcomes at different confidence levels** using quantile regression. For example, it might output:

   - P10: 130 MW (10% chance load will be below this)
   - P50: 150 MW (median estimate)
   - P90: 172 MW (90% chance load will be below this)

   This is more useful for operational decisions than a point forecast because it communicates uncertainty explicitly. A grid operator can plan conservatively using the P90 value, or optimistically using the P10 value, depending on the risk profile of the decision.

.. dropdown:: What data do I need to get started?
   :icon: question

   At minimum you need a **time series of historical load measurements** — a pandas DataFrame with a datetime index and a target column (e.g., load in MW). The higher the resolution and the longer the history, the better.

   OpenSTEF's feature engineering can enrich your data automatically if you also provide:

   - **Weather data** — temperature, wind speed, solar irradiance (used to build features for weather-sensitive loads)
   - **Calendar information** — automatically derived from the datetime index (day of week, holidays, etc.)

   Built-in dataset utilities in ``openstef-core`` provide example datasets so you can experiment before connecting your own data source.

   .. code-block:: python

      from openstef_core.datasets import TimeSeriesDataset
      # Load a built-in example dataset to explore the expected data format

.. dropdown:: Is OpenSTEF suitable for non-energy time series?
   :icon: question

   The core ML pipeline (preprocessing, training, evaluation) is general-purpose and can be applied to any time series regression problem. However, some feature engineering is energy-specific — for example, the solar radiation to PV generation conversion uses ``pvlib`` and assumes energy domain context.

   If your data is not energy-related, you can still use OpenSTEF's pipeline infrastructure and models, but you may want to skip or replace the domain-specific feature transformations.

.. dropdown:: How is OpenSTEF structured — what do the packages do?
   :icon: info

   OpenSTEF is split into four packages:

   - **openstef-core** — foundational data structures, base classes, dataset utilities, and shared utilities used by all other packages
   - **openstef-models** — forecasting model implementations (XGBoost, LightGBM, LightGBM-Linear) with quantile regression support
   - **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics; pipelines for measuring and comparing forecast accuracy
   - **openstef-meta** — meta-models that combine outputs from multiple base models

   For most users, installing ``openstef`` (the top-level meta-package) is the right choice. Install individual packages only if you have strict dependency constraints.

.. dropdown:: Where can I find more help?
   :icon: light-bulb

   - **Documentation** — start with :doc:`user_guide/index` for tutorials and worked examples
   - **GitHub** — browse the source code, open issues, or check the public backlog for planned features
   - **Community meetings** — the OpenSTEF community holds bi-weekly meetings; details are on the project's GitHub page
   - **Slack** — the project has a community Slack for questions and discussion

   .. note::

      OpenSTEF V4 is currently in **alpha**. APIs may change between releases. Pin your dependency versions in production and watch the changelog for breaking changes.