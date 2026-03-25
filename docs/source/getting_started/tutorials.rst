Tutorials
=========

This page provides comprehensive tutorials for OpenSTEF, guiding you from your first forecast to advanced customization. These tutorials build upon the quickstart guide and prepare you for production implementation.

First Steps with Maximum Presets
---------------------------------

The fastest way to get started with OpenSTEF is using maximum presets, which provide sensible defaults for common forecasting scenarios. This tutorial demonstrates the complete workflow from data preparation to forecast evaluation.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF works with time series data containing load measurements and weather predictors. Here's how to prepare your data:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig
   
   # Load your time series data
   # Data should include: datetime index, load column, weather features
   data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)
   
   # Create TimeSeriesDataset
   dataset = TimeSeriesDataset.from_pandas(data)
   
   # Split into training and validation sets
   split_time = dataset.index[-24*7]  # Last week for validation
   train_data = dataset.filter_by_range(end=split_time)
   val_data = dataset.filter_by_range(start=split_time)

Training Your First Model
^^^^^^^^^^^^^^^^^^^^^^^^^^

With maximum presets, model training requires minimal configuration:

.. code-block:: python

   # Configure workflow with maximum presets
   config = ForecastingWorkflowConfig(
       location={"name": "my_location", "lat": 52.0, "lon": 5.0},
       model_type="xgb",  # XGBoost with optimized hyperparameters
       quantiles=[0.1, 0.5, 0.9],  # Forecast uncertainty levels
       max_horizon_hours=48,
       feature_engineering="maximum"  # All available features
   )
   
   # Create and train the workflow
   workflow = create_forecasting_workflow(config)
   fit_result = workflow.fit(train_data, data_val=val_data)
   
   print(f"Training completed. Validation MAE: {fit_result.validation_metrics['mae']:.2f}")

Creating Forecasts
^^^^^^^^^^^^^^^^^^^

Generate probabilistic forecasts with confidence intervals:

.. code-block:: python

   from datetime import datetime
   
   # Create forecast for next 48 hours
   forecast_start = datetime.now().replace(minute=0, second=0, microsecond=0)
   forecast_data = workflow.predict(val_data, forecast_start=forecast_start)
   
   # Access forecast components
   median_forecast = forecast_data.median_series()
   p10_forecast = forecast_data.data['quantile_P10']
   p90_forecast = forecast_data.data['quantile_P90']
   
   print(f"48h forecast range: {median_forecast.iloc[-1]:.1f} MW")

Evaluating Results
^^^^^^^^^^^^^^^^^^

Assess forecast quality using built-in metrics:

.. code-block:: python

   from openstef_models.metrics import calculate_forecast_metrics
   
   # Evaluate against actual measurements
   if 'load' in forecast_data.data.columns:
       metrics = calculate_forecast_metrics(
           forecast_data.data['load'],
           forecast_data.median_series(),
           quantile_forecasts=forecast_data.quantiles_data()
       )
       
       print(f"MAE: {metrics['mae']:.2f} MW")
       print(f"MAPE: {metrics['mape']:.1f}%")
       print(f"Quantile Score (P90): {metrics['quantile_score_P90']:.3f}")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Decompose forecasts into renewable and conventional components:

.. code-block:: python

   from openstef_models.models.component_splitting import LinearComponentSplitter
   
   # Configure component splitter
   splitter = LinearComponentSplitter()
   
   # Fit splitter on historical data with weather features
   splitter.fit(train_data)
   
   # Decompose forecast into components
   components = splitter.predict(forecast_data)
   
   # Access individual components
   wind_component = components.data['wind_component']
   solar_component = components.data['solar_component']
   base_load = components.data['base_load']
   
   print(f"Wind contribution: {wind_component.mean():.1f} MW")
   print(f"Solar contribution: {solar_component.mean():.1f} MW")

Backtesting with Liander 2024 Dataset
--------------------------------------

Backtesting validates model performance on historical data. This example uses the Liander 2024 benchmark dataset to compare two different models.

Setting Up the Backtest
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkRunner, SimpleTargetProvider
   from openstef_models.presets import ForecastingWorkflowConfig
   
   # Configure target provider for Liander dataset
   target_provider = SimpleTargetProvider(
       config_path="liander_2024_targets.yaml",
       data_path="liander_2024_data/"
   )
   
   # Get available targets
   targets = target_provider.get_targets()
   print(f"Found {len(targets)} forecast targets")

Comparing XGBoost Models
^^^^^^^^^^^^^^^^^^^^^^^^

Compare standard XGBoost against gradient boosting linear model:

.. code-block:: python

   # Configuration for XGBoost model
   xgb_config = ForecastingWorkflowConfig(
       model_type="xgb",
       hyperparams={
           "n_estimators": 100,
           "max_depth": 6,
           "learning_rate": 0.1
       },
       feature_engineering="standard"
   )
   
   # Configuration for linear gradient boosting
   gblinear_config = ForecastingWorkflowConfig(
       model_type="xgb",
       hyperparams={
           "booster": "gblinear",
           "n_estimators": 500,
           "learning_rate": 0.01
       },
       feature_engineering="standard"
   )
   
   # Create workflows
   xgb_workflow = create_forecasting_workflow(xgb_config)
   gblinear_workflow = create_forecasting_workflow(gblinear_config)

Running the Backtest
^^^^^^^^^^^^^^^^^^^^^

Execute backtesting for both models:

.. code-block:: python

   from openstef_beam.benchmarking import BacktestConfig
   
   # Configure backtest parameters
   backtest_config = BacktestConfig(
       start_date="2024-01-01",
       end_date="2024-12-31",
       train_window_days=365,
       retrain_frequency_days=30,
       forecast_horizons=[0.25, 6, 24, 48]  # 15min, 6h, 24h, 48h
   )
   
   # Run backtests
   runner = BenchmarkRunner(target_provider, backtest_config)
   
   xgb_results = runner.run_benchmark("xgb_standard", xgb_workflow, targets[:5])
   gblinear_results = runner.run_benchmark("gblinear", gblinear_workflow, targets[:5])
   
   print("Backtest completed for both models")

Analyzing Results
^^^^^^^^^^^^^^^^^

Compare model performance across targets and horizons:

.. code-block:: python

   from openstef_beam.analysis import compare_benchmark_results
   
   # Compare results
   comparison = compare_benchmark_results([xgb_results, gblinear_results])
   
   # Print summary statistics
   print("Model Performance Comparison:")
   print(f"XGBoost MAE: {comparison['xgb_standard']['mae_mean']:.2f} ± {comparison['xgb_standard']['mae_std']:.2f}")
   print(f"GBLinear MAE: {comparison['gblinear']['mae_mean']:.2f} ± {comparison['gblinear']['mae_std']:.2f}")
   
   # Statistical significance test
   if comparison['statistical_significance']['mae'] < 0.05:
       print("Performance difference is statistically significant")

Advanced Customization
-----------------------

For production deployments, you'll often need custom components. This section demonstrates advanced customization patterns.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^^

Create a custom target provider for your data sources:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from dataclasses import dataclass
   
   @dataclass
   class CustomTarget:
       id: str
       name: str
       location: dict
       
   class DatabaseTargetProvider(TargetProvider):
       def __init__(self, connection_string: str):
           self.connection = create_connection(connection_string)
           
       def get_targets(self, filter_args=None):
           # Query your database for available targets
           query = "SELECT id, name, lat, lon FROM forecast_targets"
           results = self.connection.execute(query).fetchall()
           
           return [
               CustomTarget(
                   id=row['id'],
                   name=row['name'],
                   location={'lat': row['lat'], 'lon': row['lon']}
               )
               for row in results
           ]
           
       def get_measurements_for_target(self, target):
           # Load measurements from your database
           query = """
           SELECT timestamp, load, temperature, windspeed 
           FROM measurements 
           WHERE target_id = ?
           ORDER BY timestamp
           """
           df = pd.read_sql(query, self.connection, params=[target.id])
           return VersionedTimeSeriesDataset.from_pandas(df.set_index('timestamp'))

Custom Workflow Components
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build workflows with custom preprocessing and feature engineering:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.preprocessing import BasePreprocessor
   from openstef_models.feature_engineering import BaseFeatureEngineer
   
   class CustomPreprocessor(BasePreprocessor):
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Apply custom data cleaning
           df = data.to_pandas()
           
           # Remove outliers using your business logic
           df = self.remove_outliers(df)
           
           # Apply custom smoothing
           df['load'] = df['load'].rolling(window=3, center=True).mean()
           
           return TimeSeriesDataset.from_pandas(df)
           
   class DomainFeatureEngineer(BaseFeatureEngineer):
       def create_features(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.to_pandas()
           
           # Add domain-specific features
           df['peak_hour'] = (df.index.hour >= 17) & (df.index.hour <= 20)
           df['weekend'] = df.index.weekday >= 5
           df['heating_degree_days'] = np.maximum(0, 18 - df['temperature'])
           
           return TimeSeriesDataset.from_pandas(df)
   
   # Create custom workflow
   custom_workflow = CustomForecastingWorkflow(
       preprocessor=CustomPreprocessor(),
       feature_engineer=DomainFeatureEngineer(),
       model_config={"model_type": "xgb", "max_depth": 8},
       quantiles=[0.05, 0.25, 0.5, 0.75, 0.95]
   )

Custom Feature Engineering Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implement reusable feature modules for specific domains:

.. code-block:: python

   from openstef_models.feature_engineering import BaseFeatureModule
   
   class IndustrialLoadFeatures(BaseFeatureModule):
       """Features specific to industrial load forecasting."""
       
       def __init__(self, shift_schedule: dict):
           self.shift_schedule = shift_schedule
           
       def create_features(self, data: TimeSeriesDataset) -> dict:
           df = data.to_pandas()
           features = {}
           
           # Shift pattern features
           features['shift_1'] = self._is_shift_active(df.index, 1)
           features['shift_2'] = self._is_shift_active(df.index, 2)
           features['shift_3'] = self._is_shift_active(df.index, 3)
           
           # Production calendar features
           features['production_day'] = ~df.index.isin(self._get_holidays())
           features['maintenance_week'] = self._is_maintenance_period(df.index)
           
           return features
           
       def _is_shift_active(self, timestamps, shift_number):
           start_hour, end_hour = self.shift_schedule[shift_number]
           return (timestamps.hour >= start_hour) & (timestamps.hour < end_hour)
   
   # Use in workflow configuration
   config = ForecastingWorkflowConfig(
       feature_modules=[
           IndustrialLoadFeatures(shift_schedule={1: (6, 14), 2: (14, 22), 3: (22, 6)}),
           "weather_features",  # Built-in module
           "calendar_features"   # Built-in module
       ]
   )

Production Integration Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Combine custom components for a production-ready system:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.callbacks import MLflowCallback, SlackCallback
   
   # Production workflow with monitoring
   production_workflow = CustomForecastingWorkflow(
       preprocessor=CustomPreprocessor(),
       feature_engineer=DomainFeatureEngineer(),
       model_config={
           "model_type": "ensemble",
           "base_models": ["xgb", "lgb", "linear"],
           "meta_model": "linear"
       },
       callbacks=[
           MLflowCallback(tracking_uri="http://mlflow:5000"),
           SlackCallback(webhook_url="https://hooks.slack.com/...")
       ]
   )
   
   # Training with full monitoring
   fit_result = production_workflow.fit(
       train_data, 
       data_val=val_data,
       run_name=f"production_model_{datetime.now().strftime('%Y%m%d')}"
   )
   
   # Deploy if performance meets criteria
   if fit_result.validation_metrics['mae'] < acceptable_threshold:
       production_workflow.save_model("models/production/latest")
       print("Model deployed to production")

Next Steps
----------

After completing these tutorials, you're ready to:

- Explore specific use cases for your domain in the guides section
- Set up deployment and integration patterns using the how-to guides
- Dive deeper into forecasting concepts in the reference documentation
- Check the FAQ for common questions and troubleshooting

For production deployments, consider the deployment guides and integration patterns in the how-to guides section.