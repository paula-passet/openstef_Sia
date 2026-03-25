Tutorials
=========


Overview
--------


These tutorials demonstrate how to integrate OpenSTEF as a Python library into your own applications and workflows. OpenSTEF is designed as a software package that provides machine learning functionality for energy forecasting, which you can embed within your existing systems or use to build custom forecasting solutions. The examples progress from basic usage patterns to more advanced integration scenarios, showing you how to leverage OpenSTEF's pipelines, feature engineering capabilities, and forecasting models programmatically in your code.


These tutorials are organized into three progressive levels to help you master OpenSTEF as a machine learning library for energy forecasting. The **Basic Tutorial** introduces core concepts and walks you through creating your first forecast using OpenSTEF's pipeline architecture with sample data. The **Intermediate Tutorial** dives deeper into feature engineering, model customization, and working with real-world data scenarios including handling missing values and applying advanced preprocessing techniques. The **Advanced Tutorial** covers sophisticated topics like confidence interval estimation, custom model implementations, and integrating OpenSTEF into production workflows. Each tutorial builds upon the previous one, providing hands-on examples with realistic parameters and practical code snippets that demonstrate how to leverage OpenSTEF's capabilities for your specific energy forecasting needs.


- Basic Python programming knowledge and familiarity with data science libraries

- Understanding of machine learning concepts, particularly time series forecasting

- Experience with pandas DataFrames and data manipulation

- Knowledge of energy systems and load forecasting concepts (helpful but not required)

- Familiarity with Jupyter Notebooks for interactive development

- Basic understanding of feature engineering and model training workflows


First Use Tutorial
------------------


In this tutorial, we'll walk through your first experience using OpenSTEF to create energy load forecasts. We'll use a realistic scenario where you need to forecast electricity demand for a specific location on the energy grid. By the end of this tutorial, you'll understand how to set up a basic forecasting pipeline using OpenSTEF's built-in presets, which provide pre-configured settings that work well for most common use cases. This hands-on approach will demonstrate OpenSTEF's core functionality as a Python library for short-term energy forecasting, showing you how to go from raw input data to actionable forecasts with confidence intervals. We'll cover the essential steps including data preparation, model training, and generating multi-horizon forecasts that you can use for grid management and planning decisions.


.. note::

   OpenSTEF is a Python library, not a standalone application. You integrate it into your own systems and workflows. While this tutorial shows basic usage, in practice you'll typically embed OpenSTEF within your own data pipelines, scheduling systems, or applications. You're responsible for data fetching, storage, and result handling - OpenSTEF focuses purely on the machine learning forecasting functionality.


Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^


OpenSTEF requires input data in a specific format to perform accurate energy forecasting. The library expects time series data that includes both historical load measurements and relevant features such as weather data, calendar information, and other external factors that influence energy consumption. Data should be provided as pandas DataFrames with datetime indices, where each row represents a timestamp and columns contain the various input features. The format supports both univariate forecasting (using only historical load data) and multivariate forecasting (incorporating additional predictive features like temperature, solar radiation, and wind speed). OpenSTEF's data preprocessing pipeline can handle missing values and perform automatic feature engineering, but the input data structure must follow the library's expected schema with properly formatted timestamps and numeric values for optimal performance.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   from datetime import datetime, timedelta

   # Load data from CSV file
   data = pd.read_csv('energy_data.csv', parse_dates=['datetime'])
   data.set_index('datetime', inplace=True)

   # Example data structure required by OpenSTEF
   # Columns should include: load, temperature, humidity, windspeed, radiation, etc.
   print(data.head())

   # Alternative: Load from database connection
   import sqlalchemy as sa

   engine = sa.create_engine('postgresql://user:password@localhost:5432/energy_db')
   query = """
   SELECT datetime, load, temperature, humidity, windspeed, radiation
   FROM energy_measurements
   WHERE datetime >= %s AND datetime <= %s
   ORDER BY datetime
   """

   start_date = datetime.now() - timedelta(days=30)
   end_date = datetime.now()
   data = pd.read_sql(query, engine, params=[start_date, end_date], parse_dates=['datetime'])
   data.set_index('datetime', inplace=True)

   # Ensure data has the required frequency (typically hourly)
   data = data.asfreq('H')

   # Basic data validation
   print(f"Data shape: {data.shape}")
   print(f"Date range: {data.index.min()} to {data.index.max()}")
   print(f"Missing values: {data.isnull().sum()}")


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.validation import validation

   # Load your energy consumption data
   # Data should have datetime index and load column
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)

   # Create a prediction job configuration
   pj = PredictionJob(
       id=123,
       name="substation_forecast",
       model="xgb",
       resolution_minutes=15,
       horizon_minutes=2880,  # 48 hours ahead
       train_components=0.95
   )

   # Validate data format and requirements
   validation_result = validation.validate_data(data, pj)
   if not validation_result.is_valid:
       print(f"Data validation failed: {validation_result.errors}")

   # Check for required columns and data quality
   required_columns = ['load', 'T-1h', 'T-7d', 'radiation', 'windspeed_100m']
   missing_cols = [col for col in required_columns if col not in data.columns]
   if missing_cols:
       print(f"Missing required columns: {missing_cols}")

   # Handle missing values and outliers
   data_clean = data.copy()
   # Remove outliers using IQR method
   Q1 = data_clean['load'].quantile(0.25)
   Q3 = data_clean['load'].quantile(0.75)
   IQR = Q3 - Q1
   lower_bound = Q1 - 1.5 * IQR
   upper_bound = Q3 + 1.5 * IQR
   data_clean = data_clean[(data_clean['load'] >= lower_bound) & (data_clean['load'] <= upper_bound)]

   # Forward fill weather data gaps (max 3 hours)
   weather_cols = ['T-1h', 'radiation', 'windspeed_100m']
   data_clean[weather_cols] = data_clean[weather_cols].fillna(method='ffill', limit=12)

   # Ensure datetime index is properly formatted and sorted
   data_clean.index = pd.to_datetime(data_clean.index)
   data_clean = data_clean.sort_index()

   # Resample to ensure consistent 15-minute intervals
   data_resampled = data_clean.resample('15min').mean()

   print(f"Original data shape: {data.shape}")
   print(f"Cleaned data shape: {data_resampled.shape}")
   print(f"Data range: {data_resampled.index.min()} to {data_resampled.index.max()}")


.. [DIAGRAM: Data flow from raw input to OpenSTEF-ready format]


Training Your First Model
^^^^^^^^^^^^^^^^^^^^^^^^^


OpenSTEF provides several preset configurations through its pipeline system to simplify common forecasting workflows. The library includes six main pipelines that serve different use cases: `train_model` for basic model training, `create_forecast` for generating predictions, `optimize_hyperparameters` for automated parameter tuning, `create_component_forecast` for disaggregated forecasting, `create_basecase_forecast` for baseline comparisons, and `train_create_forecast_backtest` for comprehensive model evaluation. These preset configurations are designed to handle the complete machine learning workflow including data validation, feature engineering, and model training with minimal setup required. For beginners, the `train_model` pipeline is typically the best starting point as it provides a straightforward path to training your first forecasting model with default parameters that work well for most energy load forecasting scenarios.


.. code-block:: python

   ```python
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   import pandas as pd

   # Sample prediction job configuration with presets
   pj = {
       'id': 123,
       'name': 'solar_farm_forecast',
       'model': 'xgb',
       'horizon_minutes': 2880,  # 48 hours
       'resolution_minutes': 15,
       'train_components': False,
       'feature_names': ['load_entsoe', 'weather_temp', 'weather_radiation_global']
   }

   # Load your training data (example structure)
   # In practice, this would come from your database or data source
   train_data = pd.DataFrame({
       'datetime': pd.date_range('2023-01-01', periods=1000, freq='15min'),
       'load_entsoe': [100 + i * 0.1 for i in range(1000)],
       'weather_temp': [15 + (i % 24) * 0.5 for i in range(1000)],
       'weather_radiation_global': [200 + (i % 96) * 2 for i in range(1000)]
   })
   train_data.set_index('datetime', inplace=True)

   # Train the model using OpenSTEF pipeline
   model = train_model_pipeline(pj, train_data)

   print(f"Model trained successfully: {type(model).__name__}")
   print(f"Feature importance available: {hasattr(model, 'feature_importances_')}")
   ```


.. code-block:: python

   ```python
   from openstef.pipeline import train_model
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   import logging

   # Configure logging to monitor training progress
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   # Define prediction job configuration
   pj = {
       "id": 307,
       "model": "xgb_quantile",
       "horizon_minutes": 2880,  # 48 hours
       "train_components": False,
       "hyper_params": {
           "n_estimators": 100,
           "max_depth": 6,
           "learning_rate": 0.1
       }
   }

   # Train model with validation monitoring
   logger.info("Starting model training...")
   model_specs = train_model(
       pj=pj,
       input_data=train_data,
       validation_data=validation_data
   )

   # Monitor training metrics
   if model_specs:
       logger.info(f"Training completed successfully")
       logger.info(f"Model type: {model_specs.get('model_type')}")
       logger.info(f"Feature count: {len(model_specs.get('feature_names', []))}")

       # Check validation scores if available
       if 'validation_score' in model_specs:
           logger.info(f"Validation RMSE: {model_specs['validation_score']:.3f}")

       # Monitor feature importance
       if hasattr(model_specs.get('model'), 'feature_importances_'):
           top_features = sorted(
               zip(model_specs['feature_names'],
                   model_specs['model'].feature_importances_),
               key=lambda x: x[1], reverse=True
           )[:5]
           logger.info("Top 5 important features:")
           for feature, importance in top_features:
               logger.info(f"  {feature}: {importance:.3f}")
   else:
       logger.error("Training failed - check data quality and configuration")
   ```


.. note::

   During model training, OpenSTEF performs several key steps: data validation to check for issues like flatliners, feature engineering to create relevant input features based on your configuration (such as energy load from yesterday or last week), and machine learning model training using the specified algorithm (like XGBoost quantile models). The training duration varies significantly depending on your dataset size, feature complexity, and chosen model type, but typically ranges from a few minutes for simple models with small datasets to several hours for complex models with extensive historical data and multiple features.


Creating Forecasts
^^^^^^^^^^^^^^^^^^


Once you have a trained model, generating forecasts with OpenSTEF is straightforward using the library's forecasting API. The forecasting process combines input data preparation with feature engineering, allowing for single-shot, multi-horizon predictions that can forecast multiple time steps ahead in one operation. OpenSTEF produces forecasts with confidence estimates using two available methods, providing not just point predictions but also uncertainty quantification to help assess forecast reliability. The output format includes the predicted values along with confidence intervals, enabling users to understand both the expected outcome and the associated uncertainty for each forecast horizon.


.. code-block:: python

   ```python
   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core
   from datetime import datetime, timedelta

   # Load your trained model (assuming you have one from previous training)
   model = XGBQuantileOpenstfRegressor()
   # model.load_model('path/to/your/trained_model.pkl')  # Load your trained model

   # Prepare input data with weather forecasts and other features
   # This should include the same features used during training
   input_data = pd.DataFrame({
       'datetime': pd.date_range(start='2024-01-01', periods=48, freq='15T'),
       'load': [100.0] * 48,  # Historical load values
       'temp': [15.2, 15.5, 15.8] * 16,  # Weather forecast data
       'humidity': [65.0, 66.0, 64.0] * 16,
       'wind_speed': [8.5, 9.0, 8.2] * 16,
       # Add other relevant features used in your model
   })
   input_data.set_index('datetime', inplace=True)

   # Generate forecasts for different horizons
   # Short-term: next 6 hours (24 periods of 15-minute intervals)
   forecast_6h = create_forecast_pipeline_core(
       input_data=input_data,
       model=model,
       horizon_minutes=360,  # 6 hours
       resolution_minutes=15
   )

   # Medium-term: next 24 hours (96 periods of 15-minute intervals)
   forecast_24h = create_forecast_pipeline_core(
       input_data=input_data,
       model=model,
       horizon_minutes=1440,  # 24 hours
       resolution_minutes=15
   )

   # Long-term: next 48 hours (192 periods of 15-minute intervals)
   forecast_48h = create_forecast_pipeline_core(
       input_data=input_data,
       model=model,
       horizon_minutes=2880,  # 48 hours
       resolution_minutes=15
   )

   # The forecasts include confidence intervals
   print("6-hour forecast shape:", forecast_6h.shape)
   print("24-hour forecast shape:", forecast_24h.shape)
   print("48-hour forecast shape:", forecast_48h.shape)

   # Access forecast values and confidence intervals
   print("\nSample 6-hour forecast:")
   print(forecast_6h[['forecast', 'forecast_lower', 'forecast_upper']].head())
   ```


.. code-block:: python

   # Access forecast quantiles and confidence intervals
   forecast_result = pipeline.predict(
       pj=prediction_job,
       input_data=input_data,
       mlflow_tracking_uri="sqlite:///mlruns.db"
   )

   # The forecast result contains quantiles for uncertainty estimation
   print("Available forecast columns:", forecast_result.columns.tolist())

   # Access different quantiles
   forecast_10th = forecast_result['quantile_P10']  # 10th percentile
   forecast_50th = forecast_result['quantile_P50']  # Median forecast
   forecast_90th = forecast_result['quantile_P90']  # 90th percentile

   # Calculate confidence intervals
   confidence_80_lower = forecast_result['quantile_P10']
   confidence_80_upper = forecast_result['quantile_P90']
   confidence_interval_width = confidence_80_upper - confidence_80_lower

   print(f"80% confidence interval width: {confidence_interval_width.mean():.2f}")

   # Display forecast with uncertainty bounds
   import matplotlib.pyplot as plt

   plt.figure(figsize=(12, 6))
   plt.plot(forecast_result.index, forecast_50th, label='Median Forecast', color='blue')
   plt.fill_between(forecast_result.index, confidence_80_lower, confidence_80_upper,
                    alpha=0.3, color='blue', label='80% Confidence Interval')
   plt.xlabel('Time')
   plt.ylabel('Load (MW)')
   plt.title('Energy Load Forecast with Confidence Intervals')
   plt.legend()
   plt.show()


.. image:: _static/images/placeholder_example_forecast_visualization_showing_predictions_with_confidence_bands.png
   :alt: Example forecast visualization showing predictions with confidence bands
   :align: center


Evaluating Model Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^


OpenSTEF provides a comprehensive suite of evaluation metrics designed to assess forecasting performance across different aspects of energy prediction. The library includes standard regression metrics like Mean Absolute Error (MAE), Root Mean Square Error (RMSE), and bias, alongside specialized energy forecasting metrics such as the Franks Skill Score for peak detection and relative metrics that focus on the highest and lowest values in your dataset. These metrics help you understand not just overall accuracy, but also how well your models perform during critical periods like peak demand or low generation scenarios. The evaluation framework also includes confidence interval assessment through metrics like fraction in standard deviation (frac_in_stdev), allowing you to validate the reliability of your uncertainty estimates alongside point forecasts.


.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.metrics.metrics import mae, rmse, bias, skill_score, r_mae_highest, r_mae_lowest

   # Assume we have predictions and actual values from our trained model
   # In practice, these would come from your model's predict() method
   actual_values = np.array([100, 120, 95, 110, 130, 105, 115, 125, 90, 140])
   predicted_values = np.array([98, 115, 100, 108, 125, 110, 112, 120, 95, 135])

   # Calculate basic evaluation metrics
   mae_score = mae(actual_values, predicted_values)
   rmse_score = rmse(actual_values, predicted_values)
   bias_score = bias(actual_values, predicted_values)

   print(f"Mean Absolute Error (MAE): {mae_score:.2f}")
   print(f"Root Mean Square Error (RMSE): {rmse_score:.2f}")
   print(f"Bias: {bias_score:.2f}")

   # Calculate skill score (compares against naive persistence forecast)
   naive_forecast = np.roll(actual_values, 1)[1:]  # Previous value as forecast
   skill_score_value = skill_score(actual_values[1:], predicted_values[1:], naive_forecast)
   print(f"Skill Score: {skill_score_value:.3f}")

   # Calculate relative errors for peak values
   r_mae_high = r_mae_highest(actual_values, predicted_values)
   r_mae_low = r_mae_lowest(actual_values, predicted_values)

   print(f"Relative MAE for highest 5% values: {r_mae_high:.3f}")
   print(f"Relative MAE for lowest 5% values: {r_mae_low:.3f}")

   # Create a summary DataFrame for easy visualization
   metrics_summary = pd.DataFrame({
       'Metric': ['MAE', 'RMSE', 'Bias', 'Skill Score', 'R-MAE High', 'R-MAE Low'],
       'Value': [mae_score, rmse_score, bias_score, skill_score_value, r_mae_high, r_mae_low]
   })

   print("\nMetrics Summary:")
   print(metrics_summary.to_string(index=False, float_format='%.3f'))


.. code-block:: python

   # Generate comprehensive evaluation plots and visualizations
   from openstef.metrics.figure import plot_data_series, plot_feature_importance
   from openstef.metrics.metrics import mae, rmse, bias, skill_score
   from openstef.metrics.reporter import Reporter
   import matplotlib.pyplot as plt
   import pandas as pd

   # Assume we have predictions and actual values from previous steps
   # predictions_df contains columns: 'forecast', 'realised', 'datetime'

   # Create evaluation plots
   fig, axes = plt.subplots(2, 2, figsize=(15, 10))

   # Plot 1: Time series comparison
   plot_data_series(
       predictions_df['datetime'],
       [predictions_df['realised'], predictions_df['forecast']],
       labels=['Actual', 'Forecast'],
       ax=axes[0, 0]
   )
   axes[0, 0].set_title('Forecast vs Actual Values')
   axes[0, 0].legend()

   # Plot 2: Scatter plot for correlation
   axes[0, 1].scatter(predictions_df['realised'], predictions_df['forecast'], alpha=0.6)
   axes[0, 1].plot([predictions_df['realised'].min(), predictions_df['realised'].max()],
                   [predictions_df['realised'].min(), predictions_df['realised'].max()],
                   'r--', lw=2)
   axes[0, 1].set_xlabel('Actual Values')
   axes[0, 1].set_ylabel('Predicted Values')
   axes[0, 1].set_title('Prediction Accuracy Scatter Plot')

   # Plot 3: Residuals over time
   residuals = predictions_df['forecast'] - predictions_df['realised']
   axes[1, 0].plot(predictions_df['datetime'], residuals)
   axes[1, 0].axhline(y=0, color='r', linestyle='--')
   axes[1, 0].set_xlabel('Time')
   axes[1, 0].set_ylabel('Residuals')
   axes[1, 0].set_title('Residuals Over Time')

   # Plot 4: Feature importance (if available)
   if hasattr(trained_model, 'feature_importances_'):
       feature_names = ['load_lag_1', 'temp', 'wind_speed', 'hour', 'day_of_week']
       plot_feature_importance(
           trained_model.feature_importances_[:len(feature_names)],
           feature_names,
           ax=axes[1, 1]
       )
       axes[1, 1].set_title('Feature Importance')

   plt.tight_layout()
   plt.show()

   # Generate comprehensive evaluation report
   reporter = Reporter()
   report = reporter.generate_report(
       realised=predictions_df['realised'],
       forecast=predictions_df['forecast'],
       model=trained_model,
       feature_names=feature_names if 'feature_names' in locals() else None
   )

   # Print key metrics
   print("Model Performance Metrics:")
   print(f"MAE: {mae(predictions_df['realised'], predictions_df['forecast']):.2f}")
   print(f"RMSE: {rmse(predictions_df['realised'], predictions_df['forecast']):.2f}")
   print(f"Bias: {bias(predictions_df['realised'], predictions_df['forecast']):.2f}")
   print(f"Skill Score: {skill_score(predictions_df['realised'], predictions_df['forecast']):.3f}")

   # Save detailed report to disk
   reporter.write_report_to_disk(report, 'model_evaluation_report.html')


.. image:: _static/images/placeholder_example_evaluation_dashboard_showing_various_performance_metrics.png
   :alt: Example evaluation dashboard showing various performance metrics
   :align: center


Energy Split Analysis
^^^^^^^^^^^^^^^^^^^^^


Energy split analysis in OpenSTEF refers to the decomposition of total energy forecasts into their constituent components, enabling detailed understanding of different energy sources or consumption patterns within a single prediction. This functionality is particularly valuable for grid operators and energy companies who need to understand not just the total energy demand or supply, but how different components contribute to the overall forecast. The OpenSTEF library implements this through its Domain Adaptation for Zero Shot Learning in Sequence (DAZLS) methodology, which allows for sophisticated splitting of energy forecasts based on historical patterns and learned relationships between different energy components. Applications include analyzing renewable versus conventional energy contributions, separating industrial from residential consumption patterns, or breaking down regional energy flows to better inform grid management decisions and capacity planning strategies.


.. code-block:: python

   ```python
   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.feature_engineering.apply_features import apply_features

   # Load your energy data with components (solar, wind, load, etc.)
   data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)

   # Prepare prediction job configuration for energy split analysis
   pj = {
       'id': 307,
       'name': 'Energy_Split_Analysis',
       'model': 'xgb_quantile',
       'horizon_minutes': 2880,  # 48 hours ahead
       'resolution_minutes': 15,
       'train_components': ['solar', 'wind', 'conventional'],
       'feature_names': ['T-1d', 'T-7d', 'humidity', 'radiation', 'windspeed_100m']
   }

   # Apply feature engineering for split analysis
   data_with_features = apply_features(data, pj)

   # Train model for total energy forecast
   model = train_model_pipeline(
       pj=pj,
       input_data=data_with_features,
       model_type=XGBQuantileOpenstfRegressor()
   )

   # Create forecast with energy component breakdown
   forecast_result = create_forecast_pipeline(
       pj=pj,
       input_data=data_with_features,
       model=model
   )

   # Analyze energy split components
   total_forecast = forecast_result['forecast']
   components = {}

   # Calculate component contributions
   for component in ['solar', 'wind', 'conventional']:
       if f'{component}_forecast' in forecast_result:
           components[component] = forecast_result[f'{component}_forecast']
           contribution_pct = (components[component] / total_forecast * 100).fillna(0)
           print(f"{component.title()} contribution: {contribution_pct.mean():.1f}% average")

   # Identify peak contribution periods
   peak_solar_hours = components['solar'].between_time('10:00', '16:00')
   peak_wind_periods = components['wind'][components['wind'] > components['wind'].quantile(0.8)]

   print(f"Peak solar generation: {peak_solar_hours.max():.2f} MW")
   print(f"High wind periods: {len(peak_wind_periods)} intervals")

   # Export split analysis results
   split_analysis = pd.DataFrame({
       'total_forecast': total_forecast,
       **components,
       'renewable_share': (components['solar'] + components['wind']) / total_forecast * 100
   })

   split_analysis.to_csv('energy_split_analysis.csv')
   ```


.. image:: _static/images/placeholder_energy_split_visualization_showing_different_energy_components.png
   :alt: Energy split visualization showing different energy components
   :align: center


Backtesting Tutorial
--------------------


Backtesting is a critical validation technique that evaluates how well your forecasting models would have performed on historical data. In OpenSTEF, backtesting allows you to simulate the entire forecasting process using past data, where you train models on historical periods and test their predictions against known outcomes. This retrospective analysis is essential for understanding model reliability, identifying potential overfitting, and comparing different forecasting approaches before deploying them in production. OpenSTEF's backtesting capabilities include specialized forecaster classes like OpenSTEF4BacktestForecaster that can replay historical forecasting scenarios while maintaining the same feature engineering and prediction methodologies used in live forecasting. By validating your models against historical data, you can build confidence in their performance and make informed decisions about model selection and deployment strategies.


This tutorial demonstrates OpenSTEF's backtesting capabilities through a comprehensive historical validation scenario based on Liander's 2024 energy grid forecasting challenges. The example walks through validating forecast accuracy across multiple grid components using real historical data from Dutch distribution networks. You'll learn how to configure OpenSTEF4BacktestForecaster instances to evaluate model performance against actual energy consumption patterns, including handling renewable energy integration effects and grid balancing scenarios that were critical during 2024's energy transition period. This practical scenario showcases OpenSTEF's resilient forecasting strategies and probabilistic forecast capabilities in a real-world context where forecast availability was essential for grid stability decisions.


Setting Up Backtest Framework
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Before running backtests with OpenSTEF, you need to prepare your data environment and configure the backtesting framework. The backtesting system requires two primary datasets: ground truth data containing actual energy measurements and predictor data with historical features. Both datasets must be structured as VersionedTimeSeriesDataset objects with consistent time indexing and appropriate frequency matching. Data preparation involves ensuring sufficient historical coverage - typically several months to years depending on your forecasting horizon - and validating data completeness using OpenSTEF's validation functions. The BacktestConfig class allows you to specify simulation parameters including training windows, prediction intervals, and model update frequencies, while the BacktestPipeline orchestrates the entire simulation process by generating realistic training and prediction events that mirror operational forecasting scenarios.


.. code-block:: python

   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline
   from datetime import datetime, timedelta
   import pandas as pd

   # Configure backtesting parameters
   config = BacktestConfig(
       model_type="xgb",
       horizons=[0.25, 1.0, 6.0, 24.0, 47.0],  # Forecast horizons in hours
       train_window_days=90,  # Training window length
       retrain_frequency_days=7,  # How often to retrain the model
       validation_fraction=0.2,  # Fraction of training data for validation
       feature_importance=True,  # Calculate feature importance
       save_predictions=True  # Save prediction results
   )

   # Define backtesting time window
   start_date = datetime(2023, 1, 1)
   end_date = datetime(2023, 12, 31)

   # Initialize backtesting pipeline
   pipeline = BacktestPipeline(config=config)

   # Run backtest simulation
   results = pipeline.run(
       ground_truth=ground_truth_dataset,
       predictors=predictor_dataset,
       start=start_date,
       end=end_date,
       show_progress=True
   )


.. [DIAGRAM: Backtesting timeline showing training and validation periods]


Comparing Multiple Models
^^^^^^^^^^^^^^^^^^^^^^^^^


Comparing different forecasting models is essential for understanding which approaches work best for your specific energy forecasting scenarios. OpenSTEF's benchmarking capabilities allow you to systematically evaluate multiple model configurations across the same datasets, providing quantitative insights into their relative performance. Through backtesting simulations that mirror real-world operational conditions, you can assess how different models would have performed historically, helping you make informed decisions about which approaches to deploy in production. The library's comparison pipeline generates comprehensive analysis at global, group, and individual target levels, enabling you to identify patterns in model performance across different types of forecasting challenges and select the most appropriate model for each use case.


.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef.model.regressors import XGBQuantileOpenstfRegressor, LinearQuantileOpenstfRegressor
   from datetime import datetime

   # Configure two different models for comparison
   xgb_config = BacktestConfig(
       model=XGBQuantileOpenstfRegressor(),
       horizon_hours=47,
       resolution_minutes=15,
       feature_names=['load_entsoe', 'weather_temp', 'weather_windspeed'],
       train_horizons_hours=[0.25, 24, 47]
   )

   linear_config = BacktestConfig(
       model=LinearQuantileOpenstfRegressor(),
       horizon_hours=47,
       resolution_minutes=15,
       feature_names=['load_entsoe', 'weather_temp', 'weather_windspeed'],
       train_horizons_hours=[0.25, 24, 47]
   )

   # Set up backtest pipelines for both models
   xgb_pipeline = BacktestPipeline(xgb_config)
   linear_pipeline = BacktestPipeline(linear_config)

   # Run backtests for the same period
   start_date = datetime(2023, 1, 1)
   end_date = datetime(2023, 3, 31)

   xgb_results = xgb_pipeline.run(
       ground_truth=ground_truth_data,
       predictors=predictor_data,
       start=start_date,
       end=end_date,
       show_progress=True
   )

   linear_results = linear_pipeline.run(
       ground_truth=ground_truth_data,
       predictors=predictor_data,
       start=start_date,
       end=end_date,
       show_progress=True
   )

   # Compare results using benchmark comparison
   run_data = {
       'XGBoost': xgb_results,
       'Linear': linear_results
   }

   comparison_pipeline = BenchmarkComparisonPipeline()
   comparison_results = comparison_pipeline.run(run_data)


.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from datetime import datetime, timedelta
   import pandas as pd

   # Define different time periods for comparison
   periods = {
       "summer_2023": (datetime(2023, 6, 1), datetime(2023, 8, 31)),
       "winter_2023": (datetime(2023, 12, 1), datetime(2024, 2, 29)),
       "spring_2024": (datetime(2024, 3, 1), datetime(2024, 5, 31))
   }

   # Configure backtesting for each period
   results = {}
   for period_name, (start_date, end_date) in periods.items():
       # Set up backtest configuration
       config = BacktestConfig(
           model_type="xgb",
           horizon_minutes=15,
           resolution_minutes=15,
           train_horizon_hours=2160  # 90 days
       )

       # Initialize pipeline
       pipeline = BacktestPipeline(config)

       # Run backtesting for the specific period
       predictions = pipeline.run(
           ground_truth=ground_truth_data,
           predictors=predictor_data,
           start=start_date,
           end=end_date,
           show_progress=True
       )

       results[period_name] = predictions

   # Compare performance across periods using benchmark comparison
   comparison_pipeline = BenchmarkComparisonPipeline()

   # Prepare run data for comparison
   run_data = {
       period_name: benchmark_storage
       for period_name, benchmark_storage in results.items()
   }

   # Execute comparison analysis
   comparison_results = comparison_pipeline.run(run_data)

   # Display performance metrics by period
   for period_name in periods.keys():
       period_metrics = comparison_results.get_period_metrics(period_name)
       print(f"{period_name.title()} Performance:")
       print(f"  MAE: {period_metrics['mae']:.2f}")
       print(f"  RMSE: {period_metrics['rmse']:.2f}")
       print(f"  MAPE: {period_metrics['mape']:.2f}%")
       print()


.. image:: _static/images/placeholder_comparative_performance_charts_showing_two_models_over_time.png
   :alt: Comparative performance charts showing two models over time
   :align: center


Analyzing Backtest Results
^^^^^^^^^^^^^^^^^^^^^^^^^^


After running a backtest, OpenSTEF provides several tools to help you interpret and analyze the results. The backtest pipeline returns a TimeSeriesDataset containing predictions that can be compared against ground truth data to evaluate model performance. Use the WindowedMetricPlotter to visualize how your model's performance metrics change over time by adding your model's timestamps and metric values, then creating time series plots that reveal patterns in forecasting accuracy. The PerformanceMeter helps you understand computational performance by tracking timing checkpoints throughout the backtesting process. When analyzing results, pay attention to periods where performance degrades, as these may indicate when model retraining is needed or when external factors significantly impact forecasting accuracy. The batch processing capabilities allow you to efficiently analyze large datasets while maintaining realistic simulation conditions that mirror production deployment scenarios.


.. code-block:: python

   ```python
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.analysis.plots import WindowedMetricPlotter
   from openstef.monitoring import PerformanceMeter
   import pandas as pd
   from datetime import datetime, timedelta

   # Configure comprehensive backtest analysis
   config = BacktestConfig(
       model_type="xgb",
       horizon_minutes=15,
       train_window_days=30,
       retrain_frequency_hours=24
   )

   # Initialize performance monitoring
   perf_meter = PerformanceMeter(logger)

   # Run backtest pipeline
   pipeline = BacktestPipeline(config)
   perf_meter.start_level("backtest", "comprehensive_analysis")

   predictions = pipeline.run(
       ground_truth=historical_data,
       predictors=predictor_data,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True
   )

   perf_meter.checkpoint("backtest_complete")

   # Generate comprehensive analysis reports
   analysis_results = {}

   # Calculate time-windowed metrics
   timestamps = predictions.index.tolist()
   mae_values = []
   rmse_values = []

   for i in range(len(predictions)):
       window_start = max(0, i - 168)  # 1 week window
       window_data = predictions.iloc[window_start:i+1]

       mae = abs(window_data['prediction'] - window_data['actual']).mean()
       rmse = ((window_data['prediction'] - window_data['actual']) ** 2).mean() ** 0.5

       mae_values.append(mae)
       rmse_values.append(rmse)

   # Create windowed metric visualization
   plotter = WindowedMetricPlotter()
   plotter.set_window_size("7D")
   plotter.add_model("XGBoost", timestamps, mae_values)

   mae_plot = plotter.plot(
       title="Mean Absolute Error Over Time",
       metric_name="MAE (MW)"
   )

   # Generate performance summary report
   perf_meter.checkpoint("metrics_calculated")

   summary_report = {
       'overall_mae': sum(mae_values) / len(mae_values),
       'overall_rmse': sum(rmse_values) / len(rmse_values),
       'best_performance_period': timestamps[mae_values.index(min(mae_values))],
       'worst_performance_period': timestamps[mae_values.index(max(mae_values))],
       'total_predictions': len(predictions),
       'data_coverage': len(predictions) / len(historical_data) * 100
   }

   perf_meter.complete_level(successful=True, **summary_report)

   print(f"Backtest Analysis Complete:")
   print(f"Overall MAE: {summary_report['overall_mae']:.2f} MW")
   print(f"Overall RMSE: {summary_report['overall_rmse']:.2f} MW")
   print(f"Data Coverage: {summary_report['data_coverage']:.1f}%")
   ```


- Model accuracy trends over time using windowed metric analysis to identify performance degradation or improvement patterns

- Training frequency effectiveness by comparing prediction quality between different retraining intervals

- Seasonal performance variations to understand when your model performs best and worst throughout the year

- Prediction horizon accuracy to determine optimal forecast lead times for your specific use case

- Event batch processing efficiency to identify bottlenecks in your forecasting pipeline

- Ground truth data quality issues revealed through systematic prediction errors or anomalies

- Model generalization capability by analyzing performance across different time periods and conditions

- Resource utilization patterns during training and prediction phases to optimize computational costs


Advanced Customization Tutorial
-------------------------------


OpenSTEF provides extensive customization capabilities for advanced users who need to adapt the library to specific forecasting scenarios or integrate with custom data pipelines. The library's modular architecture allows you to create custom target providers for loading data from specialized sources, implement custom visualization providers for domain-specific analysis requirements, and develop custom workflow orchestrations that incorporate your organization's unique forecasting processes. These customization points enable you to extend OpenSTEF beyond its standard functionality while maintaining compatibility with the core benchmarking and analysis framework, making it suitable for research environments, specialized energy markets, or organizations with unique data formats and business requirements.


.. warning::

   Advanced customization of OpenSTEF components requires a solid understanding of time series forecasting concepts, machine learning workflows, and the library's internal architecture. Before implementing custom target providers, visualization components, or forecasting workflows, ensure you are familiar with concepts such as feature engineering, model validation, evaluation metrics, and the specific domain requirements of short-term energy forecasting. Improper customization can lead to biased models, incorrect evaluations, or unreliable forecasts.


Custom Target Providers
^^^^^^^^^^^^^^^^^^^^^^^


Target providers in OpenSTEF serve as data source abstractions that define how the library accesses training data, ground truth measurements, and predictor features for benchmarking and model evaluation. The TargetProvider interface standardizes data loading operations, allowing you to specify where your time series data is stored and how it should be retrieved. While OpenSTEF includes built-in providers like SimpleTargetProvider for file-based datasets and specialized providers like Liander2024TargetProvider for specific benchmarks, you may need to create custom target providers when working with unique data sources such as proprietary databases, cloud storage systems, or APIs that don't match the standard file-based patterns. Custom target providers are particularly useful when you need to implement specific data filtering logic, handle non-standard data formats, or integrate with existing data infrastructure that requires custom authentication or connection protocols.


.. code-block:: python

   ```python
   from pathlib import Path
   import pandas as pd
   from openstef_beam.benchmarking.target_provider import TargetProvider
   from openstef_beam.benchmarking.benchmark_target import BenchmarkTarget
   from openstef_beam.benchmarking.versioned_time_series_dataset import VersionedTimeSeriesDataset
   from openstef_beam.benchmarking.metric_provider import MetricProvider

   class CustomTargetProvider(TargetProvider[BenchmarkTarget, dict]):
       """Custom target provider that loads data from a specific database or API."""

       def __init__(self, data_source_config: dict):
           self.data_source_config = data_source_config
           self.connection_string = data_source_config.get('connection_string')

       def get_targets(self, filter_args: dict | None = None) -> list[BenchmarkTarget]:
           """Load available targets from your custom data source."""
           # Example: Query your database or API to get available targets
           targets = []

           # Filter targets based on criteria if provided
           if filter_args:
               region = filter_args.get('region')
               target_type = filter_args.get('type')
               # Apply filtering logic here

           # Create BenchmarkTarget objects for each available target
           for target_id in ['solar_farm_001', 'wind_farm_002', 'load_point_003']:
               target = BenchmarkTarget(
                   id=target_id,
                   name=f"Custom {target_id}",
                   description=f"Custom target from external source: {target_id}"
               )
               targets.append(target)

           return targets

       def get_measurements_for_target(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           """Load ground truth measurements for the target."""
           # Example: Query your data source for historical measurements
           # This could be from a database, API, or file system

           # Create sample data (replace with actual data loading logic)
           date_range = pd.date_range('2023-01-01', '2023-12-31', freq='15T')
           measurements_df = pd.DataFrame({
               'datetime': date_range,
               'load': [100 + i * 0.1 for i in range(len(date_range))]
           }).set_index('datetime')

           return VersionedTimeSeriesDataset(
               data=measurements_df,
               version='v1.0',
               metadata={'source': 'custom_database', 'target_id': target.id}
           )

       def get_predictors_for_target(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           """Load predictor features for the target."""
           # Example: Load weather data, calendar features, etc.
           date_range = pd.date_range('2023-01-01', '2023-12-31', freq='15T')
           predictors_df = pd.DataFrame({
               'datetime': date_range,
               'temperature': [15 + 10 * (i % 24) / 24 for i in range(len(date_range))],
               'humidity': [60 + 20 * (i % 48) / 48 for i in range(len(date_range))],
               'is_weekend': [(date_range[i].weekday() >= 5) for i in range(len(date_range))]
           }).set_index('datetime')

           return VersionedTimeSeriesDataset(
               data=predictors_df,
               version='v1.0',
               metadata={'source': 'weather_api', 'target_id': target.id}
           )

       def get_metrics_for_target(self, target: BenchmarkTarget) -> list[MetricProvider]:
           """Return metrics to use for evaluating this target."""
           from openstef_beam.benchmarking.metrics import MAEMetricProvider, RMSEMetricProvider

           return [
               MAEMetricProvider(),
               RMSEMetricProvider()
           ]

       def get_evaluation_mask_for_target(self, target: BenchmarkTarget) -> pd.DatetimeIndex | None:
           """Optional: Define specific time periods for evaluation."""
           # Example: Only evaluate on weekdays during business hours
           full_range = pd.date_range('2023-01-01', '2023-12-31', freq='15T')
           business_hours = full_range[
               (full_range.hour >= 8) &
               (full_range.hour <= 18) &
               (full_range.weekday < 5)
           ]
           return business_hours

   # Usage example
   config = {
       'connection_string': 'postgresql://user:pass@localhost/energy_db',
       'api_key': 'your_api_key_here'
   }

   custom_provider = CustomTargetProvider(config)
   targets = custom_provider.get_targets({'region': 'north', 'type': 'solar'})
   ```


.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking.target_provider import TargetProvider, TargetProviderConfig
   from openstef_beam.benchmarking.benchmarks import BenchmarkTarget
   from openstef_beam.benchmarking.metrics import MetricProvider
   from openstef_beam.benchmarking.datasets import VersionedTimeSeriesDataset
   import pandas as pd
   import yaml

   class CustomTargetProvider(TargetProvider[BenchmarkTarget, dict]):
       """Custom target provider for loading data from your own sources."""

       def __init__(self, config_path: Path, data_path: Path):
           self.config_path = config_path
           self.data_path = data_path

       def get_targets(self, filter_args: dict = None) -> list[BenchmarkTarget]:
           """Load targets from custom configuration."""
           with open(self.config_path, 'r') as f:
               config = yaml.safe_load(f)

           targets = []
           for target_config in config['targets']:
               if filter_args is None or self._matches_filter(target_config, filter_args):
                   target = BenchmarkTarget(
                       id=target_config['id'],
                       name=target_config['name'],
                       description=target_config.get('description', ''),
                       metadata=target_config.get('metadata', {})
                   )
                   targets.append(target)
           return targets

       def get_measurements_for_target(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           """Load ground truth measurements from custom data source."""
           measurements_file = self.data_path / f"{target.id}_measurements.parquet"
           df = pd.read_parquet(measurements_file)
           return VersionedTimeSeriesDataset(df, version="1.0")

       def get_predictors_for_target(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           """Load predictor features from custom data source."""
           predictors_file = self.data_path / f"{target.id}_predictors.parquet"
           df = pd.read_parquet(predictors_file)
           return VersionedTimeSeriesDataset(df, version="1.0")

       def get_metrics_for_target(self, target: BenchmarkTarget) -> list[MetricProvider]:
           """Return metrics for evaluation."""
           from openstef_beam.benchmarking.metrics import MAEMetricProvider, RMSEMetricProvider
           return [MAEMetricProvider(), RMSEMetricProvider()]

       def _matches_filter(self, target_config: dict, filter_args: dict) -> bool:
           """Check if target matches filter criteria."""
           for key, value in filter_args.items():
               if target_config.get(key) != value:
                   return False
           return True

   # Integrate custom provider into benchmark workflow
   from openstef_beam.benchmarking.pipeline import BenchmarkPipeline
   from openstef_beam.benchmarking.storage import LocalBenchmarkStorage

   # Initialize custom target provider
   custom_provider = CustomTargetProvider(
       config_path=Path("config/custom_targets.yaml"),
       data_path=Path("data/custom_datasets")
   )

   # Create benchmark pipeline with custom provider
   pipeline = BenchmarkPipeline(
       target_provider=custom_provider,
       storage=LocalBenchmarkStorage(Path("results")),
       forecaster_factory=lambda: YourCustomForecaster()
   )

   # Run benchmark with filtered targets
   results = pipeline.run(
       target_filter={'category': 'industrial', 'region': 'north'}
   )


Custom Workflows
^^^^^^^^^^^^^^^^


OpenSTEF provides a flexible workflow system that allows you to customize forecasting and component splitting operations for your specific requirements. The library offers two main workflow types: CustomForecastingWorkflow for energy demand predictions and CustomComponentSplitWorkflow for decomposing energy consumption into individual components. Each workflow follows a standardized interface with fit() and predict() methods, enabling consistent training and inference patterns across different use cases. The workflow system includes built-in callback mechanisms through ForecastingCallback and ComponentSplitCallback interfaces, allowing you to monitor lifecycle events, implement custom logging, or add validation steps. For common scenarios, OpenSTEF provides preset configurations like EnsembleForecastingWorkflowConfig that can be easily customized through the create_ensemble_forecasting_workflow() function. Additionally, the library supports pipeline customization through components like AnalysisPipeline for generating visualizations from evaluation reports, giving you complete control over the analysis and reporting workflow.


.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow, ForecastingCallback
   from openstef_models.datasets import TimeSeriesDataset, ForecastDataset
   from openstef_models.predictors import XGBQuantileOpenstfRegressor
   from openstef_models.feature_engineering import ApplyLags, HolidayFeatures
   from openstef_models.postprocessing import LimitForecast
   from datetime import datetime
   import pandas as pd

   # Create a custom callback for specialized monitoring
   class SpecializedForecastingCallback(ForecastingCallback):
       def on_fit_start(self, workflow, data):
           print(f"Starting training for specialized forecasting at {datetime.now()}")

       def on_fit_end(self, workflow, data, result):
           if result and hasattr(result, 'metrics'):
               print(f"Training completed. R² score: {result.metrics.get('r2', 'N/A')}")

       def on_predict_start(self, workflow, data):
           print(f"Generating specialized forecasts for {len(data)} data points")

   # Configure a custom workflow for renewable energy forecasting
   workflow = CustomForecastingWorkflow(
       predictor=XGBQuantileOpenstfRegressor(
           quantiles=[0.1, 0.5, 0.9],  # Predict uncertainty bands
           n_estimators=200,
           max_depth=8,
           learning_rate=0.05
       ),
       feature_pipeline=[
           ApplyLags(lags=[1, 2, 24, 48, 168]),  # Hour, day, week lags
           HolidayFeatures(country='NL')  # Dutch holidays for local patterns
       ],
       postprocessors=[
           LimitForecast(min_value=0.0, max_value=1000.0)  # Physical constraints
       ],
       callbacks=[SpecializedForecastingCallback()]
   )

   # Set a descriptive run name for tracking
   workflow = workflow.with_run_name("renewable_energy_forecast_v2")

   # Prepare training data with renewable energy features
   train_data = TimeSeriesDataset(
       data=pd.DataFrame({
           'datetime': pd.date_range('2023-01-01', periods=8760, freq='H'),
           'load': renewable_energy_data,  # Your renewable energy time series
           'wind_speed': wind_data,
           'solar_irradiance': solar_data,
           'temperature': temperature_data
       }),
       target_column='load',
       datetime_column='datetime'
   )

   # Train the specialized workflow
   fit_result = workflow.fit(train_data)

   # Generate forecasts with uncertainty quantification
   forecast_data = TimeSeriesDataset(
       data=pd.DataFrame({
           'datetime': pd.date_range('2024-01-01', periods=168, freq='H'),
           'wind_speed': future_wind_data,
           'solar_irradiance': future_solar_data,
           'temperature': future_temperature_data
       }),
       datetime_column='datetime'
   )

   forecasts = workflow.predict(
       forecast_data,
       forecast_start=datetime(2024, 1, 1)
   )

   # Access quantile forecasts for uncertainty analysis
   forecast_df = forecasts.data
   print(f"Generated forecasts with columns: {list(forecast_df.columns)}")
   print(f"Forecast range: {forecast_df['forecast'].min():.2f} - {forecast_df['forecast'].max():.2f} MW")


.. [DIAGRAM: Custom workflow architecture showing modified components]


Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^


OpenSTEF provides a flexible feature engineering system that allows you to enhance your forecasting models with domain-specific features. The library includes built-in features such as lagged load values (1 day and 7 days ago), holiday and weekday indicators, extrapolated wind speed at 100m height, and normalized wind power based on turbine-specific power curves. For customization, OpenSTEF offers the FeatureAdder abstract class that enables you to create custom feature implementations. You can extend this class to add specialized features relevant to your energy forecasting domain, such as temperature-based cooling/heating degree days, seasonal adjustments, or market-specific indicators. The feature engineering pipeline automatically applies requested features through the apply_features function, and you can control which features are included by specifying feature names in your prediction job configuration.


.. code-block:: python

   ```python
   from openstef.feature_engineering.feature_adder import FeatureAdder
   import pandas as pd
   import numpy as np

   class CustomWeatherFeatureAdder(FeatureAdder):
       """Custom feature adder for weather-based features."""

       @property
       def name(self) -> str:
           return "custom_weather"

       def parse_feature_name(self, feature_name: str):
           """Parse feature names like 'custom_weather_temp_smooth'."""
           if feature_name.startswith("custom_weather_"):
               params = feature_name.replace("custom_weather_", "").split("_")
               return {"weather_type": params[0] if params else "temp"}
           return None

       def apply_features(self, df: pd.DataFrame, parsed_feature_names: dict) -> pd.DataFrame:
           """Add custom weather-based features."""
           df_copy = df.copy()

           for feature_name, params in parsed_feature_names.items():
               weather_type = params.get("weather_type", "temp")

               if weather_type == "temp" and "T_2m" in df.columns:
                   # Add temperature smoothing feature
                   df_copy[f"temp_smooth_3h"] = df["T_2m"].rolling(window=3).mean()
                   df_copy[f"temp_variation"] = df["T_2m"].diff().abs()

               elif weather_type == "wind" and "WS_10m" in df.columns:
                   # Add wind power estimation
                   df_copy[f"wind_power_est"] = np.where(
                       df["WS_10m"] < 3, 0,
                       np.where(df["WS_10m"] > 25, 0,
                                np.power(df["WS_10m"], 3) / 1000)
                   )

           return df_copy

   class CustomLoadFeatureAdder(FeatureAdder):
       """Custom feature adder for load-based features."""

       @property
       def name(self) -> str:
           return "custom_load"

       def parse_feature_name(self, feature_name: str):
           """Parse feature names like 'custom_load_trend_7d'."""
           if feature_name.startswith("custom_load_"):
               parts = feature_name.replace("custom_load_", "").split("_")
               return {"feature_type": parts[0], "period": parts[1] if len(parts) > 1 else "1d"}
           return None

       def apply_features(self, df: pd.DataFrame, parsed_feature_names: dict) -> pd.DataFrame:
           """Add custom load-based features."""
           df_copy = df.copy()

           for feature_name, params in parsed_feature_names.items():
               feature_type = params.get("feature_type", "trend")
               period = params.get("period", "1d")

               if "load" in df.columns:
                   if feature_type == "trend":
                       # Add load trend features
                       if period == "7d":
                           df_copy["load_trend_7d"] = df["load"].rolling(window=168).mean()  # 7 days * 24 hours
                       elif period == "1d":
                           df_copy["load_trend_1d"] = df["load"].rolling(window=24).mean()

                   elif feature_type == "ratio":
                       # Add load ratio features
                       df_copy["load_ratio_current_avg"] = df["load"] / df["load"].rolling(window=168).mean()

           return df_copy

   # Example usage with apply_features function
   from openstef.feature_engineering.apply_features import apply_features

   # Sample data preparation
   data = pd.DataFrame({
       'load': np.random.normal(100, 20, 1000),
       'T_2m': np.random.normal(15, 5, 1000),
       'WS_10m': np.random.normal(8, 3, 1000)
   }, index=pd.date_range('2023-01-01', periods=1000, freq='H'))

   # Define custom features to apply
   custom_features = [
       'custom_weather_temp_smooth',
       'custom_weather_wind_power',
       'custom_load_trend_7d',
       'custom_load_ratio_current'
   ]

   # Apply features including custom ones
   enhanced_data = apply_features(
       data=data,
       feature_names=custom_features,
       horizon=24.0
   )

   print(f"Original features: {list(data.columns)}")
   print(f"Enhanced features: {list(enhanced_data.columns)}")
   ```


.. code-block:: python

   ```python
   from openstef.feature_engineering.feature_adder import FeatureAdder
   from openstef.feature_engineering.apply_features import apply_features
   import pandas as pd

   # Create a custom feature adder for domain-specific features
   class CustomEnergyFeatureAdder(FeatureAdder):
       @property
       def name(self):
           return "custom_energy"

       def apply_features(self, df, parsed_feature_names):
           """Add custom energy domain features"""
           df_with_features = df.copy()

           # Add peak hour indicator (7-9 AM, 5-8 PM)
           df_with_features['is_peak_hour'] = (
               ((df_with_features.index.hour >= 7) & (df_with_features.index.hour <= 9)) |
               ((df_with_features.index.hour >= 17) & (df_with_features.index.hour <= 20))
           ).astype(int)

           # Add temperature-load interaction
           if 'temperature' in df_with_features.columns:
               df_with_features['temp_load_interaction'] = (
                   df_with_features['temperature'] * df_with_features.get('load', 0)
               )

           # Add rolling energy demand features
           if 'load' in df_with_features.columns:
               df_with_features['load_rolling_3h'] = df_with_features['load'].rolling(
                   window=3, min_periods=1
               ).mean()
               df_with_features['load_volatility_6h'] = df_with_features['load'].rolling(
                   window=6, min_periods=1
               ).std()

           return df_with_features

   # Integrate custom features into training pipeline
   def prepare_training_data_with_custom_features(data, pj, custom_feature_names=None):
       """Prepare training data with both standard and custom features"""

       # First apply standard OpenSTEF features
       standard_features = ['T-1d', 'T-7d', 'IsWeekDay', 'windspeed_100m']
       data_with_standard = apply_features(
           data=data,
           pj=pj,
           feature_names=standard_features,
           horizon=24.0
       )

       # Apply custom domain-specific features
       custom_adder = CustomEnergyFeatureAdder()
       data_with_custom = custom_adder.apply_features(
           df=data_with_standard,
           parsed_feature_names=custom_feature_names or []
       )

       return data_with_custom

   # Example usage in training pipeline
   training_data = pd.DataFrame({
       'load': [100, 120, 110, 95, 130],
       'temperature': [20, 22, 18, 25, 19],
       'windspeed': [5, 8, 3, 12, 6]
   }, index=pd.date_range('2023-01-01', periods=5, freq='H'))

   # Apply features for training
   enhanced_data = prepare_training_data_with_custom_features(
       data=training_data,
       pj=prediction_job,
       custom_feature_names=['peak_hours', 'temp_interaction']
   )
   ```


.. note::

   When implementing custom feature engineering in OpenSTEF, follow these key practices: Always validate that your custom FeatureAdder properly implements the abstract methods (apply_features, name, parse_feature_name) and handles edge cases gracefully. Test features with different data scenarios including missing values and varying time horizons. Use the feature_names parameter in apply_features() to control which features are added, as weather features are added by default and may need filtering. Implement proper error handling in your parse_feature_name() method to return None for unrecognized features and empty dictionaries for recognized features without parameters. Consider the forecast horizon when designing features - some features requiring recent label data will be automatically omitted for longer horizons. Always validate your custom features against known good data before deploying to production forecasting workflows.


Next Steps
----------


Congratulations! You've now learned the fundamentals of using OpenSTEF as a machine learning library for energy forecasting. Through these tutorials, you've explored data preparation, model training, prediction generation, and evaluation techniques. You've also seen how OpenSTEF's automated pipelines can streamline your forecasting workflow while providing probabilistic forecasts and confidence estimates.

As your next steps, consider exploring the OpenSTEF-reference repository for a complete deployment example, or dive into the OpenSTEF-offline-example Jupyter notebooks for more advanced use cases. If you're ready for production deployment, review the application architecture guidance to understand how to integrate OpenSTEF with data fetchers, APIs, and scheduling systems. For organizations looking to implement OpenSTEF at scale, the modular design allows you to adapt the library to your specific IT landscape while leveraging features like resilient fallback strategies and cloud-based deployment options.


- Explore the OpenSTEF-reference repository for a complete deployment example with databases and UI components

- Check out OpenSTEF-offline-example for Jupyter notebooks demonstrating practical use cases and workflows

- Review the OpenSTEF-dbc repository if you need custom database connectors for your specific environment

- Learn about containerized deployment options for cloud-based and platform-agnostic installations

- Study the application architecture guide to understand how to integrate OpenSTEF as a library with data fetchers, APIs, and schedulers

- Implement probabilistic forecasting capabilities for risk-based decision making in production environments

- Configure fallback strategies and resilience features for critical energy sector applications

- Set up split forecasting for renewable energy components (wind and solar) to meet regulatory requirements


OpenSTEF thrives as an open-source project through active community participation. Whether you're interested in contributing code improvements, reporting issues, or sharing your deployment experiences, your involvement helps make the library more robust for everyone. The project welcomes contributions of all sizes - from documentation improvements and bug fixes to new features and algorithmic enhancements. You can find the source code, contribute to discussions, and explore good first issues on the OpenSTEF GitHub organization. By engaging with the community, you not only help advance the state of energy forecasting but also gain insights from other practitioners working with similar challenges in the energy sector.


