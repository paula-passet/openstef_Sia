Meta Models and Ensemble Architectures
=======================================

The ``openstef_meta`` package extends OpenSTEF's forecasting capabilities beyond single-model pipelines. It provides the infrastructure for **ensemble models** — architectures where multiple independent base forecasters run in parallel and their predictions are combined by a learned or rule-based combiner. This page explains how that architecture is structured, how the two-phase training process works, and how to configure and use ensemble models in your own code.

For the base forecasting models and transform pipelines that serve as building blocks here, see :doc:`models`. For backtesting and evaluating ensemble performance, see :doc:`beam`.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd

----

The Core Abstraction: ``EnsembleForecastingModel``
--------------------------------------------------

The central class in ``openstef_meta`` is ``EnsembleForecastingModel``. It is a sibling of ``ForecastingModel`` from ``openstef_models`` — not a subclass — and implements the same ``BaseForecastingModel`` interface. This means it can be dropped into any workflow that accepts a ``BaseForecastingModel`` without any special-casing.

The model is configured with three categories of processing steps and two categories of model components:

**Processing steps:**

- ``preprocessing`` — a ``TransformPipeline`` applied to the raw ``TimeSeriesDataset`` before any forecaster sees the data. Shared across all base forecasters.
- ``model_specific_preprocessing`` — a ``dict[str, TransformPipeline]`` keyed by forecaster name, applied on top of the common preprocessing for each individual forecaster.
- ``combiner_preprocessing`` — a ``TransformPipeline`` that prepares the data fed to the combiner (typically selects the target column and sample weights).
- ``postprocessing`` / ``model_specific_postprocessing`` / ``combiner_postprocessing`` — analogous postprocessing pipelines applied to ``ForecastDataset`` outputs.

**Model components:**

- ``forecasters`` — a ``dict[str, Forecaster]`` mapping names to configured base forecaster instances.
- ``combiner`` — a ``ForecastCombiner`` that learns to combine the base forecasters' predictions.

----

Two-Phase Training
------------------

Training an ``EnsembleForecastingModel`` proceeds in two sequential phases, both triggered by a single call to ``fit()``.

**Phase 1 — Base forecaster training.** Each base forecaster is trained independently on the preprocessed ``TimeSeriesDataset``. After fitting, each forecaster generates in-sample predictions on the training, validation, and test splits. These predictions are assembled into an ``EnsembleForecastDataset``.

**Phase 2 — Combiner training.** The combiner is trained on the ``EnsembleForecastDataset`` produced in Phase 1. It learns how to weight or transform the base forecasters' outputs into a single final prediction. The combiner never sees the raw features directly — it only sees the base forecasters' predictions (and any additional features explicitly passed via ``combiner_preprocessing``).

This clean separation means the combiner is always trained on out-of-fold or held-out predictions from the base forecasters, which prevents it from simply memorising the strongest base model.

The ``fit()`` method returns an ``EnsembleModelFitResult``, which bundles the combiner's own ``ModelFitResult`` with a ``dict[str, ModelFitResult]`` of per-forecaster results. You can inspect all metrics together via ``metrics_to_flat_dict()``, which prefixes each base forecaster's metrics with its name:

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel

   # Assuming `model` is a configured EnsembleForecastingModel
   # and `train_data` is a TimeSeriesDataset
   fit_result = model.fit(data=train_data)

   # Flat dict: {"mae": ..., "lgbm_mae": ..., "xgb_mae": ..., ...}
   all_metrics = fit_result.metrics_to_flat_dict()

   # Per-forecaster results
   for name, result in fit_result.component_fit_results.items():
       print(f"{name}: {result.metrics_to_flat_dict()}")

----

Forecast Combiners
------------------

The ``ForecastCombiner`` base class (``openstef_meta.models.forecast_combiners``) defines the interface all combiners must implement: ``fit()``, ``predict()``, ``predict_contributions()``, and ``feature_importances()``. OpenSTEF ships two concrete implementations.

**WeightsCombiner**

A learned-weights combiner that trains one classifier per quantile to assign weights to the base forecasters. Several underlying model types are supported, each with its own hyperparameter class:

- ``LGBMCombinerHyperParams``
- ``XGBCombinerHyperParams``
- ``RFCombinerHyperParams``
- ``LogisticCombinerHyperParams``

The ``WeightsCombiner`` is well-suited when you want an interpretable combination strategy — the per-quantile feature importances directly reflect how much each base forecaster contributes.

**StackingCombiner**

A stacking combiner that trains one independent meta-regressor per quantile on top of the base forecasters' outputs. It accepts a ``meta_forecaster`` template (any ``Forecaster`` instance) and clones it once per quantile during ``model_post_init()``. This makes it straightforward to use any model from ``openstef_models`` as the stacking layer:

.. code-block:: python

   from openstef_meta.models.forecast_combiners import StackingCombiner
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_core.types import Quantile, LeadTime

   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   horizons = [LeadTime(1), LeadTime(24)]

   # Template: one quantile and max horizon — StackingCombiner clones it per quantile
   template = LGBMForecaster(
       horizons=[max(horizons)],
       quantiles=[quantiles[0]],
   )

   combiner = StackingCombiner(
       meta_forecaster=template,
       horizons=horizons,
       quantiles=quantiles,
   )

The ``StackingCombiner`` also exposes ``predict_contributions()``, so you can inspect how each base forecaster influenced the final stacked prediction.

----

Using the Preset Workflow
-------------------------

For most use cases you do not need to assemble ``EnsembleForecastingModel`` by hand. The ``openstef_meta.presets`` module provides ``EnsembleForecastingWorkflowConfig`` and ``create_ensemble_forecasting_workflow()``, which wire up all preprocessing, forecasters, and combiners from a single configuration object.

.. code-block:: python

   from openstef_meta.presets import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )

   config = EnsembleForecastingWorkflowConfig(
       model_id="my_ensemble",
       run_name="experiment_01",
       target_column="load",
       ensemble_type="stacking",
       combiner_model="lgbm",
       horizons=[1, 24],
       quantiles=[0.1, 0.5, 0.9],
       # ... location, data_splitter, evaluation_metrics, etc.
   )

   workflow = create_ensemble_forecasting_workflow(config)
   # `workflow` is a CustomForecastingWorkflow ready to call .run()

Internally, ``create_ensemble_forecasting_workflow()`` constructs the full ``EnsembleForecastingModel`` — including common preprocessing (checks, shifters, feature adders, holiday and datetime features, standardizers), per-forecaster preprocessing, a ``StackingCombiner`` or ``WeightsCombiner`` depending on ``combiner_model``, and postprocessing steps such as ``QuantileSorter`` and ``ConfidenceIntervalApplicator``.

.. note::

   The ``cutoff_history`` parameter on ``EnsembleForecastingModel`` is important when base forecasters use lag-based features. It controls how far back in history the model requires data to be present before the first valid prediction timestamp. Set it to at least the largest lag used by any base forecaster.

----

Explainability in Ensembles
---------------------------

Both ``WeightsCombiner`` and ``StackingCombiner`` implement the ``ExplainableForecaster`` interface from ``openstef_models``. This means you can call ``predict_contributions()`` on the combiner to obtain a ``TimeSeriesDataset`` of per-forecaster contributions to the final prediction, and ``feature_importances()`` to retrieve a ``pd.DataFrame`` of importances per quantile.

You can also retrieve the explainable base forecasters directly from the ensemble model:

.. code-block:: python

   # Returns dict[str, ExplainableForecaster] for base forecasters that support it
   explainable = model.get_explainable_components()

   for name, forecaster in explainable.items():
       importances = forecaster.feature_importances()
       print(f"Feature importances for {name}:\n{importances}")

This makes it possible to audit both the base forecasters and the combination layer independently.

----

Design Considerations
---------------------

A few patterns are worth keeping in mind when building ensemble models with ``openstef_meta``:

- **Diversity matters.** The combiner can only improve on the best base forecaster if the base forecasters make different errors. Use different model families (e.g., LightGBM and XGBoost), different feature sets via ``model_specific_preprocessing``, or different horizon configurations.

- **Combiner data leakage.** The two-phase training design guards against the combiner seeing the same data the base forecasters trained on. However, if you pass ``additional_features`` directly to the combiner that are derived from the target, you can reintroduce leakage. Keep ``combiner_preprocessing`` lean.

- **Horizon consistency.** All base forecasters must cover the same set of horizons as the ensemble model. The ``max_horizon`` property on ``EnsembleForecastingModel`` is derived from the union of its forecasters' horizons.

- **Component hyperparameters.** ``component_hyperparams`` exposes a ``dict[str, HyperParams]`` for each base forecaster, making it straightforward to pass them to a hyperparameter search framework without unpacking the model manually.

----

Related Pages
-------------

- :doc:`models` — The ``openstef_models`` package: base ``Forecaster`` classes, ``TransformPipeline``, and the transforms used as building blocks in ensemble preprocessing.
- :doc:`core` — The ``openstef_core`` package: ``TimeSeriesDataset``, ``ForecastDataset``, ``EnsembleForecastDataset``, and the interfaces that tie everything together.
- :doc:`beam` — Backtesting and statistical evaluation tools for comparing ensemble variants against baselines.