FAQ
===

This page answers the most common questions from new users of OpenSTEF. Whether you are evaluating the library, setting it up for the first time, or trying to understand how it fits into your workflow, you should find a clear answer here. For deeper dives, each answer links to the relevant documentation.

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for building and running accurate short-term load forecasts in the power grid domain. It is a **framework**, not a single model — it provides complete pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing.

   Short-term forecasting means predicting energy load hours to days ahead. Typical use cases include congestion management, transport forecasts, EV charging capacity estimation, and grid loss prediction.

   See :doc:`getting_started` for a hands-on introduction.

.. dropdown:: What does "short-term" mean in this context?
   :icon: question

   Short-term refers to forecasting horizons of roughly **hours to two days ahead**. A common configuration is a 36-hour forecast horizon, producing predictions at 15-minute or hourly resolution. This is distinct from medium-term (weeks) or long-term (years) planning forecasts.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using a gradient boosting library directly requires you to build all the surrounding infrastructure yourself. OpenSTEF adds:

   - **Domain-specific feature engineering** — built-in transformations for energy data, including solar radiation to PV generation estimates, calendar features, and lag features tuned for load curves.
   - **Probabilistic forecasts** — every model produces quantile predictions (e.g., P10, P50, P90) out of the box, not just a single point estimate.
   - **Model-agnostic pipelines** — swap between XGBoost, LightGBM, GBLinear, and other models without rewriting your pipeline.
   - **Backtesting and evaluation** — the ``openstef-beam`` package provides structured backtesting, scoring, and visualisation utilities.
   - **Production-ready structure** — consistent dataset types, configuration objects, and workflow presets that work the same way across projects.

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF requires **Python 3.12 or newer** (``>=3.12,<4.0``). Make sure your environment meets this requirement before installing.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   Install the full framework with a single command:

   .. code-block:: bash

      pip install openstef

   This installs four packages together: ``openstef-core``, ``openstef-models``, ``openstef-beam``, and ``openstef-meta``.

   If you only need specific functionality you can install individual packages:

   .. code-block:: bash

      # Core data structures and utilities only
      pip install openstef-core

      # Models (includes LightGBM support by default)
      pip install openstef-models

      # Add XGBoost support
      pip install "openstef-models[xgb-cpu]"

      # Backtesting, evaluation, and metrics
      pip install openstef-beam

   See :doc:`installation` for the full list of packages and optional extras.

.. dropdown:: Which models are available?
   :icon: question

   OpenSTEF ships with several gradient boosting models in ``openstef-models``:

   - **XGBoost** — robust general-purpose gradient boosted trees; install with ``openstef-models[xgb-cpu]`` (or ``[xgb-gpu]`` for GPU support).
   - **LightGBM** — fast gradient boosted trees, well-suited for large datasets; install with ``openstef-models[lgbm]``.
   - **GBLinear** — gradient boosted linear model; can extrapolate beyond training data, making it useful for rare peak events, and produces interpretable feature importance.

   All models support **multi-quantile regression** for probabilistic forecasts. You select a model through the ``ForecastingWorkflowConfig``:

   .. code-block:: python

      from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

      workflow = create_forecasting_workflow(
          config=ForecastingWorkflowConfig(
              model_id="my_forecast",
              model_type="xgboost",   # or "lgbm", "gblinear"
              ...
          )
      )

.. dropdown:: Do I need GPU hardware to use OpenSTEF?
   :icon: question

   No. All models run on CPU by default. GPU support is an optional extra for XGBoost:

   .. code-block:: bash

      pip install "openstef-models[xgb-gpu]"

   For most energy forecasting workloads, CPU training is fast enough.

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   OpenSTEF works with **time-indexed pandas DataFrames**. A typical training dataset contains:

   - A ``load`` column with historical energy consumption or generation values (in MW).
   - Weather feature columns (e.g., temperature, irradiance, wind speed).
   - A ``DatetimeIndex`` with a consistent frequency (e.g., 15 minutes or 1 hour).

   OpenSTEF's built-in dataset types (``TimeSeriesDataset``, ``ForecastInputDataset``) wrap these DataFrames and validate their structure. You do not need to pre-engineer calendar or lag features — the pipelines handle that automatically.

.. dropdown:: What are quantiles and why does OpenSTEF use them?
   :icon: light-bulb

   Instead of predicting a single value, OpenSTEF produces a **distribution of outcomes** by training separate quantile regressors. For example, requesting quantiles ``[0.1, 0.5, 0.9]`` gives you a low estimate (P10), a median estimate (P50), and a high estimate (P90) for every time step.

   This is valuable in grid operations because decisions — such as whether to call a customer to reduce load — depend on the *uncertainty* of the forecast, not just the central estimate.

   .. code-block:: python

      from openstef_core.types import Q

      # Request P10, P50, and P90 forecasts
      quantiles = [Q(0.1), Q(0.5), Q(0.9)]

.. dropdown:: How do I run a backtest to evaluate model performance?
   :icon: question

   The ``openstef-beam`` package provides backtesting utilities. A backtest re-trains the model on rolling historical windows and scores predictions against held-out actuals, giving you a realistic picture of production performance.

   .. code-block:: python

      from openstef_beam.backtesting import BacktestPipeline

      results = BacktestPipeline(workflow=workflow, dataset=dataset).run()

   See :doc:`backtesting` for a full walkthrough including scoring metrics and visualisation.

.. dropdown:: Can I add my own custom model?
   :icon: light-bulb

   Yes. OpenSTEF is model-agnostic by design. Any model that implements the ``Forecaster`` interface from ``openstef_models.models.forecasting.forecaster`` can be plugged into the standard pipelines. You can subclass an existing forecaster (e.g., ``LGBMForecaster``) or implement the interface from scratch.

.. dropdown:: Does OpenSTEF handle missing data or outliers?
   :icon: question

   Yes. The preprocessing pipelines in ``openstef-core`` include steps for detecting and handling missing values and outliers before training or forecasting. These steps are applied automatically when you use the built-in workflow presets. You can also configure or extend them if your data has specific characteristics.

.. dropdown:: Where can I find complete working examples?
   :icon: info

   The best place to start is the :doc:`tutorials/index` section, which contains end-to-end Jupyter notebooks covering dataset preparation, model training, forecasting, and evaluation. The :doc:`getting_started` page also walks through a minimal working example from installation to first forecast.

.. dropdown:: Is OpenSTEF production software or a research prototype?
   :icon: info

   OpenSTEF is used in production at Alliander, one of the largest grid operators in the Netherlands, to manage congestion across hundreds of grid points. The library is open-source under the Mozilla Public License 2.0. Version 4 (the current major version) introduced a modular package architecture and is actively maintained.

.. dropdown:: How do I get help or report a bug?
   :icon: alert

   - **GitHub Issues** — report bugs or request features at the `OpenSTEF GitHub repository <https://github.com/OpenSTEF>`_.
   - **Discussions** — use GitHub Discussions for questions and community support.
   - **Documentation** — check :doc:`api/index` for detailed API reference, or :doc:`tutorials/index` for worked examples.

   When reporting a bug, include your Python version, the versions of installed OpenSTEF packages, and a minimal reproducible example.