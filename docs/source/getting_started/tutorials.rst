Tutorials
=========


First Steps with OpenSTEF
-------------------------


OpenSTEF is a Python library for energy load forecasting that requires you to prepare data and train models. This tutorial series guides you through your first complete forecasting workflow using built-in presets to minimize complexity. You'll learn to use OpenSTEF's pipelines for training models, creating forecasts, and evaluating performance with minimal configuration required.


.. code-block:: python

   import pandas as pd
   from openstef.pipeline import train_model, create_forecast
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   from openstef.validation.validation import calc_metrics

   # Load sample data
   input_data = pd.read_csv('sample_energy_data.csv', index_col=0, parse_dates=True)
   input_data = input_data.resample('15T').mean()

   # Create prediction job with preset configuration
   pj = PredictionJobDataClass(
       id=1,
       name="sample_forecast",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,
       resolution_minutes=15,
       feature_names=["load", "weather_temp", "weather_radiation"]
   )

   # Train model using pipeline
   model = train_model(pj, input_data)

   # Create forecast
   forecast_input = input_data.tail(672)  # Last 7 days for context
   forecast = create_forecast(pj, forecast_input, model)

   # Basic evaluation
   actual = input_data['load'].tail(192)  # Last 48 hours
   predicted = forecast['forecast'].head(192)
   metrics = calc_metrics(actual, predicted)
   print(f"MAE: {metrics['MAE']:.2f}, RMSE: {metrics['RMSE']:.2f}")


Data Preparation and Model Training
-----------------------------------


OpenSTEF requires input data as pandas DataFrames with datetime indices and specific column structures. The library validates data completeness using configurable thresholds and minimal table length requirements. Data validation includes flatliner detection, where constant values exceeding specified time thresholds are replaced with NaN values to ensure model quality.

Feature engineering in OpenSTEF involves preprocessing steps that transform raw time series data into model-ready features. The library centralizes data preprocessing logic to handle missing values, outliers, and temporal patterns. Users can configure completeness thresholds and validation parameters to match their data quality requirements.

The training process begins with data validation using the validate function, which checks datetime indexing and identifies problematic patterns. After validation, the is_data_sufficient function determines whether enough clean data remains for reliable model training. The library supports flexible data formats while maintaining robust validation to ensure forecast accuracy.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.validation.validation import validate, is_data_sufficient
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator

   # Load time series data with datetime index
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)
   data = data.resample('15T').mean()  # Ensure 15-minute resolution

   # Create prediction job configuration
   pj = PredictionJobDataClass(
       id=123,
       name="solar_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="solar"
   )

   # Validate input data
   validated_data = validate(
       pj_id=pj.id,
       data=data,
       flatliner_threshold_minutes=180,
       resolution_minutes=15,
       detect_non_zero_flatliner=False
   )

   # Check data sufficiency
   sufficient = is_data_sufficient(
       data=validated_data,
       completeness_threshold=0.9,
       minimal_table_length=2000
   )

   if sufficient:
       # Apply feature engineering
       feature_applicator = TrainFeatureApplicator(
           horizons=[0.25, 1.0, 6.0, 24.0, 47.0],
           feature_names=["load", "solar", "wind", "temp"]
       )

       feature_data = feature_applicator.add_features(validated_data, pj)

       # Initialize and train model
       model = XGBOpenstfRegressor()
       model.fit(feature_data.drop('target', axis=1), feature_data['target'])


Creating and Evaluating Forecasts
---------------------------------


OpenSTEF generates forecasts through a systematic process: retrieving historic training data (load, weather, and price data), applying feature engineering, loading trained models, and making predictions. The create_forecast_task function orchestrates this workflow, requiring prediction job parameters including location coordinates, resolution, and forecast horizon. Forecasts can be generated for individual quantiles or as ensemble predictions, with outputs typically stored as pandas DataFrames indexed by datetime.

Forecast evaluation uses multiple metrics to assess prediction quality across different scenarios. Key metrics include RMSE for overall accuracy, MAE for average errors, and specialized measures like r_mpe_highest and r_mpe_lowest that evaluate performance during peak and low demand periods respectively. The evaluation framework supports quantile-specific metrics and provides methods to flatten results for logging and comparison purposes.


.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.metrics.metrics import mae, rmse, bias
   from openstef.evaluation.figure import plot_feature_importance
   import matplotlib.pyplot as plt

   # Create sample data for forecast generation
   index = pd.date_range(start="2023-01-01 09:00:00", freq='15T', periods=300)
   data = pd.DataFrame(index=index, data=dict(
       load=np.sin(index.hour/24*np.pi)*np.random.uniform(0.7, 1.7, 300)
   ))
   data['insolation'] = data.load * np.random.uniform(0.8, 1.2, len(index)) + 0.1

   # Generate forecast using prediction job
   pj = {
       'id': 123,
       'lat': 52.0,
       'lon': 4.0,
       'resolution_minutes': 15,
       'horizon_minutes': 2880,
       'type': 'load',
       'name': 'test_forecast',
       'quantiles': [0.1, 0.5, 0.9]
   }

   # Create forecast (requires context and database setup)
   forecast = create_forecast_task(pj, context, t_behind_days=14)

   # Evaluate forecast performance with multiple metrics
   realised = data['load'].dropna()
   predicted = forecast['forecast'][:len(realised)]

   mae_score = mae(realised, predicted)
   rmse_score = rmse(realised, predicted)
   bias_score = bias(realised, predicted)

   print(f"MAE: {mae_score:.3f}")
   print(f"RMSE: {rmse_score:.3f}")
   print(f"Bias: {bias_score:.3f}")

   # Energy split analysis by time periods
   morning_mask = (realised.index.hour >= 6) & (realised.index.hour < 12)
   afternoon_mask = (realised.index.hour >= 12) & (realised.index.hour < 18)

   morning_mae = mae(realised[morning_mask], predicted[morning_mask])
   afternoon_mae = mae(realised[afternoon_mask], predicted[afternoon_mask])

   print(f"Morning MAE: {morning_mae:.3f}")
   print(f"Afternoon MAE: {afternoon_mae:.3f}")

   # Visualize forecast vs actual
   plt.figure(figsize=(12, 6))
   plt.plot(realised.index, realised, label='Actual', alpha=0.7)
   plt.plot(predicted.index, predicted, label='Forecast', alpha=0.7)
   plt.legend()
   plt.title('Forecast vs Actual Load')
   plt.show()


Backtesting with Real-World Data
--------------------------------


Backtesting simulates how forecasting models would perform in real operational conditions using historical data. The OpenSTEF library provides BacktestPipeline to conduct realistic validation by splitting historical data into training and testing periods. This approach evaluates model performance across different time periods and market conditions, helping identify potential issues before deployment. Set up backtesting by defining ground truth data, predictors, and time ranges for comprehensive model validation.


.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.models import XGBoostQuantileOpenstfRegressor, LinearQuantileOpenstfRegressor
   from openstef_beam.data import TimeSeriesDataset, VersionedTimeSeriesDataset
   from datetime import datetime, timedelta
   import pandas as pd

   # Load historical data
   ground_truth = VersionedTimeSeriesDataset.from_csv("historical_load.csv")
   predictors = VersionedTimeSeriesDataset.from_csv("weather_features.csv")

   # Configure models to compare
   xgb_config = BacktestConfig(
       model=XGBoostQuantileOpenstfRegressor(
           quantiles=[0.1, 0.5, 0.9],
           n_estimators=100,
           max_depth=6
       ),
       horizons=[0.25, 1.0, 24.0],
       train_window_days=365
   )

   linear_config = BacktestConfig(
       model=LinearQuantileOpenstfRegressor(quantiles=[0.1, 0.5, 0.9]),
       horizons=[0.25, 1.0, 24.0],
       train_window_days=365
   )

   # Run backtesting for comparison period
   start_date = datetime(2023, 1, 1)
   end_date = datetime(2023, 12, 31)

   xgb_pipeline = BacktestPipeline(xgb_config)
   linear_pipeline = BacktestPipeline(linear_config)

   xgb_results = xgb_pipeline.run(ground_truth, predictors, start_date, end_date)
   linear_results = linear_pipeline.run(ground_truth, predictors, start_date, end_date)

   # Compare model performance
   xgb_mae = xgb_results.calculate_mae()
   linear_mae = linear_results.calculate_mae()

   print(f"XGBoost MAE: {xgb_mae:.2f}")
   print(f"Linear MAE: {linear_mae:.2f}")


Advanced Customization
----------------------


OpenSTEF provides extensive customization capabilities for advanced users who need to tailor forecasting workflows to specific requirements. The library supports custom workflow implementations through CustomForecastingWorkflow and CustomComponentSplitWorkflow classes, which offer complete control over model training and prediction pipelines with lifecycle hooks and callback mechanisms.

Advanced feature engineering is available through the feature_engineering package, allowing users to create custom features, modify data preparation strategies, and implement domain-specific transformations. The FeatureAdder and FeatureDispatcher classes enable flexible feature management, while AbstractDataPreparation provides a foundation for custom data preprocessing workflows.

Custom target providers can be implemented to handle specialized data sources or prediction targets beyond standard energy forecasting scenarios. These components integrate seamlessly with OpenSTEF's core architecture while maintaining full compatibility with existing model types and evaluation frameworks.


.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow, ForecastingCallback
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.feature_engineering.feature_adder import FeatureAdder
   from openstef.data_classes import PredictionJobDataClass
   import pandas as pd
   from datetime import datetime

   # Custom target provider
   class CustomTargetProvider:
       def __init__(self, scaling_factor=1.0):
           self.scaling_factor = scaling_factor

       def get_target_data(self, start_date, end_date):
           # Custom logic to fetch and transform target data
           data = pd.DataFrame({
               'load': [100, 120, 110] * self.scaling_factor,
               'datetime': pd.date_range(start_date, periods=3, freq='H')
           })
           return data.set_index('datetime')

   # Custom feature engineering pipeline
   class CustomFeatureAdder(FeatureAdder):
       @property
       def name(self):
           return "custom_weather_interaction"

       def apply_features(self, data, pj=None):
           # Add custom weather interaction features
           if 'windspeed' in data.columns and 'temperature' in data.columns:
               data['wind_temp_interaction'] = data['windspeed'] * data['temperature']
           return data

   # Custom workflow callback
   class MetricsCallback(ForecastingCallback):
       def on_fit_start(self, workflow, data):
           print(f"Training started with {len(data)} samples")

       def on_predict_end(self, workflow, result):
           print(f"Forecast generated for {len(result.forecasts)} periods")

   # Initialize custom workflow
   pj = PredictionJobDataClass(id=123, name="custom_forecast")
   workflow = CustomForecastingWorkflow(
       prediction_job=pj,
       callbacks=[MetricsCallback()]
   )

   # Apply custom features
   data = pd.DataFrame({
       'load': [100, 120, 110, 95],
       'windspeed': [10, 15, 12, 8],
       'temperature': [20, 22, 18, 16]
   }, index=pd.date_range('2024-01-01', periods=4, freq='H'))

   enhanced_data = apply_features(
       data,
       pj=pj,
       feature_names=['load_7d', 'windspeed_100m', 'is_weekend'],
       horizon=24.0
   )

   # Train and predict with custom workflow
   fit_result = workflow.fit(enhanced_data)
   forecast = workflow.predict(enhanced_data, forecast_start=datetime(2024, 1, 1, 4))


