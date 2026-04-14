FAQ
===

This FAQ answers the most common questions from new OpenSTEF users — covering what the
library does, how to get it running, how to choose models, and how the pieces fit
together. If you need deeper detail on any topic, follow the links to the relevant
documentation pages.

.. note::
   Can't find your answer here? Open a discussion on the
   `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_ or reach out
   via the community channels listed in :doc:`project/index`.

----

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source **Python library**
   for building short-term load and energy forecasts. It provides a complete machine
   learning pipeline — data preprocessing, feature engineering, model training,
   probabilistic forecasting, evaluation, and post-processing — all in one package.

   OpenSTEF is *not* a standalone application or a hosted service. You import it into
   your own Python code and use its components to build forecasting workflows that fit
   your infrastructure.

   .. code-block:: python

      import openstef_models
      print(openstef_models.__version__)

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load or generation **hours to days
   ahead** — typically up to 48 hours into the future. This time horizon is critical
   for operational decisions such as congestion management, transport forecasting, EV
   charging capacity estimation, and grid loss prediction.

   Longer-horizon planning (weeks, months, years) is a different problem domain and
   is outside the scope of OpenSTEF.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a gradient boosting library directly gives you a model. OpenSTEF gives you a
   **complete, energy-aware forecasting pipeline** built on top of those models:

   - **Domain-specific feature engineering** — built-in transformations for solar
     irradiance, holidays, lag features, and other energy-sector signals that would
     take significant effort to replicate from scratch.
   - **Probabilistic forecasts** — rather than a single point prediction, OpenSTEF
     produces forecasts with uncertainty bandwidths using quantile regression.
   - **Model-agnostic design** — swap XGBoost for LightGBM (or a custom model) without
     rewriting your pipeline.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides rigorous
     regression testing so you can measure whether a model change is statistically
     significant.
   - **Production-ready patterns** — versioned datasets, model storage, and workflow
     orchestration are all first-class concepts in the library.

.. dropdown:: Who builds and maintains OpenSTEF?
   :icon: info

   OpenSTEF was originally developed by data science engineers at **Alliander**, a
   Dutch electricity grid operator, to solve real congestion management problems on
   their network. It is now an open-source project under the
   `LF Energy <https://lfenergy.org/>`_ foundation and welcomes contributions from
   the broader community. See :doc:`project/index` for governance details and
   :doc:`contribute/index` for contribution guidelines.

----

Installation & Requirements
---------------------------

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF 4.0 requires **Python 3.12 or higher** (Python 3.13 is also supported).
   The library uses modern type safety features that are not available in earlier
   Python releases.

   If you are constrained to Python 3.10 or 3.11, use **OpenSTEF 3.x** instead.

   Check your current Python version with:

   .. code-block:: bash

      python --version

   We recommend `pyenv <https://github.com/pyenv/pyenv>`_ or
   `conda <https://conda.io/>`_ to manage multiple Python versions on the same machine.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest approach is to install the ``openstef`` meta-package, which pulls in
   the core components automatically:

   .. code-block:: bash

      # pip
      pip install openstef

      # uv (recommended for faster dependency resolution)
      uv add openstef

      # conda / pixi
      conda install -c conda-forge openstef

   This installs ``openstef-core`` (data types, interfaces, base classes) and
   ``openstef-models`` (ML models, feature engineering, presets). For backtesting and
   evaluation tooling, also install ``openstef-beam``:

   .. code-block:: bash

      pip install openstef-beam

   See :doc:`user_guide/installation` for the full installation guide, including
   optional extras and development setup.

.. dropdown:: What operating systems are supported?
   :icon: checklist

   OpenSTEF runs on **Windows, macOS, and Linux** — any 64-bit operating system with
   a supported Python version. The library has no native compiled extensions of its
   own; all platform-specific dependencies (XGBoost, LightGBM, etc.) ship pre-built
   wheels for all major platforms.

.. dropdown:: I see a Python version error when installing. What do I do?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   Your active Python interpreter is too old. Upgrade to Python 3.12+ using
   ``pyenv``, ``conda``, or your system package manager, then retry the install.
   Alternatively, pin to the OpenSTEF 3.x release series, which supports Python 3.10
   and 3.11.

----

Library Architecture
--------------------

.. dropdown:: What are the different OpenSTEF packages and which one do I need?
   :icon: info

   OpenSTEF 4.0 is structured as a **modular monorepo**. Each package has a distinct
   responsibility:

   - **openstef** — meta-package; installs core components in one command.
   - **openstef-core** — data types, interfaces, shared exceptions, and base classes.
     Every other package depends on this.
   - **openstef-models** — ML models (XGBoost, LightGBM, …), feature engineering
     pipelines, and ready-to-use presets for common forecasting tasks.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Use this
     when you need to rigorously compare model versions or run regression tests.
   - **openstef-foundational-models** — Deep learning and foundational models
     *(coming soon)*.
   - **openstef-compatibility** — Compatibility layer for migrating from OpenSTEF 3.x
     *(coming soon)*.

   **Most users only need** ``pip install openstef`` to get started. Add
   ``openstef-beam`` when you reach the evaluation and backtesting stage.

.. dropdown:: Is OpenSTEF a framework or a library?
   :icon: question

   OpenSTEF is a **library**. It does not impose an application structure, a specific
   scheduler, or a particular data store on you. You call its functions and classes
   from your own code, integrate them into your existing pipelines, and retain full
   control over orchestration. The library provides high-level workflow helpers as
   conveniences, but you are never required to use them.

----

Models & Forecasting
--------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   Out of the box, ``openstef-models`` ships implementations built on:

   - **XGBoost** — gradient boosting trees; strong general-purpose baseline.
   - **LightGBM** — faster gradient boosting; often preferred for larger datasets.

   Both are wrapped to support **quantile regression**, so they produce probabilistic
   forecasts with configurable uncertainty intervals rather than single-point
   predictions. The library is model-agnostic by design: you can register a custom
   model that implements the ``Forecaster`` interface and use it anywhere in the
   pipeline without changing any other code.

   Additional architectures (deep learning, foundational models) are planned for the
   ``openstef-foundational-models`` package.

.. dropdown:: How do I choose between XGBoost and LightGBM?
   :icon: light-bulb

   Both models perform well on energy time series. As a starting point:

   - Use **LightGBM** when training speed matters or your dataset is large — it is
     typically faster to train and uses less memory.
   - Use **XGBoost** when you want a well-understood baseline with extensive
     community documentation and tooling.

   In practice, the best approach is to benchmark both on your specific data using
   ``openstef-beam``'s evaluation utilities. The pipeline interface is identical for
   both, so switching is a one-line change.

.. dropdown:: What is a probabilistic forecast and why does OpenSTEF produce one?
   :icon: question

   A probabilistic forecast provides a **range of likely outcomes** rather than a
   single predicted value. OpenSTEF achieves this through quantile regression —
   training the model to predict multiple quantiles (e.g., the 10th, 50th, and 90th
   percentile) simultaneously.

   For grid operators, knowing the uncertainty around a forecast is just as important
   as the forecast itself. A narrow band means high confidence; a wide band signals
   that conditions are uncertain and more conservative operational decisions may be
   warranted.

.. dropdown:: Does OpenSTEF handle feature engineering automatically?
   :icon: question

   Yes. The ``openstef-models`` feature pipeline includes built-in transformations
   relevant to energy forecasting:

   - **Lag features** — past load values at configurable offsets.
   - **Holiday features** — calendar-aware flags for national and regional holidays.
   - **Solar/weather features** — transformations that convert raw weather inputs
     (e.g., solar irradiance) into signals useful for PV generation estimation.
   - **Data scaling** — normalisation steps applied before model training.

   You can compose these into a ``FeaturePipeline``, extend them with your own
   transformers, or replace them entirely. See :doc:`user_guide/index` for pipeline
   configuration examples.

----

Getting Started
---------------

.. dropdown:: What is the minimal code to train a model and make a forecast?
   :icon: light-bulb

   The quickest path uses one of the built-in presets, which bundle a sensible
   default pipeline configuration:

   .. code-block:: python

      from datetime import timedelta
      from openstef_models.presets import get_preset
      from openstef_core.datasets import VersionedTimeSeriesDataset

      # Load your time series data into a VersionedTimeSeriesDataset
      # (replace this with your actual data loading logic)
      dataset = VersionedTimeSeriesDataset(...)

      # Retrieve a pre-configured forecasting model
      model = get_preset("xgboost")

      # Train
      model.fit(dataset.train, dataset.validation)

      # Predict
      forecast = model.predict(dataset.test)

   For a fully worked example including synthetic data generation, model storage, and
   workflow orchestration, see the :doc:`examples` page.

.. dropdown:: Where do I store trained models?
   :icon: question

   OpenSTEF provides a ``LocalModelStorage`` class for file-based persistence during
   development and testing. In production you would typically implement the
   ``ModelStorage`` interface to back the store with a database, object storage
   (S3, Azure Blob, etc.), or an MLflow tracking server — whichever fits your
   infrastructure. Because OpenSTEF is a library, it does not mandate a specific
   storage backend.

.. dropdown:: Can I use OpenSTEF with my existing data pipeline?
   :icon: question

   Yes. OpenSTEF works with standard **pandas DataFrames** and numpy arrays as its
   primary data interchange format. If your pipeline already produces DataFrames you
   can pass them directly to OpenSTEF's dataset constructors. The library does not
   require a specific ingestion framework, message broker, or database — integration
   points are plain Python objects.

.. dropdown:: Where can I find more examples?
   :icon: light-bulb

   The :doc:`examples` page contains runnable notebooks and scripts covering common
   use cases. The ``examples/`` directory in the repository includes a
   ``forecasting_preset_example.py`` that walks through a complete pipeline from
   synthetic data generation to trained model storage. The :doc:`user_guide/index`
   provides conceptual explanations alongside code for each major feature area.