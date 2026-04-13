FAQ
===

This FAQ answers the most common questions from new OpenSTEF users — covering what the library
does, how to get started, which models to use, and how the packages fit together. If you need
more depth on any topic, follow the links to the relevant documentation pages.

.. note::
   Can't find your answer here? Open a discussion on the
   `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_.

----

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source **Python library** for
   building machine learning pipelines that produce short-term energy forecasts. It is
   developed under the LF Energy umbrella and originated at Alliander, a Dutch grid operator.

   The library covers the full ML lifecycle — data preprocessing, feature engineering, model
   training, probabilistic forecasting, evaluation, and post-processing — all in one coherent
   package. It is *not* a standalone application or a hosted service; you integrate it into
   your own Python code and infrastructure.

   See :doc:`user_guide/index` for a guided introduction.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load or generation **hours to a few days
   ahead** — typically up to 48 hours. This horizon is long enough to be operationally useful
   (e.g., scheduling, congestion management) but short enough that statistical and ML models
   can achieve high accuracy using recent measurements and near-term weather forecasts.

   Common use cases include:

   - Grid congestion management (identifying peak load moments 2 days ahead)
   - Transport capacity forecasting
   - EV charging capacity estimation
   - Grid loss prediction

.. dropdown:: What makes OpenSTEF different from just training an XGBoost model myself?
   :icon: light-bulb

   Training a single model is only a small part of production forecasting. OpenSTEF adds the
   surrounding infrastructure that is tedious to build from scratch:

   - **Energy-domain feature engineering** — built-in transformations for solar irradiance,
     holidays, lag features, and other energy-specific signals.
   - **Probabilistic forecasts** — quantile regression out of the box, so you get uncertainty
     bandwidths alongside point forecasts, not just a single number.
   - **Model-agnostic pipelines** — swap XGBoost for LightGBM (or a custom model) without
     rewriting your pipeline.
   - **Single-shot multi-horizon forecasting** — one training run produces forecasts across
     multiple time horizons simultaneously.
   - **Evaluation and backtesting** — the ``openstef-beam`` package answers "are my model
     changes actually significant?" with rigorous regression testing.
   - **Presets for common setups** — sensible defaults so you can get a working forecast
     running quickly, then tune from there.

.. dropdown:: Is OpenSTEF only useful for grid operators?
   :icon: question

   No. While OpenSTEF was built to solve congestion management problems at a grid operator,
   the library itself is general-purpose for energy time series forecasting. Researchers,
   energy retailers, aggregators, and anyone working with load or generation data can use it.
   The domain-specific feature engineering (e.g., PV generation estimates from solar
   radiation) is optional — you can use only the parts that are relevant to your use case.

----

Installation & Requirements
----------------------------

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF 4.0 requires **Python 3.12 or higher** (Python 3.13 is also supported). If you
   are on Python 3.10 or 3.11, use OpenSTEF 3.x instead.

   Check your Python version before installing:

   .. code-block:: bash

      python --version

   If you need to manage multiple Python versions, tools like
   `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ make this
   straightforward.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   For most users, install the meta-package with pip:

   .. code-block:: bash

      pip install openstef

   This pulls in ``openstef-core`` and ``openstef-models`` — everything you need to build
   and run forecasting pipelines. Other package managers are also supported:

   .. code-block:: bash

      # uv
      uv add openstef

      # conda
      conda install -c conda-forge openstef

      # pixi
      pixi add openstef

   For detailed instructions, including optional packages and development setups, see
   :doc:`user_guide/installation`.

.. dropdown:: What are the individual packages and do I need all of them?
   :icon: question

   OpenSTEF 4.0 uses a **modular monorepo** structure. The top-level ``openstef`` package is
   a meta-package that installs the essentials. The individual packages are:

   - **openstef-core** — data types, interfaces, base classes, and shared utilities.
     Everything else depends on this.
   - **openstef-models** — ML models, feature engineering pipelines, preprocessing, and
     explainability. This is where most users spend their time.
   - **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics. Install this when
     you need rigorous model comparison and regression testing.
   - **openstef-foundational-models** — Deep learning and foundational model architectures
     *(coming soon)*.
   - **openstef-compatibility** — Compatibility layer for OpenSTEF 3.x users migrating to
     4.0 *(coming soon)*.

   Most users only need ``pip install openstef``. Add ``openstef-beam`` when you are ready
   to run backtests or evaluate model changes systematically.

.. dropdown:: I get a Python version error when installing. What do I do?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. The quickest path is to create a fresh
   virtual environment with the correct version:

   .. code-block:: bash

      # Using conda
      conda create -n openstef-env python=3.12
      conda activate openstef-env
      pip install openstef

      # Using pyenv + venv
      pyenv install 3.12
      pyenv local 3.12
      python -m venv .venv
      source .venv/bin/activate
      pip install openstef

----

Models & Forecasting
---------------------

.. dropdown:: Which forecasting model should I use?
   :icon: light-bulb

   OpenSTEF ships with several models, and the right choice depends on your data and goals:

   - **XGBoost** — a strong default for most energy forecasting tasks. Well-understood,
     fast to train, and produces reliable probabilistic forecasts via quantile regression.
   - **LightGBM** — similar to XGBoost but often faster on larger datasets. Also supports
     quantile regression out of the box.

   Both models expose a ``HyperParams`` class (``XGBoostHyperParams``,
   ``LGBMHyperParams``) that gives you fine-grained control over tree depth, learning rate,
   regularisation, and sampling. A good starting point is to use the built-in presets, which
   apply sensible defaults, and then tune from there.

   .. code-block:: python

      from openstef_models.models.forecasting.xgb import XGBoostHyperParams

      hyperparams = XGBoostHyperParams(
          n_estimators=200,
          max_depth=6,
          learning_rate=0.05,
      )

   If you are unsure, start with XGBoost — it is the most battle-tested option in
   production deployments.

.. dropdown:: Does OpenSTEF only produce point forecasts?
   :icon: question

   No — probabilistic forecasting is a first-class feature. OpenSTEF uses **quantile
   regression** to produce forecasts with uncertainty bandwidths. Instead of a single
   predicted value, you get a distribution of outcomes, which is essential for risk-aware
   decisions like congestion management.

   Both XGBoost and LightGBM backends support this via ``MultiQuantileRegressor``
   internally, so you do not need to configure it manually when using the standard pipelines.

.. dropdown:: Can I bring my own custom model?
   :icon: question

   Yes. OpenSTEF is model-agnostic by design. Custom models should implement the
   ``Predictor`` interface from ``openstef_core``, which follows the familiar
   scikit-learn ``fit`` / ``predict`` pattern and adds state management for serialisation.

   .. code-block:: python

      from openstef_core.mixins.predictor import Predictor
      from openstef_core.datasets import ForecastInputDataset, ForecastDataset

      class MyCustomForecaster(Predictor[ForecastInputDataset, ForecastDataset]):
          def fit(self, data: ForecastInputDataset, **kwargs) -> None:
              # Your training logic here
              ...

          def predict(self, data: ForecastInputDataset) -> ForecastDataset:
              # Your inference logic here
              ...

   Once your model implements this interface, it plugs into the same pipelines and
   evaluation tooling as the built-in models.

.. dropdown:: What is the methodology behind training and prediction?
   :icon: info

   OpenSTEF automates the typical ML activities around a forecast:

   1. **Data ingestion** — raw time series data is wrapped in typed dataset objects.
   2. **Feature engineering** — lag features, holiday indicators, solar irradiance
      transformations, and other energy-specific signals are added automatically.
   3. **Training** — a single training run produces a model capable of **multi-horizon
      forecasting** (one shot, many horizons).
   4. **Probabilistic prediction** — quantile regression provides uncertainty estimates
      alongside point forecasts.
   5. **Post-processing** — optional transformations are applied to the raw model output.

   See :doc:`user_guide/index` for a detailed walkthrough of the pipeline.

----

Getting Started
---------------

.. dropdown:: What is the quickest way to get a forecast running?
   :icon: light-bulb

   The fastest path is to use one of the built-in **presets**, which bundle a complete
   pipeline (preprocessing, feature engineering, model, post-processing) with sensible
   defaults. Here is a minimal example using a preset with synthetic data:

   .. code-block:: python

      import pandas as pd
      import numpy as np
      from openstef_core.datasets import VersionedTimeSeriesDataset

      # Create a simple time series (replace with your real data)
      index = pd.date_range("2024-01-01", periods=8760, freq="1h")
      load = pd.Series(np.random.rand(8760) * 100, index=index, name="load")
      df = load.to_frame()

      # Wrap in an OpenSTEF dataset
      dataset = VersionedTimeSeriesDataset(data=df)

   From here, configure a ``ForecastingModel`` with a preset and call the workflow to
   train and predict. See the :doc:`user_guide/index` and the bundled examples for a
   complete, runnable walkthrough.

.. dropdown:: Do I need a database or external infrastructure to use OpenSTEF?
   :icon: question

   No. OpenSTEF is a **Python library** — it has no mandatory dependency on a database,
   message broker, or any external service. You supply data as pandas DataFrames or
   OpenSTEF dataset objects, and the library returns forecasts in the same form.

   For model persistence, the library includes ``LocalModelStorage`` for saving and loading
   models to and from the local filesystem. You can replace this with your own storage
   backend by implementing the storage interface.

.. dropdown:: Where can I find working code examples?
   :icon: info

   The repository ships with a set of runnable examples covering common scenarios:

   - Configuring a full forecasting pipeline with preprocessing and postprocessing
   - Using presets for quick-start setups
   - Backtesting and evaluating model changes with ``openstef-beam``

   Browse them in the :doc:`examples` section of this documentation, or find the source
   files in the ``examples/`` directory of the repository.

.. dropdown:: How do I verify my installation is working correctly?
   :icon: checklist

   Run the following in a Python interpreter after installing:

   .. code-block:: python

      import openstef_models
      print(f"OpenSTEF Models version: {openstef_models.__version__}")

      # Optional: check openstef-beam if you installed it
      try:
          import openstef_beam
          print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
      except ImportError:
          print("openstef-beam not installed (this is fine if you did not install it)")

   If you see the version numbers printed without errors, your installation is working.

----

Project & Community
--------------------

.. dropdown:: Is OpenSTEF production-ready?
   :icon: question

   OpenSTEF has been used in production at Alliander (a major Dutch grid operator) for
   congestion management and load forecasting at scale. The 4.0 release represents a
   significant architectural rework — more modular, more flexible, and better suited for
   integration into diverse software landscapes.

   The ``openstef-foundational-models`` and ``openstef-compatibility`` packages are still
   marked *coming soon*, so if you depend on deep learning models or are migrating from 3.x,
   check the changelog for the latest status.

.. dropdown:: How do I contribute or report a bug?
   :icon: info

   OpenSTEF is an open-source project under the LF Energy umbrella. Contributions are
   welcome — bug reports, feature requests, documentation improvements, and code all help.

   - **Bug reports & feature requests:** open an issue on GitHub.
   - **Code contributions:** see :doc:`contribute/index` for the development setup guide,
     coding standards, and pull request process.
   - **Community discussions:** join the conversation via the LF Energy community channels
     linked from the project homepage.