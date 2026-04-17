FAQ
===

This FAQ covers the most common questions from new OpenSTEF users — from understanding what the library does and how to install it, to choosing models and integrating OpenSTEF into your own project. If you don't find your answer here, check the :doc:`getting_started` guide or open a discussion on GitHub.

.. rubric:: General

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building accurate short-term energy forecasts. It provides a complete machine learning framework — covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing — all within a single, composable toolkit.

   OpenSTEF is model-agnostic by design. Rather than locking you into one algorithm, it gives you a consistent pipeline interface that works across multiple gradient-boosting backends (XGBoost, LightGBM, and others). It was originally developed at Alliander, one of the largest grid operators in the Netherlands, and is now maintained as an open-source project under the LF Energy umbrella.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load or generation **hours to days ahead** — typically up to 48 hours into the future. This horizon is particularly important for operational decisions such as congestion management, EV charging capacity planning, transport forecasts, and grid loss prediction.

   This is distinct from medium-term (weeks/months) or long-term (years) forecasting, which require fundamentally different modelling approaches. OpenSTEF is purpose-built for the short-term horizon where weather conditions, time-of-day patterns, and recent load history are the dominant predictive signals.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a raw ML library for energy forecasting means building a lot of infrastructure yourself. OpenSTEF provides that infrastructure out of the box:

   - **Domain-specific feature engineering** — automatic lag features, holiday calendars, solar radiation-to-PV generation estimates, rolling window statistics, and weather feature mappings are all built in.
   - **Probabilistic forecasts** — OpenSTEF produces quantile forecasts with uncertainty bandwidths, not just single-point predictions. This is critical for risk-aware grid operations.
   - **Complete pipelines** — preprocessing, training, prediction, and post-processing are wired together in a consistent ``ForecastingModel`` / ``CustomForecastingWorkflow`` pattern.
   - **Model storage and versioning** — built-in MLflow integration means trained models are tracked, versioned, and retrievable without extra glue code.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides a dedicated backtesting, evaluation, analysis, and metrics (BEAM) framework.

   If you only need a generic gradient-boosting model, scikit-learn is fine. If you need production-grade energy forecasting with minimal boilerplate, OpenSTEF is the better starting point.

.. dropdown:: Who uses OpenSTEF and for what?
   :icon: question

   OpenSTEF was created by data science engineers at Alliander to solve a concrete operational problem: grid congestion. When a substation is at capacity, accurate 48-hour load forecasts allow grid operators to call customers in advance and request temporary load reductions — avoiding outages without waiting years for physical grid reinforcement.

   Beyond congestion management, the library is used for transport forecasts, EV charging capacity estimation, and grid loss prediction. Because it is a general-purpose short-term forecasting library, it can be applied to any time series where energy load or generation needs to be predicted hours to days ahead.

----

.. rubric:: Installation & Requirements

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or later** (Python < 4.0). It runs on Linux, macOS, and Windows.

   The library is split into focused sub-packages so you only install what you need:

   - ``openstef-core`` — data structures, preprocessing, and shared utilities
   - ``openstef-models`` — forecasting models (XGBoost, LightGBM, GBLinear, etc.)
   - ``openstef-beam`` — backtesting, evaluation, analysis, and metrics
   - ``openstef-meta`` — meta-models that combine the above

   The ``openstef`` meta-package installs all of them at once.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest approach installs everything:

   .. code-block:: bash

      pip install openstef

   If you only need specific functionality, install individual packages:

   .. code-block:: bash

      # Core data structures and preprocessing only
      pip install openstef-core

      # Models package (includes XGBoost and LightGBM support)
      pip install openstef-models

      # Backtesting, evaluation, and analysis tools
      pip install openstef-beam

   Some packages have optional extras. For example, to enable LightGBM support in ``openstef-models``:

   .. code-block:: bash

      pip install openstef-models[lgbm]

   To enable XGBoost on CPU:

   .. code-block:: bash

      pip install openstef-models[xgb-cpu]

   To verify your installation:

   .. code-block:: python

      import openstef_beam
      import openstef_core
      import openstef_models

.. dropdown:: Do I need a GPU?
   :icon: question

   No. OpenSTEF works entirely on CPU by default. GPU support is available as an optional extra for XGBoost if you have the hardware and want faster training on large datasets:

   .. code-block:: bash

      pip install openstef-models[xgb-gpu]

   For most energy forecasting workloads — even production deployments with many grid points — CPU training is fast enough.

.. dropdown:: Does OpenSTEF require MLflow?
   :icon: question

   MLflow is an **optional** dependency, not a hard requirement. You can train and run forecasts without it. MLflow becomes useful when you want model versioning, experiment tracking, and a centralised model registry in production.

   If you want MLflow integration, it is included with ``openstef-models``:

   .. code-block:: python

      from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

   For local development or quick experiments, ``LocalModelStorage`` (file-based persistence) is available without any MLflow setup.

----

.. rubric:: Models & Forecasting

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several gradient-boosting forecasters out of the box:

   - **XGBoost** — gradient-boosted trees; handles complex non-linear patterns well and is the most widely used option.
   - **LightGBM** — a faster gradient-boosting alternative, particularly efficient on large datasets.
   - **GBLinear** — a gradient-boosted linear model; better extrapolation behaviour and faster inference, useful when the relationship between features and load is more linear.

   All models share the same pipeline interface, so switching between them requires only a configuration change. You can also integrate custom models by implementing the expected interface.

.. dropdown:: What are probabilistic forecasts and why does OpenSTEF produce them?
   :icon: light-bulb

   A **probabilistic forecast** produces a range of possible outcomes rather than a single predicted value. OpenSTEF generates **quantile forecasts** — for example, the 10th, 50th, and 90th percentiles of the predicted load distribution. This gives you an uncertainty bandwidth around the median prediction.

   For grid operations, knowing *how uncertain* a forecast is matters as much as the forecast itself. A narrow band means high confidence; a wide band signals that conditions are volatile and more caution is warranted. Single-point forecasts discard this information entirely.

   You specify which quantiles you want when configuring the workflow:

   .. code-block:: python

      from openstef_core.types import Q

      # Request the 10th, 50th, and 90th percentile forecasts
      quantiles = [Q(0.10), Q(0.50), Q(0.90)]

.. dropdown:: How much historical data do I need to train a model?
   :icon: question

   As a practical guideline, **at least a few months of historical load data** at your target resolution (e.g., hourly or 15-minute intervals) is recommended. More data — especially data that covers multiple seasons — will generally produce better models because seasonal patterns, holiday effects, and weather correlations need sufficient examples to be learned reliably.

   For quick experimentation, OpenSTEF includes a synthetic dataset generator so you can explore the API without real data:

   .. code-block:: python

      from openstef_core.testing import create_synthetic_forecasting_dataset

      dataset = create_synthetic_forecasting_dataset()

.. dropdown:: Does OpenSTEF handle weather data automatically?
   :icon: question

   OpenSTEF has built-in support for weather-driven features. When you configure a forecasting workflow, you can map your weather data columns to named feature slots — temperature, wind speed, solar radiation, surface pressure, and relative humidity — and the library's feature engineering pipeline takes care of the rest, including converting solar radiation into PV generation estimates.

   .. code-block:: python

      from openstef_models.presets import ForecastingWorkflowConfig

      config = ForecastingWorkflowConfig(
          model_id="my_substation",
          radiation_column="shortwave_radiation",
          wind_speed_column="wind_speed_80m",
          temperature_column="temperature_2m",
          pressure_column="surface_pressure",
          relative_humidity_column="relative_humidity_2m",
      )

   You are responsible for sourcing and providing the weather data itself; OpenSTEF does not fetch it from external APIs.

.. dropdown:: Can I add my own custom features?
   :icon: question

   Yes. OpenSTEF's feature engineering is built around a composable ``TransformPipeline`` / ``FeaturePipeline`` abstraction. You can add your own transform steps alongside the built-in ones (holiday features, lag transforms, scalers, etc.) and they will be applied consistently during both training and inference.

   See :doc:`user_guide` for examples of building custom feature pipelines.

----

.. rubric:: Using the Library

.. dropdown:: What is the minimal code needed to train a model and get a forecast?
   :icon: question

   The following sketch shows the key components wired together. It uses synthetic data so you can run it immediately:

   .. code-block:: python

      import logging
      from pathlib import Path
      from openstef_core.testing import create_synthetic_forecasting_dataset
      from openstef_models.presets import ForecastingWorkflowConfig
      from openstef_models.workflows import CustomForecastingWorkflow
      from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage

      logging.basicConfig(level=logging.INFO)

      # 1. Create (or load) your dataset
      dataset = create_synthetic_forecasting_dataset()

      # 2. Configure the forecasting workflow
      config = ForecastingWorkflowConfig(
          model_id="my_first_model",
          model="xgboost",
          horizons=[1, 2, 24, 48],   # lead times in hours
      )

      # 3. Set up model storage (MLflow or local)
      storage = MLFlowStorage(experiment_name="openstef-quickstart")

      # 4. Run the workflow — trains and produces forecasts
      workflow = CustomForecastingWorkflow(config=config, storage=storage)
      forecast = workflow.run(dataset)

   For a more detailed walkthrough, see :doc:`getting_started`.

.. dropdown:: How do I evaluate forecast quality?
   :icon: question

   The ``openstef-beam`` package (Backtesting, Evaluation, Analysis and Metrics) is the dedicated evaluation toolkit. It provides backtesting pipelines that simulate how your model would have performed on historical data, along with scoring utilities and visualisation tools.

   .. code-block:: python

      from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

      plotter = ForecastTimeSeriesPlotter()
      fig = plotter.plot(forecast)
      fig.show()

   For a full backtesting example, see :doc:`backtesting`.

.. dropdown:: Is OpenSTEF suitable for non-energy time series?
   :icon: question

   OpenSTEF is purpose-built for energy forecasting and its built-in feature engineering reflects that — solar irradiance, PV generation estimates, energy price signals, and grid-specific holiday calendars are first-class concepts. That said, the core pipeline machinery (lag features, rolling aggregates, quantile forecasting, model storage) is general enough to be useful for other short-term time series problems.

   If your use case is entirely outside the energy domain, you may find that you are working around the energy-specific assumptions rather than benefiting from them. For energy and grid applications, OpenSTEF is a strong fit.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - **GitHub Issues** — for bug reports and feature requests, open an issue in the OpenSTEF repository.
   - **GitHub Discussions** — for questions, ideas, and community conversation.
   - **LF Energy Slack** — the ``#openstef`` channel on the LF Energy Slack workspace is a good place for real-time questions.

   When reporting a bug, please include your Python version, the versions of the OpenSTEF packages you have installed, a minimal reproducible example, and the full traceback.