Comprehensive Tutorials
=======================

This tutorial series takes you from your first OpenSTEF forecast through advanced customization for production deployment. Each section builds on the previous, moving from basic usage with maximum presets to sophisticated custom implementations.

Getting Started with Maximum Presets
-------------------------------------

The fastest way to understand OpenSTEF's capabilities is to use the maximum preset configuration. This approach handles most decisions automatically while demonstrating the complete forecasting workflow.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects time series data with specific columns. The library includes data validation and preparation utilities to ensure your data meets requirements::

   import pandas as pd
   from openstef.data_classes import PredictionJobDataClass
   from openstef.pipeline import train_model, create_forecast
   
   # Load your energy consumption data
   # Required columns: datetime (index), load, and weather features
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)
   
   # Create prediction job with maximum presets
   prediction_job = PredictionJobDataClass(
       id=1,
       name="tutorial_forecast",
       forecast_type="demand",
       model="xgb",  # XGBoost with quantile regression
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=15,  # 15-minute intervals
       train_components=True,  # Enable energy split decomposition
   )

Training Your First Model
^^^^^^^^^^^^^^^^^^^^^^^^^^

The train_model pipeline handles feature engineering, model training, and validation automatically::

   # Train model with automatic feature engineering
   model, model_specs, report = train_model.train_pipeline(
       pj=prediction_job,
       input_data=data,
       mlflow_tracking_uri=None,  # Use local storage
   )
   
   # The model is now ready for forecasting
   print(f"Model trained successfully: {model}")
   print(f"Feature importance: {model.feature_importances_}")

Creating Forecasts
^^^^^^^^^^^^^^^^^^^

Generate multi-horizon forecasts with confidence intervals using the trained model::

   # Create forecast for next 48 hours
   forecast_data = data.tail(100)  # Recent data for context
   
   forecast = create_forecast.create_forecast_pipeline_core(
       pj=prediction_job,
       input_data=forecast_data,
       model=model,
       model_specs=model_specs,
   )
   
   # Forecast includes quantiles for uncertainty estimation
   print(forecast.columns)  # ['forecast', 'quantile_P10', 'quantile_P90', ...]
   print(f"Next 24 hours peak: {forecast['forecast'].head(96).max():.2f}")

Evaluating Results
^^^^^^^^^^^^^^^^^^

OpenSTEF provides comprehensive evaluation metrics to assess forecast quality::

   from openstef.metrics import metrics
   
   # Split data for evaluation
   train_size = int(len(data) * 0.8)
   train_data = data[:train_size]
   test_data = data[train_size:]
   
   # Generate forecasts for test period
   test_forecasts = []
   for i in range(0, len(test_data) - 96, 96):  # Daily forecasts
       context_data = pd.concat([train_data.tail(100), test_data[i:i+96]])
       forecast = create_forecast.create_forecast_pipeline_core(
           pj=prediction_job,
           input_data=context_data,
           model=model,
           model_specs=model_specs,
       )
       test_forecasts.append(forecast)
   
   # Calculate evaluation metrics
   all_forecasts = pd.concat(test_forecasts)
   mae = metrics.mean_absolute_error(test_data['load'], all_forecasts['forecast'])
   rmse = metrics.root_mean_squared_error(test_data['load'], all_forecasts['forecast'])
   
   print(f"Mean Absolute Error: {mae:.2f}")
   print(f"Root Mean Squared Error: {rmse:.2f}")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

When `train_components=True`, OpenSTEF automatically decomposes forecasts into renewable and conventional components::

   from openstef.tasks.split_forecast import split_forecast_task
   
   # Energy splitting requires weather data columns
   # Ensure your data includes: wind_ref, pv_ref, temperature
   if prediction_job.train_components:
       # Split forecast into components
       split_result = split_forecast_task(prediction_job, data)
       
       print("Energy components:")
       print(f"Wind component: {split_result['wind_component'].sum():.2f}")
       print(f"Solar component: {split_result['pv_component'].sum():.2f}")
       print(f"Base load: {split_result['base_component'].sum():.2f}")

Backtesting with Liander 2024 Dataset
--------------------------------------

The Liander 2024 benchmark provides a standardized way to evaluate OpenSTEF performance across different energy system types. This section demonstrates backtesting with two different models.

Setting Up the Benchmark
^^^^^^^^^^^^^^^^^^^^^^^^^

::

   from openstef_beam.benchmarking.benchmarks.liander2024 import (
       create_liander2024_benchmark_runner,
       Liander2024Category
   )
   from pathlib import Path
   
   # Download benchmark data (instructions at openstef.org)
   data_dir = Path("liander2024_data")
   
   # Create benchmark runner
   benchmark = create_liander2024_benchmark_runner(
       data_dir=data_dir,
       storage=None,  # Use default storage
   )

Comparing Two Models
^^^^^^^^^^^^^^^^^^^^

Compare XGBoost and LightGBM performance across different energy system categories::

   # Define two model configurations
   xgb_job = PredictionJobDataClass(
       id=1,
       name="xgb_benchmark",
       model="xgb",
       forecast_type="demand",
       horizon_minutes=2880,
       resolution_minutes=15,
   )
   
   lgb_job = PredictionJobDataClass(
       id=2,
       name="lgb_benchmark", 
       model="lgb",
       forecast_type="demand",
       horizon_minutes=2880,
       resolution_minutes=15,
   )
   
   # Run benchmark for solar parks category
   solar_results = benchmark.run_benchmark(
       models=[xgb_job, lgb_job],
       categories=[Liander2024Category.SOLAR_PARKS],
   )
   
   # Compare results
   for model_name, results in solar_results.items():
       mae = results['metrics']['mae']
       rmse = results['metrics']['rmse']
       print(f"{model_name}: MAE={mae:.2f}, RMSE={rmse:.2f}")

Advanced Customization
----------------------

Production deployments often require custom components tailored to specific data sources, business logic, or integration requirements.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^^

Create custom target providers to integrate with your data infrastructure::

   from openstef_beam.benchmarking.target_provider import TargetProvider
   from typing import List
   
   class CustomTargetProvider(TargetProvider):
       """Custom target provider for company-specific data sources."""
       
       def __init__(self, database_config: dict):
           self.db_config = database_config
           
       def get_targets(self, filter_args=None) -> List[PredictionJobDataClass]:
           """Fetch prediction jobs from custom database."""
           # Connect to your database
           targets = []
           
           # Example: Load from custom configuration
           for location_id in self.get_active_locations():
               target = PredictionJobDataClass(
                   id=location_id,
                   name=f"location_{location_id}",
                   model="xgb",
                   forecast_type="demand",
                   horizon_minutes=2880,
                   resolution_minutes=15,
               )
               targets.append(target)
               
           return targets
           
       def get_data_for_target(self, target: PredictionJobDataClass) -> pd.DataFrame:
           """Fetch training data for specific target."""
           # Implement your data retrieval logic
           query = f"""
           SELECT datetime, load, temperature, wind_speed
           FROM energy_data 
           WHERE location_id = {target.id}
           ORDER BY datetime
           """
           return self.execute_query(query)

Custom Workflow Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Integrate OpenSTEF with workflow orchestration systems like Dagster or Airflow::

   from dagster import op, job, Config
   from openstef.pipeline import train_model, create_forecast
   
   class ForecastConfig(Config):
       location_id: int
       horizon_hours: int = 48
       
   @op
   def load_training_data(config: ForecastConfig) -> pd.DataFrame:
       """Load data from your data warehouse."""
       # Implement data loading logic
       return pd.read_sql(f"SELECT * FROM energy_data WHERE id={config.location_id}")
       
   @op 
   def train_forecast_model(data: pd.DataFrame, config: ForecastConfig):
       """Train OpenSTEF model."""
       prediction_job = PredictionJobDataClass(
           id=config.location_id,
           name=f"forecast_{config.location_id}",
           model="xgb",
           horizon_minutes=config.horizon_hours * 60,
       )
       
       model, specs, report = train_model.train_pipeline(
           pj=prediction_job,
           input_data=data,
       )
       
       return model, specs
       
   @op
   def generate_forecast(model_data, recent_data: pd.DataFrame):
       """Generate and store forecast."""
       model, specs = model_data
       forecast = create_forecast.create_forecast_pipeline_core(
           pj=prediction_job,
           input_data=recent_data,
           model=model,
           model_specs=specs,
       )
       
       # Store forecast in your system
       self.store_forecast(forecast)
       
   @job
   def daily_forecast_job():
       data = load_training_data()
       model_data = train_forecast_model(data)
       recent_data = load_recent_data()  # Another op
       generate_forecast(model_data, recent_data)

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering with domain-specific features::

   from openstef.feature_engineering.feature_adder import FeatureAdder
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   
   class CustomFeatureAdder(FeatureAdder):
       """Add custom business-specific features."""
       
       @property
       def name(self) -> str:
           return "custom_business_features"
           
       def apply_features(self, df: pd.DataFrame) -> pd.DataFrame:
           """Add custom features to dataframe."""
           # Add business day indicator
           df['is_business_day'] = df.index.to_series().apply(
               lambda x: x.weekday() < 5 and not self.is_holiday(x)
           )
           
           # Add peak/off-peak pricing periods
           df['peak_period'] = df.index.to_series().apply(
               lambda x: 7 <= x.hour <= 23 and df.loc[x, 'is_business_day']
           )
           
           # Add seasonal industrial patterns
           df['industrial_season'] = df.index.month.map({
               12: 'winter_shutdown', 1: 'winter_shutdown', 2: 'winter_shutdown',
               7: 'summer_vacation', 8: 'summer_vacation',
           }).fillna('normal_operation')
           
           return df
           
       def is_holiday(self, date) -> bool:
           """Check if date is a holiday (implement your logic)."""
           # Implement holiday detection for your region
           return False
   
   # Use custom features in pipeline
   custom_applicator = TrainFeatureApplicator(
       feature_modules=['openstef.feature_engineering', 'your_custom_module'],
       additional_adders=[CustomFeatureAdder()]
   )

Next Steps
----------

This tutorial covered OpenSTEF's core functionality from basic usage to advanced customization. For production deployment, consider:

- Review the how-to guides for deployment patterns and data integration
- Explore the use cases guide to identify the best approach for your specific application  
- Check the concepts reference for deeper understanding of forecasting principles
- Join the OpenSTEF community for support and best practices sharing

The library's modular design allows you to start simple and gradually add sophistication as your forecasting needs evolve.