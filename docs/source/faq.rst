FAQ
===

This FAQ covers the most common questions from new OpenSTEF users — from understanding what the library does and how it is structured, to installation, model choices, and getting your first forecast running. If you don't find your answer here, check the :doc:`getting_started` guide or open a discussion on GitHub.

.. mermaid:: /diagrams/root/faq_diagram_1.mmd

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building accurate short-term energy load forecasts. It provides complete, production-ready pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing — all in one cohesive framework.

   "Short-term" means predicting energy load from hours to a couple of days ahead. This time horizon is critical for grid operators who need to anticipate congestion, schedule flexible assets, and manage EV charging capacity before problems occur.

   OpenSTEF is developed and maintained by Alliander, a Dutch grid operator, and is released under the Mozilla Public License 2.0 as part of the LF Energy foundation.

.. dropdown:: What problems is OpenSTEF designed to solve?
   :icon: question

   OpenSTEF was built to address the growing complexity of modern electricity grids. As solar panels, wind turbines, EVs, and heat pumps reshape both supply and demand, grid congestion has become one of the most pressing challenges for utilities.

   The library is used in production at Alliander for:

   - **Congestion management** — forecasting load at grid points 2 days ahead to identify peak moments and coordinate demand reduction with customers
   - **Transport forecasts** — predicting how much capacity different parts of the grid will need
   - **EV charging capacity estimation** — anticipating charging demand at scale
   - **Grid loss prediction** — estimating energy losses across the network

   OpenSTEF currently makes forecasts for over 10,000 different grid locations in production.

.. dropdown:: Is OpenSTEF just a model, or something more?
   :icon: question

   OpenSTEF is much more than a single model. It is a **model-agnostic machine learning framework** — meaning it provides the full pipeline infrastructure around models, not just the models themselves.

   What this means in practice:

   - You bring your data; OpenSTEF handles preprocessing, feature engineering, training, and evaluation
   - You can swap in different model backends (XGBoost, LightGBM, GBLinear, and more) without rewriting your pipeline
   - Built-in energy-domain knowledge — such as deriving PV generation estimates from solar radiation data — is available out of the box
   - Probabilistic forecasts with configurable quantile intervals are a first-class feature, not an afterthought

.. dropdown:: How is OpenSTEF different from generic forecasting libraries like Prophet or statsforecast?
   :icon: question

   Generic forecasting libraries are general-purpose tools. OpenSTEF is purpose-built for the **energy domain**, which means:

   - **Domain-specific feature engineering** is built in — holiday calendars, lag transforms, solar irradiance-to-PV conversion, and other energy-relevant transformations are ready to use without custom code
   - **Probabilistic forecasts** (quantile regression) are the default output, giving you uncertainty bandwidths rather than just a single-point prediction
   - **Production-grade pipelines** are the primary abstraction — the library is designed to run reliably at scale across thousands of grid locations
   - **Backtesting and evaluation tooling** (the ``openstef-beam`` package) is included, so you can rigorously validate model changes before deploying them

   If you need a quick univariate forecast for a general time series, a simpler library may suffice. If you are building a robust, scalable energy forecasting system, OpenSTEF provides the infrastructure to do it properly.

.. dropdown:: Who maintains OpenSTEF and is it production-ready?
   :icon: question

   OpenSTEF is developed by data science software engineers at **Alliander**, one of the largest grid operators in the Netherlands. It is an open-source project under the **LF Energy** foundation and is actively maintained with a public backlog on GitHub, bi-weekly community meetings, and regular co-coding sessions.

   The library is in **production at Alliander**, generating forecasts for over 10,000 grid locations. The current release is OpenSTEF V4 (alpha), which represents a significant architectural redesign from V3 with improved modularity and flexibility.

----

Installation & Requirements
----------------------------

.. dropdown:: What Python version does OpenSTEF require?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (and less than 4.0). Make sure your environment meets this requirement before installing.

   .. code-block:: python

      import sys
      print(sys.version)  # Should show 3.12.x or higher

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the ``openstef`` meta-package, which pulls in all sub-packages at once:

   .. code-block:: bash

      pip install openstef

   This installs ``openstef-core``, ``openstef-models``, ``openstef-beam``, and ``openstef-meta`` together.

   If you only need specific functionality, you can install individual packages:

   .. code-block:: bash

      # Core data types and interfaces only
      pip install openstef-core

      # Forecasting models
      pip install openstef-models

      # Backtesting, evaluation, analysis, and metrics
      pip install openstef-beam

      # Meta/ensemble models
      pip install openstef-meta

   To verify your installation:

   .. code-block:: python

      import openstef_core
      import openstef_models
      import openstef_beam
      print("OpenSTEF installed successfully.")

.. dropdown:: Do I need a GPU to use OpenSTEF?
   :icon: question

   No, a GPU is not required. OpenSTEF's gradient boosting models (XGBoost, LightGBM, GBLinear) run efficiently on CPU. GPU support is available as an optional extra for XGBoost if you want to accelerate training on large datasets:

   .. code-block:: bash

      # CPU-only XGBoost (default for Linux and Windows)
      pip install openstef-models[xgb-cpu]

      # GPU-accelerated XGBoost
      pip install openstef-models[xgb-gpu]

   For most energy forecasting workloads, CPU training is fast enough and is the recommended starting point.

.. dropdown:: How do I install support for LightGBM or XGBoost?
   :icon: checklist

   These model backends are available as optional extras on ``openstef-models``:

   .. code-block:: bash

      # LightGBM support
      pip install openstef-models[lgbm]

      # XGBoost (CPU)
      pip install openstef-models[xgb-cpu]

      # XGBoost (GPU)
      pip install openstef-models[xgb-gpu]

   If you installed the top-level ``openstef`` meta-package, LightGBM is already included via ``openstef-meta``.

.. dropdown:: Does OpenSTEF work in a virtual environment or conda environment?
   :icon: checklist

   Yes — and it is strongly recommended. Use any standard Python environment manager:

   .. code-block:: bash

      # Using venv
      python -m venv .venv
      source .venv/bin/activate   # On Windows: .venv\Scripts\activate
      pip install openstef

      # Using conda
      conda create -n openstef python=3.12
      conda activate openstef
      pip install openstef

   .. note::

      OpenSTEF uses ``uv`` and ``ruff`` internally for development. If you are contributing to the library, refer to the :doc:`contributing` guide for the recommended developer setup.

----

Models & Forecasting
---------------------

.. dropdown:: What forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF is model-agnostic and ships with several built-in model backends:

   - **GBLinear** — a gradient boosted linear model that can extrapolate beyond training data, provides interpretable feature importance, and is fast to train. Recommended as a starting point for energy forecasting.
   - **XGBoost** — a powerful gradient boosting tree model, available in CPU and GPU variants
   - **LightGBM** — another gradient boosting tree model, optimised for speed and memory efficiency with multi-quantile support
   - **Constant Median Forecaster** — a simple baseline useful for testing pipelines and sanity-checking results

   All models produce **probabilistic forecasts** via quantile regression, giving you prediction intervals rather than just a single-point estimate.

.. dropdown:: What are probabilistic forecasts and why does OpenSTEF use them?
   :icon: light-bulb

   A probabilistic forecast produces a range of possible outcomes at different confidence levels, rather than a single predicted value. In OpenSTEF, this is expressed as **quantiles** — for example, the 10th, 50th, and 90th percentile of the predicted load.

   This matters for energy grid operations because:

   - A single-point forecast tells you the expected load, but not how uncertain that estimate is
   - Knowing the upper bound (e.g., 90th percentile) helps operators plan for worst-case congestion scenarios
   - Uncertainty information enables smarter decisions about when to intervene and how aggressively

   You configure quantiles when setting up your forecasting workflow:

   .. code-block:: python

      from openstef_core.types import Q

      # Request forecasts at the 10th, 50th, and 90th percentiles
      quantiles = [Q(0.10), Q(0.50), Q(0.90)]

.. dropdown:: How do I configure and run a forecasting pipeline?
   :icon: question

   OpenSTEF uses a ``ForecastingWorkflowConfig`` to define your pipeline, and ``create_forecasting_workflow`` to assemble it. Here is a minimal example using the GBLinear preset:

   .. code-block:: python

      from openstef_core.types import LeadTime, Q
      from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

      # Define the forecasting workflow
      workflow = create_forecasting_workflow(
          config=ForecastingWorkflowConfig(
              model_id="my_grid_point",
              forecast_horizons=[LeadTime(hours=h) for h in range(1, 37)],
              quantiles=[Q(0.10), Q(0.50), Q(0.90)],
          )
      )

      # Train on historical data
      workflow.train(train_dataset)

      # Generate a forecast
      forecast = workflow.predict(input_dataset)

   See :doc:`getting_started` for a complete walkthrough including data preparation and evaluation.

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   OpenSTEF expects **time series data** structured as a pandas ``DataFrame`` with a ``DatetimeIndex``. At minimum you need:

   - A ``load`` column containing the historical energy measurements (in MW or a consistent unit)
   - Weather feature columns if you want to use meteorological predictors (e.g., temperature, solar irradiance, wind speed)

   OpenSTEF provides ``ForecastDataset`` and ``ForecastInputDataset`` wrappers from ``openstef_core.datasets`` to validate and manage this data. For quick experimentation, you can generate synthetic data:

   .. code-block:: python

      from openstef_core.testing import create_synthetic_forecasting_dataset

      train_dataset, input_dataset = create_synthetic_forecasting_dataset()

.. dropdown:: Does OpenSTEF handle missing data and data quality issues?
   :icon: question

   Yes. Data preprocessing — including handling of missing values, outlier detection, and normalisation — is part of the built-in ``FeaturePipeline`` in ``openstef-models``. You can configure preprocessing steps when building your pipeline, and the library applies them consistently at both training and prediction time.

   For production use cases where measurements may arrive late (delayed sensor readings or delayed weather forecasts), OpenSTEF's design explicitly accounts for **data availability constraints**, so your pipeline can be configured to reflect real-world data latency.

----

Architecture & Packages
------------------------

.. dropdown:: What is the difference between openstef-core, openstef-models, openstef-beam, and openstef-meta?
   :icon: info

   OpenSTEF V4 is structured as a **modular mono-repo** with four self-contained packages, each with a distinct responsibility:

   - **openstef-core** — data types, interfaces, base classes, shared exceptions, and testing utilities. This is the foundation everything else builds on.
   - **openstef-models** — forecasting models, data preprocessing pipelines, energy-specific feature transformations, explainability features, and presets for common use cases.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Answers the question "are my model changes actually significant?" Includes regression testing against benchmarks and visualisation tools.
   - **openstef-meta** — meta-learning and ensemble models that combine multiple base models for improved accuracy.

   Install them all at once with ``pip install openstef``, or pick only what you need.

.. dropdown:: Can I use just part of OpenSTEF, or do I need the whole framework?
   :icon: light-bulb

   You can absolutely use individual packages. The modular design is intentional — if you only need the evaluation and backtesting tooling from ``openstef-beam``, you can install just that. If you want to use OpenSTEF's feature engineering and models but plug in your own evaluation logic, install ``openstef-models`` alone.

   The ``openstef`` top-level package is a convenience meta-package for users who want everything. It does not add any code of its own.

.. dropdown:: Is OpenSTEF designed to be integrated into existing systems?
   :icon: info

   Yes. One of the explicit design goals of OpenSTEF V4 is to support **enterprise integration** — complex software landscapes with custom APIs and policies. The library is intentionally **unopinionated**: it does not assume a particular data storage backend, orchestration framework, or deployment environment.

   You integrate OpenSTEF by calling its Python API from your own application code. Model persistence is handled via ``LocalModelStorage`` (file-based) or you can implement your own storage backend using the provided interfaces.

----

Troubleshooting & Common Issues
---------------------------------

.. dropdown:: I get an import error after installing. What should I check?
   :icon: alert

   First, confirm that your Python version is 3.12 or higher:

   .. code-block:: bash

      python --version

   Then verify the package is installed in the active environment:

   .. code-block:: bash

      pip show openstef-core

   A common mistake is installing into a different Python environment than the one you are running. Make sure your virtual environment is activated before installing and before running your code.

   If you installed individual packages, check that you have the right one for the import you are attempting — for example, ``openstef_beam`` requires ``pip install openstef-beam``.

.. dropdown:: My forecast accuracy is poor. Where do I start debugging?
   :icon: alert

   Poor forecast accuracy usually has one of a few root causes:

   - **Insufficient training data** — gradient boosting models benefit from at least several months of historical data covering seasonal patterns
   - **Missing weather features** — energy load is strongly correlated with temperature and solar irradiance; including relevant weather variables typically improves accuracy significantly
   - **Data quality issues** — check for gaps, outliers, or unit inconsistencies in your ``load`` column
   - **Wrong forecast horizon** — models trained for short horizons (1–6 hours) will perform poorly if asked to forecast 36 hours ahead; configure ``forecast_horizons`` to match your actual use case

   Use ``openstef-beam``'s evaluation pipeline to segment performance by lead time and time window, which helps pinpoint where accuracy degrades:

   .. code-block:: python

      from openstef_beam.evaluation.evaluation_pipeline import EvaluationConfig

      config = EvaluationConfig(...)

   See :doc:`evaluation` for a full guide to diagnosing model performance.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - **GitHub Issues** — for bug reports and feature requests, open an issue on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_
   - **Community Slack** — for questions and discussion, join the LF Energy Slack workspace
   - **Bi-weekly community meetings** — open to all; check the GitHub repository for the schedule
   - **Good first issues** — if you want to contribute, look for issues tagged ``good first issue`` on GitHub

   When reporting a bug, include your Python version, OpenSTEF package versions (``pip show openstef-core``), a minimal reproducible example, and the full traceback.