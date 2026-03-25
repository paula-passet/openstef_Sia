Tutorials
=========


First Forecast with Presets
---------------------------


OpenSTEF provides preset configurations that simplify the forecasting workflow by bundling common settings and components. This tutorial demonstrates how to create your first forecast using the EnsembleForecastingWorkflowConfig preset, which handles data preparation, model training, and prediction generation with minimal configuration required from you.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.validation.validation import calc_forecast_skill

   # Load sample data
   data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)

   # Create prediction job configuration
   pj = PredictionJobDataClass(
       id=1,
       name="solar_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       train_horizons_minutes=[15, 60, 240]
   )

   # Train model
   model, model_specs, model_age = train_model_pipeline(
       pj=pj,
       input_data=data,
       check_hyper_params=True
   )

   # Create forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=data,
       model=model,
       model_specs=model_specs
   )

   # Evaluate results
   skill_score = calc_forecast_skill(
       forecast=forecast,
       reference_forecast=data['load'].shift(24)  # naive forecast
   )

   print(f"Model trained successfully. Forecast skill: {skill_score:.3f}")


Data Loading and Preparation
----------------------------


OpenSTEF requires time series data with a datetime index and specific column structures. The library validates data completeness, checks for required columns, and detects flatliner patterns where measurements remain constant. Data preparation includes feature engineering to create lag features and validation steps to ensure sufficient data quality for model training.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.validation.validation import validate, is_data_sufficient

   # Load data from CSV
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)

   # Load prediction job configuration
   pj = PredictionJob(
       id=123,
       name="wind_farm_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand"
   )

   # Basic validation and preprocessing
   validated_data = validate(
       pj_id=pj.id,
       data=data,
       flatliner_threshold_minutes=60,
       resolution_minutes=pj.resolution_minutes
   )

   # Check data sufficiency
   sufficient = is_data_sufficient(
       data=validated_data,
       completeness_threshold=0.9,
       minimal_table_length=1000
   )

   if sufficient:
       print("Data ready for training")
   else:
       print("Insufficient data quality")


Model Training and Forecasting
------------------------------


OpenSTEF provides automated model training through hyperparameter optimization pipelines. The library supports multiple model types including XGBoost, LightGBM, ARIMA, and linear models, with automatic objective function creation based on model type selection.

Training uses the optimize_hyperparameters_pipeline function with configurable trial counts for hyperparameter tuning. The process requires prediction job specifications, input data, and MLflow tracking for experiment management and artifact storage.

Forecast generation occurs through prediction pipelines that accept trained models and input data. The library outputs structured forecasts as DataFrames with datetime indices, supporting both point predictions and quantile forecasts for uncertainty estimation.


.. code-block:: python

   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes import PredictionJobDataClass, ModelSpecificationDataClass
   import pandas as pd
   import numpy as np

   # Create sample training data
   index = pd.date_range(start="2023-01-01", freq="15T", periods=2000)
   train_data = pd.DataFrame(index=index)
   train_data['load'] = np.sin(index.hour/24*np.pi) * np.random.uniform(0.7, 1.7, len(index))
   train_data['T_2m'] = 15 + 10 * np.sin(index.dayofyear/365*2*np.pi) + np.random.normal(0, 3, len(index))
   train_data['radiation'] = np.maximum(0, np.sin(index.hour/24*np.pi) * 800 + np.random.normal(0, 100, len(index)))

   # Define prediction job
   pj = PredictionJobDataClass(
       id=123,
       name="wind_farm_forecast",
       model="xgb_quantile",
       resolution_minutes=15,
       quantiles=[0.1, 0.5, 0.9]
   )

   # Train model with hyperparameter optimization
   trained_model = train_model_pipeline(
       pj=pj,
       input_data=train_data,
       mlflow_tracking_uri="./mlruns"
   )

   # Create model specifications
   model_specs = ModelSpecificationDataClass(
       id=pj.id,
       model_type=pj.model,
       hyper_params=trained_model.get_params(),
       feature_names=trained_model.feature_names
   )

   # Generate forecast with confidence intervals
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=train_data.tail(96),  # Last 24 hours for context
       model=trained_model,
       model_specs=model_specs
   )

   print("Forecast with confidence intervals:")
   print(forecast[['forecast', 'quantile_0.1', 'quantile_0.9']].head())


Evaluation and Energy Split Analysis
------------------------------------


OpenSTEF provides comprehensive evaluation metrics through the EvaluationReport and SubsetMetric models to assess forecast quality across different data subsets and time windows. These metrics include quantile-specific measurements that help understand prediction accuracy at various confidence levels.

Energy split analysis decomposes total energy forecasts into renewable components (wind and solar) using linear component splitters. The split_forecast functionality applies coefficients to separate load forecasts into constituent energy sources, enabling detailed analysis of renewable energy contributions.

Results are organized in structured reports that can be saved to parquet files for persistence and analysis. The EvaluationSubsetReport provides methods to extract measurements, quantile predictions, and global metrics, while energy split coefficients indicate the proportion of each renewable source in the total forecast.


.. code-block:: python

   # Evaluate forecast quality and perform energy split analysis
   from openstef_beam.evaluation.models.report import EvaluationReport
   from openstef.tasks.split_forecast import split_forecast_task
   import matplotlib.pyplot as plt
   import pandas as pd

   # Load evaluation report
   report = EvaluationReport.read_parquet("evaluation_results/")

   # Get subset report for specific filtering
   subset_report = report.get_subset(filtering={'season': 'winter'})

   # Extract global metrics
   global_metric = subset_report.get_global_metric()
   mae = global_metric.get_metric('global', 'mae')
   rmse = global_metric.get_metric('global', 'rmse')

   print(f"Global MAE: {mae:.2f}")
   print(f"Global RMSE: {rmse:.2f}")

   # Get windowed metrics for detailed analysis
   windowed_metrics = subset_report.get_windowed_metrics()
   metrics_df = pd.concat([m.to_dataframe() for m in windowed_metrics])

   # Perform energy split analysis
   pj = {'id': 123, 'name': 'wind_solar_split'}
   context = {'database': database}
   split_coefficients = split_forecast_task(pj, context)

   print("Energy split coefficients:")
   print(split_coefficients)

   # Visualize evaluation metrics over time
   fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

   # Plot MAE over different time windows
   metrics_df.groupby('window')['mae'].mean().plot(kind='bar', ax=ax1)
   ax1.set_title('Mean Absolute Error by Time Window')
   ax1.set_ylabel('MAE (MW)')

   # Plot energy split components
   split_coefficients[['wind_component', 'solar_component']].plot(kind='bar', ax=ax2)
   ax2.set_title('Energy Split Components')
   ax2.set_ylabel('Coefficient Value')

   plt.tight_layout()
   plt.show()


Backtesting for Model Validation
--------------------------------


Backtesting simulates how forecasting models would perform in real operational conditions by testing them against historical data. This validation technique helps assess model accuracy and reliability before deployment. OpenSTEF's backtesting pipeline evaluates energy forecasting models using realistic scenarios, providing insights into model performance across different time periods and conditions.


.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_core.datasets import TimeSeriesDataset

   # Configure backtesting parameters
   config = BacktestConfig(
       models=['xgb', 'lgb', 'linear'],
       horizons=[0.25, 1.0, 24.0],
       quantiles=[0.1, 0.5, 0.9],
       cv_folds=5
   )

   # Initialize backtesting pipeline
   pipeline = BacktestPipeline(config)

   # Run backtest over historical period
   predictions = pipeline.run(
       ground_truth=historical_load_data,
       predictors=weather_features,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True
   )

   # Results contain predictions for all models and horizons
   model_performance = predictions.groupby(['model', 'horizon']).apply(
       lambda x: calculate_metrics(x['prediction'], x['actual'])
   )


Advanced Customization
----------------------


OpenSTEF provides advanced customization capabilities for specialized forecasting scenarios. Custom target providers enable integration with proprietary data sources by implementing the TargetProvider interface, allowing you to define how targets, measurements, and predictors are loaded. Advanced workflows support custom feature engineering pipelines beyond standard features, enabling domain-specific transformations and predictor combinations. These customizations are ideal when standard OpenSTEF functionality doesn't match your data architecture or when you need specialized forecasting logic for unique energy systems.


.. code-block:: python

   from openstef_beam.benchmarking.target_provider import TargetProvider
   from openstef.feature_engineering.apply_features import apply_features
   import pandas as pd

   # Custom target provider implementation
   class CustomTargetProvider(TargetProvider):
       def get_targets(self, filter_args=None):
           # Return list of custom targets
           return self.load_custom_targets()

       def get_measurements_for_target(self, target):
           # Load ground truth data for target
           return self.load_measurements(target.id)

       def get_predictors_for_target(self, target):
           # Load predictor features for target
           return self.load_predictors(target.id)

   # Feature engineering with custom features
   data = pd.DataFrame(index=pd.date_range('2024-01-01', periods=100, freq='H'))
   data['load'] = np.random.randn(100)
   data['temperature'] = np.random.randn(100) * 10 + 15

   # Apply standard features with custom horizon
   enriched_data = apply_features(
       data=data,
       pj=prediction_job,
       feature_names=['load_7d_ago', 'is_weekend', 'temperature_lag_1h'],
       horizon=48.0,
       years=[2023, 2024]
   )


