Models Package (``openstef_models``)
=====================================

The ``openstef_models`` package contains OpenSTEF's feature engineering transforms, forecasting model implementations, and explainability tools. It sits between the foundational ``openstef_core`` layer (which defines base abstractions like ``TimeSeriesDataset`` and ``Transform``) and the higher-level orchestration in ``openstef_beam``. This page explores the three main modules within the package: **transforms**, **models**, and **explainability**.

.. note:: [DIAGRAM: Component diagram showing openstef_models with three layers: transforms (bottom) feeding into models (middle), with explainability (top) as mixins applied to model classes. Arrows show that transforms operate on TimeSeriesDataset from openstef_core, and models inherit from BaseForecastingModel which uses the Predictor protocol from openstef_core.]

For the foundational data structures and abstractions that this package builds on, see :doc:`core`. For how these models are orchestrated in production pipelines, see :doc:`beam`.


Transforms Module
-----------------

The ``openstef_models.transforms`` module provides feature engineering organized by domain. Each subpackage contains transforms that follow the scikit-learn-style ``fit``/``transform`` pattern defined by the ``TimeSeriesTransform`` base class in ``openstef_core``.

The five subpackages are:

- ``energy_domain`` — Features specific to energy systems (e.g., wind power curves)
- ``weather_domain`` — Weather-derived features
- ``time_domain`` — Temporal features (lags, calendar effects)
- ``general`` — Domain-agnostic transforms (e.g., clipping, scaling)
- ``validation`` — Data quality and validation transforms

Each transform implements a consistent interface:

.. code-block:: python

   from openstef_models.transforms.energy_domain.wind_power_feature_adder import (
       WindPowerFeatureAdder,
   )

   # Create a transform
   wind_transform = WindPowerFeatureAdder()

   # Fit learns parameters from training data
   wind_transform.fit(data=training_dataset)

   # Transform adds computed features to the dataset
   enriched_dataset = wind_transform.transform(data=training_dataset)

   # Inspect which columns were added
   print(wind_transform.features_added())

Transforms are stateful: the ``fit`` method learns parameters (such as observed min/max values for the ``Clipper`` transform), and ``transform`` applies the learned transformation. The ``is_fitted`` property lets you check whether a transform is ready to use.

Composing Transforms with Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual transforms are composed into pipelines using ``TransformPipeline``, which chains multiple transforms sequentially:

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TransformPipeline

   pipeline = TransformPipeline(transforms=[
       WindPowerFeatureAdder(),
       Clipper(columns=["wind_power"]),
   ])

   # Fit all transforms in sequence
   pipeline.fit(data=training_dataset)

   # Apply all transforms in sequence
   transformed = pipeline.transform(data=training_dataset)

   # Check if the entire pipeline is fitted
   assert pipeline.is_fitted

The pipeline's ``fit`` method is sequential: each transform is fit and then applied before the next transform sees the data. This ensures that downstream transforms receive the enriched dataset from upstream transforms.

This compositional design means you can mix and match transforms from different domains to build feature engineering pipelines tailored to specific forecasting tasks — solar forecasting pipelines will use different transforms than wind or load forecasting pipelines.


Models Module
-------------

The ``openstef_models.models`` subpackage contains concrete forecasting implementations. All models inherit from ``BaseForecastingModel``, which provides a shared pipeline skeleton:

1. **Preprocessing** — A ``TransformPipeline`` of transforms applied before prediction
2. **Prediction** — The core forecasting logic (model-specific)
3. **Postprocessing** — Output formatting and validation

Each model wraps a ``Forecaster`` — the component that handles the actual ML training and inference. OpenSTEF ships with several forecaster implementations:

- ``LGBMForecaster`` — LightGBM gradient boosting trees for multi-quantile forecasting
- ``LGBMLinearForecaster`` — LightGBM with linear tree leaves
- Additional forecasters for different ML backends

Forecasters follow a consistent interface:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )

   # Configure hyperparameters
   hparams = LGBMHyperParams(
       n_estimators=500,
       learning_rate=0.05,
       max_depth=8,
   )

   # Create a forecaster from hyperparameters
   forecaster = hparams.forecaster_class()

   # Fit on prepared data
   forecaster.fit(data=train_data, data_val=val_data)

   # Predict returns a ForecastDataset with quantile predictions
   forecast = forecaster.predict(data=input_data)

.. note::

   The ``cutoff_history`` parameter on ``BaseForecastingModel`` is important when using lag-based features. For example, a lag-14 transformation creates NaN values for the first 14 days of data. Set ``cutoff_history`` to exclude these incomplete rows from training.

Hyperparameter Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each forecaster type defines its own ``HyperParams`` subclass (e.g., ``LGBMHyperParams``). These are Pydantic-based configuration objects that:

- Define valid parameter ranges and defaults
- Provide a ``forecaster_class()`` method that instantiates the corresponding forecaster
- Are serializable for storage and reproducibility

This pattern keeps model configuration separate from model logic, making it straightforward to experiment with different hyperparameter settings or implement hyperparameter optimization.

Preprocessing in Models
^^^^^^^^^^^^^^^^^^^^^^^^

Each ``BaseForecastingModel`` has a ``preprocessing`` attribute — a ``TransformPipeline`` built from the transforms module. Some models also have ``model_specific_preprocessing`` for transforms that are unique to a particular forecaster within an ensemble. The test suite verifies that applying transforms through an ensemble's shared preprocessing followed by model-specific preprocessing produces the same result as applying a standalone model's full pipeline:

.. code-block:: python

   # Ensemble path: shared preprocessing -> model-specific preprocessing
   common_data = ensemble_model.preprocessing.transform(data=dataset)
   final_data = ensemble_model.model_specific_preprocessing["lgbm"].transform(
       data=common_data
   )

   # Standalone path: full preprocessing
   standalone_data = lgbm_model.preprocessing.transform(data=dataset)

   # These produce identical results
   assert final_data == standalone_data


Explainability Module
---------------------

The ``openstef_models.explainability`` module provides tools for understanding model predictions. Rather than being a separate layer, explainability is integrated directly into forecasters through mixins:

- ``ExplainableForecaster`` — Mixin providing a standardized interface for feature importance scores. Any forecaster implementing this mixin exposes a ``feature_importances`` property returning a DataFrame of importance scores.

- ``ContributionsMixin`` — Mixin for per-sample feature contributions (e.g., SHAP values). Forecasters with this mixin provide a ``predict_contributions()`` method that returns a ``TimeSeriesDataset`` with per-feature contribution columns.

- ``FeatureImportancePlotter`` — Visualization utility that creates treemap visualizations of feature importance scores.

The ``LGBMForecaster``, for example, implements both ``ExplainableForecaster`` and ``ContributionsMixin``:

.. code-block:: python

   # After fitting a model
   forecaster.fit(data=train_data)

   # Global feature importance
   importances = forecaster.feature_importances
   print(importances.head())

   # Per-sample SHAP contributions
   contributions = forecaster.predict_contributions(data=input_data)

   # Visualize importance as a treemap
   from openstef_models.explainability import FeatureImportancePlotter

   plotter = FeatureImportancePlotter(importances=importances)

The mixin approach means explainability is opt-in at the forecaster level. Not all forecasters need to support all explainability features, but those that do share a consistent API. The ``get_explainable_components()`` method on ``BaseForecastingModel`` returns a dictionary of all components that support explainability, making it easy to introspect ensemble models.


Compositional Design
--------------------

The ``openstef_models`` package demonstrates a compositional architecture where complex forecasting systems are assembled from simple, well-defined components:

- **Transforms** are small, focused units of feature engineering
- **Pipelines** compose transforms into sequential processing chains
- **Forecasters** wrap ML backends with a consistent interface
- **Explainability mixins** add interpretability without modifying core logic
- **Models** combine preprocessing pipelines with forecasters

This design makes it straightforward to:

- Add new feature transforms without modifying existing models
- Swap forecasting backends while keeping the same preprocessing
- Add explainability to new forecasters by mixing in the appropriate classes
- Test each component in isolation

The ensemble model (covered in the ``openstef_meta`` package) takes this further by composing multiple ``BaseForecastingModel`` instances with shared and model-specific preprocessing, demonstrating how the compositional pattern scales to more complex architectures.