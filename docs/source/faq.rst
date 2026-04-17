FAQ
===

This FAQ answers the most common questions from new OpenSTEF users — covering what the library does,
how to install it, which models to choose, and how to get your first forecast running. If you have a
question that isn't answered here, check the :doc:`getting_started` guide or open a discussion on GitHub.

----

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building
   accurate short-term energy forecasts. It provides complete, production-ready pipelines covering
   data preprocessing, feature engineering, model training, forecasting, evaluation, and
   post-processing — all in one cohesive framework.

   OpenSTEF is model-agnostic by design. Rather than locking you into a single algorithm, it gives
   you a consistent API across multiple gradient-boosting and linear backends so you can swap models
   without rewriting your pipeline.

   The library is developed and maintained by Alliander, a Dutch grid operator, and is part of the
   LF Energy foundation. It is used in production to generate forecasts for more than 10,000 grid
   locations.

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load or generation **hours to days ahead** — typically
   up to 48 hours into the future. This time horizon is long enough to be operationally useful (e.g.,
   scheduling grid interventions or EV charging capacity) but short enough that weather-driven features
   remain highly predictive.

   Common use cases include:

   - Congestion management on electricity distribution grids
   - Transport capacity forecasting
   - EV charging capacity estimation
   - Grid loss prediction
   - Solar park and wind park output forecasting

.. dropdown:: Is OpenSTEF only for grid operators?
   :icon: question

   No. While OpenSTEF was built to solve real problems at Alliander, the library is general-purpose.
   Any organisation that needs to forecast time-series energy data — utilities, aggregators, research
   institutions, or industrial consumers — can use it. The built-in feature engineering includes
   domain knowledge such as solar radiation to PV generation estimates, but these are optional
   components you can include or omit as needed.

.. dropdown:: How is OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using XGBoost or LightGBM directly gives you a model. OpenSTEF gives you a **forecasting system**.
   The key differences are:

   - **Probabilistic output** — OpenSTEF produces quantile forecasts (e.g., P10, P50, P90) out of
     the box, not just a single point prediction. This lets downstream systems reason about
     uncertainty.
   - **Energy-domain feature engineering** — holiday calendars, lag transforms, solar radiation
     features, and more are built in and composable via ``FeaturePipeline``.
   - **End-to-end pipelines** — training, prediction, model versioning, and backtesting all follow
     the same workflow pattern, reducing the glue code you have to write.
   - **Model storage and versioning** — built-in integrations with MLflow and local storage mean
     your trained models are reproducible and deployable without extra infrastructure.

----

Installation and Requirements
------------------------------

.. dropdown:: What Python version does OpenSTEF require?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (and below 4.0). If you are on an older Python version,
   you will need to upgrade before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   The simplest way is to install the meta-package, which pulls in all sub-packages:

   .. code-block:: python

      # From your terminal:
      # pip install openstef

   This installs ``openstef-core``, ``openstef-models``, ``openstef-beam``, and ``openstef-meta``
   in one step.

   If you only need specific functionality, you can install individual packages:

   .. code-block:: python

      # Core data structures and utilities only
      # pip install openstef-core

      # Models (XGBoost, LightGBM, etc.)
      # pip install openstef-models

      # Backtesting, Evaluation, Analysis and Metrics
      # pip install openstef-beam

   To enable optional model backends, use extras:

   .. code-block:: python

      # LightGBM support
      # pip install openstef-models[lgbm]

      # XGBoost (CPU)
      # pip install openstef-models[xgb-cpu]

      # XGBoost (GPU)
      # pip install openstef-models[xgb-gpu]

.. dropdown:: How do I verify my installation?
   :icon: checklist

   After installing, run the following in a Python session to confirm everything is importable:

   .. code-block:: python

      import openstef_core
      import openstef_models
      import openstef_beam

      print("OpenSTEF installed successfully!")

   If any import raises a ``ModuleNotFoundError``, double-check that you installed into the correct
   virtual environment and that your Python version meets the ``>=3.12`` requirement.

.. dropdown:: What are the key runtime dependencies?
   :icon: info

   The main dependencies brought in automatically are:

   - **numpy / pandas / pyarrow** — core data handling
   - **pydantic** — configuration and data validation
   - **pvlib** — solar irradiance and PV generation modelling
   - **holidays** — public holiday calendars for feature engineering
   - **mlflow-skinny** — lightweight MLflow client for model tracking
   - **plotly** — interactive visualisation (via ``openstef-beam``)
   - **scoringrules** — probabilistic forecast scoring metrics

   LightGBM and XGBoost are **optional** and installed via extras (see above) so you only pull in
   the backends you actually use.

----

Models and Forecasting
-----------------------

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships several gradient-boosting and linear models, all implementing the same
   ``Forecaster`` interface for probabilistic (multi-quantile) output:

   - **LGBMForecaster** — LightGBM gradient boosting trees (requires ``openstef-models[lgbm]``)
   - **LGBMLinearForecaster** — LightGBM with linear leaves, useful when the relationship between
     features and target is partially linear
   - **XGBoostForecaster** — XGBoost gradient boosting trees (requires ``openstef-models[xgb-cpu]``
     or ``openstef-models[xgb-gpu]``)
   - **GBLinearForecaster** — XGBoost with a linear booster (``gblinear``), a good baseline for
     well-behaved signals

   All models support SHAP-based feature contribution analysis via the ``predict_contributions``
   method, so you can always explain what is driving a forecast.

.. dropdown:: Which model should I start with?
   :icon: light-bulb

   For most energy time-series problems, **LGBMForecaster** is a solid default — it trains quickly,
   handles missing values gracefully, and tends to generalise well on tabular data. If you want a
   simpler, more interpretable baseline first, try **GBLinearForecaster**.

   The ``create_forecasting_workflow`` helper lets you switch models by changing a single string,
   so it is easy to compare:

   .. code-block:: python

      from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
      from openstef_core.types import LeadTime, Q

      # Try "lgbm", "lgbmlinear", "xgb", or "gblinear"
      config = ForecastingWorkflowConfig(
          model_id="my_forecast_v1",
          model="lgbm",
          horizons=[LeadTime.from_string("PT36H")],
          quantiles=[Q(0.1), Q(0.5), Q(0.9)],
      )
      workflow = create_forecasting_workflow(config)

.. dropdown:: What are quantile forecasts and why does OpenSTEF use them?
   :icon: question

   A quantile forecast gives you a **range of plausible outcomes** rather than a single number.
   For example, requesting quantiles ``[0.1, 0.5, 0.9]`` gives you:

   - **P10** — the load will exceed this value 90 % of the time (lower bound)
   - **P50** — the median forecast (best single-point estimate)
   - **P90** — the load will exceed this value only 10 % of the time (upper bound)

   This matters in grid operations because the cost of under-forecasting (unexpected congestion)
   is often very different from the cost of over-forecasting. Quantile forecasts let operators
   choose a risk-appropriate operating point rather than being forced to act on a single number.

   All OpenSTEF models produce quantile forecasts natively using multi-quantile regression — no
   post-hoc conformal prediction or bootstrapping required.

.. dropdown:: Can I bring my own custom model?
   :icon: question

   Yes. Any model that implements the ``Forecaster`` base class from ``openstef_core`` can be
   plugged into the standard pipeline. The interface requires ``fit``, ``predict``, and
   ``predict_contributions`` methods, and your hyperparameters should be declared as a
   ``HyperParams`` subclass so they integrate with the configuration system.

   See :doc:`guides/custom_models` for a step-by-step walkthrough.

----

Getting Started
---------------

.. dropdown:: How do I run my first forecast?
   :icon: light-bulb

   The fastest path to a working forecast uses ``create_synthetic_forecasting_dataset`` to generate
   test data and ``create_forecasting_workflow`` to wire up the full pipeline:

   .. code-block:: python

      import logging
      from datetime import timedelta
      from pathlib import Path

      from openstef_core.testing import create_synthetic_forecasting_dataset
      from openstef_core.types import LeadTime, Q
      from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
      from openstef_models.integrations.mlflow import MLFlowStorage

      logging.basicConfig(level=logging.INFO)

      # 1. Create 90 days of synthetic training data
      dataset = create_synthetic_forecasting_dataset(
          length=timedelta(days=90),
          wind_influence=-10.0,
          temp_influence=5.0,
          radiation_influence=-7.0,
          stochastic_influence=2.0,
          sample_interval=timedelta(hours=1),
      )

      # 2. Configure and build the workflow
      workflow = create_forecasting_workflow(
          config=ForecastingWorkflowConfig(
              model_id="my_first_forecast",
              model="lgbm",
              horizons=[LeadTime.from_string("PT36H")],
              quantiles=[Q(0.1), Q(0.5), Q(0.9)],
              mlflow_storage=MLFlowStorage(
                  tracking_uri="./mlflow_tracking",
                  local_artifacts_path=Path("./mlflow_artifacts"),
              ),
          )
      )

      # 3. Train
      result = workflow.fit(dataset)

      # 4. Predict
      forecast = workflow.predict(dataset)

   From here you can swap in real data, adjust quantiles, or change the model string — the rest of
   the pipeline stays the same.

.. dropdown:: What data format does OpenSTEF expect?
   :icon: question

   OpenSTEF works with ``TimeSeriesDataset`` and ``ForecastInputDataset`` objects defined in
   ``openstef_core``. These wrap pandas DataFrames with a consistent time-indexed structure.
   The ``create_synthetic_forecasting_dataset`` helper is a good reference for the expected shape
   and column conventions when you are preparing real data for the first time.

   .. note::

      [DIAGRAM: Illustration of the TimeSeriesDataset structure — a time-indexed DataFrame with
      target load column and optional weather/contextual feature columns.]

.. dropdown:: Where are trained models stored?
   :icon: question

   OpenSTEF supports two storage backends out of the box:

   - **LocalModelStorage** — saves model artefacts to a local directory. Useful for development
     and single-machine deployments.
   - **MLFlowStorage** — integrates with MLflow for experiment tracking, model versioning, and
     artefact management. Recommended for production use.

   Both implement the same storage interface, so switching between them requires only a
   configuration change — no pipeline code changes needed.

.. dropdown:: Does OpenSTEF include tools for evaluating forecast quality?
   :icon: question

   Yes. The ``openstef-beam`` package (Backtesting, Evaluation, Analysis and Metrics) provides:

   - **Backtesting pipelines** — walk-forward validation over historical data
   - **Scoring rules** — proper scoring rules for probabilistic forecasts (via ``scoringrules``)
   - **Visualisation** — ``ForecastTimeSeriesPlotter`` for interactive Plotly charts of forecasts
     versus actuals

   .. code-block:: python

      from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

      plotter = ForecastTimeSeriesPlotter()
      fig = plotter.plot(forecast)
      fig.show()

   See :doc:`guides/backtesting` for a full backtesting walkthrough.

----

.. note::

   Something missing? If your question isn't answered here, please open a GitHub Discussion or
   check the full :doc:`api_reference` for detailed interface documentation.