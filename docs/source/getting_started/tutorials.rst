Tutorials
=========

This comprehensive tutorial takes you from your first OpenSTEF model to production-ready implementations. Whether you're exploring the library's capabilities or preparing for deployment, these examples demonstrate the complete forecasting workflow with real-world scenarios.

First Steps with OpenSTEF
--------------------------

Let's start with a complete example that covers the essential OpenSTEF workflow: loading data, training a model, creating forecasts, and evaluating results.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.metrics import metrics
   
   # Set up plotting
   pd.options.plotting.backend = 'plotly'

First, define your prediction job with the model specifications:

.. code-block:: python

   # Define the forecasting task
   prediction_job = PredictionJobDataClass(
       id=307,
       name="Tutorial_Location",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       lat=52.132633,
       lon=5.291266,
       horizon_minutes=2880,  # 48 hours ahead
       train_components=["load", "weather", "apx"],
       quantiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
   )

Load your training data. OpenSTEF expects a DataFrame with datetime index and columns for load, weather variables, and market prices:

.. code-block:: python

   # Load training data from CSV
   training_data = pd.read_csv("energy_data.csv", index_col=0, parse_dates=True)
   
   # Data should include columns like:
   # - load: actual energy consumption/production
   # - T_2m: temperature at 2 meters
   # - windspeed_100m: wind speed at 100 meters  
   # - radiation: solar radiation
   # - apx: day-ahead electricity prices
   
   print(f"Training data shape: {training_data.shape}")
   print(f"Date range: {training_data.index.min()} to {training_data.index.max()}")

Train your model using the complete pipeline:

.. code-block:: python

   # Train the model
   trained_model, model_specs, report = train_model_pipeline(
       pj=prediction_job,
       input_data=training_data,
       mlflow_tracking_uri="./mlruns"
   )
   
   print(f"Model trained successfully: {trained_model}")
   print(f"Validation R²: {report['validation_score']:.3f}")

Create forecasts with your trained model:

.. code-block:: python

   # Prepare recent data for forecasting
   forecast_data = training_data.tail(200)  # Use recent data for context
   
   # Generate forecast
   forecast = create_forecast_pipeline(
       pj=prediction_job,
       input_data=forecast_data,
       mlflow_tracking_uri="./mlruns"
   )
   
   print(f"Forecast created with {len(forecast)} time steps")
   print(f"Forecast columns: {forecast.columns.tolist()}")

Evaluate your forecast results:

.. code-block:: python

   # Calculate forecast metrics (assuming you have actual values)
   if 'load' in forecast.columns:
       mae = metrics.mean_absolute_error(forecast['load'], forecast['forecast'])
       rmse = metrics.root_mean_squared_error(forecast['load'], forecast['forecast'])
       
       print(f"Mean Absolute Error: {mae:.2f}")
       print(f"Root Mean Squared Error: {rmse:.2f}")
       
       # Visualize results
       fig = forecast[['load', 'forecast']].plot(
           title="Forecast vs Actual Load",
           labels={'value': 'Load (MW)', 'index': 'Time'}
       )
       fig.show()

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF can decompose energy forecasts into renewable components, helping you understand the contribution of solar and wind generation:

.. code-block:: python

   from openstef.tasks.split_forecast import find_components
   
   # Perform energy splitting on forecast results
   components, coefficients = find_components(
       df=forecast,
       zero_bound=True  # Ensure non-negative components
   )
   
   print("Energy split coefficients:")
   for component, coef in coefficients.items():
       print(f"  {component}: {coef:.3f}")
   
   # Visualize the decomposition
   components_plot = components[['solar_component', 'wind_component']].plot(
       title="Renewable Energy Components",
       labels={'value': 'Power (MW)', 'index': 'Time'}
   )
   components_plot.show()

Backtesting with Multiple Models
---------------------------------

Backtesting simulates how your models would have performed in real operational conditions. Here's an example using the Liander 2024 benchmark dataset with two different models:

.. code-block:: python

   from openstef.pipeline.train_create_forecast_backtest import train_model_and_forecast_back_test
   from openstef_beam.benchmarking.benchmarks.liander2024 import create_liander2024_benchmark_runner
   import openstef.metrics.metrics as openstef_metrics
   
   # Define two models to compare
   xgb_job = PredictionJobDataClass(
       id=1,
       name="XGBoost_Model",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       lat=52.132633,
       lon=5.291266,
       horizon_minutes=2880,
       train_components=["load", "weather", "apx"]
   )
   
   lgb_job = PredictionJobDataClass(
       id=2,
       name="LightGBM_Model", 
       model="lgb",
       resolution_minutes=15,
       forecast_type="demand",
       lat=52.132633,
       lon=5.291266,
       horizon_minutes=2880,
       train_components=["load", "weather", "apx"]
   )

Run backtests for both models:

.. code-block:: python

   # Backtest configuration
   backtest_start = pd.Timestamp("2023-01-01")
   backtest_end = pd.Timestamp("2023-12-31")
   
   # Run backtest for XGBoost
   xgb_results = train_model_and_forecast_back_test(
       pj=xgb_job,
       input_data=training_data,
       start_date=backtest_start,
       end_date=backtest_end,
       retrain_frequency_days=30
   )
   
   # Run backtest for LightGBM  
   lgb_results = train_model_and_forecast_back_test(
       pj=lgb_job,
       input_data=training_data,
       start_date=backtest_start,
       end_date=backtest_end,
       retrain_frequency_days=30
   )

Compare model performance:

.. code-block:: python

   # Calculate metrics for both models
   xgb_mae = openstef_metrics.mean_absolute_error(
       xgb_results['load'], xgb_results['forecast']
   )
   lgb_mae = openstef_metrics.mean_absolute_error(
       lgb_results['load'], lgb_results['forecast']
   )
   
   print("Backtest Results:")
   print(f"XGBoost MAE: {xgb_mae:.2f}")
   print(f"LightGBM MAE: {lgb_mae:.2f}")
   
   # Visualize comparison
   comparison_df = pd.DataFrame({
       'XGBoost': xgb_results['forecast'],
       'LightGBM': lgb_results['forecast'],
       'Actual': xgb_results['load']
   })
   
   fig = comparison_df.plot(
       title="Model Comparison - Backtest Results",
       labels={'value': 'Load (MW)', 'index': 'Time'}
   )
   fig.show()

Using the Liander 2024 Benchmark
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For standardized comparison, use the Liander 2024 benchmark dataset:

.. code-block:: python

   from pathlib import Path
   
   # Set up benchmark runner
   benchmark_runner = create_liander2024_benchmark_runner(
       data_dir=Path("./liander2024_data"),
       storage=None  # Use default storage
   )
   
   # Run benchmark with your models
   benchmark_results = benchmark_runner.run_benchmark(
       models=[xgb_job, lgb_job],
       categories=["residential", "industrial"]  # Specify categories to test
   )
   
   print("Benchmark completed:")
   for result in benchmark_results:
       print(f"Model: {result.model_name}, Category: {result.category}")
       print(f"  MAE: {result.metrics['mae']:.2f}")
       print(f"  RMSE: {result.metrics['rmse']:.2f}")

Advanced Customization
----------------------

For production deployments, you'll often need to customize OpenSTEF's behavior. Here are examples of the most common customizations.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Create a custom target provider to load data from your specific data sources:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider, BenchmarkTarget
   from pathlib import Path
   import yaml
   
   class CustomTargetProvider(TargetProvider):
       """Custom target provider for your data infrastructure."""
       
       def __init__(self, config_dir: Path, data_dir: Path):
           self.config_dir = config_dir
           self.data_dir = data_dir
           
       def get_targets(self, filter_args=None):
           """Load targets from your configuration system."""
           targets = []
           
           for config_file in self.config_dir.glob("*.yaml"):
               with open(config_file) as f:
                   config = yaml.safe_load(f)
                   
               target = BenchmarkTarget(
                   name=config['name'],
                   prediction_job=PredictionJobDataClass(**config['prediction_job']),
                   data_path=self.data_dir / f"{config['name']}.parquet"
               )
               targets.append(target)
               
           return targets
           
       def get_metrics_for_target(self, target):
           """Define which metrics to calculate for each target."""
           from openstef_beam.metrics import mae, rmse, r2
           return [mae, rmse, r2]

Use your custom target provider:

.. code-block:: python

   # Initialize with your data locations
   custom_provider = CustomTargetProvider(
       config_dir=Path("./configs"),
       data_dir=Path("./datasets")
   )
   
   # Get all available targets
   targets = custom_provider.get_targets()
   print(f"Found {len(targets)} forecasting targets")

Custom Workflow
^^^^^^^^^^^^^^^

Build a custom workflow that integrates with your existing systems:

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import logging
   
   class CustomForecastWorkflow:
       """Custom workflow integrating OpenSTEF with your systems."""
       
       def __init__(self, mlflow_uri: str, notification_webhook: str = None):
           self.mlflow_uri = mlflow_uri
           self.notification_webhook = notification_webhook
           self.logger = logging.getLogger(__name__)
           
       def run_training_workflow(self, prediction_job, training_data):
           """Complete training workflow with error handling and notifications."""
           try:
               self.logger.info(f"Starting training for {prediction_job.name}")
               
               # Validate input data
               self._validate_training_data(training_data)
               
               # Train model
               model, specs, report = train_model_pipeline(
                   pj=prediction_job,
                   input_data=training_data,
                   mlflow_tracking_uri=self.mlflow_uri
               )
               
               # Check model quality
               if report['validation_score'] < 0.5:
                   raise ValueError(f"Model quality too low: {report['validation_score']}")
               
               self.logger.info(f"Training completed. R²: {report['validation_score']:.3f}")
               self._send_notification(f"Training successful for {prediction_job.name}")
               
               return model, specs, report
               
           except Exception as e:
               self.logger.error(f"Training failed: {e}")
               self._send_notification(f"Training failed for {prediction_job.name}: {e}")
               raise
               
       def run_forecast_workflow(self, prediction_job, input_data):
           """Complete forecast workflow with validation."""
           try:
               # Create forecast
               forecast = create_forecast_pipeline(
                   pj=prediction_job,
                   input_data=input_data,
                   mlflow_tracking_uri=self.mlflow_uri
               )
               
               # Validate forecast output
               self._validate_forecast(forecast)
               
               # Post-process if needed
               forecast = self._post_process_forecast(forecast, prediction_job)
               
               return forecast
               
           except Exception as e:
               self.logger.error(f"Forecast failed: {e}")
               raise
               
       def _validate_training_data(self, data):
           """Validate training data quality."""
           if data.isnull().sum().sum() / len(data) > 0.1:
               raise ValueError("Too many missing values in training data")
               
       def _validate_forecast(self, forecast):
           """Validate forecast output."""
           if forecast.isnull().any().any():
               raise ValueError("Forecast contains missing values")
               
       def _post_process_forecast(self, forecast, prediction_job):
           """Apply business rules and constraints."""
           # Example: Apply minimum/maximum constraints
           if 'forecast' in forecast.columns:
               forecast['forecast'] = forecast['forecast'].clip(lower=0)
           return forecast
           
       def _send_notification(self, message):
           """Send notification to monitoring system."""
           if self.notification_webhook:
               # Implement your notification logic here
               pass

Use your custom workflow:

.. code-block:: python

   # Initialize workflow
   workflow = CustomForecastWorkflow(
       mlflow_uri="./mlruns",
       notification_webhook="https://your-webhook-url.com"
   )
   
   # Run training
   model, specs, report = workflow.run_training_workflow(
       prediction_job=prediction_job,
       training_data=training_data
   )
   
   # Run forecasting
   forecast = workflow.run_forecast_workflow(
       prediction_job=prediction_job,
       input_data=forecast_data
   )

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering with domain-specific features:

.. code-block:: python

   from openstef.feature_engineering.general import apply_features
   import pandas as pd
   
   def add_custom_features(data: pd.DataFrame, prediction_job: PredictionJobDataClass) -> pd.DataFrame:
       """Add custom features specific to your use case."""
       
       # Apply standard OpenSTEF features first
       data = apply_features(data, prediction_job)
       
       # Add custom business calendar features
       data = add_business_calendar_features(data)
       
       # Add location-specific weather features
       data = add_weather_interactions(data, prediction_job.lat, prediction_job.lon)
       
       # Add market-based features
       data = add_market_features(data)
       
       return data
   
   def add_business_calendar_features(data: pd.DataFrame) -> pd.DataFrame:
       """Add business calendar features."""
       data['is_business_day'] = data.index.to_series().dt.dayofweek < 5
       data['days_until_weekend'] = (4 - data.index.to_series().dt.dayofweek).clip(lower=0)
       
       # Add holiday indicators (customize for your region)
       holidays = pd.to_datetime(['2024-01-01', '2024-12-25'])  # Add your holidays
       data['is_holiday'] = data.index.isin(holidays)
       
       return data
   
   def add_weather_interactions(data: pd.DataFrame, lat: float, lon: float) -> pd.DataFrame:
       """Add weather interaction features."""
       if 'T_2m' in data.columns and 'radiation' in data.columns:
           # Heat index approximation
           data['heat_index'] = data['T_2m'] + 0.1 * data['radiation']
           
           # Cooling/heating degree days
           data['cooling_degrees'] = (data['T_2m'] - 18).clip(lower=0)
           data['heating_degrees'] = (18 - data['T_2m']).clip(lower=0)
           
       return data
   
   def add_market_features(data: pd.DataFrame) -> pd.DataFrame:
       """Add electricity market features."""
       if 'apx' in data.columns:
           # Price volatility
           data['price_volatility'] = data['apx'].rolling(24).std()
           
           # High/low price indicators
           data['high_price'] = (data['apx'] > data['apx'].rolling(168).quantile(0.8)).astype(int)
           data['low_price'] = (data['apx'] < data['apx'].rolling(168).quantile(0.2)).astype(int)
           
       return data

Integrate custom features into your workflow:

.. code-block:: python

   # Modify your training data preparation
   def prepare_training_data(raw_data, prediction_job):
       """Prepare training data with custom features."""
       
       # Apply custom feature engineering
       processed_data = add_custom_features(raw_data, prediction_job)
       
       # Log feature statistics
       print(f"Features added: {len(processed_data.columns) - len(raw_data.columns)}")
       print(f"Final feature count: {len(processed_data.columns)}")
       
       return processed_data
   
   # Use in your training pipeline
   enhanced_training_data = prepare_training_data(training_data, prediction_job)
   
   model, specs, report = train_model_pipeline(
       pj=prediction_job,
       input_data=enhanced_training_data,
       mlflow_tracking_uri="./mlruns"
   )

.. note::
   These tutorials provide a foundation for using OpenSTEF in production environments. For deployment-specific guidance, see :doc:`../guides/how_to_guides`. For understanding the underlying concepts, refer to :doc:`../reference/concepts`.