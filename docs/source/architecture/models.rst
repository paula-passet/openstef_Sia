Models Package
===============

The ``openstef_models`` package provides the forecasting implementations, feature engineering pipelines, and explainability tools that form OpenSTEF's machine learning layer. This package builds on ``openstef_core`` data structures and implements domain-specific transforms, production-ready forecasting models, and tools for interpreting predictions.

Architecture Overview
---------------------

The package follows a compositional design with three main layers:

**Transforms Layer**: Domain-organized feature engineering pipelines that convert raw time series data into model-ready features. Transforms are grouped by domain (time, weather, energy, general) and compose into reusable pipelines.

**Models Layer**: Forecasting implementations including XGBoost-based quantile regressors and baseline models. Models consume ``ForecastInputDataset`` objects and produce ``ForecastDataset`` predictions.

**Explainability Layer**: Mixins and utilities for model interpretation, including SHAP-based feature contributions and interactive visualization of feature importance.

.. note:: [DIAGRAM: Component architecture showing transforms → models → explainability flow, with TransformPipeline orchestrating multiple domain-specific transforms feeding into Forecaster implementations that implement ExplainableForecaster and ContributionsMixin interfaces]

Feature Engineering Transforms
-------------------------------

The ``transforms`` module organizes feature engineering by domain, providing composable building blocks for preprocessing pipelines. Each transform implements the ``TimeSeriesTransform`` interface from ``openstef_core``, supporting fit/transform patterns and pipeline composition.

Domain Organization
^^^^^^^^^^^^^^^^^^^

**time_domain**: Temporal feature extraction including lag features, rolling aggregates, datetime components, cyclic encodings, and holiday indicators. These transforms capture temporal patterns and seasonality.

**weather_domain**: Weather-specific features such as daylight calculations, atmospheric derived features, and radiation-based features. Essential for weather-dependent energy forecasting.

**energy_domain**: Energy sector-specific transforms like wind power calculations from wind speed data. Domain knowledge encoded as reusable components.

**general**: Cross-domain utilities including data validation, imputation, scaling, clipping, and feature selection. These handle data quality and normalization concerns.

**validation**: Input validation transforms like completeness checking, flatline detection, and consistency validation. Run early in pipelines to catch data quality issues.

Pipeline Composition
^^^^^^^^^^^^^^^^^^^^

Transforms compose into pipelines using ``TransformPipeline`` from ``openstef_core``. Pipelines fit transforms sequentially, with each transform receiving the output of the previous stage:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       LagsAdder,
       RollingAggregatesAdder,
       AggregationFunction,
   )
   from openstef_models.transforms.general import Imputer, Scaler
   from openstef_models.transforms.validation import CompletenessChecker
   
   # Build a feature engineering pipeline
   preprocessing = TransformPipeline(transforms=[
       CompletenessChecker(min_completeness=0.95),
       DatetimeFeaturesAdder(),
       LagsAdder(lags=[1, 2, 24, 168]),
       RollingAggregatesAdder(
           windows=[24, 168],
           functions=[AggregationFunction.MEAN, AggregationFunction.STD],
       ),
       Imputer(),
       Scaler(),
   ])
   
   # Fit and transform training data
   processed_train = preprocessing.fit_transform(data=train_dataset)
   
   # Transform validation data using fitted parameters
   processed_val = preprocessing.transform(data=val_dataset)

The pipeline maintains state across transforms—scalers fit on training data apply the same normalization to validation data, ensuring consistency.

Common Transform Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Lag Features**: Create autoregressive features by adding historical values at specified time offsets. Critical for capturing temporal dependencies:

.. code-block:: python

   from openstef_models.transforms.time_domain import LagsAdder
   
   # Add hourly, daily, and weekly lags
   lags_transform = LagsAdder(lags=[1, 24, 168])
   data_with_lags = lags_transform.fit_transform(data=dataset)

**Rolling Aggregates**: Compute statistics over sliding windows to capture trends and variability:

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       RollingAggregatesAdder,
       AggregationFunction,
   )
   
   rolling_transform = RollingAggregatesAdder(
       windows=[24, 168],  # 1 day and 1 week
       functions=[AggregationFunction.MEAN, AggregationFunction.MAX],
   )

**Cyclic Encoding**: Encode periodic features (hour, day of week) as sine/cosine pairs to preserve cyclical nature:

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder
   
   cyclic_transform = CyclicFeaturesAdder()
   # Adds sin/cos encodings for hour, day_of_week, etc.

**Domain-Specific Features**: Apply energy sector knowledge through specialized transforms:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   # Convert wind speed to wind power using power curve
   wind_transform = WindPowerFeatureAdder()
   data_with_wind_power = wind_transform.fit_transform(data=dataset)

Forecasting Models
------------------

The ``models.forecasting`` module provides production-ready forecasting implementations. All forecasters implement the ``Forecaster`` interface and support quantile regression for probabilistic predictions.

XGBoost Forecaster
^^^^^^^^^^^^^^^^^^

``XGBoostForecaster`` is the primary production model, using gradient boosting trees for multi-quantile energy forecasting. It trains separate models for each quantile to produce full prediction intervals:

.. code-block:: python

   from openstef_models.models.forecasting import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_core.types import Q
   
   # Configure hyperparameters
   hparams = XGBoostHyperParams(
       max_depth=7,
       learning_rate=0.1,
       n_estimators=100,
       subsample=0.8,
       colsample_bytree=0.8,
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],  # 10th, 50th, 90th percentiles
   )
   
   # Create and train forecaster
   forecaster = XGBoostForecaster(hparams=hparams)
   forecaster.fit(data=train_input, data_val=val_input)
   
   # Generate probabilistic predictions
   forecast = forecaster.predict(data=test_input)
   
   # Access quantile predictions
   median_forecast = forecast.quantiles[Q(0.5)]
   lower_bound = forecast.quantiles[Q(0.1)]
   upper_bound = forecast.quantiles[Q(0.9)]

The forecaster automatically handles quantile loss optimization and provides separate models for each quantile, enabling accurate uncertainty quantification.

Baseline Models
^^^^^^^^^^^^^^^

The package includes baseline forecasters for comparison and fallback scenarios:

**MedianForecaster**: Simple baseline that predicts the median of recent lag features. Useful for benchmarking and as a fallback when more complex models fail:

.. code-block:: python

   from openstef_models.models.forecasting import MedianForecaster
   
   baseline = MedianForecaster()
   baseline.fit(data=train_input)
   baseline_forecast = baseline.predict(data=test_input)

Baseline models implement the same ``Forecaster`` interface as production models, making them drop-in replacements for testing and comparison.

Model Configuration
^^^^^^^^^^^^^^^^^^^

Forecasters use Pydantic-based configuration through hyperparameter classes. This provides validation, serialization, and type safety:

.. code-block:: python

   # Hyperparameters are validated at construction
   hparams = XGBoostHyperParams(
       max_depth=7,
       min_child_weight=5,
       gamma=0.1,
       subsample=0.8,
       colsample_bytree=0.8,
       learning_rate=0.1,
       n_estimators=100,
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )
   
   # Serialize configuration
   config_dict = hparams.model_dump()
   
   # Reconstruct from configuration
   loaded_hparams = XGBoostHyperParams.model_validate(config_dict)

Explainability Tools
--------------------

The ``explainability`` module provides tools for interpreting model predictions through feature importance analysis and per-sample contributions.

Feature Importance
^^^^^^^^^^^^^^^^^^

Models implementing ``ExplainableForecaster`` expose feature importance scores showing which features most influence predictions:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   
   forecaster = XGBoostForecaster(hparams=hparams)
   forecaster.fit(data=train_input)
   
   # Get feature importance scores
   importance_df = forecaster.feature_importances
   # Returns DataFrame with features as index, quantiles as columns
   
   # Visualize with built-in plotter
   fig = forecaster.plot_feature_importances(quantile=Q(0.5))
   fig.show()  # Interactive Plotly treemap

Feature importance helps identify which inputs drive predictions, useful for model debugging and domain validation.

SHAP Contributions
^^^^^^^^^^^^^^^^^^

Models implementing ``ContributionsMixin`` compute per-sample feature contributions using SHAP (SHapley Additive exPlanations):

.. code-block:: python

   # Compute contributions for specific predictions
   contributions = forecaster.predict_contributions(data=test_input)
   
   # contributions is a TimeSeriesDataset with contribution values
   # for each feature at each time step
   
   # Analyze which features contributed most to a specific prediction
   sample_contributions = contributions.data.iloc[0]
   top_features = sample_contributions.abs().nlargest(10)

SHAP contributions explain individual predictions by showing how each feature value contributed to the final forecast, enabling detailed prediction analysis.

Visualization Integration
^^^^^^^^^^^^^^^^^^^^^^^^^

Explainability tools integrate with OpenSTEF's built-in visualization utilities. The ``FeatureImportancePlotter`` creates interactive treemap visualizations:

.. code-block:: python

   from openstef_models.explainability import FeatureImportancePlotter
   
   plotter = FeatureImportancePlotter()
   fig = plotter.plot(
       feature_importances=forecaster.feature_importances,
       quantile=Q(0.5),
   )
   fig.show()

These visualizations use Plotly for interactivity, allowing users to explore feature hierarchies and importance distributions.

Integration with Core
---------------------

The models package builds directly on ``openstef_core`` abstractions:

- **Data Structures**: Transforms consume and produce ``TimeSeriesDataset`` objects; forecasters use ``ForecastInputDataset`` and ``ForecastDataset``
- **Transform Interface**: All transforms implement ``Transform`` protocol from core, enabling pipeline composition
- **Type Safety**: Uses core types like ``Quantile`` and ``Horizon`` for type-safe configuration

This tight integration ensures models work seamlessly with core data structures while adding domain-specific functionality.

See Also
--------

- :doc:`core` - Core data structures and interfaces used by models
- :doc:`beam` - Backtesting and evaluation tools for model validation