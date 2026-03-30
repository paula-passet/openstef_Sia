Tutorials
=========

This page provides comprehensive tutorials to help you move from basic OpenSTEF usage to production-ready implementations. Each tutorial builds on the previous one, starting with a complete first-use example and progressing to advanced customization techniques.

First Use Tutorial
------------------

This tutorial demonstrates the complete OpenSTEF workflow using maximum presets to minimize configuration complexity. You'll learn to load data, train a model, create forecasts, evaluate results, and perform energy split decomposition.

Setting Up Your First Prediction Job
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF organizes forecasting tasks using prediction jobs, which define all the parameters needed for training and forecasting:

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Define your first prediction job with sensible defaults
   pj = PredictionJobDataClass(
       id=1,
       model='xgb',  # XGBoost with default hyperparameters
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],  # Probabilistic forecasts
       horizon_minutes=24*60,  # 24-hour forecast horizon
       resolution_minutes=15,  # 15-minute intervals
       save_train_forecasts=True,  # Enable model evaluation on training data
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       name="My_First_Forecast"
   )

Loading and Preparing Your Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects time-series data with a datetime index and at minimum a 'load' column containing your target values:

.. code-block:: python

   import pandas as pd
   import numpy as np
   
   # Load your data (CSV with datetime index)
   input_data = pd.read_csv('your_data.csv', parse_dates=True, index_col=0)
   
   # Split data for training and testing
   test_days = 2
   test_rows = test_days * 24 * 4  # 15-minute intervals
   
   train_data = input_data.iloc[:-test_rows]
   test_data = input_data.iloc[-test_rows:]
   
   # Prepare forecast data (set future load values to NaN)
   to_forecast_data = input_data.copy(deep=True)
   to_forecast_data.loc[test_data.index, 'load'] = np.nan

Training Your Model
^^^^^^^^^^^^^^^^^^^

Use OpenSTEF's training pipeline to automatically handle feature engineering, model training, and validation:

.. code-block:: python

   import openstef.pipeline.train_model
   
   # Train model with automatic feature engineering
   trained_model, model_specs, report = openstef.pipeline.train_model.train_pipeline_common(
       pj=pj,
       input_data=train_data,
       mlflow_tracking_uri="./mlflow_models"  # Local model storage
   )
   
   print(f"Model training completed. RMSE: {report['rmse']:.2f}")

Creating Forecasts
^^^^^^^^^^^^^^^^^^

Generate probabilistic forecasts using your trained model:

.. code-block:: python

   import openstef.pipeline.create_forecast
   
   # Create forecast for the test period
   forecast = openstef.pipeline.create_forecast.create_forecast_pipeline_core(
       pj=pj,
       input_data=to_forecast_data,
       mlflow_tracking_uri="./mlflow_models"
   )
   
   # Display forecast results
   print(forecast.head())
   print(f"Forecast covers {len(forecast)} time steps")

Evaluating Results
^^^^^^^^^^^^^^^^^^

Assess forecast quality using OpenSTEF's built-in evaluation metrics:

.. code-block:: python

   from openstef.validation.validation import calc_forecast_quality
   
   # Compare forecast with actual values
   realized_values = input_data.loc[test_data.index, 'load']
   
   # Calculate comprehensive quality metrics
   quality_metrics = calc_forecast_quality(
       forecast=forecast['forecast'],
       realized=realized_values,
       quantiles=pj.quantiles
   )
   
   print(f"MAE: {quality_metrics['MAE']:.2f}")
   print(f"RMSE: {quality_metrics['RMSE']:.2f}")
   print(f"Bias: {quality_metrics['bias']:.2f}")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^

Understand forecast components by analyzing feature contributions:

.. code-block:: python

   from openstef.feature_engineering.apply_features import apply_features
   
   # Generate features for analysis
   features_df = apply_features(
       df=input_data,
       pj=pj,
       sid=pj.id
   )
   
   # Analyze weather dependency
   weather_features = [col for col in features_df.columns if 'T-1d' in col or 'windspeed' in col]
   print(f"Weather-related features: {len(weather_features)}")
   
   # Feature importance from trained model
   if hasattr(trained_model, 'feature_importances_'):
       feature_importance = dict(zip(features_df.columns, trained_model.feature_importances_))
       top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
       print("Top 10 most important features:")
       for feature, importance in top_features:
           print(f"  {feature}: {importance:.3f}")

Backtesting Tutorial
--------------------

This tutorial demonstrates how to perform systematic backtesting using the Liander 2024 benchmark dataset, comparing multiple models to assess relative performance.

Setting Up Benchmark Comparison
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides standardized benchmark datasets for reproducible model comparison:

.. code-block:: python

   from openstef_beam.backtesting import BacktestConfig, BenchmarkPipeline
   from openstef_beam.evaluation import EvaluationConfig
   from openstef_beam.analysis import AnalysisConfig
   from datetime import datetime, timedelta
   
   # Configure backtesting parameters
   backtest_config = BacktestConfig(
       start_date=datetime(2024, 1, 1),
       end_date=datetime(2024, 12, 31),
       window_size=timedelta(days=365),  # Training window
       window_step=timedelta(days=1),    # Daily re-training
       forecast_horizon_hours=48
   )
   
   # Configure evaluation metrics
   evaluation_config = EvaluationConfig(
       metrics=['MAE', 'RMSE', 'MAPE', 'bias'],
       quantile_metrics=['coverage', 'sharpness']
   )

Comparing Multiple Models
^^^^^^^^^^^^^^^^^^^^^^^^^

Set up model factories to test different algorithms systematically:

.. code-block:: python

   def create_xgboost_forecaster(context, target):
       """Factory for XGBoost models with target-specific tuning."""
       return PredictionJobDataClass(
           id=target.id,
           model='xgb',
           quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
           horizon_minutes=48*60,
           resolution_minutes=15,
           forecast_type=target.forecast_type,
           lat=target.latitude,
           lon=target.longitude,
           name=f"xgb_{target.name}"
       )
   
   def create_linear_forecaster(context, target):
       """Factory for linear models as baseline comparison."""
       return PredictionJobDataClass(
           id=target.id,
           model='linear',
           quantiles=[0.50],  # Point forecasts only
           horizon_minutes=48*60,
           resolution_minutes=15,
           forecast_type=target.forecast_type,
           lat=target.latitude,
           lon=target.longitude,
           name=f"linear_{target.name}"
       )

Running Benchmark Comparison
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Execute the benchmark pipeline with parallel processing for efficiency:

.. code-block:: python

   from openstef_beam.benchmarking.target_providers import Liander2024TargetProvider
   
   # Initialize benchmark data provider
   target_provider = Liander2024TargetProvider(
       data_path="./benchmark_data/liander_2024"
   )
   
   # Create benchmark pipeline
   pipeline = BenchmarkPipeline(
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       target_provider=target_provider
   )
   
   # Run XGBoost benchmark
   xgb_results = pipeline.run(
       forecaster_factory=create_xgboost_forecaster,
       run_name="liander_2024_xgboost",
       n_processes=4
   )
   
   # Run linear model benchmark
   linear_results = pipeline.run(
       forecaster_factory=create_linear_forecaster,
       run_name="liander_2024_linear",
       n_processes=4
   )

Analyzing Benchmark Results
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compare model performance across different targets and time periods:

.. code-block:: python

   from openstef_beam.analysis import compare_benchmark_results
   
   # Generate comparison report
   comparison = compare_benchmark_results([
       ("XGBoost", xgb_results),
       ("Linear", linear_results)
   ])
   
   # Display aggregate performance
   print("Average MAE by model:")
   print(comparison.groupby('model')['MAE'].mean().sort_values())
   
   # Analyze performance by target characteristics
   print("\nPerformance by target group:")
   performance_by_group = comparison.groupby(['model', 'target_group']).agg({
       'MAE': 'mean',
       'RMSE': 'mean',
       'coverage_50': 'mean'
   })
   print(performance_by_group)

Advanced Customization Tutorial
-------------------------------

This tutorial covers advanced OpenSTEF customization for production deployments, including custom target providers, workflow modifications, and feature engineering extensions.

Creating Custom Target Providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Target providers enable OpenSTEF to work with diverse data sources and organizational structures:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider
   from openstef_beam.benchmarking.models.benchmark_target import BenchmarkTarget
   from pathlib import Path
   import pandas as pd
   
   class CustomEnergyProvider(TargetProvider):
       """Custom provider for company-specific energy data."""
       
       def __init__(self, database_config, region_filter=None):
           super().__init__()
           self.db_config = database_config
           self.region_filter = region_filter
       
       def get_targets(self, filter_args=None):
           """Load target definitions from company database."""
           # Connect to your data source
           targets = []
           
           # Example: Load from database or configuration
           target_configs = self._load_target_configs()
           
           for config in target_configs:
               if self.region_filter and config['region'] not in self.region_filter:
                   continue
                   
               target = BenchmarkTarget(
                   name=config['substation_id'],
                   description=f"Load forecast for {config['name']}",
                   group_name=config['region'],
                   latitude=config['lat'],
                   longitude=config['lon'],
                   forecast_type="demand",
                   metadata=config.get('metadata', {})
               )
               targets.append(target)
           
           return targets
       
       def get_measurements(self, target, start_date, end_date):
           """Retrieve historical load measurements."""
           query = f"""
           SELECT timestamp, load_mw as load
           FROM measurements 
           WHERE substation_id = '{target.name}'
           AND timestamp BETWEEN '{start_date}' AND '{end_date}'
           ORDER BY timestamp
           """
           
           df = pd.read_sql(query, self.db_config['connection'])
           df.set_index('timestamp', inplace=True)
           return df
       
       def get_predictors(self, target, start_date, end_date):
           """Retrieve predictor variables (weather, calendar, etc.)."""
           # Combine multiple data sources
           weather_df = self._get_weather_data(target, start_date, end_date)
           calendar_df = self._get_calendar_features(start_date, end_date)
           
           # Merge on datetime index
           predictors = weather_df.join(calendar_df, how='outer')
           return predictors

Implementing Custom Workflows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Customize OpenSTEF pipelines to integrate with existing MLOps infrastructure:

.. code-block:: python

   import mlflow
   from openstef.pipeline.train_model import train_pipeline_common
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core
   
   class ProductionWorkflow:
       """Custom workflow with company-specific requirements."""
       
       def __init__(self, mlflow_uri, model_registry, notification_service):
           self.mlflow_uri = mlflow_uri
           self.model_registry = model_registry
           self.notifications = notification_service
       
       def train_with_validation(self, pj, training_data, validation_data):
           """Enhanced training with custom validation logic."""
           
           # Set MLflow experiment
           mlflow.set_tracking_uri(self.mlflow_uri)
           mlflow.set_experiment(f"production_{pj.name}")
           
           with mlflow.start_run():
               # Train model
               model, specs, report = train_pipeline_common(
                   pj=pj,
                   input_data=training_data,
                   mlflow_tracking_uri=self.mlflow_uri
               )
               
               # Custom validation on held-out data
               validation_forecast = create_forecast_pipeline_core(
                   pj=pj,
                   input_data=validation_data,
                   mlflow_tracking_uri=self.mlflow_uri
               )
               
               # Calculate business-specific metrics
               business_metrics = self._calculate_business_metrics(
                   validation_forecast, 
                   validation_data
               )
               
               # Log custom metrics
               mlflow.log_metrics(business_metrics)
               
               # Model promotion logic
               if business_metrics['revenue_impact'] > self.promotion_threshold:
                   self._promote_model_to_production(model, pj)
                   self.notifications.send_success(pj.name, business_metrics)
               else:
                   self.notifications.send_warning(pj.name, business_metrics)
               
               return model, specs, report, business_metrics
       
       def _calculate_business_metrics(self, forecast, validation_data):
           """Calculate company-specific performance metrics."""
           # Example: Revenue impact, operational constraints, etc.
           return {
               'revenue_impact': 0.95,  # Custom calculation
               'constraint_violations': 2,
               'peak_accuracy': 0.88
           }

Advanced Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering with domain-specific predictors:

.. code-block:: python

   from openstef.feature_engineering.apply_features import apply_features
   import pandas as pd
   import numpy as np
   
   def apply_custom_features(df, pj, additional_features=None):
       """Enhanced feature engineering with custom predictors."""
       
       # Start with standard OpenSTEF features
       features_df = apply_features(df, pj, sid=pj.id)
       
       # Add custom business features
       if additional_features:
           # Economic indicators
           if 'economic' in additional_features:
               features_df = add_economic_features(features_df, pj)
           
           # Grid topology features
           if 'topology' in additional_features:
               features_df = add_topology_features(features_df, pj)
           
           # Demand response features
           if 'demand_response' in additional_features:
               features_df = add_demand_response_features(features_df, pj)
       
       return features_df
   
   def add_economic_features(df, pj):
       """Add economic indicators as predictors."""
       # Example: Electricity prices, industrial activity indices
       df['electricity_price_lag1d'] = df['electricity_price'].shift(24*4)  # 1 day lag
       df['industrial_index_ma7d'] = df['industrial_activity'].rolling(window=7*24*4).mean()
       
       # Price volatility
       df['price_volatility_24h'] = df['electricity_price'].rolling(window=24*4).std()
       
       return df
   
   def add_topology_features(df, pj):
       """Add grid topology-based features."""
       # Example: Neighboring substation loads, grid constraints
       if hasattr(pj, 'neighboring_stations'):
           for neighbor in pj.neighboring_stations:
               neighbor_col = f'neighbor_{neighbor}_load'
               if neighbor_col in df.columns:
                   df[f'{neighbor_col}_lag1h'] = df[neighbor_col].shift(4)  # 1 hour lag
                   df[f'{neighbor_col}_ratio'] = df['load'] / (df[neighbor_col] + 1e-6)
       
       return df
   
   def add_demand_response_features(df, pj):
       """Add demand response program features."""
       # Example: DR event indicators, price signals
       df['dr_event_active'] = (df['dr_signal'] > df['dr_threshold']).astype(int)
       df['dr_event_lag2h'] = df['dr_event_active'].shift(8)  # 2 hour lag
       
       # Price-responsive load estimation
       df['price_elasticity'] = df['load'].rolling(window=24*4).corr(df['electricity_price'])
       
       return df

Integration Example
^^^^^^^^^^^^^^^^^^^

Combine all customizations in a complete production pipeline:

.. code-block:: python

   # Initialize custom components
   target_provider = CustomEnergyProvider(
       database_config={'connection': db_connection},
       region_filter=['north', 'central']
   )
   
   workflow = ProductionWorkflow(
       mlflow_uri="http://mlflow-server:5000",
       model_registry=model_registry,
       notification_service=slack_notifier
   )
   
   # Execute custom pipeline
   for target in target_provider.get_targets():
       # Load data
       measurements = target_provider.get_measurements(target, start_date, end_date)
       predictors = target_provider.get_predictors(target, start_date, end_date)
       
       # Combine data
       input_data = measurements.join(predictors, how='outer')
       
       # Create prediction job
       pj = PredictionJobDataClass(
           id=target.id,
           model='xgb',
           quantiles=[0.10, 0.50, 0.90],
           horizon_minutes=24*60,
           resolution_minutes=15,
           forecast_type=target.forecast_type,
           lat=target.latitude,
           lon=target.longitude,
           name=target.name
       )
       
       # Apply custom feature engineering
       enhanced_data = apply_custom_features(
           input_data, 
           pj, 
           additional_features=['economic', 'topology', 'demand_response']
       )
       
       # Train with custom workflow
       model, specs, report, metrics = workflow.train_with_validation(
           pj, enhanced_data, validation_data
       )

.. note::
   These tutorials provide comprehensive examples for different skill levels. For simpler getting-started scenarios, see the :doc:`quickstart` guide. For specific implementation tasks, consult the :doc:`../guides/how_to_guides`.