FAQ
===

This FAQ covers the most common questions from new users of OpenSTEF — from understanding what the library does and why it exists, to getting your environment set up and running your first forecast. If you don't find your answer here, check the :doc:`getting_started` guide or open a discussion on GitHub.

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for building accurate short-term energy load forecasts. It provides complete, production-ready pipelines covering data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation, and post-processing — all in one cohesive framework.

   OpenSTEF is not a standalone application or a hosted service. You import it into your own Python code and use its components to build forecasting workflows tailored to your data and infrastructure.

   .. code-block:: python

      # OpenSTEF is a library — you import and use it in your own code
      from openstef_models.presets import ForecastingWorkflowConfig

      config = ForecastingWorkflowConfig(
          model_id="my_substation",
          model="xgboost",
          horizons=[1, 24, 48],
          quantiles=[0.1, 0.5, 0.9],
      )

.. dropdown:: What does "short-term" forecasting mean?
   :icon: question

   Short-term forecasting means predicting energy load **hours to days ahead** — typically up to 48 hours into the future. This time horizon is critical for grid operators who need to anticipate congestion, plan dispatch, estimate EV charging capacity, and manage grid losses before conditions change.

   Longer-horizon forecasting (weeks, months, years) is a different problem domain with different modelling approaches. OpenSTEF is specifically designed and optimised for the short-term window where weather patterns, time-of-day effects, and recent load history are the dominant signals.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a raw ML library gives you a model. OpenSTEF gives you a **forecasting system**. The difference matters in production:

   - **Domain-aware feature engineering** — built-in transforms convert raw weather data (solar radiation, wind speed, temperature, pressure, humidity) into features that directly reflect physical generation and consumption behaviour.
   - **Probabilistic outputs** — every forecast produces a full set of quantile predictions (e.g. P10, P50, P90), not just a single point estimate. Uncertainty bands are calibrated using isotonic regression.
   - **Pipeline completeness** — preprocessing, training, prediction, confidence interval application, and post-processing are all handled consistently, reducing the surface area for subtle bugs.
   - **Model agnosticism** — you can swap between XGBoost, LightGBM, GBLinear, and ensemble combiners without rewriting your pipeline.
   - **Evaluation tooling** — the ``openstef-beam`` package provides backtesting, scoring rules, and interactive visualisations out of the box.

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF requires:

   - **Python** ``>=3.12, <4.0``
   - A standard pip-compatible environment (virtualenv, conda, etc.)

   No special hardware is required for typical grid substation forecasting. GPU support is not needed — the gradient boosting models used by OpenSTEF train efficiently on CPU.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest way is to install the meta-package, which pulls in all sub-packages:

   .. code-block:: bash

      pip install openstef

   This installs four packages together:

   - ``openstef-core`` — shared data structures, datasets, and utilities
   - ``openstef-models`` — forecasting models (XGBoost, LightGBM, GBLinear, ensembles)
   - ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM)
   - ``openstef-meta`` — meta-learning and forecast combination utilities

   If you only need a subset of the functionality, you can install individual packages:

   .. code-block:: bash

      pip install openstef-core      # Core framework only
      pip install openstef-models    # Models + core
      pip install openstef-beam      # Evaluation + analysis

   For S3-backed storage or baseline model comparisons, install optional extras:

   .. code-block:: bash

      pip install "openstef-beam[all]"

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several model types, all accessible through the same pipeline interface:

   - **XGBoost** — gradient boosting trees; handles complex non-linear patterns well and is a strong default choice for most substations.
   - **LightGBM (LGBM)** — gradient boosting trees with a leaf-wise growth strategy; often faster to train and competitive in accuracy.
   - **GBLinear** — gradient boosted linear model; better extrapolation behaviour outside the training distribution and faster inference.
   - **Ensemble / combiner models** — ``LGBMCombiner`` and related classes that learn to blend predictions from multiple base forecasters.

   You select a model by setting the ``model`` field in your workflow configuration:

   .. code-block:: python

      from openstef_models.presets import ForecastingWorkflowConfig

      config = ForecastingWorkflowConfig(
          model_id="my_substation",
          model="lgbm",          # or "xgboost", "gblinear"
          horizons=[1, 24, 48],
          quantiles=[0.1, 0.5, 0.9],
      )

   See :doc:`models/index` for a detailed comparison of each model's strengths and trade-offs.

.. dropdown:: What does a probabilistic forecast look like?
   :icon: question

   Instead of a single predicted value, OpenSTEF returns a forecast for each quantile you request. For example, requesting quantiles ``[0.1, 0.5, 0.9]`` gives you:

   - ``quantile_P10`` — lower bound (10th percentile): load is unlikely to fall below this
   - ``quantile_P50`` — median prediction: the central estimate
   - ``quantile_P90`` — upper bound (90th percentile): load is unlikely to exceed this

   The spread between P10 and P90 is your uncertainty bandwidth. Wider bands indicate periods where the model is less confident — for example, during unusual weather or public holidays.

   .. code-block:: python

      from openstef_core.datasets import ForecastDataset

      forecast: ForecastDataset = workflow.predict(forecast_dataset)

      print(forecast.quantiles)        # e.g. [0.1, 0.5, 0.9]
      print(forecast.median_series)    # P50 point forecast as a pandas Series
      print(forecast.quantiles_data)   # Full quantile DataFrame

.. dropdown:: Can I visualise my forecasts without leaving OpenSTEF?
   :icon: question

   Yes. The ``openstef-beam`` package includes ``ForecastTimeSeriesPlotter``, an interactive Plotly-based visualisation tool that renders forecasts with shaded confidence bands:

   .. code-block:: python

      from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

      fig = (
          ForecastTimeSeriesPlotter()
          .add_measurements(measurements=forecast_dataset.data["load"])
          .add_model(
              model_name="XGBoost",
              forecast=forecast.median_series,
              quantiles=forecast.quantiles_data,
          )
          .plot()
      )

      fig.update_layout(
          title="Energy Load Forecast vs Actual",
          yaxis_title="Load (MW)",
      )
      fig.show()

   The resulting chart shows actual measurements as a line, the median forecast as an overlay, and the P10–P90 interval as a shaded area. No external plotting setup is required.

.. dropdown:: What input data does OpenSTEF need?
   :icon: question

   At a minimum, OpenSTEF needs a time-indexed pandas ``DataFrame`` containing:

   - **Historical load measurements** — the target variable you want to forecast (e.g. MW at a substation).
   - **Weather features** — at least some subset of: solar radiation, wind speed, temperature, surface pressure, and relative humidity. These are mapped to model inputs via column name configuration.

   Optional but beneficial inputs include energy price signals (e.g. day-ahead EPEX prices) and any domain-specific features relevant to your site.

   Column names are configured explicitly in ``ForecastingWorkflowConfig``, so your data does not need to follow a rigid naming convention:

   .. code-block:: python

      config = ForecastingWorkflowConfig(
          model_id="my_substation",
          model="xgboost",
          horizons=[1, 24, 48],
          quantiles=[0.1, 0.5, 0.9],
          radiation_column="shortwave_radiation",
          wind_speed_column="wind_speed_80m",
          temperature_column="temperature_2m",
          pressure_column="surface_pressure",
          relative_humidity_column="relative_humidity_2m",
          energy_price_column="EPEX_NL",
      )

.. dropdown:: How does OpenSTEF handle missing data?
   :icon: question

   OpenSTEF's pipeline is designed to degrade gracefully rather than crash when data is incomplete. Forecasters check whether sufficient data is available before attempting a prediction and return ``None`` when the input is insufficiently complete. The ``InsufficientlyCompleteError`` exception is used internally to signal these cases in a structured way.

   For training, gaps in historical data are handled during the preprocessing stage. You should still aim to provide as complete a history as possible — sparse training data will reduce model accuracy, particularly for capturing seasonal and weekly patterns.

.. dropdown:: Is OpenSTEF only useful for electricity grid operators?
   :icon: question

   OpenSTEF was built by and for grid operators (it originated at Alliander, a Dutch distribution system operator), but the library itself is general-purpose. Any time series forecasting problem that shares the same structure — a load-like target variable, weather covariates, and a short-term horizon — can benefit from OpenSTEF's pipelines.

   Documented use cases include:

   - Substation load forecasting for congestion management
   - Transport capacity forecasting
   - EV charging capacity estimation
   - Grid loss prediction

   If your domain fits this pattern, OpenSTEF's built-in feature engineering and probabilistic outputs are directly applicable.

.. dropdown:: Where can I find a complete working example?
   :icon: light-bulb

   The best starting point is the :doc:`getting_started` guide, which walks through a full workflow using the Liander 2024 Energy Forecasting Benchmark dataset. It covers data loading, configuration, training, prediction, and visualisation end-to-end.

   You can also explore the ``openstef-beam`` backtesting utilities for evaluating model performance across multiple time windows — see :doc:`evaluation/backtesting` for details.

.. dropdown:: How do I report a bug or request a feature?
   :icon: alert

   OpenSTEF is open source and developed on GitHub. To report a bug, open an issue in the relevant sub-package repository and include:

   - Your OpenSTEF version (``pip show openstef``)
   - Your Python version
   - A minimal reproducible example
   - The full traceback if an exception was raised

   Feature requests and architectural discussions are welcome as GitHub Discussions. For questions about usage, check the existing issues and discussions before opening a new one — your question may already have an answer.