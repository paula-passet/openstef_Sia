Comprehensive Tutorials
=======================


Complete Forecasting Workflow
-----------------------------


This tutorial demonstrates OpenSTEF's complete forecasting workflow from data preparation to model evaluation. You'll learn to use the library's pipelines for training models, creating forecasts, and assessing performance using realistic energy load data. The workflow covers data loading, feature engineering, model training with hyperparameter optimization, forecast generation, and comprehensive evaluation metrics.


.. code-block:: python

   import pandas as pd
   from openstef.pipeline import train_model, create_forecast
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Load example data
   data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)

   # Define prediction job configuration
   pj = PredictionJobDataClass(
       id=123,
       model='xgb',
       hyper_params={},
       feature_names=['T-1d', 'radiation', 'windspeed']
   )

   # Train model
   train_data, val_data, test_data = train_model.train_model_pipeline(
       pj=pj,
       input_data=data
   )

   # Create forecast
   forecast_data = create_forecast.create_forecast_pipeline(
       pj=pj,
       input_data=data
   )

   # Evaluate results
   mae = abs(test_data['forecast'] - test_data['load']).mean()
   print(f"Mean Absolute Error: {mae:.2f}")


Energy Split Decomposition Analysis
-----------------------------------


Energy split decomposition analyzes forecast components by separating total energy predictions into constituent parts like wind, solar, and base load. This technique helps users understand which energy sources contribute to forecasts and identify model behavior patterns. The LinearComponentSplitter in OpenSTEF provides this functionality through linear regression methods that decompose energy predictions into interpretable components.


.. code-block:: python

   from openstef_models.models.component_splitting import LinearComponentSplitter
   from openstef_models.data_classes import TimeSeriesDataset
   import pandas as pd

   # Prepare data with required columns: load, wind_ref, pv_ref, tdcv columns
   data = pd.DataFrame({
       'load': [100, 120, 90, 110],
       'wind_ref': [0.3, 0.7, 0.1, 0.5],
       'pv_ref': [0.2, 0.8, 0.0, 0.6],
       'T-1d': [95, 115, 85, 105],
       'T-7d': [98, 118, 88, 108]
   })

   # Create dataset and splitter
   dataset = TimeSeriesDataset(data=data)
   splitter = LinearComponentSplitter()

   # Perform energy split decomposition
   components = splitter.predict(dataset)

   # Access wind and solar components
   wind_component = components.wind
   solar_component = components.solar

   # View decomposition results
   print(f"Wind contribution: {wind_component.mean():.2f} MW")
   print(f"Solar contribution: {solar_component.mean():.2f} MW")
   print(f"Total renewable: {(wind_component + solar_component).mean():.2f} MW")


Backtesting with Multiple Models
--------------------------------


Backtesting evaluates forecasting model performance using historical data to simulate real-world conditions. OpenSTEF provides comprehensive backtesting functionality through benchmark examples that demonstrate model comparison workflows. The Liander 2024 dataset serves as a realistic benchmark for testing different forecasting approaches, allowing users to compare model performance using standardized evaluation metrics and data preprocessing steps.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.model.model_creator import ModelCreator
   from openstef.validation.validation import validate_forecast
   from openstef.datasets import load_liander_2024_data

   # Load Liander 2024 dataset
   data = load_liander_2024_data()
   train_data = data[data.index < '2024-06-01']
   test_data = data[data.index >= '2024-06-01']

   # Create prediction job
   pj = PredictionJobDataClass(
       id=123,
       name="backtest_comparison",
       model="xgb",
       horizon_minutes=15,
       train_components=0.95
   )

   # Model 1: XGBoost
   model_creator_xgb = ModelCreator(pj)
   model_xgb = model_creator_xgb.create_model(train_data)
   forecast_xgb = model_xgb.predict(test_data)

   # Model 2: Linear Regression
   pj.model = "linear"
   model_creator_lr = ModelCreator(pj)
   model_lr = model_creator_lr.create_model(train_data)
   forecast_lr = model_lr.predict(test_data)

   # Compare results
   metrics_xgb = validate_forecast(forecast_xgb, test_data['load'])
   metrics_lr = validate_forecast(forecast_lr, test_data['load'])

   print(f"XGBoost MAE: {metrics_xgb['MAE']:.2f}")
   print(f"Linear Regression MAE: {metrics_lr['MAE']:.2f}")


Custom Target Provider Implementation
-------------------------------------


Custom target providers enable integration with organization-specific data sources and evaluation requirements that differ from standard benchmark datasets. Create custom providers when your production data resides in proprietary databases, requires specialized preprocessing, or needs domain-specific evaluation metrics. The TargetProvider interface allows you to define how OpenSTEF accesses measurements, predictors, and evaluation criteria for your unique forecasting scenarios.


.. code-block:: python

   from pathlib import Path
   from typing import List
   import pandas as pd
   from openstef_beam.benchmarking.target_provider import TargetProvider
   from openstef_beam.benchmarking.benchmark_target import BenchmarkTarget
   from openstef_beam.benchmarking.versioned_time_series_dataset import VersionedTimeSeriesDataset
   from openstef_beam.benchmarking.metric_provider import MetricProvider


   class CustomTargetProvider(TargetProvider[BenchmarkTarget, dict]):
       def __init__(self, data_path: Path, config_path: Path):
           self.data_path = data_path
           self.config_path = config_path
           self._targets = None

       def get_targets(self, filter_args: dict = None) -> List[BenchmarkTarget]:
           if self._targets is None:
               self._targets = self._load_targets_from_config()

           if filter_args:
               return [t for t in self._targets if self._matches_filter(t, filter_args)]
           return self._targets

       def get_measurements_for_target(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           measurements_file = self.data_path / f"{target.name}_measurements.parquet"
           df = pd.read_parquet(measurements_file)
           return VersionedTimeSeriesDataset(df, version="1.0")

       def get_predictors_for_target(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           predictors_file = self.data_path / f"{target.name}_predictors.parquet"
           df = pd.read_parquet(predictors_file)
           return VersionedTimeSeriesDataset(df, version="1.0")

       def get_metrics_for_target(self, target: BenchmarkTarget) -> List[MetricProvider]:
           return [MetricProvider("mae"), MetricProvider("rmse")]

       def get_evaluation_mask_for_target(self, target: BenchmarkTarget) -> pd.DatetimeIndex:
           start_date = pd.Timestamp("2023-01-01")
           end_date = pd.Timestamp("2023-12-31")
           return pd.date_range(start_date, end_date, freq="15T")

       def _load_targets_from_config(self) -> List[BenchmarkTarget]:
           import yaml
           with open(self.config_path) as f:
               config = yaml.safe_load(f)

           targets = []
           for target_config in config["targets"]:
               target = BenchmarkTarget(
                   name=target_config["name"],
                   description=target_config.get("description", ""),
                   metadata=target_config.get("metadata", {})
               )
               targets.append(target)
           return targets

       def _matches_filter(self, target: BenchmarkTarget, filter_args: dict) -> bool:
           for key, value in filter_args.items():
               if target.metadata.get(key) != value:
                   return False
           return True


Advanced Workflow Customization
-------------------------------


OpenSTEF's workflow customization enables tailored forecasting solutions for specialized production scenarios. The CustomForecastingWorkflow class provides complete control over model management and lifecycle hooks, while EnsembleForecastingWorkflow supports multi-model approaches. Common customizations include feature engineering modifications, callback implementations for monitoring, and specialized post-processing for energy disaggregation or forecast combination workflows.


.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef.feature_engineering.feature_applicator import OperationalPredictFeatureApplicator
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.data_classes import PredictionJobDataClass
   import pandas as pd
   from datetime import datetime

   # Create custom feature applicator with specialized features
   feature_applicator = OperationalPredictFeatureApplicator(
       horizons=[0.25, 1.0, 24.0, 47.0],
       feature_names=['load_lag_1h', 'temp_rolling_24h', 'wind_speed_forecast'],
       feature_modules=['weather', 'load_patterns', 'calendar']
   )

   # Initialize prediction job configuration
   prediction_job = PredictionJobDataClass(
       id=123,
       name="solar_farm_forecast",
       model="xgb_quantile",
       lat=52.1,
       lon=4.3,
       resolution_minutes=15
   )

   # Create custom workflow with specialized components
   workflow = CustomForecastingWorkflow(
       model=XGBQuantileOpenstfRegressor(
           quantiles=[0.1, 0.5, 0.9],
           n_estimators=200,
           max_depth=8
       ),
       feature_applicator=feature_applicator,
       run_name="specialized_solar_forecast"
   )

   # Load and prepare training data
   train_data = pd.read_csv("solar_training_data.csv", parse_dates=['datetime'])
   train_data.set_index('datetime', inplace=True)

   # Fit workflow with custom feature pipeline
   fit_result = workflow.fit(train_data)

   # Generate forecasts with specialized features
   forecast_start = datetime(2024, 6, 15, 12, 0)
   predictions = workflow.predict(train_data, forecast_start=forecast_start)


Production Implementation Considerations
----------------------------------------


Moving from tutorials to production requires careful consideration of data quality, performance monitoring, and deployment architecture. Key factors include evaluating forecast accuracy through backtesting, implementing proper monitoring systems, and choosing appropriate deployment patterns. For comprehensive guidance on operational implementation including code examples, see the Pipelines user guide. A complete reference implementation with databases and user interface is available in the OpenSTEF application repository.


- Evaluate model performance using backtesting with real historical data

- Set up monitoring and logging using PerformanceMeter for production tracking

- Implement proper data validation to ensure input data quality

- Configure hyperparameter optimization for your specific use case

- Test deployment with openstef-beam benchmark to validate accuracy metrics

- Set up automated retraining pipelines for model maintenance

- Implement error handling and fallback mechanisms for data outages

- Configure appropriate forecast horizons (maximum 7 days for energy forecasting)

- Set up database connections and data storage for operational use

- Consider reference implementation from OpenSTEF GitHub repository for full application deployment

- Establish performance monitoring dashboards for operational oversight

- Plan for scaling considerations based on prediction volume requirements


