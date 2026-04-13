FAQ
===

This FAQ answers the most common questions from new OpenSTEF users — covering what the
library is, how to install it, which models to use, and how its components fit together.
If you don't find your answer here, check the :doc:`user_guide/index` or open a
discussion on the project's community channels.

.. rubric:: General

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source **Python library**
   for building and running machine learning pipelines that produce short-term load
   forecasts for the energy sector. It is not an application or a hosted service — it
   is a library you import into your own code and integrate with your own data
   infrastructure.

   The library covers every stage of the forecasting workflow: data preprocessing,
   energy-domain feature engineering, model training, probabilistic prediction,
   evaluation, and post-processing. You can use individual components à la carte or
   wire them together into a complete pipeline.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load (or generation) **hours to
   days ahead** — typically up to 48 hours into the future at 15-minute or hourly
   resolution. This horizon is long enough to be operationally useful (e.g., for
   congestion management or scheduling) but short enough that weather forecasts and
   recent historical patterns are the dominant signals.

   Longer-horizon planning (weeks, months, years) is outside the scope of OpenSTEF.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using a gradient-boosting library directly gives you a model, but not a forecasting
   system. OpenSTEF adds the layers that matter in production energy forecasting:

   - **Energy-domain feature engineering** — automatic lag features, holiday calendars,
     solar radiation estimates, and other domain-specific transformations are built in.
   - **Probabilistic forecasts** — every prediction comes with uncertainty bandwidths
     (quantile regression), not just a single point estimate.
   - **Model-agnostic pipelines** — swap XGBoost for LightGBM or any custom forecaster
     without changing your pipeline code.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides structured
     regression testing so you can verify that model changes are statistically
     significant before deploying them.
   - **Versioned model storage** — built-in utilities for persisting, loading, and
     versioning trained models.

   In short, OpenSTEF is the scaffolding around the model, not a replacement for the
   underlying algorithm.

.. dropdown:: Who created OpenSTEF and is it production-ready?
   :icon: info

   OpenSTEF was created by data science engineers at **Alliander**, a Dutch distribution
   system operator, where it is used in production for congestion management across the
   electricity grid. It is hosted under the **LF Energy** foundation and is actively
   maintained as an open-source project. Version 4.0 represents a significant
   architectural redesign focused on modularity and enterprise integration.

----

.. rubric:: Installation & Requirements

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF 4.0 requires **Python 3.12 or higher** (Python 3.13 is also supported).
   A 64-bit operating system is required (Windows, macOS, or Linux all work).

   .. note::

      If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead. Version 4.0
      adopted Python 3.12 as the minimum to take advantage of modern type safety
      features and performance improvements.

   You can check your current Python version with:

   .. code-block:: bash

      python --version

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The core library installs with any standard Python package manager:

   .. code-block:: bash

      # pip
      pip install openstef

      # uv (recommended for development)
      uv add openstef

      # conda / pixi
      conda install -c conda-forge openstef

   For more detailed instructions, including optional extras and development setup,
   see :doc:`user_guide/installation`.

.. dropdown:: I see a Python version error during installation. What do I do?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. The cleanest way to manage multiple
   Python versions is with `pyenv <https://github.com/pyenv/pyenv>`_ (Linux/macOS) or
   `conda <https://conda.io/>`_ (all platforms):

   .. code-block:: bash

      # Using conda to create a compatible environment
      conda create -n openstef-env python=3.12
      conda activate openstef-env
      pip install openstef

.. dropdown:: What are the main packages in OpenSTEF 4.0?
   :icon: info

   OpenSTEF 4.0 is structured as a **modular mono-repo**. You can install only the
   parts you need:

   - **openstef-core** — data types, base classes, shared interfaces, and exceptions.
     This is the foundation that all other packages depend on.
   - **openstef-models** — forecasting models, preprocessing pipelines, energy-specific
     feature engineering, explainability tools, and ready-to-use presets.
   - **openstef-meta** — meta-learning components including ensemble models and
     advanced model architectures.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Use this to
     answer "are my model changes statistically significant?" and to run regression
     tests against benchmarks.

   The top-level ``openstef`` package installs a sensible default set of these
   components. See :doc:`user_guide/installation` for details on installing specific
   extras.

----

.. rubric:: Models & Forecasting

.. dropdown:: Which forecasting model should I use?
   :icon: question

   OpenSTEF ships with several models out of the box. For most energy load forecasting
   tasks, **LightGBM** and **XGBoost** are the recommended starting points — both are
   gradient-boosted tree models that handle the tabular, time-series-derived features
   that OpenSTEF generates very well.

   - **LightGBM** (``LGBMForecaster``) — generally faster to train and memory-efficient;
     a good default for iterative experimentation.
   - **XGBoost** (``XGBoostForecaster``) — well-established, with fine-grained control
     over regularization and tree structure.

   Both support quantile regression for probabilistic forecasts. If you have multiple
   related forecast targets, the **meta-learning ensemble** in ``openstef-meta`` can
   combine individual model outputs for improved accuracy.

   Start with the presets in ``openstef-models`` to get a working pipeline quickly,
   then tune hyperparameters once you have a baseline.

.. dropdown:: Does OpenSTEF only produce single-point forecasts?
   :icon: question

   No — probabilistic forecasting is a first-class feature. Every built-in forecaster
   supports **quantile regression**, so a single call returns a forecast with multiple
   quantile bands (e.g., p10, p50, p90). This gives you uncertainty estimates alongside
   the central prediction, which is critical for risk-aware operational decisions like
   congestion management.

.. dropdown:: How do I get started with a basic forecasting pipeline?
   :icon: light-bulb

   The fastest path is to use one of the built-in presets from ``openstef-models``,
   which wire together preprocessing, feature engineering, and a model for you:

   .. code-block:: python

      import pandas as pd
      from openstef_models.models.forecasting_model import ForecastingModel
      from openstef_models.pipeline.feature_pipeline import FeaturePipeline
      from openstef_models.storage.local_model_storage import LocalModelStorage

      # 1. Prepare your time series data as a VersionedTimeSeriesDataset
      #    (see the user guide for data format requirements)

      # 2. Configure a forecasting model with a feature pipeline
      model = ForecastingModel(
          forecaster=...,          # e.g. LGBMForecaster()
          feature_pipeline=FeaturePipeline(...),
          model_storage=LocalModelStorage(path="./models"),
      )

      # 3. Train
      model.train(training_dataset)

      # 4. Predict — returns probabilistic forecasts
      forecast = model.predict(input_dataset)

   For a complete, runnable example see the
   `examples directory <https://github.com/OpenSTEF/openstef/tree/main/examples>`_
   in the repository, or the :doc:`user_guide/index`.

.. dropdown:: Can I plug in my own custom model?
   :icon: question

   Yes. OpenSTEF is explicitly **model-agnostic**. Any forecaster that implements the
   ``Forecaster`` interface from ``openstef-models`` can be dropped into a
   ``ForecastingModel`` pipeline. This means you can use a proprietary model, a
   research prototype, or a model from any third-party library while still benefiting
   from OpenSTEF's feature engineering, evaluation, and storage utilities.

----

.. rubric:: Architecture & Integration

.. dropdown:: Is OpenSTEF a service I can deploy, or just a library?
   :icon: info

   OpenSTEF is purely a **Python library**. It has no server component, no REST API,
   and no built-in scheduler. You integrate it into your own application, workflow
   orchestrator (Airflow, Prefect, etc.), or notebook environment. This design is
   intentional — it keeps OpenSTEF unopinionated about your infrastructure and easy
   to embed in complex software landscapes.

.. dropdown:: How does OpenSTEF handle model persistence?
   :icon: question

   The library includes a ``LocalModelStorage`` class for file-based model saving and
   loading, with support for versioned model artefacts. You can read and write
   configuration using YAML files through the built-in ``BaseConfig`` utilities:

   .. code-block:: python

      from openstef_core.base_model import BaseConfig

      # Write a configuration to disk
      config = MyForecastConfig(...)
      config.write_yaml("forecast_config.yaml")

      # Load it back later
      loaded_config = MyForecastConfig.read_yaml("forecast_config.yaml")

   For production deployments with custom storage backends (databases, object stores),
   you can implement the storage interface defined in ``openstef-core``.

.. dropdown:: What is openstef-beam and do I need it?
   :icon: question

   ``openstef-beam`` stands for **Backtesting, Evaluation, Analysis, and Metrics**. It
   is an optional package that answers the question: *"Are my model changes actually an
   improvement?"*

   You need it when you want to:

   - Run structured backtests over historical periods
   - Compare two model versions with statistical rigour
   - Generate evaluation plots and performance reports
   - Set up regression testing in a CI/CD pipeline to catch model degradation

   If you are just getting started or only need to generate forecasts, you can skip
   ``openstef-beam`` initially and add it later when you need systematic evaluation.

.. dropdown:: Where can I find more examples and community support?
   :icon: info

   - **Examples** — the `examples directory <https://github.com/OpenSTEF/openstef/tree/main/examples>`_
     in the repository contains complete, runnable scripts covering common use cases.
   - **User Guide** — :doc:`user_guide/index` covers installation, data formats,
     pipeline configuration, and more.
   - **API Reference** — :doc:`api/index` provides full documentation for every public
     class and function.
   - **Community** — :doc:`project/index` lists the project's communication channels,
     governance, and how to ask questions.
   - **Contributing** — :doc:`contribute/index` explains how to report bugs, suggest
     features, and submit pull requests.