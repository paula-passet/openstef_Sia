FAQ
===

This FAQ answers the most common questions from new OpenSTEF users — from understanding what the library does, to installing it, choosing models, and running your first forecast. If you are looking for step-by-step guidance, see :doc:`getting_started`.

.. note::
   Can't find your answer here? Join the community on Slack or open a discussion on GitHub.

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for predicting energy load hours to days ahead. It provides complete machine learning pipelines covering data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing — so you are not starting from scratch.

   It is model-agnostic by design: the same pipeline works with XGBoost, LightGBM, or any custom model you plug in. Rather than producing a single-point prediction, OpenSTEF generates **probabilistic forecasts** with uncertainty bandwidths, which are more useful for operational decisions.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term means predicting load **hours to roughly two days ahead**. This horizon is long enough to act on — for example, calling industrial customers to reduce consumption before a grid congestion event — but short enough that weather forecasts and recent load patterns are still reliable predictors.

   Typical use cases include:

   - Congestion management at grid substations
   - Transport capacity forecasting
   - EV charging capacity estimation
   - Grid loss prediction
   - Solar park and wind park output forecasting

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using a gradient boosting library directly leaves a lot of work to you: feature engineering, handling missing data, time-aware train/test splits, quantile regression for uncertainty, model evaluation, and reproducibility. OpenSTEF handles all of that.

   Key differentiators:

   - **Energy-domain feature engineering** built in — for example, estimating PV generation from solar radiation data using ``pvlib``, and encoding calendar and weather features automatically.
   - **Probabilistic output** — forecasts include configurable quantile intervals, not just a mean prediction.
   - **Production-tested** — OpenSTEF runs in production at Alliander, generating forecasts for over 10,000 grid locations.
   - **Backtesting and benchmarking** — the ``openstef-beam`` package provides structured backtesting pipelines so you can validate accuracy before deploying.

.. dropdown:: Who built OpenSTEF and who uses it?
   :icon: info

   OpenSTEF was created by data science engineers at **Alliander**, a Dutch distribution system operator. It is open-source under the Mozilla Public License 2.0 and is a project under the LF Energy foundation. Alliander uses it in production for congestion management across thousands of grid points.

Installation & Requirements
---------------------------

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (``>=3.12,<4.0``). Make sure your environment matches before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the meta-package, which pulls in all sub-packages:

   .. code-block:: python

      # In your terminal:
      # pip install openstef

   This installs ``openstef-beam``, ``openstef-core``, ``openstef-meta``, and ``openstef-models``.

   If you only need specific functionality, install individual packages:

   .. code-block:: python

      # Core data structures and utilities only
      # pip install openstef-core

      # Backtesting, evaluation, and metrics only
      # pip install openstef-beam

      # Forecasting models (LightGBM, XGBoost, etc.)
      # pip install openstef-models

   Verify the installation:

   .. code-block:: python

      import openstef_beam
      import openstef_core

      print(openstef_beam.__version__)
      print(openstef_core.__version__)

.. dropdown:: What are the main dependencies?
   :icon: info

   The core dependencies are:

   - ``numpy``, ``pandas``, ``pyarrow`` — data handling
   - ``pydantic`` — configuration and data validation
   - ``joblib`` — parallelism
   - ``pvlib`` — solar irradiance to PV generation conversion
   - ``holidays`` — calendar feature engineering
   - ``mlflow-skinny`` — experiment tracking
   - ``plotly`` — interactive evaluation plots (via ``openstef-beam``)
   - ``scoringrules`` — probabilistic forecast scoring

   Model backends are optional extras:

   .. code-block:: bash

      pip install "openstef-models[lgbm]"        # LightGBM
      pip install "openstef-models[xgb-cpu]"     # XGBoost (CPU)
      pip install "openstef-models[xgb-gpu]"     # XGBoost (GPU)

.. dropdown:: Can I install OpenSTEF in a conda environment?
   :icon: question

   Yes. Create a conda environment with Python 3.12, then use ``pip`` to install OpenSTEF inside it:

   .. code-block:: bash

      conda create -n openstef python=3.12
      conda activate openstef
      pip install openstef

   There are no conda-specific packages for OpenSTEF; ``pip`` is the supported installation method.

Models & Forecasting
--------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with gradient boosting models as the primary backends:

   - **LightGBM** (``LGBMForecaster``) — fast training, good default choice for most energy signals
   - **LightGBM Linear** (``LGBMLinearForecaster``) — LightGBM with a linear tree structure, useful when relationships are more linear
   - **XGBoost** (``XGBoostForecaster``) — well-established alternative, supports GPU acceleration

   All models produce **multi-quantile probabilistic forecasts** using quantile regression, so you get an uncertainty bandwidth alongside the median prediction.

   The framework is model-agnostic: you can integrate a custom model by implementing the ``Forecaster`` interface from ``openstef_models``.

.. dropdown:: What is a probabilistic forecast and why does it matter?
   :icon: light-bulb

   A probabilistic forecast gives you a **range of likely outcomes** rather than a single number. OpenSTEF expresses this as quantile predictions — for example, the 10th, 50th, and 90th percentiles of expected load.

   This matters in practice because:

   - Grid operators need to know the *worst-case* load, not just the expected load, to avoid equipment damage.
   - Congestion management decisions depend on how confident the forecast is — a wide uncertainty band may trigger an earlier customer call.
   - Probabilistic scores (like the continuous ranked probability score, CRPS) give a more complete picture of model quality than mean absolute error alone.

.. dropdown:: How do I choose between LightGBM and XGBoost?
   :icon: question

   For most energy forecasting tasks, **LightGBM is a good starting point** — it trains faster and tends to perform well out of the box on tabular time series data. XGBoost is a solid alternative if you have GPU hardware available or prefer its regularisation behaviour.

   The best approach is to benchmark both on your specific signals using ``openstef-beam``'s backtesting pipeline. See :doc:`backtesting` for how to run a structured comparison.

.. dropdown:: Can I use my own custom model?
   :icon: question

   Yes. OpenSTEF's pipeline is model-agnostic. Implement the ``Forecaster`` base class from ``openstef_models`` and pass your model into the pipeline:

   .. code-block:: python

      from openstef_models.models.forecasting.forecaster import Forecaster

      class MyCustomForecaster(Forecaster):
          # Implement required methods: fit, predict, etc.
          ...

   Your model will then benefit from all of OpenSTEF's feature engineering, preprocessing, and evaluation tooling automatically.

Data & Feature Engineering
--------------------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   OpenSTEF works with **time series data** represented as pandas DataFrames with a datetime index. At minimum you need a target load signal (e.g., MW measured at a grid point) and timestamps. Weather data (temperature, wind speed, solar irradiance) significantly improves accuracy and is used automatically when provided.

   Data is structured using ``openstef-core`` dataset classes such as ``ForecastDataset`` and ``ForecastInputDataset``, which validate the shape and types of your inputs.

   .. code-block:: python

      from openstef_core.datasets import ForecastInputDataset

      dataset = ForecastInputDataset(
          load=my_load_dataframe,
          weather=my_weather_dataframe,
      )

.. dropdown:: Does OpenSTEF handle missing data automatically?
   :icon: question

   Yes. The preprocessing pipeline includes missing value handling as a built-in step. You do not need to impute data manually before passing it to the pipeline. However, large gaps in your training data will still affect model quality — it is worth inspecting your data for systematic outages or sensor failures before training.

.. dropdown:: How does OpenSTEF incorporate solar generation?
   :icon: light-bulb

   OpenSTEF uses ``pvlib`` under the hood to convert solar irradiance forecasts into estimated PV generation. This is part of the built-in feature engineering — if you provide irradiance data (global horizontal irradiance, for example), the library automatically derives a PV generation feature. This domain knowledge is one of the reasons OpenSTEF outperforms generic ML pipelines on grids with significant solar penetration.

Configuration & Setup
---------------------

.. dropdown:: How is OpenSTEF configured?
   :icon: checklist

   Configuration is handled through Pydantic models defined in ``openstef-core``. You can define configuration in Python or load it from a YAML file:

   .. code-block:: python

      from openstef_core.base_model import BaseConfig
      from pathlib import Path

      # Load from a YAML file
      config = BaseConfig.read_yaml(Path("config.yaml"))

      # Or write a config to YAML for later reuse
      config.write_yaml(Path("config.yaml"))

   This makes it straightforward to version-control your experiment configurations alongside your code.

.. dropdown:: Does OpenSTEF integrate with MLflow?
   :icon: info

   Yes. ``openstef-models`` depends on ``mlflow-skinny`` for experiment tracking. Training runs, hyperparameters, and metrics are logged automatically. You can point MLflow at a local directory or a remote tracking server by setting the standard ``MLFLOW_TRACKING_URI`` environment variable before running your pipeline.

.. dropdown:: Is OpenSTEF ready for production use?
   :icon: info

   The V4 series is currently in **alpha**. It has feature parity with the stable V3 release and is already running in production at Alliander for over 10,000 grid locations, but the API may still change before a stable release. For new projects, V4 is recommended. If you need a fully stable API today, check the V3 branch.

   .. note::
      Follow the `GitHub repository <https://github.com/OpenSTEF/openstef>`_ and the community Slack for release announcements.

Contributing & Community
------------------------

.. dropdown:: How do I report a bug or request a feature?
   :icon: alert

   Open an issue on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_. The backlog is public and includes stories, tasks, and milestones. Issues labelled **"good first issue"** are a good entry point if you want to contribute code.

.. dropdown:: How do I contribute to OpenSTEF?
   :icon: checklist

   The project uses ``uv`` for dependency management and ``ruff`` for linting. The development workflow is:

   1. Fork the repository and create a branch.
   2. Install the development dependencies with ``uv sync``.
   3. Run the test suite and type checker (``mypy``) before submitting a pull request.
   4. Join the bi-weekly community meetings or co-coding sessions to discuss larger changes before implementing them.

   See the contributing guide in the repository root for full details.