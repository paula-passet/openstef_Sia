Tutorials
=========


First Steps with OpenSTEF
-------------------------


OpenSTEF is a Python machine learning library designed for short-term energy forecasting, not a standalone application. This tutorial demonstrates a complete forecasting workflow using OpenSTEF's preset configurations, which provide pre-configured machine learning pipelines for common forecasting scenarios. You'll learn to load data, train models, generate predictions, and evaluate results using the library's core functionality.


.. code-block:: python

   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline_core
   from openstef.data_classes.prediction_job import PredictionJob

   # Initialize a basic prediction job configuration
   prediction_job = PredictionJob(
       id=1,
       name="solar_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       train_components=0.95
   )

   # Create forecast pipeline with default settings
   pipeline = create_forecast_pipeline_core(
       pj=prediction_job,
       input_data=pd.DataFrame(),
       check_hyper_params=True
   )


Loading and Preparing Your Data
-------------------------------


OpenSTEF requires time-series data with datetime index and numeric load values. The library supports flexible data formats but expects consistent temporal resolution. Input data should include relevant features like weather variables, calendar information, and historical load patterns. Data validation ensures proper structure and identifies missing values or inconsistencies before model training.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes import PredictionJobDataClass
   from openstef.validation import validate_data
   from openstef.preprocessing import apply_preprocessing

   # Load data from CSV with datetime index
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)

   # Create prediction job configuration
   job = PredictionJobDataClass(
       id=123,
       name="substation_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand"
   )

   # Validate data format and completeness
   validated_data = validate_data(data, job)

   # Apply basic preprocessing: fill gaps, add features
   processed_data = apply_preprocessing(
       validated_data,
       job,
       fill_missing=True,
       add_weather_features=True
   )

   print(f"Processed {len(processed_data)} records for forecasting")


Training Your First Model
-------------------------


OpenSTEF provides a streamlined model training workflow through the train_model pipeline. The library includes preset configurations for various machine learning models including XGBoost, LightGBM, linear regression, and ARIMA models. These presets handle feature engineering, data validation, and hyperparameter defaults automatically.

The training process follows a structured approach: data validation checks for issues like flatliners, feature engineering creates relevant predictors based on your prediction job configuration, and the machine learning component trains your selected model type. You can use the train_model pipeline directly with your own data or leverage the higher-level tasks that handle database operations.


.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd

   # Create prediction job with preset configuration
   pjob = PredictionJob(
       id=123,
       name="solar_forecast_model",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       train_components=False
   )

   # Load your training data
   train_data = pd.read_csv("energy_data.csv", parse_dates=["datetime"])
   train_data.set_index("datetime", inplace=True)

   # Train model with monitoring
   model, model_specs, importances = train_model_pipeline(
       pjob=pjob,
       input_data=train_data
   )

   # Monitor training progress
   print(f"Model type: {model_specs['model_type']}")
   print(f"Training score: {model_specs.get('score', 'N/A')}")
   print(f"Feature count: {len(importances)}")
   print("Top 3 features:", importances.head(3).index.tolist())


Creating and Evaluating Forecasts
---------------------------------


OpenSTEF generates probabilistic forecasts with uncertainty estimates rather than single-point predictions. The library supports single-shot, multi-horizon forecasting, allowing you to predict multiple time steps ahead in one operation. Two confidence estimation methods are available to quantify forecast uncertainty and provide prediction intervals.

The forecasting process combines automated feature engineering with domain-specific knowledge for energy systems. Built-in features include solar radiation conversion to PV generation estimates and other energy-specific transformations. The framework handles complete pipelines from data preprocessing through model training to forecast evaluation.

OpenSTEF includes comprehensive evaluation metrics to assess model performance across different forecasting horizons. The evaluation system supports various metrics relevant to energy forecasting applications, enabling you to select appropriate measures based on your specific use case and data quality requirements.


.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.validation.validation import calc_forecast_skill_score

   # Create prediction job configuration
   prediction_job = PredictionJobDataClass(
       id=123,
       name="solar_farm_forecast",
       model="xgb",
       horizon_minutes=2880,  # 48 hours ahead
       resolution_minutes=15,
       feature_names=["load_entsoe", "radiation", "windspeed_100m", "temp"]
   )

   # Train model with historical data
   model_specs = train_model_pipeline(
       pj=prediction_job,
       input_data=train_data,
       mlflow_tracking_uri=None
   )

   # Generate probabilistic forecasts
   forecast_data = create_forecast_pipeline(
       pj=prediction_job,
       input_data=test_data,
       model_specs=model_specs
   )

   # Calculate evaluation metrics
   skill_score = calc_forecast_skill_score(
       forecast=forecast_data["forecast"],
       realized=test_data["load"],
       reference_forecast=forecast_data["stdev"]
   )

   # Extract confidence intervals
   lower_bound = forecast_data["forecast"] - 1.96 * forecast_data["stdev"]
   upper_bound = forecast_data["forecast"] + 1.96 * forecast_data["stdev"]

   print(f"Forecast skill score: {skill_score:.3f}")
   print(f"95% confidence interval coverage: {((test_data['load'] >= lower_bound) & (test_data['load'] <= upper_bound)).mean():.2%}")


Understanding Energy Split Analysis
-----------------------------------


Energy split analysis decomposes forecasts into individual components, revealing how different factors contribute to the total prediction. This functionality helps users understand model behavior by showing the relative impact of weather, seasonal patterns, and other input features on energy forecasts, enabling better interpretation and validation of model results.


.. code-block:: python

   from openstef_models.models.component_splitting.linear_component_splitter import LinearComponentSplitter
   import pandas as pd
   import matplotlib.pyplot as plt

   # Load your forecast data
   data = pd.read_csv('forecast_data.csv', parse_dates=['datetime'])
   data.set_index('datetime', inplace=True)

   # Initialize the component splitter
   splitter = LinearComponentSplitter()

   # Create TimeSeriesDataset from your data
   from openstef_models.data_classes import TimeSeriesDataset
   dataset = TimeSeriesDataset(data=data)

   # Perform energy split analysis
   components = splitter.predict(dataset)

   # Visualize the components
   fig, axes = plt.subplots(3, 1, figsize=(12, 10))

   # Plot total forecast
   axes[0].plot(components.data.index, components.data['total'], label='Total Forecast')
   axes[0].set_title('Total Energy Forecast')
   axes[0].legend()

   # Plot individual components
   axes[1].plot(components.data.index, components.data['base_load'], label='Base Load')
   axes[1].plot(components.data.index, components.data['weather_dependent'], label='Weather Dependent')
   axes[1].set_title('Energy Components')
   axes[1].legend()

   # Plot component contributions as percentages
   total = components.data['total']
   base_pct = (components.data['base_load'] / total) * 100
   weather_pct = (components.data['weather_dependent'] / total) * 100

   axes[2].stackplot(components.data.index, base_pct, weather_pct,
                     labels=['Base Load %', 'Weather Dependent %'])
   axes[2].set_title('Component Contributions (%)')
   axes[2].legend()

   plt.tight_layout()
   plt.show()


Backtesting and Advanced Workflows
----------------------------------


Backtesting enables rigorous evaluation of forecasting model performance using historical data, ensuring reliability before deployment. OpenSTEF provides comprehensive backtesting capabilities through the OpenSTEF4BacktestForecaster and benchmarking framework. The library supports advanced customization through CustomForecastingWorkflow, allowing integration of custom callbacks, model configurations, and lifecycle hooks to tailor forecasting workflows to specific operational requirements.


.. code-block:: python

   from openstef_beam.benchmarking.baselines.openstef4 import create_openstef4_preset_backtest_forecaster
   from openstef_models.presets.forecasting_workflow import ForecastingWorkflowConfig
   from pathlib import Path

   # Configure workflow for backtesting
   config = ForecastingWorkflowConfig(
       location_id="solar_farm_001",
       model_type="xgb",
       horizon_minutes=1440
   )

   # Create backtest forecaster factory
   forecaster_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=config,
       cache_dir=Path("backtest_cache")
   )

   # Use factory to create forecaster for specific target
   forecaster = forecaster_factory.create(target="load_mw")

   # Fit and predict on historical data
   forecaster.fit(historical_data)
   predictions = forecaster.predict(test_data)


