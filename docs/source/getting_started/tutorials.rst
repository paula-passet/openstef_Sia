Tutorials
=========

This comprehensive tutorial guides you through OpenSTEF's complete workflow, from your first forecast to advanced customization. You'll learn to train models, create forecasts, evaluate performance, and customize the library for production use.

Getting Started with Your First Forecast
-----------------------------------------

OpenSTEF makes it straightforward to create your first energy forecast using sensible defaults. This section walks through the complete process: loading data, training a model, generating forecasts, and evaluating results.

Setting Up Your Prediction Job
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every OpenSTEF workflow starts with defining a prediction job that specifies what you want to forecast and how:

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_pipeline_common
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Define your forecasting task
   pj = PredictionJobDataClass(
       id=1,
       model='xgb',  # XGBoost with default hyperparameters
       quantiles=[10, 50, 90],  # Probabilistic forecast with confidence intervals
       horizon_minutes=24*60,   # 24-hour ahead forecast
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       resolution_minutes=15,   # 15-minute intervals
       name="Tutorial_Forecast",
       save_train_forecasts=True  # Evaluate on training period
   )

Loading and Preparing Your Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects time series data with a datetime index and requires at minimum a target column (typically 'load') and weather features:

.. code-block:: python

   # Load your historical data
   # Data should include: datetime index, 'load' column, weather features
   data = pd.read_csv('your_data.csv', parse_dates=True, index_col=0)
   
   # Verify data structure
   print(f"Data shape: {data.shape}")
   print(f"Date range: {data.index.min()} to {data.index.max()}")
   print(f"Columns: {data.columns.tolist()}")
   
   # Remove incomplete recent data if needed
   data = data.iloc[:-96, :]  # Remove last 24 hours if incomplete

Training Your Model
^^^^^^^^^^^^^^^^^^^

With your data prepared, train a forecasting model using OpenSTEF's integrated pipeline:

.. code-block:: python

   # Train model with automatic feature engineering and validation
   model_specs, model, report = train_pipeline_common(
       pj=pj,
       input_data=data,
       mlflow_tracking_uri="file:./mlruns"  # Local MLflow tracking
   )
   
   print(f"Model trained successfully: {model_specs.id}")
   print(f"Training R²: {report['train']['r2']:.3f}")
   print(f"Validation R²: {report['validation']['r2']:.3f}")

Creating Forecasts
^^^^^^^^^^^^^^^^^^

Generate forecasts using your trained model with the most recent data:

.. code-block:: python

   # Prepare recent data for forecasting (last few days)
   forecast_input = data.tail(7*24*4)  # Last 7 days of 15-min data
   
   # Create forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=forecast_input,
       mlflow_tracking_uri="file:./mlruns"
   )
   
   # Display forecast results
   print(f"Forecast period: {forecast.index.min()} to {forecast.index.max()}")
   print(forecast[['forecast', 'quantile_P10', 'quantile_P90']].head())

Evaluating Model Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assess your model's accuracy using OpenSTEF's comprehensive evaluation metrics:

.. code-block:: python

   from openstef_beam.metrics import mae, rmae, r2
   
   # Extract validation predictions from training report
   val_predictions = report['validation']['predictions']
   val_actual = report['validation']['actual']
   
   # Calculate key metrics
   mae_score = mae(val_actual, val_predictions)
   rmae_score = rmae(val_actual, val_predictions)
   r2_score = r2(val_actual, val_predictions)
   
   print(f"Validation Metrics:")
   print(f"  MAE: {mae_score:.2f}")
   print(f"  rMAE: {rmae_score:.1%}")
   print(f"  R²: {r2_score:.3f}")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^

For renewable energy forecasts, decompose your predictions into solar and wind components:

.. code-block:: python

   from openstef.tasks.split_forecast import split_forecast_task
   from openstef.data_classes.task_context import TaskContext
   
   # Perform energy splitting (requires solar/wind features in data)
   context = TaskContext()  # Default context for standalone use
   
   try:
       split_results = split_forecast_task(pj, context)
       print("Energy split coefficients:")
       print(split_results[['solar_coef', 'wind_coef']].head())
   except Exception as e:
       print(f"Energy splitting requires solar/wind features: {e}")

Backtesting with Multiple Models
---------------------------------

Compare different forecasting approaches using OpenSTEF's backtesting framework. This example demonstrates the Liander 2024 benchmark comparing XGBoost models with different configurations.

Setting Up the Benchmark
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_beam.benchmarking import Benchmark
   from openstef_beam.benchmarking.target_provider import SimpleTargetProvider
   from openstef_beam.evaluation.metric_providers import RMAEProvider, MAEProvider
   
   # Configure benchmark with multiple models
   benchmark_config = {
       'models': [
           {
               'name': 'xgb_default',
               'model_type': 'xgb',
               'hyperparameters': {}  # Use defaults
           },
           {
               'name': 'xgb_optimized', 
               'model_type': 'xgb',
               'hyperparameters': {
                   'max_depth': 8,
                   'learning_rate': 0.1,
                   'n_estimators': 200
               }
           }
       ],
       'quantiles': [10, 50, 90],
       'horizon_minutes': 24*60
   }

Running the Backtest
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Set up target provider for your dataset
   target_provider = SimpleTargetProvider(
       data_path="path/to/liander_data",
       target_config="targets.yaml"
   )
   
   # Initialize benchmark
   benchmark = Benchmark(
       target_provider=target_provider,
       metric_providers=[RMAEProvider(), MAEProvider()],
       output_path="benchmark_results"
   )
   
   # Run comparison across all targets and models
   results = benchmark.run(
       models=benchmark_config['models'],
       start_date="2023-01-01",
       end_date="2023-12-31",
       cv_folds=5
   )

Analyzing Backtest Results
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Compare model performance
   summary = results.get_summary()
   print("Model Performance Comparison:")
   print(summary.groupby('model_name')[['rmae', 'mae', 'r2']].mean())
   
   # Identify best performing model per target
   best_models = results.get_best_models(metric='rmae')
   print(f"\nBest models by target:")
   for target, model in best_models.items():
       print(f"  {target}: {model}")
   
   # Visualize results
   results.plot_comparison(metric='rmae', save_path='model_comparison.png')

Advanced Customization
-----------------------

For production deployments, you'll often need to customize OpenSTEF's behavior. This section covers the most common customization patterns.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Create a custom data source by implementing the TargetProvider interface:

.. code-block:: python

   from openstef_beam.benchmarking.target_provider import TargetProvider
   from openstef_core.datasets import TimeSeriesDataset
   from pathlib import Path
   
   class DatabaseTargetProvider(TargetProvider):
       """Load targets from database instead of files."""
       
       def __init__(self, connection_string: str, table_name: str):
           super().__init__()
           self.connection_string = connection_string
           self.table_name = table_name
       
       def get_targets(self, filter_args=None):
           """Load target definitions from database."""
           # Connect to your database
           import sqlalchemy as sa
           engine = sa.create_engine(self.connection_string)
           
           query = f"SELECT * FROM {self.table_name}"
           if filter_args:
               # Add filtering logic
               pass
           
           targets_df = pd.read_sql(query, engine)
           return [self._row_to_target(row) for _, row in targets_df.iterrows()]
       
       def get_measurements(self, target, start_date, end_date):
           """Load measurement data for a specific target."""
           # Implement database query for measurements
           pass
       
       def get_predictors(self, target, start_date, end_date):
           """Load predictor data (weather, etc.) for forecasting."""
           # Implement database query for predictors
           pass

Custom Workflow Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Integrate OpenSTEF into existing workflows by customizing the core pipelines:

.. code-block:: python

   from openstef.pipeline.train_model import train_pipeline_common
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core
   import mlflow
   
   class CustomForecastWorkflow:
       """Custom workflow with preprocessing and postprocessing."""
       
       def __init__(self, config):
           self.config = config
           self.mlflow_uri = config.get('mlflow_uri', 'file:./mlruns')
       
       def preprocess_data(self, raw_data):
           """Apply custom data preprocessing."""
           # Remove outliers
           data = raw_data.copy()
           q99 = data['load'].quantile(0.99)
           data.loc[data['load'] > q99, 'load'] = q99
           
           # Add custom features
           data['hour_sin'] = np.sin(2 * np.pi * data.index.hour / 24)
           data['hour_cos'] = np.cos(2 * np.pi * data.index.hour / 24)
           
           return data
       
       def train_model(self, pj, raw_data):
           """Train model with custom preprocessing."""
           processed_data = self.preprocess_data(raw_data)
           
           return train_pipeline_common(
               pj=pj,
               input_data=processed_data,
               mlflow_tracking_uri=self.mlflow_uri
           )
       
       def create_forecast(self, pj, raw_data, postprocess=True):
           """Create forecast with optional postprocessing."""
           processed_data = self.preprocess_data(raw_data)
           
           # Load model from MLflow
           with mlflow.start_run():
               model = mlflow.sklearn.load_model(f"models:/{pj.name}/latest")
               model_specs = self._load_model_specs(pj)
           
           # Generate forecast
           forecast = create_forecast_pipeline_core(
               pj=pj,
               input_data=processed_data,
               model=model,
               model_specs=model_specs
           )
           
           if postprocess:
               forecast = self.postprocess_forecast(forecast)
           
           return forecast
       
       def postprocess_forecast(self, forecast):
           """Apply business rules to forecast."""
           # Ensure non-negative values
           forecast['forecast'] = forecast['forecast'].clip(lower=0)
           
           # Smooth extreme jumps
           forecast['forecast'] = forecast['forecast'].rolling(
               window=4, center=True
           ).mean().fillna(forecast['forecast'])
           
           return forecast

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend OpenSTEF's feature engineering with domain-specific features:

.. code-block:: python

   from openstef.feature_engineering.apply_features import apply_features
   
   def add_custom_features(data, pj):
       """Add custom features to the dataset."""
       # Start with OpenSTEF's standard features
       featured_data = apply_features(
           data=data,
           pj=pj,
           horizon=pj.horizon_minutes/60
       )
       
       # Add business-specific features
       featured_data['is_peak_hour'] = (
           (featured_data.index.hour >= 17) & 
           (featured_data.index.hour <= 20)
       ).astype(int)
       
       # Add seasonal decomposition
       from statsmodels.tsa.seasonal import seasonal_decompose
       if len(featured_data) > 365 * 24 * 4:  # Need enough data
           decomp = seasonal_decompose(
               featured_data['load'].dropna(),
               model='additive',
               period=24*4*7  # Weekly seasonality
           )
           featured_data['seasonal_component'] = decomp.seasonal
           featured_data['trend_component'] = decomp.trend
       
       # Add weather interaction features
       if 'temperature' in featured_data.columns and 'windspeed_100m' in featured_data.columns:
           featured_data['temp_wind_interaction'] = (
               featured_data['temperature'] * featured_data['windspeed_100m']
           )
       
       return featured_data
   
   # Use in your workflow
   def train_with_custom_features(pj, input_data):
       # Apply custom feature engineering
       featured_data = add_custom_features(input_data, pj)
       
       # Train with enhanced features
       return train_pipeline_common(
           pj=pj,
           input_data=featured_data,
           mlflow_tracking_uri="file:./mlruns"
       )

Next Steps
----------

You now have the foundation to use OpenSTEF effectively in production. For specific implementation tasks, see our :doc:`../guides/how_to_guides` covering deployment, data integration, and migration. To understand the concepts behind OpenSTEF's design, explore :doc:`../reference/concepts`.

For questions about advanced use cases or customization, visit our community channels linked in the main :doc:`../index`.