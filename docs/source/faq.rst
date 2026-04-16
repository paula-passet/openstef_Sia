FAQ
===

New to OpenSTEF? This page answers the most common questions from users getting started with the library — from installation and requirements to model selection and core concepts.

.. note::

   Can't find your answer here? Join the community on Slack or open a discussion on `GitHub <https://github.com/OpenSTEF/openstef>`_.

---------------

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building accurate short-term energy load forecasts. It provides complete, ready-to-use pipelines for data preprocessing, feature engineering, model training, probabilistic forecasting, backtesting, and evaluation — all in one cohesive framework.

   OpenSTEF is model-agnostic by design: it is not tied to a single algorithm. You bring your data; OpenSTEF handles the rest of the machine learning workflow.

   It is developed and maintained by Alliander, a Dutch grid operator, and is currently used in production to generate forecasts for over 10,000 grid locations.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load **hours to days ahead** — typically up to 48 hours into the future. This is the horizon that matters most for operational grid management tasks such as:

   - Congestion management (identifying when load will exceed equipment limits)
   - Transport capacity planning
   - EV charging capacity estimation
   - Grid loss prediction

   OpenSTEF is not designed for long-range seasonal or annual energy planning.

.. dropdown:: What makes OpenSTEF different from a generic ML library?
   :icon: light-bulb

   General-purpose ML libraries like scikit-learn give you building blocks. OpenSTEF gives you a complete, domain-aware forecasting system built on top of those blocks. Key differentiators include:

   - **Probabilistic forecasts by default** — every model produces prediction intervals (quantiles), not just a single point estimate. This is critical for risk-aware grid operations.
   - **Built-in energy domain knowledge** — feature engineering pipelines include solar radiation to PV generation estimates, national holiday calendars, lag transforms, and more — all pre-wired.
   - **End-to-end pipelines** — training, prediction, backtesting, evaluation, and model storage are all first-class citizens in the library, not afterthoughts.
   - **Production-tested** — the same library runs in Alliander's production systems, so operational concerns like model versioning and reuse are built in.

.. dropdown:: Is OpenSTEF only useful for grid operators?
   :icon: question

   No. While OpenSTEF was created to solve grid congestion problems at Alliander, the library is general enough for any time-series load forecasting problem where you have historical load data and weather covariates. Solar parks, wind parks, district heating networks, and industrial energy consumers are all valid use cases. The domain-specific features (e.g., PV generation estimation) are optional components you can include or omit.

---------------

Installation & Requirements
---------------------------

.. dropdown:: What Python version does OpenSTEF require?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (``>=3.12,<4.0``). Make sure your environment meets this requirement before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the ``openstef`` meta-package, which pulls in all sub-packages:

   .. code-block:: python

      # From your terminal:
      # pip install openstef

   This installs four packages:

   - ``openstef-core`` — data structures, base classes, and shared utilities
   - ``openstef-models`` — forecasting models (XGBoost, LightGBM, GBLinear, etc.)
   - ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM)
   - ``openstef-meta`` — meta-model ensembles

   See :doc:`installation` for the full installation guide, including how to install individual packages or optional extras.

.. dropdown:: Can I install only part of OpenSTEF?
   :icon: question

   Yes. Each sub-package is independently installable. For example, if you only need the core data structures and don't need the full model suite:

   .. code-block:: python

      # pip install openstef-core

   Or if you want backtesting and evaluation tooling with baseline model support:

   .. code-block:: python

      # pip install openstef-beam[baselines]

   Available optional extras include:

   - ``openstef-beam[all]`` — includes S3 filesystem support and baselines
   - ``openstef-beam[baselines]`` — adds ``openstef-meta`` and ``openstef-models``
   - ``openstef-models[lgbm]`` — adds LightGBM support
   - ``openstef-models[xgb-cpu]`` — adds XGBoost (CPU-only build)
   - ``openstef-models[xgb-gpu]`` — adds XGBoost with GPU support

.. dropdown:: How do I verify my installation?
   :icon: checklist

   After installing, you can confirm everything is in order by importing the top-level packages:

   .. code-block:: python

      import openstef_core
      import openstef_models
      import openstef_beam

      print("OpenSTEF is ready!")

   If any import fails, check that your Python version is 3.12+ and that the package was installed into the correct environment.

---------------

Core Concepts
-------------

.. dropdown:: What is a forecasting workflow?
   :icon: question

   A forecasting workflow in OpenSTEF is a high-level object that orchestrates the full lifecycle of a forecast: data preprocessing, feature engineering, model training, and prediction. You configure it once and then call it repeatedly for training and inference.

   The ``create_forecasting_workflow`` factory function is the recommended entry point:

   .. code-block:: python

      from openstef_core.types import LeadTime, Q
      from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

      workflow = create_forecasting_workflow(
          config=ForecastingWorkflowConfig(
              model_id="my_grid_point",
              forecast_horizon=LeadTime(hours=36),
              quantiles=[Q(0.1), Q(0.5), Q(0.9)],
          )
      )

   See :doc:`user_guide/workflows` for a full walkthrough.

.. dropdown:: What is a probabilistic forecast and why does OpenSTEF use it?
   :icon: light-bulb

   A probabilistic forecast produces a **range of possible outcomes** rather than a single number. OpenSTEF expresses this as quantiles — for example, the 10th, 50th, and 90th percentile of the predicted load distribution.

   This matters in grid operations because decisions are rarely binary. Knowing that load will be "around 50 MW" is less useful than knowing there is a 90% chance it will stay below 60 MW. Quantile forecasts let operators set risk thresholds and act accordingly.

   All models in OpenSTEF produce multi-quantile outputs by default. You specify which quantiles you want at configuration time using the ``Q`` type from ``openstef_core.types``.

.. dropdown:: What is the ForecastDataset and how do I create one?
   :icon: question

   ``ForecastDataset`` is OpenSTEF's primary data container. It wraps a time-indexed pandas DataFrame and enforces the structure that pipelines expect (a ``load`` column for the target, plus any feature columns).

   For development and testing, you can generate synthetic data without any real measurements:

   .. code-block:: python

      from openstef_core.testing import create_synthetic_forecasting_dataset

      dataset = create_synthetic_forecasting_dataset()
      print(dataset.data.head())

   For production use, you construct a ``ForecastDataset`` from your own DataFrame. See :doc:`user_guide/data_preparation` for details on the expected schema.

.. dropdown:: What is the FeaturePipeline and what features does it add?
   :icon: question

   The ``FeaturePipeline`` is a preprocessing component that transforms raw time-series data into a rich feature matrix before it reaches the model. Built-in transforms include:

   - **Holiday features** — binary flags for national public holidays (configurable per country)
   - **Lag transforms** — historical load values at configurable time offsets (e.g., load 24 h ago, 48 h ago)
   - **Data scaling** — normalisation to improve model convergence

   You can compose these transforms declaratively when configuring your ``ForecastingModel``. Domain-specific transforms such as PV generation estimation from solar irradiance are available in ``openstef-models``.

---------------

Models & Algorithms
-------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships several gradient-boosting models out of the box:

   - **GBLinear** (``gblinear``) — a gradient-boosted linear model. Recommended as a starting point because it can extrapolate beyond training data, provides interpretable feature importance, and trains quickly.
   - **XGBoost** (``xgboost``) — requires ``openstef-models[xgb-cpu]`` or ``openstef-models[xgb-gpu]``
   - **LightGBM** (``lgbm``) — requires ``openstef-models[lgbm]``

   All models implement the same interface and produce multi-quantile probabilistic outputs.

.. dropdown:: Which model should I start with?
   :icon: light-bulb

   Start with **GBLinear**. It is the default in OpenSTEF's preset workflows and is particularly well-suited to energy forecasting because:

   1. It extrapolates beyond the range of training data — important when rare weather events push load to unseen levels.
   2. Feature importance is interpretable, making it easier to debug and explain forecasts.
   3. It trains and predicts quickly, which matters when you are forecasting thousands of grid points.

   Switch to XGBoost or LightGBM if you need to squeeze out additional accuracy on a specific dataset and are comfortable with the extra tuning effort.

.. dropdown:: Can I use my own custom model?
   :icon: question

   Yes. OpenSTEF's model interface is designed to be extended. You can implement the ``BaseForecastingModel`` interface from ``openstef_core`` and plug your custom model into any workflow that accepts a standard forecasting model. The rest of the pipeline — feature engineering, evaluation, model storage — works unchanged.

---------------

Model Storage & Tracking
------------------------

.. dropdown:: How does OpenSTEF store trained models?
   :icon: question

   OpenSTEF provides two storage backends out of the box:

   - **LocalModelStorage** — saves models to the local filesystem using joblib serialisation. Good for development and single-machine deployments.
   - **MLFlowStorage** — integrates with an MLflow tracking server for experiment tracking, model versioning, and centralised artifact storage. Recommended for production.

   .. code-block:: python

      from openstef_models.integrations.mlflow import MLFlowStorage

      storage = MLFlowStorage(tracking_uri="http://my-mlflow-server:5000")

   The MLflow integration logs hyperparameters, training metrics, feature importance plots, and the serialised model automatically on each training run.

.. dropdown:: Does OpenSTEF support model versioning?
   :icon: question

   Yes. When using ``MLFlowStorage``, every training run is recorded as a versioned experiment in MLflow. The storage backend also supports **model reuse** — if a sufficiently recent model already exists, it can skip retraining — and **model selection**, where the better-performing model (based on a configurable metric) is retained automatically.

   For local development, ``LocalModelStorage`` uses joblib serialisation and you manage versioning yourself via file paths.

---------------

Backtesting & Evaluation
------------------------

.. dropdown:: What is backtesting and how do I run it?
   :icon: question

   Backtesting simulates how your model would have performed on historical data by training on a past window and evaluating on a subsequent held-out period. This gives you a realistic estimate of live forecast accuracy before deploying a model.

   OpenSTEF's ``openstef-beam`` package provides a dedicated backtesting pipeline. See :doc:`user_guide/backtesting` for a step-by-step guide.

.. dropdown:: How do I evaluate forecast quality?
   :icon: question

   The ``openstef-beam`` package includes an ``EvaluationPipeline`` that segments forecast results across multiple dimensions — lead time, availability time, and configurable time windows — and computes performance metrics for each subset. This lets you understand not just overall accuracy, but *where* and *when* the model struggles.

   .. code-block:: python

      from openstef_beam.evaluation.evaluation_pipeline import EvaluationConfig

      eval_config = EvaluationConfig(
          # Configure windows, metrics, and filtering here
      )

   Metrics include standard probabilistic scoring rules (via the ``scoringrules`` dependency) as well as point-forecast metrics. Results are returned as structured ``EvaluationReport`` objects that you can inspect or export.

.. dropdown:: How do I visualise forecasts?
   :icon: question

   OpenSTEF includes built-in visualisation utilities in ``openstef-beam`` — no need to write your own plotting code from scratch. The ``ForecastTimeSeriesPlotter`` produces interactive Plotly charts showing the forecast alongside actuals and prediction intervals:

   .. code-block:: python

      from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

      plotter = ForecastTimeSeriesPlotter()
      fig = plotter.plot(forecast_dataset)
      fig.show()

   These plots are also logged automatically to MLflow when using the ``MLFlowStorageCallback``.

---------------

Contributing & Community
------------------------

.. dropdown:: Is OpenSTEF open source? Can I contribute?
   :icon: light-bulb

   Yes. OpenSTEF is released under the **Mozilla Public License 2.0 (MPL-2.0)** and welcomes community contributions. The project is hosted on GitHub and maintains a public backlog with labelled "good first issues" for new contributors.

   The community meets bi-weekly, with co-coding sessions every eight weeks. You can also join the Slack workspace to ask questions and discuss ideas.

.. dropdown:: Where can I get help if I'm stuck?
   :icon: alert

   The following resources are available:

   - **This documentation** — start with :doc:`getting_started/quickstart` for a guided introduction.
   - **GitHub Issues** — for bug reports and feature requests.
   - **GitHub Discussions** — for open-ended questions and design conversations.
   - **Slack** — for real-time community support.

   When reporting a bug, please include your OpenSTEF version, Python version, and a minimal reproducible example.