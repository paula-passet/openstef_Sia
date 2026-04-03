FAQ
===

This FAQ answers common questions from new users about OpenSTEF's capabilities, requirements, and getting started with short-term energy forecasting.

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: info

   OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides machine learning models and tools for predicting energy demand, solar generation, wind power, and other time series up to 48 hours ahead.

   OpenSTEF is a library, not an application—you integrate it into your own Python code to build forecasting pipelines tailored to your needs.

.. dropdown:: What is short-term forecasting?
   :icon: question

   Short-term forecasting predicts energy values from a few hours up to 48 hours into the future. This differs from long-term forecasting (weeks, months, or years ahead) which is used for planning and investment decisions.

   Short-term forecasts help grid operators and energy companies make operational decisions like:

   - Balancing supply and demand in real-time
   - Scheduling maintenance windows
   - Trading energy on day-ahead markets
   - Managing battery storage systems

.. dropdown:: What makes OpenSTEF special?
   :icon: light-bulb

   OpenSTEF brings production-grade forecasting capabilities from real grid operations to the open source community:

   - **Battle-tested**: Used by multiple grid operators managing real electricity networks
   - **Probabilistic forecasting**: Provides prediction intervals, not just point forecasts
   - **Modular design**: Install only what you need—core models, evaluation tools, or the complete suite
   - **Energy-focused**: Built specifically for energy sector challenges like weather dependencies and grid constraints

.. dropdown:: Is OpenSTEF free to use?
   :icon: checklist

   Yes. OpenSTEF is open source under the Mozilla Public License 2.0 (MPL-2.0). You can use it freely for commercial and non-commercial purposes. See the :doc:`../project/license` page for details.

Installation and Setup
----------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF 4.0 requires:

   - Python 3.12 or higher (Python 3.13 supported)
   - 64-bit operating system (Windows, macOS, or Linux)
   - Standard scientific Python stack (numpy, pandas, scikit-learn)

   If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   For most users, start with the meta-package:

   .. code-block:: bash

      pip install openstef

   This installs core forecasting functionality. For the complete toolkit including evaluation tools:

   .. code-block:: bash

      pip install "openstef[all]"

   See the :doc:`installation` guide for detailed instructions and package options.

.. dropdown:: Which package should I install?
   :icon: question

   OpenSTEF 4.0 uses a modular architecture. Choose based on your needs:

   - **openstef** (meta-package): Core forecasting models—recommended starting point
   - **openstef-core**: Base utilities and datasets only
   - **openstef-models**: Forecasting models without dependencies on other packages
   - **openstef-beam**: Backtesting and evaluation tools
   - **openstef[all]**: Everything together

   For production forecasting, ``openstef-models`` provides a lightweight installation. For research and experimentation, use ``openstef[all]``.

.. dropdown:: Can I use OpenSTEF with conda?
   :icon: question

   Yes. OpenSTEF is available on conda-forge:

   .. code-block:: bash

      conda install -c conda-forge openstef

   Make sure the conda-forge channel is added to your configuration.

Models and Forecasting
----------------------

.. dropdown:: What machine learning models does OpenSTEF use?
   :icon: light-bulb

   OpenSTEF primarily uses XGBoost (gradient boosted trees) for forecasting. XGBoost provides:

   - Fast training and prediction
   - Excellent performance on tabular time series data
   - Built-in handling of missing values
   - Feature importance analysis

   The library implements custom quantile regression objectives for probabilistic forecasting, allowing you to generate prediction intervals alongside point forecasts.

.. dropdown:: Do I need to be a machine learning expert?
   :icon: question

   No. OpenSTEF provides sensible defaults that work well for most energy forecasting tasks. You can start making forecasts with just a few lines of code:

   .. code-block:: python

      from openstef_models.forecasting import create_model

      # Create and train a model
      model = create_model("xgb")
      model.fit(train_data, target_column="load")

      # Make predictions
      forecast = model.predict(test_data)

   As you gain experience, you can customize models and tune hyperparameters for your specific use case.

.. dropdown:: What kind of data do I need?
   :icon: question

   At minimum, you need historical time series data with:

   - Timestamps (typically hourly or 15-minute intervals)
   - Target values (e.g., energy demand, solar generation)

   Forecasts improve significantly when you add:

   - Weather forecasts (temperature, wind speed, solar radiation)
   - Calendar features (hour of day, day of week, holidays)
   - Lagged values of the target variable

   OpenSTEF includes feature engineering tools to create these features automatically. See the :doc:`quick_start` guide for examples.

.. dropdown:: Can OpenSTEF handle missing data?
   :icon: question

   Yes. XGBoost, the primary model in OpenSTEF, handles missing values natively during training and prediction. However, you'll get better results by:

   - Filling small gaps with interpolation
   - Understanding why data is missing (sensor failures vs. planned outages)
   - Using data quality checks before training

   The library provides utilities for data validation and preprocessing.

.. dropdown:: How accurate are the forecasts?
   :icon: alert

   Forecast accuracy depends on many factors:

   - Data quality and availability
   - Predictability of the target (solar is easier than wind)
   - Forecast horizon (next hour vs. 48 hours ahead)
   - Weather forecast accuracy

   In production use, OpenSTEF typically achieves:

   - 1-5% MAPE for day-ahead load forecasting
   - 5-15% MAPE for solar generation
   - 10-25% MAPE for wind generation

   Use the backtesting tools in ``openstef-beam`` to evaluate performance on your specific data.

Getting Started
---------------

.. dropdown:: Where should I start?
   :icon: checklist

   Follow this path:

   1. Install OpenSTEF: :doc:`installation`
   2. Try the Quick Start guide: :doc:`quick_start`
   3. Work through tutorials: :doc:`tutorials`
   4. Read about energy forecasting concepts: :doc:`intro/index`

   Most users can create their first forecast within an hour.

.. dropdown:: Can I use OpenSTEF for non-energy forecasting?
   :icon: question

   While OpenSTEF is optimized for energy sector use cases, the underlying models work for any time series forecasting problem. The library is particularly well-suited for:

   - Time series with strong calendar patterns (daily, weekly, seasonal)
   - Problems requiring probabilistic forecasts
   - Applications where weather is a key driver

   However, domain-specific features and defaults assume energy sector data.

.. dropdown:: How do I get help?
   :icon: info

   Several resources are available:

   - Check the documentation you're reading now
   - Search `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for similar problems
   - Ask questions in GitHub Discussions
   - Contact the community: openstef@lfenergy.org

   See the :doc:`../project/support` page for complete details.

.. dropdown:: Can I contribute to OpenSTEF?
   :icon: light-bulb

   Yes! OpenSTEF welcomes contributions from the community. You can:

   - Report bugs and request features
   - Improve documentation
   - Submit code improvements
   - Share your use cases and results

   See the :doc:`../contribute/index` guide to get started.