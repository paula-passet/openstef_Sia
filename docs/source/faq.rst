FAQ
===

This FAQ covers the most common questions from new users of OpenSTEF — an open-source Python library for short-term energy forecasting. Whether you're evaluating the library, setting it up for the first time, or trying to understand how its components fit together, you should find answers here.

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building and running short-term load forecasts in the energy sector. It provides a complete machine learning pipeline — data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing — all in one coherent package.

   OpenSTEF is **not** a standalone application or a hosted service. You integrate it into your own Python code or data platform, choosing exactly the components you need.

   The library was originally developed at Alliander, a Dutch grid operator, to tackle real-world challenges like congestion management. It is now an open-source project under the LF Energy umbrella.

   .. note::

      For a broader introduction, see :doc:`user_guide/index`.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load **hours to days ahead** — typically up to 48 hours into the future. This horizon is long enough to be operationally useful (e.g., scheduling, congestion management, EV charging capacity planning) but short enough that weather forecasts and recent load patterns are still highly predictive.

   Common use cases include:

   - Forecasting load at grid substations to identify upcoming capacity peaks
   - Estimating available capacity for EV charging
   - Predicting grid losses
   - Transport forecasting for network planning

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using a gradient boosting library directly gives you a model. OpenSTEF gives you a **forecasting system**. The key differences are:

   - **Energy-domain feature engineering** — built-in transformations for holiday calendars, lag features, and solar radiation-to-PV generation estimates, so you don't have to build these yourself.
   - **Probabilistic forecasts** — OpenSTEF produces uncertainty bandwidths alongside point predictions, not just a single value. This is critical for risk-aware operational decisions.
   - **Model-agnostic pipelines** — the same preprocessing and evaluation pipeline works across XGBoost, LightGBM, and other backends. Swapping models is a one-line change.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides a structured framework for regression testing and benchmarking model changes.
   - **Production-ready patterns** — model storage, versioned datasets, and workflow orchestration are first-class concepts in the library.

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF 4.0 requires **Python 3.12 or higher** (Python 3.13 is also supported). A 64-bit operating system is required; Windows, macOS, and Linux are all supported.

   If you need Python 3.10 or 3.11 support, consider using **OpenSTEF 3.x** instead.

   You can check your current Python version with:

   .. code-block:: bash

      python --version

   If you need to manage multiple Python versions, tools like `pyenv <https://github.com/pyenv/pyenv>`_ or ``conda`` make this straightforward.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest installation uses ``pip``:

   .. code-block:: bash

      pip install openstef

   OpenSTEF 4.0 has a modular architecture, so you can also install individual packages depending on what you need:

   .. code-block:: bash

      # Core data types and interfaces only
      pip install openstef-core

      # Forecasting models (XGBoost, LightGBM, etc.)
      pip install openstef-models

      # Backtesting, Evaluation, Analysis and Metrics
      pip install openstef-beam

   Other supported package managers:

   .. code-block:: bash

      # uv
      uv add openstef

      # conda
      conda install -c conda-forge openstef

   For a full walkthrough including development setup, see :doc:`user_guide/installation`.

.. dropdown:: What are the main packages in OpenSTEF 4.0?
   :icon: info

   OpenSTEF 4.0 is structured as a modular monorepo. Each package can be used independently:

   - **openstef-core** — Data types, interfaces, base classes, and shared utilities. This is the foundation that all other packages build on.
   - **openstef-models** — Concrete forecasting models (XGBoost, LightGBM, and more), preprocessing pipelines, energy-specific feature transformations, and explainability tools.
   - **openstef-meta** — Meta-learning and ensemble model architectures for combining multiple forecasters.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Use this to answer "are my model changes actually an improvement?" with structured regression testing.

   If you're just getting started, installing the top-level ``openstef`` package pulls in everything you need.

.. dropdown:: Which forecasting model should I use?
   :icon: light-bulb

   OpenSTEF supports several model backends. For most energy forecasting tasks, **LightGBM** and **XGBoost** are the recommended starting points — both are gradient boosting tree models that handle tabular time series data well and support quantile regression for probabilistic outputs.

   .. code-block:: python

      from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
      from openstef_models.models.forecasting.xgb_forecaster import XGBForecaster

      # LightGBM — generally faster training, good default choice
      forecaster = LGBMForecaster()

      # XGBoost — well-established, extensive hyperparameter control
      forecaster = XGBForecaster()

   If you're unsure, start with LightGBM. It tends to train faster and is a strong baseline. You can always benchmark alternatives using ``openstef-beam`` once you have a working pipeline.

   For a simple sanity-check baseline, a ``ConstantMedianForecaster`` is also available — useful for verifying your pipeline end-to-end before introducing a more complex model.

.. dropdown:: How do I make my first forecast?
   :icon: light-bulb

   The quickest path is to use a preset, which bundles a sensible default pipeline configuration for you:

   .. code-block:: python

      from openstef_models.models.forecasting_model import ForecastingModel
      from openstef_models.presets import get_default_forecasting_model
      from openstef_core.datasets import VersionedTimeSeriesDataset

      # Load your time series data
      dataset = VersionedTimeSeriesDataset(data=your_dataframe)

      # Get a pre-configured model with feature engineering included
      model = get_default_forecasting_model()

      # Train and predict
      model.fit(dataset.train)
      forecast = model.predict(dataset.predict)

   For a complete working example including synthetic data generation and model storage, see the examples in :doc:`examples`.

.. dropdown:: Does OpenSTEF only work with electricity load data?
   :icon: question

   No. While OpenSTEF was built for electricity grid use cases, the library is designed to be **unopinionated about the specific signal** you're forecasting. Any time series where energy-domain features (weather, solar irradiance, holidays, calendar effects) are relevant can benefit from OpenSTEF's pipeline.

   In practice it has been applied to load forecasting, solar generation, grid losses, and EV charging capacity — and the same pipeline structure applies to all of them.

.. dropdown:: Does OpenSTEF produce uncertainty estimates, or just point forecasts?
   :icon: question

   OpenSTEF produces **probabilistic forecasts** by default. Rather than a single predicted value, the library outputs forecasts at multiple quantiles, giving you an uncertainty bandwidth around the central prediction.

   This is built into the model backends (via quantile regression in LightGBM and XGBoost) and is a core design principle of the library — single-point predictions are rarely sufficient for operational energy decisions.

.. dropdown:: I'm getting a Python version error during installation. What should I do?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. The recommended approach is to use ``pyenv`` or ``conda`` to manage multiple Python versions without affecting your system Python:

   .. code-block:: bash

      # Using pyenv
      pyenv install 3.12
      pyenv local 3.12

      # Then reinstall
      pip install openstef

   See :doc:`user_guide/installation` for more troubleshooting steps.

.. dropdown:: Is OpenSTEF free to use? What is the license?
   :icon: info

   Yes. OpenSTEF is open-source software released under the **Mozilla Public License 2.0 (MPL-2.0)**. You are free to use it in your own projects, including commercial ones. The MPL-2.0 is a file-level copyleft license — modifications to OpenSTEF source files must be shared, but your own code that *uses* the library is not affected.

   OpenSTEF is a project under the `LF Energy <https://lfenergy.org/>`_ foundation.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - **Documentation** — start with :doc:`user_guide/index` for guides and :doc:`api/index` for the full API reference.
   - **Examples** — working code examples are available at :doc:`examples`.
   - **Community** — see :doc:`project/index` for links to the project's GitHub repository, issue tracker, and community channels.
   - **Contributing** — if you'd like to fix a bug or add a feature, :doc:`contribute/index` explains how to get started.