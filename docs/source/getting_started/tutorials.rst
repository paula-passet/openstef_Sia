Tutorials
=========


First Use with Presets
----------------------


OpenSTEF provides preset configurations that streamline the initial setup process for forecasting workflows. These presets encapsulate common configuration patterns and best practices, allowing users to quickly start with proven setups rather than manually configuring each component. The preset-based approach reduces complexity by providing ready-to-use workflow configurations for both single model and ensemble forecasting scenarios, making it easier to explore OpenSTEF's capabilities without deep configuration knowledge.


.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow
   )
   from openstef_core.datasets.validated_datasets import ForecastInputDataset
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Load sample data
   data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)
   data = data.resample('15T').mean()

   # Create prediction job configuration
   prediction_job = PredictionJobDataClass(
       id=123,
       name="solar_forecast",
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=15,
       train_horizons_minutes=[15, 30, 60, 240],
       quantiles=[0.1, 0.5, 0.9]
   )

   # Configure workflow with preset
   location = LocationConfig(
       name="Amsterdam Solar Park",
       country="NL",
       region="North Holland"
   )

   config = ForecastingWorkflowConfig(
       location=location,
       prediction_job=prediction_job
   )

   # Create workflow from preset
   workflow = create_forecasting_workflow(config)

   # Prepare forecast dataset
   forecast_start = datetime.now().replace(minute=0, second=0, microsecond=0)
   dataset = ForecastInputDataset.from_timeseries(
       dataset=data,
       target_column='load',
       forecast_start=forecast_start
   )

   # Train model
   trained_model = workflow.train(dataset)

   # Create forecast
   forecast_horizon = timedelta(hours=48)
   forecast = workflow.predict(dataset, horizon=forecast_horizon)

   # Basic evaluation
   if dataset.target_series is not None:
       mae = abs(forecast.median_series() - dataset.target_series).mean()
       print(f"Mean Absolute Error: {mae:.2f}")


Data Loading and Preparation
----------------------------


OpenSTEF requires time series data in pandas DataFrame format with a datetime index and specific column structures. The TimeSeriesDataset class serves as the foundation for data handling, requiring columns like 'load' for target values and optional 'available_at' and 'horizon' columns for forecast metadata.

Data validation ensures required columns are present and properly formatted using validate_required_columns() and validate_datetime_column() functions. The sample_interval parameter defines the temporal resolution of your data, typically 15-minute intervals for energy forecasting applications.

Common preprocessing steps include feature selection with select_features(), time-based filtering using filter_time_range(), and horizon-specific data extraction via select_horizon(). The ForecastInputDataset class provides specialized methods for separating input features from target variables during model training.


.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets.validated_datasets import ForecastInputDataset
   from openstef_core.datasets.time_series import TimeSeriesDataset

   # Load data from CSV file
   df = pd.read_csv('energy_data.csv', parse_dates=['timestamp'], index_col='timestamp')

   # Create TimeSeriesDataset with 15-minute intervals
   sample_interval = timedelta(minutes=15)
   dataset = TimeSeriesDataset.from_pandas(df, sample_interval=sample_interval)

   # Validate required columns are present
   from openstef_core.datasets.validation import validate_required_columns
   required_cols = ['load', 'temperature', 'wind_speed']
   validate_required_columns(dataset.to_pandas(), required_cols)

   # Create forecast input dataset
   forecast_start = datetime(2024, 1, 15, 12, 0)
   forecast_dataset = ForecastInputDataset.from_timeseries(
       dataset,
       target_column='load',
       forecast_start=forecast_start
   )

   # Extract input features and target series
   input_features = forecast_dataset.input_data()
   target_values = forecast_dataset.target_series()

   # Filter data for specific time range
   start_time = datetime(2024, 1, 1)
   filtered_dataset = dataset.filter_time_range(start=start_time)

   # Select subset of features
   selected_features = ['temperature', 'wind_speed', 'solar_radiation']
   feature_dataset = dataset.select_features(selected_features)


Model Training and Forecasting
------------------------------


The training process uses the train_model_pipeline_core function which compares new models against existing ones based on performance metrics. Training requires a PredictionJobDataClass, input data, and model specifications, with configurable horizons for feature engineering. OpenSTEF generates forecasts with confidence intervals through two methods: standard deviation columns calculated during training, and quantile predictions for more precise uncertainty estimates. Quantile models use specialized regression techniques to predict multiple quantiles, while non-quantile models assume normally distributed errors around the point forecast.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core

   # Create prediction job
   pj = PredictionJobDataClass(
       id=123,
       name="solar_farm_forecast",
       type="demand",
       resolution_minutes=15,
       quantiles=[0.1, 0.5, 0.9]
   )

   # Model specifications
   model_specs = ModelSpecificationDataClass(
       model_type="xgb",
       hyper_params={"n_estimators": 100, "max_depth": 6}
   )

   # Load training data (example structure)
   training_data = pd.DataFrame({
       "load": [100, 120, 95, 110, 105],
       "temperature": [20, 22, 18, 21, 19],
       "wind_speed": [5, 7, 4, 6, 5],
       "datetime": pd.date_range("2023-01-01", periods=5, freq="15T")
   })

   # Train model
   trained_model = train_model_pipeline_core(
       pj=pj,
       model_specs=model_specs,
       input_data=training_data,
       horizons=[0.25, 1.0, 4.0]
   )

   # Generate forecast with confidence intervals
   forecast = create_forecast_pipeline_core(
       pj=pj,
       input_data=training_data,
       model=trained_model,
       model_specs=model_specs
   )

   print(forecast[["forecast", "stdev", "quantile_P10", "quantile_P50", "quantile_P90"]].head())


Evaluation and Energy Split Analysis
------------------------------------


OpenSTEF provides comprehensive evaluation metrics to assess forecast quality for grid management applications. Key deterministic metrics include Mean Absolute Error (MAE), relative MAE (rMAE), and Mean Absolute Percentage Error (MAPE) for measuring prediction accuracy. Advanced metrics like Nash-Sutcliffe Model Efficiency (NSME) and Franks Skill Score evaluate model performance against baseline forecasts, while confusion matrices help analyze peak detection accuracy crucial for grid capacity planning.

Energy split analysis enables grid operators to decompose total demand forecasts into component loads across different network segments. This capability supports critical grid management decisions including load balancing, capacity allocation, and infrastructure planning. The library's modular architecture allows customization of evaluation approaches to match specific grid operational requirements and regional energy market characteristics.


.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.metrics.metrics import mae, rmse, mape, bias
   from openstef.feature_engineering.apply_features import apply_features
   import matplotlib.pyplot as plt

   # Load forecast results and actual measurements
   forecast_data = pd.read_csv('forecast_results.csv', index_col=0, parse_dates=True)
   actual_data = pd.read_csv('actual_measurements.csv', index_col=0, parse_dates=True)

   # Merge datasets for evaluation
   evaluation_df = pd.merge(forecast_data, actual_data, left_index=True, right_index=True, suffixes=('_pred', '_actual'))

   # Calculate evaluation metrics
   mae_score = mae(evaluation_df['load_actual'], evaluation_df['load_pred'])
   rmse_score = rmse(evaluation_df['load_actual'], evaluation_df['load_pred'])
   mape_score = mape(evaluation_df['load_actual'], evaluation_df['load_pred'])
   bias_score = bias(evaluation_df['load_actual'], evaluation_df['load_pred'])

   print(f"MAE: {mae_score:.2f} MW")
   print(f"RMSE: {rmse_score:.2f} MW")
   print(f"MAPE: {mape_score:.2f}%")
   print(f"Bias: {bias_score:.2f} MW")

   # Energy split analysis for grid management
   evaluation_df['hour'] = evaluation_df.index.hour
   evaluation_df['weekday'] = evaluation_df.index.weekday

   # Calculate peak vs off-peak performance
   peak_hours = evaluation_df[evaluation_df['hour'].isin([17, 18, 19, 20])]
   off_peak_hours = evaluation_df[~evaluation_df['hour'].isin([17, 18, 19, 20])]

   peak_mae = mae(peak_hours['load_actual'], peak_hours['load_pred'])
   off_peak_mae = mae(off_peak_hours['load_actual'], off_peak_hours['load_pred'])

   # Visualize forecast performance
   fig, axes = plt.subplots(2, 2, figsize=(12, 8))

   # Time series comparison
   axes[0,0].plot(evaluation_df.index, evaluation_df['load_actual'], label='Actual', alpha=0.7)
   axes[0,0].plot(evaluation_df.index, evaluation_df['load_pred'], label='Forecast', alpha=0.7)
   axes[0,0].set_title('Forecast vs Actual Load')
   axes[0,0].legend()

   # Scatter plot
   axes[0,1].scatter(evaluation_df['load_actual'], evaluation_df['load_pred'], alpha=0.5)
   axes[0,1].plot([0, evaluation_df['load_actual'].max()], [0, evaluation_df['load_actual'].max()], 'r--')
   axes[0,1].set_xlabel('Actual Load (MW)')
   axes[0,1].set_ylabel('Predicted Load (MW)')
   axes[0,1].set_title('Prediction Accuracy')

   # Hourly performance
   hourly_mae = evaluation_df.groupby('hour').apply(lambda x: mae(x['load_actual'], x['load_pred']))
   axes[1,0].bar(hourly_mae.index, hourly_mae.values)
   axes[1,0].set_xlabel('Hour of Day')
   axes[1,0].set_ylabel('MAE (MW)')
   axes[1,0].set_title('Hourly Forecast Error')

   # Weekly performance
   weekly_mae = evaluation_df.groupby('weekday').apply(lambda x: mae(x['load_actual'], x['load_pred']))
   axes[1,1].bar(weekly_mae.index, weekly_mae.values)
   axes[1,1].set_xlabel('Day of Week (0=Monday)')
   axes[1,1].set_ylabel('MAE (MW)')
   axes[1,1].set_title('Weekly Forecast Error')

   plt.tight_layout()
   plt.show()

   print(f"\nEnergy Split Analysis:")
   print(f"Peak hours MAE: {peak_mae:.2f} MW")
   print(f"Off-peak hours MAE: {off_peak_mae:.2f} MW")
   print(f"Peak/Off-peak ratio: {peak_mae/off_peak_mae:.2f}")


Backtesting Scenarios
---------------------


Backtesting validates model performance by simulating historical forecasting scenarios using past data. OpenSTEF's BacktestPipeline splits data into train, validation, and test sets with configurable ratios, ensuring realistic evaluation conditions that mirror real-world deployment.

The pipeline supports stratified sampling to include extreme weather days in validation sets, providing representative performance assessment. Configure test_fraction and validation_fraction parameters to control data splits, with stratification_min_max ensuring balanced coverage of operational conditions.


.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef.model.regressors import XGBQuantileOpenstfRegressor, LinearQuantileOpenstfRegressor
   from datetime import datetime

   # Configure backtesting for multiple models
   models = {
       'xgb': XGBQuantileOpenstfRegressor(),
       'linear': LinearQuantileOpenstfRegressor()
   }

   backtest_results = {}

   for model_name, model in models.items():
       config = BacktestConfig(
           model=model,
           test_fraction=0.2,
           validation_fraction=0.15,
           horizons=[0.25, 1.0, 6.0, 24.0]
       )

       pipeline = BacktestPipeline(config)
       predictions = pipeline.run(
           ground_truth=ground_truth_data,
           predictors=predictor_data,
           start=datetime(2023, 1, 1),
           end=datetime(2023, 12, 31)
       )

       backtest_results[model_name] = predictions

   # Compare model performance
   comparison_pipeline = BenchmarkComparisonPipeline()
   comparison_results = comparison_pipeline.run(backtest_results)


Advanced Customization
----------------------


OpenSTEF provides advanced customization capabilities for specialized forecasting requirements. Custom target providers enable integration with proprietary data sources and evaluation frameworks. Component splitting workflows allow decomposition of energy forecasts into constituent parts. Advanced feature engineering supports domain-specific transformations and custom predictor functions. These features are designed for experienced users implementing complex forecasting pipelines or integrating OpenSTEF into existing enterprise systems.


.. code-block:: python

   from openstef_beam.benchmarking.target_provider import SimpleTargetProvider, TargetProviderConfig
   from openstef.feature_engineering.apply_features import apply_features
   from openstef_models.workflows.custom_component_split_workflow import CustomComponentSplitWorkflow, ComponentSplitCallback
   import pandas as pd

   # Custom target provider implementation
   class CustomTargetProvider(SimpleTargetProvider):
       def get_targets(self, filter_args=None):
           targets = super().get_targets(filter_args)
           return [t for t in targets if t.capacity > 100]

       def get_measurements_for_target(self, target):
           data = super().get_measurements_for_target(target)
           # Apply custom preprocessing
           data.data = data.data.resample('15T').mean()
           return data

   # Initialize target provider with config
   config = TargetProviderConfig(
       data_path="/path/to/benchmark/data",
       target_config_path="/path/to/targets.yaml"
   )
   provider = CustomTargetProvider(config)

   # Custom feature engineering
   def add_custom_features(data, pj=None):
       # Apply standard features
       enhanced_data = apply_features(
           data=data,
           pj=pj,
           feature_names=['load_7d', 'weekday', 'holiday'],
           horizon=48.0,
           years=[2023, 2024]
       )

       # Add custom business logic features
       enhanced_data['peak_hour'] = enhanced_data.index.hour.isin([8, 9, 17, 18, 19])
       enhanced_data['temperature_lag_2h'] = enhanced_data['temperature'].shift(8)

       return enhanced_data

   # Custom workflow callback
   class CustomCallback(ComponentSplitCallback):
       def on_fit_start(self, workflow, data):
           print(f"Training started with {len(data)} samples")

       def on_predict_end(self, workflow, result):
           print(f"Prediction completed: {result.components.shape}")

   # Component splitting workflow with custom callback
   workflow = CustomComponentSplitWorkflow()
   callback = CustomCallback()
   workflow.add_callback(callback)

   # Training and prediction
   train_data = provider.get_measurements_for_target(target)
   workflow.fit(train_data.data)
   predictions = workflow.predict(test_data)


