Tutorials
=========

This page guides you through using OpenSTEF for real-world forecasting scenarios. You'll start with a complete end-to-end example using sensible defaults, then learn how to backtest multiple models, and finally explore advanced customization options for production deployments.

These tutorials assume you've already completed the :doc:`quickstart` and are ready to build production-ready forecasting systems.

First Forecast: End-to-End Example
-----------------------------------

This tutorial demonstrates the complete forecasting workflow: loading data, training a model, creating forecasts, evaluating results, and decomposing energy components. We'll use maximum presets to minimize configuration while still producing production-quality forecasts.

Setting Up the Prediction Job
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A prediction job defines all parameters needed for training and forecasting. Start by creating a configuration with sensible defaults:

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Define the prediction job
   pj_dict = dict(
       id=101,
       model='xgb',  # XGBoost model
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=15,  # 15-minute intervals
       name="tutorial_forecast",
       save_train_forecasts=True,
   )
   pj = PredictionJobDataClass(**pj_dict)

The prediction job specifies the location (lat/lon for weather data), forecast horizon, time resolution, and which quantiles to predict. Quantile forecasts provide uncertainty estimates alongside point predictions.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects input data with a datetime index and columns for load (target variable) and weather predictors:

.. code-block:: python

   # Load your data (CSV, database, or API)
   input_data = pd.read_csv("energy_data.csv", index_col=0, parse_dates=True)
   
   # Expected columns: 'load', 'radiation', 'windspeed_100m', 'temperature', etc.
   # The datetime index should have consistent intervals matching resolution_minutes
   
   # Split into training and forecasting periods
   train_data = input_data.iloc[:-192]  # All but last 48 hours (192 = 48*4 for 15-min data)
   forecast_data = input_data.iloc[-192:].copy()
   
   # Set load to NaN for the forecast period (simulating real forecasting)
   forecast_data['load'] = float('nan')

The split separates historical data for training from the period you want to forecast. Setting load to NaN in the forecast period simulates real-world conditions where you don't yet know the actual values.

Training the Model
^^^^^^^^^^^^^^^^^^

Train a model using the prepared data and prediction job:

.. code-block:: python

   # Train the model
   trained_model, report, train_forecasts, validation_forecasts = train_model_pipeline(
       pj=pj,
       input_data=train_data,
   )
   
   # The report contains training metrics and feature importance
   print(f"Training RMSE: {report['rmse']:.2f}")
   print(f"Training MAE: {report['mae']:.2f}")
   print(f"Skill Score: {report['skill_score']:.3f}")

The training pipeline automatically handles feature engineering, model training, and validation. The skill score indicates how much better your model performs compared to a naive baseline (typically the mean).

Creating Forecasts
^^^^^^^^^^^^^^^^^^

Use the trained model to create forecasts for the test period:

.. code-block:: python

   # Create forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=forecast_data,
       model=trained_model,
   )
   
   # Forecast contains quantile predictions
   print(forecast[['forecast', 'quantile_P10', 'quantile_P50', 'quantile_P90']].head())

The forecast includes point predictions (typically the median, P50) and quantile predictions that represent uncertainty. Lower quantiles (P10) represent optimistic scenarios, while higher quantiles (P90) represent pessimistic scenarios.

Evaluating Results
^^^^^^^^^^^^^^^^^^

Compare forecasts against actual values to assess model performance:

.. code-block:: python

   from openstef.metrics.metrics import rmse, mae, skill_score, r_mae
   
   # Get actual values for comparison
   actual = input_data.iloc[-192:]['load']
   predicted = forecast['forecast']
   
   # Calculate metrics
   forecast_rmse = rmse(actual, predicted)
   forecast_mae = mae(actual, predicted)
   forecast_rmae = r_mae(actual, predicted)
   
   # Calculate skill score (requires baseline - typically the mean)
   baseline = pd.Series([actual.mean()] * len(actual), index=actual.index)
   forecast_skill = skill_score(actual, predicted, baseline)
   
   print(f"Forecast RMSE: {forecast_rmse:.2f}")
   print(f"Forecast MAE: {forecast_mae:.2f}")
   print(f"Forecast rMAE: {forecast_rmae:.1%}")
   print(f"Forecast Skill Score: {forecast_skill:.3f}")

The relative MAE (rMAE) expresses error as a percentage of average load, making it easier to interpret across different scales. A skill score above 0 indicates your model outperforms the baseline.

Visualizing Forecasts
^^^^^^^^^^^^^^^^^^^^^

Visualize the forecast with uncertainty bands:

.. code-block:: python

   import plotly.graph_objects as go
   
   fig = go.Figure()
   
   # Add actual values
   fig.add_trace(go.Scatter(
       x=actual.index, y=actual.values,
       name='Actual', mode='lines',
       line=dict(color='black', width=2)
   ))
   
   # Add forecast
   fig.add_trace(go.Scatter(
       x=forecast.index, y=forecast['forecast'],
       name='Forecast', mode='lines',
       line=dict(color='blue', width=2)
   ))
   
   # Add uncertainty bands (P10 to P90)
   fig.add_trace(go.Scatter(
       x=forecast.index, y=forecast['quantile_P90'],
       name='P90', mode='lines',
       line=dict(width=0), showlegend=False
   ))
   fig.add_trace(go.Scatter(
       x=forecast.index, y=forecast['quantile_P10'],
       name='P10', fill='tonexty', mode='lines',
       line=dict(width=0), fillcolor='rgba(0,100,255,0.2)'
   ))
   
   fig.update_layout(title='Energy Forecast with Uncertainty',
                     xaxis_title='Time', yaxis_title='Load (MW)')
   fig.show()

Energy Component Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For locations with significant solar or wind generation, you can decompose the total forecast into renewable components:

.. code-block:: python

   from openstef.tasks.split_forecast import find_components
   
   # Combine forecast with weather data
   forecast_with_weather = forecast.join(input_data[['radiation', 'windspeed_100m']])
   
   # Decompose into components
   components, coefficients = find_components(forecast_with_weather, zero_bound=True)
   
   # Components DataFrame contains: 'wind', 'solar', 'baseload'
   print(components[['wind', 'solar', 'baseload']].head())
   print(f"\nCoefficients: {coefficients}")

The component splitting identifies how much of the load variation is explained by wind, solar, and baseload consumption. The coefficients indicate the sensitivity to each renewable source. Setting ``zero_bound=True`` ensures physically realistic (non-negative) component values.

Backtesting with Multiple Models
---------------------------------

Backtesting evaluates model performance across multiple historical periods, helping you choose the best model and understand forecast reliability. This example uses the Liander 2024 benchmark dataset to compare XGBoost and linear models.

Setting Up the Benchmark
^^^^^^^^^^^^^^^^^^^^^^^^^

The benchmarking framework provides a standardized way to evaluate models:

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking import SimpleTargetProvider, BenchmarkRunner
   from openstef_beam.benchmarking.models import BenchmarkTarget
   from openstef_beam.evaluation.metric_providers import RMAEProvider, SkillScoreProvider
   
   # Define benchmark configuration
   data_path = Path("data/liander_2024")
   
   # Create target provider (loads benchmark datasets)
   class Liander2024Provider(SimpleTargetProvider):
       def __init__(self):
           super().__init__(
               config_path=data_path / "targets.yaml",
               data_path=data_path / "measurements",
           )
   
   provider = Liander2024Provider()
   targets = provider.get_targets()
   
   print(f"Loaded {len(targets)} benchmark targets")

The target provider loads configuration and data for multiple prediction jobs. Each target represents a different location or asset to forecast.

Configuring Multiple Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Define the models you want to compare:

.. code-block:: python

   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   from openstef.model.regressors.linear import LinearQuantileOpenstfRegressor
   
   # Model configurations
   models_config = {
       'xgboost': {
           'model_type': 'xgb',
           'model_class': XGBQuantileOpenstfRegressor,
           'params': {
               'max_depth': 5,
               'learning_rate': 0.1,
               'n_estimators': 100,
           }
       },
       'linear': {
           'model_type': 'linear',
           'model_class': LinearQuantileOpenstfRegressor,
           'params': {
               'fit_intercept': True,
           }
       }
   }

Running the Backtest
^^^^^^^^^^^^^^^^^^^^

Execute the benchmark across all targets and models:

.. code-block:: python

   from datetime import datetime, timedelta
   
   # Define backtest periods
   backtest_start = datetime(2023, 1, 1)
   backtest_end = datetime(2023, 12, 31)
   train_window_days = 365  # Use 1 year of training data
   
   results = {}
   
   for model_name, config in models_config.items():
       print(f"\nRunning backtest for {model_name}...")
       
       model_results = []
       
       for target in targets:
           # Get data for this target
           measurements = provider.get_measurements(target)
           predictors = provider.get_predictors(target)
           
           # Create prediction job for this target
           pj = PredictionJobDataClass(
               id=target.name,
               model=config['model_type'],
               quantiles=[0.10, 0.50, 0.90],
               forecast_type="demand",
               lat=target.latitude,
               lon=target.longitude,
               horizon_minutes=2880,
               resolution_minutes=15,
               name=target.name,
           )
           
           # Train model
           train_end = backtest_start - timedelta(days=1)
           train_start = train_end - timedelta(days=train_window_days)
           train_data = measurements[train_start:train_end].join(predictors)
           
           model, report, _, _ = train_model_pipeline(pj=pj, input_data=train_data)
           
           # Create forecasts for backtest period
           test_data = measurements[backtest_start:backtest_end].join(predictors)
           forecast = create_forecast_pipeline(pj=pj, input_data=test_data, model=model)
           
           # Calculate metrics
           actual = measurements.loc[forecast.index, 'load']
           metrics = {
               'target': target.name,
               'rmse': rmse(actual, forecast['forecast']),
               'mae': mae(actual, forecast['forecast']),
               'rmae': r_mae(actual, forecast['forecast']),
           }
           model_results.append(metrics)
       
       results[model_name] = pd.DataFrame(model_results)

Analyzing Backtest Results
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compare model performance across targets:

.. code-block:: python

   # Aggregate results
   comparison = pd.DataFrame({
       model_name: df.set_index('target')['rmae']
       for model_name, df in results.items()
   })
   
   print("\nrMAE by Model and Target:")
   print(comparison)
   
   print("\nAverage rMAE by Model:")
   print(comparison.mean())
   
   print("\nModel wins (lowest rMAE per target):")
   print(comparison.idxmin(axis=1).value_counts())
   
   # Visualize comparison
   comparison.plot(kind='box', title='rMAE Distribution by Model')

This analysis reveals which model performs best overall and whether certain models excel for specific targets. XGBoost typically outperforms linear models but requires more computational resources.

Advanced Customization
----------------------

For production deployments, you may need to customize data loading, feature engineering, or the forecasting workflow. This section demonstrates common customization patterns.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Create a custom target provider to load data from your own systems:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider
   from openstef_beam.benchmarking.models import BenchmarkTarget
   import sqlalchemy as sa
   
   class DatabaseTargetProvider(TargetProvider):
       """Load targets and data from a database."""
       
       def __init__(self, connection_string: str, region: str):
           super().__init__()
           self.engine = sa.create_engine(connection_string)
           self.region = region
       
       def get_targets(self, filter_args=None):
           """Load target configurations from database."""
           query = """
               SELECT id, name, latitude, longitude, forecast_type
               FROM prediction_jobs
               WHERE region = :region AND active = true
           """
           
           with self.engine.connect() as conn:
               rows = conn.execute(sa.text(query), {'region': self.region})
               
               targets = []
               for row in rows:
                   targets.append(BenchmarkTarget(
                       name=row.name,
                       description=f"Forecast for {row.name}",
                       group_name=self.region,
                       latitude=row.latitude,
                       longitude=row.longitude,
                       forecast_type=row.forecast_type,
                   ))
               
               return targets
       
       def get_measurements(self, target: BenchmarkTarget) -> pd.DataFrame:
           """Load measurement data for a target."""
           query = """
               SELECT timestamp, load
               FROM measurements
               WHERE location_name = :name
               ORDER BY timestamp
           """
           
           with self.engine.connect() as conn:
               df = pd.read_sql(
                   sa.text(query),
                   conn,
                   params={'name': target.name},
                   index_col='timestamp',
                   parse_dates=['timestamp']
               )
               
               return df
       
       def get_predictors(self, target: BenchmarkTarget) -> pd.DataFrame:
           """Load weather predictor data for a target."""
           query = """
               SELECT timestamp, temperature, radiation, windspeed_100m
               FROM weather_data
               WHERE latitude = :lat AND longitude = :lon
               ORDER BY timestamp
           """
           
           with self.engine.connect() as conn:
               df = pd.read_sql(
                   sa.text(query),
                   conn,
                   params={'lat': target.latitude, 'lon': target.longitude},
                   index_col='timestamp',
                   parse_dates=['timestamp']
               )
               
               return df
   
   # Use the custom provider
   provider = DatabaseTargetProvider(
       connection_string="postgresql://user:pass@localhost/forecasts",
       region="north"
   )

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add domain-specific features to improve forecast accuracy:

.. code-block:: python

   from openstef.feature_engineering.apply_features import apply_features
   
   def add_custom_features(data: pd.DataFrame, pj: PredictionJobDataClass) -> pd.DataFrame:
       """Add custom features before standard feature engineering."""
       
       # Add holiday indicators
       from pandas.tseries.holiday import USFederalHolidayCalendar
       cal = USFederalHolidayCalendar()
       holidays = cal.holidays(start=data.index.min(), end=data.index.max())
       data['is_holiday'] = data.index.isin(holidays).astype(int)
       
       # Add day-before-holiday indicator
       data['is_pre_holiday'] = data.index.isin(holidays - pd.Timedelta(days=1)).astype(int)
       
       # Add temperature-based features
       if 'temperature' in data.columns:
           # Heating degree days (base 18°C)
           data['heating_degree_days'] = (18 - data['temperature']).clip(lower=0)
           
           # Cooling degree days (base 22°C)
           data['cooling_degree_days'] = (data['temperature'] - 22).clip(lower=0)
       
       # Add solar angle features (improves solar forecasts)
       if 'radiation' in data.columns:
           from openstef.feature_engineering.weather_features import add_solar_features
           data = add_solar_features(data, pj.lat, pj.lon)
       
       return data
   
   # Use in training pipeline
   def train_with_custom_features(pj, input_data):
       # Add custom features
       data_with_features = add_custom_features(input_data, pj)
       
       # Apply standard features
       data_with_features = apply_features(data_with_features, pj)
       
       # Train model
       return train_model_pipeline(pj=pj, input_data=data_with_features)

Custom Workflow Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Integrate OpenSTEF into a custom orchestration workflow:

.. code-block:: python

   from typing import Dict, Any
   import mlflow
   
   class ForecastWorkflow:
       """Custom workflow for production forecasting."""
       
       def __init__(self, config: Dict[str, Any]):
           self.config = config
           self.mlflow_tracking_uri = config['mlflow_tracking_uri']
           mlflow.set_tracking_uri(self.mlflow_tracking_uri)
       
       def run_daily_forecast(self, pj: PredictionJobDataClass):
           """Execute daily forecasting workflow."""
           
           with mlflow.start_run(run_name=f"forecast_{pj.name}"):
               # Log parameters
               mlflow.log_params({
                   'prediction_job_id': pj.id,
                   'model_type': pj.model,
                   'horizon_hours': pj.horizon_minutes / 60,
               })
               
               # Load data from your data source
               data = self._load_data(pj)
               
               # Load or train model
               model = self._get_or_train_model(pj, data)
               
               # Create forecast
               forecast = create_forecast_pipeline(
                   pj=pj,
                   input_data=data,
                   model=model,
               )
               
               # Post-process and validate
               forecast = self._validate_forecast(forecast, pj)
               
               # Store results
               self._store_forecast(forecast, pj)
               
               # Log metrics
               mlflow.log_metrics({
                   'forecast_points': len(forecast),
                   'forecast_mean': forecast['forecast'].mean(),
                   'forecast_std': forecast['forecast'].std(),
               })
               
               return forecast
       
       def _load_data(self, pj: PredictionJobDataClass) -> pd.DataFrame:
           """Load data from configured source."""
           # Implement your data loading logic
           pass
       
       def _get_or_train_model(self, pj: PredictionJobDataClass, data: pd.DataFrame):
           """Load existing model or train new one if needed."""
           model_path = f"models/{pj.name}/latest"
           
           try:
               # Try loading existing model
               model = mlflow.sklearn.load_model(model_path)
               
               # Check if retraining is needed
               if self._should_retrain(pj, model):
                   model = self._train_and_save_model(pj, data)
               
           except Exception:
               # No existing model, train new one
               model = self._train_and_save_model(pj, data)
           
           return model
       
       def _should_retrain(self, pj: PredictionJobDataClass, model) -> bool:
           """Determine if model should be retrained."""
           # Implement retraining logic (e.g., based on age, performance)
           return False
       
       def _train_and_save_model(self, pj: PredictionJobDataClass, data: pd.DataFrame):
           """Train and save a new model."""
           model, report, _, _ = train_model_pipeline(pj=pj, input_data=data)
           
           # Save model
           mlflow.sklearn.log_model(model, f"models/{pj.name}")
           
           # Log training metrics
           mlflow.log_metrics({
               'train_rmse': report['rmse'],
               'train_mae': report['mae'],
               'train_skill_score': report['skill_score'],
           })
           
           return model
       
       def _validate_forecast(self, forecast: pd.DataFrame, pj: PredictionJobDataClass) -> pd.DataFrame:
           """Validate and clean forecast results."""
           # Check for NaN values
           if forecast['forecast'].isna().any():
               raise ValueError(f"Forecast contains NaN values for {pj.name}")
           
           # Check for negative values (if inappropriate)
           if (forecast['forecast'] < 0).any():
               print(f"Warning: Negative forecast values for {pj.name}, clipping to 0")
               forecast['forecast'] = forecast['forecast'].clip(lower=0)
           
           # Ensure quantiles are ordered correctly
           quantile_cols = [c for c in forecast.columns if c.startswith('quantile_')]
           if quantile_cols:
               for i in range(len(quantile_cols) - 1):
                   if (forecast[quantile_cols[i]] > forecast[quantile_cols[i+1]]).any():
                       print(f"Warning: Quantile ordering violated for {pj.name}")
           
           return forecast
       
       def _store_forecast(self, forecast: pd.DataFrame, pj: PredictionJobDataClass):
           """Store forecast results to configured destination."""
           # Implement your storage logic (database, S3, etc.)
           pass
   
   # Use the workflow
   workflow = ForecastWorkflow({
       'mlflow_tracking_uri': 'http://localhost:5000',
       'data_source': 'postgresql://...',
   })
   
   forecast = workflow.run_daily_forecast(pj)

Next Steps
----------

You now have the knowledge to build production forecasting systems with OpenSTEF. For specific implementation tasks, see the :doc:`../guides/how_to_guides`. To understand different forecasting scenarios, explore :doc:`../guides/use_cases`. For deeper understanding of forecasting concepts, read :doc:`../reference/concepts`.