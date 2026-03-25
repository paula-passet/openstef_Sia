Tutorials
=========


First Steps with OpenSTEF
-------------------------


OpenSTEF provides a complete machine learning workflow for energy load forecasting through its library architecture. The workflow consists of data loading, feature engineering, model training, and prediction generation - all orchestrated through configurable pipelines and tasks. To simplify getting started, OpenSTEF includes preset configurations that handle common forecasting scenarios with minimal setup, allowing you to focus on your data rather than complex parameter tuning.


.. code-block:: python

   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Load sample data
   data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)
   data.columns = ['load', 'T-1h', 'radiation', 'windspeed_100m']

   # Create prediction job with default settings
   pj = PredictionJobDataClass(
       id=1,
       name="basic_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand"
   )

   # Train model
   model_specs = train_model_pipeline(
       pj=pj,
       input_data=data,
       check_hyper_params=False
   )

   # Create forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=data,
       model_specs=model_specs
   )

   # Basic evaluation
   mae = abs(forecast['forecast'] - data['load'].iloc[-len(forecast):]).mean()
   print(f"Mean Absolute Error: {mae:.2f}")


Energy Split Analysis
---------------------


Energy split analysis decomposes energy forecasts into constituent components, helping users understand which factors drive prediction changes. This functionality is particularly useful when analyzing forecast accuracy across different energy sources or time periods. Use energy split when you need to identify specific contributors to forecast variations or validate model behavior across different energy generation types.


.. code-block:: python

   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.validation.validation import split_forecast_and_actual

   # Load your data
   data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)
   data['load'] = data['load'].astype(float)

   # Apply feature engineering
   data_with_features = apply_features(data, pj={'id': 123, 'name': 'test_pj'})

   # Train model
   model = XGBQuantileOpenstfRegressor()
   train_data = data_with_features[:'2023-06-01']
   model.fit(train_data.drop('load', axis=1), train_data['load'])

   # Generate forecasts
   test_data = data_with_features['2023-06-02':]
   forecast = model.predict(test_data.drop('load', axis=1))

   # Perform energy split analysis
   forecast_df = pd.DataFrame({
       'forecast': forecast,
       'actual': test_data['load']
   }, index=test_data.index)

   split_results = split_forecast_and_actual(forecast_df)
   print("Energy split analysis:")
   print(f"Mean forecast: {split_results['forecast'].mean():.2f}")
   print(f"Mean actual: {split_results['actual'].mean():.2f}")
   print(f"Split ratio: {split_results['forecast'].sum() / split_results['actual'].sum():.3f}")


Backtesting Your Models
-----------------------


Backtesting evaluates model performance by testing predictions against historical data over multiple time periods. This process simulates real-world forecasting conditions to validate model accuracy and reliability before deployment. OpenSTEF's backtesting pipeline provides realistic evaluation by respecting data availability constraints and temporal dependencies that occur in production environments.


.. code-block:: python

   from openstef_beam.backtesting.backtest_pipeline import BacktestPipeline, BacktestConfig
   from openstef_beam.benchmarking.baselines.openstef4 import create_openstef4_preset_backtest_forecaster
   from openstef_beam.forecasting.workflows.config import ForecastingWorkflowConfig
   from openstef_beam.data.time_series import VersionedTimeSeriesDataset
   from datetime import datetime
   from pathlib import Path

   # Configure backtesting parameters
   backtest_config = BacktestConfig(
       horizon_hours=48,
       retrain_frequency_hours=168,
       min_train_hours=8760
   )

   # Create forecaster factories for different models
   xgb_config = ForecastingWorkflowConfig(model_type="xgb", quantiles=[0.1, 0.5, 0.9])
   lgb_config = ForecastingWorkflowConfig(model_type="lgb", quantiles=[0.1, 0.5, 0.9])

   xgb_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=xgb_config,
       cache_dir=Path("cache/xgb")
   )

   lgb_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=lgb_config,
       cache_dir=Path("cache/lgb")
   )

   # Set up backtest pipeline with multiple models
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster_factories={"xgb": xgb_factory, "lgb": lgb_factory}
   )

   # Run backtest
   predictions = pipeline.run(
       ground_truth=ground_truth_data,
       predictors=predictor_data,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True
   )


Advanced Customization
----------------------


OpenSTEF's modular architecture allows extensive customization of core components including feature engineering pipelines, model specifications, and data preprocessing logic. Custom implementations are typically needed when working with domain-specific data formats, integrating proprietary models, or adapting forecasting workflows to unique business requirements beyond standard energy forecasting scenarios.


.. code-block:: python

   from openstef.data_classes import PredictionJobDataClass
   from openstef.feature_engineering.feature_applicator import FeatureApplicator
   from openstef.feature_engineering.lag_features import apply_lag_features
   from openstef.feature_engineering.weather_features import apply_weather_features
   import pandas as pd

   # Custom target provider
   class CustomTargetProvider:
       def get_load_data(self, pid: int, start: str, end: str) -> pd.DataFrame:
           # Custom logic to fetch target data
           data = pd.DataFrame({
               'datetime': pd.date_range(start, end, freq='15T'),
               'load': [100 + i * 0.1 for i in range(len(pd.date_range(start, end, freq='15T')))]
           })
           return data.set_index('datetime')

   # Custom feature engineering
   def custom_feature_engineering(data: pd.DataFrame, pj: PredictionJobDataClass) -> pd.DataFrame:
       # Apply standard lag features
       data = apply_lag_features(data, pj)

       # Add custom business logic features
       data['peak_hour'] = (data.index.hour >= 17) & (data.index.hour <= 20)
       data['weekend'] = data.index.weekday >= 5

       # Apply weather features if available
       if 'temperature' in data.columns:
           data = apply_weather_features(data, pj)

       return data

   # Custom workflow implementation
   def run_custom_forecast_pipeline(pid: int, start_date: str, end_date: str):
       # Initialize custom components
       target_provider = CustomTargetProvider()

       # Create prediction job
       pj = PredictionJobDataClass(
           id=pid,
           model='xgb',
           horizon_minutes=960,
           resolution_minutes=15
       )

       # Get data and apply features
       data = target_provider.get_load_data(pid, start_date, end_date)
       featured_data = custom_feature_engineering(data, pj)

       return featured_data


