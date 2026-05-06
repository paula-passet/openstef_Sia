The openstef_meta Package
=========================

The ``openstef_meta`` package is the top-level orchestration layer of OpenSTEF. It combines the outputs of multiple independently-trained base forecasters into a single, higher-quality ensemble prediction. Because it depends on all three other packages — ``openstef_core``, ``openstef_models``, and ``openstef_beam`` — it sits at the apex of the dependency graph and is the natural entry point for production ensemble workflows.

This page covers the three central abstractions: ``EnsembleForecastingModel``, the ``ForecastCombiner`` hierarchy, and the ``EnsembleForecastingWorkflowConfig`` preset system.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd

How the Ensemble Pipeline Works
--------------------------------

``EnsembleForecastingModel`` implements the same ``BaseForecastingModel`` interface as the single-model ``ForecastingModel`` in ``openstef_models``, so it is a *sibling*, not a subclass. Internally it runs a two-phase training procedure:

1. **Phase 1 — fit base forecasters.** Each base forecaster is trained independently on the historical ``TimeSeriesDataset``. Their in-sample predictions are collected and assembled into an ``EnsembleForecastDataset``.
2. **Phase 2 — fit the combiner.** The ``ForecastCombiner`` is trained on those stacked predictions, learning how to weight or blend them into a final ``ForecastDataset``.

At prediction time the same two steps execute in sequence: each base forecaster produces a forecast, and the combiner merges them.

Common preprocessing (the ``preprocessing`` field inherited from the base class) is applied *once* before any base forecaster sees the data. Per-forecaster transforms can be layered on top via ``model_specific_preprocessing``, keeping shared feature engineering efficient while still allowing specialisation.

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
   from openstef_meta.models.forecast_combiners import WeightsCombiner

   # Inspect the fitted model after training
   model: EnsembleForecastingModel  # obtained from a workflow

   print(model.forecaster_names)          # ['lgbm', 'gblinear']
   print(model.quantiles)                 # [Q(0.5)]
   print(model.is_fitted)                 # True

   # Per-component fit metrics are surfaced through EnsembleModelFitResult
   fit_result = model.fit(train_data)
   flat = fit_result.metrics_to_flat_dict()
   # keys are prefixed: 'lgbm_mae', 'gblinear_mae', plus combiner-level metrics

.. note::

   The ``cutoff_history`` parameter is important when base forecasters use lag-based features. Lags require a look-back window that must be present in the input data at prediction time; set ``cutoff_history`` to at least the largest lag used by any base forecaster.

The ``ForecastCombiner`` Hierarchy
------------------------------------

``ForecastCombiner`` is an abstract base class (ABC) that also inherits from ``BaseConfig`` and ``Predictor``. Any concrete combiner must implement ``fit`` and ``predict`` against the ``EnsembleForecastDataset`` type. Two production-ready implementations ship with the package.

WeightsCombiner
^^^^^^^^^^^^^^^

``WeightsCombiner`` trains a *learned* regression model whose inputs are the base forecaster predictions and whose target is the ground-truth load. The regression model itself is configurable; four hyperparameter classes are provided out of the box:

- ``LGBMCombinerHyperParams`` — LightGBM gradient boosting (default)
- ``XGBCombinerHyperParams`` — XGBoost gradient boosting
- ``RFCombinerHyperParams`` — Random Forest
- ``LogisticCombinerHyperParams`` — Logistic regression (useful for classification-style quantile problems)

Because the combiner is itself a trained model, it can learn non-linear relationships between base forecaster outputs — for example, preferring the LGBM forecaster during peak hours and the linear model during off-peak periods.

StackingCombiner
^^^^^^^^^^^^^^^^

``StackingCombiner`` implements classical model stacking: the combiner receives the raw base forecaster predictions *and* the original input features, giving it access to the full context when learning to blend. This is more expressive than ``WeightsCombiner`` but requires more data to train reliably and is slower at prediction time.

Both combiners expose ``feature_importances`` and implement ``ExplainableForecaster``, so SHAP-based explanations work uniformly across the ensemble.

.. code-block:: python

   from openstef_meta.models.forecast_combiners import (
       ForecastCombiner,
       WeightsCombiner,
       StackingCombiner,
       LGBMCombinerHyperParams,
       XGBCombinerHyperParams,
   )

   # WeightsCombiner with an XGBoost meta-learner
   combiner = WeightsCombiner(hparams=XGBCombinerHyperParams())

   # StackingCombiner with default LGBM meta-learner
   stacking_combiner = StackingCombiner()

   # Both share the same interface — swap without changing downstream code
   combiner.fit(ensemble_dataset, data_val=val_ensemble)
   forecast: ForecastDataset = combiner.predict(ensemble_dataset)

The ``EnsembleForecastingWorkflowConfig`` Preset
-------------------------------------------------

Rather than assembling ``EnsembleForecastingModel`` and its dependencies by hand, the ``presets`` module provides ``EnsembleForecastingWorkflowConfig`` — a validated Pydantic config that describes the full ensemble workflow declaratively. Passing it to ``create_ensemble_forecasting_workflow`` returns a ready-to-run ``CustomForecastingWorkflow`` (from ``openstef_models``).

Key fields and their defaults:

.. code-block:: python

   from datetime import timedelta
   from openstef_meta.presets.forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )
   from openstef_core.domain import LeadTime, Quantile as Q

   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42",
       # Ensemble strategy
       ensemble_type="learned_weights",   # or "stacking" or "rules"
       base_models=["lgbm", "gblinear"],  # base forecaster pool
       combiner_model="lgbm",             # meta-learner for WeightsCombiner
       # Forecast shape
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       sample_interval=timedelta(minutes=15),
       horizons=[LeadTime.from_string("PT48H")],
   )

   workflow = create_ensemble_forecasting_workflow(config)
   fit_result = workflow.fit(train_dataset)
   forecast = workflow.predict(input_dataset)

The ``ensemble_type`` field acts as a discriminator that selects the combiner class:

- ``"learned_weights"`` → ``WeightsCombiner`` with the ``combiner_model`` backend
- ``"stacking"`` → ``StackingCombiner``
- ``"rules"`` → a rule-based (non-learned) combiner for interpretable baselines

The ``base_models`` list accepts ``"lgbm"``, ``"gblinear"``, ``"xgboost"``, and ``"lgbm_linear"``. Adding more base models increases diversity but also training time; two to three complementary models (e.g. a tree-based and a linear model) typically give the best cost-to-accuracy trade-off.

.. note::

   ``EnsembleForecastingWorkflowConfig`` uses the same ``BaseConfig`` base class as all other OpenSTEF configs, so it serialises to and from JSON/YAML with full validation. Store configs in version control alongside model artefacts to make experiments reproducible.

Dependency Relationships
------------------------

``openstef_meta`` is intentionally thin: it adds orchestration logic on top of the three lower-level packages rather than reimplementing their functionality.

- **openstef_core** — provides ``ForecastInputDataset``, ``EnsembleForecastDataset``, ``ForecastDataset``, ``LeadTime``, ``Quantile``, and other domain types used throughout the ensemble pipeline. See the :doc:`core` page for dataset hierarchy details.
- **openstef_models** — supplies the ``BaseForecastingModel`` interface, all preprocessing transforms, and ``CustomForecastingWorkflow``. The base forecasters inside ``EnsembleForecastingModel`` are standard ``Forecaster`` instances from this package. See the :doc:`models` page for transform details.
- **openstef_beam** — when running at scale, the ensemble workflow can be executed as an Apache Beam pipeline. The ``openstef_beam`` pipelines accept any ``CustomForecastingWorkflow``, including those produced by ``create_ensemble_forecasting_workflow``. See the :doc:`beam` page for distributed execution patterns.

The ``combine_forecast_input_datasets`` utility in ``openstef_meta.utils.datasets`` handles the bookkeeping of merging base forecaster predictions with optional additional features before the combiner sees them, using an ``inner`` join by default to avoid introducing NaNs.

Choosing a Combiner Strategy
-----------------------------

The right combiner depends on data volume and interpretability requirements:

- Use ``WeightsCombiner`` with ``combiner_model="lgbm"`` as the default. It trains quickly, handles non-linear blending, and exposes feature importances that show which base forecaster dominates at each horizon.
- Switch to ``StackingCombiner`` when you have at least several months of training data and suspect that raw input features (weather, calendar) should influence the blending weights directly.
- Use ``ensemble_type="rules"`` for a transparent baseline or when training data is scarce — it applies fixed, interpretable combination rules without a learned meta-model.

For probabilistic forecasting (multiple quantiles), each combiner trains a separate meta-model per quantile, so the blending strategy can differ across the forecast distribution.