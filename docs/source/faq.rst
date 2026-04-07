FAQ
===

This FAQ answers common questions from new users about OpenSTEF's capabilities, requirements, and usage. For more detailed information, check the relevant documentation sections linked throughout.

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: info

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term energy forecasts. It provides complete machine learning pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing.

   OpenSTEF is **not just a model**—it's a model-agnostic framework that includes domain knowledge specific to energy forecasting, such as converting solar radiation to PV generation estimates. The library generates probabilistic forecasts with uncertainty bandwidths, not just single-point predictions.

.. dropdown:: What does "short-term forecasting" mean?
   :icon: question

   Short-term forecasting means predicting energy load hours to days ahead, typically from 15 minutes to 48 hours into the future. This is distinct from long-term forecasting (months or years ahead) used for infrastructure planning.

   Short-term forecasts are essential for congestion management, transport forecasts, EV charging capacity estimation, and grid loss prediction.

.. dropdown:: What makes OpenSTEF special compared to other forecasting libraries?
   :icon: light-bulb

   OpenSTEF is purpose-built for energy forecasting with several unique features:

   - **Domain-specific feature engineering**: Built-in transformers for solar radiation, wind power, atmospheric conditions, and daylight calculations
   - **Probabilistic forecasts**: Native support for quantile regression to capture forecast uncertainty
   - **Production-ready**: Battle-tested at Alliander for congestion management on the Dutch electricity grid
   - **Complete pipelines**: Everything from data validation to post-processing in one library

   See :doc:`user_guide/index` for a comprehensive overview.

.. dropdown:: Is OpenSTEF an application or a library?
   :icon: info

   OpenSTEF is a **library**, not a standalone application. You integrate it into your own Python applications and workflows. This gives you flexibility to customize data sources, deployment strategies, and integration with existing systems.

   For a quick start example, see :doc:`user_guide/quickstart`.

Installation and Setup
----------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   - Python 3.12 or higher (Python 3.13 supported)
   - 64-bit operating system (Windows, macOS, or Linux)

   You can check your Python version with:

   .. code-block:: bash

      python --version

   If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest installation uses pip:

   .. code-block:: bash

      pip install openstef

   OpenSTEF 4.0 has a modular architecture. The base ``openstef`` package includes core functionality and models. For additional components, you can install:

   .. code-block:: bash

      pip install openstef-beam  # Apache Beam pipelines
      pip install openstef-dbc   # Database connectors

   See :doc:`user_guide/installation` for detailed instructions including conda, uv, and pixi options.

.. dropdown:: What dependencies does OpenSTEF require?
   :icon: checklist

   OpenSTEF automatically installs its dependencies when you install the package. Key dependencies include:

   - **XGBoost**: For gradient boosting models
   - **scikit-learn**: For preprocessing and linear models
   - **pandas**: For data manipulation
   - **numpy**: For numerical operations
   - **pydantic**: For configuration validation

   You don't need to install these manually—the package manager handles them automatically.

Models and Forecasting
----------------------

.. dropdown:: What models does OpenSTEF support?
   :icon: question

   OpenSTEF supports multiple model types:

   - **XGBoostForecaster**: Gradient boosting trees (recommended for most use cases)
   - **LinearForecaster**: Ridge regression with L2 regularization
   - **GBLinearForecaster**: Linear model using XGBoost's linear booster

   All models support multi-quantile probabilistic forecasting. XGBoost is the default and most commonly used model due to its strong performance on energy forecasting tasks.

   Example:

   .. code-block:: python

      from openstef_models.models.forecasting import XGBoostForecaster

      forecaster = XGBoostForecaster(
          quantiles=[0.1, 0.5, 0.9],
          horizons=[0.25, 24.0, 47.0]
      )

.. dropdown:: How do I choose between XGBoost and linear models?
   :icon: light-bulb

   **Use XGBoost** (default) when:

   - You have sufficient training data (weeks to months)
   - You need to capture non-linear patterns
   - Forecast accuracy is the top priority
   - You have computational resources for training

   **Use LinearForecaster** when:

   - You have limited training data
   - You need fast training and inference
   - Model interpretability is critical
   - Your load patterns are relatively simple

   Start with XGBoost—it works well for most energy forecasting scenarios.

.. dropdown:: Can I use my own custom model?
   :icon: question

   Yes! OpenSTEF is model-agnostic. You can implement custom models by inheriting from the base forecaster classes and implementing the required methods. The preprocessing and feature engineering pipelines work with any model.

   See :doc:`api/index` for details on the forecaster interface.

.. dropdown:: What is quantile regression and why does OpenSTEF use it?
   :icon: info

   Quantile regression predicts multiple quantiles (e.g., 10th, 50th, 90th percentiles) instead of just the mean. This provides uncertainty estimates alongside your forecast.

   For example, a forecast might predict:

   - 10th percentile: 500 kW (optimistic scenario)
   - 50th percentile: 750 kW (median forecast)
   - 90th percentile: 1000 kW (conservative scenario)

   This is crucial for grid operations where you need to know the range of possible outcomes, not just a single prediction.

Data and Features
-----------------

.. dropdown:: What input data does OpenSTEF need?
   :icon: question

   At minimum, you need:

   - **Historical load data**: Your target variable (energy consumption or generation)
   - **Timestamps**: DateTime index for your data
   - **Weather forecasts**: Temperature, radiation, wind speed (depending on your use case)

   Optional but recommended:

   - Solar radiation (for PV forecasting)
   - Wind speed (for wind power forecasting)
   - Energy prices
   - Holiday calendars

   See :doc:`user_guide/data_requirements` for detailed specifications.

.. dropdown:: Does OpenSTEF handle feature engineering automatically?
   :icon: light-bulb

   Yes! OpenSTEF includes extensive built-in feature engineering:

   - Cyclic encoding of time features (hour, day of week, month)
   - Daylight calculations based on geographic coordinates
   - Atmospheric features (dew point, saturation pressure)
   - Wind power curves
   - Solar radiation transformations
   - Rolling aggregates and lag features

   You configure which features to use, and OpenSTEF handles the transformations. See :doc:`user_guide/feature_engineering` for details.

Common Issues
-------------

.. dropdown:: I'm getting a Python version error during installation
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. We recommend using `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions.

   If you cannot upgrade, use OpenSTEF 3.x which supports Python 3.10+.

.. dropdown:: Where can I find code examples?
   :icon: question

   Check these resources:

   - :doc:`user_guide/quickstart`: Basic usage example
   - :doc:`examples`: Complete end-to-end examples
   - `GitHub repository <https://github.com/OpenSTEF/openstef>`_: Example notebooks and scripts

.. dropdown:: How do I get help or report issues?
   :icon: info

   - **Documentation**: Start with :doc:`user_guide/index`
   - **GitHub Issues**: Report bugs or request features at https://github.com/OpenSTEF/openstef/issues
   - **Community**: Join discussions on the LF Energy Slack workspace

   See :doc:`project/index` for more community resources.