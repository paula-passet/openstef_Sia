FAQ
===

This FAQ covers the most common questions from new OpenSTEF users — from
installation and requirements to understanding what the library does and how
to get started with it. If you have a question not answered here, check the
:doc:`user_guide/index` or open a discussion on the project's community
channels.

.. rubric:: General

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python
   **library** for building short-term load and energy forecasts. It provides
   a complete machine learning pipeline — data preprocessing, feature
   engineering, model training, probabilistic forecasting, evaluation, and
   post-processing — all in one package.

   OpenSTEF is model-agnostic and deliberately unopinionated: it is not
   built for a single use case or a single organisation. It was originally
   developed at Alliander, a Dutch grid operator, and is now maintained as
   part of the LF Energy foundation.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load or generation
   **hours to days ahead** — typically up to 48 hours into the future.
   This time horizon is critical for operational decisions such as congestion
   management, transport capacity planning, EV charging scheduling, and grid
   loss prediction.

   OpenSTEF produces multi-horizon forecasts in a single model pass, meaning
   one trained model covers the full forecast window rather than requiring a
   separate model per lead time.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using a gradient boosting library directly gives you a model. OpenSTEF
   gives you a **forecasting system**. The key differences are:

   - **Energy-domain feature engineering** — built-in transformations for
     holiday effects, lag features, and solar radiation to PV generation
     estimates. These features are hard to get right from scratch.
   - **Probabilistic forecasts** — OpenSTEF produces quantile forecasts
     (uncertainty bandwidths) out of the box, not just a single point
     prediction.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides
     rigorous regression testing so you can answer "is my model change
     actually an improvement?"
   - **Production-ready pipelines** — preprocessing, training, and prediction
     are composed into reusable, configurable pipelines with built-in model
     storage.
   - **Explainability** — feature contribution analysis is built into the
     model interface.

.. dropdown:: Who uses OpenSTEF and for what?
   :icon: question

   OpenSTEF was built to solve congestion management at Alliander: when grid
   capacity is full, accurate 48-hour load forecasts allow operators to
   identify peak moments and coordinate demand reduction with customers in
   advance, avoiding costly grid reinforcement.

   More broadly, the library is suited for any organisation that needs
   reliable short-term energy forecasts — grid operators, energy retailers,
   aggregators, and researchers working on load forecasting problems.

----

.. rubric:: Installation & Requirements

.. dropdown:: What are the system requirements?
   :icon: checklist

   - **Python 3.12 or higher** (Python 3.13 is also supported)
   - A 64-bit operating system — Windows, macOS, or Linux all work

   .. note::

      OpenSTEF 4.x requires Python 3.12+. If you are constrained to
      Python 3.10 or 3.11, use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest installation uses ``pip``:

   .. code-block:: bash

      pip install openstef

   OpenSTEF 4.0 has a modular architecture, so you can also install only the
   packages you need. The main packages are:

   - ``openstef-core`` — data types, interfaces, and base classes
   - ``openstef-models`` — forecasting models and preprocessing pipelines
   - ``openstef-beam`` — backtesting, evaluation, analysis, and metrics

   Alternative package managers are also supported:

   .. code-block:: bash

      # uv
      uv add openstef

      # conda
      conda install -c conda-forge openstef

      # pixi
      pixi add openstef

   For full details, including development setup, see :doc:`user_guide/installation`.

.. dropdown:: I get a Python version error when installing. What should I do?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. The recommended approach is
   to use a version manager such as ``pyenv`` or ``conda`` to create an
   isolated environment with the correct Python version:

   .. code-block:: bash

      # Using conda
      conda create -n openstef-env python=3.12
      conda activate openstef-env
      pip install openstef

.. dropdown:: Do I need a GPU to use OpenSTEF?
   :icon: question

   No. The core forecasting models (XGBoost, LightGBM, GBLinear) are
   CPU-based gradient boosting algorithms that run efficiently on standard
   hardware. A GPU is not required for typical short-term energy forecasting
   workloads.

----

.. rubric:: Models & Forecasting

.. dropdown:: Which machine learning models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several built-in forecasting models, including:

   - **XGBoost** — gradient boosted trees, a robust default choice
   - **LightGBM** — fast gradient boosting, well-suited to large datasets
   - **GBLinear** — gradient boosted linear models
   - **Flatliner** — a simple baseline model

   The library is model-agnostic by design: you can integrate custom models
   by implementing the ``Forecaster`` interface. Advanced ensemble
   architectures are available via the ``openstef-meta`` package.

.. dropdown:: How do I choose which model to use?
   :icon: light-bulb

   For most short-term energy forecasting tasks, **XGBoost or LightGBM** are
   a good starting point. Both handle the tabular, time-indexed data typical
   in energy forecasting very well. LightGBM tends to be faster to train on
   larger datasets; XGBoost is often slightly more robust out of the box.

   OpenSTEF provides preset workflow configurations for common model
   combinations, so you do not need to assemble the pipeline from scratch:

   .. code-block:: python

      from openstef_models.presets import get_forecast_workflow

      workflow = get_forecast_workflow("xgboost")

   If you are unsure, start with a preset and use the ``openstef-beam``
   evaluation tools to compare alternatives on your own data before
   committing to a model choice.

.. dropdown:: What are probabilistic forecasts and why does OpenSTEF produce them?
   :icon: light-bulb

   A **probabilistic forecast** provides a range of possible outcomes rather
   than a single predicted value. OpenSTEF produces **quantile forecasts** —
   for example, the 10th, 50th, and 90th percentile of expected load — giving
   operators an uncertainty bandwidth around the central prediction.

   This matters in practice because grid operators need to know not just the
   expected load, but also the worst-case scenario they should plan for.
   Knowing that load will *probably* be 80 MW but *could* reach 95 MW is
   far more useful for congestion management than a single number.

   Two uncertainty estimation methods are available in OpenSTEF; see the
   methodology documentation for a detailed comparison.

.. dropdown:: Does OpenSTEF handle missing data or delayed measurements?
   :icon: question

   Yes. OpenSTEF is explicitly designed with **data availability constraints**
   in mind — real-world energy data often arrives late or with gaps.
   The preprocessing pipelines include handling for delayed measurements and
   delayed weather forecasts, which are common in operational settings.

----

.. rubric:: Getting Started

.. dropdown:: What is the quickest way to see OpenSTEF in action?
   :icon: light-bulb

   The fastest path is to run one of the bundled examples. After installing
   OpenSTEF, you can configure and run a complete forecasting pipeline with
   synthetic data in just a few lines:

   .. code-block:: python

      from openstef_models.presets import get_forecast_workflow

      # Load a pre-configured workflow (model + preprocessing + postprocessing)
      workflow = get_forecast_workflow("xgboost")

      # Fit on your training data and generate forecasts
      workflow.train(train_dataset)
      forecast = workflow.predict(forecast_dataset)

   For a full working example with synthetic data, see the
   :doc:`examples` page.

.. dropdown:: How does OpenSTEF fit into my existing data infrastructure?
   :icon: question

   OpenSTEF is a **library**, not an application or a service. It does not
   impose a particular data storage layer, message bus, or deployment
   platform. You bring your own data as a ``pandas`` DataFrame or an
   OpenSTEF ``TimeSeriesDataset``, call the library's pipeline functions,
   and consume the results however you like.

   Model persistence is handled through a pluggable storage interface.
   The built-in ``LocalModelStorage`` saves models to disk; you can implement
   the same interface to store models in a database, object store, or MLflow
   tracking server.

.. dropdown:: Where can I find more detailed documentation?
   :icon: info

   - :doc:`user_guide/index` — step-by-step guides for installation, core
     concepts, and common workflows
   - :doc:`api/index` — full API reference for all packages
   - :doc:`examples` — runnable end-to-end examples
   - :doc:`contribute/index` — how to contribute to the project

   For questions not covered here, visit the project's community channels
   listed in :doc:`project/index`.