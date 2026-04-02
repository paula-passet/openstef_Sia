Tutorials
=========

This page guides you from your first forecast to production-ready implementations. We start with a complete end-to-end example using sensible defaults, then show how to evaluate model performance through backtesting, and finally demonstrate how to customize OpenSTEF for your specific requirements.

If you're looking for the absolute fastest way to get started, see :doc:`quickstart`. For specific implementation tasks like deployment or data integration, check :doc:`../guides/how_to_guides`.

Tutorial 1: Your First Complete Forecast
-----------------------------------------

This tutorial walks through the complete forecasting workflow: loading data, training a model, creating forecasts, and evaluating results. We'll use maximum presets to minimize configuration while still producing production-quality forecasts.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects time series data with load measurements and weather features. The library handles missing data, feature engineering, and validation automatically.

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline import train_model, create_forecast
   
   # Load your historical data
   # Required columns: datetime (index), load, temperature, windspeed, radiation
   data = pd.read_csv('historical_load.csv', index_col='datetime', parse_dates=True)
   
   # Define the prediction job
   # This tells OpenSTEF what to forecast and how
   pj = PredictionJob(
       id=1,
       name="substation_alpha",
       model="xgb",  # XGBoost is the default and most reliable
       quantiles=[0.1, 0.5, 0.9],  # Forecast uncertainty bands
       horizon_minutes=2880,  # 48-hour forecast horizon
       resolution_minutes=15,  # 15-minute resolution
       train_components=True,  # Enable energy split decomposition
   )

The ``PredictionJob`` is the central configuration object. It defines what you're forecasting (the prediction target), which model to use, and how far ahead to predict. Setting ``train_components=True`` enables energy split decomposition, which we'll explore later.

Training Your Model
^^^^^^^^^^^^^^^^^^^

Training is a single function call. OpenSTEF handles feature engineering, hyperparameter optimization, and model validation internally.

.. code-block:: python

   # Train the model
   # Returns trained model and feature importance information
   model, model_specs, report = train_model(pj, data)
   
   # Inspect what the model learned
   print(f"Model type: {model_specs['model_type']}")
   print(f"Training score (R²): {report['r2_score']:.3f}")
   print(f"Feature importance (top 5):")
   for feature, importance in report['feature_importance'][:5]:
       print(f"  {feature}: {importance:.3f}")

The training function returns three objects:

- ``model``: The trained scikit-learn compatible model
- ``model_specs``: Metadata about the model (hyperparameters, feature names, etc.)
- ``report``: Training diagnostics including scores and feature importance

OpenSTEF automatically splits your data into training and validation sets, engineers features from weather data and time information, and tunes hyperparameters using cross-validation.

Creating Forecasts
^^^^^^^^^^^^^^^^^^

Once trained, creating forecasts requires the model and recent data including weather predictions.

.. code-block:: python

   # Load recent data with weather forecasts
   # Must include the same features as training data
   recent_data = pd.read_csv('recent_data_with_weather_forecast.csv', 
                              index_col='datetime', parse_dates=True)
   
   # Create forecast
   forecast = create_forecast(pj, model, model_specs, recent_data)
   
   # Forecast DataFrame includes:
   # - forecast: median prediction (quantile 0.5)
   # - quantile_P10, quantile_P90: uncertainty bands
   # - stdev: standard deviation of prediction
   print(forecast.head())

The forecast DataFrame contains multiple columns representing different aspects of the prediction. The ``forecast`` column is your point prediction, while the quantile columns show uncertainty ranges. For example, there's a 10% chance the actual load will be below ``quantile_P10`` and a 10% chance it will be above ``quantile_P90``.

Evaluating Results
^^^^^^^^^^^^^^^^^^

After your forecast period, compare predictions against actual measurements to assess accuracy.

.. code-block:: python

   from openstef.metrics import metrics
   
   # Load actual measurements for the forecast period
   actuals = pd.read_csv('actuals.csv', index_col='datetime', parse_dates=True)
   
   # Merge forecast and actuals
   comparison = forecast.join(actuals['load'], rsuffix='_actual')
   
   # Calculate error metrics
   mae = metrics.mae(comparison['load_actual'], comparison['forecast'])
   rmse = metrics.rmse(comparison['load_actual'], comparison['forecast'])
   skill_score = metrics.skill_score(comparison['load_actual'], comparison['forecast'])
   
   print(f"Mean Absolute Error: {mae:.2f} MW")
   print(f"Root Mean Square Error: {rmse:.2f} MW")
   print(f"Skill Score: {skill_score:.3f}")

The skill score is particularly useful—it compares your model against a naive persistence forecast (predicting tomorrow will be like today). A skill score above 0.5 indicates your model is adding value.

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Energy split decomposition separates your forecast into interpretable components: baseload, wind-driven, solar-driven, and other effects. This is invaluable for understanding what drives your load and for explaining forecasts to stakeholders.

.. code-block:: python

   from openstef.pipeline import train_model_with_components, create_component_forecast
   
   # Train with component decomposition enabled
   # This trains separate models for each component
   model, model_specs, report, component_models = train_model_with_components(pj, data)
   
   # Create forecast with component breakdown
   forecast, components = create_component_forecast(
       pj, model, model_specs, component_models, recent_data
   )
   
   # Components DataFrame shows contribution of each factor
   print(components[['baseload', 'wind', 'solar', 'other']].head())
   
   # Verify components sum to total forecast
   assert (components.sum(axis=1) - forecast['forecast']).abs().max() < 0.01

Component forecasts help answer questions like "How much of tomorrow's peak is due to low wind?" or "What's our baseload trend over time?" This is especially useful for grid operators managing renewable integration.

Tutorial 2: Backtesting for Model Validation
---------------------------------------------

Backtesting evaluates how your model would have performed historically. This is essential before deploying to production—it reveals whether your model generalizes well and helps you choose between different modeling approaches.

We'll demonstrate using a realistic scenario: comparing XGBoost against a linear model for a Liander substation using 2024 data.

Setting Up the Backtest
^^^^^^^^^^^^^^^^^^^^^^^^

A backtest repeatedly trains models on historical data and evaluates forecasts on subsequent periods, simulating real-world deployment.

.. code-block:: python

   from openstef.validation.validation import backtest
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd
   
   # Load full year of historical data
   data = pd.read_csv('liander_substation_2024.csv', 
                      index_col='datetime', parse_dates=True)
   
   # Define two prediction jobs with different models
   pj_xgb = PredictionJob(
       id=1,
       name="liander_substation_xgb",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,
       resolution_minutes=15,
   )
   
   pj_linear = PredictionJob(
       id=2,
       name="liander_substation_linear",
       model="linear",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,
       resolution_minutes=15,
   )
   
   # Run backtest for both models
   # This trains on first 6 months, tests on next month, then slides forward
   results_xgb = backtest(
       pj_xgb, 
       data,
       train_window_days=180,  # Use 6 months for training
       test_window_days=30,    # Test on 1 month
       step_days=30,           # Slide forward 1 month at a time
   )
   
   results_linear = backtest(
       pj_linear,
       data,
       train_window_days=180,
       test_window_days=30,
       step_days=30,
   )

The backtest function returns detailed results for each test period, including forecasts, actuals, and error metrics.

Comparing Model Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Analyze the backtest results to determine which model performs best for your use case.

.. code-block:: python

   from openstef.metrics import metrics
   import matplotlib.pyplot as plt
   
   # Aggregate metrics across all backtest periods
   def summarize_backtest(results):
       all_mae = []
       all_rmse = []
       all_skill = []
       
       for period_result in results:
           comparison = period_result['forecast'].join(
               period_result['actuals'], rsuffix='_actual'
           )
           all_mae.append(metrics.mae(comparison['load_actual'], comparison['forecast']))
           all_rmse.append(metrics.rmse(comparison['load_actual'], comparison['forecast']))
           all_skill.append(metrics.skill_score(comparison['load_actual'], comparison['forecast']))
       
       return {
           'mae_mean': np.mean(all_mae),
           'mae_std': np.std(all_mae),
           'rmse_mean': np.mean(all_rmse),
           'skill_mean': np.mean(all_skill),
       }
   
   summary_xgb = summarize_backtest(results_xgb)
   summary_linear = summarize_backtest(results_linear)
   
   print("XGBoost Performance:")
   print(f"  MAE: {summary_xgb['mae_mean']:.2f} ± {summary_xgb['mae_std']:.2f} MW")
   print(f"  RMSE: {summary_xgb['rmse_mean']:.2f} MW")
   print(f"  Skill Score: {summary_xgb['skill_mean']:.3f}")
   
   print("\nLinear Model Performance:")
   print(f"  MAE: {summary_linear['mae_mean']:.2f} ± {summary_linear['mae_std']:.2f} MW")
   print(f"  RMSE: {summary_linear['rmse_mean']:.2f} MW")
   print(f"  Skill Score: {summary_linear['skill_mean']:.3f}")

Typically, XGBoost outperforms linear models for load forecasting because it captures non-linear relationships between weather and load. However, linear models train faster and are more interpretable, which may matter for some applications.

Analyzing Forecast Errors
^^^^^^^^^^^^^^^^^^^^^^^^^^

Beyond aggregate metrics, examine when and why forecasts fail. This guides model improvements.

.. code-block:: python

   # Combine all backtest periods for error analysis
   all_forecasts_xgb = pd.concat([r['forecast'] for r in results_xgb])
   all_actuals = pd.concat([r['actuals'] for r in results_xgb])
   
   combined = all_forecasts_xgb.join(all_actuals, rsuffix='_actual')
   combined['error'] = combined['forecast'] - combined['load_actual']
   combined['abs_error'] = combined['error'].abs()
   
   # Error by hour of day
   hourly_error = combined.groupby(combined.index.hour)['abs_error'].mean()
   print("Average error by hour:")
   print(hourly_error)
   
   # Error by forecast horizon
   # (requires tracking how far ahead each prediction was made)
   combined['horizon_hours'] = (combined.index - combined['forecast_time']) / pd.Timedelta(hours=1)
   horizon_error = combined.groupby('horizon_hours')['abs_error'].mean()
   
   # Plot error degradation with horizon
   plt.figure(figsize=(10, 6))
   horizon_error.plot()
   plt.xlabel('Forecast Horizon (hours)')
   plt.ylabel('Mean Absolute Error (MW)')
   plt.title('Forecast Error vs. Horizon')
   plt.savefig('error_by_horizon.png')

Common patterns include higher errors during morning/evening ramps, degrading accuracy with longer horizons, and larger errors during extreme weather events. Understanding these patterns helps you set realistic expectations and identify where model improvements will have the most impact.

Tutorial 3: Advanced Customization
-----------------------------------

OpenSTEF's default pipeline works well for most use cases, but you may need custom behavior for specialized applications. This tutorial shows how to extend OpenSTEF with custom data providers, workflows, and feature engineering.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

A target provider defines what you're forecasting and how to retrieve it. The default provider assumes a single load column, but you might need to forecast derived quantities like grid losses or free capacity.

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model
   import pandas as pd
   
   class GridLossTargetProvider:
       """Custom target provider for grid loss forecasting.
       
       Calculates losses as difference between input and output power.
       """
       
       def get_target(self, data: pd.DataFrame) -> pd.Series:
           """Calculate grid losses from input/output measurements."""
           if 'power_in' not in data.columns or 'power_out' not in data.columns:
               raise ValueError("Data must contain power_in and power_out columns")
           
           losses = data['power_in'] - data['power_out']
           
           # Validate losses are positive and reasonable
           if (losses < 0).any():
               raise ValueError("Negative losses detected - check data quality")
           if (losses > data['power_in'] * 0.2).any():
               raise ValueError("Losses exceed 20% - check data quality")
           
           return losses
       
       def get_target_name(self) -> str:
           return "grid_losses"
   
   # Use custom target provider
   data = pd.read_csv('grid_data.csv', index_col='datetime', parse_dates=True)
   
   target_provider = GridLossTargetProvider()
   target = target_provider.get_target(data)
   
   # Add target to data for training
   data['load'] = target  # OpenSTEF expects 'load' column
   
   pj = PredictionJob(
       id=1,
       name="grid_losses",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,
       resolution_minutes=15,
   )
   
   model, model_specs, report = train_model(pj, data)

Custom target providers are useful for forecasting derived quantities, combining multiple data sources, or applying domain-specific transformations before modeling.

Custom Workflow
^^^^^^^^^^^^^^^

The default pipeline (load data → train → forecast → evaluate) works for batch scenarios, but you might need custom orchestration for real-time systems or complex data dependencies.

.. code-block:: python

   from openstef.pipeline import train_model, create_forecast
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd
   from datetime import datetime, timedelta
   
   class RealTimeForecastWorkflow:
       """Custom workflow for real-time forecasting with automatic retraining."""
       
       def __init__(self, pj: PredictionJob, data_source, retrain_interval_days=7):
           self.pj = pj
           self.data_source = data_source
           self.retrain_interval = timedelta(days=retrain_interval_days)
           self.model = None
           self.model_specs = None
           self.last_train_time = None
       
       def should_retrain(self) -> bool:
           """Check if model needs retraining."""
           if self.model is None:
               return True
           if datetime.now() - self.last_train_time > self.retrain_interval:
               return True
           return False
       
       def run(self) -> pd.DataFrame:
           """Execute workflow: retrain if needed, then forecast."""
           
           # Fetch latest data
           data = self.data_source.get_historical_data(days=365)
           
           # Retrain if necessary
           if self.should_retrain():
               print(f"Retraining model at {datetime.now()}")
               self.model, self.model_specs, report = train_model(self.pj, data)
               self.last_train_time = datetime.now()
               
               # Log training performance
               print(f"Training R²: {report['r2_score']:.3f}")
           
           # Get recent data with weather forecast
           recent_data = self.data_source.get_recent_data_with_forecast()
           
           # Create forecast
           forecast = create_forecast(
               self.pj, self.model, self.model_specs, recent_data
           )
           
           # Post-process: clip negative forecasts
           forecast['forecast'] = forecast['forecast'].clip(lower=0)
           
           return forecast
   
   # Use custom workflow
   pj = PredictionJob(id=1, name="realtime_forecast", model="xgb")
   workflow = RealTimeForecastWorkflow(pj, data_source=my_data_source)
   
   # Run periodically (e.g., every 15 minutes via cron or scheduler)
   forecast = workflow.run()

Custom workflows give you full control over when and how models are trained and deployed. This is essential for production systems with specific requirements around retraining frequency, data freshness, or integration with external systems.

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF automatically engineers features from weather and time data, but you may have domain-specific features that improve accuracy.

.. code-block:: python

   from openstef.pipeline import train_model
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd
   import numpy as np
   
   def add_custom_features(data: pd.DataFrame) -> pd.DataFrame:
       """Add domain-specific features for industrial load forecasting."""
       
       data = data.copy()
       
       # Working day indicator (accounting for holidays)
       data['is_working_day'] = (
           (data.index.dayofweek < 5) &  # Monday-Friday
           (~data.index.isin(get_holidays()))  # Not a holiday
       )
       
       # Shift patterns (3 shifts per day for industrial facilities)
       hour = data.index.hour
       data['shift_1'] = ((hour >= 6) & (hour < 14)).astype(int)
       data['shift_2'] = ((hour >= 14) & (hour < 22)).astype(int)
       data['shift_3'] = ((hour >= 22) | (hour < 6)).astype(int)
       
       # Temperature-load interaction (heating/cooling effects)
       # Load increases when temperature is far from comfort zone
       comfort_temp = 18
       data['temp_discomfort'] = (data['temperature'] - comfort_temp).abs()
       
       # Wind chill effect (feels colder with wind)
       data['wind_chill'] = data['temperature'] - 0.5 * data['windspeed']
       
       # Lagged load features (recent history)
       data['load_lag_24h'] = data['load'].shift(96)  # 96 periods = 24h at 15min resolution
       data['load_lag_168h'] = data['load'].shift(672)  # 1 week ago
       
       # Rolling statistics
       data['load_rolling_mean_24h'] = data['load'].rolling(96).mean()
       data['load_rolling_std_24h'] = data['load'].rolling(96).std()
       
       return data
   
   def get_holidays():
       """Return list of holiday dates."""
       # Simplified - use a proper holiday library in production
       return pd.DatetimeIndex([
           '2024-01-01', '2024-12-25', '2024-12-26'
       ])
   
   # Apply custom features
   data = pd.read_csv('industrial_load.csv', index_col='datetime', parse_dates=True)
   data = add_custom_features(data)
   
   pj = PredictionJob(
       id=1,
       name="industrial_forecast",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,
       resolution_minutes=15,
   )
   
   # Train with custom features
   model, model_specs, report = train_model(pj, data)
   
   # Check if custom features are important
   print("Top 10 features:")
   for feature, importance in report['feature_importance'][:10]:
       print(f"  {feature}: {importance:.3f}")

Good custom features encode domain knowledge that the model can't learn from raw data alone. Examples include shift patterns for industrial loads, school calendars for residential areas, or tide schedules for coastal regions.

.. note::

   When adding custom features, ensure they're available at forecast time. Features based on future load values (like ``load_lag_24h`` for tomorrow) won't be available when making real forecasts.

Next Steps
----------

You now have the tools to implement OpenSTEF in production. For specific deployment tasks, see :doc:`../guides/how_to_guides`. To understand forecasting concepts in depth, read :doc:`../reference/concepts`. For help choosing the right approach for your application, check :doc:`../guides/use_cases`.

If you encounter issues or have questions, visit our community channels listed on the :doc:`../index` page.