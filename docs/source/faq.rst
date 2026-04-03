Frequently Asked Questions
==========================

This page answers common questions from users getting started with OpenSTEF, covering installation, core concepts, model choices, and practical usage.

General Questions
-----------------

What is OpenSTEF?
^^^^^^^^^^^^^^^^^

OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides machine learning models and tools specifically designed for forecasting energy loads, solar generation, wind production, and other time series with horizons ranging from minutes to days ahead.

As a library, OpenSTEF is designed to be integrated into your own applications and workflows. It's not a standalone application or web service—you write Python code that uses OpenSTEF's components to build forecasting systems tailored to your needs.

What is short-term forecasting?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Short-term forecasting predicts energy-related values from 15 minutes to several days into the future. This differs from:

- **Ultra-short-term forecasting**: Seconds to minutes ahead, often used for real-time grid control
- **Medium-term forecasting**: Weeks to months ahead, used for maintenance planning
- **Long-term forecasting**: Years ahead, used for infrastructure investment decisions

Short-term forecasts are critical for operational decisions like unit commitment, economic dispatch, and balancing market participation. They help grid operators and energy companies optimize resources and maintain grid stability.

What makes OpenSTEF special?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF was built by energy professionals for energy forecasting, with several unique features:

**Probabilistic forecasting**: OpenSTEF produces quantile forecasts (e.g., P10, P50, P90) rather than just point predictions. This gives you prediction intervals that quantify uncertainty, essential for risk management and decision-making under uncertainty.

**Energy-specific features**: Built-in support for holidays, weather data integration, load patterns, and other domain-specific features that matter for energy forecasting.

**Production-tested**: Originally developed at Alliander (a major Dutch grid operator) and used in production for years. The library reflects real-world operational requirements.

**Modular architecture**: Install only what you need. Use just the core models, add backtesting tools, or include all components for comprehensive analysis.

**Open source and extensible**: Fully open source under the Mozilla Public License 2.0, hosted by LF Energy. You can extend it, contribute improvements, or adapt it to your specific needs.

Installation and Setup
----------------------

What are the system requirements?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 requires:

- Python 3.12 or higher (Python 3.13 is supported)
- 64-bit operating system (Windows, macOS, or Linux)
- Sufficient memory for your datasets (typically 4GB+ RAM recommended)

.. note::
   OpenSTEF 4.0 requires Python 3.12+. If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

How do I install OpenSTEF?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For most users, start with the meta-package:

.. code-block:: bash

   pip install openstef

This installs the core functionality including ``openstef-core`` and ``openstef-models``, which is sufficient for basic forecasting tasks.

For the complete toolkit including backtesting and evaluation:

.. code-block:: bash

   pip install "openstef[all]"

You can also install individual packages:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core
   
   # Core forecasting models only
   pip install openstef-models
   
   # Backtesting and evaluation tools only
   pip install openstef-beam

What's the difference between the packages?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 uses a modular architecture:

- **openstef-core**: Base utilities, data structures, and configuration management
- **openstef-models**: Forecasting models (XGBoost, linear models, quantile regressors)
- **openstef-beam**: Backtesting, evaluation, and analysis tools
- **openstef**: Meta-package that bundles core and models by default

Choose based on your needs. For production forecasting, ``openstef-models`` might be sufficient. For research and experimentation, install ``openstef[all]`` to get everything.

Models and Forecasting
----------------------

What models does OpenSTEF support?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides several forecasting models:

**XGBoost-based models**: The primary workhorses for most forecasting tasks. XGBoost handles non-linear relationships, automatically captures interactions, and works well with diverse feature sets. OpenSTEF includes custom quantile loss functions for probabilistic forecasting.

**Linear models**: Quantile regression using scikit-learn's ``QuantileRegressor``. Useful when interpretability is critical or when you have limited data.

**Ensemble models**: Combine multiple forecasters for improved robustness.

**Baseline models**: Simple forecasters like ``ConstantMedianForecaster`` for benchmarking and testing.

All models implement a consistent interface, making it easy to swap between them or compare performance.

Should I use XGBoost or linear models?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For most energy forecasting tasks, start with XGBoost:

- Handles complex non-linear patterns (e.g., temperature-load relationships)
- Automatically captures feature interactions
- Robust to outliers and missing data
- Generally provides better accuracy for energy time series

Use linear models when:

- You need maximum interpretability (e.g., regulatory requirements)
- You have very limited training data (< 1 month)
- You want faster training and prediction times
- Your relationships are genuinely linear

You can easily compare both approaches since they share the same interface.

What are quantiles and why do they matter?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Quantiles represent different percentiles of the prediction distribution. For example:

- **P10 (10th percentile)**: 10% chance actual value will be below this
- **P50 (50th percentile)**: The median prediction
- **P90 (90th percentile)**: 90% chance actual value will be below this

This gives you prediction intervals: "We predict 100 MW with 80% confidence the actual load will be between 90 MW (P10) and 110 MW (P90)."

Quantile forecasts enable better decision-making:

- **Risk management**: Understand worst-case and best-case scenarios
- **Reserve sizing**: Size reserves based on uncertainty
- **Trading strategies**: Optimize bids considering forecast uncertainty
- **Operational planning**: Make robust decisions that account for variability

How do I train a basic model?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a minimal example:

.. code-block:: python

   from openstef_models.models.forecasting.xgb_quantile_forecaster import XGBQuantileForecaster
   from openstef_core.datasets import ForecastInputDataset
   import pandas as pd
   
   # Prepare your data as a DataFrame with a datetime index
   data = pd.DataFrame({
       'load': [100, 105, 110, 95, 100],  # Target variable
       'temperature': [15, 16, 18, 14, 15],  # Feature
   }, index=pd.date_range('2024-01-01', periods=5, freq='h'))
   
   # Create a dataset
   dataset = ForecastInputDataset(
       data=data,
       target_column='load',
       sample_interval=pd.Timedelta('1h')
   )
   
   # Create and train the model
   model = XGBQuantileForecaster()
   model.fit(dataset)
   
   # Make predictions
   forecast = model.predict(dataset)
   print(forecast.data)

This produces quantile forecasts (P10, P50, P90 by default) for your target variable.

How do I use the complete forecasting pipeline?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For production use, you'll want the full pipeline with preprocessing:

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgb_quantile_forecaster import XGBQuantileForecaster
   from openstef_models.preprocessing.feature_pipeline import FeaturePipeline
   from openstef_models.preprocessing.transforms import AddHolidayFeatures, AddLagFeatures
   from openstef_models.storage.local_model_storage import LocalModelStorage
   from openstef_core.datasets import ForecastInputDataset
   
   # Configure preprocessing
   preprocessing = FeaturePipeline(
       transforms=[
           AddHolidayFeatures(country='NL'),
           AddLagFeatures(lags=[24, 48, 168]),  # 1, 2, 7 days for hourly data
       ]
   )
   
   # Create the complete model
   model = ForecastingModel(
       forecaster=XGBQuantileForecaster(),
       preprocessing=preprocessing,
       cutoff_history=pd.Timedelta('7d')  # Exclude first 7 days (max lag)
   )
   
   # Train
   model.fit(dataset)
   
   # Save for later use
   storage = LocalModelStorage(base_path='./models')
   storage.save(model, identifier='my_forecast_model')
   
   # Load and predict
   loaded_model = storage.load(identifier='my_forecast_model')
   forecast = loaded_model.predict(dataset)

This pattern handles feature engineering, model training, persistence, and prediction in a production-ready way.

Data and Features
-----------------

What data do I need?
^^^^^^^^^^^^^^^^^^^^

At minimum, you need:

- **Target variable**: The value you want to forecast (e.g., load, generation)
- **Historical data**: At least several weeks, preferably months or years
- **Datetime index**: Timestamps for each observation

Recommended additional data:

- **Weather data**: Temperature, wind speed, solar radiation
- **Calendar features**: Automatically added by OpenSTEF (day of week, hour, holidays)
- **Lagged values**: Past values of the target (automatically created with ``AddLagFeatures``)

How much historical data do I need?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It depends on your use case:

- **Minimum**: 1-2 months for basic patterns
- **Recommended**: 1-2 years to capture seasonal patterns
- **Ideal**: 2+ years for robust models that handle rare events

More data generally improves accuracy, especially for capturing seasonal effects, holiday patterns, and extreme weather events.

How do I handle missing data?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's XGBoost models handle missing data automatically—XGBoost learns the best direction to handle missing values during training.

For other models or preprocessing:

- **Forward fill**: Use the last known value
- **Interpolation**: Linear or time-weighted interpolation
- **Removal**: Drop rows with missing critical features

Avoid filling with zeros or means, as this can introduce bias in energy time series.

Common Issues
-------------

Why am I getting import errors?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 uses new package names. Use:

.. code-block:: python

   # Correct
   from openstef_models import forecasting
   from openstef_core.datasets import ForecastInputDataset
   
   # Not: from openstef.models import ...

If you see ``ModuleNotFoundError``, ensure you've installed the correct package (e.g., ``pip install openstef-models``).

What does "cutoff_history" mean?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using lag features (e.g., lag-7 for weekly patterns), the first 7 days of your data will have NaN values for those features. The ``cutoff_history`` parameter tells OpenSTEF to exclude these incomplete rows from training.

Set ``cutoff_history`` to match your maximum lag:

.. code-block:: python

   model = ForecastingModel(
       forecaster=XGBQuantileForecaster(),
       preprocessing=preprocessing,
       cutoff_history=pd.Timedelta('7d')  # For lag-168 (7 days hourly)
   )

How do I improve forecast accuracy?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Try these approaches:

1. **Add more features**: Weather data, calendar features, lagged values
2. **Increase training data**: More historical data captures more patterns
3. **Tune hyperparameters**: Adjust XGBoost parameters like ``max_depth``, ``learning_rate``
4. **Feature engineering**: Create domain-specific features (e.g., cooling degree days)
5. **Ensemble models**: Combine multiple forecasters
6. **Regular retraining**: Update models as new data arrives

Start with good features and sufficient data before tuning hyperparameters.

Where can I find more examples?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check the ``examples/`` directory in the OpenSTEF repository for complete working examples:

- Basic forecasting workflows
- Feature engineering patterns
- Model configuration and tuning
- Backtesting and evaluation
- Custom model development

The examples use real patterns from production systems and demonstrate best practices.

Getting Help
------------

Where can I get support?
^^^^^^^^^^^^^^^^^^^^^^^^^

- **Documentation**: Read the user guide and API reference
- **GitHub Issues**: Report bugs or request features at https://github.com/OpenSTEF/openstef/issues
- **Email**: Contact the team at openstef@lfenergy.org
- **Community**: Join discussions on the LF Energy OpenSTEF project page

How can I contribute?
^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF welcomes contributions! You can:

- Report bugs or suggest features via GitHub Issues
- Submit pull requests with improvements
- Improve documentation
- Share your use cases and examples

See the contribution guide in the documentation for details on setting up a development environment and contribution guidelines.

Is OpenSTEF suitable for production use?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes. OpenSTEF has been used in production by Alliander (a major European grid operator) for years, handling operational forecasting for thousands of grid segments. The library is designed for reliability, maintainability, and scalability.

That said, you're responsible for:

- Validating models for your specific use case
- Monitoring forecast performance
- Handling data quality and availability
- Integrating with your operational systems

OpenSTEF provides the forecasting components; you build the complete system around them.