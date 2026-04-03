Models Package
===============

The ``openstef_models`` package provides the machine learning components that power OpenSTEF's forecasting capabilities. This package is organized into three main layers: feature engineering transforms, forecasting model implementations, and explainability tools. Together, these components form a compositional design where domain-specific transforms prepare data, models generate predictions, and explainability tools help interpret results.

.. note::
   [DIAGRAM: Component architecture showing three layers: transforms (energy_domain, weather_domain, time_domain, general, validation), models (XGBoostForecaster, LinearQuantileForecaster, etc.), and explainability (ContributionsMixin, ExplainableForecaster, FeatureImportancePlotter) with arrows showing data flow from TimeSeriesDataset through transforms to models to predictions]

Package Structure
-----------------

The models package builds on the core abstractions defined in ``openstef_core``. While core provides the foundational data structures like ``TimeSeriesDataset`` and ``ForecastInputDataset``, the models package implements the actual forecasting logic and feature engineering pipelines.

For information about the core data structures, see :doc:`core`. For backtesting and evaluation capabilities, see :doc:`beam`.

Feature Engineering Transforms
-------------------------------

The ``openstef_models.transforms`` module organizes feature engineering into domain-specific subpackages. Each transform implements the ``TimeSeriesTransform`` protocol, accepting and returning ``TimeSeriesDataset`` objects. This compositional design allows you to build complex feature pipelines from simple, testable components.

Domain-Specific Transform Packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Energy Domain** (``transforms.energy_domain``)

Energy-specific feature engineering for power systems:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_core import TimeSeriesDataset
   
   # Convert wind speed to wind power using standard power curve
   wind_transform = WindPowerFeatureAdder()
   data_with_power = wind_transform.transform(dataset)
   
   # Check which features were added
   print(wind_transform.features_added())  # ['wind_power_100m']

**Weather Domain** (``transforms.weather_domain``)

Weather-related feature engineering for meteorological inputs.

**Time Domain** (``transforms.time_domain``)

Temporal features like hour-of-day, day-of-week, and holiday indicators.

**General Transforms** (``transforms.general``)

Domain-agnostic transforms like clipping and scaling:

.. code-block:: python

   from openstef_models.transforms.general import Clipper
   
   # Clip features to observed ranges during training
   clipper = Clipper()
   clipper.fit(training_data)
   clipped_data = clipper.transform(test_data)

**Validation** (``transforms.validation``)

Data quality checks and validation transforms to ensure input data meets model requirements.

Transform Pipeline Pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms are designed to be composed into pipelines. Each transform is stateless or explicitly manages its fitted state:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.general import Clipper
   
   # Build a feature engineering pipeline
   transforms = [
       WindPowerFeatureAdder(),
       Clipper()
   ]
   
   # Fit transforms that need training
   for transform in transforms:
       if hasattr(transform, 'fit'):
           transform.fit(training_data)
   
   # Apply all transforms in sequence
   processed_data = training_data
   for transform in transforms:
       processed_data = transform.transform(processed_data)

Forecasting Models
------------------

The ``openstef_models.models.forecasting`` module provides implementations of the ``Forecaster`` protocol. All forecasters support multi-quantile probabilistic forecasting and can handle multiple prediction horizons.

Base Forecaster Protocol
^^^^^^^^^^^^^^^^^^^^^^^^^

Every forecaster inherits from the ``Forecaster`` base class, which defines the core interface:

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting import XGBoostForecaster
   
   # Configure forecaster with quantiles and horizons
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           LeadTime.from_string("PT15M"),
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT6H")
       ]
   )
   
   # Standard fit/predict interface
   forecaster.fit(train_data)
   predictions = forecaster.predict(test_data)
   
   # Access configuration
   print(f"Max horizon: {forecaster.max_horizon}")
   print(f"Number of quantiles: {len(forecaster.quantiles)}")

XGBoost-Based Models
^^^^^^^^^^^^^^^^^^^^

The ``XGBoostForecaster`` uses gradient boosting trees for non-linear pattern learning:

.. code-block:: python

   from openstef_models.models.forecasting import (
       XGBoostForecaster,
       XGBoostHyperParams
   )
   
   # Configure with hyperparameters
   hparams = XGBoostHyperParams(
       max_depth=6,
       learning_rate=0.1,
       n_estimators=100
   )
   
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime.from_string("PT1H")],
       hparams=hparams
   )
   
   # Fit with optional validation set
   forecaster.fit(train_data, data_val=validation_data)
   predictions = forecaster.predict(test_data)

The XGBoost implementation supports quantile regression, allowing it to produce probabilistic forecasts with uncertainty estimates.

Linear Quantile Models
^^^^^^^^^^^^^^^^^^^^^^^

For simpler patterns or when interpretability is critical, use linear models:

.. code-block:: python

   from openstef_models.models.forecasting import LinearQuantileForecaster
   
   # Linear model for fast, interpretable forecasts
   linear_forecaster = LinearQuantileForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime.from_string("PT15M")]
   )
   
   linear_forecaster.fit(train_data)
   predictions = linear_forecaster.predict(test_data)

Specialized Forecasters
^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes specialized forecasters for specific use cases:

- **MedianForecaster**: Uses historical median values, useful for baselines
- **FlatlinerForecaster**: Returns constant predictions, useful for testing
- **LGBMForecaster**: LightGBM-based alternative to XGBoost
- **GBLinearForecaster**: Linear model using XGBoost's gblinear booster

Model State Management
^^^^^^^^^^^^^^^^^^^^^^

Forecasters follow Pydantic's configuration model pattern. Immutable configuration is stored in regular fields, while mutable runtime state (like fitted models) is stored in private attributes:

.. code-block:: python

   # Configuration is immutable after creation
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime.from_string("PT1H")]
   )
   
   # Check if model has been fitted
   if not forecaster.is_fitted:
       forecaster.fit(train_data)
   
   # Underlying XGBoost model is initialized in model_post_init
   # and updated during fit()

Explainability Tools
--------------------

The ``openstef_models.explainability`` module provides tools for understanding model predictions. This is crucial for building trust in forecasting systems and debugging model behavior.

Feature Importance
^^^^^^^^^^^^^^^^^^

Models that implement ``ExplainableForecaster`` can report global feature importance:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.types import Quantile
   
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime.from_string("PT1H")]
   )
   
   forecaster.fit(train_data)
   
   # Get feature importance scores
   importance_df = forecaster.feature_importances
   print(importance_df.head())
   
   # Create interactive visualization
   fig = forecaster.plot_feature_importances(quantile=Quantile(0.5))
   fig.show()

The ``feature_importances`` property returns a DataFrame with importance scores for each feature, typically based on the model's internal metrics (like gain for tree-based models).

Per-Sample Contributions
^^^^^^^^^^^^^^^^^^^^^^^^^

Models implementing ``ContributionsMixin`` can explain individual predictions using SHAP values:

.. code-block:: python

   # Compute SHAP contributions for specific predictions
   contributions = forecaster.predict_contributions(test_data)
   
   # contributions is a TimeSeriesDataset where each feature column
   # contains its contribution to the prediction
   print(contributions.data.head())

SHAP (SHapley Additive exPlanations) values decompose each prediction into contributions from individual features, showing which features pushed the prediction higher or lower.

Visualization Tools
^^^^^^^^^^^^^^^^^^^

The ``FeatureImportancePlotter`` creates interactive treemap visualizations:

.. code-block:: python

   from openstef_models.explainability import FeatureImportancePlotter
   
   # Create plotter with importance scores
   plotter = FeatureImportancePlotter(
       feature_names=importance_df.index.tolist(),
       importance_scores=importance_df.values.tolist()
   )
   
   # Generate interactive treemap
   fig = plotter.create_treemap()
   fig.show()

These visualizations help identify which features dominate model predictions and can reveal unexpected patterns or data quality issues.

Compositional Design
--------------------

The models package is designed for composition. Transforms prepare data, models consume prepared data, and explainability tools interpret model outputs:

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.general import Clipper
   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.types import Quantile, LeadTime
   
   # 1. Feature engineering pipeline
   wind_transform = WindPowerFeatureAdder()
   clipper = Clipper()
   
   # 2. Fit transforms
   clipper.fit(train_data)
   
   # 3. Apply transforms
   train_transformed = wind_transform.transform(train_data)
   train_transformed = clipper.transform(train_transformed)
   
   # 4. Train forecaster
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime.from_string("PT1H")]
   )
   forecaster.fit(train_transformed)
   
   # 5. Generate predictions
   test_transformed = wind_transform.transform(test_data)
   test_transformed = clipper.transform(test_transformed)
   predictions = forecaster.predict(test_transformed)
   
   # 6. Explain predictions
   importance = forecaster.feature_importances
   contributions = forecaster.predict_contributions(test_transformed)

This separation of concerns makes it easy to test each component independently and swap implementations without affecting other parts of the pipeline.

Integration with Core
---------------------

The models package depends heavily on ``openstef_core`` for its data structures:

- **TimeSeriesDataset**: Input and output for transforms
- **ForecastInputDataset**: Input for forecaster training and prediction
- **ForecastDataset**: Output from forecasters containing predictions
- **Quantile** and **LeadTime**: Type-safe configuration for probabilistic forecasts

All transforms and models are designed to work seamlessly with these core types, ensuring type safety and clear contracts between components.

Next Steps
----------

- For details on core data structures, see :doc:`core`
- For backtesting and evaluation workflows, see :doc:`beam`
- For API reference, see the :doc:`/api/openstef_models` documentation