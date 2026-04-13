FAQ
===

This FAQ covers the most common questions from new users of the OpenSTEF library — from
installation and requirements to model selection and core concepts. If your question isn't
answered here, check the :doc:`user_guide/index` or open a discussion on the project's
community channels.

.. note::

   OpenSTEF is a **Python library**, not a standalone application or service. You integrate
   it into your own code, pipelines, and infrastructure.

----

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for
   building and running short-term load forecasts in the energy sector. It provides a
   complete machine learning pipeline — data preprocessing, feature engineering, model
   training, probabilistic forecasting, evaluation, and post-processing — all in one
   cohesive package.

   The library is model-agnostic and ships with built-in support for gradient boosting
   models (XGBoost, LightGBM) as well as more advanced ensemble architectures. Rather
   than giving you a single fixed model, OpenSTEF gives you a framework you can adapt
   to your own data and use case.

   See :doc:`user_guide/index` for a guided introduction.

.. dropdown:: What does "short-term forecasting" mean?
   :icon: question

   Short-term forecasting means predicting energy load **hours to days ahead** — typically
   up to 48 hours into the future. This horizon is especially useful for operational
   decisions such as congestion management, scheduling flexible loads, and estimating
   available grid capacity.

   OpenSTEF produces **multi-horizon forecasts** in a single pass, so you get predictions
   for every time step in the forecast window at once rather than running the model
   repeatedly.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a raw ML library requires you to build all the surrounding infrastructure
   yourself: feature engineering, lag creation, holiday calendars, weather data
   integration, uncertainty estimation, model versioning, and evaluation harnesses.
   OpenSTEF provides all of this out of the box, with energy-domain knowledge already
   baked in.

   Key differentiators include:

   - **Probabilistic forecasts** — outputs uncertainty bandwidths alongside point
     predictions, not just a single value per time step.
   - **Energy-specific feature engineering** — built-in transformations such as solar
     radiation to PV generation estimates, lag features, and holiday indicators.
   - **Complete pipelines** — preprocessing, training, prediction, and evaluation are
     orchestrated together so components are always consistent.
   - **Modular architecture** — install only the packages you need; swap models without
     rewriting your pipeline.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides a dedicated
     framework for regression testing and benchmarking model changes.

.. dropdown:: Who uses OpenSTEF and what for?
   :icon: question

   OpenSTEF was originally developed at Alliander, a Dutch grid operator, where it powers
   congestion management workflows. The typical operational loop is:

   1. Forecast load at grid points up to 48 hours ahead.
   2. Identify time windows where load will exceed equipment limits.
   3. Notify flexible customers in advance to reduce consumption or generation.

   Beyond congestion management, the library is used for transport forecasts, EV charging
   capacity estimation, and grid loss prediction. Because it is a general-purpose
   forecasting library, it can be applied to any time series problem in the energy domain.

----

Installation & Requirements
----------------------------

.. dropdown:: What Python version do I need?
   :icon: question

   OpenSTEF 4.0 requires **Python 3.12 or higher** (Python 3.13 is also supported).
   A 64-bit operating system is required; Windows, macOS, and Linux are all supported.

   .. note::

      If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

   You can check your current Python version with:

   .. code-block:: bash

      python --version

   If you need to manage multiple Python versions, tools like
   `pyenv <https://github.com/pyenv/pyenv>`_ or ``conda`` work well alongside OpenSTEF.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest installation uses ``pip``:

   .. code-block:: bash

      pip install openstef

   OpenSTEF 4.0 has a modular architecture, so you can also install individual packages
   depending on what you need:

   .. code-block:: bash

      # Core data types and interfaces only
      pip install openstef-core

      # Forecasting models and pipelines
      pip install openstef-models

      # Backtesting, evaluation, analysis and metrics
      pip install openstef-beam

   Other package managers are also supported:

   .. code-block:: bash

      # uv
      uv add openstef

      # conda / pixi
      conda install -c conda-forge openstef

   For full installation details, including development setup, see
   :doc:`user_guide/installation`.

.. dropdown:: I'm getting a Python version error during installation. What do I do?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. The recommended approach is to use
   ``pyenv`` or ``conda`` to create a dedicated environment:

   .. code-block:: bash

      # Using conda
      conda create -n openstef-env python=3.12
      conda activate openstef-env
      pip install openstef

   .. code-block:: bash

      # Using pyenv + venv
      pyenv install 3.12
      pyenv local 3.12
      python -m venv .venv
      source .venv/bin/activate
      pip install openstef

.. dropdown:: How do I verify that my installation is working?
   :icon: checklist

   After installing, run the following in a Python session:

   .. code-block:: python

      import openstef_models
      print(f"OpenSTEF Models version: {openstef_models.__version__}")

      # If you also installed openstef-beam:
      try:
          import openstef_beam
          print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
      except ImportError:
          print("OpenSTEF BEAM not installed (optional)")

   If both imports succeed without errors, your installation is ready to use.

----

Architecture & Packages
------------------------

.. dropdown:: What are the different OpenSTEF packages and which one do I need?
   :icon: question

   OpenSTEF 4.0 is structured as a modular mono-repo. The packages are:

   - **openstef-core** — Data types, interfaces, base classes, and shared utilities.
     This is the foundation that all other packages depend on.
   - **openstef-models** — Forecasting models (XGBoost, LightGBM, LightGBM-Linear),
     preprocessing pipelines, energy-specific feature transformations, explainability
     features, and presets for quick-start workflows.
   - **openstef-meta** — Advanced ensemble models and meta-learning architectures for
     more complex forecasting scenarios.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Use this when
     you need to benchmark model changes, run regression tests, or analyse forecast
     quality over historical periods.

   For most new users, installing the top-level ``openstef`` package (which pulls in the
   core components) is the right starting point. Add ``openstef-beam`` when you are ready
   to evaluate and compare models systematically.

.. dropdown:: Is OpenSTEF a service or an application I can just run?
   :icon: question

   No — OpenSTEF is a **Python library**. It provides building blocks (models, pipelines,
   data structures, evaluation tools) that you integrate into your own code. There is no
   server to start, no configuration file to deploy, and no UI to open.

   You write Python code that imports OpenSTEF, feeds it your data, and calls the
   relevant pipeline functions. This design keeps the library flexible and easy to embed
   in any existing infrastructure, from Jupyter notebooks to production Airflow DAGs.

----

Models & Forecasting
--------------------

.. dropdown:: Which forecasting model should I use?
   :icon: question

   OpenSTEF ships with several gradient boosting models, all of which produce probabilistic
   (multi-quantile) forecasts:

   - **LightGBM** (``LGBMForecaster``) — A strong general-purpose default. Fast to train
     and well-suited to tabular time series data with many features.
   - **LightGBM-Linear** (``LGBMLinearForecaster``) — A LightGBM variant that uses
     linear tree leaves, which can be useful when the relationship between features and
     load is more linear in nature.
   - **XGBoost** (``XGBForecaster``) — Another robust gradient boosting option, often
     competitive with LightGBM and worth benchmarking against it.

   If you are unsure where to start, use the built-in **presets** in ``openstef-models``,
   which configure a complete pipeline with sensible defaults:

   .. code-block:: python

      from openstef_models.presets import get_preset_pipeline

      pipeline = get_preset_pipeline("lgbm")

   For advanced use cases with multiple data sources or ensemble requirements, explore
   ``openstef-meta``.

.. dropdown:: Does OpenSTEF only produce point forecasts?
   :icon: question

   No. OpenSTEF is designed around **probabilistic forecasting**. Every built-in model
   produces multiple quantile forecasts alongside the median prediction, giving you
   uncertainty bandwidths rather than a single value.

   This is particularly important in energy applications where knowing the range of
   possible outcomes — not just the expected value — is critical for safe operational
   decisions.

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   OpenSTEF works with time series data structured as a ``TimeSeriesDataset`` (or
   ``VersionedTimeSeriesDataset`` for workflows that require data versioning). At minimum
   you need a time-indexed series of the load or quantity you want to forecast.

   The library's feature engineering pipelines can automatically enrich your data with:

   - Lag features (configurable look-back windows)
   - Holiday and calendar indicators
   - Weather-derived features (e.g., solar radiation to PV generation estimates)

   You do not need to pre-compute these features manually — the pipeline handles them
   as part of training and prediction.

.. dropdown:: How does OpenSTEF handle missing data or delayed measurements?
   :icon: question

   OpenSTEF is designed with real-world data constraints in mind. The library explicitly
   supports scenarios where measurements arrive with a delay (e.g., smart meter data
   that is only available with a 15-minute lag) and where weather forecast data may not
   be available for the full horizon.

   The preprocessing pipelines include configurable strategies for handling gaps and
   aligning features with the correct temporal offsets so that your model never
   accidentally uses future information during training.

----

Evaluation & Development
------------------------

.. dropdown:: How do I evaluate whether my model changes are actually an improvement?
   :icon: question

   Use the ``openstef-beam`` package, which provides a dedicated backtesting and
   evaluation framework. It is designed specifically to answer the question: *"Are my
   model changes statistically significant?"*

   ``openstef-beam`` supports:

   - Backtesting over historical periods with configurable re-training windows.
   - Regression testing against saved benchmark results.
   - A suite of energy-forecasting-specific metrics.

   .. code-block:: bash

      pip install openstef-beam

   See the :doc:`api/index` for the full ``openstef_beam`` API reference.

.. dropdown:: Can I contribute my own model or pipeline component?
   :icon: question

   Yes. OpenSTEF is open source (MPL-2.0 licence) and welcomes contributions. The
   modular architecture makes it straightforward to add a new forecaster by implementing
   the ``BaseForecaster`` interface defined in ``openstef-core``.

   Before contributing, read the :doc:`contribute/index` guide, which covers the
   development setup (the project uses ``uv`` as its package manager), coding standards,
   and the pull request process.

.. dropdown:: Where can I find more examples?
   :icon: light-bulb

   The repository includes a dedicated ``examples/`` directory with runnable scripts
   covering common workflows such as:

   - Configuring a full forecasting pipeline with preprocessing and postprocessing.
   - Using presets for quick-start model setup.
   - Persisting and loading models with ``LocalModelStorage``.
   - Running backtests with ``openstef-beam``.

   You can also browse the :doc:`examples` page in this documentation, or explore the
   :doc:`api/index` for detailed reference material on every public class and function.