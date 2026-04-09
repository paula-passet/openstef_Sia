Models Package
===============

The ``openstef_models`` package provides the forecasting implementations, feature engineering pipelines, and explainability tools that power OpenSTEF's machine learning capabilities. This package builds on the core data structures from ``openstef_core`` and organizes functionality into three main areas: domain-specific feature transforms, forecasting model implementations, and explainability utilities.

Package Structure
-----------------

The models package follows a compositional design where feature engineering pipelines prepare data for forecasting models, which then produce predictions that can be explained through built-in tools:

- **transforms**: Feature engineering organized by domain (energy, time, weather, general)
- **models**: Forecasting implementations (XGBoost, linear models, ensemble methods)
- **explainability**: Feature importance and contribution analysis tools

All components work with ``TimeSeriesDataset`` from ``openstef_core``, ensuring consistent data handling across the library.

Feature Engineering Transforms
-------------------------------

The ``transforms`` module organizes feature engineering into domain-specific subpackages, each providing transforms that implement the ``TimeSeriesTransform`` interface. This design allows you to compose pipelines from reusable, testable components.

Domain Organization
^^^^^^^^^^^^^^^^^^^

Feature transforms are organized by the domain knowledge they encode:

**time_domain**: Temporal patterns and calendar effects

- ``DatetimeFeaturesAdder``: Extract hour, day, month from timestamps
- ``CyclicFeaturesAdder``: Encode cyclical time features (sin/cos)
- ``HolidayFeatureAdder``: Add holiday indicators
- ``LagsAdder``: Create lagged features from target or predictors
- ``RollingAggregatesAdder``: Compute rolling statistics (mean, std, min, max)

**weather_domain**: Meteorological feature engineering

- ``DaylightFeatureAdder``: Calculate sunrise, sunset, daylight duration
- ``AtmosphereDerivedFeaturesAdder``: Derive atmospheric properties
- ``RadiationDerivedFeaturesAdder``: Compute solar radiation features

**energy_domain**: Energy-specific transformations

- ``WindPowerFeatureAdder``: Convert wind speed to power using power curves

**general**: Cross-domain utilities

- ``Imputer``: Fill missing values
- ``Scaler``: Normalize features
- ``Clipper``: Constrain values to observed ranges
- ``Selector``: Choose specific features
- ``NaNDropper``: Remove incomplete samples
- ``EmptyFeatureRemover``: Drop columns with no variance
- ``SampleWeighter``: Assign sample weights for training

**validation**: Data quality checks

- ``CompletenessChecker``: Verify sufficient data coverage
- ``FlatlineChecker``: Detect constant values
- ``InputConsistencyChecker``: Validate data structure

Transform Pipeline Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms compose into pipelines that fit and transform data sequentially:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.general import Imputer, Scaler
   from openstef_models.transforms.validation import CompletenessChecker
   
   # Build a feature engineering pipeline
   pipeline = TransformPipeline[TimeSeriesDataset](
       transforms=[
           CompletenessChecker(min_completeness=0.9),
           DatetimeFeaturesAdder(),
           LagsAdder(lags=[1, 2, 24, 48], target_column="load"),
           RollingAggregatesAdder(
               window_sizes=[24, 168],
               aggregations=["mean", "std"],
               target_column="load",
           ),
           Imputer(strategy="forward_fill"),
           Scaler(method="standard"),
       ]
   )
   
   # Fit on training data
   pipeline.fit(train_data)
   
   # Transform training and test data
   train_features = pipeline.transform(train_data)
   test_features = pipeline.transform(test_data)

Each transform in the pipeline receives the output of the previous transform. The pipeline tracks fitted state and raises ``NotFittedError`` if you attempt to transform before fitting.

Forecasting Models
------------------

The ``models.forecasting`` module provides implementations of forecasting algorithms that consume feature-engineered data and produce probabilistic predictions.

XGBoost Forecaster
^^^^^^^^^^^^^^^^^^

The primary forecasting model is ``XGBoostForecaster``, which uses gradient boosting trees to produce multi-quantile forecasts:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster, XGBoostHyperParams
   from openstef_core.datasets import ForecastInputDataset
   
   # Configure hyperparameters
   hparams = XGBoostHyperParams(
       max_depth=5,
       learning_rate=0.1,
       n_estimators=100,
       subsample=0.8,
       colsample_bytree=0.8,
   )
   
   # Create forecaster
   forecaster = XGBoostForecaster(hparams=hparams)
   
   # Fit on training data
   forecaster.fit(train_data, data_val=validation_data)
   
   # Generate predictions
   forecast = forecaster.predict(test_data)

The forecaster produces a ``ForecastDataset`` containing predictions at multiple quantiles (typically 0.1, 0.5, 0.9), enabling probabilistic forecasting and uncertainty quantification.

Other Model Types
^^^^^^^^^^^^^^^^^

The package includes additional forecasting implementations:

- **MedianForecaster**: Simple baseline using median of lagged values
- **LinearForecaster**: Ridge regression for linear relationships
- **Ensemble methods**: Combine multiple models for improved robustness

All forecasters implement the ``Forecaster`` interface, providing consistent ``fit`` and ``predict`` methods that work with ``ForecastInputDataset`` and return ``ForecastDataset``.

Explainability Tools
--------------------

The ``explainability`` module provides tools for understanding model predictions through feature importance and contribution analysis.

Feature Importance
^^^^^^^^^^^^^^^^^^

Models that implement the ``ExplainableForecaster`` mixin expose feature importance scores:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   
   # After fitting the model
   forecaster.fit(train_data)
   
   # Get feature importance scores
   importances = forecaster.feature_importances
   # Returns DataFrame with features as index, quantiles as columns
   
   # Visualize with built-in plotting
   fig = forecaster.plot_feature_importances(quantile=0.5)
   fig.show()

The ``plot_feature_importances`` method creates an interactive treemap visualization using Plotly, showing which features contribute most to predictions.

Feature Contributions
^^^^^^^^^^^^^^^^^^^^^

For per-sample explanations, models implementing ``ContributionsMixin`` compute SHAP-based feature contributions:

.. code-block:: python

   # Compute contributions for specific predictions
   contributions = forecaster.predict_contributions(test_data)
   
   # Returns TimeSeriesDataset with contribution values for each feature
   # at each timestamp, showing how each feature influenced the prediction

This uses SHAP (SHapley Additive exPlanations) internally to decompose predictions into additive feature contributions, enabling detailed analysis of individual forecasts.

Compositional Design
--------------------

The models package demonstrates OpenSTEF's compositional architecture. Rather than monolithic workflows, you compose functionality from small, focused components:

1. **Transforms** are stateful but side-effect-free, producing new datasets rather than modifying inputs
2. **Forecasters** depend only on the ``ForecastInputDataset`` interface, not specific transforms
3. **Explainability** is added through mixins, keeping model implementations focused

This design enables testing components in isolation, swapping implementations, and building custom workflows without modifying library code.

Integration with Core
^^^^^^^^^^^^^^^^^^^^^

All components in ``openstef_models`` operate on data structures from ``openstef_core``:

- Transforms consume and produce ``TimeSeriesDataset``
- Forecasters accept ``ForecastInputDataset`` and return ``ForecastDataset``
- Feature selection uses ``FeatureSelection`` with ``Include``/``Exclude`` patterns

See :doc:`core` for details on these data structures and how they enable type-safe, validated data flow through the library.

Next Steps
----------

For complete forecasting workflows that combine transforms, models, and validation, see the workflows documentation. For backtesting and model evaluation, see :doc:`beam` which provides distributed evaluation tools.