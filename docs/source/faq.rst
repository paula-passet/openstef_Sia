FAQ
===

This FAQ covers the most common questions from new users of OpenSTEF — the open-source Python library
for short-term energy forecasting. Whether you're evaluating the library, setting it up for the first
time, or trying to understand how it fits into your workflow, you should find answers here.

.. contents:: Questions at a glance
   :local:
   :depth: 1

----

General
-------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building
   accurate short-term energy load forecasts. It provides complete, production-ready pipelines for
   data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation,
   and post-processing — all in one coherent framework.

   OpenSTEF is developed and maintained by Alliander, a Dutch grid operator, and released under the
   LF Energy umbrella. It is used in production to manage grid congestion across thousands of grid
   points.

   See :doc:`getting_started` for a hands-on introduction.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load **hours to days ahead** — typically up to
   48 hours into the future. This time horizon is particularly important for operational decisions
   such as congestion management, EV charging capacity planning, transport forecasts, and grid
   loss prediction.

   This is distinct from medium-term (weeks/months) or long-term (years) forecasting, which serve
   different planning purposes and require different modelling approaches.

.. dropdown:: Is OpenSTEF just a model, or something more?
   :icon: question

   OpenSTEF is much more than a single model. It is a **model-agnostic machine learning framework**
   that wraps the full forecasting lifecycle:

   - **Data preprocessing** — cleaning, validation, and gap handling
   - **Feature engineering** — built-in energy-domain features such as solar radiation estimates,
     holiday calendars, lag transforms, and rolling statistics
   - **Model training** — pluggable support for XGBoost, LightGBM, and custom models
   - **Probabilistic forecasting** — quantile predictions with uncertainty bands (e.g. P10–P90),
     not just a single point estimate
   - **Post-processing** — confidence interval calibration using isotonic regression
   - **Evaluation and backtesting** — via the ``openstef-beam`` BEAM package

   You bring your data; OpenSTEF handles the rest.

.. dropdown:: Who is OpenSTEF built for?
   :icon: question

   OpenSTEF is aimed at:

   - **Data scientists and ML engineers** at grid operators or energy companies who need a
     battle-tested forecasting framework rather than building pipelines from scratch
   - **Researchers** who want a reproducible baseline and evaluation harness for energy forecasting
   - **Developers** integrating short-term load forecasts into operational systems

   Because OpenSTEF is a library (not an application), you integrate it into your own code and
   infrastructure — you remain in full control of data ingestion, scheduling, and storage.

----

Installation & Requirements
----------------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF requires:

   - **Python** >= 3.12, < 4.0
   - A standard pip-compatible environment (virtualenv, conda, etc.)

   No special hardware is required for CPU-based models. GPU support is available as an optional
   extra for XGBoost (see below).

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest way is to install the meta-package, which pulls in all sub-packages:

   .. code-block:: bash

      pip install openstef

   This installs four packages:

   - ``openstef-core`` — core data structures, datasets, and utilities
   - ``openstef-models`` — forecasting models (XGBoost, LightGBM, etc.)
   - ``openstef-beam`` — Backtesting, Evaluation, Analysis and Metrics (BEAM)
   - ``openstef-meta`` — meta-models that combine multiple forecasters

   If you only need specific functionality, install individual packages:

   .. code-block:: bash

      # Just the core data structures
      pip install openstef-core

      # Core + models only (no evaluation tooling)
      pip install openstef-models

      # Evaluation and backtesting tools
      pip install openstef-beam

.. dropdown:: How do I install support for XGBoost or LightGBM?
   :icon: question

   Model backends are available as optional extras on ``openstef-models``:

   .. code-block:: bash

      # LightGBM support
      pip install "openstef-models[lgbm]"

      # XGBoost (CPU)
      pip install "openstef-models[xgb-cpu]"

      # XGBoost (GPU)
      pip install "openstef-models[xgb-gpu]"

      # Everything at once
      pip install "openstef[lgbm,xgb-cpu]"

   .. note::

      The ``openstef-beam`` package also has an ``[all]`` extra that adds S3 support and
      baseline model comparisons:

      .. code-block:: bash

         pip install "openstef-beam[all]"

.. dropdown:: How do I verify my installation?
   :icon: checklist

   After installing, you can confirm everything is in order by importing the top-level packages:

   .. code-block:: python

      import openstef_core
      import openstef_models
      import openstef_beam

      print("OpenSTEF installed successfully!")

----

Models & Forecasting
---------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several built-in models, all accessible through the same pipeline interface:

   - **XGBoost (gbtree)** — gradient boosting trees; handles complex nonlinear patterns well
   - **GBLinear** — gradient boosted linear model; better extrapolation behaviour and faster to train
   - **LightGBM** — efficient gradient boosting with leaf-wise tree growth; good for large datasets

   All models support **quantile regression**, meaning they produce probabilistic forecasts
   (e.g. P10, P50, P90) rather than a single point prediction.

   You can also implement a custom forecaster by subclassing ``Forecaster`` from
   ``openstef_models.models.forecasting.forecaster``.

.. dropdown:: What does "probabilistic forecasting" mean in practice?
   :icon: question

   Instead of predicting a single value, OpenSTEF produces a **distribution of outcomes** expressed
   as quantiles. For example, a forecast might include:

   - ``quantile_P10`` — lower bound (10th percentile): load will exceed this value 90% of the time
   - ``quantile_P50`` — median prediction: the most likely outcome
   - ``quantile_P90`` — upper bound (90th percentile): load will be below this value 90% of the time

   This is critical for risk-aware decisions in grid operations, where knowing the uncertainty of a
   forecast is just as important as the forecast itself.

   .. code-block:: python

      from openstef_core.datasets import ForecastDataset

      # After running workflow.predict(forecast_dataset):
      print(forecast.quantiles)
      # e.g. [0.1, 0.5, 0.9]

      print(forecast.data[["quantile_P10", "quantile_P50", "quantile_P90"]].head())

   **[VISUALIZATION: Example forecast plot showing median line with P10–P90 shaded confidence band over a 48-hour horizon]**

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   At a minimum, OpenSTEF expects a **time-indexed pandas DataFrame** containing:

   - A **load** column (the target variable — energy consumption or generation in MW)
   - **Weather features** such as temperature, solar radiation, wind speed, humidity, and pressure
     (column names are configurable)
   - Optionally, additional features like day-ahead electricity prices

   Data is wrapped in OpenSTEF's ``TimeSeriesDataset`` or ``ForecastInputDataset`` structures,
   which handle validation and enforce correct formatting before it reaches the model.

   .. code-block:: python

      from openstef_core.testing import create_synthetic_forecasting_dataset

      # Quickly generate a synthetic dataset for experimentation
      dataset = create_synthetic_forecasting_dataset()
      print(dataset.data.head())

   .. note::

      OpenSTEF does **not** fetch weather data for you — you are responsible for supplying
      weather forecasts alongside your load measurements. The library provides the feature
      engineering logic once the raw data is available.

.. dropdown:: How does OpenSTEF handle missing data?
   :icon: question

   OpenSTEF's preprocessing pipeline includes built-in gap handling. Models are designed to
   return ``None`` gracefully when input data is insufficiently complete, rather than producing
   unreliable forecasts. The ``InsufficientlyCompleteError`` exception is raised in cases where
   the data quality falls below a configurable threshold, allowing your application to handle
   the situation explicitly.

----

Architecture & Design
----------------------

.. dropdown:: What are the main sub-packages and what does each do?
   :icon: info

   OpenSTEF is split into focused sub-packages:

   - **openstef-core** — foundational building blocks: dataset classes (``ForecastDataset``,
     ``TimeSeriesDataset``), base model interfaces, mixins, type definitions, and shared utilities.
     Everything else depends on this.

   - **openstef-models** — concrete forecasting models (XGBoost, LightGBM, GBLinear), feature
     engineering transforms, preprocessing/postprocessing pipelines, and the ``ForecastingModel``
     class that ties them together.

   - **openstef-beam** — the **B**\ acktesting, **E**\ valuation, **A**\ nalysis and **M**\ etrics
     toolkit. Contains ``EvaluationPipeline``, backtesting workflows, scoring rules, and
     ``ForecastTimeSeriesPlotter`` for interactive visualisations.

   - **openstef-meta** — meta-models that combine multiple base forecasters (e.g. via an LightGBM
     combiner) to improve robustness.

   **[DIAGRAM: Package dependency graph showing openstef-core at the base, openstef-models and openstef-beam depending on it, and openstef-meta depending on both openstef-models and openstef-beam]**

.. dropdown:: How does a typical training and forecasting workflow look?
   :icon: info

   A standard OpenSTEF workflow follows these steps:

   **[DIAGRAM: Flowchart showing: Raw Data → TimeSeriesDataset → FeaturePipeline (holidays, lags, rolling stats) → ForecastingModel.fit() → LocalModelStorage → ForecastingModel.predict() → ForecastDataset (quantile_P10/P50/P90) → EvaluationPipeline]**

   In code, this looks like:

   .. code-block:: python

      import logging
      from pathlib import Path
      from openstef_core.testing import create_synthetic_forecasting_dataset
      from openstef_models.presets import ForecastingWorkflowConfig
      from openstef_models.workflows import CustomForecastingWorkflow
      from openstef_models.storage import LocalModelStorage

      logging.basicConfig(level=logging.INFO)

      # 1. Load or create your dataset
      dataset = create_synthetic_forecasting_dataset()

      # 2. Configure the workflow
      config = ForecastingWorkflowConfig(
          model_id="my_first_model",
          model="lgbm",
          horizons=[1, 2, 4, 8, 24, 48],   # lead times in hours
          quantiles=[0.1, 0.5, 0.9],
      )

      # 3. Set up model storage and workflow
      storage = LocalModelStorage(path=Path("./models"))
      workflow = CustomForecastingWorkflow(config=config, storage=storage)

      # 4. Train
      workflow.fit(dataset)

      # 5. Predict
      forecast = workflow.predict(dataset)
      print(forecast.data[["quantile_P10", "quantile_P50", "quantile_P90"]].tail())

.. dropdown:: Can I use my own custom model with OpenSTEF?
   :icon: question

   Yes. OpenSTEF is designed to be extensible. You can plug in a custom forecaster by subclassing
   the ``Forecaster`` base class from ``openstef_models.models.forecasting.forecaster`` and
   implementing the ``fit()`` and ``predict()`` methods. Your model will then work seamlessly with
   the rest of the pipeline — feature engineering, post-processing, evaluation, and backtesting
   all remain unchanged.

   .. code-block:: python

      from openstef_models.models.forecasting.forecaster import Forecaster
      from openstef_core.types import Quantile
      import pandas as pd

      class MyCustomForecaster(Forecaster):
          """A minimal custom forecaster skeleton."""

          @property
          def quantiles(self) -> list[Quantile]:
              return [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

          def fit(self, data) -> None:
              # Your training logic here
              ...

          def predict(self, data) -> pd.DataFrame | None:
              # Your prediction logic here — return None if data is insufficient
              ...

----

Evaluation & Backtesting
-------------------------

.. dropdown:: How do I evaluate forecast quality?
   :icon: question

   The ``openstef-beam`` package provides ``EvaluationPipeline`` for systematic forecast
   evaluation. It supports multiple scoring metrics including R² and proper scoring rules
   for probabilistic forecasts (via the ``scoringrules`` dependency).

   .. code-block:: python

      from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig

      eval_config = EvaluationConfig(
          metrics=["r2", "crps"],   # continuous ranked probability score
      )
      pipeline = EvaluationPipeline(config=eval_config)
      results = pipeline.evaluate(forecast=forecast, observations=observations)
      print(results)

.. dropdown:: How do I visualise forecast results?
   :icon: question

   OpenSTEF includes ``ForecastTimeSeriesPlotter`` in ``openstef_beam.analysis.plots``, which
   produces interactive Plotly charts showing the forecast median alongside shaded confidence
   intervals and actual measurements — no external plotting setup required.

   .. code-block:: python

      from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

      fig = (
          ForecastTimeSeriesPlotter()
          .add_measurements(measurements=forecast_dataset.data["load"])
          .add_model(
              model_name="LightGBM",
              forecast=forecast.median_series,
              quantiles=forecast.quantiles_data,
          )
          .plot()
      )
      fig.show()

   **[VISUALIZATION: Interactive Plotly forecast chart with actual load as a solid line, P50 forecast as a dashed line, and P10–P90 shaded band over a 48-hour window]**

----

Contributing & Community
-------------------------

.. dropdown:: Is OpenSTEF open source? Can I contribute?
   :icon: info

   Yes — OpenSTEF is released under the **Mozilla Public License 2.0 (MPL-2.0)** and is hosted
   under the LF Energy Foundation. Contributions are welcome: bug reports, feature requests, and
   pull requests can all be submitted via the project's GitHub repository.

   See :doc:`contributing` for guidelines on how to get involved.

.. dropdown:: Where can I get help if I'm stuck?
   :icon: light-bulb

   Several resources are available:

   - **This documentation** — start with :doc:`getting_started` for a guided introduction
   - **GitHub Issues** — for bug reports and feature requests
   - **LF Energy Slack** — the ``#openstef`` channel for community discussion
   - **Example notebooks** — runnable examples covering common use cases are included in the
     repository under ``examples/``

   If you encounter unexpected behaviour, check that your Python version is >= 3.12 and that
   optional model extras (``[lgbm]``, ``[xgb-cpu]``) are installed for the model type you
   are using.