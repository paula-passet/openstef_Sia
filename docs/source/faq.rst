FAQ
===

This FAQ answers the most common questions from new OpenSTEF users — covering what the library
does, how to get started, how to choose a model, and what to do when things go wrong. If you
don't find your answer here, check the :doc:`user_guide/index` or open a discussion on GitHub.

.. note::
   OpenSTEF is a **Python library**, not a hosted service or application. You integrate it
   directly into your own code and infrastructure.

----

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library that provides
   a complete machine learning pipeline for producing short-term energy forecasts. It covers
   every stage of the workflow: data preprocessing, feature engineering, model training,
   probabilistic forecasting, evaluation, and post-processing.

   The library is model-agnostic and deliberately unopinionated — it ships with strong defaults
   for common energy forecasting tasks while remaining flexible enough to accommodate custom
   models, custom features, and complex integration requirements.

   See :doc:`user_guide/index` for a guided introduction.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load or generation **hours to days ahead** —
   typically up to 48 hours into the future. This horizon is directly useful for operational
   decisions such as congestion management, EV charging capacity planning, grid loss prediction,
   and transport forecasts.

   OpenSTEF produces a single-shot, multi-horizon forecast in one pass, so you get predictions
   across the entire horizon without running the model repeatedly.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using a raw ML library for energy forecasting requires you to build a large amount of
   supporting infrastructure yourself. OpenSTEF provides that infrastructure out of the box:

   - **Energy-specific feature engineering** — built-in transformations for lag features,
     holiday calendars, and solar radiation estimates (PV generation proxies).
   - **Probabilistic forecasts** — quantile regression support across all models, so you get
     uncertainty bands alongside point predictions rather than a single number.
   - **Complete pipelines** — preprocessing, training, prediction, and model persistence are
     wired together and tested as a unit.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides rigorous regression
     testing so you can tell whether a model change is statistically significant.
   - **Domain knowledge encoded** — years of production experience at Alliander are baked into
     the defaults, so you don't start from scratch.

.. dropdown:: Is OpenSTEF only useful for electricity grid operators?
   :icon: question

   No. While OpenSTEF was originally developed at Alliander for grid congestion management, the
   library is general-purpose. Any time-series forecasting problem with an energy or load
   character — solar generation, EV charging demand, building energy consumption, grid losses —
   is a natural fit. The pipelines and feature engineering are designed around energy data
   patterns, but the architecture is modular enough to adapt to related domains.

----

Installation & Requirements
----------------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   - **Python 3.12 or higher** (Python 3.13 is also supported)
   - A **64-bit operating system** — Windows, macOS, or Linux all work

   .. note::
      OpenSTEF 4.x requires Python 3.12+. If you are constrained to Python 3.10 or 3.11,
      use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   Install the meta-package with your preferred tool. It pulls in ``openstef-core`` and
   ``openstef-models`` automatically:

   .. code-block:: bash

      # pip
      pip install openstef

      # uv
      uv add openstef

      # conda
      conda install -c conda-forge openstef

   Verify the installation:

   .. code-block:: python

      import openstef_models
      print(f"OpenSTEF Models version: {openstef_models.__version__}")

   For more options, including development installs, see :doc:`user_guide/installation`.

.. dropdown:: What are the individual packages and do I need all of them?
   :icon: question

   OpenSTEF 4.0 uses a modular monorepo structure. The ``openstef`` meta-package installs the
   essentials, but you can also install packages individually:

   - **openstef-core** — data types, interfaces, base classes, and shared utilities. Every other
     package depends on this.
   - **openstef-models** — the ML models, feature engineering pipelines, and preprocessing
     transformations. This is where most users spend their time.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Install this when you
     need rigorous model comparison and regression testing.
   - **openstef-meta** — advanced ensemble and meta-learning architectures. Optional; for users
     who need more sophisticated model stacking.

   Most new users only need ``pip install openstef`` to get started.

.. dropdown:: I get a Python version error when installing. What should I do?
   :icon: alert

   If you see a message like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. The recommended approach is to use a version
   manager so you can switch Python versions without affecting your system installation:

   .. code-block:: bash

      # Using pyenv
      pyenv install 3.12
      pyenv local 3.12

      # Or create a conda environment with the right version
      conda create -n openstef-env python=3.12
      conda activate openstef-env
      pip install openstef

----

Models & Forecasting
---------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several forecasting model implementations in ``openstef-models``,
   including:

   - **LightGBM** (``LGBMForecaster``) — gradient boosting trees; fast, accurate, and the most
     commonly used model in production deployments.
   - **XGBoost** — another gradient boosting option with a different regularisation approach.
   - **Constant/Median baselines** — simple baselines useful for sanity-checking pipelines and
     as a fallback.

   All models support **quantile regression** for probabilistic output. The ``openstef-meta``
   package adds ensemble combiners (including an LGBM-based combiner) for multi-model stacking.

.. dropdown:: How do I choose which model to use?
   :icon: light-bulb

   For most energy load forecasting tasks, **LightGBM is a sensible default**. It trains
   quickly, handles the tabular feature matrices that OpenSTEF produces well, and has a mature
   quantile regression implementation.

   A practical approach:

   1. Start with the LightGBM preset to establish a baseline.
   2. Evaluate using ``openstef-beam`` to get statistically grounded metrics.
   3. Try XGBoost or a meta-ensemble if the baseline does not meet your accuracy requirements.

   Avoid over-engineering the model choice early — feature engineering and data quality
   typically have a larger impact than model selection for this problem class.

.. dropdown:: What does "probabilistic forecast" mean and why does it matter?
   :icon: question

   A probabilistic forecast produces a **range of predictions at different quantiles** rather
   than a single point estimate. For example, OpenSTEF can output the 10th, 50th, and 90th
   percentile predictions simultaneously.

   This matters for operational decisions: knowing that load will be between 80 MW and 120 MW
   with 80% confidence is far more actionable than knowing the point estimate is 100 MW. Grid
   operators can use the upper quantile as a conservative planning figure and the lower quantile
   to avoid unnecessary interventions.

.. dropdown:: Can I bring my own custom model?
   :icon: question

   Yes. OpenSTEF is designed to be model-agnostic. You can implement the ``Forecaster``
   interface from ``openstef-core`` and plug your model into the same pipeline infrastructure
   that the built-in models use — including feature engineering, model storage, and evaluation.

   See the API reference at :doc:`api/index` for the interface definition.

----

Getting Started
---------------

.. dropdown:: What does a minimal forecasting workflow look like?
   :icon: light-bulb

   The core pattern in OpenSTEF is: build a ``ForecastingModel`` with a feature pipeline,
   train it on a ``TimeSeriesDataset``, then call predict. Here is a minimal sketch:

   .. code-block:: python

      import pandas as pd
      from openstef_models.models.forecasting import ForecastingModel
      from openstef_models.feature_engineering import FeaturePipeline
      from openstef_core.datasets import VersionedTimeSeriesDataset
      from openstef_models.storage import LocalModelStorage

      # Wrap your time series data
      dataset = VersionedTimeSeriesDataset(data=your_dataframe)

      # Configure a pipeline with holiday and lag features
      pipeline = FeaturePipeline(steps=["holidays", "lags"])

      # Build and train the model
      model = ForecastingModel(feature_pipeline=pipeline)
      model.fit(dataset)

      # Persist and reload
      storage = LocalModelStorage(path="./models")
      storage.save(model)

      # Produce a forecast
      forecast = model.predict(dataset)

   For a complete, runnable example see the :doc:`examples` page.

.. dropdown:: What data format does OpenSTEF expect?
   :icon: question

   OpenSTEF works with **pandas DataFrames** with a ``DatetimeIndex``. The index should be
   timezone-aware and the data should be at a consistent frequency (e.g., 15-minute or hourly
   intervals). Missing values are handled by the preprocessing pipeline, but large gaps in
   historical data will reduce forecast quality.

   The ``VersionedTimeSeriesDataset`` and related dataset classes in ``openstef-core`` wrap
   your DataFrame and add metadata needed by the pipeline (such as the forecast horizon and
   resolution).

.. dropdown:: Do I need weather data to use OpenSTEF?
   :icon: question

   Weather data is **optional but strongly recommended** for solar and wind-related forecasting.
   OpenSTEF includes built-in feature transformations that convert solar radiation inputs into
   PV generation estimates, which significantly improves accuracy for grids with high solar
   penetration.

   For pure load forecasting without renewables, calendar features (time of day, day of week,
   holidays) and lag features from historical load are often sufficient to get a good baseline.

.. dropdown:: Where can I find complete, runnable examples?
   :icon: light-bulb

   The :doc:`examples` page contains end-to-end notebooks and scripts covering:

   - Configuring a full forecasting pipeline with preprocessing and postprocessing
   - Using the ``CustomForecastingWorkflow`` pattern for training and prediction
   - Backtesting a model with ``openstef-beam``

   The examples use synthetic data so you can run them immediately without needing access to
   real grid measurements.

----

Contributing & Community
-------------------------

.. dropdown:: How do I report a bug or request a feature?
   :icon: info

   OpenSTEF is developed in the open under the LF Energy umbrella. You can:

   - **Report bugs** by opening an issue on the GitHub repository.
   - **Request features** via GitHub Discussions.
   - **Contribute code** by following the guide at :doc:`contribute/index`.

   The project is licensed under the Mozilla Public License 2.0 (MPL-2.0).

.. dropdown:: Is OpenSTEF production-ready?
   :icon: question

   OpenSTEF 4.0 is the current major version and is actively maintained. The library has been
   running in production at Alliander — one of the largest grid operators in the Netherlands —
   for several years, where it powers congestion management forecasts across hundreds of grid
   points.

   That said, the 4.0 modular architecture is a significant redesign from 3.x. If you are
   migrating from OpenSTEF 3.x, watch for the ``openstef-compatibility`` package which will
   provide a migration layer (listed as coming soon in the current release).