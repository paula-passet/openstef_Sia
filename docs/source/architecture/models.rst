Models Package
==============

The ``openstef_models`` package provides the forecasting models, feature engineering pipelines, and explainability tools that form the machine learning layer of OpenSTEF. This package builds on the data structures and interfaces defined in ``openstef_core`` to deliver production-ready forecasting capabilities organized around three key components: domain-specific feature transforms, model implementations, and explainability utilities.

.. note:: [DIAGRAM: Component architecture showing three layers - transforms (energy_domain, time_domain, weather_domain, general, validation), models (XGBoostForecaster, LGBMForecaster, LGBMLinearForecaster, GBLinearForecaster), and explainability (ExplainableForecaster mixin, ContributionsMixin, FeatureImportancePlotter). Arrows show data flow from TimeSeriesDataset through TransformPipeline to Forecaster to predictions, with explainability as a cross-cutting concern.]

Package Structure
-----------------

The package is organized into three main modules:

- **transforms**: Feature engineering pipelines organized by domain (energy, time, weather, general) plus validation utilities
- **models**: Forecasting model implementations wrapping gradient boosting and linear algorithms
- **explainability**: Tools for interpreting model behavior through feature importance and per-sample contributions

This compositional design allows you to mix and match transforms, swap model implementations, and add explainability without modifying core logic.

Feature Engineering with Transforms
------------------------------------

The ``transforms`` module provides domain-specific feature engineering organized into subpackages. Each transform implements the ``Transform[I, O]`` interface from ``openstef_core``, supporting ``fit()``, ``transform()``, and ``fit_transform()`` methods.

Domain-Specific Transform Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**energy_domain**
  Energy-specific transformations like wind power calculation from wind speed data. The ``WindPowerFeatureAdder`` computes wind power features using physical models.

**time_domain**
  Temporal feature engineering such as lag features, rolling statistics, and time-based indicators (hour of day, day of week).

**weather_domain**
  Weather-related transformations including temperature conversions, radiation calculations, and weather regime indicators.

**general**
  General-purpose transforms like the ``Clipper``, which constrains feature values to observed ranges during training to prevent extrapolation issues.

**validation**
  Data validation transforms that check for required columns, valid ranges, and data quality issues before model training.

Transform Pipelines
^^^^^^^^^^^^^^^^^^^

Transforms compose into pipelines using the ``TransformPipeline[T]`` class, which applies transforms sequentially and manages fitting state:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.general import Clipper
   from openstef_models.transforms.validation import RequiredColumnsValidator

   # Build a feature engineering pipeline
   pipeline = TransformPipeline[TimeSeriesDataset](
       transforms=[
           RequiredColumnsValidator(required_columns=["windspeed_100m"]),
           WindPowerFeatureAdder(),
           Clipper(features_to_clip=["windspeed_100m", "wind_power"]),
       ]
   )

   # Fit and transform training data
   train_transformed = pipeline.fit_transform(data=train_data)

   # Transform validation data using fitted parameters
   val_transformed = pipeline.transform(data=val_data)

The pipeline ensures transforms are applied in order, with each transform receiving the output of the previous one. Fitting happens sequentially—each transform fits on the intermediate output of the previous transforms.

Forecasting Models
------------------

The ``models`` module provides forecasting implementations that wrap gradient boosting and linear algorithms. All models implement the ``Forecaster`` interface from ``openstef_core``, providing consistent ``fit()`` and ``predict()`` methods.

Available Model Implementations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**XGBoostForecaster**
  Gradient boosted trees using XGBoost with quantile regression support. Configured via ``XGBoostHyperParams`` including learning rate, tree depth, and regularization parameters.

**LGBMForecaster**
  Gradient boosted trees using LightGBM with quantile regression. Configured via ``LGBMHyperParams`` with similar parameters to XGBoost but optimized for LightGBM's architecture.

**GBLinearForecaster**
  Linear model using XGBoost's linear booster. Provides interpretable linear relationships while leveraging XGBoost's optimization infrastructure.

**LGBMLinearForecaster**
  Linear model using LightGBM's linear booster. Alternative to GBLinearForecaster with LightGBM's computational advantages.

All models support multi-quantile forecasting, allowing you to predict multiple quantiles simultaneously for probabilistic forecasts.

Model Configuration and Usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Models are configured using Pydantic-based hyperparameter classes and support both CPU and GPU computation:

.. code-block:: python

   from openstef_models.models import XGBoostForecaster, XGBoostHyperParams
   from openstef_core.datasets import ForecastInputDataset

   # Configure model with custom hyperparameters
   forecaster = XGBoostForecaster(
       hyperparams=XGBoostHyperParams(
           n_estimators=100,
           learning_rate=0.1,
           max_depth=6,
           subsample=0.8,
           colsample_bytree=0.8,
       ),
       device="cpu",
       n_jobs=4,
       verbosity=1,
   )

   # Train the model
   forecaster.fit(data=train_data, data_val=val_data)

   # Generate predictions
   predictions = forecaster.predict(data=test_data)

The ``fit()`` method accepts optional validation data for early stopping, and ``predict()`` returns a ``ForecastOutputDataset`` containing quantile predictions.

Integrating Transforms and Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Models typically include preprocessing and postprocessing pipelines as configuration parameters. For example, component splitters use transform pipelines to prepare data:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.general import Clipper
   from openstef_models.models import XGBoostForecaster

   # Create preprocessing pipeline
   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           Clipper(features_to_clip=["temperature", "radiation"]),
       ]
   )

   # Configure forecaster with preprocessing
   forecaster = XGBoostForecaster(
       hyperparams=XGBoostHyperParams(n_estimators=100),
   )

   # Manually apply preprocessing before training
   train_processed = preprocessing.fit_transform(data=train_data)
   forecaster.fit(data=train_processed)

This separation allows you to test feature engineering independently from model training and swap preprocessing logic without modifying model code.

Explainability Tools
--------------------

The ``explainability`` module provides tools for understanding model behavior through feature importance and per-sample contribution analysis. These capabilities are exposed through mixin classes that models can implement.

Feature Importance with ExplainableForecaster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``ExplainableForecaster`` mixin provides aggregate feature importance scores across all training data. Models implementing this mixin expose a ``feature_importances`` property returning a DataFrame with features as index and quantiles as columns:

.. code-block:: python

   from openstef_models.models import XGBoostForecaster

   # Train a model
   forecaster = XGBoostForecaster()
   forecaster.fit(data=train_data)

   # Access feature importance scores
   importance_df = forecaster.feature_importances
   print(importance_df.head())
   #                    quantile_P50  quantile_P95
   # temperature              0.35           0.38
   # hour_of_day              0.22           0.25
   # day_of_week              0.15           0.18

   # Create interactive visualization
   fig = forecaster.plot_feature_importances(quantile=Q(0.5))
   fig.show()

The ``plot_feature_importances()`` method generates an interactive treemap visualization using the built-in ``FeatureImportancePlotter``, showing relative importance with color intensity.

Per-Sample Contributions with ContributionsMixin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``ContributionsMixin`` provides per-sample feature contributions—decomposing each prediction into the contribution of each input feature. For tree-based models, this uses SHAP TreeExplainer values. For linear models, it's the coefficient times feature value:

.. code-block:: python

   from openstef_models.models import XGBoostForecaster

   # Train a model
   forecaster = XGBoostForecaster()
   forecaster.fit(data=train_data)

   # Compute per-sample contributions
   contributions = forecaster.predict_contributions(data=test_data)

   # contributions is a TimeSeriesDataset where each column represents
   # the contribution of that feature to the prediction
   print(contributions.data.head())
   #                      temperature  hour_of_day  day_of_week  ...
   # 2024-01-01 00:00:00         2.3          1.5         -0.2  ...
   # 2024-01-01 01:00:00         2.1          1.8         -0.2  ...

This per-sample decomposition is valuable for debugging unexpected predictions, understanding model behavior on specific examples, and building trust in production systems.

Compositional Design Patterns
------------------------------

The models package demonstrates OpenSTEF's compositional architecture. Rather than monolithic forecasting pipelines, you compose small, focused components:

1. **Transform composition**: Build feature engineering pipelines from domain-specific transforms
2. **Model swapping**: Replace model implementations without changing preprocessing or evaluation logic
3. **Explainability layering**: Add interpretation capabilities through mixins rather than modifying model internals

This design supports experimentation—you can test new feature engineering approaches, compare model algorithms, and add explainability without touching core library code.

See Also
--------

- :doc:`core` - Data structures and interfaces that models build upon
- :doc:`beam` - Backtesting and evaluation tools for assessing model performance