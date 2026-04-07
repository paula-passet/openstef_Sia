FAQ
===

This FAQ covers common questions from new users about OpenSTEF's capabilities, requirements, and getting started with short-term energy forecasting.

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: info

   OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides machine learning models and tools specifically designed for predicting energy consumption, generation, and grid loads over horizons ranging from minutes to days ahead.

   OpenSTEF is a **library**, not an application—you integrate it into your own Python code to build forecasting pipelines tailored to your needs.

.. dropdown:: What is short-term forecasting?
   :icon: question

   Short-term forecasting predicts energy values over near-future time horizons, typically from 15 minutes to several days ahead. This differs from long-term forecasting (months to years) used for capacity planning.

   Short-term forecasts are essential for:

   - Real-time grid operations and balancing
   - Energy trading and market participation
   - Demand response optimization
   - Renewable energy integration

.. dropdown:: What makes OpenSTEF different from other forecasting libraries?
   :icon: light-bulb

   OpenSTEF is purpose-built for energy sector forecasting with several unique features:

   - **Multi-quantile forecasting**: Generate probabilistic forecasts with confidence intervals, not just point predictions
   - **Energy-specific preprocessing**: Built-in handling of weather data, holidays, and energy-specific patterns
   - **Production-ready models**: Battle-tested algorithms used by grid operators in real-world operations
   - **Modular architecture**: Install only the components you need for your use case

Installation and Setup
----------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF 4.0 requires:

   - Python 3.12 or higher (Python 3.13 supported)
   - 64-bit operating system (Windows, macOS, or Linux)
   - Sufficient memory for your dataset size (typically 4GB+ RAM recommended)

   If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

   See :doc:`user_guide/installation` for complete details.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   For most users, start with the meta-package:

   .. code-block:: bash

      pip install openstef

   This installs the core functionality and forecasting models. For the complete toolkit including evaluation tools:

   .. code-block:: bash

      pip install "openstef[all]"

   OpenSTEF uses a modular design, so you can also install individual packages:

   .. code-block:: bash

      pip install openstef-models  # Core forecasting models only
      pip install openstef-beam    # Backtesting and evaluation tools

   See :doc:`user_guide/installation` for more installation options.

.. dropdown:: Which package do I need for my use case?
   :icon: question

   Choose based on what you're building:

   - **Research and experimentation**: ``pip install "openstef[all]"`` gives you the full toolkit
   - **Production forecasting**: ``pip install openstef-models`` for lightweight core models
   - **Model evaluation**: ``pip install "openstef[beam]"`` for models plus evaluation tools
   - **Basic development**: ``pip install openstef`` for core functionality

   The modular design lets you start small and add components as needed.

Models and Forecasting
----------------------

.. dropdown:: What forecasting models does OpenSTEF provide?
   :icon: question

   OpenSTEF includes several production-ready models:

   - **XGBoostForecaster**: Gradient boosting model for complex non-linear patterns (most commonly used)
   - **GBLinearForecaster**: Linear model using XGBoost's linear learner
   - **ConstantMedianForecaster**: Simple baseline that predicts historical median values

   All models support multi-quantile forecasting for probabilistic predictions. XGBoost models use magnitude-weighted pinball loss for improved accuracy.

   Example:

   .. code-block:: python

      from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
      from openstef_core.types import Quantile, LeadTime
      from datetime import timedelta

      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
          horizons=[LeadTime(timedelta(hours=1))],
      )

.. dropdown:: What is quantile forecasting and why should I use it?
   :icon: info

   Quantile forecasting produces multiple predictions at different probability levels, giving you a range of possible outcomes instead of a single point prediction.

   For example, predicting quantiles 0.1, 0.5, and 0.9 tells you:

   - 10% chance actual value will be below the 0.1 quantile (lower bound)
   - 50% chance actual value will be below the 0.5 quantile (median prediction)
   - 90% chance actual value will be below the 0.9 quantile (upper bound)

   This is crucial for energy operations where you need to understand forecast uncertainty for risk management and decision-making.

.. dropdown:: How do I choose the right model?
   :icon: light-bulb

   Start with **XGBoostForecaster**—it's the most widely used and handles complex patterns well:

   .. code-block:: python

      from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
          horizons=[LeadTime(timedelta(hours=1))],
      )

   Use **GBLinearForecaster** if you need a simpler linear model or want more interpretability.

   Use **ConstantMedianForecaster** as a baseline to compare against more sophisticated models.

   The best model depends on your data characteristics, forecast horizon, and accuracy requirements. Evaluate multiple models using the backtesting tools in ``openstef-beam``.

Getting Started
---------------

.. dropdown:: How do I create my first forecast?
   :icon: question

   Here's a minimal example:

   .. code-block:: python

      from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
      from openstef_core.types import Quantile, LeadTime
      from datetime import timedelta

      # Create forecaster
      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.5)],  # Median prediction
          horizons=[LeadTime(timedelta(hours=1))],
      )

      # Train on your historical data
      forecaster.fit(training_data)

      # Generate predictions
      predictions = forecaster.predict(test_data)

   Your data should be a pandas DataFrame with a datetime index and relevant features (load values, weather, etc.).

   See :doc:`user_guide/quick_start` for a complete walkthrough.

.. dropdown:: What data format does OpenSTEF expect?
   :icon: question

   OpenSTEF expects pandas DataFrames with:

   - **DatetimeIndex**: Timestamps for your time series
   - **Target column**: The values you want to forecast (e.g., energy load)
   - **Feature columns**: Predictors like temperature, hour of day, day of week, etc.

   The library includes dataset classes like ``ForecastInputDataset`` to help structure your data correctly with validation and type checking.

   For training data, ensure regular time intervals and handle missing values appropriately.

.. dropdown:: Where can I find examples and tutorials?
   :icon: info

   Start with these resources:

   - :doc:`user_guide/quick_start` - Your first forecast in minutes
   - :doc:`user_guide/tutorials` - Step-by-step guides for common tasks
   - :doc:`intro/index` - Understanding energy forecasting concepts
   - :doc:`api/index` - Complete API reference

   The documentation includes executable code examples you can adapt to your use case.

Troubleshooting
---------------

.. dropdown:: I'm getting a Python version error during installation. What should I do?
   :icon: alert

   OpenSTEF 4.0 requires Python 3.12 or higher. If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade Python. We recommend using `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions:

   .. code-block:: bash

      # Using pyenv
      pyenv install 3.12
      pyenv local 3.12

      # Using conda
      conda create -n openstef python=3.12
      conda activate openstef

   If you cannot upgrade, use OpenSTEF 3.x which supports Python 3.10+.

.. dropdown:: I'm getting import errors. What's wrong?
   :icon: alert

   OpenSTEF 4.0 uses a modular package structure with specific import paths. Make sure you're using the correct package names:

   .. code-block:: python

      # Correct imports
      from openstef_models.models.forecasting import XGBoostForecaster
      from openstef_core.types import Quantile, LeadTime
      from openstef_beam.evaluation import evaluate_model

      # Incorrect (won't work)
      from openstef.models import XGBoostForecaster  # Wrong!

   Also verify you've installed the package containing the module you're trying to import. For example, ``openstef_beam`` requires separate installation.

.. dropdown:: Where can I get help?
   :icon: question

   If you're stuck:

   1. Check the :doc:`user_guide/installation` troubleshooting section
   2. Search `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for similar problems
   3. Review the :doc:`../contribute/index` guide for development setup help
   4. Visit our :doc:`../project/support` page for community resources
   5. Contact us at openstef@lfenergy.org

   When asking for help, include your Python version, OpenSTEF version, and a minimal code example that reproduces the issue.