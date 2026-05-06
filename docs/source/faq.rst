FAQ
===

This FAQ covers the most common questions from new users of OpenSTEF — from understanding what the library does, to installing it, choosing models, and running your first forecast. If you are looking for step-by-step instructions, see :doc:`getting_started/index`.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building and running machine learning pipelines that predict energy load hours to days into the future. It is **not** a deployable application or a hosted service — it is a framework you import and use in your own code.

   The library covers the full forecasting workflow: data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing. It is model-agnostic, meaning you can plug in different models (XGBoost, LightGBM, and others) without rewriting your pipeline.

   .. code-block:: python

      # OpenSTEF is a library — you import it like any other Python package
      import openstef_core
      import openstef_models
      import openstef_beam

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term means predicting energy load from a few hours up to roughly seven days ahead. Beyond seven days, weather forecasts lose the 15-minute resolution that solar and wind predictions depend on, so forecast quality degrades significantly.

   Typical horizons:

   - **Intraday** — next few hours, used for real-time grid balancing
   - **Day-ahead** — next 24–48 hours, the most common operational horizon
   - **Week-ahead** — up to ~7 days, used for capacity planning

.. dropdown:: What use cases is OpenSTEF designed for?
   :icon: question

   OpenSTEF was originally built at Alliander (a Dutch grid operator) and is now used in production for over 10,000 grid locations. The library is designed to be general enough for any energy forecasting task, including:

   - **Congestion management** — predicting peak load at substations so grid operators can call customers in advance to reduce consumption
   - **Transport forecasts** — communicating planned energy usage to upstream network operators (e.g., Alliander → TenneT)
   - **Grid loss forecasting** — estimating system losses for financial optimisation
   - **EV charging capacity estimation** — forecasting demand from electric vehicle charging infrastructure
   - **District heating** — thermal demand forecasting

   The library is not limited to Dutch or European grids. Holiday calendars, pricing signals, and other domain-specific inputs are configurable.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using XGBoost directly gives you a model. OpenSTEF gives you a complete, production-ready forecasting framework built on top of models like XGBoost and LightGBM. The key additions are:

   - **Energy-specific feature engineering** — built-in features such as solar radiation estimates, time-of-day cyclical encodings, and lag features tuned for energy time series
   - **Probabilistic forecasts** — outputs quantile forecasts (uncertainty bandwidths), not just a single point prediction
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides structured backtesting, scoring rules, and visualisation
   - **Modular pipelines** — preprocessing, training, and forecasting are separate, composable steps
   - **Domain knowledge included** — years of operational experience at a grid operator are encoded in the library's defaults

----

Installation and Requirements
------------------------------

.. dropdown:: What Python version does OpenSTEF require?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (``>=3.12,<4.0``). Make sure your environment meets this requirement before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the ``openstef`` meta-package, which pulls in all sub-packages:

   .. code-block:: bash

      pip install openstef

   This installs four packages:

   - ``openstef-core`` — data structures, preprocessing, and core utilities
   - ``openstef-models`` — forecasting models (XGBoost, LightGBM, and more)
   - ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM)
   - ``openstef-meta`` — meta-learning and forecast combination models

   If you only need specific functionality, install individual packages:

   .. code-block:: bash

      # Only core + models, no backtesting tooling
      pip install openstef-core openstef-models

      # Only backtesting and evaluation
      pip install openstef-beam

.. dropdown:: How do I verify my installation?
   :icon: checklist

   Import the packages and print their versions:

   .. code-block:: python

      import openstef_beam
      import openstef_core

      print(openstef_beam.__version__)
      print(openstef_core.__version__)

   If no ``ImportError`` is raised, the installation is working correctly.

.. dropdown:: Do I need a GPU to use OpenSTEF?
   :icon: question

   No. OpenSTEF works entirely on CPU by default. GPU support is available as an optional extra for XGBoost if you want faster training on large datasets:

   .. code-block:: bash

      # CPU-only XGBoost (default)
      pip install openstef-models[xgb-cpu]

      # GPU-accelerated XGBoost
      pip install openstef-models[xgb-gpu]

   For most forecasting tasks on typical grid datasets, CPU training is fast enough.

.. dropdown:: Does OpenSTEF require MLflow or a database?
   :icon: question

   No. In OpenSTEF V4, external dependencies like MLflow and database connectors have been decoupled from the core library. You can run OpenSTEF entirely in-memory without any external services. MLflow and other experiment tracking tools can be integrated optionally if your workflow requires them.

----

Models and Forecasting
-----------------------

.. dropdown:: Which models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several models in the ``openstef-models`` package:

   - **XGBoost** (``xgboost_forecaster``) — gradient boosting trees; the default and most battle-tested choice for energy forecasting
   - **LightGBM** (``lgbmlinear_forecaster``) — fast gradient boosting; useful for large datasets or when training speed matters
   - **Meta/ensemble models** — the ``openstef-meta`` package provides forecast combiners that blend predictions from multiple base models

   All models produce **probabilistic (quantile) forecasts**, not just a single point prediction.

   .. code-block:: python

      from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
      from openstef_models.models.forecasting.lgbmlinear_forecaster import LGBMLinearForecaster

.. dropdown:: Which model should I start with?
   :icon: light-bulb

   Start with **XGBoost**. It is the most thoroughly tested model in OpenSTEF and performs well across congestion management, transport forecasting, and grid loss use cases. LightGBM is a good alternative if you have very large datasets and training time is a concern.

   To compare models objectively on your own data, use the ``openstef-beam`` backtesting pipeline. The `Alliander 2021 Energy Forecasting Benchmark <https://github.com/alliander-opensource/energy-forecasting-benchmark>`_ is also publicly available and provides a realistic comparison across 50+ energy signals.

.. dropdown:: What are probabilistic forecasts and why do they matter?
   :icon: question

   A probabilistic forecast produces a range of predictions at different quantiles (e.g., the 10th, 50th, and 90th percentile) rather than a single number. This gives you an uncertainty bandwidth around the central forecast.

   For energy grid operations, this matters because:

   - **Congestion management** cares about the upper quantiles — you need to know when load *might* be high, not just the average expectation
   - **Risk-aware decisions** require knowing how confident the model is, not just what it predicts
   - **Operational planning** benefits from knowing the spread of possible outcomes

   OpenSTEF models output quantile forecasts by default. You do not need to configure anything special to get them.

.. dropdown:: How accurate are the forecasts?
   :icon: question

   Accuracy depends on three factors:

   1. **Use case** — congestion management optimises for peak detection, not nighttime accuracy; transport forecasts optimise for overall rMAE
   2. **Input data quality** — garbage in, garbage out; missing or noisy input data will degrade results
   3. **Metrics chosen** — RMSE, rMAE, peak detection rate, and rCRPS can tell very different stories about the same model

   Rather than quoting a single number, we recommend running the `Alliander 2021 Energy Forecasting Benchmark <https://github.com/alliander-opensource/energy-forecasting-benchmark>`_ on your own data using ``openstef-beam`` to get performance metrics and diagnostic plots relevant to your specific use case.

----

Common Setup Questions
-----------------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   OpenSTEF expects time series data as a ``pandas.DataFrame`` with a ``DatetimeIndex``. The core data structures are defined in ``openstef-core``:

   .. code-block:: python

      from openstef_core.datasets import ForecastInputDataset, TimeSeriesDataset

   At minimum you need:

   - A target variable (the load or energy signal you want to forecast)
   - A datetime index with consistent frequency (e.g., 15-minute intervals)
   - Optionally: weather features, calendar features, or other covariates

   OpenSTEF's feature engineering pipeline can automatically generate many useful features (lag features, time-of-day encodings, solar radiation estimates) from the raw time series.

.. dropdown:: Can I use OpenSTEF outside the Netherlands or Europe?
   :icon: question

   Yes. OpenSTEF V4 was explicitly designed to generalise beyond Alliander and the Netherlands. Holiday calendars, pricing signals, and other locale-specific inputs are configurable. The core forecasting logic does not assume any particular geography.

   If you are using features that depend on solar radiation or local holidays, make sure to configure those inputs for your region.

.. dropdown:: Is OpenSTEF V4 compatible with V3?
   :icon: alert

   OpenSTEF V4 is a major architectural refactor and is **not** backwards compatible with V3. The monolithic V3 package has been split into four focused sub-packages (``openstef-core``, ``openstef-models``, ``openstef-beam``, ``openstef-meta``), and many APIs have changed.

   .. note::

      If you are migrating from V3, refer to the migration guide in :doc:`getting_started/index` for a mapping of old APIs to their V4 equivalents.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - **GitHub Issues** — report bugs or request features on the `OpenSTEF GitHub repository <https://github.com/alliander-opensource/openstef>`_
   - **Community Slack** — join the community Slack for questions and discussion
   - **Bi-weekly community meetings** — open to all contributors and users
   - **Good first issues** — if you want to contribute, look for issues tagged ``good first issue`` on GitHub

   For documentation improvements, pull requests are welcome.