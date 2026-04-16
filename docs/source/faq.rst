FAQ
===

New to OpenSTEF? This page answers the most common questions from users getting started with the library — from understanding what short-term forecasting is, to choosing the right model, to wiring up your first pipeline.

.. note::

   Looking for a hands-on introduction instead? See :doc:`getting-started/index` for
   step-by-step tutorials and working code examples.

-------------------------------------------------------------------------------

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** for
   building accurate short-term load and energy forecasts in the power grid domain.
   It is published under the MPL-2.0 license and developed by engineers at Alliander.

   "Short-term" means predicting load or generation **hours to days ahead** — the
   time horizon most relevant for grid congestion management, transport forecasts,
   EV charging capacity estimation, and grid loss prediction.

   OpenSTEF is not a standalone application or a hosted service. It is a library you
   import into your own Python code and integrate into your own data and ML pipelines.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: question

   Using a raw ML library for energy forecasting requires you to build a lot of
   domain-specific infrastructure yourself. OpenSTEF provides all of that out of the box:

   - **Domain-aware feature engineering** — built-in transforms for holidays, lag
     features, solar radiation → PV generation estimates, rolling window statistics,
     and more.
   - **Probabilistic forecasts** — every forecast includes uncertainty bandwidths
     (quantile predictions), not just a single point estimate.
   - **Complete pipelines** — preprocessing, training, forecasting, post-processing,
     and evaluation are all first-class citizens in the library.
   - **Model-agnostic design** — swap between XGBoost, LightGBM, linear models, and
     custom forecasters without rewriting your pipeline.
   - **Production patterns** — versioned model storage, workflow orchestration, and
     calibration utilities are included.

   In short, OpenSTEF handles the energy-forecasting-specific plumbing so you can
   focus on your data and your use case.

.. dropdown:: What is a "probabilistic forecast" and why does it matter?
   :icon: question

   A probabilistic forecast produces a **range of possible outcomes** rather than a
   single predicted value. OpenSTEF expresses this as quantile predictions — for
   example, the P10, P50, and P90 quantiles tell you that the true value is expected
   to fall below the P90 estimate 90 % of the time.

   For grid operators, this matters enormously. Knowing that demand will be
   "around 150 MW" is less useful than knowing it will be "between 130 MW and 175 MW
   with 80 % confidence." Uncertainty bandwidths enable better risk management,
   congestion avoidance, and capacity planning.

   OpenSTEF uses isotonic quantile calibration and confidence interval applicators
   as post-processing steps to ensure these uncertainty estimates are well-calibrated
   against historical data.

.. dropdown:: Who develops and maintains OpenSTEF?
   :icon: info

   OpenSTEF was created by data science software engineers at **Alliander**, a Dutch
   distribution system operator (DSO). It is an open-source project hosted under the
   LF Energy foundation and welcomes community contributions.

   The library is actively developed — see the project repository and changelog for
   the latest release information.

-------------------------------------------------------------------------------

Installation and Requirements
------------------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF requires **Python 3.10 or later**. It is structured as a set of
   installable packages:

   - ``openstef-core`` — core data structures, types, and utilities
   - ``openstef-models`` — forecasting models, feature pipelines, and transforms
   - Additional optional packages (e.g., ``openstef-beam``) for orchestration and
     visualisation

   Install the main packages from PyPI:

   .. code-block:: python

      # Install core library and models
      pip install openstef-core openstef-models

   Key runtime dependencies include ``pandas``, ``numpy``, ``scikit-learn``,
   ``xgboost``, ``lightgbm``, and ``pydantic``. These are declared as package
   dependencies and will be installed automatically.

.. dropdown:: Do I need a GPU to use OpenSTEF?
   :icon: question

   No. The default models (XGBoost, LightGBM, gradient-boosted linear) run
   efficiently on CPU hardware. A modern multi-core CPU is sufficient for both
   training and inference on typical grid forecasting datasets.

.. dropdown:: Can I use OpenSTEF in a virtual environment or container?
   :icon: question

   Yes — and it is recommended. A standard Python virtual environment (``venv`` or
   ``conda``) or a Docker container both work well. There is nothing special about
   OpenSTEF's packaging that would prevent containerised deployment.

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate      # Linux / macOS
      # .venv\Scripts\activate       # Windows
      pip install openstef-core openstef-models

-------------------------------------------------------------------------------

Models and Forecasting
-----------------------

.. dropdown:: Which ML models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several built-in forecasters:

   - **XGBoost** — gradient-boosted trees; handles complex non-linear patterns well
     and is a strong default choice for most grid forecasting tasks.
   - **LightGBM** — gradient-boosted trees with faster training and lower memory
     usage; well-suited to large datasets.
   - **GBLinear** — gradient-boosted linear model; better extrapolation behaviour
     outside the training distribution and faster to train.
   - **ConstantMedianForecaster** — a simple baseline that predicts the historical
     median; useful for sanity-checking pipelines.

   All models share the same ``Forecaster`` interface, so switching between them
   requires changing only the ``model`` parameter in your configuration — the rest
   of your pipeline stays the same.

.. dropdown:: How do I choose between XGBoost and LightGBM?
   :icon: light-bulb

   Both are strong choices. As a starting point:

   - Use **XGBoost** when your dataset is moderate in size and you want a well-tested
     default with broad community support.
   - Use **LightGBM** when training speed or memory usage is a concern, or when your
     dataset is large (millions of rows).

   In practice, the difference in forecast accuracy is often small. The best approach
   is to benchmark both on your specific data using OpenSTEF's built-in backtesting
   utilities and let the metrics decide. See :doc:`user-guide/models` for a detailed
   comparison.

.. dropdown:: Can I plug in my own custom model?
   :icon: question

   Yes. OpenSTEF is designed to be model-agnostic. You can implement the
   ``Forecaster`` interface from ``openstef_models`` and drop your custom model
   into any standard pipeline without modifying the surrounding infrastructure.
   See :doc:`user-guide/models` for the interface contract and an example.

.. dropdown:: What forecast horizons does OpenSTEF support?
   :icon: question

   OpenSTEF is designed for **short-term forecasting**, typically from 15 minutes
   to 48 hours ahead. Horizons are expressed as ``LeadTime`` values and are
   configurable per pipeline. You can specify multiple horizons in a single training
   run:

   .. code-block:: python

      from openstef_core.types import LeadTime
      from datetime import timedelta

      horizons = [
          LeadTime(timedelta(hours=1)),
          LeadTime(timedelta(hours=24)),
          LeadTime(timedelta(hours=48)),
      ]

   Very long-range forecasting (weeks to months) is outside the library's primary
   design scope.

-------------------------------------------------------------------------------

Data and Feature Engineering
------------------------------

.. dropdown:: What input data does OpenSTEF expect?
   :icon: question

   At minimum, OpenSTEF needs a **time-indexed pandas DataFrame** containing your
   target variable (e.g., measured load in MW) and any available weather or
   contextual features. The library wraps this in its own ``TimeSeriesDataset`` and
   ``ForecastDataset`` types for type safety and pipeline compatibility.

   For testing and prototyping, you can generate synthetic data without any real
   dataset:

   .. code-block:: python

      from openstef_core.testing import create_synthetic_forecasting_dataset

      dataset = create_synthetic_forecasting_dataset()

.. dropdown:: Does OpenSTEF handle missing data and outliers automatically?
   :icon: question

   Yes. The preprocessing pipeline includes data cleaning steps that handle common
   issues such as missing values and flatliners (periods where the meter reports a
   constant value, often indicating a sensor fault). These are applied automatically
   when you use the standard ``FeaturePipeline``.

   You can also customise or extend the preprocessing steps if your data has
   domain-specific quality issues. See :doc:`user-guide/data-preparation` for details.

.. dropdown:: What weather features does OpenSTEF use?
   :icon: question

   OpenSTEF includes built-in feature engineering for common meteorological variables:

   - **Solar radiation** — converted to estimated PV generation
   - **Wind speed** — supports 80 m hub-height wind speed for wind park forecasting
   - **Temperature** — for heating/cooling demand modelling
   - **Surface pressure** and **relative humidity**

   These column names are configurable so you can map them to whatever your weather
   data source provides. The library also computes **rolling aggregate features**
   (mean, median, min, max over configurable windows) and **lag features**
   automatically.

.. dropdown:: Does OpenSTEF include holiday and calendar features?
   :icon: question

   Yes. The ``FeaturePipeline`` includes a holiday feature transform that adds
   calendar-aware flags (public holidays, weekends, day-of-week, hour-of-day) to
   your feature set. These are important for energy forecasting because load patterns
   differ significantly between working days and holidays.

   Country-specific holiday calendars are supported via the ``CountryAlpha2`` type
   from ``pydantic-extra-types``.

-------------------------------------------------------------------------------

Pipelines and Workflows
------------------------

.. dropdown:: What is the difference between a FeaturePipeline and a ForecastingModel?
   :icon: question

   - A **FeaturePipeline** is a preprocessing chain: it takes raw time series data
     and produces an enriched feature matrix ready for model training or inference.
     It includes steps like holiday encoding, lag transforms, and data scaling.
   - A **ForecastingModel** wraps a ``FeaturePipeline`` together with a core ML
     model (e.g., LightGBM) and post-processing steps (e.g., quantile calibration)
     into a single, trainable, serialisable object.

   In most workflows you interact with the ``ForecastingModel`` directly and let it
   manage the pipeline internally.

.. dropdown:: How do I persist a trained model and reload it later?
   :icon: question

   OpenSTEF provides a ``LocalModelStorage`` utility for file-based model
   persistence. Models are versioned automatically so you can roll back to a
   previous version if needed.

   .. code-block:: python

      from openstef_models.storage import LocalModelStorage
      from pathlib import Path

      storage = LocalModelStorage(base_path=Path("./models"))

      # Save after training
      storage.save(model, model_id="my_grid_substation")

      # Load for inference
      model = storage.load(model_id="my_grid_substation")

   For production deployments, MLflow-based storage is also supported. See
   :doc:`user-guide/models` for the full storage API.

.. dropdown:: How do I run a backtest to evaluate forecast quality?
   :icon: question

   OpenSTEF includes backtesting utilities that walk through your historical data
   in a time-ordered fashion, training on past data and evaluating on held-out
   future windows. This gives you realistic performance estimates that respect the
   temporal structure of the problem (no data leakage from the future).

   See :doc:`user-guide/pipelines` for a worked backtesting example.

-------------------------------------------------------------------------------

Troubleshooting
----------------

.. dropdown:: My model trains without errors but the forecasts look wrong. Where do I start?
   :icon: alert

   A few common causes and checks:

   - **Check your target variable** — confirm the column you are forecasting contains
     clean, physically plausible values. Flatliners and outliers in the training data
     are a frequent source of poor forecasts.
   - **Check feature alignment** — make sure weather and other contextual features
     are available at inference time and are aligned to the same timestamps as your
     target.
   - **Run the baseline first** — train a ``ConstantMedianForecaster`` and compare
     its error metrics to your main model. If the baseline is competitive, your
     features may not be adding signal.
   - **Inspect feature importance** — OpenSTEF models expose feature importance
     scores. Low importance for features you expect to matter is a sign of a data
     or alignment issue.

.. dropdown:: I get an import error when importing openstef_models. What should I check?
   :icon: alert

   First, confirm both packages are installed in the same environment:

   .. code-block:: bash

      pip show openstef-core openstef-models

   If either is missing, install it:

   .. code-block:: bash

      pip install openstef-core openstef-models

   If you see version conflicts, ensure your ``openstef-core`` and ``openstef-models``
   versions are compatible — they are released together and should be kept in sync.
   Check the release notes for the correct version pairing.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - **GitHub Issues** — for bug reports and feature requests, open an issue on the
     OpenSTEF repository.
   - **GitHub Discussions** — for questions, usage help, and community conversation.
   - **LF Energy Slack** — the ``#openstef`` channel is a good place for real-time
     questions.

   When reporting a bug, please include your Python version, package versions
   (``pip show openstef-core openstef-models``), a minimal reproducible example,
   and the full traceback.