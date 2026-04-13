The Models Package
==================

The ``openstef-models`` package is the forecasting heart of OpenSTEF. It provides
everything needed to go from raw time series data to a calibrated probabilistic
forecast: domain-specific feature engineering transforms, concrete forecaster
implementations, a high-level orchestration layer, and SHAP-based explainability
tools. This page explains how those layers are designed and how they compose.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

For the ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` types that flow
through this package, see the :doc:`core` sibling page. For backtesting and
evaluation of trained models, see :doc:`beam`.

---

The Transforms Module
---------------------

Feature engineering in OpenSTEF is built around a single abstract base class,
``TimeSeriesTransform``, defined in ``openstef-core``. Every transform follows
the scikit-learn convention: a ``fit`` phase that learns parameters from training
data, and a ``transform`` phase that applies them. Transforms are stateless until
fitted, making them safe to serialise alongside a trained model.

The ``openstef_models.transforms`` package organises concrete implementations
into five domain subpackages:

- **validation** — sanity checks and outlier detection before features are built.
- **general** — domain-agnostic utilities such as ``Clipper``, which constrains
  feature values to the min/max range observed during training.
- **time_domain** — calendar and lag features (holidays, day-of-week encodings,
  configurable lag windows).
- **weather_domain** — transforms that derive meteorological features from raw
  weather observations or forecasts.
- **energy_domain** — physics-informed transforms such as ``WindPowerFeatureAdder``,
  which converts wind speed to estimated wind power using a power curve model.

Composing Transforms into a Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms are composed using ``TransformPipeline``, which runs each step in
sequence, passing the output of one transform as the input to the next. During
``fit``, each step calls ``fit_transform`` so that later transforms see already-
processed data. During ``predict``, only ``transform`` is called, preserving the
parameters learned at training time.

.. code-block:: python

   from openstef_models.transforms import time_domain, general
   from openstef_core.transforms.pipeline import TransformPipeline

   pipeline = TransformPipeline(
       transforms=[
           time_domain.HolidayFeatureAdder(country="NL"),
           time_domain.LagTransform(lags=[1, 2, 7, 14]),
           general.Clipper(),
       ]
   )

   # During training
   pipeline.fit(train_dataset)
   train_features = pipeline.transform(train_dataset)

   # During inference — same parameters, no re-fitting
   live_features = pipeline.transform(live_dataset)

The ``FeaturePipeline`` wrapper (used inside ``ForecastingModel``) extends this
pattern to handle the bookkeeping between preprocessing and the forecaster: it
tracks which columns are features versus the target, and manages the
``cutoff_history`` offset that discards the initial rows made invalid by lag
features.

.. note::

   When using lag-based transforms you must set ``cutoff_history`` on the
   ``ForecastingModel`` to match the longest lag in your pipeline. For example,
   a 14-day lag creates 14 days of ``NaN`` rows at the start of the training
   window. OpenSTEF cannot infer this automatically because the lag length is
   encoded inside the transform, not in the model's hyperparameters.

---

The Models Module
-----------------

The models layer sits above the transforms layer. It provides two levels of
abstraction:

1. **Forecaster** — a low-level interface that operates on ``ForecastInputDataset``
   (a pre-engineered feature matrix). Implementations include ``LGBMForecaster``,
   ``LGBMLinearForecaster``, and ``ConstantMedianForecaster``.

2. **ForecastingModel** — a high-level pipeline that owns a ``FeaturePipeline``
   (preprocessing), a ``Forecaster``, and optional postprocessing. It accepts
   raw ``TimeSeriesDataset`` objects and handles the full data flow internally.

This two-level design keeps the forecasters focused and testable in isolation,
while ``ForecastingModel`` provides the ergonomic entry point for end-to-end use.

Forecaster Implementations
^^^^^^^^^^^^^^^^^^^^^^^^^^^

All forecasters share the ``Forecaster`` interface: ``fit``, ``predict``,
``is_fitted``, ``quantiles``, and ``max_horizon``. Forecasters that support SHAP
explanations additionally implement ``ExplainableForecaster``, which adds
``predict_contributions`` and the ``feature_importances`` property.

``LGBMForecaster`` is the primary production forecaster. It wraps a
``MultiQuantileRegressor`` backed by LightGBM, producing simultaneous predictions
at multiple quantile levels (e.g. P10, P50, P90) in a single pass. Key
configuration options include:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )

   forecaster = LGBMForecaster(
       hyperparams=LGBMHyperParams(n_estimators=500, learning_rate=0.05),
       device="cpu",
       n_jobs=4,
       early_stopping_rounds=50,
       random_state=42,
   )

``LGBMLinearForecaster`` provides an alternative that uses LightGBM's linear tree
booster, which can be more interpretable for datasets with strong linear
relationships. ``ConstantMedianForecaster`` is a simple baseline that always
predicts the median of the training target — useful for sanity-checking pipelines
and as a benchmark in evaluation.

Building a Complete Pipeline with ForecastingModel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ForecastingModel`` is the recommended entry point for most use cases. It
accepts a ``FeaturePipeline`` for preprocessing, a ``Forecaster``, and optional
postprocessing transforms, then orchestrates the full train/predict lifecycle:

.. code-block:: python

   from datetime import timedelta

   import numpy as np
   import pandas as pd

   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )
   from openstef_models.transforms.pipeline import FeaturePipeline
   from openstef_models.transforms.time_domain import HolidayFeatureAdder, LagTransform
   from openstef_models.transforms.general import Clipper

   # Build the feature engineering pipeline
   feature_pipeline = FeaturePipeline(
       transforms=[
           HolidayFeatureAdder(country="NL"),
           LagTransform(lags=[1, 2, 7, 14]),
           Clipper(),
       ]
   )

   # Assemble the full forecasting model
   model = ForecastingModel(
       forecaster=LGBMForecaster(
           hyperparams=LGBMHyperParams(n_estimators=300),
       ),
       preprocessing=feature_pipeline,
       quantiles=[0.10, 0.50, 0.90],
       max_horizon=timedelta(hours=48),
       cutoff_history=timedelta(days=14),  # matches longest lag
   )

   # Train — accepts a raw TimeSeriesDataset
   fit_result = model.fit(
       data=train_dataset,
       data_val=val_dataset,
   )

   # Predict — returns a ForecastDataset with one column per quantile
   forecast = model.predict(live_dataset)

The ``ModelFitResult`` returned by ``fit`` carries per-split metrics and, for
ensemble models, per-component results. Call ``fit_result.metrics_to_flat_dict()``
to obtain a flat mapping suitable for experiment tracking systems.

---

Explainability Tools
--------------------

Understanding *why* a model produced a particular forecast is important for
operator trust and debugging. OpenSTEF provides SHAP-based explainability through
the ``ExplainableForecaster`` interface, implemented by ``LGBMForecaster`` and
``LGBMLinearForecaster``.

There are two complementary entry points:

``predict_contributions``
   Returns a ``TimeSeriesDataset`` where each column is the SHAP contribution of
   one input feature to the median-quantile forecast, plus a ``bias`` column
   representing the model's base value. Contributions sum to the median prediction.

``feature_importances``
   Returns a ``pd.DataFrame`` of aggregated SHAP importances across the training
   set — useful for feature selection and pipeline auditing.

Both methods are also available on ``ForecastingModel`` directly, which routes
them through the preprocessing pipeline so you can pass raw ``TimeSeriesDataset``
objects rather than pre-engineered feature matrices:

.. code-block:: python

   # Compute per-timestep SHAP contributions
   contributions = model.predict_contributions(
       data=live_dataset,
       forecast_start=pd.Timestamp("2024-06-01 00:00"),
   )
   # contributions is a TimeSeriesDataset; each column is one feature's SHAP value

   # Inspect global feature importance
   importances = model.get_explainable_components()["forecaster"].feature_importances()
   print(importances.sort_values("importance", ascending=False).head(10))

.. note::

   ``predict_contributions`` is only available when the underlying ``Forecaster``
   implements ``ExplainableForecaster``. Calling it on a ``ForecastingModel``
   backed by ``ConstantMedianForecaster`` raises ``NotImplementedError``. Check
   ``model.get_explainable_components()`` to discover which components support
   explanations at runtime.

---

Design Patterns and Extension Points
-------------------------------------

The package is designed for composition rather than inheritance. A few patterns
are worth understanding before extending it:

**Transforms are stateful, pipelines are not.** Each ``TimeSeriesTransform``
instance owns its fitted state. A ``TransformPipeline`` is simply an ordered
container — it has no state of its own beyond the list of transforms it holds.
This makes it straightforward to swap, add, or remove steps without touching the
rest of the pipeline.

**Forecasters are decoupled from feature engineering.** A ``Forecaster`` operates
on ``ForecastInputDataset``, which is already a clean feature matrix. This means
you can test a forecaster against any feature set without modifying the forecaster
code, and you can swap forecasters without changing the feature pipeline.

**Hyperparameters are typed Pydantic models.** Each forecaster exposes a
``HyperParams`` class (e.g. ``LGBMHyperParams``) that validates configuration at
construction time. This makes hyperparameter serialisation and deserialisation
straightforward and catches misconfiguration early.

**Energy-domain transforms encode physics.** Rather than treating energy
forecasting as a generic regression problem, the ``energy_domain`` subpackage
encodes domain knowledge directly into the feature engineering layer. For example,
``WindPowerFeatureAdder`` derives power estimates from wind speed before the
model ever sees the data, reducing the burden on the learner to discover
non-linear physical relationships from scratch.

To implement a custom transform, subclass ``TimeSeriesTransform`` from
``openstef-core``, implement ``fit`` (if stateful) and ``transform``, and declare
``features_added`` to advertise which new columns your transform produces. The
transform can then be dropped into any ``TransformPipeline`` or ``FeaturePipeline``
without further changes.

---

.. seealso::

   - :doc:`core` — ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and the
     base transform interfaces that this package builds on.
   - :doc:`beam` — backtesting, regression testing, and metric evaluation for
     models trained with this package.