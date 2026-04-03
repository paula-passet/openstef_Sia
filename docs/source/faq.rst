Frequently Asked Questions
==========================

This page answers common questions from users getting started with OpenSTEF, covering installation, forecasting concepts, model selection, and typical setup scenarios.

General Questions
-----------------

What is OpenSTEF?
^^^^^^^^^^^^^^^^^

OpenSTEF is a Python library for creating short-term energy forecasts. It provides machine learning models and workflows specifically designed for forecasting energy consumption, production, and grid loads with horizons ranging from minutes to days ahead.

OpenSTEF is a **library**, not a standalone application. You integrate it into your own Python applications and workflows to add forecasting capabilities.

What is short-term forecasting?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Short-term forecasting predicts energy values from minutes to several days ahead. This differs from long-term forecasting (months to years) used for infrastructure planning.

Typical use cases include:

- **Grid operators**: Predicting load on substations and feeders to prevent overloads
- **Energy traders**: Forecasting production from renewable sources for market bidding
- **Building managers**: Anticipating consumption for demand response programs

Short-term forecasts use recent historical data and weather predictions to capture patterns like daily cycles, weather impacts, and seasonal effects.

What makes OpenSTEF special?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF is purpose-built for energy forecasting with features that generic machine learning libraries don't provide:

- **Probabilistic forecasts**: Generates prediction intervals (quantiles) to quantify uncertainty, not just point estimates
- **Energy-specific features**: Automatic feature engineering for weather, time patterns, and energy components
- **Production-ready workflows**: Complete pipelines for training, validation, backtesting, and deployment
- **Proven in practice**: Developed by Alliander and used in production for managing the Dutch electricity grid

The library handles common energy forecasting challenges like missing data, irregular intervals, and combining multiple data sources.

Installation and Setup
----------------------

What are the system requirements?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF requires:

- **Python**: 3.9 or higher
- **Operating system**: Linux, macOS, or Windows
- **Memory**: Depends on dataset size; 4GB+ recommended for typical use
- **Optional dependencies**: XGBoost for tree-based models (most common use case)

How do I install OpenSTEF?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For basic usage, install the core package:

.. code-block:: bash

   pip install openstef-core

For the most common forecasting scenarios using XGBoost models, install the models package:

.. code-block:: bash

   pip install openstef-models[xgboost]

For batch processing and benchmarking capabilities:

.. code-block:: bash

   pip install openstef-beam

The modular structure lets you install only what you need. Most users start with ``openstef-models[xgboost]`` which includes everything for standard forecasting workflows.

What dependencies does OpenSTEF have?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Core dependencies include:

- **pandas**: Data manipulation and time series handling
- **numpy**: Numerical computations
- **scikit-learn**: Data preprocessing and linear models
- **pydantic**: Configuration validation

Optional dependencies:

- **xgboost**: Tree-based gradient boosting models (recommended for most use cases)
- **mlflow**: Experiment tracking and model registry
- **plotly**: Interactive visualization

The library uses a workspace structure where packages depend on each other: ``openstef-beam`` depends on ``openstef-models``, which depends on ``openstef-core``.

Models and Algorithms
----------------------

What forecasting models does OpenSTEF support?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides several model types:

**XGBoost models** (most commonly used):

- ``XGBoostForecaster``: Tree-based gradient boosting for complex patterns
- ``GBLinearForecaster``: Linear model using XGBoost's linear booster

**Ensemble models**:

- ``EnsembleForecaster``: Combines predictions from multiple models
- ``FallbackForecaster``: Uses backup models when primary models fail

**Specialized models**:

- ``ARIMAForecaster``: Classical time series model for baseline comparisons
- ``QuantileOptimizerForecaster``: Post-processes forecasts to optimize quantile predictions

The XGBoost-based models are recommended for most scenarios due to their strong performance and ability to handle non-linear relationships.

Which model should I use?
^^^^^^^^^^^^^^^^^^^^^^^^^^

Start with ``XGBoostForecaster`` for most energy forecasting tasks. It handles:

- Non-linear relationships between weather and load
- Interactions between features (e.g., temperature and time of day)
- Missing data through built-in imputation
- Multiple forecast horizons and quantiles

Use ``GBLinearForecaster`` when:

- You need interpretable coefficients
- Your relationships are primarily linear
- You have limited training data

Use ``EnsembleForecaster`` to combine multiple models for improved robustness.

Here's a basic example:

.. code-block:: python

   from openstef_models import XGBoostForecaster
   from openstef_models.hyperparams import XGBoostHyperParams
   from openstef_core.types import Quantile, LeadTime
   from datetime import timedelta

   # Configure the forecaster
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=XGBoostHyperParams(n_estimators=100, max_depth=6),
   )

   # Train and predict
   forecaster.fit(training_data)
   predictions = forecaster.predict(test_data)

What are quantiles and why use them?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Quantiles provide prediction intervals that capture forecast uncertainty. Instead of a single prediction, you get a range of likely outcomes.

For example, with quantiles [0.1, 0.5, 0.9]:

- **0.1 (10th percentile)**: Lower bound - actual value expected to exceed this 90% of the time
- **0.5 (50th percentile)**: Median prediction - most likely value
- **0.9 (90th percentile)**: Upper bound - actual value expected to be below this 90% of the time

This is critical for energy applications:

- **Grid operators** use upper bounds for capacity planning
- **Traders** use ranges for risk assessment
- **Building managers** use lower bounds for minimum load guarantees

OpenSTEF models generate all quantiles simultaneously using specialized loss functions optimized for energy forecasting.

Data and Features
-----------------

What data do I need?
^^^^^^^^^^^^^^^^^^^^

At minimum, you need:

- **Historical target data**: The variable you want to forecast (e.g., load, generation)
- **Timestamps**: Regular time series with consistent intervals
- **Weather forecasts**: Temperature, wind speed, radiation (for prediction time)

Optional but recommended:

- **Weather history**: Historical weather matching your target data
- **Energy prices**: Day-ahead electricity prices
- **Calendar features**: Holidays, day of week (automatically generated)

Data should be in a pandas DataFrame with a datetime index and 15-minute intervals (configurable).

How do I prepare my data?
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF uses dataset classes that validate and structure your data:

.. code-block:: python

   from openstef_core.datasets import TrainingDataset, ForecastInputDataset
   import pandas as pd
   from datetime import timedelta

   # Prepare training data
   training_df = pd.DataFrame({
       'load': [...],  # Your target variable
       'temperature': [...],
       'windspeed': [...],
       'radiation': [...],
   }, index=pd.DatetimeIndex([...]))  # Datetime index required

   training_data = TrainingDataset(
       data=training_df,
       sample_interval=timedelta(minutes=15),
       target_column='load'
   )

   # Prepare forecast input (includes future weather)
   forecast_df = pd.DataFrame({
       'temperature': [...],  # Weather forecasts
       'windspeed': [...],
       'radiation': [...],
       'horizon': [...],  # Hours ahead for each prediction
       'available_at': [...],  # When this forecast was available
   }, index=pd.DatetimeIndex([...]))

   forecast_input = ForecastInputDataset(
       data=forecast_df,
       sample_interval=timedelta(minutes=15),
       forecast_start=pd.Timestamp('2024-01-01 00:00:00')
   )

The dataset classes automatically validate required columns, check data frequency, and prepare features for the models.

What if I'm missing weather data?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF models handle missing data through:

- **Built-in imputation**: XGBoost can work with missing values
- **Feature engineering**: Creates lag features from historical data when weather is unavailable
- **Fallback models**: Use simpler models that require fewer features

However, forecast quality improves significantly with weather data, especially for:

- Solar generation (radiation is critical)
- Wind generation (wind speed is critical)
- Temperature-sensitive loads (heating/cooling)

If weather data is completely unavailable, consider using ``ARIMAForecaster`` or historical averages as baselines.

Workflows and Usage
-------------------

What is a workflow?
^^^^^^^^^^^^^^^^^^^

Workflows orchestrate the complete forecasting process: data preparation, feature engineering, model training, validation, and prediction. They handle the boilerplate code so you can focus on configuration.

The standard workflow:

.. code-block:: python

   from openstef_models.workflows import StandardForecastingWorkflow
   from openstef_models import XGBoostForecaster
   from openstef_core.types import Quantile as Q
   from datetime import timedelta

   # Configure workflow
   workflow = StandardForecastingWorkflow(
       forecaster=XGBoostForecaster(
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           horizons=[timedelta(hours=h) for h in [1, 6, 12, 24]],
       ),
       config=WorkflowConfig(
           target_column='load',
           predict_history=timedelta(days=14),
       )
   )

   # Train model
   result = workflow.fit(training_data)

   # Generate forecasts
   forecast = workflow.predict(forecast_input)

Workflows automatically handle feature engineering, train/validation splits, and metric calculation.

How do I evaluate forecast quality?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides comprehensive evaluation through workflows and backtesting:

.. code-block:: python

   # Training returns evaluation metrics
   result = workflow.fit(training_data)
   
   # View metrics for different horizons
   print(result.metrics_full.to_dataframe())

Common metrics include:

- **MAE (Mean Absolute Error)**: Average prediction error in original units
- **RMSE (Root Mean Squared Error)**: Penalizes large errors more heavily
- **Quantile Score**: Evaluates probabilistic forecast quality
- **Skill Score**: Compares against baseline models

For production validation, use backtesting to simulate real-world performance across multiple time periods.

Can I use OpenSTEF in production?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes. OpenSTEF is designed for production use and runs in Alliander's operational systems. Key features for production:

- **Model persistence**: Save and load trained models
- **MLflow integration**: Track experiments and manage model versions
- **Batch processing**: Process multiple forecasting targets with ``openstef-beam``
- **Monitoring**: Built-in callbacks for logging and alerting
- **Fallback handling**: Automatic failover to backup models

For production deployment, consider:

- Scheduling regular model retraining (weekly or monthly)
- Monitoring forecast accuracy and data quality
- Implementing alerting for prediction failures
- Versioning models and configurations

Common Issues
-------------

Why are my forecasts all the same value?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Common causes:

- **Insufficient training data**: XGBoost needs at least several weeks of data
- **Missing features**: Check that weather and calendar features are present
- **Data quality issues**: Verify your target variable has variation
- **Incorrect configuration**: Ensure quantiles and horizons are properly set

Check the training metrics - if training error is high, the model isn't learning patterns.

How much training data do I need?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Recommended minimums:

- **XGBoost models**: 6-12 months for capturing seasonal patterns
- **Linear models**: 3-6 months minimum
- **ARIMA models**: 2-3 months for daily patterns

More data generally improves forecast quality, especially for:

- Capturing rare events (extreme weather, holidays)
- Learning seasonal patterns (summer vs. winter)
- Improving quantile accuracy

Can I forecast multiple variables?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each forecaster instance predicts one target variable. To forecast multiple variables:

- Create separate forecaster instances for each target
- Use ``openstef-beam`` for efficient batch processing of multiple targets
- Share feature engineering pipelines across forecasters

The benchmarking framework in ``openstef-beam`` is specifically designed for managing multiple forecasting targets efficiently.

Getting Help
------------

For more detailed information:

- **Tutorials**: Step-by-step guides for common scenarios
- **User Guide**: In-depth explanations of concepts and features
- **API Reference**: Complete documentation of all classes and functions
- **GitHub Issues**: Report bugs or request features at https://github.com/OpenSTEF/openstef

The OpenSTEF community welcomes questions and contributions!