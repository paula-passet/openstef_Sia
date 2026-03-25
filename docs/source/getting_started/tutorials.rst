Tutorials
=========

This comprehensive tutorial guides you through OpenSTEF's core functionality, from your first forecast to advanced customization. Whether you're moving from the quickstart guide or preparing for production deployment, these examples demonstrate real-world usage patterns with the OpenSTEF machine learning library.

Getting Started with Maximum Presets
------------------------------------

The fastest way to explore OpenSTEF's capabilities is using maximum presets - pre-configured settings that handle most decisions automatically while you focus on understanding the workflow.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects time-indexed data with load measurements and weather information. Here's how to prepare your data:

.. code-block:: python

   import pandas as pd
   from openstef.data_classes import PredictionJobDataClass
   from openstef.pipeline import train_model, create_forecast
   
   # Load your historical data
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)
   
   # Ensure required columns are present
   # data should have: 'load' (target), weather columns like 'temp', 'windspeed_100m', 'radiation'
   print(f"Data shape: {data.shape}")
   print(f"Columns: {data.columns.tolist()}")
   
   # Create prediction job with maximum presets
   pj = PredictionJobDataClass(
       id="tutorial_forecast_001",
       name="Tutorial Energy Forecast",
       model="xgb",  # XGBoost with default hyperparameters
       resolution_minutes=15,  # 15-minute resolution
       horizon_minutes=2880,   # 48-hour forecast horizon
       lat=52.1326,           # Location coordinates
       lon=5.2913,
       quantiles=[0.1, 0.5, 0.9]  # Confidence intervals
   )

Training Your First Model
^^^^^^^^^^^^^^^^^^^^^^^^^

With data prepared and prediction job configured, training is straightforward:

.. code-block:: python

   # Train model using the pipeline
   model_specs = train_model.train_model_pipeline(
       pj=pj,
       input_data=data,
       mlflow_tracking_uri="file:./mlruns"  # Local MLflow tracking
   )
   
   print(f"Model trained successfully!")
   print(f"Model type: {model_specs.id}")
   print(f"Features used: {len(model_specs.feature_names)} features")

Creating Your First Forecast
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate forecasts using the trained model:

.. code-block:: python

   # Prepare recent data for forecasting (last few days)
   forecast_data = data.tail(1000)  # Use recent data for context
   
   # Create forecast
   forecast = create_forecast.create_forecast_pipeline(
       pj=pj,
       input_data=forecast_data,
       mlflow_tracking_uri="file:./mlruns"
   )
   
   # Examine forecast results
   print(f"Forecast shape: {forecast.shape}")
   print(f"Forecast columns: {forecast.columns.tolist()}")
   print(forecast.head())

Evaluating Results
^^^^^^^^^^^^^^^^^

Understanding forecast quality is crucial for production deployment:

.. code-block:: python

   from openstef.metrics import metrics
   
   # Assuming you have actual values to compare against
   actual_values = data['load'].tail(len(forecast))
   forecast_values = forecast['forecast']
   
   # Calculate key metrics
   mae = metrics.mean_absolute_error(actual_values, forecast_values)
   rmse = metrics.root_mean_squared_error(actual_values, forecast_values)
   mape = metrics.mean_absolute_percentage_error(actual_values, forecast_values)
   
   print(f"Mean Absolute Error: {mae:.2f}")
   print(f"Root Mean Square Error: {rmse:.2f}")
   print(f"Mean Absolute Percentage Error: {mape:.2f}%")

Energy Split Decomposition with DAZLS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's DAZLS (Domain Adaptation for Zero Shot Learning in Sequence) capability decomposes total energy forecasts into components like solar, wind, and other sources:

.. code-block:: python

   from openstef.pipeline import create_component_forecast
   
   # Prepare weather data for component forecasting
   weather_data = data[['radiation', 'windspeed_100m']].copy()
   
   # Create component forecast
   component_forecast = create_component_forecast.create_components_forecast_pipeline(
       pj=pj,
       input_data=forecast_data,
       weather_data=weather_data
   )
   
   # Examine component breakdown
   print("Component forecast columns:")
   for col in component_forecast.columns:
       if 'forecast_' in col:
           print(f"  {col}: {component_forecast[col].sum():.2f} total")

Backtesting Example
------------------

Backtesting validates model performance across historical periods. This example demonstrates a realistic backtest setup:

.. code-block:: python

   from openstef.pipeline import train_create_forecast_backtest
   from openstef.model_selection.model_selection import backtest_split_default
   from datetime import datetime, timedelta
   
   # Configure backtest parameters
   backtest_pj = PredictionJobDataClass(
       id="backtest_001",
       name="Backtest Validation",
       model="xgb",
       resolution_minutes=15,
       horizon_minutes=1440,  # 24-hour horizon for backtest
       lat=52.1326,
       lon=5.2913,
       quantiles=[0.1, 0.5, 0.9],
       backtest_split_func=backtest_split_default()
   )
   
   # Run backtest over 6 months of data
   backtest_data = data.loc['2024-01-01':'2024-06-30']
   
   backtest_results = train_create_forecast_backtest.train_create_forecast_backtest_pipeline(
       pj=backtest_pj,
       input_data=backtest_data,
       mlflow_tracking_uri="file:./mlruns"
   )
   
   # Analyze backtest performance
   print(f"Backtest completed over {len(backtest_results)} time periods")
   print(f"Average forecast accuracy: {backtest_results['forecast'].corr(backtest_results['realised']):.3f}")

Comparing Multiple Models
^^^^^^^^^^^^^^^^^^^^^^^^

Compare different algorithms to find the best performer for your data:

.. code-block:: python

   models_to_test = ['xgb', 'lgb', 'linear']
   model_results = {}
   
   for model_name in models_to_test:
       test_pj = backtest_pj.copy()
       test_pj.model = model_name
       test_pj.id = f"backtest_{model_name}"
       
       results = train_create_forecast_backtest.train_create_forecast_backtest_pipeline(
           pj=test_pj,
           input_data=backtest_data,
           mlflow_tracking_uri="file:./mlruns"
       )
       
       # Calculate performance metrics
       mae = metrics.mean_absolute_error(results['realised'], results['forecast'])
       model_results[model_name] = mae
       print(f"{model_name} MAE: {mae:.2f}")
   
   # Find best model
   best_model = min(model_results, key=model_results.get)
   print(f"Best performing model: {best_model}")

Advanced Customization
----------------------

For production deployments, you'll often need to customize OpenSTEF's behavior. These examples show common customization patterns.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^

Create custom data preparation logic for specialized data sources:

.. code-block:: python

   from openstef.feature_engineering.data_preparation import AbstractDataPreparation
   
   class CustomDataPreparation(AbstractDataPreparation):
       """Custom data preparation for specialized energy data sources."""
       
       def prepare_train_data(self, data, pj):
           """Prepare training data with custom preprocessing."""
           # Apply custom transformations
           processed_data = data.copy()
           
           # Example: Custom load normalization
           processed_data['load_normalized'] = (
               processed_data['load'] / processed_data['load'].rolling(24*4).mean()
           )
           
           # Add custom features
           processed_data['load_trend'] = (
               processed_data['load'].diff().rolling(12).mean()
           )
           
           return processed_data
       
       def prepare_forecast_data(self, data, pj):
           """Prepare forecast data with same transformations."""
           return self.prepare_train_data(data, pj)
   
   # Use custom data preparation
   from openstef.data_classes import DataPrepDataClass
   
   custom_pj = pj.copy()
   custom_pj.data_prep_class = DataPrepDataClass(
       klass="__main__.CustomDataPreparation"
   )

Custom Workflow Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Configure advanced model behavior and feature engineering:

.. code-block:: python

   from openstef.data_classes import ModelSpecificationDataClass
   
   # Define custom model specifications
   custom_model_specs = ModelSpecificationDataClass(
       id="custom_xgb_config",
       hyper_params={
           'n_estimators': 200,
           'max_depth': 8,
           'learning_rate': 0.1,
           'subsample': 0.8,
           'colsample_bytree': 0.8,
           'random_state': 42
       },
       feature_names=[
           'load_7d',  # 7-day lag
           'load_1d',  # 1-day lag
           'temp',     # Temperature
           'windspeed_100m',  # Wind speed
           'radiation',       # Solar radiation
           'hour',           # Hour of day
           'dayofweek'       # Day of week
       ]
   )
   
   # Apply custom specifications
   advanced_pj = pj.copy()
   advanced_pj.default_modelspecs = custom_model_specs

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^

Implement domain-specific features for your energy forecasting use case:

.. code-block:: python

   from openstef.feature_engineering.feature_adder import FeatureAdder
   
   class CustomEnergyFeatures(FeatureAdder):
       """Custom feature engineering for energy forecasting."""
       
       name = "custom_energy"
       
       def apply_features(self, data, pj=None):
           """Add custom energy-specific features."""
           data = data.copy()
           
           # Peak/off-peak indicator
           data['is_peak_hour'] = data.index.hour.isin([7, 8, 9, 17, 18, 19, 20])
           
           # Weekend indicator
           data['is_weekend'] = data.index.weekday >= 5
           
           # Seasonal energy demand patterns
           data['heating_degree_days'] = (18 - data['temp']).clip(lower=0)
           data['cooling_degree_days'] = (data['temp'] - 22).clip(lower=0)
           
           # Wind power estimation
           if 'windspeed_100m' in data.columns:
               # Simplified wind power curve
               wind_speed = data['windspeed_100m']
               data['wind_power_potential'] = (
                   (wind_speed >= 3) & (wind_speed <= 25)
               ) * (wind_speed ** 3) / 1000
           
           return data
   
   # Register and use custom features
   from openstef.feature_engineering.apply_features import apply_features
   
   # Apply custom features to your data
   enhanced_data = apply_features(
       data=data,
       pj=pj,
       feature_names=['custom_energy'] + pj.default_modelspecs.feature_names
   )

.. note::
   These advanced customization examples require understanding of your specific energy forecasting domain. Start with the maximum presets approach and gradually introduce customizations as your requirements become clearer.

The examples in this tutorial provide a foundation for using OpenSTEF in production environments. For deployment guidance, see the :doc:`../guides/how_to_guides` section. For understanding the underlying concepts, refer to :doc:`../reference/concepts`.