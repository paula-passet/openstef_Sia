Models Package
===============

The ``openstef_models`` package provides the machine learning layer of OpenSTEF. It implements feature engineering transforms organized by domain, forecasting model implementations, and explainability tools. This package builds on ``openstef_core`` data structures and follows a compositional design where transforms, models, and explainability components work together seamlessly.

.. note::
   [DIAGRAM: Component architecture showing three layers: transforms (energy_domain, weather_domain, time_domain, general, validation) feeding into models (forecasting implementations: XGBoost, LightGBM, LGBMLinear), with explainability (ContributionsMixin, ExplainableForecaster, FeatureImportancePlotter) as a cross-cutting layer]

Package Structure
-----------------

The package is organized into three main modules:

- **transforms**: Feature engineering pipelines organized by domain
- **models**: Forecasting model implementations
- **explainability**: Tools for model interpretation and feature importance

Transforms Module
-----------------

The transforms module provides feature engineering utilities organized into domain-specific subpackages. Each transform operates on ``TimeSeriesDataset`` objects from ``openstef_core`` and follows the ``Transform`` protocol with ``fit``, ``transform``, and ``fit_transform`` methods.

Domain Organization
^^^^^^^^^^^^^^^^^^^

Transforms are grouped by their domain of application:

- **energy_domain**: Energy-specific features like wind power calculations
- **weather_domain**: Weather-related feature engineering
- **time_domain**: Temporal features (hour of day, day of week, holidays)
- **general**: Domain-agnostic transforms like clipping and scaling
- **validation**: Data quality and validation transforms

Each transform inherits from ``TimeSeriesTransform`` and can be composed into pipelines using ``TransformPipeline``.

Example: Wind Power Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``WindPowerFeatureAdder`` demonstrates domain-specific feature engineering:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   
   # Create transform
   wind_transform = WindPowerFeatureAdder()
   
   # Fit and transform data
   # Assumes dataset has wind speed columns
   transformed_data = wind_transform.fit_transform(data=input_dataset)
   
   # Check which features were added
   added_features = wind_transform.features_added()
   print(f"Added features: {added_features}")

Transform Pipelines
^^^^^^^^^^^^^^^^^^^

Multiple transforms can be chained together using ``TransformPipeline``. The pipeline fits each transform sequentially on the output of the previous transform:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.general import Clipper
   from openstef_models.transforms.validation import DataValidator
   
   # Create a pipeline of transforms
   pipeline = TransformPipeline[TimeSeriesDataset](
       transforms=[
           DataValidator(),
           WindPowerFeatureAdder(),
           Clipper(),
       ]
   )
   
   # Fit all transforms in sequence
   pipeline.fit(data=training_data)
   
   # Transform new data
   processed_data = pipeline.transform(data=test_data)

The ``Clipper`` transform clips feature values to their observed ranges during training, preventing extrapolation issues. The ``DataValidator`` ensures data quality before feature engineering.

Models Module
-------------

The models module provides forecasting implementations built on gradient boosting frameworks. All models support probabilistic forecasting through quantile regression and operate on ``ForecastInputDataset`` objects.

Forecasting Implementations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides three main forecasting implementations:

- **XGBoostForecaster**: XGBoost-based gradient boosting trees
- **LGBMForecaster**: LightGBM-based gradient boosting trees  
- **LGBMLinearForecaster**: LightGBM with linear models

All forecasters implement a common interface with ``fit`` and ``predict`` methods and support multi-quantile forecasting for probabilistic predictions.

Example: Training a Forecaster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.validation import Quantile
   
   # Create forecaster with quantiles
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )
   
   # Fit on training data
   # training_data is a ForecastInputDataset
   forecaster.fit(data=training_data)
   
   # Make predictions
   predictions = forecaster.predict(data=test_data)
   
   # predictions is a TimeSeriesDataset with columns for each quantile

The forecaster automatically trains separate models for each quantile, enabling probabilistic forecasts with prediction intervals.

Model Selection
^^^^^^^^^^^^^^^

Choose a forecasting implementation based on your requirements:

- **XGBoostForecaster**: Good general-purpose choice, widely used and well-tested
- **LGBMForecaster**: Faster training and lower memory usage than XGBoost
- **LGBMLinearForecaster**: When linear relationships dominate or interpretability is critical

All models support the same interface, making it easy to experiment with different implementations.

Explainability Module
---------------------

The explainability module provides tools for understanding model predictions through feature importance and contribution analysis. This is critical for building trust in forecasting systems and debugging model behavior.

Feature Importance
^^^^^^^^^^^^^^^^^^

The ``ExplainableForecaster`` mixin adds feature importance capabilities to forecasting models. Most gradient boosting models in OpenSTEF implement this interface:

.. code-block:: python

   # After training a forecaster
   forecaster.fit(data=training_data)
   
   # Get feature importance scores
   importance_df = forecaster.feature_importances
   print(importance_df.head())
   
   # Create interactive visualization
   fig = forecaster.plot_feature_importances(quantile=Quantile(0.5))
   fig.show()

The ``feature_importances`` property returns a DataFrame with importance scores for each feature. The ``plot_feature_importances`` method creates an interactive treemap visualization using the ``FeatureImportancePlotter``.

Per-Sample Contributions
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``ContributionsMixin`` enables SHAP-style contribution analysis, showing how each feature contributed to individual predictions:

.. code-block:: python

   # Compute contributions for specific predictions
   contributions = forecaster.predict_contributions(data=test_data)
   
   # contributions is a TimeSeriesDataset where each column shows
   # the contribution of that feature to the prediction

This is particularly useful for understanding why a model made a specific prediction at a particular time, enabling detailed analysis of forecast behavior.

Visualization Tools
^^^^^^^^^^^^^^^^^^^

The ``FeatureImportancePlotter`` creates interactive treemap visualizations that make it easy to understand which features drive model predictions:

.. code-block:: python

   from openstef_models.explainability import FeatureImportancePlotter
   
   # Create plotter with importance data
   plotter = FeatureImportancePlotter(
       importance_data=importance_df
   )
   
   # Generate interactive plot
   fig = plotter.create_treemap()
   fig.show()

The treemap groups features hierarchically, making it easy to see which feature categories (weather, temporal, energy-domain) are most important.

Compositional Design
--------------------

The models package demonstrates OpenSTEF's compositional architecture. Transforms operate on core data structures, models consume transformed data, and explainability tools work with fitted models. This separation of concerns makes the codebase maintainable and extensible.

A typical workflow combines all three layers:

.. code-block:: python

   # 1. Feature engineering
   transform_pipeline = TransformPipeline[TimeSeriesDataset](
       transforms=[
           DataValidator(),
           WindPowerFeatureAdder(),
           Clipper(),
       ]
   )
   
   # 2. Model training
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )
   
   # 3. Fit pipeline and model
   transformed_training = transform_pipeline.fit_transform(data=training_data)
   forecaster.fit(data=transformed_training)
   
   # 4. Make predictions
   transformed_test = transform_pipeline.transform(data=test_data)
   predictions = forecaster.predict(data=transformed_test)
   
   # 5. Explain results
   importance = forecaster.feature_importances
   contributions = forecaster.predict_contributions(data=transformed_test)

This pattern keeps concerns separated while enabling powerful end-to-end forecasting workflows.

Related Topics
--------------

- See :doc:`core` for details on ``TimeSeriesDataset`` and ``ForecastInputDataset`` data structures
- See :doc:`beam` for backtesting and evaluation metrics that work with these models
- See the API reference for complete details on all transforms and models