Meta Models and Ensemble Architectures
=======================================

The ``openstef_meta`` package extends OpenSTEF's forecasting capabilities beyond single-model pipelines. It provides the infrastructure for building ensemble forecasters — architectures where multiple independent base models run in parallel and their predictions are combined by a learned aggregation layer. This page covers how that architecture is structured, how the key components relate to each other, and how to use them in practice.

For information on the base ``Forecaster`` and transform primitives that feed into ensembles, see the :doc:`models` page. For backtesting and evaluating ensemble performance, see the :doc:`beam` page.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd


The Two-Phase Training Contract
---------------------------------

The central class in ``openstef_meta`` is ``EnsembleForecastingModel``. Its design enforces a strict two-phase training contract that mirrors how stacking and learned-weight ensembles are trained in practice:

**Phase 1 — fit base forecasters.** Each named forecaster is trained independently on the full training dataset. After fitting, each forecaster generates in-sample predictions, which are collected into an ``EnsembleForecastDataset`` — a dataset that holds one ``ForecastDataset`` per base model alongside the true target series.

**Phase 2 — fit the combiner.** The ``ForecastCombiner`` is trained on the ``EnsembleForecastDataset`` produced in Phase 1. It never sees the raw input features directly; it only sees what the base forecasters predicted. This clean separation prevents the combiner from learning spurious correlations with the raw data and keeps the combination layer focused on correcting systematic disagreements between base models.

This two-phase structure is enforced by ``EnsembleForecastingModel.fit()``:

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel

   # Assuming `model` is a configured EnsembleForecastingModel and
   # `train_data` is a TimeSeriesDataset:
   fit_result = model.fit(
       data=train_data,
       data_val=val_data,    # optional; bypasses internal splitter if provided
       data_test=test_data,  # optional
   )

   # fit_result is an EnsembleModelFitResult
   # Access per-forecaster metrics:
   for name, child_result in fit_result.component_fit_results.items():
       print(name, child_result.metrics_to_flat_dict())

   # Access flat metrics dict (prefixed by forecaster name):
   all_metrics = fit_result.metrics_to_flat_dict()

The returned ``EnsembleModelFitResult`` aggregates the ``ModelFitResult`` from every base forecaster alongside the combiner's own fit result, giving full visibility into how each component performed during training.


Preprocessing Layers
---------------------

``EnsembleForecastingModel`` supports four distinct preprocessing scopes, each a ``TransformPipeline``:

- **Common preprocessing** — applied once to the raw ``TimeSeriesDataset`` before any forecaster sees it. Typical contents: data quality checks, lag/shift features, holiday and datetime feature adders, feature standardizers.
- **Model-specific preprocessing** — a per-forecaster ``TransformPipeline`` applied on top of the common-preprocessed data. Useful when one base model needs a different feature set or scaling than another.
- **Combiner preprocessing** — applied to the data passed alongside the ``EnsembleForecastDataset`` to the combiner. In practice this is often minimal — for example, selecting only sample weights and the target column, since the combiner's primary input is already the base forecasters' predictions.
- **Postprocessing** — applied to the final ``ForecastDataset`` after the combiner produces its output. Shared across all paths; a typical step is ``QuantileSorter`` to enforce monotonicity across quantiles.

This layered design means you can share expensive feature engineering across all base models while still giving each model the flexibility it needs.


Forecast Combiners
-------------------

A ``ForecastCombiner`` is the learned aggregation layer that sits on top of the base forecasters. All combiners implement the same interface — ``fit()``, ``predict()``, ``predict_contributions()``, and ``feature_importances()`` — making them interchangeable within an ``EnsembleForecastingModel``.

``openstef_meta`` ships two concrete combiners:

**StackingCombiner**
   Trains one independent meta-regressor per quantile on top of the base forecasters' predictions. The meta-regressor is specified as a template ``Forecaster`` instance, which is cloned once per quantile during ``model_post_init()``. This makes it straightforward to use any ``openstef_models`` forecaster (e.g., an LGBMForecaster) as the stacking layer:

   .. code-block:: python

      from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
      from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
      from openstef_core.types import Quantile

      quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
      horizons = [1, 4, 8, 16, 24, 48]

      # Template forecaster — cloned once per quantile by StackingCombiner
      template = LGBMForecaster(
          horizons=[max(horizons)],
          quantiles=[quantiles[0]],
      )

      combiner = StackingCombiner(
          template_forecaster=template,
          horizons=horizons,
          quantiles=quantiles,
      )

**WeightsCombiner**
   Learns a classification-based weighting scheme: for each quantile, a classifier (LightGBM, XGBoost, Random Forest, or Logistic Regression) is trained to assign weights to the base forecasters' predictions. This is sometimes called a "learned weights" ensemble. The combiner exposes ``feature_importances()`` per quantile, which can reveal which base model the combiner relies on most under different conditions.

   .. code-block:: python

      from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
          WeightsCombiner,
          LGBMCombinerHyperParams,
      )

      combiner = WeightsCombiner(
          hyperparams=LGBMCombinerHyperParams(),
          horizons=horizons,
          quantiles=quantiles,
      )

Both combiners accept an optional ``additional_features`` argument in ``fit()`` and ``predict()``, allowing you to pass features that were not produced by the base forecasters — for example, weather variables or calendar features — directly into the combination layer.


Using the Preset Workflow
--------------------------

Assembling an ``EnsembleForecastingModel`` by hand requires wiring together preprocessing pipelines, forecasters, and a combiner. For common configurations, ``openstef_meta`` provides a preset that handles this construction:

.. code-block:: python

   from openstef_meta.presets.forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )
   from datetime import timedelta

   config = EnsembleForecastingWorkflowConfig(
       model_id="my_ensemble",
       ensemble_type="stacking",       # or "learned_weights"
       base_models=["lgbm", "xgboost", "gblinear"],
       combiner_model="lgbm",
       horizons=[1, 4, 8, 16, 24, 48],
       quantiles=[0.1, 0.5, 0.9],
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       energy_price_column="EPEX_NL",
       model_reuse_enable=False,
       mlflow_storage=None,
   )

   workflow = create_ensemble_forecasting_workflow(config)

The ``create_ensemble_forecasting_workflow()`` factory builds the full ``EnsembleForecastingModel`` — including all preprocessing pipelines, the named forecasters, and the combiner — from the configuration object. The returned ``workflow`` is a ``CustomForecastingWorkflow`` that can be passed directly to a backtesting pipeline (see :doc:`beam`).

.. note::

   ``ensemble_type`` and ``combiner_model`` are matched together. Valid combinations include
   ``("stacking", "lgbm")``, ``("learned_weights", "lgbm")``, ``("learned_weights", "xgboost")``,
   ``("learned_weights", "rf")``, and ``("learned_weights", "logistic")``. Unsupported
   combinations raise a ``ValueError`` at construction time.


Inspecting a Fitted Ensemble
-----------------------------

After training, ``EnsembleForecastingModel`` exposes several properties for inspection:

.. code-block:: python

   # Names of all base forecasters
   print(model.forecaster_names)

   # Per-forecaster hyperparameters
   for name, hparams in model.component_hyperparams.items():
       print(name, hparams)

   # Retrieve explainable components (forecasters that implement ExplainableForecaster)
   explainable = model.get_explainable_components()
   for name, forecaster in explainable.items():
       importances = forecaster.feature_importances
       print(f"{name}: top features = {importances.head()}")

   # Combiner feature importances (which base model is trusted most, per quantile)
   combiner_importances = model.combiner.feature_importances()
   print(combiner_importances)

The ``EnsembleModelFitResult.metrics_to_flat_dict()`` method returns a single flat dictionary where every metric from every base forecaster is prefixed with the forecaster's name (e.g., ``lgbm_mae``, ``xgboost_rmse``), alongside the combiner's own metrics. This makes it straightforward to log everything to MLflow or compare runs in a backtesting framework.


Design Considerations
----------------------

A few practical points worth keeping in mind when working with ``openstef_meta``:

- **Cutoff history matters.** If your base forecasters use lag-based features, the ``cutoff_history`` parameter on ``EnsembleForecastingModel`` must be set large enough to cover the maximum lag. Insufficient history will cause silent feature gaps.
- **In-sample predictions for the combiner.** The combiner is trained on the base forecasters' in-sample predictions. If those predictions are overfit, the combiner may learn to trust an overfit model. Using a validation split (``data_val``) is strongly recommended to give the combiner a more honest signal.
- **Combiner preprocessing is minimal by design.** The combiner's primary input is the ``EnsembleForecastDataset``, not the raw features. The combiner preprocessing pipeline is intentionally kept narrow — typically just sample weights and the target column — to avoid leaking raw features into the combination layer.
- **Interchangeable combiners.** Because all combiners share the ``ForecastCombiner`` interface, you can swap ``StackingCombiner`` for ``WeightsCombiner`` without changing any other part of the pipeline. This makes it easy to compare combination strategies under identical base forecaster configurations.

For evaluating whether a change to your ensemble architecture produces a statistically meaningful improvement, see the regression testing and metrics tooling described in :doc:`beam`.