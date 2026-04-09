Advanced Customization
======================

This guide shows how to extend OpenSTEF for advanced use cases by customizing data preparation, feature engineering, and workflow orchestration. OpenSTEF is designed as a library with clear extension points that allow you to integrate custom logic while leveraging the built-in forecasting infrastructure.

Custom Feature Engineering
---------------------------

OpenSTEF uses transform pipelines for feature engineering. You can create custom transforms by implementing the ``TimeSeriesTransform`` interface.

Creating Custom Transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^

All transforms inherit from ``TimeSeriesTransform`` and implement two key methods: ``transform()`` for the actual transformation logic, and ``features_added()`` to declare which features are created.

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class BusinessHoursTransform(TimeSeriesTransform):
       """Add a feature indicating business hours (9 AM - 5 PM on weekdays)."""
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           
           # Create business hours indicator
           is_weekday = df.index.dayofweek < 5
           is_business_hour = (df.index.hour >= 9) & (df.index.hour < 17)
           df['is_business_hours'] = (is_weekday & is_business_hour).astype(int)
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return ['is_business_hours']

For stateful transforms that learn parameters from training data, override the ``fit()`` method and ``is_fitted`` property:

.. code-block:: python

   class RollingAverageTransform(TimeSeriesTransform):
       """Add rolling average features with learned window size."""
       
       def __init__(self, target_column: str = "load"):
           self.target_column = target_column
           self.window_size = None
       
       @property
       def is_fitted(self) -> bool:
           return self.window_size is not None
       
       def fit(self, data: TimeSeriesDataset) -> None:
           # Learn optimal window size from autocorrelation
           series = data.data[self.target_column]
           autocorr = [series.autocorr(lag=i) for i in range(1, 25)]
           self.window_size = autocorr.index(max(autocorr)) + 1
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           if not self.is_fitted:
               raise ValueError("Transform must be fitted before transform")
           
           df = data.data.copy()
           df[f'{self.target_column}_rolling_avg'] = (
               df[self.target_column].rolling(window=self.window_size).mean()
           )
           
           return TimeSeriesDataset(df, data.sample_interval)
       
       def features_added(self) -> list[str]:
           return [f'{self.target_column}_rolling_avg']

Using Transform Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^

Combine multiple transforms into a pipeline that executes them in sequence. The ``TransformPipeline`` handles fitting and transforming through all stages:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.general import Clipper
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   # Create a custom preprocessing pipeline
   preprocessing = TransformPipeline[TimeSeriesDataset]()
   preprocessing.add_transform(BusinessHoursTransform())
   preprocessing.add_transform(RollingAverageTransform(target_column="load"))
   preprocessing.add_transform(WindPowerFeatureAdder())
   preprocessing.add_transform(Clipper())
   
   # Fit on training data
   preprocessing.fit(data=train_data)
   
   # Transform both training and validation data
   train_transformed = preprocessing.transform(data=train_data)
   val_transformed = preprocessing.transform(data=val_data)

Integrating Custom Transforms with Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add your custom preprocessing pipeline to any forecasting model by setting its ``preprocessing`` field:

.. code-block:: python

   from openstef_models.models import XGBForecastingModel
   
   # Create model with custom preprocessing
   model = XGBForecastingModel(
       preprocessing=preprocessing,
       target_column="load"
   )
   
   # The pipeline is automatically applied during fit and predict
   model.fit(data=train_data, data_val=val_data)
   forecast = model.predict(data=test_data)

Custom Data Preparation
------------------------

For advanced data preparation needs beyond feature engineering, you can preprocess data before passing it to OpenSTEF models.

Handling Missing Data
^^^^^^^^^^^^^^^^^^^^^^

Implement custom imputation strategies for your specific domain:

.. code-block:: python

   def prepare_data_with_imputation(
       raw_data: pd.DataFrame,
       sample_interval: pd.Timedelta
   ) -> TimeSeriesDataset:
       """Prepare data with domain-specific missing data handling."""
       df = raw_data.copy()
       
       # Forward-fill short gaps (< 1 hour)
       df['load'] = df['load'].fillna(method='ffill', limit=4)
       
       # Use weekly seasonality for longer gaps
       df['load'] = df['load'].fillna(
           df.groupby([df.index.dayofweek, df.index.hour])['load']
           .transform('mean')
       )
       
       # Remove remaining outliers
       q1 = df['load'].quantile(0.01)
       q99 = df['load'].quantile(0.99)
       df['load'] = df['load'].clip(lower=q1, upper=q99)
       
       return TimeSeriesDataset(df, sample_interval)

Combining Multiple Data Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Merge different data sources before creating a dataset:

.. code-block:: python

   def prepare_multimodal_dataset(
       load_data: pd.DataFrame,
       weather_data: pd.DataFrame,
       calendar_data: pd.DataFrame,
       sample_interval: pd.Timedelta
   ) -> TimeSeriesDataset:
       """Combine load, weather, and calendar data."""
       # Align all data to common time index
       common_index = load_data.index.intersection(weather_data.index)
       
       df = load_data.loc[common_index].copy()
       df = df.join(weather_data.loc[common_index], how='left')
       df = df.join(calendar_data.loc[common_index], how='left')
       
       # Handle timezone conversions
       if df.index.tz is None:
           df.index = df.index.tz_localize('UTC')
       
       return TimeSeriesDataset(df, sample_interval)

Custom Workflow Orchestration
------------------------------

For production systems, OpenSTEF provides workflow classes that add lifecycle hooks and callbacks to the basic model interface.

Using Workflow Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks allow you to inject custom logic at key points in the training and prediction process:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow, ForecastingCallback
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   from openstef_models.models import XGBForecastingModel
   import logging
   
   logger = logging.getLogger(__name__)
   
   class MetricsCallback(ForecastingCallback):
       """Log metrics and data statistics during workflow execution."""
       
       def on_fit_start(self, workflow, data):
           logger.info(f"Training started with {len(data.data)} samples")
           logger.info(f"Date range: {data.data.index.min()} to {data.data.index.max()}")
       
       def on_fit_end(self, workflow, data, result):
           logger.info(f"Training completed")
           if result.metrics:
               logger.info(f"Validation metrics: {result.metrics}")
       
       def on_predict_start(self, workflow, data):
           logger.info(f"Prediction started for {len(data.data)} time points")
       
       def on_predict_end(self, workflow, data, forecast):
           logger.info(f"Generated {len(forecast.data)} forecasts")
           logger.info(f"Mean prediction: {forecast.data['forecast'].mean():.2f}")
   
   # Create workflow with callback
   model = XGBForecastingModel()
   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[MetricsCallback()]
   )
   
   # Callbacks are automatically invoked
   workflow.fit(data=train_data, data_val=val_data)
   forecast = workflow.predict(data=test_data)

Advanced Callback Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks can implement validation, early stopping, or integration with external systems:

.. code-block:: python

   class ValidationCallback(ForecastingCallback):
       """Validate data quality before training."""
       
       def on_fit_start(self, workflow, data):
           # Check for sufficient data
           if len(data.data) < 1000:
               raise ValueError(f"Insufficient training data: {len(data.data)} samples")
           
           # Check for missing values in target
           target = workflow.model.target_column
           missing_pct = data.data[target].isna().mean()
           if missing_pct > 0.1:
               raise ValueError(f"Too many missing values: {missing_pct:.1%}")
   
   class MonitoringCallback(ForecastingCallback):
       """Send metrics to monitoring system."""
       
       def __init__(self, monitoring_client):
           self.client = monitoring_client
       
       def on_fit_end(self, workflow, data, result):
           if result.metrics:
               self.client.send_metrics({
                   'model_name': workflow.model.__class__.__name__,
                   'train_samples': len(data.data),
                   **result.metrics
               })
       
       def on_predict_end(self, workflow, data, forecast):
           self.client.send_metrics({
               'prediction_count': len(forecast.data),
               'mean_forecast': forecast.data['forecast'].mean(),
               'timestamp': pd.Timestamp.now()
           })

Custom Postprocessing
^^^^^^^^^^^^^^^^^^^^^

Models also support postprocessing pipelines for transforming predictions:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_core.datasets import ForecastDataset
   from openstef_core.transforms.dataset_transforms import Transform
   
   class ForecastSmootherTransform(Transform[ForecastDataset, ForecastDataset]):
       """Smooth forecasts to reduce volatility."""
       
       def __init__(self, window: int = 3):
           self.window = window
       
       @property
       def is_fitted(self) -> bool:
           return True
       
       def fit(self, data: ForecastDataset) -> None:
           pass
       
       def transform(self, data: ForecastDataset) -> ForecastDataset:
           df = data.data.copy()
           df['forecast'] = df['forecast'].rolling(
               window=self.window, 
               center=True
           ).mean().fillna(df['forecast'])
           return ForecastDataset(df, data.sample_interval)
   
   # Add to model
   postprocessing = TransformPipeline[ForecastDataset]()
   postprocessing.add_transform(ForecastSmootherTransform(window=3))
   
   model = XGBForecastingModel(
       preprocessing=preprocessing,
       postprocessing=postprocessing
   )

Next Steps
----------

- See :doc:`first_forecast` for basic model usage patterns
- See :doc:`backtesting` for evaluating custom models
- Explore the API reference for built-in transforms in ``openstef_models.transforms``