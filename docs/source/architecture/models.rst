The Models Package
==================

.. note::
   This page covers the ``openstef_models`` package in depth: how feature engineering
   transforms are structured, how forecasting model implementations are composed, and
   how the explainability layer works. For the ``TimeSeriesDataset`` and core data
   abstractions that these components operate on, see the :doc:`core` sibling page.
   For backtesting and metrics utilities, see :doc:`beam`.

The ``openstef_models`` package is the algorithmic heart of OpenSTEF. It organises
three distinct concerns — *feature engineering*, *forecasting*, and *explainability* —
into separate sub-packages that are designed to compose cleanly. Understanding how
these layers relate to one another is the key to extending or customising OpenSTEF
for a new use case.

.. note::
   [DIAGRAM: Component-level diagram showing three horizontal layers. Bottom layer:
   ``openstef_core`` (TimeSeriesDataset, VersionedTimeSeriesDataset). Middle layer:
   ``openstef_models.transforms`` (five domain sub-packages: validation, general,
   time_domain, weather_domain, energy_domain) feeding into ``TransformPipeline``.
   Top layer: ``openstef_models.models`` (Forecaster implementations) and
   ``openstef_models.explainability`` (ExplainableForecaster, ContributionsMixin,
   FeatureImportancePlotter). Arrows show data flowing upward through the layers,
   with the explainability layer drawing back down into the models layer.]


The Transforms Layer
--------------------

Feature engineering in OpenSTEF is built around two abstractions: ``TimeSeriesTransform``
and ``TransformPipeline``. Every transform is a stateful, serialisable object that
implements a ``fit`` / ``transform`` / ``fit_transform`` lifecycle — the same pattern
used by scikit-learn estimators, but typed against ``TimeSeriesDataset`` rather than
NumPy arrays.

A transform is considered *stateless* by default. Subclasses that need to learn
parameters from data (for example, a ``Clipper`` that records observed min/max values)
override ``is_fitted`` and ``fit`` accordingly. The base class provides a safe
``fit_transform`` shortcut that skips fitting when the transform is already fitted.

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms import general, time_domain

   # A stateless transform — no fitting required
   datetime_adder = time_domain.DatetimeFeaturesAdder(onehot_encode=False)

   # A stateful transform — learns clipping bounds from training data
   clipper = general.Clipper()

   # Calling fit_transform on a stateless transform is safe and idempotent
   dataset_with_dt = datetime_adder.fit_transform(data=training_dataset)

The five transform sub-packages map to distinct feature domains:

- **validation** — data quality checks and NaN handling (``NaNDropper``, ``Imputer``)
- **general** — domain-agnostic utilities (``Clipper``, ``Selector``, ``SampleWeighter``)
- **time_domain** — calendar and lag features (``DatetimeFeaturesAdder``, ``HolidayFeatureAdder``)
- **weather_domain** — meteorological features derived from weather inputs
- **energy_domain** — power-system-specific features such as wind power curves

The ``energy_domain.WindPowerFeatureAdder`` is a good example of a domain-specific
transform. It takes raw wind speed columns from the dataset and derives wind power
estimates using a configurable power curve, exposing the names of the columns it adds
through the ``features_added()`` method. This convention — every transform declares
what it adds — makes it straightforward to build downstream selectors that exclude
or include specific feature groups.


Composing Transforms with TransformPipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual transforms become useful preprocessing recipes when assembled into a
``TransformPipeline``. The pipeline applies transforms sequentially, passing the
output of each step as the input to the next. Crucially, it fits each transform on
the *intermediate* output of the previous step, so a ``Clipper`` that follows an
``Imputer`` learns its bounds on already-imputed data.

.. code-block:: python

   from openstef_models.transforms.general import Clipper, NaNDropper, Imputer
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.pipeline import TransformPipeline

   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           WindPowerFeatureAdder(),
           DatetimeFeaturesAdder(onehot_encode=False),
           HolidayFeatureAdder(country_code="NL"),
           Imputer(imputation_strategy="mean"),
           NaNDropper(),
           Clipper(),
       ]
   )

   # Fit on training data — each transform learns from the previous step's output
   preprocessing.fit(data=training_dataset)

   # Transform new data using the fitted pipeline
   processed = preprocessing.transform(data=inference_dataset)

The pipeline is serialisable via pickle, which is important for production deployments
where a fitted preprocessing pipeline must be persisted alongside the model weights.
A ``TransformPipeline`` with an empty ``transforms`` list is a valid no-op, making it
safe to use as a default in configurations that do not require preprocessing.

.. note::
   The ``is_fitted`` property on ``TransformPipeline`` returns ``True`` only when
   *all* constituent transforms report themselves as fitted. This means you can
   always check pipeline readiness with a single attribute access rather than
   iterating over individual steps.


The Models Layer
----------------

The ``openstef_models.models`` sub-package provides concrete forecasting
implementations that sit on top of the transforms layer. All forecasters share a
common interface through ``BaseForecastingModel``, which enforces three key contracts:
the model declares the ``quantiles`` it produces, the ``max_horizon`` it supports, and
the ``hyperparams`` it accepts.

The library ships with several ready-to-use forecasters:

- **XGBoostForecaster** — gradient-boosted trees via XGBoost; supports SHAP-based
  per-sample contributions through ``ContributionsMixin``
- **LGBMForecaster** — LightGBM-backed multi-quantile regressor; configurable for
  CPU or CUDA computation
- **LGBMLinearForecaster** — LightGBM with a linear booster; useful when
  interpretability or regularisation is a priority
- **GBLinearForecaster** — XGBoost with a linear booster; contributions are
  decomposed as coefficient × feature value

Each forecaster is configured through a typed ``HyperParams`` model, which means
hyperparameter validation happens at construction time rather than at fit time.

.. code-block:: python

   from openstef_models.models import XGBoostForecaster, LGBMForecaster
   from openstef_models.models.xgboost import XGBoostHyperParams

   forecaster = XGBoostForecaster(
       hyperparams=XGBoostHyperParams(n_estimators=500, learning_rate=0.05),
       quantiles=[0.1, 0.5, 0.9],
       horizons=[1, 4, 24],   # lead times in hours
   )

   fit_result = forecaster.fit(data=training_dataset)

   # fit_result carries per-split metrics and can be flattened for logging
   metrics = fit_result.metrics_to_flat_dict()

The ``ModelFitResult`` returned by ``fit`` is more than a status object. It carries
per-split metrics for each quantile and horizon, and for ensemble models it exposes
``component_fit_results()`` — a dictionary of per-member fit results that lets you
inspect how each base model performed independently.


Ensemble Models and Compositional Design
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ensemble design in ``openstef_models`` is a direct expression of the
compositional philosophy that runs through the whole package. An
``EnsembleForecastingModel`` holds a dictionary of named base forecasters, each with
its own preprocessing pipeline, and a ``ForecastCombiner`` that merges their
individual predictions into a single output.

This means you can mix forecaster types within a single ensemble — for example,
pairing an ``XGBoostForecaster`` (which handles non-linear interactions well) with an
``LGBMLinearForecaster`` (which extrapolates more gracefully outside the training
distribution). The combiner learns the optimal weighting from held-out validation
data during the fit phase.

.. code-block:: python

   from openstef_models.models.forecasting_model import BaseForecastingModel

   # Retrieve per-component results after fitting an ensemble
   ensemble_result = ensemble_model.fit(data=training_dataset)

   for component_name, component_result in ensemble_result.component_fit_results().items():
       print(component_name, component_result.metrics_to_flat_dict())


The Explainability Layer
------------------------

Interpretability is a first-class concern in OpenSTEF. The
``openstef_models.explainability`` sub-package provides two complementary
mechanisms: aggregate *feature importance* and per-sample *feature contributions*.

**ExplainableForecaster** is a mixin that any forecaster can implement to expose
``feature_importances()`` — a ``DataFrame`` indexed by feature name with quantile
columns (e.g. ``quantile_P50``, ``quantile_P95``). Values are normalised importance
scores that sum to 1.0 across features. The mixin also provides a
``plot_feature_importances()`` convenience method that returns a Plotly ``Figure``
containing an interactive treemap, so you can visualise the importance distribution
without writing any plotting code yourself.

.. code-block:: python

   # feature_importances() returns a normalised DataFrame
   importances = forecaster.feature_importances()
   print(importances.head())

   # Built-in interactive treemap — no external plotting code needed
   fig = forecaster.plot_feature_importances(quantile=0.5)
   fig.show()

**ContributionsMixin** goes further by providing per-sample decomposition. Calling
``predict_contributions(data)`` returns a ``TimeSeriesDataset`` where each column is
a feature (or, for ensembles, a base model name) and each row is a timestep. The
value in each cell is the additive contribution of that feature to the prediction at
that moment. A ``bias`` column may also be present, representing the model intercept.

The implementation behind ``predict_contributions`` differs by model type:

- For ``XGBoostForecaster``, it uses SHAP ``TreeExplainer`` values.
- For ``GBLinearForecaster`` and ``LGBMLinearForecaster``, it decomposes predictions
  as coefficient × feature value.
- For ensemble models, each cell represents a base model's weighted contribution to
  the combined forecast.

.. code-block:: python

   from openstef_models.models import XGBoostForecaster

   # XGBoostForecaster implements both ExplainableForecaster and ContributionsMixin
   contributions = forecaster.predict_contributions(data=inference_input)

   # contributions is a TimeSeriesDataset — inspect as a DataFrame
   contributions_df = contributions.data
   print(contributions_df.columns.tolist())   # ['wind_speed', 'temperature', ..., 'bias']

.. note::
   Not all forecasters implement ``ContributionsMixin``. If you call
   ``predict_contributions`` on a model that does not support it, a
   ``NotImplementedError`` is raised with a descriptive message. Check whether your
   forecaster class inherits from ``ContributionsMixin`` before calling this method
   in production code.


How the Layers Compose
-----------------------

The three layers — transforms, models, explainability — are designed to be used
together but remain independently testable. A ``TransformPipeline`` has no knowledge
of the forecaster that will consume its output; a forecaster has no knowledge of which
transforms produced its input. This separation makes it straightforward to:

- Swap a preprocessing pipeline without retraining the model (for inference-time
  feature changes that do not affect the model's feature space).
- Test a new transform in isolation by calling ``fit_transform`` on a
  ``TimeSeriesDataset`` and inspecting the result directly.
- Attach the explainability layer to any forecaster that implements the relevant
  mixin, regardless of how it was trained.

In practice, the ``ForecastingModel`` class in ``openstef_models.models.forecasting_model``
acts as the integration point: it holds a forecaster, a preprocessing pipeline, and
exposes the full ``fit`` → ``predict`` → ``predict_contributions`` workflow as a
single coherent object. This is the class you will interact with most often when
building end-to-end forecasting workflows with OpenSTEF.