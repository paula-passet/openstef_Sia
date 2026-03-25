Now I have enough information to create a comprehensive tutorial page. Let me write the complete RST documentation.

Tutorials
==========

This page provides comprehensive tutorials to guide you from your first OpenSTEF model to advanced production implementations. These tutorials build upon the :doc:`quickstart` guide and prepare you for real-world forecasting scenarios.

Getting Started with Maximum Presets
-------------------------------------

The fastest way to explore OpenSTEF's capabilities is using maximum presets, which provide sensible defaults for all configuration options. This tutorial walks through the complete forecasting workflow: loading data, training a model, creating forecasts, and evaluating results.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF works with time series data stored in ``TimeSeriesDataset`` objects. Let's start by loading sample data:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.presets.forecasting_workflow import (
       create_forecasting_workflow, ForecastingWorkflowConfig
   )

   # Load your time series data
   # This example assumes you have a CSV with columns: timestamp, load, temperature, wind_speed
   df = pd.read_csv("energy_data.csv", parse_dates=['timestamp'])
   df.set_index('timestamp', inplace=True)

   # Create a TimeSeriesDataset
   dataset = TimeSeriesDataset.from_pandas(
       df,
       sample_interval=timedelta(hours=1)
   )

   # Split data for training and testing
   split_date = datetime(2023, 10, 1)
   train_data = dataset.filter_by_range(end=split_date)
   test_data = dataset.filter_by_range(start=split_date)

Training Your First Model
^^^^^^^^^^^^^^^^^^^^^^^^^^

With maximum presets, creating and training a forecasting model requires minimal configuration:

.. code-block:: python

   # Create workflow with maximum presets
   config = ForecastingWorkflowConfig(
       model_type="xgboost",
       quantiles=[0.1, 0.5, 0.9],
       max_horizon=timedelta(hours=47),
       target_column="load"
   )
   
   workflow = create_forecasting_workflow(config)
   
   # Train the model
   fit_result = workflow.fit(
       data=train_data,
       data_val=test_data.filter_by_range(
           start=split_date, 
           end=split_date + timedelta(days=30)
       )
   )
   
   print(f"Training completed. Validation RMSE: {fit_result.metrics.rmse:.2f}")

Creating Forecasts
^^^^^^^^^^^^^^^^^^

Once trained, generating forecasts is straightforward:

.. code-block:: python

   # Create forecast for the next 24 hours
   forecast_start = datetime(2023, 11, 1)
   forecast_data = workflow.predict(
       data=test_data,
       forecast_start=forecast_start
   )
   
   # Access forecast results
   forecast_df = forecast_data.to_pandas()
   print(f"Generated {len(forecast_df)} forecast points")
   print(f"Forecast horizons: {forecast_data.horizons}")

Evaluating Results
^^^^^^^^^^^^^^^^^^

Evaluate your model's performance using built-in metrics:

.. code-block:: python

   # Score the model on test data
   test_metrics = workflow.score(test_data)
   
   print("Test Performance:")
   print(f"RMSE: {test_metrics.rmse:.2f}")
   print(f"MAE: {test_metrics.mae:.2f}")
   print(f"MAPE: {test_metrics.mape:.2f}%")
   
   # Get detailed metrics breakdown
   metrics_dict = test_metrics.to_dict()
   for metric_name, value in metrics_dict.items():
       print(f"{metric_name}: {value:.3f}")

Energy Component Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF can decompose energy forecasts into renewable and conventional components:

.. code-block:: python

   from openstef_models.models.component_splitting import LinearComponentSplitter
   
   # Create component splitter
   splitter = LinearComponentSplitter()
   
   # Fit splitter on training data (requires renewable generation features)
   splitter.fit(train_data)
   
   # Decompose forecast into components
   components = splitter.predict(forecast_data)
   
   # Access component forecasts
   components_df = components.to_pandas()
   print("Energy components:")
   print(components_df[['solar_component', 'wind_component', 'conventional_component']].head())

Backtesting with Multiple Models
---------------------------------

Production forecasting requires robust model comparison through backtesting. This example demonstrates the Liander 2024 benchmark approach using two different models.

Setting Up the Backtest
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_beam.benchmarking import SimpleTargetProvider
   from openstef_models.models import ForecastingModel, EnsembleModel
   from datetime import datetime, timedelta
   
   # Configure backtest period
   backtest_start = datetime(2024, 1, 1)
   backtest_end = datetime(2024, 6, 30)
   
   # Create two different model configurations
   xgboost_config = ForecastingWorkflowConfig(
       model_type="xgboost",
       quantiles=[0.1, 0.5, 0.9],
       max_horizon=timedelta(hours=47),
       target_column="load"
   )
   
   lgb_config = ForecastingWorkflowConfig(
       model_type="lightgbm", 
       quantiles=[0.1, 0.5, 0.9],
       max_horizon=timedelta(hours=47),
       target_column="load"
   )

Running Comparative Backtest
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Initialize models
   xgb_workflow = create_forecasting_workflow(xgboost_config)
   lgb_workflow = create_forecasting_workflow(lgb_config)
   
   models = {
       "XGBoost": xgb_workflow,
       "LightGBM": lgb_workflow
   }
   
   # Perform rolling backtest
   backtest_results = {}
   
   for model_name, workflow in models.items():
       print(f"Running backtest for {model_name}...")
       
       # Train on historical data
       train_end = backtest_start - timedelta(days=1)
       historical_data = dataset.filter_by_range(
           start=backtest_start - timedelta(days=365),
           end=train_end
       )
       
       workflow.fit(historical_data)
       
       # Generate forecasts for backtest period
       test_data = dataset.filter_by_range(
           start=backtest_start,
           end=backtest_end
       )
       
       forecasts = workflow.predict(test_data, forecast_start=backtest_start)
       metrics = workflow.score(test_data)
       
       backtest_results[model_name] = {
           'forecasts': forecasts,
           'metrics': metrics
       }

Comparing Model Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Compare model performance
   print("Backtest Results Comparison:")
   print("-" * 50)
   
   for model_name, results in backtest_results.items():
       metrics = results['metrics']
       print(f"{model_name}:")
       print(f"  RMSE: {metrics.rmse:.2f}")
       print(f"  MAE: {metrics.mae:.2f}")
       print(f"  MAPE: {metrics.mape:.2f}%")
       print()
   
   # Identify best performing model
   best_model = min(
       backtest_results.keys(),
       key=lambda x: backtest_results[x]['metrics'].rmse
   )
   print(f"Best performing model: {best_model}")

Advanced Customization
----------------------

For production deployments, you'll often need to customize OpenSTEF's behavior. This section covers advanced customization techniques.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Create custom data loading logic by implementing a target provider:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider
   from openstef_core.datasets import VersionedTimeSeriesDataset
   import pandas as pd
   
   class DatabaseTargetProvider(TargetProvider):
       """Custom target provider that loads data from a database."""
       
       def __init__(self, connection_string: str):
           self.connection_string = connection_string
       
       def get_targets(self, filter_args=None):
           """Return list of available forecast targets."""
           # Query database for available prediction jobs
           query = "SELECT DISTINCT location_id FROM energy_measurements"
           # Implementation depends on your database setup
           return self._execute_query(query)
       
       def get_measurements_for_target(self, target):
           """Load ground truth measurements for a target."""
           query = f"""
           SELECT timestamp, load, temperature, wind_speed
           FROM energy_measurements 
           WHERE location_id = '{target}'
           ORDER BY timestamp
           """
           df = self._execute_query(query)
           df.set_index('timestamp', inplace=True)
           
           return VersionedTimeSeriesDataset.from_pandas(
               df, 
               sample_interval=timedelta(hours=1)
           )
       
       def get_predictors_for_target(self, target):
           """Load predictor features for a target."""
           # Similar implementation for weather and other predictors
           pass
       
       def _execute_query(self, query):
           # Database connection and query execution logic
           pass

Custom Workflow Components
^^^^^^^^^^^^^^^^^^^^^^^^^^

Build custom forecasting workflows with specialized preprocessing and postprocessing:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.preprocessing import StandardScaler
   from openstef_models.postprocessing import QuantileClipper
   
   class ProductionForecastingWorkflow(CustomForecastingWorkflow):
       """Custom workflow with production-specific logic."""
       
       def __init__(self, model, custom_scaler=None):
           super().__init__(model=model)
           self.custom_scaler = custom_scaler or StandardScaler()
           self.clipper = QuantileClipper(min_value=0.0)
       
       def fit(self, data, data_val=None, data_test=None):
           """Custom training with specialized preprocessing."""
           # Apply custom preprocessing
           scaled_data = self._preprocess_training_data(data)
           
           # Call parent fit method
           result = super().fit(scaled_data, data_val, data_test)
           
           # Store preprocessing parameters
           self._save_preprocessing_state()
           
           return result
       
       def predict(self, data, forecast_start=None):
           """Custom prediction with postprocessing."""
           # Apply same preprocessing as training
           processed_data = self._preprocess_prediction_data(data)
           
           # Generate forecasts
           forecasts = super().predict(processed_data, forecast_start)
           
           # Apply custom postprocessing
           clipped_forecasts = self.clipper.transform(forecasts)
           
           return clipped_forecasts
       
       def _preprocess_training_data(self, data):
           """Apply custom preprocessing for training."""
           # Fit and transform scaler
           self.custom_scaler.fit(data)
           return self.custom_scaler.transform(data)
       
       def _preprocess_prediction_data(self, data):
           """Apply preprocessing for prediction."""
           # Transform using fitted scaler
           return self.custom_scaler.transform(data)

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^

Implement domain-specific feature engineering:

.. code-block:: python

   from openstef_models.feature_engineering import AbstractFeatureApplicator
   import pandas as pd
   import numpy as np
   
   class EnergyDomainFeatureApplicator(AbstractFeatureApplicator):
       """Custom feature applicator for energy forecasting."""
       
       def __init__(self, horizons, include_seasonal=True, include_weather_interactions=True):
           super().__init__(horizons)
           self.include_seasonal = include_seasonal
           self.include_weather_interactions = include_weather_interactions
       
       def add_features(self, df, pj=None):
           """Add domain-specific energy features."""
           df = df.copy()
           
           if self.include_seasonal:
               df = self._add_seasonal_features(df)
           
           if self.include_weather_interactions:
               df = self._add_weather_interactions(df)
           
           # Add load-specific features
           df = self._add_load_features(df)
           
           return df
       
       def _add_seasonal_features(self, df):
           """Add seasonal and calendar features."""
           df['hour_of_day'] = df.index.hour
           df['day_of_week'] = df.index.dayofweek
           df['month'] = df.index.month
           df['is_weekend'] = (df.index.dayofweek >= 5).astype(int)
           
           # Cyclical encoding
           df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
           df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)
           
           return df
       
       def _add_weather_interactions(self, df):
           """Add weather interaction features."""
           if 'temperature' in df.columns and 'wind_speed' in df.columns:
               df['temp_wind_interaction'] = df['temperature'] * df['wind_speed']
               df['cooling_degree_days'] = np.maximum(df['temperature'] - 18, 0)
               df['heating_degree_days'] = np.maximum(18 - df['temperature'], 0)
           
           return df
       
       def _add_load_features(self, df):
           """Add load-specific features."""
           if 'load' in df.columns:
               # Rolling statistics
               df['load_rolling_mean_24h'] = df['load'].rolling(24).mean()
               df['load_rolling_std_24h'] = df['load'].rolling(24).std()
               
               # Lag features
               df['load_lag_24h'] = df['load'].shift(24)
               df['load_lag_168h'] = df['load'].shift(168)  # Weekly lag
           
           return df

Integrating Custom Components
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Combine custom components into a complete production workflow:

.. code-block:: python

   # Create production workflow with custom components
   custom_feature_applicator = EnergyDomainFeatureApplicator(
       horizons=[timedelta(hours=h) for h in range(1, 48)],
       include_seasonal=True,
       include_weather_interactions=True
   )
   
   # Configure model with custom features
   production_config = ForecastingWorkflowConfig(
       model_type="xgboost",
       quantiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
       max_horizon=timedelta(hours=47),
       target_column="load",
       feature_applicator=custom_feature_applicator
   )
   
   # Create and train production workflow
   production_workflow = ProductionForecastingWorkflow(
       model=create_forecasting_workflow(production_config)
   )
   
   # Train with custom data provider
   db_provider = DatabaseTargetProvider("postgresql://user:pass@host:5432/db")
   targets = db_provider.get_targets()
   
   for target in targets:
       print(f"Training model for target: {target}")
       
       # Load data
       measurements = db_provider.get_measurements_for_target(target)
       predictors = db_provider.get_predictors_for_target(target)
       
       # Combine datasets
       training_data = measurements.merge(predictors)
       
       # Train model
       fit_result = production_workflow.fit(training_data)
       
       print(f"Training completed. RMSE: {fit_result.metrics.rmse:.2f}")

.. note::
   These advanced customization examples provide templates for production implementations. Adapt the code to match your specific data sources, business requirements, and infrastructure setup.

Next Steps
----------

After completing these tutorials, you're ready to explore:

- :doc:`../guides/use_cases` - Identify the best OpenSTEF approach for your specific forecasting scenario
- :doc:`../guides/how_to_guides` - Learn about deployment, data integration, and migration strategies  
- :doc:`../reference/concepts` - Deepen your understanding of forecasting concepts and model interpretation

For production deployments, consider the deployment patterns described in the how-to guides and review the architecture documentation to understand how OpenSTEF components interact in larger systems.