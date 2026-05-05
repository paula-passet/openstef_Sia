FAQ
===

This FAQ covers the most common questions from new users of OpenSTEF — from understanding what the library does, to installing it and making your first forecast. If you don't find your answer here, check the :doc:`getting_started` guide or open a discussion on GitHub.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building and running short-term energy load forecasts. It provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing — all in one package.

   It is not a standalone application or a web service. You import it into your own Python code or notebooks and call its pipelines directly.

   .. code-block:: python

      from openstef.models import create_model
      from openstef.pipeline import train_pipeline, forecast_pipeline

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term means predicting energy load **hours to roughly seven days ahead**. Beyond seven days, weather forecasts lose the 15-minute resolution that solar and wind predictions depend on, so forecast quality degrades significantly.

   Within that horizon, OpenSTEF produces forecasts at 15-minute intervals — suitable for operational decisions like congestion management, transport planning, and EV charging capacity estimation.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Three things set OpenSTEF apart from a generic ML toolkit:

   - **Energy-domain feature engineering** — built-in transformations convert raw inputs (e.g., solar irradiance) into predictive features like estimated PV generation, without you writing that logic yourself.
   - **Probabilistic forecasts** — OpenSTEF produces uncertainty bandwidths alongside point predictions, not just a single number. This matters for risk-aware decisions like congestion management.
   - **Complete pipelines** — preprocessing, training, backtesting, and evaluation are all wired together. You don't assemble the pieces; you call a pipeline.

.. dropdown:: Who uses OpenSTEF and for what?
   :icon: question

   OpenSTEF was created at Alliander, a Dutch distribution system operator, and is currently in production making forecasts for over 10,000 grid locations. Typical use cases include:

   - **Congestion management** — predicting peak load 2 days ahead so grid operators can call customers to reduce consumption before equipment limits are exceeded.
   - **Transport forecasts** — communicating planned energy usage to upstream network operators (e.g., from Alliander to TenneT).
   - **Grid loss forecasting** — minimising financial cost by weighting forecast errors against real-time market prices.
   - **EV charging capacity estimation** and district heating demand forecasting.

   The library is designed to be general enough for any energy forecasting use case, not just Alliander's specific setup.

.. dropdown:: Is OpenSTEF only useful for grid operators?
   :icon: question

   No. While it was built in a grid-operator context, OpenSTEF is a general-purpose energy forecasting library. Researchers, energy retailers, aggregators, and anyone working with time-series load data can use it. The V4 architecture explicitly generalises away from Alliander-specific assumptions — for example, holiday calendars and data formats are now configurable rather than hard-coded.

----

Installation and Requirements
------------------------------

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   OpenSTEF V4 is structured as a modular mono-repo. Install the packages you need via pip:

   .. code-block:: python

      # Core data types and interfaces
      pip install openstef-core

      # Forecasting models and preprocessing pipelines
      pip install openstef-models

      # Backtesting, evaluation, analysis, and metrics
      pip install openstef-beam

   For most users getting started, ``openstef-models`` pulls in ``openstef-core`` as a dependency. See :doc:`getting_started` for a step-by-step walkthrough.

.. dropdown:: What Python version does OpenSTEF require?
   :icon: question

   OpenSTEF V4 targets modern Python. Check the ``pyproject.toml`` in each package for the exact minimum version, but Python 3.10 or later is recommended. The development toolchain uses ``uv`` and ``ruff`` for fast dependency management and linting.

.. dropdown:: Does OpenSTEF require a database or external services?
   :icon: question

   No. OpenSTEF is a **library** — it operates on data you pass in as Python objects (typically pandas DataFrames). It does not require a running database, MLflow server, or any other external service out of the box.

   In V3, there was a tighter coupling to ``openstef-dbc`` (a database connector) and MLflow. V4 deliberately decouples these so you can integrate your own data sources and experiment tracking if you want them, but they are not required.

.. dropdown:: What data do I need to get started?
   :icon: question

   At minimum you need a time-series of historical load measurements at 15-minute resolution, plus weather forecast data (temperature, wind speed, solar irradiance) covering the same period. OpenSTEF handles the feature engineering from there.

   Data quality matters: the library includes preprocessing pipelines that handle missing values and outliers, but "garbage in, garbage out" still applies. See :doc:`guides/data_preparation` for details on expected input formats.

----

Models and Forecasting
-----------------------

.. dropdown:: Which models does OpenSTEF support?
   :icon: question

   OpenSTEF is **model-agnostic** — the pipeline architecture is designed so models are interchangeable. Out of the box, the ``openstef-models`` package ships with gradient-boosted tree models (including XGBoost variants) as well as presets tuned for common energy forecasting use cases.

   The ``openstef-meta`` package (in progress) adds modern ensemble and meta-learning architectures. You can also plug in a custom model by implementing the model interface defined in ``openstef-core``.

   .. code-block:: python

      from openstef.models import get_preset_model

      # Use a built-in preset tuned for congestion management
      model = get_preset_model("congestion_management")

.. dropdown:: How do I choose the right model for my use case?
   :icon: question

   The built-in presets are a good starting point:

   - **Congestion management** — optimised for peak detection and high-quantile accuracy.
   - **Transport forecasts** — balanced performance across the full forecast horizon.
   - **Grid losses** — error weighting based on market prices.

   If none of the presets fit, start with the default gradient-boosted model and evaluate using ``openstef-beam``. The Alliander 2021 benchmark (50+ energy signals including solar parks, wind parks, and transformers) is open-source and runnable out of the box — it gives you realistic accuracy numbers before you commit to a model choice.

.. dropdown:: What does a probabilistic forecast look like?
   :icon: question

   Instead of a single predicted value per timestep, OpenSTEF returns a forecast with multiple quantiles — for example, the 10th, 50th, and 90th percentile of expected load. This lets downstream systems reason about uncertainty: a grid operator can act on the 90th percentile to be conservative, while a cost-optimisation system might use the median.

   .. note:: [VISUALIZATION: Example probabilistic forecast plot showing load over time with shaded uncertainty bands between quantiles]

.. dropdown:: How far ahead can OpenSTEF forecast?
   :icon: question

   The practical upper limit is **around seven days**. Beyond that, weather forecasts no longer provide 15-minute resolution for solar and wind, so the features that drive accuracy become unavailable. For most operational use cases (congestion management, transport planning), a 2-day horizon is typical.

.. dropdown:: How accurate are the forecasts?
   :icon: question

   Accuracy depends on three factors: the use case, the quality of your input data, and the metric you care about. A congestion management system cares about peak detection rate, not nighttime accuracy — so a model that looks mediocre on RMSE might be excellent for its actual purpose.

   The most reliable way to answer this for your own data is to run the Alliander 2021 benchmark with ``openstef-beam``:

   .. code-block:: python

      from openstef_beam.backtesting import BacktestPipeline

      pipeline = BacktestPipeline(model=my_model, dataset="alliander_2021")
      results = pipeline.run()
      print(results.summary())

   This gives you accuracy metrics and plots across 50+ realistic energy signals.

----

Architecture and Design
------------------------

.. dropdown:: What is the difference between openstef-core, openstef-models, and openstef-beam?
   :icon: question

   OpenSTEF V4 is a modular mono-repo. Each package has a distinct responsibility:

   - **openstef-core** — data types, interfaces, base classes, and shared utilities. Every other package depends on this.
   - **openstef-models** — forecasting models, preprocessing pipelines, energy-specific feature transformations, and presets for common use cases.
   - **openstef-beam** — backtesting, evaluation, analysis, and metrics. Use this to answer "are my model changes actually an improvement?"
   - **openstef-meta** *(in progress)* — advanced ensemble and meta-learning architectures.
   - **openstef-foundation** *(in progress)* — pre-trained models and transfer learning for energy data.

   You only need to install the packages relevant to your workflow.

.. dropdown:: Can I use OpenSTEF in a production pipeline (e.g., Dagster, Airflow, cron)?
   :icon: question

   Yes. Because OpenSTEF is a library, it integrates naturally into any orchestration system. You call its pipeline functions from your own workflow tasks. The V4 architecture was explicitly designed with enterprise integration in mind — flexible, modular, and not tied to a specific deployment pattern.

   Reference deployment examples for cron jobs, Dagster, and cloud platforms are being added to the documentation. See :doc:`guides/deployment` for current guidance.

.. dropdown:: Is OpenSTEF V4 compatible with V3?
   :icon: question

   V4 is a major architectural refactor and is **not directly backwards-compatible** with V3. The modular mono-repo structure, decoupled dependencies, and revised pipeline APIs are all breaking changes. V4 is currently in **alpha** — feature parity with V3 is the target for the stable release.

   If you are migrating from V3, see :doc:`migration_v3_to_v4` for a guide covering the key differences and how to update your code.

.. dropdown:: How do I contribute or get help?
   :icon: question

   OpenSTEF is community-driven. The best places to engage are:

   - **GitHub** — public backlog with stories, tasks, milestones, and "good first issues" for new contributors.
   - **Slack** — community channel for questions and discussion.
   - **Bi-weekly community meetings** and co-coding sessions every 8 weeks.

   For bug reports and feature requests, open an issue on GitHub. For questions, start with the Slack channel or the GitHub Discussions tab.