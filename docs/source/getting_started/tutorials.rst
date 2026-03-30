Tutorials
=========

This page provides comprehensive tutorials to guide you from your first OpenSTEF model to advanced production implementations. Whether you're starting with basic forecasting or building custom workflows, these tutorials demonstrate practical patterns for real-world energy forecasting applications.

First Steps with OpenSTEF
--------------------------

Let's start by training your first model and creating a forecast using OpenSTEF's streamlined pipeline approach. This example demonstrates the complete workflow from data preparation to forecast evaluation.

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.metrics import metrics
   
   # Set up plotting backend for visualization
   pd.options.plotting.backend = 'plotly'

The first step is defining a prediction job, which specifies all the parameters needed for training and forecasting:

.. code-block:: python

   # Define the prediction job with essential parameters
   prediction_job = PredictionJobDataClass(
       id=287,
       name="Tutorial_Location",
       model="xgboost",
       quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],
       forecast_type="demand",
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=15,
       lat=53.0,
       lon=5.7,
       train_components=True
   )

Next, load your input data. OpenSTEF expects a DataFrame with datetime index and columns for load, weather, and market data:

.. code-block:: python

   # Load input data (replace with your data source)
   input_data = pd.read_csv("data/input_data_287.csv", index_col=0, parse_dates=True)
   
   # Verify data structure
   print(f"Data shape: {input_data.shape}")
   print(f"Columns: {list(input_data.columns)}")
   print(f"Date range: {input_data.index.min()} to {input_data.index.max()}")

Now train the model using OpenSTEF's pipeline:

.. code-block:: python

   # Train the model
   trained_model = train_model_pipeline(
       pj=prediction_job,
       input_data=input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_models",
       artifact_folder="./artifacts"
   )
   
   # Examine model performance
   print(f"Model type: {trained_model['model_type']}")
   print(f"Feature importance available: {'feature_importance' in trained_model}")

Create forecasts using the trained model:

.. code-block:: python

   # Create forecast for the next 48 hours
   forecast_data = create_forecast_pipeline(
       pj=prediction_job,
       input_data=input_data,
       model_specs=trained_model
   )
   
   # Display forecast structure
   print(f"Forecast columns: {list(forecast_data.columns)}")
   print(forecast_data.head())

Evaluate the forecast quality using OpenSTEF's built-in metrics:

.. code-block:: python

   # Calculate evaluation metrics
   from openstef.metrics.figure import plot_feature_importance, plot_data_series
   
   # Plot feature importance
   plot_feature_importance(trained_model)
   
   # Visualize forecast vs actual (if test data available)
   if 'load' in input_data.columns:
       plot_data_series(
           forecast_data,
           input_data['load'],
           prediction_job=prediction_job
       )

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF can decompose energy forecasts into renewable components, providing insights into wind and solar contributions:

.. code-block:: python

   from openstef.tasks.split_forecast import split_forecast_task
   
   # Perform energy splitting (requires trained model with components)
   if prediction_job.train_components:
       split_results = split_forecast_task(
           pj=prediction_job,
           context={'model': trained_model, 'data': input_data}
       )
       
       # Examine decomposition results
       print("Energy split coefficients:")
       print(split_results)

Backtesting with Multiple Models
---------------------------------

Backtesting evaluates how your models would have performed historically. This example demonstrates comparing two different model configurations using a realistic backtest setup.

.. code-block:: python

   from openstef.pipeline.train_create_forecast_backtest import train_model_and_forecast_back_test
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   
   # Define two model configurations to compare
   xgboost_config = PredictionJobDataClass(
       id=287,
       name="XGBoost_Model",
       model="xgboost",
       quantiles=[0.1, 0.5, 0.9],
       forecast_type="demand",
       horizon_minutes=2880,
       resolution_minutes=15,
       lat=53.0,
       lon=5.7
   )
   
   lgb_config = PredictionJobDataClass(
       id=288,
       name="LightGBM_Model", 
       model="lgb",
       quantiles=[0.1, 0.5, 0.9],
       forecast_type="demand",
       horizon_minutes=2880,
       resolution_minutes=15,
       lat=53.0,
       lon=5.7
   )

Run the backtest for both models:

.. code-block:: python

   # Define backtest period
   backtest_start = pd.Timestamp("2024-01-01")
   backtest_end = pd.Timestamp("2024-03-31")
   
   # Run backtest for XGBoost model
   xgb_results = train_model_and_forecast_back_test(
       pj=xgboost_config,
       input_data=input_data,
       backtest_start_datetime=backtest_start,
       backtest_end_datetime=backtest_end,
       retrain_model_days=7  # Retrain weekly
   )
   
   # Run backtest for LightGBM model  
   lgb_results = train_model_and_forecast_back_test(
       pj=lgb_config,
       input_data=input_data,
       backtest_start_datetime=backtest_start,
       backtest_end_datetime=backtest_end,
       retrain_model_days=7
   )

Compare model performance:

.. code-block:: python

   from openstef.metrics import mae, rmae, r2
   
   # Calculate metrics for both models
   xgb_mae = mae(xgb_results['y_true'], xgb_results['forecast'])
   lgb_mae = mae(lgb_results['y_true'], lgb_results['forecast'])
   
   xgb_r2 = r2(xgb_results['y_true'], xgb_results['forecast'])
   lgb_r2 = r2(lgb_results['y_true'], lgb_results['forecast'])
   
   print(f"XGBoost - MAE: {xgb_mae:.2f}, R²: {xgb_r2:.3f}")
   print(f"LightGBM - MAE: {lgb_mae:.2f}, R²: {lgb_r2:.3f}")
   
   # Visualize comparison
   comparison_df = pd.DataFrame({
       'actual': xgb_results['y_true'],
       'xgboost': xgb_results['forecast'],
       'lightgbm': lgb_results['forecast']
   })
   comparison_df.plot(title="Model Comparison")

Advanced Customization
-----------------------

For production deployments, you'll often need to customize OpenSTEF's behavior. This section demonstrates advanced patterns for custom data sources, workflows, and feature engineering.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Target providers define how OpenSTEF loads and processes your data. Create a custom provider for your specific data format:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider
   from typing import List, Dict, Any
   import pandas as pd
   
   class CustomTargetProvider(TargetProvider):
       """Custom target provider for company-specific data format."""
       
       def __init__(self, database_config: Dict[str, Any], **kwargs):
           super().__init__(**kwargs)
           self.db_config = database_config
           
       def load_targets(self) -> List[Dict[str, Any]]:
           """Load prediction targets from custom database."""
           # Connect to your database
           targets = []
           
           # Example: Load from SQL database
           import sqlalchemy as sa
           engine = sa.create_engine(self.db_config['connection_string'])
           
           query = """
           SELECT location_id, name, lat, lon, forecast_type 
           FROM forecasting_locations 
           WHERE active = true
           """
           
           locations = pd.read_sql(query, engine)
           
           for _, row in locations.iterrows():
               targets.append({
                   'id': row['location_id'],
                   'name': row['name'],
                   'lat': row['lat'],
                   'lon': row['lon'],
                   'forecast_type': row['forecast_type'],
                   'model': 'xgboost',
                   'quantiles': [0.1, 0.5, 0.9],
                   'horizon_minutes': 2880
               })
               
           return targets
           
       def load_data(self, target: Dict[str, Any]) -> pd.DataFrame:
           """Load historical data for a specific target."""
           engine = sa.create_engine(self.db_config['connection_string'])
           
           query = """
           SELECT datetime, load_mw, temperature, wind_speed, solar_irradiance
           FROM energy_data 
           WHERE location_id = %(location_id)s
           AND datetime >= %(start_date)s
           ORDER BY datetime
           """
           
           data = pd.read_sql(
               query, 
               engine,
               params={
                   'location_id': target['id'],
                   'start_date': pd.Timestamp.now() - pd.Timedelta(days=365)
               },
               parse_dates=['datetime'],
               index_col='datetime'
           )
           
           return data

Custom Workflow Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build custom workflows that integrate OpenSTEF with your existing systems:

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import logging
   from typing import Optional
   
   class ProductionForecastingWorkflow:
       """Production workflow integrating OpenSTEF with monitoring and alerting."""
       
       def __init__(self, config: Dict[str, Any]):
           self.config = config
           self.logger = logging.getLogger(__name__)
           
       def run_daily_forecast(self, prediction_job: PredictionJobDataClass) -> Optional[pd.DataFrame]:
           """Execute daily forecasting workflow with error handling."""
           
           try:
               # Load fresh data
               data = self._load_latest_data(prediction_job.id)
               
               # Validate data quality
               if not self._validate_data_quality(data):
                   self.logger.error(f"Data quality check failed for job {prediction_job.id}")
                   return None
                   
               # Load or train model
               model_specs = self._get_or_train_model(prediction_job, data)
               
               # Create forecast
               forecast = create_forecast_pipeline(
                   pj=prediction_job,
                   input_data=data,
                   model_specs=model_specs
               )
               
               # Validate forecast
               if self._validate_forecast(forecast):
                   # Store results
                   self._store_forecast(prediction_job.id, forecast)
                   
                   # Send to external systems
                   self._publish_forecast(prediction_job.id, forecast)
                   
                   self.logger.info(f"Successfully created forecast for job {prediction_job.id}")
                   return forecast
               else:
                   self.logger.error(f"Forecast validation failed for job {prediction_job.id}")
                   return None
                   
           except Exception as e:
               self.logger.error(f"Workflow failed for job {prediction_job.id}: {str(e)}")
               self._send_alert(prediction_job.id, str(e))
               return None
               
       def _validate_data_quality(self, data: pd.DataFrame) -> bool:
           """Validate input data meets quality requirements."""
           # Check for minimum data availability
           if len(data) < 24 * 4 * 7:  # At least 1 week of 15-min data
               return False
               
           # Check for excessive missing values
           missing_ratio = data.isnull().sum().max() / len(data)
           if missing_ratio > 0.1:  # Max 10% missing
               return False
               
           return True
           
       def _validate_forecast(self, forecast: pd.DataFrame) -> bool:
           """Validate forecast output."""
           # Check for NaN values
           if forecast.isnull().any().any():
               return False
               
           # Check for reasonable value ranges
           if (forecast < 0).any().any():
               return False
               
           return True

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering with domain-specific transformations:

.. code-block:: python

   from openstef.feature_engineering.apply_features import apply_features
   import pandas as pd
   import numpy as np
   
   def add_custom_features(data: pd.DataFrame, prediction_job: PredictionJobDataClass) -> pd.DataFrame:
       """Add custom features specific to your use case."""
       
       # Apply standard OpenSTEF features first
       data_with_features = apply_features(data, prediction_job)
       
       # Add custom business-specific features
       if 'load' in data.columns:
           # Industrial activity indicators
           data_with_features['is_business_hours'] = (
               (data.index.hour >= 8) & (data.index.hour <= 17) & 
               (data.index.weekday < 5)
           ).astype(int)
           
           # Seasonal industrial patterns
           data_with_features['summer_industrial_factor'] = np.where(
               data.index.month.isin([6, 7, 8]),
               0.85,  # Reduced industrial activity in summer
               1.0
           )
           
           # Peak demand indicators
           rolling_max = data['load'].rolling(window=96, min_periods=24).max()  # 24h rolling max
           data_with_features['load_stress_indicator'] = (
               data['load'] / rolling_max
           ).fillna(0)
           
       # Weather-based custom features
       if 'temperature' in data.columns:
           # Cooling/heating degree days
           data_with_features['cooling_degree_hours'] = np.maximum(
               data['temperature'] - 18, 0
           )
           data_with_features['heating_degree_hours'] = np.maximum(
               18 - data['temperature'], 0
           )
           
       # Market-based features
       if 'APX' in data.columns:  # Day-ahead electricity price
           # Price volatility indicator
           data_with_features['price_volatility'] = (
               data['APX'].rolling(window=24).std()
           )
           
           # High price periods (demand response trigger)
           price_95th = data['APX'].quantile(0.95)
           data_with_features['high_price_period'] = (
               data['APX'] > price_95th
           ).astype(int)
           
       return data_with_features

Use your custom features in the training pipeline:

.. code-block:: python

   # Integrate custom features into training
   def train_with_custom_features(prediction_job: PredictionJobDataClass, input_data: pd.DataFrame):
       """Train model with custom feature engineering."""
       
       # Apply custom features
       enhanced_data = add_custom_features(input_data, prediction_job)
       
       # Train model with enhanced features
       trained_model = train_model_pipeline(
           pj=prediction_job,
           input_data=enhanced_data,
           check_old_model_age=False
       )
       
       return trained_model, enhanced_data

.. note::
   When implementing custom features, ensure they can be computed at forecast time using only historical data. Features that require future information will cause data leakage and unrealistic performance estimates.

Next Steps
----------

These tutorials demonstrate core OpenSTEF patterns for production forecasting systems. For specific implementation tasks like deployment setup or data integration, see the :doc:`../guides/how_to_guides`. For deeper understanding of forecasting concepts and model behavior, explore the :doc:`../reference/concepts` section.

The :doc:`../guides/use_cases` page can help you identify which forecasting approach best matches your specific energy system requirements.