Tutorials
=========

This page guides you through OpenSTEF from your first forecast to production-ready implementations. You'll learn how to use preset workflows for quick results, run backtests to evaluate model performance, and customize the library for your specific forecasting needs.

These tutorials assume you've completed the :doc:`quickstart` and are ready to explore OpenSTEF's capabilities in depth.

First Use with Presets
----------------------

The fastest way to create production-quality forecasts is using OpenSTEF's preset workflows. These combine proven feature engineering, model selection, and evaluation strategies into ready-to-use configurations.

Loading and Preparing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF expects time series data in a specific format. Start by loading your historical measurements and weather predictors:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your data (example with CSV)
   df = pd.read_csv("energy_data.csv", index_col="datetime", parse_dates=True)
   
   # Required columns:
   # - load: target variable (energy consumption/production in MW)
   # - temperature_2m: temperature in Celsius
   # - radiation: solar radiation in W/m²
   # - wind_speed: wind speed in m/s
   
   # Create a TimeSeriesDataset
   data = TimeSeriesDataset(
       data=df,
       target_column="load",
       datetime_column=df.index
   )

The ``TimeSeriesDataset`` validates your data structure and ensures temporal consistency. It handles missing values and resampling automatically based on the detected frequency.

Training a Model
^^^^^^^^^^^^^^^^

Use a preset workflow configuration to train your first model. The ``ForecastingWorkflowConfig`` bundles all necessary settings:

.. code-block:: python

   from openstef_meta.presets import ForecastingWorkflowConfig
   from openstef_models.presets import create_forecasting_workflow
   
   # Configure the workflow
   config = ForecastingWorkflowConfig(
       model="xgboost",  # or "lgbm", "gblinear"
       horizon_minutes=2880,  # 48-hour forecast horizon
       resolution_minutes=15,  # 15-minute resolution
       quantiles=[0.1, 0.5, 0.9],  # Forecast quantiles
       temperature_column="temperature_2m",
       radiation_column="radiation",
       wind_speed_column="wind_speed",
   )
   
   # Create and train the workflow
   workflow = create_forecasting_workflow(config)
   workflow.fit(data)

The workflow automatically generates features like lag values, time-based features (hour, day of week), and weather interactions. Training typically takes 1-5 minutes depending on data size.

Creating a Forecast
^^^^^^^^^^^^^^^^^^^

Once trained, generate forecasts for future time periods:

.. code-block:: python

   from datetime import datetime, timedelta
   
   # Load predictor data for the forecast period
   forecast_start = datetime(2024, 1, 15, 0, 0)
   forecast_end = forecast_start + timedelta(hours=48)
   
   # Your predictor data should cover the forecast period
   predictor_df = pd.read_csv("weather_forecast.csv", index_col="datetime", parse_dates=True)
   predictor_data = TimeSeriesDataset(
       data=predictor_df,
       target_column=None,  # No target for prediction data
       datetime_column=predictor_df.index
   )
   
   # Generate forecast
   forecast = workflow.predict(predictor_data)
   
   # Access quantile predictions
   print(forecast.data[["q_0.1", "q_0.5", "q_0.9"]])

The forecast includes multiple quantiles representing prediction uncertainty. The median (q_0.5) is the point forecast, while q_0.1 and q_0.9 provide confidence bounds.

Evaluating Results
^^^^^^^^^^^^^^^^^^

Evaluate model performance on held-out test data:

.. code-block:: python

   from openstef_beam.evaluation import ForecastEvaluator
   from openstef_core.types import LeadTime
   
   # Split data for evaluation
   train_end = datetime(2023, 12, 31)
   test_data = data.filter_by_time(start=train_end)
   
   # Create predictions for test period
   test_predictions = workflow.predict(test_data)
   
   # Evaluate forecast quality
   evaluator = ForecastEvaluator()
   metrics = evaluator.evaluate(
       predictions=test_predictions,
       actuals=test_data,
       lead_times=[LeadTime(minutes=15), LeadTime(hours=1), LeadTime(hours=24)]
   )
   
   # View metrics by lead time
   print(f"RMSE at 15min: {metrics.rmse[LeadTime(minutes=15)]:.2f} MW")
   print(f"RMSE at 1h: {metrics.rmse[LeadTime(hours=1)]:.2f} MW")
   print(f"RMSE at 24h: {metrics.rmse[LeadTime(hours=24)]:.2f} MW")

Forecast accuracy typically degrades with longer lead times. Short-term forecasts (0-6 hours) are most accurate, while day-ahead forecasts (24-48 hours) rely more heavily on weather predictions.

Energy Split Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For load forecasting, decompose total consumption into weather-dependent and baseload components:

.. code-block:: python

   from openstef_models.models import ComponentSplittingModel
   from openstef_models.models.component_splitting import LinearComponentSplitter
   
   # Create component splitter
   splitter = ComponentSplittingModel(
       splitter=LinearComponentSplitter()
   )
   
   # Fit on historical data
   splitter.fit(data)
   
   # Decompose forecast
   components = splitter.predict(forecast)
   
   # Access individual components
   weather_dependent = components.weather_dependent
   baseload = components.baseload
   
   print(f"Weather-dependent load: {weather_dependent.mean():.2f} MW")
   print(f"Baseload: {baseload.mean():.2f} MW")

This decomposition helps identify temperature sensitivity and understand load patterns. Weather-dependent components correlate with heating/cooling demand, while baseload represents constant consumption.

Backtesting with Multiple Models
---------------------------------

Backtesting evaluates model performance across historical periods, simulating production conditions. The Liander 2024 benchmark provides a standardized dataset for comparing approaches.

Setting Up a Backtest
^^^^^^^^^^^^^^^^^^^^^^

Run a backtest comparing two models on the Liander 2024 dataset:

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking.benchmarks.liander2024 import (
       create_liander2024_benchmark_runner,
       Liander2024Category
   )
   from openstef_beam.benchmarking.baselines.openstef4 import (
       create_openstef4_preset_backtest_forecaster
   )
   from openstef_beam.benchmarking.storage import LocalBenchmarkStorage
   from openstef_meta.presets import ForecastingWorkflowConfig
   
   # Configure output location
   output_path = Path("./benchmark_results")
   
   # Configure first model (XGBoost)
   xgboost_config = ForecastingWorkflowConfig(
       model="xgboost",
       horizon_minutes=2880,
       resolution_minutes=15,
       quantiles=[0.1, 0.5, 0.9],
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
   )
   
   # Configure second model (GBLinear)
   gblinear_config = xgboost_config.model_copy(update={"model": "gblinear"})
   
   # Run XGBoost backtest
   xgboost_storage = LocalBenchmarkStorage(base_path=output_path / "xgboost")
   create_liander2024_benchmark_runner(storage=xgboost_storage).run(
       forecaster_factory=create_openstef4_preset_backtest_forecaster(
           workflow_config=xgboost_config,
           cache_dir=output_path / "cache"
       ),
       run_name="xgboost",
       n_processes=4
   )
   
   # Run GBLinear backtest
   gblinear_storage = LocalBenchmarkStorage(base_path=output_path / "gblinear")
   create_liander2024_benchmark_runner(storage=gblinear_storage).run(
       forecaster_factory=create_openstef4_preset_backtest_forecaster(
           workflow_config=gblinear_config,
           cache_dir=output_path / "cache"
       ),
       run_name="gblinear",
       n_processes=4
   )

The benchmark runner handles data loading, training windows, and evaluation automatically. Results are stored for comparison.

Comparing Results
^^^^^^^^^^^^^^^^^

Analyze and compare backtest results across models:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.analysis.models import RunName
   
   # Set up comparison
   comparison = BenchmarkComparisonPipeline(
       storage=LocalBenchmarkStorage(base_path=output_path),
       run_names=[RunName("xgboost"), RunName("gblinear")]
   )
   
   # Generate comparison report
   results = comparison.compare()
   
   # View aggregate metrics
   print(results.summary)
   
   # Export detailed comparison
   results.to_csv(output_path / "comparison.csv")

The comparison shows performance differences across forecast horizons, target categories, and time periods. Use this to select the best model for your use case.

Advanced Customization
----------------------

For specialized forecasting needs, customize OpenSTEF's components. This section shows how to implement custom data providers, workflows, and feature engineering.

Custom Target Provider
^^^^^^^^^^^^^^^^^^^^^^

Target providers load benchmark data from custom sources. Implement the ``TargetProvider`` interface:

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking import TargetProvider
   from openstef_beam.benchmarking.models import BenchmarkTarget
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_beam.evaluation import MetricProvider, RMAEProvider
   
   class CustomTargetProvider(TargetProvider[BenchmarkTarget, None]):
       """Load targets from a custom database or file structure."""
       
       def __init__(self, data_path: Path, region: str):
           super().__init__()
           self.data_path = data_path
           self.region = region
       
       def get_targets(self, filter_args=None):
           """Return list of forecast targets."""
           # Load from your data source
           targets = []
           for substation_id in self._load_substation_ids():
               targets.append(BenchmarkTarget(
                   name=f"substation_{substation_id}",
                   description=f"Load forecast for substation {substation_id}",
                   group_name=self.region,
                   latitude=self._get_latitude(substation_id),
                   longitude=self._get_longitude(substation_id),
               ))
           return targets
       
       def get_measurements(self, target: BenchmarkTarget) -> TimeSeriesDataset:
           """Load historical measurements for a target."""
           df = pd.read_parquet(
               self.data_path / f"{target.name}_measurements.parquet"
           )
           return TimeSeriesDataset(
               data=df,
               target_column="load",
               datetime_column=df.index
           )
       
       def get_predictors(self, target: BenchmarkTarget) -> TimeSeriesDataset:
           """Load predictor data (weather, etc.) for a target."""
           df = pd.read_parquet(
               self.data_path / f"{target.name}_predictors.parquet"
           )
           return TimeSeriesDataset(
               data=df,
               target_column=None,
               datetime_column=df.index
           )
       
       def get_metric_provider(self, target: BenchmarkTarget) -> MetricProvider:
           """Define evaluation metrics for this target."""
           return RMAEProvider()
       
       def _load_substation_ids(self):
           # Your implementation
           pass
       
       def _get_latitude(self, substation_id):
           # Your implementation
           pass
       
       def _get_longitude(self, substation_id):
           # Your implementation
           pass

Use your custom provider in benchmarks by passing it to the benchmark runner configuration.

Custom Workflow
^^^^^^^^^^^^^^^

Build a workflow with custom preprocessing and model selection:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.models import ForecastingModel
   from openstef_models.transforms import (
       AddLagFeatures,
       AddTimeFeatures,
       RemoveOutliers
   )
   from openstef_models.preprocessing import FeatureEngineeringPipeline
   
   # Define custom preprocessing steps
   preprocessing = FeatureEngineeringPipeline(
       transforms=[
           RemoveOutliers(threshold=3.5),  # Remove extreme outliers
           AddTimeFeatures(
               features=["hour", "day_of_week", "month", "is_weekend"]
           ),
           AddLagFeatures(
               lags=[1, 2, 4, 24, 48, 168],  # 15min, 30min, 1h, 6h, 12h, 1week
               columns=["load", "temperature_2m"]
           ),
       ]
   )
   
   # Create model with custom configuration
   model = ForecastingModel(
       model_type="xgboost",
       hyperparams={
           "n_estimators": 500,
           "max_depth": 8,
           "learning_rate": 0.05,
           "subsample": 0.8,
       },
       quantiles=[0.05, 0.25, 0.5, 0.75, 0.95]
   )
   
   # Build custom workflow
   workflow = CustomForecastingWorkflow(
       preprocessing=preprocessing,
       model=model,
       postprocessing=None  # Optional post-processing steps
   )
   
   # Train and predict as usual
   workflow.fit(data)
   forecast = workflow.predict(predictor_data)

This approach gives you full control over feature engineering and model configuration while maintaining OpenSTEF's workflow structure.

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implement domain-specific features by creating custom transforms:

.. code-block:: python

   from openstef_models.transforms.base import Transform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class AddHeatingDegreeDays(Transform):
       """Calculate heating degree days for temperature-sensitive loads."""
       
       def __init__(self, base_temperature: float = 18.0):
           self.base_temperature = base_temperature
       
       def fit(self, data: TimeSeriesDataset) -> "AddHeatingDegreeDays":
           """No fitting required for this transform."""
           return self
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Add heating degree day features."""
           df = data.data.copy()
           
           # Calculate heating degree days
           df["hdd"] = (self.base_temperature - df["temperature_2m"]).clip(lower=0)
           
           # Add rolling averages
           df["hdd_7d"] = df["hdd"].rolling(window=7*24*4, min_periods=1).mean()
           df["hdd_30d"] = df["hdd"].rolling(window=30*24*4, min_periods=1).mean()
           
           return TimeSeriesDataset(
               data=df,
               target_column=data.target_column,
               datetime_column=df.index
           )
   
   # Use in preprocessing pipeline
   preprocessing = FeatureEngineeringPipeline(
       transforms=[
           AddHeatingDegreeDays(base_temperature=18.0),
           AddTimeFeatures(),
           AddLagFeatures(lags=[1, 2, 4, 24]),
       ]
   )

Custom transforms integrate seamlessly with OpenSTEF's preprocessing infrastructure. They can be serialized, versioned, and reused across different workflows.

Next Steps
----------

You now have the skills to implement production forecasting systems with OpenSTEF. For specific deployment scenarios, see :doc:`../guides/how_to_guides`. To understand when to use different forecasting approaches, review :doc:`../guides/use_cases`.

For deeper understanding of forecasting concepts like quantile prediction and model selection, explore :doc:`../reference/concepts`.