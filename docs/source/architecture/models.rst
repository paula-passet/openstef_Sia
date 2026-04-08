Models Package
===============

The ``openstef_models`` package provides the machine learning layer of OpenSTEF, implementing forecasting models and the feature engineering pipelines that prepare data for them. This package builds on ``openstef_core`` by consuming ``TimeSeriesDataset`` objects and applying domain-specific transformations, training probabilistic forecasters, and providing explainability tools to understand model behavior.

The package is organized into three main components: transforms for feature engineering, models for forecasting, and explainability utilities for model interpretation.

Feature Engineering Transforms
-------------------------------

The ``transforms`` module provides feature engineering pipelines organized by domain. Each transform implements the ``TimeSeriesTransform`` interface from ``openstef_core``, following the scikit-learn fit/transform pattern. Transforms are composable and can be chained together in pipelines.

Domain-Specific Transform Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF organizes transforms into five domain-specific modules:

**time_domain**: Temporal feature engineering including:

- ``DatetimeFeaturesAdder``: Extracts hour, day of week, month, and other calendar features
- ``CyclicFeaturesAdder``: Converts temporal features to cyclic representations (sin/cos encoding)
- ``HolidayFeatureAdder``: Adds binary holiday indicators based on regional calendars
- ``RollingAggregatesAdder``: Computes rolling statistics (mean, std, min, max) over configurable windows
- ``LagsAdder``: Creates lagged features from target and predictor variables

**weather_domain**: Weather-specific transformations for meteorological data

**energy_domain**: Energy sector features including:

- ``WindPowerFeatureAdder``: Converts wind speed to wind power using power curve models

**general**: Universal transforms applicable across domains:

- ``Imputer``: Fills missing values using forward fill, interpolation, or constant strategies
- ``Scaler``: Normalizes features using standard or min-max scaling
- ``Clipper``: Clips feature values to observed training ranges to prevent extrapolation
- ``Selector``: Filters dataset to specified features
- ``EmptyFeatureRemover``: Drops columns with all missing values
- ``NaNDropper``: Removes rows with missing values
- ``SampleWeighter``: Assigns weights to samples based on recency or custom logic

**validation**: Data quality checks and validation transforms

Transform Pipeline Example
^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms are typically chained together using ``TransformPipeline`` from ``openstef_core``:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder,
       LagsAdder,
   )
   from openstef_models.transforms.general import (
       Imputer,
       Scaler,
       EmptyFeatureRemover,
   )
   
   # Build a feature engineering pipeline
   pipeline = TransformPipeline(transforms=[
       EmptyFeatureRemover(),
       DatetimeFeaturesAdder(),
       CyclicFeaturesAdder(features=["hour", "month"]),
       LagsAdder(lags=[1, 24, 168]),  # 1h, 1d, 1w lags
       Imputer(method="forward_fill"),
       Scaler(method="standard"),
   ])
   
   # Fit on training data
   pipeline.fit(train_dataset)
   
   # Transform both train and test data
   train_transformed = pipeline.transform(train_dataset)
   test_transformed = pipeline.transform(test_dataset)

Each transform implements the ``features_added()`` method, allowing you to track which features are introduced at each stage. Stateful transforms like ``Scaler`` and ``Clipper`` learn parameters during ``fit()`` and apply them consistently during ``transform()``.

Forecasting Models
------------------

The ``models.forecasting`` module provides probabilistic forecasting implementations that predict multiple quantiles simultaneously. All forecasters inherit from ``ForecastingModel`` and implement a consistent interface for training and prediction.

Available Forecasters
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes several gradient boosting implementations optimized for energy forecasting:

**XGBoostForecaster**: XGBoost-based quantile regression model. The workhorse of OpenSTEF, providing fast training and strong performance on tabular energy data. Uses ``XGBQuantileOpenstfRegressor`` internally to train separate models for each quantile.

**LGBMForecaster**: LightGBM-based quantile regression. Alternative gradient boosting implementation with different regularization characteristics.

**GBLinearForecaster**: Linear gradient boosting model for interpretable forecasts when relationships are approximately linear.

**LGBMLinearForecaster**: Hybrid model combining LightGBM with linear components.

**MedianForecaster**: Simple baseline that predicts the median of recent observations.

**FlatlinerForecaster**: Persistence baseline that repeats the last observed value.

All forecasters support configurable hyperparameters through dedicated config classes (e.g., ``XGBoostHyperParams``, ``LGBMHyperParams``).

Training and Prediction
^^^^^^^^^^^^^^^^^^^^^^^

Forecasters consume ``ForecastInputDataset`` objects and produce probabilistic predictions:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster, XGBoostHyperParams
   from openstef_core.types import Q
   
   # Configure hyperparameters
   hyperparams = XGBoostHyperParams(
       max_depth=6,
       learning_rate=0.1,
       n_estimators=100,
       subsample=0.8,
   )
   
   # Initialize forecaster with quantiles to predict
   forecaster = XGBoostForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       hyperparams=hyperparams,
   )
   
   # Train on prepared data
   forecaster.fit(train_dataset)
   
   # Generate probabilistic predictions
   predictions = forecaster.predict(test_dataset)
   
   # Access specific quantiles
   median_forecast = predictions.quantile(Q(0.5))
   lower_bound = predictions.quantile(Q(0.1))
   upper_bound = predictions.quantile(Q(0.9))

The ``ForecastingModel`` base class handles quantile management, ensuring predictions are properly sorted and aligned. Models automatically validate that quantiles are monotonically increasing.

Compositional Design
^^^^^^^^^^^^^^^^^^^^

Forecasters are designed to compose with transform pipelines. A typical workflow chains feature engineering, model training, and postprocessing:

.. code-block:: python

   from openstef_models.transforms.postprocessing import (
       QuantileSorter,
       ConfidenceIntervalApplicator,
   )
   
   # Feature engineering pipeline
   feature_pipeline = TransformPipeline(transforms=[...])
   
   # Train forecaster on transformed data
   train_features = feature_pipeline.fit_transform(train_data)
   forecaster.fit(train_features)
   
   # Predict and postprocess
   test_features = feature_pipeline.transform(test_data)
   raw_predictions = forecaster.predict(test_features)
   
   # Apply postprocessing transforms
   postprocess_pipeline = TransformPipeline(transforms=[
       QuantileSorter(),  # Ensure quantile ordering
       ConfidenceIntervalApplicator(),  # Add confidence intervals
   ])
   final_predictions = postprocess_pipeline.transform(raw_predictions)

This separation of concerns allows you to experiment with different feature engineering strategies independently of model selection, and vice versa.

Explainability Tools
--------------------

The ``explainability`` module provides tools for understanding model behavior through feature importance analysis and contribution tracking. These tools help answer questions like "Which features drive this forecast?" and "Why did the model predict this value?"

Feature Importance
^^^^^^^^^^^^^^^^^^

Forecasters that inherit from ``ExplainableForecaster`` expose feature importance scores through the ``feature_importances`` property:

.. code-block:: python

   # Get feature importance DataFrame
   importances = forecaster.feature_importances
   
   # importances is a DataFrame with:
   # - Index: feature names
   # - Columns: quantiles (e.g., Q(0.1), Q(0.5), Q(0.9))
   # - Values: importance scores (higher = more important)
   
   # Visualize with built-in plotter
   fig = forecaster.plot_feature_importances(quantile=Q(0.5))
   fig.show()

The ``plot_feature_importances()`` method generates an interactive Plotly treemap visualization, making it easy to identify the most influential features at a glance. This uses the ``FeatureImportancePlotter`` utility internally.

Feature Contributions
^^^^^^^^^^^^^^^^^^^^^

For per-sample explanations, forecasters implementing ``ContributionsMixin`` provide the ``predict_contributions()`` method:

.. code-block:: python

   # Get per-sample feature contributions (SHAP-like values)
   contributions = forecaster.predict_contributions(test_dataset)
   
   # contributions is a TimeSeriesDataset where each column
   # represents the contribution of that feature to the prediction
   # at each time point

This enables detailed analysis of individual predictions, showing how each feature pushed the forecast up or down at specific times. This is particularly valuable for debugging unexpected predictions or understanding model behavior during extreme events.

Component Architecture
----------------------

.. note:: [DIAGRAM: Three-layer architecture showing: (1) Transform layer with domain modules feeding into pipelines, (2) Model layer with forecasters consuming transformed data, (3) Explainability layer providing feature importance and contributions back to users. Arrows show data flow from TimeSeriesDataset through transforms to forecasters to predictions.]

The ``openstef_models`` package follows a compositional architecture:

1. **Transform Layer**: Domain-specific feature engineering modules that consume and produce ``TimeSeriesDataset`` objects
2. **Model Layer**: Forecasting implementations that train on transformed features and generate probabilistic predictions
3. **Explainability Layer**: Mixins and utilities that expose model internals for interpretation

This design allows components to be mixed and matched. You can swap forecasters without changing feature engineering, or experiment with different transform combinations while keeping the same model. The consistent use of ``TimeSeriesDataset`` as the data interchange format ensures all components integrate seamlessly.

Integration with Core
---------------------

The models package builds directly on ``openstef_core`` foundations:

- All transforms implement ``TimeSeriesTransform`` from ``openstef_core.transforms``
- Forecasters consume ``ForecastInputDataset`` and produce quantile predictions
- Transform pipelines use ``TransformPipeline`` from ``openstef_core`` for composition
- Type safety is enforced through ``openstef_core.types`` (``Quantile``, ``Q``, etc.)

This tight integration ensures that models package components work seamlessly with core data structures and interfaces. For details on the underlying dataset abstractions, see :doc:`core`.

Next Steps
----------

For information on how these models are evaluated and backtested at scale, see :doc:`beam`. To understand the complete forecasting workflow from data ingestion to deployment, refer to the architecture overview in :doc:`index`.