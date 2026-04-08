FAQ
===

This page answers common questions from new OpenSTEF users. Topics include what short-term forecasting is, system requirements, model choices, and getting started with the library.

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: info

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for creating short-term energy forecasts. Short-term forecasting means predicting load hours to days ahead.

   OpenSTEF is not just a model—it's a complete machine learning framework that provides:

   - Data preprocessing and feature engineering pipelines
   - Multiple forecasting models (XGBoost, linear models, etc.)
   - Probabilistic forecasts with uncertainty quantification
   - Built-in domain knowledge for energy forecasting
   - Model evaluation and post-processing tools

   The library is model-agnostic, meaning you can choose the forecasting algorithm that best fits your use case.

.. dropdown:: What is short-term forecasting and why is it important?
   :icon: question

   Short-term forecasting predicts energy load or generation hours to days ahead. This is critical for managing modern electricity grids facing increasing complexity from solar panels, wind turbines, EVs, and heat pumps.

   Key applications include:

   - **Congestion management**: Predict when grid equipment will exceed capacity limits
   - **Customer connection**: Enable new connections despite capacity constraints by forecasting and managing peak loads
   - **Grid operations**: Transport forecasts, EV charging capacity estimation, grid loss prediction

   OpenSTEF was originally developed at Alliander to address grid congestion—allowing customers to be connected despite capacity limits by forecasting peaks and coordinating load reduction in advance.

.. dropdown:: What makes OpenSTEF different from other forecasting libraries?
   :icon: light-bulb

   OpenSTEF is specifically designed for energy sector forecasting with several unique features:

   - **Domain expertise built-in**: Feature engineering tailored to energy forecasting (e.g., solar radiation → PV generation estimates)
   - **Probabilistic by default**: Generates multiple quantile forecasts with uncertainty bands, not just point predictions
   - **Complete pipeline**: Handles the entire ML workflow from raw data to actionable forecasts
   - **Production-tested**: Used in real-world grid operations at major utilities
   - **Modular architecture**: Install only the components you need

   Unlike general-purpose forecasting libraries, OpenSTEF understands energy data patterns and grid operations requirements.

Installation and Setup
----------------------

.. dropdown:: What are the system requirements?
   :icon: checklist

   OpenSTEF 4.0 requires:

   - **Python 3.12 or higher** (Python 3.13 supported)
   - **64-bit operating system** (Windows, macOS, or Linux)

   You can check your Python version with:

   .. code-block:: bash

      python --version

   If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   OpenSTEF has a modular architecture. Install the base package using your preferred package manager:

   .. code-block:: bash

      # Using pip
      pip install openstef

      # Using uv (recommended)
      uv add openstef

      # Using conda
      conda install -c conda-forge openstef

   Verify your installation:

   .. code-block:: python

      import openstef
      print(f"OpenSTEF version: {openstef.__version__}")

   For detailed installation instructions including optional components, see :doc:`user_guide/installation`.

.. dropdown:: What if I get a Python version error during installation?
   :icon: alert

   If you see an error like:

   .. code-block:: text

      ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

   You need to upgrade to Python 3.12 or higher. We recommend using `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions.

   Alternatively, install OpenSTEF 3.x which supports older Python versions.

Models and Forecasting
----------------------

.. dropdown:: Which forecasting model should I use?
   :icon: question

   OpenSTEF provides several models for different use cases:

   - **XGBoostForecaster**: Best for most energy forecasting tasks. Handles complex patterns and provides excellent accuracy. Supports quantile regression for probabilistic forecasts.
   - **GBLinearForecaster**: Linear model using gradient boosting. Good for interpretable forecasts or when linear relationships dominate.
   - **ConstantMedianForecaster**: Simple baseline model. Useful for testing pipelines or as a comparison benchmark.

   Start with XGBoostForecaster for general-purpose energy forecasting:

   .. code-block:: python

      from openstef.models import XGBoostForecaster
      from openstef.models.confidence import Quantile
      from datetime import timedelta

      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
          horizons=[LeadTime(timedelta(hours=1))],
      )

   See :doc:`user_guide/models` for detailed model comparisons.

.. dropdown:: What are quantile forecasts and why should I use them?
   :icon: info

   Quantile forecasts provide probabilistic predictions with uncertainty bands instead of single point predictions. For example, a 0.9 quantile forecast means there's a 90% probability the actual value will be below the prediction.

   Benefits for energy forecasting:

   - **Risk management**: Understand the range of possible outcomes
   - **Decision making**: Different decisions for optimistic vs. pessimistic scenarios
   - **Reliability**: Know when forecasts are uncertain

   OpenSTEF generates quantile forecasts by default:

   .. code-block:: python

      from openstef.models.confidence import Quantile

      # Predict 10th, 50th (median), and 90th percentiles
      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
      )

   The 0.5 quantile is the median prediction, while 0.1 and 0.9 provide lower and upper bounds.

.. dropdown:: How do I create my first forecast?
   :icon: light-bulb

   Here's a minimal example to get started:

   .. code-block:: python

      from openstef.models import XGBoostForecaster
      from openstef.models.confidence import Quantile
      from datetime import timedelta
      import pandas as pd

      # Prepare your data (must include datetime index and target column)
      training_data = pd.DataFrame({
          'load': [...],  # Your historical load data
          'temperature': [...],  # Weather features
      }, index=pd.date_range('2024-01-01', periods=1000, freq='h'))

      # Create and train forecaster
      forecaster = XGBoostForecaster(
          quantiles=[Quantile(0.5)],
          horizons=[LeadTime(timedelta(hours=1))],
      )
      forecaster.fit(training_data)

      # Generate predictions
      test_data = pd.DataFrame(...)  # Your test data
      predictions = forecaster.predict(test_data)

   For complete examples, see :doc:`examples` and the getting started guide.

Data and Features
-----------------

.. dropdown:: What data do I need to create forecasts?
   :icon: question

   At minimum, you need:

   - **Historical load data**: Time series of energy consumption or generation
   - **Datetime index**: Timestamps for all observations
   - **Weather data** (recommended): Temperature, solar radiation, wind speed, etc.

   OpenSTEF works with pandas DataFrames with a datetime index. The library includes feature engineering to automatically create useful features from your raw data, including:

   - Lag features (previous values)
   - Holiday indicators
   - Time-based features (hour, day of week, etc.)
   - Weather transformations

   See :doc:`user_guide/data` for data preparation guidelines.

.. dropdown:: Do I need to engineer features myself?
   :icon: info

   No—OpenSTEF includes built-in feature engineering specifically designed for energy forecasting. The library automatically creates features like:

   - Temporal features (hour of day, day of week, holidays)
   - Lag transforms (previous load values)
   - Weather-based features (solar radiation → PV estimates)
   - Rolling statistics

   You can use the default feature pipeline or customize it:

   .. code-block:: python

      from openstef.preprocessing import FeaturePipeline
      from openstef.preprocessing.transforms import AddHolidayFeatures, LagTransform

      pipeline = FeaturePipeline([
          AddHolidayFeatures(country='NL'),
          LagTransform(lags=[1, 24, 168]),  # 1h, 1d, 1w lags
      ])

   See :doc:`user_guide/feature_engineering` for customization options.

Getting Help
------------

.. dropdown:: Where can I find examples and tutorials?
   :icon: question

   OpenSTEF provides several learning resources:

   - **Examples**: Short, focused code examples in :doc:`examples`
   - **User Guide**: Comprehensive documentation at :doc:`user_guide/index`
   - **API Reference**: Detailed API documentation at :doc:`api/index`

   Start with the examples to see working code, then consult the user guide for deeper understanding.

.. dropdown:: How do I report bugs or request features?
   :icon: info

   OpenSTEF is an open-source project. You can:

   - **Report bugs**: Open an issue on GitHub with a minimal reproducible example
   - **Request features**: Describe your use case and proposed solution
   - **Contribute**: Submit pull requests with improvements

   See :doc:`contribute/index` for contribution guidelines and community information.

.. dropdown:: Is OpenSTEF suitable for production use?
   :icon: checklist

   Yes—OpenSTEF is used in production at major utilities for real-world grid operations. The library is designed for reliability and includes:

   - Model versioning and persistence
   - Comprehensive testing
   - Production-tested workflows
   - Monitoring and evaluation tools

   However, as with any ML system, thoroughly test on your specific data and use case before deploying to production. Start with pilot projects and gradually scale up.