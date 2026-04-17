The ``openstef_meta`` Package
=============================

The ``openstef_meta`` package sits at the top of the OpenSTEF dependency graph. It
draws on ``openstef_core`` for base types and dataset abstractions, ``openstef_models``
for individual forecasting models, and ``openstef_beam`` for evaluation metrics — then
combines them into an *ensemble* layer: multiple base forecasters trained in parallel,
whose predictions are merged by a configurable combiner into a single probabilistic
output.

This page covers the three main building blocks: ``EnsembleForecastingModel``, the
``ForecastCombiner`` abstraction with its two concrete implementations, and the
``EnsembleForecastingWorkflowConfig`` preset that wires everything together.

For the individual base models that feed into the ensemble, see :doc:`models`.
For the Beam pipelines that orchestrate training and inference at scale, see :doc:`beam`.

.. note:: [DIAGRAM: Component-level diagram of the meta package. Left column shows base forecasters (Forecaster 1 … Forecaster N) fed by a shared preprocessing block sourced from openstef_core. Center column shows the ForecastCombiner (WeightsCombiner or StackingCombiner) receiving the stacked base-forecaster predictions. Right column shows the final probabilistic EnsembleForecastingModel output. Dependency arrows point from openstef_meta down to openstef_core (base types, datasets), openstef_models (base forecaster implementations), and openstef_beam (evaluation metric providers used by the preset).]

----

Architecture at a Glance
-------------------------

``EnsembleForecastingModel`` implements the same ``BaseForecastingModel`` interface as
the single-model ``ForecastingModel`` in ``openstef_models`` — they are siblings, not
parent and child. This means any code that accepts a ``BaseForecastingModel`` works
equally well with a plain model or an ensemble.

Internally, training proceeds in two phases:

1. **Base-forecaster phase** — every configured forecaster is fitted independently on
   the training split. Their in-sample predictions are collected into an
   ``EnsembleForecastDataset``.
2. **Combiner phase** — the ``ForecastCombiner`` is fitted on those stacked predictions,
   learning how to weight or stack them into a final quantile forecast.

Prediction mirrors this structure: each base forecaster produces its own forecast, the
results are assembled, and the combiner maps them to the output ``ForecastDataset``.

----

``EnsembleForecastingModel``
-----------------------------

The model is configured declaratively. You supply a dictionary of named
``Forecaster`` configs and a ``ForecastCombiner`` instance; the model handles the rest.

.. code-block:: python

    from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
    from openstef_meta.models.forecast_combiners import WeightsCombiner, LGBMCombinerHyperParams
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    # Two base forecasters with different configurations
    lgbm_config = ForecastingWorkflowConfig(model_type="lgbm", ...)
    xgb_config  = ForecastingWorkflowConfig(model_type="xgb",  ...)

    ensemble = EnsembleForecastingModel(
        forecaster_configs={
            "lgbm": create_forecasting_workflow(lgbm_config).forecaster,
            "xgb":  create_forecasting_workflow(xgb_config).forecaster,
        },
        combiner=WeightsCombiner(
            hparams=LGBMCombinerHyperParams(),
            horizons=[timedelta(hours=1), timedelta(hours=24)],
        ),
        quantiles=[0.1, 0.5, 0.9],
    )

    fit_result = ensemble.fit(data=train_dataset, data_val=val_dataset)

``fit_result`` is an ``EnsembleModelFitResult``, which extends the standard
``ModelFitResult`` with a ``component_fit_results`` property — a dictionary keyed by
forecaster name, giving you per-model metrics alongside the combiner's aggregate metrics.
Calling ``metrics_to_flat_dict()`` on it produces a single flat dictionary with
prefixed keys (e.g. ``lgbm_rmse``, ``xgb_rmse``, ``combiner_rmse``) suitable for
logging or experiment tracking.

Key properties available after fitting:

- ``forecaster_names`` — ordered list of base forecaster identifiers.
- ``component_hyperparams`` — hyperparameters for each component, useful for
  serialisation and reproducibility.
- ``get_explainable_components()`` — returns the subset of base forecasters that
  implement ``ExplainableForecaster``, enabling SHAP-style feature attribution per
  component.

.. note::

    The ``cutoff_history`` parameter is important when base forecasters use lag-based
    features. It controls how far back in time the model looks when constructing
    features at prediction time, and must be consistent across all base forecasters.

----

``ForecastCombiner`` — the Combination Abstraction
----------------------------------------------------

``ForecastCombiner`` is an abstract base class (``ABC``) that defines the contract for
combining base-forecaster predictions:

.. code-block:: python

    from openstef_meta.models.forecast_combiners import ForecastCombiner

    # ForecastCombiner exposes:
    #   .fit(data: EnsembleForecastDataset, data_val=None, additional_features=None)
    #   .predict(data: EnsembleForecastDataset, additional_features=None) -> ForecastDataset
    #   .hparams  -> HyperParams
    #   .is_fitted -> bool
    #   .with_horizon(horizon) -> Self   # immutable copy with a different horizon

The combiner operates *per quantile*: for each configured quantile it learns a separate
mapping from the vector of base-forecaster predictions to a scalar output. This keeps
quantile crossing under control and lets the combiner specialise for tail behaviour.

``WeightsCombiner``
^^^^^^^^^^^^^^^^^^^

``WeightsCombiner`` trains a lightweight supervised model — your choice of LightGBM,
XGBoost, Random Forest, or Logistic Regression — to learn optimal weights for the base
forecasters. Because the meta-model is small and trained on in-sample predictions, it
converges quickly and is interpretable via feature importances (one importance value per
base forecaster per quantile).

.. code-block:: python

    from openstef_meta.models.forecast_combiners import (
        WeightsCombiner,
        LGBMCombinerHyperParams,
        XGBCombinerHyperParams,
        RFCombinerHyperParams,
        LogisticCombinerHyperParams,
    )

    # LightGBM-backed combiner (default choice for most use cases)
    lgbm_combiner = WeightsCombiner(
        hparams=LGBMCombinerHyperParams(n_estimators=100, learning_rate=0.05),
        horizons=[timedelta(hours=1), timedelta(hours=24)],
    )

    # XGBoost-backed combiner
    xgb_combiner = WeightsCombiner(
        hparams=XGBCombinerHyperParams(),
        horizons=[timedelta(hours=1), timedelta(hours=24)],
    )

The hyperparameter classes (``LGBMCombinerHyperParams``, ``XGBCombinerHyperParams``,
``RFCombinerHyperParams``, ``LogisticCombinerHyperParams``) are Pydantic models, so
they validate inputs at construction time and serialise cleanly to JSON for experiment
tracking.

``StackingCombiner``
^^^^^^^^^^^^^^^^^^^^

``StackingCombiner`` trains a dedicated meta-regressor *per quantile* on top of the
base forecasters' predictions. Unlike ``WeightsCombiner``, which constrains the
combination to a weighted sum, ``StackingCombiner`` can learn non-linear interactions
between forecasters — useful when base models have complementary strengths that a linear
blend cannot fully exploit.

.. code-block:: python

    from openstef_meta.models.forecast_combiners import StackingCombiner

    stacking_combiner = StackingCombiner(
        horizons=[timedelta(hours=1), timedelta(hours=24)],
    )

    ensemble = EnsembleForecastingModel(
        forecaster_configs={"lgbm": ..., "linear": ...},
        combiner=stacking_combiner,
        quantiles=[0.1, 0.5, 0.9],
    )

The trade-off is interpretability: ``StackingCombiner`` is more expressive but harder
to inspect than ``WeightsCombiner``. For most operational deployments, start with
``WeightsCombiner`` and switch to ``StackingCombiner`` only if validation metrics
justify the added complexity.

----

``EnsembleForecastingWorkflowConfig`` — the Preset
----------------------------------------------------

Rather than assembling ``EnsembleForecastingModel`` by hand, the preset in
``openstef_meta.presets`` mirrors the ``ForecastingWorkflowConfig`` pattern from
``openstef_models`` and produces a ready-to-run ``CustomForecastingWorkflow``.

.. code-block:: python

    from openstef_meta.presets import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )
    from openstef_meta.models.forecast_combiners import WeightsCombiner, LGBMCombinerHyperParams
    from datetime import timedelta

    config = EnsembleForecastingWorkflowConfig(
        forecaster_configs={
            "lgbm": lgbm_forecaster_config,
            "xgb":  xgb_forecaster_config,
        },
        combiner=WeightsCombiner(
            hparams=LGBMCombinerHyperParams(),
            horizons=[timedelta(hours=1), timedelta(hours=24)],
        ),
        quantiles=[0.1, 0.5, 0.9],
        horizons=[timedelta(hours=1), timedelta(hours=24)],
    )

    workflow = create_ensemble_forecasting_workflow(config)

The returned ``CustomForecastingWorkflow`` is the same type accepted by the Beam
pipelines in ``openstef_beam``. Passing it to a training or backtesting pipeline
requires no further adaptation — the ensemble is a drop-in replacement for a
single-model workflow.

The preset also wires up evaluation metrics from ``openstef_beam``:
``R2Provider`` and ``ObservedProbabilityProvider`` are attached by default, giving you
deterministic accuracy and probabilistic calibration scores out of the box.

.. note::

    ``EnsembleForecastingWorkflowConfig`` inherits from ``BaseConfig`` (``openstef_core``),
    so it is a Pydantic model. You can serialise the entire ensemble configuration —
    including nested forecaster configs and combiner hyperparameters — to JSON and
    reload it later for reproducibility.

----

Choosing a Combiner
--------------------

The right combiner depends on your base forecasters and data characteristics:

- **Few, diverse base forecasters** (e.g. one tree-based, one linear): ``WeightsCombiner``
  with ``LGBMCombinerHyperParams`` is a strong default. Feature importances tell you
  which forecaster dominates at each quantile.
- **Many base forecasters with overlapping strengths**: ``StackingCombiner`` can exploit
  non-linear interactions that a weighted average would miss.
- **Interpretability is a hard requirement**: ``WeightsCombiner`` with
  ``LogisticCombinerHyperParams`` gives the most transparent combination — the learned
  coefficients are directly interpretable as per-forecaster weights.
- **Limited training data for the combiner**: prefer simpler hyperparameter classes
  (``LogisticCombinerHyperParams``, ``RFCombinerHyperParams``) to avoid overfitting the
  meta-model.

----

Dataset Utilities
-----------------

``openstef_meta.utils`` provides ``combine_forecast_input_datasets``, which merges the
base forecasters' prediction outputs with any additional features you want to expose to
the combiner (e.g. calendar features, weather forecasts not used by the base models):

.. code-block:: python

    from openstef_meta.utils.datasets import combine_forecast_input_datasets

    combined = combine_forecast_input_datasets(
        input_data=base_predictions,
        additional_features=extra_features,
        join="inner",   # or "outer" to keep all timestamps
    )

This is called internally by ``EnsembleForecastingModel`` but is also available for
custom combiner implementations that extend ``ForecastCombiner``.

----

Related Pages
--------------

- :doc:`core` — ``BaseForecastingModel``, ``TimeSeriesDataset``, and the type system
  that ``EnsembleForecastingModel`` builds on.
- :doc:`models` — the individual forecasting models (LightGBM, XGBoost, linear) that
  serve as base forecasters inside the ensemble.
- :doc:`beam` — Beam pipelines for training, backtesting, and serving; accept
  ``CustomForecastingWorkflow`` produced by ``create_ensemble_forecasting_workflow``.