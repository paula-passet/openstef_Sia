FAQ
===

New to OpenSTEF? This page answers the most common questions from users getting started with the library — from installation and requirements to model choices and what makes OpenSTEF different from general-purpose ML tools. If you don't find your answer here, check the :doc:`user_guide/index` or open a discussion on GitHub.

.. note::
   Click any question below to expand the answer.

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source **Python library** for building and running short-term energy load forecasts. It provides a complete machine learning pipeline — data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing — all with built-in domain knowledge for the energy sector.

   OpenSTEF is not a standalone application or a hosted service. It is a library you integrate into your own Python code or data platform. You bring your own data; OpenSTEF brings the forecasting machinery.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting refers to predicting energy load **hours to days ahead** — typically up to 48 hours into the future. This time horizon is critical for operational decisions such as congestion management, EV charging capacity planning, grid loss prediction, and transport forecasts.

   OpenSTEF is specifically designed and tuned for this horizon. It is not intended for long-term capacity planning (months or years ahead), which requires fundamentally different modelling approaches.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a general-purpose ML library directly means you have to build everything yourself: feature engineering, time-aware train/test splits, uncertainty estimation, retraining logic, and energy-specific transformations. OpenSTEF provides all of this out of the box.

   Key differentiators include:

   - **Probabilistic forecasts** — OpenSTEF produces quantile forecasts with uncertainty bandwidths, not just single-point predictions.
   - **Energy domain knowledge** — built-in feature engineering handles things like converting solar radiation data into PV generation estimates, lag features, and holiday calendars automatically.
   - **Model-agnostic pipelines** — swap between XGBoost, LightGBM, or other backends without rewriting your pipeline.
   - **Production-ready patterns** — the library includes backtesting, evaluation metrics, and model storage utilities designed for recurring operational forecasts.

   In short, OpenSTEF is the layer between raw time series data and a production-quality energy forecast.

.. dropdown:: Who develops and maintains OpenSTEF?
   :icon: question

   OpenSTEF was originally developed at **Alliander**, a Dutch distribution system operator, to solve real congestion management problems on the electricity grid. It is now an open-source project under the **LF Energy** foundation, with contributions welcome from the broader community.

   The library is licensed under the **Mozilla Public License 2.0 (MPL-2.0)**.

Installation & Requirements
---------------------------

.. dropdown:: What Python version do I need?
   :icon: question

   OpenSTEF 4.0 requires **Python 3.12 or higher** (Python 3.13 is also supported). It runs on 64-bit Windows, macOS, and Linux.

   .. note::

      If you need Python 3.10 or 3.11 support, use **OpenSTEF 3.x** instead. OpenSTEF 4.0 requires Python 3.12+ for modern type safety features and optimal performance.

   You can check your current Python version with:

   .. code-block:: bash

      python --version

   If you need to manage multiple Python versions, tools like `pyenv <https://github.com/pyenv/pyenv>`_ or ``conda`` make this straightforward.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   For most users, install the ``openstef`` meta-package, which pulls in the core components automatically:

   .. code-block:: bash

      pip install openstef

   Alternatively, using ``uv`` (recommended for faster dependency resolution):

   .. code-block:: bash

      uv add openstef

   Or via conda:

   .. code-block:: bash

      conda install -c conda-forge openstef

   For more detailed instructions, including development installs and optional packages, see :doc:`user_guide/installation`.

.. dropdown:: What packages does OpenSTEF install? Do I need all of them?
   :icon: question

   OpenSTEF 4.0 uses a **modular monorepo architecture**. The top-level ``openstef`` package is a meta-package that installs the essential components:

   - **openstef-core** — core data types, interfaces, base classes, and shared utilities. Every other package depends on this.
   - **openstef-models** — the ML models, feature engineering pipelines, and energy-specific data transformations.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Install this when you need to benchmark model changes or run regression tests.

   Additional packages are available for advanced use cases:

   - **openstef-meta** — ensemble and advanced model architectures (meta-learning).
   - **openstef-foundational-models** — deep learning and foundational models (coming soon).
   - **openstef-compatibility** — compatibility layer for migrating from OpenSTEF 3.x (coming soon).

   If you only need to run forecasts, ``pip install openstef`` is sufficient. Install ``openstef-beam`` separately if you also need backtesting and evaluation tooling.

.. dropdown:: I get a Python version error when installing. What should I do?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. The easiest way is to use ``pyenv`` or ``conda`` to install and switch to a supported version without affecting your system Python:

   .. code-block:: bash

      # Using conda
      conda create -n openstef-env python=3.12
      conda activate openstef-env
      pip install openstef

   See :doc:`user_guide/installation` for full troubleshooting guidance.

Models & Forecasting
--------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF includes several built-in forecasting models, all supporting **probabilistic (quantile) forecasting**:

   - **LGBMForecaster** — LightGBM-based gradient boosting, well-suited for tabular time series data with many features. Generally fast to train and accurate.
   - **XGBForecaster** — XGBoost-based gradient boosting, another strong performer for energy load data.
   - Additional models are available via ``openstef-meta`` for ensemble and advanced architectures.

   All models share a common interface, so switching between them requires minimal code changes:

   .. code-block:: python

      from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
      from openstef_models.models.forecasting.xgboost_forecaster import XGBForecaster

      # Both follow the same fit/predict interface
      model = LGBMForecaster()

   See :doc:`user_guide/index` for guidance on choosing and configuring models.

.. dropdown:: What is a probabilistic forecast and why does OpenSTEF produce one?
   :icon: question

   A **probabilistic forecast** provides not just a single predicted value but a range of possible outcomes expressed as quantiles (e.g., the 10th, 50th, and 90th percentile of expected load). This gives operators a sense of uncertainty — how confident the model is — which is essential for risk-based operational decisions.

   For example, a congestion management system needs to know not just the expected peak load, but how likely it is that load will *exceed* a critical threshold. A single-point forecast cannot answer that question reliably.

   OpenSTEF uses **multi-quantile regression** internally to produce these uncertainty bandwidths in a single training pass, making probabilistic forecasting a first-class feature rather than an afterthought.

.. dropdown:: Does OpenSTEF handle feature engineering automatically?
   :icon: question

   Yes. One of OpenSTEF's core strengths is its built-in, energy-domain-aware feature engineering. When you configure a forecasting pipeline, OpenSTEF can automatically generate:

   - **Lag features** — past load values at configurable time offsets.
   - **Holiday and calendar features** — day-of-week, hour-of-day, public holidays per country.
   - **Weather-derived features** — for example, converting solar irradiance into estimated PV generation.
   - **Rolling statistics** — moving averages and other aggregations over historical windows.

   You can customise or extend the feature pipeline for your specific use case. See :doc:`user_guide/index` for details on configuring the ``FeaturePipeline``.

.. dropdown:: Can I bring my own custom model?
   :icon: question

   Yes. OpenSTEF is designed to be **model-agnostic**. The library defines clear interfaces (via ``openstef-core``) that your custom model can implement, allowing it to slot into the same pipeline, feature engineering, and evaluation infrastructure as the built-in models.

   This means you can experiment with novel architectures while still benefiting from OpenSTEF's data handling, backtesting, and production utilities.

Usage & Integration
-------------------

.. dropdown:: Do I need a database or specific data infrastructure to use OpenSTEF?
   :icon: question

   No. OpenSTEF is a **library** — it does not impose any infrastructure requirements. You provide data as standard Python objects (primarily ``pandas`` DataFrames and OpenSTEF's ``TimeSeriesDataset`` types), and the library processes them in memory.

   How you store, retrieve, or stream your data is entirely up to you. OpenSTEF includes ``LocalModelStorage`` for saving trained models to disk, but you can implement your own storage backend by following the storage interface defined in ``openstef-core``.

.. dropdown:: Can I use OpenSTEF in a production pipeline or scheduled job?
   :icon: question

   Yes, and this is a primary design goal. OpenSTEF includes workflow utilities (such as ``CustomForecastingWorkflow``) and model persistence (``LocalModelStorage``) that are intended for recurring, automated forecasting runs — for example, retraining a model nightly and generating a 48-hour forecast every 15 minutes.

   Because OpenSTEF is a library, you integrate it into whatever orchestration system you already use (Airflow, Prefect, a simple cron job, etc.). The library handles the ML logic; your infrastructure handles scheduling and data movement.

.. dropdown:: Is OpenSTEF suitable for forecasting things other than electricity load?
   :icon: question

   OpenSTEF was built for electricity grid use cases — load forecasting, congestion management, EV charging capacity, and grid loss prediction — and its built-in feature engineering reflects that domain. However, the core pipeline is general enough to apply to any time series forecasting problem where:

   - You have regularly sampled historical measurements.
   - The target variable has temporal patterns (daily, weekly, seasonal cycles).
   - Probabilistic forecasts are useful.

   Users have applied OpenSTEF to related energy domains such as gas load and renewable generation forecasting. For highly different domains, you may need to customise or replace the feature engineering components.

.. dropdown:: Where can I find examples to get started quickly?
   :icon: light-bulb

   The best starting point is the :doc:`examples` page, which contains runnable notebooks and scripts covering common workflows. The ``forecasting_preset_example`` in particular demonstrates a complete end-to-end pipeline:

   .. code-block:: python

      from openstef_models.presets import ForecastingModel
      from openstef_models.pipelines import FeaturePipeline
      from openstef_core.storage import LocalModelStorage

      # Configure your pipeline, train, and generate forecasts
      # See the full example in docs/examples for complete working code

   For a conceptual overview of how training and prediction fit together, see :doc:`user_guide/index`.

Contributing & Community
------------------------

.. dropdown:: How do I report a bug or request a feature?
   :icon: checklist

   Open an issue on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_. For bugs, include your Python version, OpenSTEF version (``import openstef; print(openstef.__version__)``), and a minimal reproducible example.

   For feature requests, describe your use case — the maintainers prioritise features that address real operational needs.

.. dropdown:: How do I contribute code to OpenSTEF?
   :icon: checklist

   Contributions are welcome! Start by reading the :doc:`contribute/index` guide, which covers the development setup, coding standards, and the pull request process.

   OpenSTEF 4.0 uses ``uv`` as its primary package manager and follows a monorepo structure. The contributing guide walks you through setting up a local development environment:

   .. code-block:: bash

      git clone https://github.com/OpenSTEF/openstef.git
      cd openstef
      uv sync --dev