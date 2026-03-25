Tutorials
=========

This comprehensive tutorial guides you from your first OpenSTEF forecast through advanced customization techniques. OpenSTEF is a Python machine learning library designed for short-term energy forecasting, providing all components needed to build production-ready forecasting systems.

First Forecast with Maximum Presets
------------------------------------

The fastest way to understand OpenSTEF's capabilities is to create your first forecast using maximum presets. This approach handles most configuration automatically while demonstrating the complete machine learning pipeline.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects time series data with specific columns. The minimum required data includes load measurements and weather features:

.. code-block:: python

   import pandas as pd
   from openstef.pipeline import train_model, create_forecast
   from openstef.data_classes import PredictionJobDataClass
   
   # Load your data - must include 'load' column and weather features
   data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)
   
   # Verify required columns exist
   required_columns = ['load', 'temperature', 'windspeed_100m', 'radiation']
   print(f"Available columns: {data.columns.tolist()}")
   print(f"Data shape: {data.shape}")

Your data should be structured with datetime index and these key columns:

- ``load``: Energy consumption/generation measurements (required)
- ``temperature``: Temperature in Celsius
- ``windspeed_100m``: Wind speed at 100m height
- ``radiation``: Solar radiation
- Additional weather features enhance forecast accuracy

Training Your First Model
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a prediction job configuration and train a model using OpenSTEF's default settings:

.. code-block:: python

   # Create prediction job with maximum presets
   pj = PredictionJobDataClass(
       id=1,
       name="tutorial_forecast",
       forecast_type="demand",
       model="xgb",  # XGBoost with default hyperparameters
       horizon_minutes=2880,  # 48-hour forecast horizon
       resolution_minutes=15,  # 15-minute resolution
       train_components=False  # Disable energy splitting for simplicity
   )
   
   # Train the model using the pipeline
   trained_model = train_model.main(
       pj=pj,
       input_data=data
   )
   
   print(f"Model trained successfully: {type(trained_model)}")
   print(f"Model features: {trained_model.feature_names}")

The training pipeline automatically handles feature engineering, data validation, and model optimization using OpenSTEF's proven defaults.

Creating Your First Forecast
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate forecasts using the trained model:

.. code-block:: python

   # Create forecast for the next 48 hours
   forecast = create_forecast.main(
       pj=pj,
       model=trained_model,
       input_data=data
   )
   
   # Display forecast results
   print(f"Forecast shape: {forecast.shape}")
   print(f"Forecast columns: {forecast.columns.tolist()}")
   print(forecast.head())

The forecast includes point predictions and confidence intervals (quantiles) that indicate uncertainty ranges around the central prediction.

Evaluating Results
^^^^^^^^^^^^^^^^^^

Assess your model's performance using OpenSTEF's built-in metrics:

.. code-block:: python

   from openstef.metrics import metrics
   
   # Split data for evaluation (use last 20% as test set)
   split_point = int(len(data) * 0.8)
   test_data = data.iloc[split_point:]
   
   # Calculate key metrics
   mae = metrics.mean_absolute_error(test_data['load'], forecast['forecast'])
   rmse = metrics.root_mean_squared_error(test_data['load'], forecast['forecast'])
   mape = metrics.mean_absolute_percentage_error(test_data['load'], forecast['forecast'])
   
   print(f"Mean Absolute Error: {mae:.2f}")
   print(f"Root Mean Squared Error: {rmse:.2f}")
   print(f"Mean Absolute Percentage Error: {mape:.2f}%")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^

For demand forecasts, OpenSTEF can decompose total load into renewable and conventional components:

.. code-block:: python

   # Enable energy splitting in prediction job
   pj_with_splitting = PredictionJobDataClass(
       id=2,
       name="tutorial_with_splitting",
       forecast_type="demand",
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=15,
       train_components=True  # Enable energy splitting
   )
   
   # Train model with splitting enabled
   model_with_splitting = train_model.main(
       pj=pj_with_splitting,
       input_data=data
   )
   
   # Create forecast with components
   forecast_with_components = create_forecast.main(
       pj=pj_with_splitting,
       model=model_with_splitting,
       input_data=data
   )
   
   # View component forecasts
   component_columns = [col for col in forecast_with_components.columns 
                       if 'component' in col.lower()]
   print(f"Available components: {component_columns}")

This decomposition helps understand how solar, wind, and conventional demand contribute to total load patterns.

Backtesting with Liander 2024 Dataset
--------------------------------------

Backtesting evaluates model performance across historical periods, providing robust performance estimates. The Liander 2024 benchmark dataset offers a standardized evaluation framework.

Setting Up the Backtest
^^^^^^^^^^^^^^^^^^^^^^^^

Configure a backtest using OpenSTEF's benchmarking framework:

.. code-block:: python

   from openstef.pipeline import train_create_forecast_backtest
   from openstef.benchmarking.benchmarks.liander2024 import create_liander2024_benchmark_runner
   
   # Load Liander 2024 benchmark data
   benchmark_runner = create_liander2024_benchmark_runner()
   targets = benchmark_runner.target_provider.get_targets()
   
   # Select first target for demonstration
   target = targets[0]
   print(f"Backtesting target: {target.name}")
   print(f"Target category: {target.category}")

Comparing Two Models
^^^^^^^^^^^^^^^^^^^^

Compare XGBoost and Linear Regression models using the same dataset:

.. code-block:: python

   # Define two prediction jobs with different models
   pj_xgb = PredictionJobDataClass(
       id=10,
       name="backtest_xgb",
       forecast_type="demand",
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=15
   )
   
   pj_linear = PredictionJobDataClass(
       id=11,
       name="backtest_linear",
       model="linear",
       forecast_type="demand",
       horizon_minutes=2880,
       resolution_minutes=15
   )
   
   # Run backtest for both models
   backtest_results_xgb = train_create_forecast_backtest.main(
       pj=pj_xgb,
       input_data=target.data,
       backtest_months=6  # Test on 6 months of data
   )
   
   backtest_results_linear = train_create_forecast_backtest.main(
       pj=pj_linear,
       input_data=target.data,
       backtest_months=6
   )

Analyzing Backtest Results
^^^^^^^^^^^^^^^^^^^^^^^^^^

Compare model performance across different metrics and time periods:

.. code-block:: python

   # Calculate performance metrics for both models
   def analyze_backtest(results, model_name):
       mae = results['metrics']['mae']
       rmse = results['metrics']['rmse']
       skill_score = results['metrics']['skill_score']
       
       print(f"\n{model_name} Performance:")
       print(f"MAE: {mae:.2f}")
       print(f"RMSE: {rmse:.2f}")
       print(f"Skill Score: {skill_score:.3f}")
       
       return {'mae': mae, 'rmse': rmse, 'skill_score': skill_score}
   
   xgb_metrics = analyze_backtest(backtest_results_xgb, "XGBoost")
   linear_metrics = analyze_backtest(backtest_results_linear, "Linear Regression")
   
   # Determine better performing model
   if xgb_metrics['mae'] < linear_metrics['mae']:
       print("\nXGBoost performs better on MAE")
   else:
       print("\nLinear Regression performs better on MAE")

The backtest provides realistic performance estimates by training and testing on multiple time periods, revealing how models perform under different seasonal and operational conditions.

Advanced Customization
-----------------------

OpenSTEF's modular architecture enables extensive customization for specialized use cases. This section demonstrates key customization patterns for production deployments.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^^

Create custom target providers to integrate your specific data sources and forecasting targets:

.. code-block:: python

   from openstef.benchmarking.target_provider import TargetProvider
   from openstef.benchmarking.target import Target
   from typing import List
   
   class CustomTargetProvider(TargetProvider):
       """Custom target provider for your specific data sources."""
       
       def __init__(self, data_directory: str):
           self.data_directory = data_directory
           
       def get_targets(self, filter_args=None) -> List[Target]:
           """Load targets from your data sources."""
           targets = []
           
           # Example: Load from your database or file system
           for location_id in self._get_location_ids():
               data = self._load_location_data(location_id)
               target = Target(
                   id=location_id,
                   name=f"Location_{location_id}",
                   data=data,
                   category="demand"
               )
               targets.append(target)
               
           return targets
           
       def _get_location_ids(self):
           # Implement your logic to discover available locations
           return [1, 2, 3, 4, 5]
           
       def _load_location_data(self, location_id):
           # Implement your data loading logic
           # Return pandas DataFrame with required columns
           pass
   
   # Use custom target provider
   custom_provider = CustomTargetProvider("/path/to/your/data")
   targets = custom_provider.get_targets()

Custom Workflow Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build custom workflows that integrate OpenSTEF components with your existing systems:

.. code-block:: python

   from openstef.feature_engineering.data_preparation import AbstractDataPreparation
   from openstef.model.model_creator import ModelCreator
   import logging
   
   class CustomForecastingWorkflow:
       """Custom workflow integrating OpenSTEF with external systems."""
       
       def __init__(self, config):
           self.config = config
           self.logger = logging.getLogger(__name__)
           
       def run_forecast_pipeline(self, prediction_job, raw_data):
           """Complete forecasting pipeline with custom preprocessing."""
           
           # Step 1: Custom data validation and cleaning
           validated_data = self._validate_and_clean_data(raw_data)
           
           # Step 2: Apply OpenSTEF feature engineering
           data_prep = self._get_data_preparation(prediction_job)
           features_data = data_prep.prepare_train_data(validated_data)
           
           # Step 3: Train or load model
           model = self._get_or_train_model(prediction_job, features_data)
           
           # Step 4: Generate forecast
           forecast_data = data_prep.prepare_forecast_data(validated_data)
           forecast = model.predict(forecast_data)
           
           # Step 5: Custom post-processing
           final_forecast = self._apply_business_rules(forecast, prediction_job)
           
           # Step 6: Store results in your systems
           self._store_forecast(final_forecast, prediction_job)
           
           return final_forecast
           
       def _validate_and_clean_data(self, data):
           # Implement your data quality checks
           self.logger.info("Applying custom data validation")
           return data
           
       def _apply_business_rules(self, forecast, pj):
           # Apply domain-specific constraints
           self.logger.info("Applying business rules to forecast")
           return forecast
           
       def _store_forecast(self, forecast, pj):
           # Store in your database/API
           self.logger.info(f"Storing forecast for job {pj.id}")

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering with domain-specific features:

.. code-block:: python

   from openstef.feature_engineering.feature_adder import FeatureAdder
   import pandas as pd
   import numpy as np
   
   class IndustrySpecificFeatures(FeatureAdder):
       """Custom features for industrial energy forecasting."""
       
       @property
       def name(self):
           return "industry_features"
           
       def apply_features(self, data: pd.DataFrame) -> pd.DataFrame:
           """Add industry-specific features to the dataset."""
           
           # Production schedule features
           data = self._add_production_schedule_features(data)
           
           # Equipment maintenance indicators
           data = self._add_maintenance_features(data)
           
           # Market price sensitivity features
           data = self._add_price_features(data)
           
           return data
           
       def _add_production_schedule_features(self, data):
           """Add features based on production schedules."""
           # Example: Binary indicator for planned production periods
           data['planned_production'] = 0  # Default to no production
           
           # Set production periods based on your business logic
           business_hours = (data.index.hour >= 6) & (data.index.hour <= 18)
           weekdays = data.index.weekday < 5
           data.loc[business_hours & weekdays, 'planned_production'] = 1
           
           return data
           
       def _add_maintenance_features(self, data):
           """Add maintenance schedule indicators."""
           # Example: Planned maintenance reduces capacity
           data['maintenance_factor'] = 1.0  # Default to full capacity
           
           # Implement your maintenance schedule logic
           # data.loc[maintenance_periods, 'maintenance_factor'] = 0.7
           
           return data
           
       def _add_price_features(self, data):
           """Add energy price-related features."""
           if 'electricity_price' in data.columns:
               # Price volatility features
               data['price_volatility'] = data['electricity_price'].rolling(24).std()
               
               # Price quantile features
               data['price_percentile'] = data['electricity_price'].rolling(168).rank(pct=True)
               
           return data
   
   # Register and use custom features
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   
   # Create prediction job with custom features
   pj_custom = PredictionJobDataClass(
       id=20,
       name="industrial_forecast",
       forecast_type="demand",
       model="xgb",
       horizon_minutes=1440,  # 24-hour horizon
       resolution_minutes=60,  # Hourly resolution
       feature_modules=["industry_features"]  # Use custom features
   )

These customization examples demonstrate OpenSTEF's flexibility for production deployments. The library's modular design allows you to replace or extend any component while maintaining compatibility with the core forecasting pipeline.

.. note::
   For additional examples and detailed API documentation, see the API reference section. The how-to guides provide specific implementation guidance for common deployment scenarios.