Tutorials
=========

This page provides comprehensive tutorials for OpenSTEF, a Python machine learning library for short-term energy forecasting. These tutorials guide you from first use to production implementation, covering essential workflows, backtesting, and advanced customization.

First Use with Maximum Presets
-------------------------------

This tutorial demonstrates the complete OpenSTEF workflow using default settings to get you started quickly. You'll learn to load data, train a model, create forecasts, evaluate results, and perform energy split decomposition.

Setting Up Your Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, import the necessary packages and configure plotting:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.metrics import metrics
   
   # Set plotly as the default pandas plotting backend
   pd.options.plotting.backend = 'plotly'

Defining the Prediction Job
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF uses prediction jobs to define model properties and forecasting parameters:

.. code-block:: python

   # Define properties of training/prediction
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',  # XGBoost model
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],  # Confidence intervals
       forecast_type="demand",
       lat=53.0,  # Used for solar feature calculations
       lon=5.7,   # Used for solar feature calculations
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=15,  # 15-minute intervals
       name="tutorial_first_use"
   )

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^

Load your data from CSV files containing load, weather, and energy market data:

.. code-block:: python

   # Load input data with load, weather, and market information
   input_data = pd.read_csv("data/input_data_287.csv", 
                           index_col=0, 
                           parse_dates=True)
   
   # Split data for training and testing
   train_data = input_data[:-192]  # All except final 192 rows
   test_data = input_data[-192:]   # Final 192 rows (8 days)
   
   # Prepare forecast data by clearing load values for forecast period
   to_forecast_data = input_data.copy()
   to_forecast_data.loc[test_data.index, 'load'] = np.nan

Training the Model
^^^^^^^^^^^^^^^^^^

Train your forecasting model using the training pipeline:

.. code-block:: python

   # Set MLflow tracking URI for model storage
   mlflow_tracking_uri = "./mlflow_trained_models"
   
   # Train the model
   trained_model, model_specs, report = train_model_pipeline(
       pj=pj,
       input_data=train_data,
       mlflow_tracking_uri=mlflow_tracking_uri
   )
   
   print(f"Model trained successfully. Report: {report}")

Creating Forecasts
^^^^^^^^^^^^^^^^^^

Generate forecasts using the trained model:

.. code-block:: python

   # Create forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=to_forecast_data,
       mlflow_tracking_uri=mlflow_tracking_uri
   )
   
   print(f"Forecast created with {len(forecast)} data points")

Evaluating Results
^^^^^^^^^^^^^^^^^^

Assess forecast quality using OpenSTEF's built-in metrics:

.. code-block:: python

   # Extract realized values for comparison
   realized = input_data.loc[test_data.index, 'load']
   forecast_values = forecast['forecast']
   
   # Calculate evaluation metrics
   rmse_score = metrics.rmse(realized, forecast_values)
   mae_score = metrics.mae(realized, forecast_values)
   bias_score = metrics.bias(realized, forecast_values)
   
   print(f"RMSE: {rmse_score:.2f}")
   print(f"MAE: {mae_score:.2f}")
   print(f"Bias: {bias_score:.2f}%")
   
   # Visualize results
   comparison_df = pd.DataFrame({
       'Realized': realized,
       'Forecast': forecast_values
   })
   comparison_df.plot(title="Forecast vs Realized Load")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^

Decompose forecasts into renewable energy components:

.. code-block:: python

   from openstef.tasks.split_forecast import split_forecast_task
   
   # Perform energy splitting to identify wind and solar components
   splitting_coefficients = split_forecast_task(pj, context={'data': input_data})
   
   print("Energy splitting coefficients:")
   print(splitting_coefficients)

Backtesting Example
-------------------

Backtesting evaluates how your model would have performed historically by simulating real-world operational conditions. This example uses the Liander 2024 benchmark dataset.

Setting Up the Backtest
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline.train_create_forecast_backtest import train_model_and_forecast_back_test
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   
   # Define prediction job for backtesting
   backtest_pj = PredictionJobDataClass(
       id=288,
       model='xgb',
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=2880,
       resolution_minutes=15,
       name="liander_backtest_xgb"
   )

Running the Backtest
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Load historical data for backtesting
   backtest_data = pd.read_csv("data/liander_2024_data.csv", 
                              index_col=0, 
                              parse_dates=True)
   
   # Run backtest with periodic model retraining
   backtest_results = train_model_and_forecast_back_test(
       pj=backtest_pj,
       input_data=backtest_data,
       mlflow_tracking_uri="./backtest_models",
       n_folds=10,  # Number of backtest folds
       retrain_interval_days=30  # Retrain every 30 days
   )

Comparing Multiple Models
^^^^^^^^^^^^^^^^^^^^^^^^^

Compare XGBoost and Linear Regression models:

.. code-block:: python

   # Define second prediction job with linear regression
   linear_pj = PredictionJobDataClass(
       id=289,
       model='linear',
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=2880,
       resolution_minutes=15,
       name="liander_backtest_linear"
   )
   
   # Run backtest for linear model
   linear_results = train_model_and_forecast_back_test(
       pj=linear_pj,
       input_data=backtest_data,
       mlflow_tracking_uri="./backtest_models",
       n_folds=10,
       retrain_interval_days=30
   )
   
   # Compare results
   xgb_rmse = metrics.rmse(backtest_results['realized'], backtest_results['forecast'])
   linear_rmse = metrics.rmse(linear_results['realized'], linear_results['forecast'])
   
   print(f"XGBoost RMSE: {xgb_rmse:.2f}")
   print(f"Linear RMSE: {linear_rmse:.2f}")

Advanced Customization
----------------------

For production deployments, you may need to customize OpenSTEF's behavior. This section covers custom target providers, workflows, and feature engineering.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Create a custom target provider for specialized data sources:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider
   from openstef_core.base_model import BaseConfig
   
   class CustomTargetProvider(TargetProvider):
       """Custom target provider for proprietary data sources."""
       
       def __init__(self, data_source_config: dict):
           super().__init__()
           self.config = data_source_config
       
       def get_targets(self, filter_args=None):
           """Load targets from custom data source."""
           # Implement your custom data loading logic
           targets = []
           for location_id in self.config['location_ids']:
               target = {
                   'id': location_id,
                   'name': f"Location_{location_id}",
                   'lat': self.config['locations'][location_id]['lat'],
                   'lon': self.config['locations'][location_id]['lon']
               }
               targets.append(target)
           return targets
       
       def load_data(self, target):
           """Load time series data for a specific target."""
           # Implement your data loading logic
           # Return pandas DataFrame with required columns
           pass

Custom Workflow
^^^^^^^^^^^^^^^

Build a custom workflow that integrates with your existing systems:

.. code-block:: python

   from openstef.feature_engineering.apply_features import apply_features
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   class CustomForecastingWorkflow:
       """Custom workflow integrating OpenSTEF with external systems."""
       
       def __init__(self, config):
           self.config = config
           self.mlflow_uri = config['mlflow_tracking_uri']
       
       def preprocess_data(self, raw_data):
           """Custom preprocessing steps."""
           # Apply your domain-specific preprocessing
           processed_data = raw_data.copy()
           
           # Remove outliers using custom logic
           processed_data = self.remove_outliers(processed_data)
           
           # Apply custom data quality checks
           processed_data = self.validate_data_quality(processed_data)
           
           return processed_data
       
       def train_and_forecast(self, pj, raw_data):
           """Complete training and forecasting workflow."""
           # Preprocess data
           processed_data = self.preprocess_data(raw_data)
           
           # Train model
           model, specs, report = train_model_pipeline(
               pj=pj,
               input_data=processed_data,
               mlflow_tracking_uri=self.mlflow_uri
           )
           
           # Create forecast
           forecast = create_forecast_pipeline(
               pj=pj,
               input_data=processed_data,
               mlflow_tracking_uri=self.mlflow_uri
           )
           
           # Post-process results
           final_forecast = self.postprocess_forecast(forecast)
           
           return final_forecast, report
       
       def remove_outliers(self, data):
           """Custom outlier detection and removal."""
           # Implement your outlier detection logic
           return data
       
       def validate_data_quality(self, data):
           """Custom data quality validation."""
           # Implement your validation logic
           return data
       
       def postprocess_forecast(self, forecast):
           """Custom post-processing of forecast results."""
           # Apply business rules or adjustments
           return forecast

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering with domain-specific features:

.. code-block:: python

   from openstef.feature_engineering.apply_features import apply_features
   
   def add_custom_features(data, pj):
       """Add custom features to the dataset."""
       # Start with standard OpenSTEF features
       enhanced_data = apply_features(data, pj)
       
       # Add custom industrial activity features
       enhanced_data['is_industrial_peak'] = (
           (enhanced_data.index.hour >= 8) & 
           (enhanced_data.index.hour <= 17) &
           (enhanced_data.index.weekday < 5)
       ).astype(int)
       
       # Add custom weather interaction features
       if 'radiation' in enhanced_data.columns and 'T' in enhanced_data.columns:
           enhanced_data['temp_radiation_interaction'] = (
               enhanced_data['T'] * enhanced_data['radiation']
           )
       
       # Add custom seasonal features
       enhanced_data['heating_degree_days'] = np.maximum(
           18 - enhanced_data.get('T', 18), 0
       )
       
       # Add custom lag features for specific use case
       enhanced_data['load_lag_2d'] = enhanced_data['load'].shift(2 * 24 * 4)  # 2 days
       enhanced_data['load_lag_1w'] = enhanced_data['load'].shift(7 * 24 * 4)  # 1 week
       
       return enhanced_data
   
   # Usage in custom workflow
   def custom_train_with_features(pj, input_data):
       """Train model with custom features."""
       # Apply custom feature engineering
       featured_data = add_custom_features(input_data, pj)
       
       # Train model with enhanced features
       model, specs, report = train_model_pipeline(
           pj=pj,
           input_data=featured_data,
           mlflow_tracking_uri="./custom_models"
       )
       
       return model, specs, report

.. note::
   
   When implementing custom workflows, ensure your data maintains the required OpenSTEF format with proper time indexing and column naming conventions.

Next Steps
----------

After completing these tutorials, you're ready to implement OpenSTEF in production environments. Consider exploring:

- :doc:`../guides/how_to_guides` for specific deployment scenarios
- :doc:`../guides/use_cases` to identify the best approach for your application
- :doc:`../reference/concepts` for deeper understanding of forecasting principles

For questions or community support, visit our GitHub repository or join the OpenSTEF community discussions.