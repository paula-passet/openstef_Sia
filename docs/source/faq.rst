FAQ
===

This FAQ answers the most common questions from new OpenSTEF users — from understanding what the library does, to installing it, choosing models, and running your first forecast. If you have a question not covered here, check the community resources linked at the bottom of this page.

.. note::
   This page covers OpenSTEF V4. Some details may differ from earlier versions.

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building and running machine-learning-based forecasts of electrical load and generation. It provides complete pipelines for data preprocessing, feature engineering, model training, prediction, evaluation, and post-processing — so you are not assembling these pieces yourself from scratch.

   The library is model-agnostic: it ships with several ready-to-use gradient-boosting models (XGBoost, LightGBM) and a clean interface for plugging in your own. It is developed and used in production at Alliander, one of the largest grid operators in the Netherlands, where it currently generates forecasts for more than 10,000 grid locations.

   See :doc:`getting_started` for a hands-on introduction.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term means predicting load or generation **hours to roughly two days ahead**. This horizon is long enough to be operationally useful — for example, identifying tomorrow's peak load so a grid operator can call customers in advance — but short enough that machine-learning models trained on recent historical patterns remain accurate.

   Typical use cases include:

   - Congestion management (will a cable or transformer be overloaded tomorrow?)
   - Transport capacity planning
   - EV charging capacity estimation
   - Grid loss prediction
   - Solar and wind generation forecasting

.. dropdown:: Is OpenSTEF only useful for grid operators?
   :icon: question

   No. While OpenSTEF was built to solve grid-congestion problems at Alliander, the library is general-purpose for any time-series load or generation forecasting task. If you have a metered energy signal and want probabilistic forecasts a few hours to two days ahead, OpenSTEF is a good fit — whether you work at a utility, an aggregator, an industrial site, or in research.

.. dropdown:: What makes OpenSTEF different from a generic ML library?
   :icon: question

   Three things set it apart from using scikit-learn or similar tools directly:

   - **Energy-domain feature engineering** — built-in features such as solar radiation estimates, PV generation proxies, calendar effects, and lag features tuned for energy time series. You do not have to build these yourself.
   - **Probabilistic forecasts out of the box** — every model produces quantile forecasts (uncertainty bandwidths), not just a single point prediction. This matters for risk-aware operational decisions.
   - **Production-ready pipelines** — the library handles the full workflow: data validation, feature construction, training, backtesting, and evaluation. The same pipeline that runs in research can run in production.

Installation & Requirements
---------------------------

.. dropdown:: What Python version does OpenSTEF require?
   :icon: info

   OpenSTEF requires **Python 3.12 or newer** (Python < 4.0). It does not support Python 3.11 or earlier.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the ``openstef`` meta-package, which pulls in all sub-packages:

   .. code-block:: python

      # In your terminal:
      # pip install openstef

   If you only need specific functionality, install individual packages:

   .. code-block:: python

      # Core data structures and utilities only
      # pip install openstef-core

      # Backtesting, evaluation, and metrics (BEAM)
      # pip install openstef-beam

      # Forecasting models (LightGBM, XGBoost, etc.)
      # pip install openstef-models

   Verify the installation:

   .. code-block:: python

      import openstef_beam
      import openstef_core
      print(openstef_beam.__version__)
      print(openstef_core.__version__)

   See :doc:`installation` for the full guide including optional extras.

.. dropdown:: What are the main dependencies?
   :icon: info

   The core dependencies are:

   - **openstef-core** — ``numpy``, ``pandas``, ``pyarrow``, ``pydantic``, ``joblib``
   - **openstef-beam** — ``plotly``, ``pyyaml``, ``scoringrules``, ``tqdm``
   - **openstef-models** — ``pvlib``, ``holidays``, ``mlflow-skinny``, plus the model backends below

   Model backends are optional extras so you only install what you need:

   .. code-block:: bash

      pip install "openstef-models[lgbm]"        # LightGBM
      pip install "openstef-models[xgb-cpu]"     # XGBoost (CPU)
      pip install "openstef-models[xgb-gpu]"     # XGBoost (GPU)

.. dropdown:: Can I install OpenSTEF in a virtual environment or conda?
   :icon: checklist

   Yes — OpenSTEF is a standard Python package and works in any isolated environment. Using ``venv``, ``conda``, or ``uv`` (the tool used internally by the OpenSTEF team) all work fine:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate   # Windows: .venv\Scripts\activate
      pip install openstef

Models & Forecasting
--------------------

.. dropdown:: Which forecasting models does OpenSTEF include?
   :icon: question

   OpenSTEF ships with gradient-boosting tree models as its primary forecasters:

   - **LGBMForecaster** — LightGBM-based multi-quantile forecaster, generally fast to train and memory-efficient.
   - **LGBMLinearForecaster** — LightGBM with a linear tree structure, useful when interpretability matters.
   - **XGBoostForecaster** — XGBoost-based multi-quantile forecaster, with CPU and GPU variants.

   All models produce **probabilistic (quantile) forecasts** rather than a single point prediction, giving you uncertainty estimates alongside the central forecast.

   .. code-block:: python

      from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
      from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

.. dropdown:: Why does OpenSTEF use gradient-boosting models instead of deep learning?
   :icon: question

   Gradient-boosting trees (XGBoost, LightGBM) consistently outperform deep learning on tabular time-series data with the feature sizes typical in energy forecasting. They train faster, require less data, are easier to debug, and produce well-calibrated quantile estimates. OpenSTEF's architecture is model-agnostic, so deep-learning models can be added — but the built-in models reflect what works best in practice.

.. dropdown:: What are probabilistic forecasts and why do they matter?
   :icon: light-bulb

   A probabilistic forecast returns a range of possible outcomes at different confidence levels (quantiles) rather than a single number. For example, instead of "load will be 150 MW", you get "there is a 90 % chance load will be below 170 MW and a 10 % chance it will be below 130 MW".

   This matters for operational decisions: a grid operator managing congestion needs to know not just the expected load, but how likely it is to exceed a cable's rated capacity. Single-point forecasts hide that risk.

   .. note:: [VISUALIZATION: Example probabilistic forecast plot showing a central forecast line with shaded quantile bands over a 48-hour horizon]

.. dropdown:: Can I use my own custom model with OpenSTEF?
   :icon: question

   Yes. OpenSTEF is model-agnostic. You can implement the ``Forecaster`` interface from ``openstef_models.models.forecasting.forecaster`` and plug your model into the same pipelines used by the built-in models. This lets you benefit from OpenSTEF's feature engineering, data handling, and evaluation tooling while supplying your own estimator.

.. dropdown:: What hyperparameters can I tune?
   :icon: question

   Each model exposes a typed ``HyperParams`` class. For LightGBM, for example:

   .. code-block:: python

      from openstef_models.models.forecasting.lgbm_forecaster import LGBMHyperParams

      hyperparams = LGBMHyperParams(
          n_estimators=200,
          max_depth=8,
          learning_rate=0.1,
          reg_alpha=0.1,
          reg_lambda=1.0,
      )

   Using typed hyperparameter classes means mistakes (wrong types, unknown keys) are caught immediately rather than silently ignored at training time.

Data & Configuration
--------------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   OpenSTEF works with time-series data in pandas ``DataFrame`` format, indexed by a ``DatetimeIndex``. The minimum requirement is a target column (the load or generation signal you want to forecast) and a timestamp. Weather features, calendar features, and lag features are constructed automatically by the library's feature-engineering pipeline.

   For backtesting and evaluation, data is wrapped in typed dataset classes from ``openstef_core.datasets`` (e.g., ``TimeSeriesDataset``, ``ForecastDataset``) which enforce the expected schema and make pipelines composable.

.. dropdown:: How do I configure a pipeline or model?
   :icon: question

   OpenSTEF uses Pydantic-based configuration objects that can be created in code or loaded from YAML files:

   .. code-block:: python

      from openstef_core.base_model import BaseConfig
      from pathlib import Path

      # Load configuration from a YAML file
      config = BaseConfig.read_yaml(Path("my_config.yaml"))

      # Or write a config to YAML for reproducibility
      config.write_yaml(Path("my_config.yaml"))

   This makes experiment configurations version-controllable and shareable without changing code.

.. dropdown:: Does OpenSTEF integrate with MLflow?
   :icon: question

   Yes. ``openstef-models`` depends on ``mlflow-skinny`` and the training pipelines support MLflow experiment tracking. This lets you log hyperparameters, metrics, and model artefacts to an MLflow server (local or remote) as part of a standard training run.

Community & Contributing
------------------------

.. dropdown:: Where can I get help if I'm stuck?
   :icon: light-bulb

   - **GitHub Issues** — bug reports and feature requests: `github.com/OpenSTEF <https://github.com/OpenSTEF>`_
   - **Community Slack** — questions and discussion with other users and the core team
   - **Bi-weekly community meetings** — open to all; check the GitHub repository for the schedule
   - **Co-coding sessions** — held every eight weeks for hands-on collaboration

.. dropdown:: How do I contribute to OpenSTEF?
   :icon: checklist

   The project maintains a public backlog on GitHub with labelled "good first issues" suitable for new contributors. The development workflow uses ``uv`` for environment management and ``ruff`` for linting. See :doc:`contributing` for the full contribution guide.

.. dropdown:: Is OpenSTEF production-ready?
   :icon: alert

   The current release is **V4 Alpha**. It is already running in production at Alliander for congestion management across 10,000+ grid locations, so the core functionality is proven. However, as an alpha release, APIs may still change before the stable V4 release. If you are building on OpenSTEF today, pin your dependency to a specific version and watch the changelog for breaking changes.