The openstef_meta Package
=========================

The ``openstef_meta`` package implements ensemble forecasting on top of the other three
OpenSTEF packages. Where ``openstef_models`` trains a single model per prediction task,
``openstef_meta`` trains *N* base forecasters in parallel and then learns how to combine
their outputs — either by fitting a weighted blend or by stacking a second-level
meta-regressor. This page covers the three central abstractions: ``EnsembleForecastingModel``,
the ``ForecastCombiner`` hierarchy, and the ``EnsembleForecastingWorkflowConfig`` preset.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd

For the building blocks that ``openstef_meta`` depends on — validated datasets, transform
pipelines, and individual model presets — see the :doc:`core` and :doc:`models` sibling
pages.


How the ensemble pipeline works
--------------------------------

``EnsembleForecastingModel`` is a sibling of ``ForecastingModel`` from ``openstef_models``;
both inherit from ``BaseForecastingModel`` in ``openstef_core``, but the ensemble variant
is *not* a subclass of the single-model variant. Its training loop has two explicit phases:

1. **Fit base forecasters.** Each base forecaster is trained on the historical
   ``TimeSeriesDataset``. Their in-sample predictions are collected into an
   ``EnsembleForecastDataset`` — a dataset whose features are the per-forecaster,
   per-quantile predictions rather than raw input features.

2. **Fit the combiner.** The ``ForecastCombiner`` is trained on that
   ``EnsembleForecastDataset``. It learns, for every quantile, how to map the base
   forecasters' outputs to a single final prediction.

At inference time the same two-stage flow runs in sequence: base forecasters predict
first, then the combiner aggregates.

A shared ``preprocessing`` transform pipeline (inherited from ``BaseForecastingModel``)
runs *before* any base forecaster sees the data. Per-forecaster transforms can be added
on top via ``model_specific_preprocessing``, so each base model can still receive a
customised view of the features.

.. note::

   The ``cutoff_history`` parameter is important when base forecasters use lag-based
   features. It controls how much historical context is retained when slicing the dataset
   for each forecaster, preventing look-ahead leakage across the two training phases.


``ForecastCombiner`` — the ABC
-------------------------------

``ForecastCombiner`` is an abstract base class defined in
``openstef_meta.models.forecast_combiners``. It extends both ``BaseConfig`` (Pydantic
configuration) and ``Predictor``, so a combiner is simultaneously a configuration object
and a trainable predictor. The interface is intentionally narrow:

.. code-block:: python

   from openstef_meta.models.forecast_combiners import ForecastCombiner

   # ForecastCombiner exposes:
   #   .fit(data, data_val, additional_features)  -> None
   #   .predict(data, additional_features)        -> ForecastDataset
   #   .is_fitted                                 -> bool
   #   .hparams                                   -> HyperParams
   #   .max_horizon                               -> LeadTime

Concrete implementations only need to supply the fitting and prediction logic; horizon
management, explainability hooks (``ExplainableForecaster``), and serialisation are
handled by the base class.

Two concrete combiners ship with the package.


WeightsCombiner
^^^^^^^^^^^^^^^

``WeightsCombiner`` learns a *per-quantile weighted blend* of the base forecasters'
predictions. The underlying blending model is configurable: XGBoost, LightGBM, Random
Forest, or Logistic Regression are all available through their respective hyperparameter
dataclasses.

.. code-block:: python

   from openstef_meta.models.forecast_combiners import (
       WeightsCombiner,
       XGBCombinerHyperParams,
       LGBMCombinerHyperParams,
       RFCombinerHyperParams,
       LogisticCombinerHyperParams,
   )

   # Use LightGBM as the blending model
   combiner = WeightsCombiner(hparams=LGBMCombinerHyperParams())

The hyperparameter dataclasses follow the same pattern as model hyperparameters in
``openstef_models`` — they are Pydantic models, so fields can be overridden at
construction time and validated automatically.


StackingCombiner
^^^^^^^^^^^^^^^^

``StackingCombiner`` trains a *separate meta-regressor per quantile* on top of the base
forecasters' predictions. This is a classic stacking approach: the meta-regressor sees
the full distribution of base forecaster outputs and can learn non-linear relationships
between them.

.. code-block:: python

   from openstef_meta.models.forecast_combiners import StackingCombiner

   combiner = StackingCombiner()

Because each quantile gets its own meta-regressor, ``StackingCombiner`` is more
expressive than ``WeightsCombiner`` but requires more training data to avoid overfitting.
Use ``WeightsCombiner`` when base forecasters are already well-calibrated and you want a
lightweight, interpretable blend; use ``StackingCombiner`` when the base forecasters
disagree substantially and you have enough held-out data for the second stage.


Assembling an ``EnsembleForecastingModel``
-------------------------------------------

The model is configured as a Pydantic object. Base forecasters are supplied as a
dictionary keyed by name, and the combiner is passed as a field.

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
   from openstef_meta.models.forecast_combiners import WeightsCombiner, LGBMCombinerHyperParams
   from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig

   # Build two base forecasters with different feature sets
   xgb_forecaster_config = ForecastingWorkflowConfig(model_type="xgb")
   lgbm_forecaster_config = ForecastingWorkflowConfig(model_type="lgbm")

   ensemble = EnsembleForecastingModel(
       forecaster_configs={
           "xgb": xgb_forecaster_config,
           "lgbm": lgbm_forecaster_config,
       },
       combiner=WeightsCombiner(hparams=LGBMCombinerHyperParams()),
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
   )

Training follows the standard ``BaseForecastingModel`` interface:

.. code-block:: python

   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   # dataset: a TimeSeriesDataset loaded via openstef_core utilities
   fit_result = ensemble.fit(data=dataset)

   # fit_result.component_fit_results contains per-forecaster ModelFitResult objects
   for name, result in fit_result.component_fit_results.items():
       print(name, result.metrics_to_flat_dict())

The returned ``EnsembleModelFitResult`` wraps both the combiner's fit metrics and a
``component_fit_results`` dictionary so you can inspect each base forecaster's
performance independently.


``EnsembleForecastingWorkflowConfig`` and the preset factory
-------------------------------------------------------------

For most use cases you do not need to assemble ``EnsembleForecastingModel`` by hand.
The ``openstef_meta.presets`` module provides ``EnsembleForecastingWorkflowConfig`` — a
``BaseConfig`` subclass that mirrors the ``ForecastingWorkflowConfig`` preset in
``openstef_models`` but adds ensemble-specific fields — and a factory function
``create_ensemble_forecasting_workflow`` that wires everything together into a
``CustomForecastingWorkflow`` ready for execution by ``openstef_beam``.

.. code-block:: python

   from openstef_meta.presets import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )
   from openstef_meta.models.forecast_combiners import StackingCombiner

   config = EnsembleForecastingWorkflowConfig(
       forecaster_configs={
           "xgb": ForecastingWorkflowConfig(model_type="xgb"),
           "lgbm": ForecastingWorkflowConfig(model_type="lgbm"),
           "linear": ForecastingWorkflowConfig(model_type="linear"),
       },
       combiner=StackingCombiner(),
       quantiles=[Quantile(0.05), Quantile(0.5), Quantile(0.95)],
   )

   workflow = create_ensemble_forecasting_workflow(config)

The resulting ``workflow`` object is a ``CustomForecastingWorkflow`` that plugs directly
into the Beam-based execution layer described on the :doc:`beam` page. Evaluation metrics
— including ``R2Provider`` and ``ObservedProbabilityProvider`` — are configured
automatically by the preset, matching the metric suite used in the single-model workflow.

.. note::

   ``EnsembleForecastingWorkflowConfig`` imports metric providers from
   ``openstef_beam.evaluation``, which means ``openstef_beam`` is a runtime dependency
   of ``openstef_meta``. The dependency graph therefore flows:
   ``openstef_meta`` → ``openstef_beam`` → ``openstef_models`` → ``openstef_core``.


Dependency relationships
-------------------------

``openstef_meta`` sits at the top of the package dependency graph and relies on all
three other packages:

- **openstef_core** — ``BaseForecastingModel``, ``TimeSeriesDataset``,
  ``TransformPipeline``, and the shared type system (``Quantile``, ``LeadTime``).
- **openstef_models** — individual ``Forecaster`` implementations and
  ``ForecastingWorkflowConfig`` presets used as base forecaster configurations.
- **openstef_beam** — the ``CustomForecastingWorkflow`` execution runtime and
  evaluation metric providers consumed by the preset factory.

This layering means you can use ``EnsembleForecastingModel`` standalone (without Beam)
by constructing it directly, but the ``presets`` module requires the full stack.

For dataset construction and transform utilities, see :doc:`core`. For the individual
model types available as base forecasters, see :doc:`models`. For how workflows are
executed at scale, see :doc:`beam`.