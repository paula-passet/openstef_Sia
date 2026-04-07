Models Package
==============

The ``openstef_models`` package provides the machine learning layer of OpenSTEF: feature engineering transforms organized by domain, forecasting model implementations, and explainability tools. This package builds on the core data structures from ``openstef_core`` to deliver production-ready forecasting capabilities.

The package follows a compositional design where transforms, models, and explainability components work together through well-defined interfaces. All components operate on ``TimeSeriesDataset`` instances from the core package, ensuring type safety and consistent data handling.

.. note:: [DIAGRAM: Component architecture showing three layers: transforms (energy_domain, time_domain, weather_domain, general, validation), models (XGBoostForecaster, LGBMForecaster, etc.), and explainability (ExplainableForecaster mixin, FeatureImportancePlotter). Arrows show data flow from TimeSeriesDataset through transforms to models, with explainability as a cross-cutting concern.]

Feature Engineering Transforms
-------------------------------

The ``transforms`` module organizes feature engineering pipelines by domain expertise. Each transform implements the ``TimeSeriesTransform`` protocol, providing ``fit()`` and ``transform()`` methods that operate on ``TimeSeriesDataset`` instances.

Domain-Specific Transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms are organized into domain-specific subpackages:

- ``energy_domain``: Energy-specific features like wind power calculations
- ``time_domain``: Temporal features including lags, rolling aggregates, and holiday indicators
- ``weather_domain``: Weather-related feature engineering
- ``general``: Domain-agnostic transforms like scaling, clipping, and imputation
- ``validation``: Data quality and validation transforms

This organization reflects the multidisciplinary nature of energy forecasting, where domain knowledge from meteorology, energy systems, and time series analysis must be combined.

Example: Time Domain Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The time domain transforms handle temporal patterns that are critical for energy forecasting:

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from openstef_core.datasets import TimeSeriesDataset
   
   # Add datetime features (hour, day of week, month, etc.)
   datetime_adder = DatetimeFeaturesAdder()
   data = datetime_adder.transform(data)
   
   # Add cyclic encodings for periodic features
   cyclic_adder = CyclicFeaturesAdder()
   data = cyclic_adder.transform(data)
   
   # Add holiday indicators
   holiday_adder = HolidayFeatureAdder(country="NL")
   data = holiday_adder.transform(data)
   
   # Add lagged features
   lags_adder = LagsAdder(lags=[1, 2, 24, 168])  # 1h, 2h, 1d, 1w
   data = lags_adder.fit(data).transform(data)
   
   # Add rolling aggregates
   rolling_adder = RollingAggregatesAdder(
       windows=[24, 168],
       functions=["mean", "std"]
   )
   data = rolling_adder.fit(data).transform(data)

Example: Energy Domain Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Energy domain transforms encode physical relationships specific to energy systems:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   # Convert wind speed to wind power using power curve
   wind_adder = WindPowerFeatureAdder()
   data = wind_adder.transform(data)
   
   # Check which features were added
   print(wind_adder.features_added())

Example: General Transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

General transforms handle common preprocessing tasks:

.. code-block:: python

   from openstef_models.transforms.general import (
       Imputer,
       Scaler,
       Clipper,
       Selector,
       EmptyFeatureRemover,
       NaNDropper,
       SampleWeighter,
   )
   
   # Impute missing values
   imputer = Imputer(strategy="forward_fill")
   data = imputer.transform(data)
   
   # Scale features
   scaler = Scaler(method="standard")
   data = scaler.fit(data).transform(data)
   
   # Clip features to observed ranges
   clipper = Clipper(features=["temperature", "wind_speed"])
   data = clipper.fit(data).transform(data)
   
   # Select specific features
   selector = Selector(features=["hour", "temperature", "load_lag_24"])
   data = selector.transform(data)
   
   # Remove empty features
   empty_remover = EmptyFeatureRemover()
   data = empty_remover.transform(data)
   
   # Add sample weights for training
   weighter = SampleWeighter(
       weight_type="exponential",
       decay_rate=0.01
   )
   data = weighter.fit(data).transform(data)

Transform Composition
^^^^^^^^^^^^^^^^^^^^^

Transforms are designed to be composed into pipelines. Each transform returns a ``TimeSeriesDataset``, allowing chaining:

.. code-block:: python

   # Build a feature engineering pipeline
   data = (
       datetime_adder.transform(data)
       .pipe(cyclic_adder.transform)
       .pipe(holiday_adder.transform)
       .pipe(lags_adder.fit(data).transform)
       .pipe(rolling_adder.fit(data).transform)
       .pipe(wind_adder.transform)
       .pipe(imputer.transform)
       .pipe(scaler.fit(data).transform)
   )

Forecasting Models
------------------

The ``models.forecasting`` module provides implementations of forecasting algorithms optimized for energy prediction. All models implement the ``ForecastingModel`` protocol and support quantile regression for probabilistic forecasting.

Available Models
^^^^^^^^^^^^^^^^

OpenSTEF provides several gradient boosting implementations:

- ``XGBoostForecaster``: XGBoost-based quantile regression
- ``LGBMForecaster``: LightGBM-based quantile regression
- ``GBLinearForecaster``: Linear gradient boosting
- ``LGBMLinearForecaster``: LightGBM with linear trees
- ``FlatlinerForecaster``: Baseline model that predicts constant values
- ``MedianForecaster``: Baseline model that predicts historical median

The gradient boosting models are the workhorses of OpenSTEF, providing accurate probabilistic forecasts through quantile regression.

Example: Training a Forecaster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster, XGBoostHyperParams
   from openstef_core.types import Q
   
   # Configure hyperparameters
   hyperparams = XGBoostHyperParams(
       max_depth=5,
       learning_rate=0.1,
       n_estimators=100,
       subsample=0.8,
       colsample_bytree=0.8,
   )
   
   # Create forecaster for multiple quantiles
   forecaster = XGBoostForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       hyperparams=hyperparams,
   )
   
   # Train on ForecastInputDataset
   forecaster.fit(train_data)
   
   # Make predictions
   predictions = forecaster.predict(test_data)

The ``XGBoostForecaster`` trains separate models for each quantile, enabling full probabilistic forecasts. The predictions are returned as a ``TimeSeriesDataset`` with columns for each quantile.

Example: Using Different Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_models.models.forecasting import (
       LGBMForecaster,
       LGBMHyperParams,
       FlatlinerForecaster,
   )
   
   # LightGBM model
   lgbm_forecaster = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       hyperparams=LGBMHyperParams(
           num_leaves=31,
           learning_rate=0.1,
           n_estimators=100,
       ),
   )
   lgbm_forecaster.fit(train_data)
   
   # Baseline flatliner model
   baseline = FlatlinerForecaster()
   baseline.fit(train_data)
   baseline_predictions = baseline.predict(test_data)

Model Persistence
^^^^^^^^^^^^^^^^^

Models can be saved and loaded for production deployment:

.. code-block:: python

   import joblib
   
   # Save trained model
   joblib.dump(forecaster, "forecaster.pkl")
   
   # Load model
   loaded_forecaster = joblib.load("forecaster.pkl")
   predictions = loaded_forecaster.predict(new_data)

For production systems, consider using the MLflow integration provided in ``openstef_models.integrations.mlflow`` for model versioning and tracking.

Explainability Tools
--------------------

The ``explainability`` module provides tools for understanding model behavior through feature importance analysis and contribution tracking. These tools are essential for validating models and building trust with stakeholders.

Feature Importance
^^^^^^^^^^^^^^^^^^

Models that inherit from ``ExplainableForecaster`` expose feature importance scores:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.types import Q
   
   # Train a model
   forecaster = XGBoostForecaster(quantiles=[Q(0.5)])
   forecaster.fit(train_data)
   
   # Get feature importances as DataFrame
   importances = forecaster.feature_importances
   print(importances.head(10))  # Top 10 features
   
   # Create interactive visualization
   fig = forecaster.plot_feature_importances(quantile=Q(0.5))
   fig.show()

The ``feature_importances`` property returns a DataFrame with feature names as the index and quantiles as columns. This allows you to see which features are most important for each quantile prediction.

Feature Contributions
^^^^^^^^^^^^^^^^^^^^^

Models that inherit from ``ContributionsMixin`` can explain individual predictions:

.. code-block:: python

   # Compute per-sample feature contributions (SHAP values)
   contributions = forecaster.predict_contributions(test_data)
   
   # Contributions is a TimeSeriesDataset with same shape as predictions
   # Each value shows how much that feature contributed to the prediction

Feature contributions use SHAP (SHapley Additive exPlanations) values to decompose each prediction into the sum of feature contributions. This is particularly useful for debugging unexpected predictions or explaining forecasts to stakeholders.

Visualization
^^^^^^^^^^^^^

The ``plotters`` submodule provides visualization tools:

.. code-block:: python

   from openstef_models.explainability.plotters import FeatureImportancePlotter
   
   # Create custom importance visualizations
   plotter = FeatureImportancePlotter()
   fig = plotter.plot_treemap(
       importances=forecaster.feature_importances,
       quantile=Q(0.5),
       top_n=20,
   )
   fig.show()

Integration with Core
---------------------

The models package is designed to work seamlessly with ``openstef_core`` data structures. All transforms and models consume and produce ``TimeSeriesDataset`` instances, and forecasters accept ``ForecastInputDataset`` for training and prediction.

This tight integration ensures type safety and consistent data handling across the forecasting pipeline. See the :doc:`core` documentation for details on these data structures.

For information on model evaluation and backtesting, see the :doc:`beam` documentation, which covers the ``openstef_beam`` package for batch processing and metrics computation.