Models Package
==============

The ``openstef_models`` package provides the forecasting engine for OpenSTEF: feature engineering transforms, model implementations, and explainability tools. This package builds on the ``openstef_core`` data structures to deliver production-ready probabilistic energy forecasting.

The package follows a compositional design with three main layers:

- **Transforms**: Domain-organized feature engineering pipelines
- **Models**: Gradient boosting forecasting implementations
- **Explainability**: Feature importance and contribution analysis

.. note::
   [DIAGRAM: Component diagram showing three layers - transforms (time_domain, weather_domain, energy_domain, general, validation) feeding into models (XGBoost, LightGBM variants) with explainability (ExplainableForecaster, ContributionsMixin, FeatureImportancePlotter) as a cross-cutting layer]

Architecture Overview
---------------------

The ``openstef_models`` package operates on ``TimeSeriesDataset`` objects from ``openstef_core``. Transforms enrich datasets with engineered features, models consume these datasets for training and prediction, and explainability tools help interpret model behavior.

All transforms implement the ``TimeSeriesTransform`` interface with ``fit()`` and ``transform()`` methods, enabling consistent pipeline composition. Models implement the ``Forecaster`` interface for training and probabilistic prediction across multiple quantiles.

Transforms Module
-----------------

The transforms module organizes feature engineering by domain expertise, making it easy to apply relevant transformations for different forecasting scenarios.

Domain Organization
^^^^^^^^^^^^^^^^^^^

Transforms are grouped into five subpackages:

**time_domain**: Temporal features extracted from datetime indices, including hour of day, day of week, month, and holiday indicators.

**weather_domain**: Meteorological feature engineering such as daylight calculations, atmospheric derived features (apparent temperature, heat index), and radiation-based features.

**energy_domain**: Energy-specific transforms like wind power calculations from wind speed data.

**general**: Cross-domain utilities including clipping, scaling, and data validation.

**validation**: Input data consistency checks and validation transforms.

Example Usage
^^^^^^^^^^^^^

Transforms can be composed into pipelines that progressively enrich a dataset:

.. code-block:: python

   from openstef_core import TimeSeriesDataset
   from openstef_models.transforms.time_domain import TemporalFeaturesAdder
   from openstef_models.transforms.weather_domain import DaylightFeatureAdder
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   # Start with raw data
   dataset = TimeSeriesDataset(...)
   
   # Add temporal features
   temporal_transform = TemporalFeaturesAdder()
   dataset = temporal_transform.fit(dataset).transform(dataset)
   
   # Add daylight features
   daylight_transform = DaylightFeatureAdder(latitude=52.0, longitude=5.0)
   dataset = daylight_transform.transform(dataset)
   
   # Add wind power features
   wind_transform = WindPowerFeatureAdder()
   dataset = wind_transform.transform(dataset)

Each transform adds specific features while preserving existing data. The ``features_added()`` method reports which features a transform contributes:

.. code-block:: python

   print(temporal_transform.features_added())
   # ['hour', 'dayofweek', 'month', 'is_holiday', ...]

Transform Interface
^^^^^^^^^^^^^^^^^^^

All transforms follow a consistent interface:

.. code-block:: python

   class TimeSeriesTransform:
       def fit(self, data: TimeSeriesDataset) -> Self:
           """Learn parameters from training data."""
           
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           """Apply transformation to data."""
           
       def features_added(self) -> list[str]:
           """Return list of feature names added by this transform."""
           
       @property
       def is_fitted(self) -> bool:
           """Check if transform has been fitted."""

Some transforms like ``Clipper`` require fitting to learn parameters (min/max values), while others like ``DaylightFeatureAdder`` are stateless and compute features directly.

Models Module
-------------

The models module provides gradient boosting implementations optimized for probabilistic energy forecasting. All models support multi-quantile prediction, enabling uncertainty quantification.

Available Forecasters
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes three primary forecasting implementations:

**XGBoostForecaster**: XGBoost-based gradient boosting trees with quantile regression. Robust and widely used for energy forecasting.

**LGBMForecaster**: LightGBM-based gradient boosting with faster training and lower memory usage than XGBoost.

**LGBMLinearForecaster**: Linear models using LightGBM's linear tree learner, suitable for scenarios requiring interpretability or when relationships are approximately linear.

All forecasters share a common interface for training and prediction:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core import ForecastInputDataset, TrainingDataset
   
   # Initialize forecaster
   forecaster = XGBoostForecaster(
       quantiles=[0.1, 0.5, 0.9],
       max_depth=6,
       learning_rate=0.1
   )
   
   # Train on historical data
   train_data = TrainingDataset(...)
   forecaster.fit(train_data)
   
   # Generate probabilistic forecasts
   forecast_input = ForecastInputDataset(...)
   predictions = forecaster.predict(forecast_input)
   
   # Access different quantiles
   median_forecast = predictions.quantile(0.5)
   lower_bound = predictions.quantile(0.1)
   upper_bound = predictions.quantile(0.9)

Quantile Forecasting
^^^^^^^^^^^^^^^^^^^^

OpenSTEF models produce probabilistic forecasts by predicting multiple quantiles simultaneously. This enables uncertainty quantification without assuming a specific distribution:

.. code-block:: python

   # Configure quantiles during initialization
   forecaster = LGBMForecaster(
       quantiles=[0.05, 0.25, 0.5, 0.75, 0.95]
   )
   
   # Predictions include all quantiles
   predictions = forecaster.predict(data)
   
   # Extract specific quantiles
   p50 = predictions.quantile(0.5)  # Median forecast
   p90_p10_range = predictions.quantile(0.9) - predictions.quantile(0.1)

The quantile regression objective ensures predictions are properly calibrated across the probability distribution.

Explainability Tools
--------------------

The explainability module provides tools for understanding model behavior through feature importance analysis and per-prediction contributions.

Feature Importance
^^^^^^^^^^^^^^^^^^

The ``ExplainableForecaster`` mixin adds feature importance capabilities to forecasting models:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   
   forecaster = XGBoostForecaster(quantiles=[0.5])
   forecaster.fit(train_data)
   
   # Get feature importance scores
   importance_df = forecaster.feature_importances
   print(importance_df.head())
   #                    importance
   # temperature           0.342
   # hour                  0.189
   # dayofweek             0.156
   # ...

Feature importance scores indicate which features contribute most to model predictions. The ``FeatureImportancePlotter`` creates interactive treemap visualizations:

.. code-block:: python

   from openstef_models.explainability import FeatureImportancePlotter
   
   # Create interactive visualization
   fig = forecaster.plot_feature_importances(quantile=0.5)
   fig.show()

Contribution Analysis
^^^^^^^^^^^^^^^^^^^^^

The ``ContributionsMixin`` enables per-prediction feature contribution analysis, showing how each feature influences individual forecasts:

.. code-block:: python

   # Get contributions for specific predictions
   contributions = forecaster.predict_contributions(forecast_input)
   
   # Contributions is a TimeSeriesDataset with same shape as input
   # Each feature column shows its contribution to the prediction
   print(contributions.data.head())
   #                      temperature  hour  dayofweek  ...
   # 2024-01-01 00:00:00        +2.3  -0.8       +1.2  ...
   # 2024-01-01 01:00:00        +2.1  -0.6       +1.2  ...

This is particularly useful for debugging unexpected predictions or understanding model behavior in specific scenarios.

Compositional Design
--------------------

The ``openstef_models`` package is designed for composition. Transforms can be chained, models can be swapped, and explainability tools work across all forecaster implementations:

.. code-block:: python

   # Build a complete forecasting pipeline
   from openstef_models.transforms.time_domain import TemporalFeaturesAdder
   from openstef_models.transforms.weather_domain import (
       DaylightFeatureAdder,
       AtmosphereDerivedFeaturesAdder
   )
   from openstef_models.models.forecasting import LGBMForecaster
   
   # Apply transforms
   transforms = [
       TemporalFeaturesAdder(),
       DaylightFeatureAdder(latitude=52.0, longitude=5.0),
       AtmosphereDerivedFeaturesAdder()
   ]
   
   enriched_data = train_data
   for transform in transforms:
       enriched_data = transform.fit(enriched_data).transform(enriched_data)
   
   # Train model on enriched data
   forecaster = LGBMForecaster(quantiles=[0.1, 0.5, 0.9])
   forecaster.fit(enriched_data)
   
   # Explain results
   importance = forecaster.feature_importances
   fig = forecaster.plot_feature_importances()

This compositional approach enables flexible experimentation with different feature engineering strategies and model configurations.

Integration with Core
---------------------

The ``openstef_models`` package builds directly on ``openstef_core`` data structures. All transforms and models consume and produce ``TimeSeriesDataset``, ``TrainingDataset``, or ``ForecastInputDataset`` objects, ensuring type safety and consistent data handling.

For details on these core data structures, see the :doc:`core` page. For information on model evaluation and backtesting workflows, see the :doc:`beam` page.