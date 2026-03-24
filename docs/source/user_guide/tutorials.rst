Tutorials
=========

This comprehensive tutorial guide covers everything from your first forecast to advanced customization. Each section builds on the previous one, so we recommend following them in order if you're new to OpenSTEF.

First Use Tutorial
------------------

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF requires time series data with specific columns to create forecasts. The library includes built-in validation to ensure your data meets the requirements.

**Required Data Schema:**

Your input data should be a pandas DataFrame with these essential columns:

- ``datetime``: Timestamp index (pandas DatetimeIndex)
- ``load``: The target variable you want to forecast (energy load values)
- Weather predictors (temperature, wind speed, solar irradiation, etc.)
- Calendar features (automatically generated if not provided)

.. code-block:: python

    import pandas as pd
    from openstef.data_classes.prediction_job import PredictionJob
    from openstef.pipeline.train_model import train_model_pipeline
    
    # Load your data
    data = pd.read_csv('your_energy_data.csv', parse_dates=['datetime'], index_col='datetime')
    
    # Verify required columns
    required_columns = ['load']  # Weather columns added automatically if available
    assert all(col in data.columns for col in required_columns)

**Data Validation:**

OpenSTEF automatically validates your data during training and prediction:

.. code-block:: python

    from openstef.validation.validation import validate_data
    
    # Validation happens automatically, but you can run it manually
    validation_result = validate_data(data)
    if not validation_result.is_valid:
        print("Data validation issues:", validation_result.errors)

**Common Data Sources:**

- CSV files with timestamp and load columns
- Time series databases (InfluxDB, TimescaleDB)
- Weather APIs combined with load measurements
- SCADA systems for grid measurements

Training a Model
^^^^^^^^^^^^^^^^

Training in OpenSTEF centers around the ``PredictionJob`` configuration object, which defines what and how to forecast.

**Basic Model Training:**

.. code-block:: python

    from openstef.data_classes.prediction_job import PredictionJob
    from openstef.pipeline.train_model import train_model_pipeline
    
    # Create a prediction job configuration
    pj = PredictionJob(
        id=1,
        name="my_first_forecast",
        model="xgb",  # XGBoost model
        quantiles=[0.1, 0.5, 0.9],  # Probabilistic forecast
        horizon_minutes=2880,  # 48 hours ahead
        resolution_minutes=15,  # 15-minute intervals
    )
    
    # Train the model
    trained_model = train_model_pipeline(pj, data)

**Model Types Available:**

- ``xgb``: XGBoost (recommended for most use cases)
- ``lgb``: LightGBM (faster training, similar performance)
- ``linear``: Linear regression (interpretable, good baseline)

**Training Parameters:**

.. code-block:: python

    # Advanced training configuration
    pj = PredictionJob(
        id=1,
        name="advanced_forecast",
        model="xgb",
        quantiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
        horizon_minutes=1440,  # 24 hours
        resolution_minutes=15,
        train_components_separately=False,  # Set True for component forecasting
        feature_names=["load", "temp", "windspeed"],  # Specify features
    )

Creating a Forecast
^^^^^^^^^^^^^^^^^^^

Once you have a trained model, creating forecasts is straightforward:

.. code-block:: python

    from openstef.pipeline.create_forecast import create_forecast_pipeline
    
    # Create forecast using the trained model
    forecast = create_forecast_pipeline(
        pj, 
        trained_model, 
        data  # Recent data for context
    )
    
    # Forecast is a DataFrame with columns for each quantile
    print(forecast.head())
    #                      forecast_0.1  forecast_0.5  forecast_0.9
    # 2024-01-01 00:00:00          45.2          52.1          59.8
    # 2024-01-01 00:15:00          44.8          51.7          59.2

**Understanding Probabilistic Forecasts:**

OpenSTEF provides quantile forecasts, not just point predictions:

- ``forecast_0.1``: 10th percentile (low estimate)
- ``forecast_0.5``: 50th percentile (median/most likely)
- ``forecast_0.9``: 90th percentile (high estimate)

This gives you uncertainty bounds around your predictions.

Evaluating Performance
^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes comprehensive evaluation metrics:

.. code-block:: python

    from openstef.metrics.reporter import Report
    
    # Create evaluation report
    report = Report(forecast, actual_data, pj)
    
    # Get key metrics
    mae = report.get_mae()  # Mean Absolute Error
    rmse = report.get_rmse()  # Root Mean Square Error
    bias = report.get_bias()  # Forecast bias
    
    print(f"MAE: {mae:.2f}")
    print(f"RMSE: {rmse:.2f}")
    print(f"Bias: {bias:.2f}")

**Visualization:**

.. code-block:: python

    import matplotlib.pyplot as plt
    
    # Plot forecast vs actual
    plt.figure(figsize=(12, 6))
    plt.plot(forecast.index, forecast['forecast_0.5'], label='Forecast (median)')
    plt.fill_between(forecast.index, 
                     forecast['forecast_0.1'], 
                     forecast['forecast_0.9'], 
                     alpha=0.3, label='80% confidence interval')
    plt.plot(actual_data.index, actual_data['load'], label='Actual', alpha=0.7)
    plt.legend()
    plt.title('Energy Load Forecast')
    plt.show()

Energy Split (Optional)
^^^^^^^^^^^^^^^^^^^^^^^

For some use cases, you may want to forecast energy components separately (solar, wind, base load):

.. code-block:: python

    # Enable component forecasting
    pj = PredictionJob(
        id=1,
        name="component_forecast",
        model="xgb",
        train_components_separately=True,  # Key setting
        quantiles=[0.1, 0.5, 0.9],
    )
    
    # Your data should include component columns
    # e.g., 'solar', 'wind', 'baseload' in addition to total 'load'

This is useful when you need to understand the contribution of different energy sources to total demand.

Backtesting
-----------

What Backtesting Tests
^^^^^^^^^^^^^^^^^^^^^^

Backtesting evaluates how well your model would have performed on historical data by simulating real-world forecasting conditions. It tests model quality over time and helps identify:

- Seasonal performance variations
- Model degradation over time  
- Optimal retraining frequency
- Comparative performance between different models

**How Backtesting Works:**

1. Split historical data into training and testing periods
2. Train model on early data
3. Generate forecasts for later periods
4. Compare forecasts against actual values
5. Repeat across multiple time windows

Running a Backtest
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from openstef.pipeline.create_backtest import create_backtest_pipeline
    
    # Define backtest parameters
    backtest_config = {
        'start_date': '2023-01-01',
        'end_date': '2023-12-31', 
        'train_window_days': 365,  # Use 1 year of data for training
        'test_window_days': 30,    # Test on 30-day periods
        'step_days': 7,            # Move forward 1 week each iteration
    }
    
    # Run backtest
    backtest_results = create_backtest_pipeline(
        pj, 
        data, 
        **backtest_config
    )

Interpreting Backtest Results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Analyze backtest performance
    from openstef.metrics.reporter import BacktestReport
    
    report = BacktestReport(backtest_results)
    
    # Overall metrics
    print(f"Average MAE: {report.get_average_mae():.2f}")
    print(f"MAE Standard Deviation: {report.get_mae_std():.2f}")
    
    # Performance over time
    monthly_performance = report.get_monthly_breakdown()
    print(monthly_performance)
    
    # Identify best/worst periods
    worst_month = report.get_worst_performing_period()
    print(f"Worst performing period: {worst_month}")

**Key Metrics to Monitor:**

- **Consistency**: Low standard deviation in MAE across periods
- **Seasonal patterns**: Performance variations by month/season
- **Trend**: Whether performance degrades over time
- **Quantile performance**: How well uncertainty estimates perform

Advanced Topics
---------------

Custom TargetProvider
^^^^^^^^^^^^^^^^^^^^^^

When you need to fetch data from custom sources or apply specific preprocessing:

.. code-block:: python

    from openstef.data_classes.model_input import ModelInput
    from openstef.pipeline.train_model import train_model_pipeline
    
    class CustomTargetProvider:
        def __init__(self, data_source):
            self.data_source = data_source
            
        def get_model_input(self, pj: PredictionJob) -> ModelInput:
            # Custom logic to fetch and prepare data
            raw_data = self.data_source.fetch_data(pj.id)
            processed_data = self.preprocess_data(raw_data)
            
            return ModelInput(
                data=processed_data,
                prediction_job=pj
            )
        
        def preprocess_data(self, data):
            # Your custom preprocessing logic
            return data
    
    # Use custom provider
    provider = CustomTargetProvider(your_data_source)
    model_input = provider.get_model_input(pj)
    trained_model = train_model_pipeline(pj, model_input.data)

Custom Workflows
^^^^^^^^^^^^^^^^

Extending the default training and inference workflows:

.. code-block:: python

    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.feature_engineering.feature_applicator import FeatureApplicator
    
    def custom_training_workflow(pj, data):
        # Custom preprocessing
        data = apply_custom_filters(data)
        
        # Custom feature engineering
        feature_applicator = FeatureApplicator()
        data = feature_applicator.add_custom_features(data, pj)
        
        # Standard training
        model = train_model_pipeline(pj, data)
        
        # Custom post-processing
        model = apply_custom_model_adjustments(model)
        
        return model
    
    def apply_custom_filters(data):
        # Remove outliers, handle missing data, etc.
        return data.dropna()
    
    def apply_custom_model_adjustments(model):
        # Model-specific adjustments
        return model

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adding domain-specific features to improve forecast accuracy:

.. code-block:: python

    from openstef.feature_engineering.feature_applicator import FeatureApplicator
    
    class CustomFeatureApplicator(FeatureApplicator):
        def add_features(self, data, pj):
            # Start with standard features
            data = super().add_features(data, pj)
            
            # Add custom features
            data = self.add_holiday_effects(data)
            data = self.add_industrial_schedule_features(data)
            data = self.add_weather_interaction_features(data)
            
            return data
        
        def add_holiday_effects(self, data):
            # Custom holiday calendar effects
            data['is_local_holiday'] = self.check_local_holidays(data.index)
            data['days_to_holiday'] = self.calculate_days_to_holiday(data.index)
            return data
        
        def add_industrial_schedule_features(self, data):
            # Industry-specific patterns
            data['industrial_shift_pattern'] = self.get_shift_patterns(data.index)
            return data
        
        def add_weather_interaction_features(self, data):
            # Weather interaction terms
            if 'temp' in data.columns and 'humidity' in data.columns:
                data['temp_humidity_interaction'] = data['temp'] * data['humidity']
            return data

**Best Practices for Custom Features:**

- Test feature importance after adding custom features
- Validate that new features don't cause overfitting
- Document custom features for model interpretability
- Consider computational cost in production environments

.. note::
   Custom workflows and features should be thoroughly tested with backtesting before deployment to production systems.