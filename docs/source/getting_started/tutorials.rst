Tutorials
=========

This comprehensive tutorial guides you through OpenSTEF's complete machine learning workflow, from basic usage to advanced customization. You'll learn how to train models, create forecasts, evaluate performance, and customize the library for production use.

These tutorials build on the :doc:`quickstart <quickstart>` guide and prepare you for implementing OpenSTEF in production environments. For specific deployment tasks, see the :doc:`../guides/how_to_guides`.

.. note::
   All examples use realistic data and parameters. The complete code examples are available in the `OpenSTEF offline examples repository <https://github.com/OpenSTEF/openstef-offline-example>`_.

First Steps with Maximum Presets
---------------------------------

OpenSTEF provides high-level pipelines that handle most machine learning complexity automatically. This section shows the complete workflow from data loading to forecast evaluation.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Start by loading your time series data into OpenSTEF's dataset format:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import ForecastInputDataset
   from openstef.pipeline import train_model, create_forecast
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Load your time series data
   data = pd.read_parquet("energy_data.parquet")
   
   # Create a ForecastInputDataset with required columns
   dataset = ForecastInputDataset(
       data=data,
       target_column="load",  # The column you want to forecast
       sample_interval="15min"
   )
   
   # Define prediction job configuration
   pj = PredictionJobDataClass(
       id=1,
       name="substation_forecast",
       model="xgb",  # XGBoost model
       resolution_minutes=15,
       forecast_type="demand",
       train_horizons_minutes=[15, 30, 45, 60]  # Multi-horizon forecast
   )

The dataset automatically validates your data structure and ensures consistent time intervals. OpenSTEF expects datetime-indexed data with your target variable and optional weather features.

Training Your Model
^^^^^^^^^^^^^^^^^^^

Train a model using OpenSTEF's automated pipeline:

.. code-block:: python

   # Train model with automatic feature engineering
   model_specs, trained_model, report = train_model.train_model_pipeline(
       pj=pj,
       input_data=dataset,
       mlflow_tracking_uri=None  # Set to enable MLflow tracking
   )
   
   # The pipeline automatically:
   # - Engineers time-based features (hour, day of week, etc.)
   # - Handles missing data
   # - Optimizes hyperparameters
   # - Validates model performance
   
   print(f"Model trained successfully: {model_specs.model_type}")
   print(f"Training R² score: {report['train_r2']:.3f}")
   print(f"Validation R² score: {report['validation_r2']:.3f}")

The training pipeline applies OpenSTEF's proven feature engineering automatically, including temporal features, lag features, and weather transformations if weather data is present.

Creating Forecasts
^^^^^^^^^^^^^^^^^^

Generate multi-horizon probabilistic forecasts:

.. code-block:: python

   from openstef.pipeline import create_forecast
   
   # Create forecast for next 24 hours
   forecast_dataset = create_forecast.create_forecast_pipeline(
       pj=pj,
       input_data=dataset,
       model_specs=model_specs,
       trained_model=trained_model
   )
   
   # Access forecast results
   forecast_df = forecast_dataset.data
   print(forecast_df.head())
   
   # Forecast includes:
   # - Point forecasts for each horizon
   # - Quantile estimates (10%, 25%, 75%, 90%)
   # - Confidence intervals
   # - Feature importance scores

OpenSTEF generates probabilistic forecasts with quantile estimates, enabling uncertainty quantification for operational decisions.

Evaluating Results
^^^^^^^^^^^^^^^^^^

Assess forecast quality using comprehensive metrics:

.. code-block:: python

   from openstef_beam.evaluation import ForecastEvaluator
   from openstef_beam.metrics import bias, mae, rmse
   
   # Create evaluator for comprehensive analysis
   evaluator = ForecastEvaluator()
   
   # Evaluate against actual values (assuming you have test data)
   evaluation_results = evaluator.evaluate_forecasts(
       forecasts=forecast_dataset,
       actuals=test_dataset,
       metrics=[bias, mae, rmse]
   )
   
   # Print key performance metrics
   for horizon in [15, 30, 45, 60]:
       results = evaluation_results.get_horizon_results(horizon)
       print(f"Horizon {horizon}min - MAE: {results.mae:.2f}, RMSE: {results.rmse:.2f}")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^

For renewable energy forecasting, decompose total load into components:

.. code-block:: python

   from openstef.pipeline import create_component_forecast
   
   # Decompose forecast into wind and solar components
   component_forecast = create_component_forecast.create_component_forecast_pipeline(
       pj=pj,
       input_data=dataset,
       model_specs=model_specs,
       trained_model=trained_model
   )
   
   # Access decomposed components
   components_df = component_forecast.data
   print("Component breakdown:")
   print(components_df[['wind_component', 'solar_component', 'other_component']].head())

This decomposition helps understand the contribution of different energy sources to total demand or generation.

Backtesting Example
-------------------

Backtesting evaluates how models would have performed in real operational conditions by simulating historical forecasting scenarios.

Setting Up Backtest Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Configure a realistic backtest using OpenSTEF's backtesting framework:

.. code-block:: python

   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline
   from openstef_beam.benchmarking import SimpleTargetProvider
   from datetime import datetime, timedelta
   
   # Configure backtest parameters
   backtest_config = BacktestConfig(
       start_date=datetime(2024, 1, 1),
       end_date=datetime(2024, 3, 31),
       retrain_frequency_days=30,  # Retrain monthly
       forecast_frequency_hours=1,  # Generate hourly forecasts
       initial_training_days=365   # Use 1 year for initial training
   )
   
   # Set up target provider for multiple prediction jobs
   target_config = {
       "data_dir": "backtest_data/",
       "targets": [
           {"name": "substation_a", "file": "substation_a.parquet"},
           {"name": "substation_b", "file": "substation_b.parquet"}
       ]
   }
   
   target_provider = SimpleTargetProvider(**target_config)

Running Multi-Model Comparison
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compare different models using the same backtest framework:

.. code-block:: python

   from openstef_models.models import XGBRegressorModel, LinearRegressionModel
   
   # Define models to compare
   models_to_test = {
       "xgboost": XGBRegressorModel(),
       "linear": LinearRegressionModel()
   }
   
   backtest_results = {}
   
   for model_name, model in models_to_test.items():
       # Create prediction job for this model
       pj_model = PredictionJobDataClass(
           id=1,
           name=f"backtest_{model_name}",
           model=model_name,
           resolution_minutes=15,
           forecast_type="demand",
           train_horizons_minutes=[15, 30, 45, 60]
       )
       
       # Run backtest
       pipeline = BacktestPipeline(
           config=backtest_config,
           forecaster=model
       )
       
       results = pipeline.run_backtest(
           prediction_job=pj_model,
           target_provider=target_provider
       )
       
       backtest_results[model_name] = results

Analyzing Backtest Results
^^^^^^^^^^^^^^^^^^^^^^^^^^

Compare model performance across the backtest period:

.. code-block:: python

   from openstef_beam.analysis import BacktestAnalyzer
   
   # Create analyzer for comprehensive comparison
   analyzer = BacktestAnalyzer()
   
   # Generate performance comparison
   comparison_report = analyzer.compare_models(backtest_results)
   
   print("Model Performance Comparison:")
   print(comparison_report.summary_table)
   
   # Analyze temporal patterns
   seasonal_analysis = analyzer.analyze_seasonal_performance(
       backtest_results,
       groupby="month"
   )
   
   print("\nSeasonal Performance Patterns:")
   for model_name, seasonal_metrics in seasonal_analysis.items():
       print(f"{model_name}: Best month = {seasonal_metrics.best_period}")

Advanced Customization
----------------------

For production deployments, you'll often need to customize OpenSTEF's behavior to match your specific requirements.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Create a custom target provider for your data infrastructure:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider
   from openstef_core.datasets import ForecastInputDataset
   import requests
   
   class APITargetProvider(TargetProvider):
       """Custom target provider that fetches data from an API."""
       
       def __init__(self, api_base_url: str, auth_token: str):
           self.api_base_url = api_base_url
           self.auth_token = auth_token
       
       def get_targets(self) -> list[str]:
           """Return list of available forecast targets."""
           response = requests.get(
               f"{self.api_base_url}/targets",
               headers={"Authorization": f"Bearer {self.auth_token}"}
           )
           return response.json()["targets"]
       
       def get_target_data(self, target_name: str) -> ForecastInputDataset:
           """Fetch data for a specific target."""
           response = requests.get(
               f"{self.api_base_url}/data/{target_name}",
               headers={"Authorization": f"Bearer {self.auth_token}"}
           )
           
           data = pd.DataFrame(response.json()["data"])
           data["datetime"] = pd.to_datetime(data["datetime"])
           data.set_index("datetime", inplace=True)
           
           return ForecastInputDataset(
               data=data,
               target_column="load",
               sample_interval="15min"
           )
   
   # Use your custom provider
   api_provider = APITargetProvider(
       api_base_url="https://api.yourcompany.com/energy",
       auth_token="your-api-token"
   )

Custom Workflow Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build a custom workflow that integrates with your existing systems:

.. code-block:: python

   from openstef.pipeline import train_model, create_forecast
   from openstef_core.datasets import ForecastInputDataset
   import logging
   
   class ProductionForecastWorkflow:
       """Custom workflow for production forecasting."""
       
       def __init__(self, data_source, model_store, notification_service):
           self.data_source = data_source
           self.model_store = model_store
           self.notification_service = notification_service
           self.logger = logging.getLogger(__name__)
       
       def run_daily_forecast(self, prediction_jobs: list):
           """Execute daily forecasting workflow."""
           
           for pj in prediction_jobs:
               try:
                   # Load latest data
                   dataset = self.data_source.get_latest_data(pj.name)
                   
                   # Check if model needs retraining
                   if self.should_retrain_model(pj):
                       self.logger.info(f"Retraining model for {pj.name}")
                       model_specs, trained_model, report = train_model.train_model_pipeline(
                           pj=pj,
                           input_data=dataset
                       )
                       
                       # Store updated model
                       self.model_store.save_model(pj.name, trained_model, model_specs)
                   else:
                       # Load existing model
                       trained_model, model_specs = self.model_store.load_model(pj.name)
                   
                   # Generate forecast
                   forecast = create_forecast.create_forecast_pipeline(
                       pj=pj,
                       input_data=dataset,
                       model_specs=model_specs,
                       trained_model=trained_model
                   )
                   
                   # Store forecast results
                   self.data_source.save_forecast(pj.name, forecast)
                   
                   self.logger.info(f"Forecast completed for {pj.name}")
                   
               except Exception as e:
                   self.logger.error(f"Forecast failed for {pj.name}: {e}")
                   self.notification_service.send_alert(pj.name, str(e))
       
       def should_retrain_model(self, pj) -> bool:
           """Determine if model needs retraining based on performance drift."""
           # Implement your retraining logic here
           last_retrain = self.model_store.get_last_retrain_date(pj.name)
           days_since_retrain = (datetime.now() - last_retrain).days
           return days_since_retrain >= 30

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering for domain-specific requirements:

.. code-block:: python

   from openstef_models.transforms import OpenstfRegressor
   from sklearn.base import BaseEstimator, TransformerMixin
   import pandas as pd
   
   class CustomFeatureTransformer(BaseEstimator, TransformerMixin):
       """Custom transformer for domain-specific features."""
       
       def __init__(self, holiday_calendar=None):
           self.holiday_calendar = holiday_calendar
       
       def fit(self, X, y=None):
           return self
       
       def transform(self, X):
           """Add custom features to the dataset."""
           X_transformed = X.copy()
           
           # Add holiday indicators
           if self.holiday_calendar:
               X_transformed['is_holiday'] = X_transformed.index.to_series().apply(
                   lambda x: x.date() in self.holiday_calendar
               ).astype(int)
           
           # Add industrial activity indicators
           X_transformed['is_business_day'] = (
               (X_transformed.index.weekday < 5) & 
               (~X_transformed.get('is_holiday', False))
           ).astype(int)
           
           # Add temperature-based cooling/heating degree days
           if 'temperature' in X_transformed.columns:
               X_transformed['cooling_degree_days'] = np.maximum(
                   X_transformed['temperature'] - 18, 0
               )
               X_transformed['heating_degree_days'] = np.maximum(
                   18 - X_transformed['temperature'], 0
               )
           
           return X_transformed
   
   # Integrate custom transformer into OpenSTEF pipeline
   class CustomOpenstfRegressor(OpenstfRegressor):
       """Extended regressor with custom feature engineering."""
       
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.custom_transformer = CustomFeatureTransformer(
               holiday_calendar=self.get_holiday_calendar()
           )
       
       def create_features(self, data):
           """Override feature creation to include custom features."""
           # Apply standard OpenSTEF features
           features = super().create_features(data)
           
           # Apply custom transformations
           features = self.custom_transformer.transform(features)
           
           return features

This tutorial covers OpenSTEF's complete workflow from basic usage to production customization. For deployment-specific guidance, see :doc:`../guides/how_to_guides`. For understanding core concepts, refer to :doc:`../reference/concepts`.