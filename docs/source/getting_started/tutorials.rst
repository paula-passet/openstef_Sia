Tutorials
=========

This comprehensive tutorial series guides you from your first OpenSTEF forecast through advanced production implementations. Each section builds on the previous, taking you from basic usage to sophisticated customization of the forecasting library.

First Steps with OpenSTEF
--------------------------

Let's start with a complete end-to-end example that demonstrates the core OpenSTEF workflow. This example uses maximum preset configurations to minimize setup complexity while showing all essential steps.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF works with time series data organized in the ``TimeSeriesDataset`` format. This ensures consistent sampling intervals and proper temporal alignment:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your energy consumption data
   data = pd.read_parquet('energy_data.parquet')
   data['timestamp'] = pd.to_datetime(data['timestamp'])
   data = data.set_index('timestamp')
   
   # Create a TimeSeriesDataset with 15-minute intervals
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15),
       target_column='load',  # Your energy consumption column
       check_frequency=True
   )

The dataset automatically validates temporal consistency and provides methods for data manipulation. Weather features, calendar information, and other predictors should be included as additional columns in your DataFrame.

Training Your First Model
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides ready-to-use forecasting models with sensible defaults. The ``ForecastingModel`` handles the complete pipeline from preprocessing to prediction:

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.forecasters.xgboost import XGBoostForecaster
   from openstef_models.preprocessing import StandardPreprocessingPipeline
   
   # Configure the complete forecasting pipeline
   model = ForecastingModel(
       forecaster=XGBoostForecaster(
           max_horizon=timedelta(hours=47),  # Forecast up to 47 hours ahead
           quantiles=[0.1, 0.5, 0.9]  # Probabilistic forecasts
       ),
       preprocessing=StandardPreprocessingPipeline(),
       cutoff_history=timedelta(days=14)  # Remove incomplete lag features
   )
   
   # Train the model on your dataset
   fit_result = model.fit(dataset)
   print(f"Training completed. R² score: {fit_result.metrics.r2:.3f}")

The training process automatically splits your data into train/validation/test sets, applies feature engineering, and fits the underlying XGBoost model. The ``fit_result`` contains detailed metrics and model diagnostics.

Creating Forecasts
^^^^^^^^^^^^^^^^^^^

Once trained, the model can generate forecasts for new time periods. OpenSTEF handles the complexity of multi-horizon predictions and uncertainty quantification:

.. code-block:: python

   from datetime import datetime
   
   # Generate forecasts starting from a specific time
   forecast_start = datetime(2024, 1, 15, 0, 0)
   forecasts = model.predict(dataset, forecast_start=forecast_start)
   
   # Access forecast results
   forecast_df = forecasts.to_pandas()
   print(f"Generated {len(forecast_df)} forecast points")
   print(f"Forecast horizons: {forecasts.horizons}")
   print(f"Available quantiles: {forecasts.quantiles}")

The forecast dataset contains predictions for multiple horizons (lead times) and quantiles. This enables both point forecasts (median) and uncertainty intervals for risk assessment.

Evaluating Results
^^^^^^^^^^^^^^^^^^

OpenSTEF includes specialized metrics for energy forecasting evaluation. These metrics account for the operational challenges of energy systems:

.. code-block:: python

   from openstef_beam.metrics import rmae, confusion_matrix, crps
   
   # Evaluate model performance on test data
   test_metrics = model.score(dataset)
   print(f"Test RMAE: {test_metrics.rmae:.3f}")
   print(f"Test R²: {test_metrics.r2:.3f}")
   
   # Detailed evaluation for specific use cases
   y_true = dataset.target_series
   y_pred = forecasts.select_quantile(0.5).target_series  # Median forecast
   
   # Relative Mean Absolute Error (industry standard)
   rmae_score = rmae(y_true, y_pred)
   print(f"RMAE: {rmae_score:.3f}")
   
   # Peak detection performance (critical for congestion management)
   threshold = y_true.quantile(0.95)  # Top 5% as peaks
   cm = confusion_matrix(y_true, y_pred, threshold=threshold)
   print(f"Peak detection precision: {cm.precision:.3f}")

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For renewable energy integration, OpenSTEF can decompose total load into components like solar and wind contributions:

.. code-block:: python

   from openstef_models.models.component_splitting import LinearComponentSplitter
   
   # Configure component splitter
   splitter = LinearComponentSplitter()
   
   # Decompose forecasts into energy components
   components = splitter.predict(forecasts)
   
   # Access individual components
   component_df = components.to_pandas()
   solar_forecast = component_df['solar_component']
   wind_forecast = component_df['wind_component']
   
   print(f"Solar contribution: {solar_forecast.mean():.1f} MW average")
   print(f"Wind contribution: {wind_forecast.mean():.1f} MW average")

This decomposition helps grid operators understand the renewable energy mix and plan accordingly for variability management.

Backtesting with Real Data
---------------------------

Production forecasting requires rigorous validation through backtesting. OpenSTEF provides comprehensive benchmarking tools that simulate realistic operational conditions.

Liander 2024 Benchmark Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Liander 2024 dataset provides a standardized benchmark for comparing forecasting approaches. This example shows how to run backtests with multiple models:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline, SimpleTargetProvider
   from openstef_beam.benchmarking import LocalBenchmarkStorage
   from openstef_models.forecasters import XGBoostForecaster, LinearForecaster
   from pathlib import Path
   
   # Configure data source
   target_provider = SimpleTargetProvider(
       config_path=Path("liander_2024/targets.yaml"),
       data_path=Path("liander_2024/data/")
   )
   
   # Set up result storage
   storage = LocalBenchmarkStorage(base_path=Path("benchmark_results/"))
   
   # Define forecasting approaches to compare
   def create_xgboost_model(context):
       return ForecastingModel(
           forecaster=XGBoostForecaster(
               max_horizon=timedelta(hours=47),
               quantiles=[0.1, 0.5, 0.9]
           ),
           preprocessing=StandardPreprocessingPipeline()
       )
   
   def create_linear_model(context):
       return ForecastingModel(
           forecaster=LinearForecaster(
               max_horizon=timedelta(hours=47)
           ),
           preprocessing=StandardPreprocessingPipeline()
       )

Setting Up the Benchmark Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The benchmark pipeline orchestrates training and evaluation across multiple targets and time periods:

.. code-block:: python

   from openstef_beam.benchmarking.config import BacktestConfig
   from datetime import date
   
   # Configure backtesting parameters
   backtest_config = BacktestConfig(
       start_date=date(2024, 1, 1),
       end_date=date(2024, 3, 31),
       forecast_frequency=timedelta(hours=1),
       retrain_frequency=timedelta(days=7)
   )
   
   # Create benchmark pipeline
   pipeline = BenchmarkPipeline(
       backtest_config=backtest_config,
       target_provider=target_provider,
       storage=storage,
       forecaster_factories={
           'xgboost': create_xgboost_model,
           'linear': create_linear_model
       }
   )
   
   # Execute benchmark across all targets
   results = pipeline.run()
   print(f"Completed benchmark on {len(results)} targets")

Running and Analyzing Results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The benchmark generates comprehensive evaluation reports comparing model performance:

.. code-block:: python

   from openstef_beam.benchmarking import read_evaluation_reports
   
   # Load benchmark results
   targets = target_provider.get_targets()
   reports = read_evaluation_reports(
       targets=targets,
       storage=storage,
       forecaster_names=['xgboost', 'linear']
   )
   
   # Compare model performance
   for target_name, report in reports.items():
       xgb_rmae = report['xgboost']['metrics']['rmae']
       linear_rmae = report['linear']['metrics']['rmae']
       improvement = (linear_rmae - xgb_rmae) / linear_rmae * 100
       
       print(f"{target_name}: XGBoost improves RMAE by {improvement:.1f}%")
   
   # Aggregate results across all targets
   avg_xgb_rmae = sum(r['xgboost']['metrics']['rmae'] for r in reports.values()) / len(reports)
   avg_linear_rmae = sum(r['linear']['metrics']['rmae'] for r in reports.values()) / len(reports)
   
   print(f"\nOverall average RMAE:")
   print(f"XGBoost: {avg_xgb_rmae:.3f}")
   print(f"Linear: {avg_linear_rmae:.3f}")

Advanced Customization
-----------------------

Production deployments often require customization beyond the standard presets. OpenSTEF's modular architecture supports extensive customization while maintaining reliability and performance.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^^

For integration with existing data systems, you can create custom target providers that load data from databases, APIs, or other sources:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider, BenchmarkTarget
   from openstef_core.datasets import TimeSeriesDataset
   import sqlalchemy as sa
   
   class DatabaseTargetProvider(TargetProvider):
       def __init__(self, connection_string: str, region: str):
           super().__init__()
           self.engine = sa.create_engine(connection_string)
           self.region = region
       
       def get_targets(self, filter_args=None):
           # Query database for available forecasting targets
           query = """
           SELECT substation_id, name, latitude, longitude, capacity_mw
           FROM substations 
           WHERE region = %s AND active = true
           """
           
           targets = []
           with self.engine.connect() as conn:
               result = conn.execute(sa.text(query), (self.region,))
               for row in result:
                   targets.append(BenchmarkTarget(
                       name=f"substation_{row.substation_id}",
                       description=f"Load forecast for {row.name}",
                       group_name=self.region,
                       latitude=row.latitude,
                       longitude=row.longitude,
                       capacity_mw=row.capacity_mw
                   ))
           
           return targets
       
       def get_measurements(self, target: BenchmarkTarget, 
                          start_date: date, end_date: date) -> TimeSeriesDataset:
           # Load historical measurements from database
           query = """
           SELECT timestamp, load_mw, temperature, wind_speed, solar_irradiance
           FROM measurements 
           WHERE substation_id = %s AND timestamp BETWEEN %s AND %s
           ORDER BY timestamp
           """
           
           substation_id = target.name.split('_')[1]
           df = pd.read_sql(
               sa.text(query), 
               self.engine, 
               params=(substation_id, start_date, end_date)
           )
           
           return TimeSeriesDataset(
               data=df.set_index('timestamp'),
               sample_interval=timedelta(minutes=15),
               target_column='load_mw'
           )

Custom Workflow Implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For complex production scenarios, you can implement custom workflows that integrate with existing systems and add specialized logic:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow, ForecastingCallback
   from openstef_models.models import ForecastingModel
   import logging
   
   class ProductionForecastingCallback(ForecastingCallback):
       def __init__(self, notification_service, model_registry):
           self.notification_service = notification_service
           self.model_registry = model_registry
           
       def on_fit_start(self, workflow, data):
           logging.info(f"Starting model training with {len(data)} samples")
           
       def on_fit_complete(self, workflow, data, result):
           # Validate model performance before deployment
           if result.metrics.r2 < 0.7:
               raise ValueError(f"Model R² {result.metrics.r2:.3f} below threshold")
           
           # Register model for production use
           model_id = self.model_registry.register_model(
               workflow.model, 
               metrics=result.metrics
           )
           logging.info(f"Registered model {model_id} with R² {result.metrics.r2:.3f}")
           
       def on_predict_complete(self, workflow, data, forecast):
           # Send alerts for unusual forecasts
           max_forecast = forecast.select_quantile(0.9).target_series.max()
           if max_forecast > workflow.model.capacity_threshold:
               self.notification_service.send_alert(
                   f"High load forecast: {max_forecast:.1f} MW"
               )
   
   # Create custom workflow with callbacks
   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[ProductionForecastingCallback(notification_service, model_registry)]
   )
   
   # Use in production pipeline
   fit_result = workflow.fit(training_data)
   forecasts = workflow.predict(forecast_data)

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Advanced use cases may require specialized feature engineering beyond the standard preprocessing pipeline:

.. code-block:: python

   from openstef_models.preprocessing import BasePreprocessingPipeline
   from openstef_core.datasets import TimeSeriesDataset
   import numpy as np
   
   class AdvancedPreprocessingPipeline(BasePreprocessingPipeline):
       def __init__(self, include_topology_features: bool = False):
           super().__init__()
           self.include_topology_features = include_topology_features
           
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Apply standard preprocessing first
           processed_data = super().transform(data)
           df = processed_data.to_pandas()
           
           # Add custom weather interaction features
           if 'temperature' in df.columns and 'humidity' in df.columns:
               df['heat_index'] = self._calculate_heat_index(
                   df['temperature'], df['humidity']
               )
           
           # Add grid topology features if available
           if self.include_topology_features and 'voltage_level' in df.columns:
               df['topology_risk'] = self._calculate_topology_risk(
                   df['voltage_level'], df['load']
               )
           
           # Add seasonal decomposition features
           df['trend'] = self._extract_trend(df['load'])
           df['seasonal'] = self._extract_seasonal(df['load'])
           
           return processed_data.copy_with(df)
       
       def _calculate_heat_index(self, temp: pd.Series, humidity: pd.Series) -> pd.Series:
           # Simplified heat index calculation
           return temp + 0.5 * (humidity - 50) / 100 * temp
       
       def _calculate_topology_risk(self, voltage: pd.Series, load: pd.Series) -> pd.Series:
           # Custom topology-based risk indicator
           normalized_load = load / load.rolling(window=24*4).mean()  # 24-hour rolling mean
           voltage_stability = voltage / voltage.rolling(window=4).std()  # 1-hour stability
           return normalized_load * (1 / voltage_stability)
       
       def _extract_trend(self, series: pd.Series) -> pd.Series:
           # Simple trend extraction using rolling statistics
           return series.rolling(window=24*4*7, center=True).mean()  # Weekly trend
       
       def _extract_seasonal(self, series: pd.Series) -> pd.Series:
           # Extract daily seasonal pattern
           return series.groupby(series.index.hour).transform('mean')

This advanced preprocessing pipeline demonstrates how to extend OpenSTEF's capabilities with domain-specific features while maintaining compatibility with the existing model architecture.

The modular design ensures that custom components integrate seamlessly with standard OpenSTEF workflows, enabling gradual migration from prototype to production systems.