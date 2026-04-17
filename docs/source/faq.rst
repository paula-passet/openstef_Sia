FAQ
===

New to OpenSTEF? This page answers the most common questions from users getting started with the library — covering what it does, how to install it, which models to use, and how to integrate it into your own project.

.. note::

   OpenSTEF is a **Python library**, not a standalone application. You import and call it from your own code, notebooks, or pipelines — just like scikit-learn or pandas.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building accurate short-term energy forecasts. It provides complete, composable pipelines covering data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing — all in one framework.

   It is **model-agnostic**: you can plug in XGBoost, LightGBM, a linear model, or your own custom estimator. Rather than shipping a single fixed model, OpenSTEF gives you the building blocks to assemble a forecasting system that fits your use case.

   OpenSTEF is developed and maintained by Alliander, a Dutch grid operator, and is used in production to generate forecasts for over 10,000 grid locations.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term means predicting energy load **hours to roughly seven days ahead**. Beyond seven days, weather forecasts lose the 15-minute resolution that solar and wind predictions require, and forecast quality degrades significantly.

   Typical applications include:

   - **Congestion management** — predicting peak load at grid points 2 days ahead so operators can act in advance
   - **Transport forecasts** — communicating planned energy usage to upstream network operators
   - **Grid loss forecasting** — estimating system losses for financial optimisation
   - **EV charging capacity estimation** — anticipating demand at charging infrastructure

.. dropdown:: Is OpenSTEF only useful for grid operators?
   :icon: question

   No. While OpenSTEF was built at a grid operator (Alliander) and its built-in domain knowledge reflects that context, the library is designed to be broadly applicable. Version 4 explicitly generalises domain-specific logic to support use cases beyond the Netherlands — including customisable holiday calendars, flexible weather feature mappings, and configurable energy pricing inputs.

   If you have a time series that is influenced by weather, time-of-day patterns, or calendar effects, OpenSTEF's feature engineering and modelling pipelines are likely a good fit.

.. dropdown:: How is OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using XGBoost directly requires you to build everything around the model yourself: feature engineering, lag creation, holiday encoding, weather feature derivation (e.g., converting solar radiation to PV generation estimates), quantile regression, model versioning, and evaluation. OpenSTEF provides all of that out of the box, specifically tuned for energy time series.

   Key things OpenSTEF adds on top of a raw ML library:

   - **Probabilistic forecasts** — multiple quantiles with uncertainty bandwidths, not just a single point prediction
   - **Energy-domain feature engineering** — lag transforms, holiday features, solar/wind-aware features, rolling aggregates
   - **Pipeline composition** — preprocessing, model, and postprocessing steps wired together cleanly
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides structured backtesting, scoring, and visualisation
   - **Model storage and versioning** — built-in MLflow integration and local storage backends

----

Installation and Requirements
------------------------------

.. dropdown:: What Python version does OpenSTEF require?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or later** (and below 4.0). Make sure your environment meets this requirement before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the meta-package, which pulls in all sub-packages:

   .. code-block:: python

      # In your terminal:
      # pip install openstef

   If you only need specific functionality, you can install individual packages:

   .. code-block:: python

      # Core forecasting functionality only
      # pip install openstef-core

      # Models (XGBoost, LightGBM, etc.)
      # pip install openstef-models

      # Backtesting, evaluation, analysis, and metrics
      # pip install openstef-beam

      # Meta-learning models
      # pip install openstef-meta

   To include optional model backends:

   .. code-block:: python

      # LightGBM support
      # pip install openstef-models[lgbm]

      # XGBoost on CPU
      # pip install openstef-models[xgb-cpu]

      # XGBoost with GPU support
      # pip install openstef-models[xgb-gpu]

.. dropdown:: What are the main dependencies?
   :icon: checklist

   The core dependencies brought in automatically include:

   - ``numpy``, ``pandas``, ``pyarrow`` — data handling
   - ``pydantic`` — configuration and type validation
   - ``joblib`` — parallelism
   - ``pvlib`` — solar position and irradiance calculations
   - ``holidays`` — calendar-aware holiday features
   - ``mlflow-skinny`` — lightweight model tracking and storage
   - ``plotly`` — interactive visualisation (via ``openstef-beam``)
   - ``scoringrules`` — probabilistic forecast scoring

   Optional model backends (LightGBM, XGBoost) are not installed by default — use the extras syntax shown above.

.. dropdown:: How do I verify my installation is working?
   :icon: checklist

   After installing, run a quick import check:

   .. code-block:: python

      import openstef_core
      import openstef_models
      import openstef_beam

      print("OpenSTEF installed successfully.")

   To go further, try generating a synthetic dataset and running a minimal pipeline — see :doc:`getting_started/quickstart` for a working example.

----

Models and Forecasting
-----------------------

.. dropdown:: Which model should I use?
   :icon: light-bulb

   OpenSTEF ships two primary gradient-boosting forecasters:

   - **XGBoost** (``XGBoostForecaster``) — handles complex nonlinear patterns well; the default choice for most energy forecasting tasks
   - **LightGBM** (``LGBMForecaster``) — similar accuracy, often faster to train; a good alternative when training time matters
   - **GBLinear** (``GBLinearForecaster``) — gradient-boosted linear model; better extrapolation behaviour outside the training distribution, and faster than tree-based models

   If you are unsure, start with XGBoost or LightGBM. Use the ``openstef-beam`` backtesting tools to compare them on your own data before committing to one.

.. dropdown:: Does OpenSTEF produce uncertainty estimates, or just point forecasts?
   :icon: question

   OpenSTEF is built around **probabilistic forecasting**. Every model produces forecasts at multiple quantiles (e.g., p10, p50, p90), giving you an uncertainty bandwidth around the central prediction rather than a single number.

   This is especially important for congestion management, where knowing whether a peak is *likely* or *certain* changes the operational response.

   You specify which quantiles you want at configuration time:

   .. code-block:: python

      from openstef_models.presets import ForecastingWorkflowConfig

      config = ForecastingWorkflowConfig(
          model_id="my_substation",
          quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],
          horizons=[1, 2, 4, 8, 24, 48],  # hours ahead
          # ... other settings
      )

.. dropdown:: What features does OpenSTEF engineer automatically?
   :icon: question

   OpenSTEF's built-in transforms cover the most important feature families for energy time series:

   - **Lag features** — past load values at horizon-aware offsets (via ``LagsAdder``)
   - **Holiday features** — country-specific public holidays encoded as binary indicators (via ``HolidayFeatureAdder``)
   - **Weather-derived features** — solar radiation to PV generation estimates, wind speed at multiple heights
   - **Rolling aggregates** — mean, median, min, max over configurable windows
   - **Time-domain features** — hour of day, day of week, month, and similar cyclical encodings

   You can compose these transforms into a ``FeaturePipeline`` and add your own custom transforms alongside them.

.. dropdown:: How far ahead can OpenSTEF forecast?
   :icon: question

   The practical upper limit is around **seven days (168 hours)**. Beyond that, weather forecast inputs lose the temporal resolution needed for reliable solar and wind-influenced predictions, and accuracy degrades substantially.

   Within that window, you configure the specific forecast horizons you need. A typical setup might request forecasts at 1, 2, 4, 8, 24, and 48 hours ahead simultaneously.

----

Using the Library
-----------------

.. dropdown:: Do I need MLflow to use OpenSTEF?
   :icon: question

   No. MLflow integration is optional. OpenSTEF also ships a ``LocalModelStorage`` backend that saves models to the local filesystem with no external services required. This is the easiest way to get started:

   .. code-block:: python

      from openstef_models.models.forecasting_model import ForecastingModel
      from openstef_core.datasets import TimeSeriesDataset

      # LocalModelStorage requires no external services
      # See the configuring_model_pipeline example for full setup

   When you are ready to move to a more production-oriented setup, you can swap in ``MLFlowStorage`` without changing the rest of your pipeline.

.. dropdown:: Can I use my own custom model with OpenSTEF?
   :icon: light-bulb

   Yes. OpenSTEF is designed for extensibility. Custom models, transforms, and metrics can be added without modifying library code — you implement the relevant interface and pass your object into the pipeline. The ``Forecaster`` base class defines the contract your model needs to satisfy.

   Similarly, custom preprocessing steps can be written as ``TimeSeriesTransform`` subclasses and inserted into a ``FeaturePipeline`` alongside the built-in transforms.

.. dropdown:: How do I evaluate forecast quality?
   :icon: question

   The ``openstef-beam`` package (Backtesting, Evaluation, Analysis and Metrics) is the right tool for this. It provides structured backtesting over historical data, a suite of probabilistic scoring rules (including CRPS), and built-in visualisation via Plotly.

   .. code-block:: python

      from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

      # ForecastTimeSeriesPlotter produces interactive Plotly figures
      # showing actuals vs. forecast quantiles over time

   To benchmark against baselines or compare multiple model configurations, see :doc:`guides/backtesting`.

.. dropdown:: Where can I find complete working examples?
   :icon: light-bulb

   The best starting points are:

   - :doc:`getting_started/quickstart` — minimal end-to-end example
   - :doc:`getting_started/first_forecast` — step-by-step first forecast walkthrough
   - The ``examples/`` directory in the repository contains runnable scripts including ``configuring_model_pipeline_example.py`` and ``forecasting_preset_example.py``

   All examples use ``openstef_core.testing.create_synthetic_forecasting_dataset`` to generate data, so you can run them immediately without needing a real dataset.

----

.. note::

   Have a question that isn't answered here? Open a discussion on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_ or join the community Slack channel.