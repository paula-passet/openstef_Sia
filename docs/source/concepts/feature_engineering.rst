Feature Engineering for Energy Forecasting
===========================================

Feature engineering is critical to energy forecasting performance. OpenSTEF embeds domain knowledge directly into features through built-in transforms that capture weather patterns, temporal cycles, load behavior, and energy-specific relationships. Good features enable classical machine learning models to achieve high accuracy without requiring deep learning architectures.

This page explains what makes effective features for energy forecasting and how to use OpenSTEF's feature engineering capabilities.

Why Features Matter for Energy Forecasting
-------------------------------------------

Energy consumption and generation follow predictable patterns driven by weather, time, and human behavior. Feature engineering translates raw measurements into representations that machine learning models can exploit:

- **Weather features** capture the relationship between temperature, solar radiation, wind speed, and energy demand or generation
- **Time features** encode daily, weekly, and seasonal cycles in human activity
- **Load patterns** reveal autocorrelation and recent trends
- **Derived features** combine raw measurements using domain knowledge (e.g., apparent temperature, solar angle)

OpenSTEF's philosophy is that classical ML models (XGBoost, LightGBM, linear regression) combined with smart features often outperform complex deep learning approaches for short-term energy forecasting.

Built-in Feature Transforms
----------------------------

OpenSTEF provides feature transforms organized by domain. These are applied automatically in forecasting workflows, but you can also use them directly for custom pipelines.

Weather Domain Features
^^^^^^^^^^^^^^^^^^^^^^^^

Weather is the primary driver of energy demand and renewable generation. OpenSTEF includes several weather-specific transforms:

**AtmosphereDerivedFeaturesAdder** calculates derived meteorological features from basic weather measurements:

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta
   import pandas as pd

   # Create dataset with basic weather data
   data = pd.DataFrame({
       'load': [100.0, 105.0, 110.0],
       'temperature': [20.0, 22.0, 25.0],
       'pressure': [1013.0, 1012.0, 1011.0],
       'relative_humidity': [60.0, 55.0, 50.0],
   }, index=pd.date_range('2025-01-01', periods=3, freq='h', tz='UTC'))
   
   dataset = TimeSeriesDataset(data, timedelta(hours=1))
   
   # Add derived atmospheric features
   transform = AtmosphereDerivedFeaturesAdder(
       pressure_column='pressure',
       relative_humidity_column='relative_humidity',
       temperature_column='temperature'
   )
   
   transformed = transform.fit_transform(dataset)
   print(transform.features_added())  # Shows which features were added

**RadiationDerivedFeaturesAdder** calculates solar-related features critical for PV forecasting:

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
   from openstef_core.types import Coordinate

   transform = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(latitude=52.1326, longitude=5.2913),  # Utrecht, NL
       radiation_column='radiation'
   )
   
   transformed = transform.fit_transform(dataset)

**WindPowerFeatureAdder** adds wind power-related features for wind generation forecasting:

.. code-block:: python

   from openstef_models.transforms.weather_domain import WindPowerFeatureAdder

   transform = WindPowerFeatureAdder(windspeed_reference_column='windspeed')
   transformed = transform.fit_transform(dataset)

**DaylightFeatureAdder** adds daylight indicators based on location:

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder

   transform = DaylightFeatureAdder(
       coordinate=Coordinate(latitude=52.1326, longitude=5.2913)
   )
   transformed = transform.fit_transform(dataset)

Time Domain Features
^^^^^^^^^^^^^^^^^^^^^

Temporal patterns are fundamental to energy forecasting. OpenSTEF provides several time-based transforms:

**CyclicFeaturesAdder** encodes time as cyclic features (sine/cosine) to capture daily and weekly patterns:

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder

   transform = CyclicFeaturesAdder()
   transformed = transform.fit_transform(dataset)
   # Adds features like hour_sin, hour_cos, day_of_week_sin, day_of_week_cos

**DatetimeFeaturesAdder** extracts discrete time features:

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

   # One-hot encoding for tree-based models
   transform = DatetimeFeaturesAdder(onehot_encode=False)
   transformed = transform.fit_transform(dataset)
   # Adds features like hour, day_of_week, month

**HolidayFeatureAdder** adds holiday indicators:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder

   transform = HolidayFeatureAdder(country_code='NL')
   transformed = transform.fit_transform(dataset)
   # Adds binary indicators for holidays in the Netherlands

Load Pattern Features
^^^^^^^^^^^^^^^^^^^^^^

Historical load patterns contain valuable information about recent trends and autocorrelation:

**RollingAggregatesAdder** creates lagged and rolling statistics:

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from openstef_core.enums import AggregationFunction
   from openstef_core.types import LeadTime

   transform = RollingAggregatesAdder(
       feature='load',
       aggregation_functions=[
           AggregationFunction.MEAN,
           AggregationFunction.MAX,
           AggregationFunction.MIN
       ],
       horizons=[LeadTime.from_string('PT24H'), LeadTime.from_string('PT48H')]
   )
   transformed = transform.fit_transform(dataset)
   # Adds rolling mean, max, min over 24h and 48h windows

What Makes Good Features
-------------------------

Effective features for energy forecasting share several characteristics:

**Predictive power**: Features should correlate with the target variable. Temperature strongly predicts heating/cooling demand. Solar radiation predicts PV generation.

**Availability at forecast time**: Features must be available when making predictions. Historical load is available. Future load is not. Weather forecasts are available but contain uncertainty.

**Stability**: Features should have consistent relationships with the target over time. Sudden changes in data collection or sensor calibration can break models.

**Low redundancy**: Highly correlated features add little value and can slow training. OpenSTEF includes ``EmptyFeatureRemover`` to drop features with no variance.

**Domain relevance**: Energy-specific transformations often outperform generic features. Apparent temperature (combining temperature, humidity, wind) better predicts heating demand than temperature alone.

Custom Feature Engineering
---------------------------

While OpenSTEF's built-in transforms cover common use cases, you may need custom features for specific forecasting problems. You can add custom features in two ways:

**Pre-process your data** before passing it to OpenSTEF:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta

   # Load raw data
   df = pd.read_csv('energy_data.csv', index_col='timestamp', parse_dates=True)
   
   # Add custom feature: temperature deviation from seasonal average
   df['temp_deviation'] = df['temperature'] - df.groupby(df.index.month)['temperature'].transform('mean')
   
   # Create dataset with custom feature
   dataset = TimeSeriesDataset(df, timedelta(hours=1))

**Create a custom transform** following OpenSTEF's transform interface:

.. code-block:: python

   from openstef_models.transforms.base import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig

   class CustomFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add custom domain-specific features."""
       
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           
           # Example: interaction between temperature and hour
           df['temp_hour_interaction'] = df['temperature'] * df.index.hour
           
           return TimeSeriesDataset(df, data.resolution)
       
       def features_added(self) -> list[str]:
           return ['temp_hour_interaction']

Custom transforms integrate seamlessly with OpenSTEF's preprocessing pipelines.

Feature Selection and Importance
---------------------------------

Not all features improve model performance. OpenSTEF handles feature selection through several mechanisms:

**Automatic removal**: ``EmptyFeatureRemover`` drops features with zero variance.

**Model-based selection**: Tree-based models (XGBoost, LightGBM) naturally perform feature selection by ignoring uninformative features.

**Configuration-based selection**: Use ``FeatureSelection`` in workflow configs to include or exclude specific features:

.. code-block:: python

   from openstef_core.workflow_config import FeatureSelection

   # Clip specific features to remove outliers
   clip_features = FeatureSelection(
       include=['temperature', 'radiation'],
       exclude=None
   )

Feature Preprocessing
---------------------

Raw features often require preprocessing before modeling:

**Clipping** removes outliers that can distort models:

.. code-block:: python

   from openstef_models.transforms.preprocessing import Clipper
   from openstef_core.workflow_config import Include

   clipper = Clipper(
       selection=Include('temperature', 'radiation'),
       mode='standard'  # Clip to mean ± 3 standard deviations
   )

**Scaling** normalizes feature ranges for linear models:

.. code-block:: python

   from openstef_models.transforms.preprocessing import Scaler
   from openstef_core.workflow_config import Exclude

   scaler = Scaler(
       selection=Exclude('load'),  # Don't scale the target
       method='standard'  # Z-score normalization
   )

**Imputation** handles missing values:

.. code-block:: python

   from openstef_models.transforms.preprocessing import Imputer

   imputer = Imputer(
       selection=Exclude('load'),
       imputation_strategy='mean'
   )

OpenSTEF workflows apply these preprocessing steps automatically based on the chosen model type.

Integration with Workflows
---------------------------

Feature engineering happens automatically in OpenSTEF's forecasting workflows. The workflow configuration determines which transforms are applied:

.. code-block:: python

   from openstef_core.workflow_config import ForecastingWorkflowConfig
   from openstef_core.enums import AggregationFunction

   config = ForecastingWorkflowConfig(
       model='xgboost',
       rolling_aggregate_features=[
           AggregationFunction.MEAN,
           AggregationFunction.MAX
       ],
       # Other configuration...
   )

The workflow automatically constructs a preprocessing pipeline with appropriate feature transforms for the selected model.

For details on model-specific feature requirements, see :doc:`model_selection`.

Next Steps
----------

- Learn about :doc:`forecasting_basics` to understand how features drive predictions
- Explore :doc:`model_selection` to see how different models use features
- Review the API documentation for specific transform classes