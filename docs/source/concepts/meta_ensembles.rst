Ensemble Forecasting
====================

When a single model fails to capture the full complexity of energy load behaviour —
seasonal shifts, weather extremes, sudden demand events — combining several
complementary base forecasters into a *meta ensemble* often yields more accurate and
more robust predictions. This page explains the design of the ``openstef-meta``
ensemble approach, how its two main combiners work, and when to reach for an ensemble
instead of a single model.

For background on probabilistic forecasts and quantiles, see
:doc:`quantiles_and_confidence`. For production reliability considerations, see
:doc:`reliability_and_fallback`.

Why Ensembles?
--------------

No single algorithm dominates across all operating conditions in energy forecasting.
Gradient-boosted trees handle non-linear feature interactions well but can struggle
with linear trends. Linear models generalise cleanly to unseen conditions but miss
complex interactions. By training several base forecasters in parallel and learning
*how to combine* their outputs, a meta ensemble can exploit the strengths of each
while suppressing individual weaknesses.

The practical benefits are:

- **Reduced variance** — errors from individual models partially cancel out.
- **Improved tail coverage** — different models capture extreme events differently,
  leading to better-calibrated quantile intervals.
- **Graceful degradation** — if one base model produces poor predictions for a
  particular horizon or weather regime, the combiner can down-weight it automatically.

.. mermaid:: /diagrams/concepts/meta_ensembles_diagram_1.mmd

Architecture Overview
---------------------

The central class is ``EnsembleForecastingModel``. It orchestrates three stages:

1. **Common preprocessing** — shared feature engineering applied once to the raw
   input (weather features, datetime features, lag shifters, etc.).
2. **Base forecasters** — N independently trained forecasters, each optionally
   preceded by model-specific preprocessing (e.g. feature scaling for linear models).
3. **Combiner** — a meta-layer that receives all base forecaster predictions as
   additional features and produces the final ``ForecastDataset``.

The easiest way to configure this pipeline is through
``EnsembleForecastingWorkflowConfig``:

.. code-block:: python

    from datetime import timedelta
    from openstef_meta.workflows.ensemble_forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )
    from openstef_core.types import LeadTime, Quantile as Q

    config = EnsembleForecastingWorkflowConfig(
        model_id="my_substation_ensemble",
        ensemble_type="learned_weights",   # or "stacking"
        base_models=["lgbm", "gblinear"],  # base forecasters to combine
        combiner_model="lgbm",             # classifier/regressor used by the combiner
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
    )

    workflow = create_ensemble_forecasting_workflow(config)

The ``create_ensemble_forecasting_workflow`` factory wires up all preprocessing
transforms, instantiates the base forecasters, and attaches the requested combiner —
you do not need to assemble these components manually.

The WeightsCombiner
-------------------

``WeightsCombiner`` (``ensemble_type="learned_weights"``) treats combination as a
*classification problem*. During training it observes which base forecaster produced
the lowest error for each sample and trains a per-quantile classifier to predict that
label from the available features.

At inference time the combiner can operate in two modes, controlled by the
``combiner_model`` choice and internal hyperparameters:

**Hard selection**
   The classifier picks the single best base forecaster for each time step. The final
   prediction is taken entirely from that forecaster. This is interpretable and fast
   but can produce discontinuities at regime boundaries.

**Soft selection**
   The classifier outputs a probability distribution over base forecasters. These
   probabilities are used as weights to form a weighted average of the base
   predictions. Soft selection is smoother and generally more accurate when no single
   forecaster dominates.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
        WeightsCombiner,
    )
    from openstef_meta.models.forecast_combiners.hyperparams import (
        XGBoostCombinerHyperParams,
    )
    from openstef_core.types import Quantile as Q

    # Standalone usage — normally created via EnsembleForecastingWorkflowConfig
    combiner = WeightsCombiner(
        hparams=XGBoostCombinerHyperParams(),
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
    )

    # combiner.fit(ensemble_dataset, data_val=val_dataset)
    # forecast = combiner.predict(ensemble_dataset)

The ``feature_importances()`` property returns a ``pd.DataFrame`` of per-quantile
feature importances from the internal classifiers, which is useful for understanding
which base forecaster the combiner relies on most under different conditions.

.. note::

   ``WeightsCombiner`` trains one classifier per quantile. For a three-quantile
   setup this means three classifiers, each learning potentially different selection
   strategies — the combiner may prefer a linear model for the median but a
   tree-based model for the tails.

The StackingCombiner
--------------------

``StackingCombiner`` (``ensemble_type="stacking"``) treats combination as a
*regression problem*. It trains one meta-regressor per quantile on top of the
stacked base forecaster outputs. The meta-regressor sees the base predictions as
input features and learns a mapping directly to the target value.

This approach is more expressive than weighted averaging: the meta-regressor can
learn non-linear interactions between base forecasters, correct systematic biases,
and incorporate additional context features passed via ``additional_features``.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.stacking_combiner import (
        StackingCombiner,
    )
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
    from openstef_core.types import Quantile as Q, LeadTime

    # The meta_forecaster template is cloned once per quantile
    meta = LGBMForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
    )

    combiner = StackingCombiner(
        meta_forecaster=meta,
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
    )

    # combiner.fit(ensemble_dataset, data_val=val_dataset)
    # forecast = combiner.predict(ensemble_dataset)

Because each quantile has its own independent meta-regressor, ``StackingCombiner``
naturally produces well-separated quantile bands without requiring an explicit
quantile-sorting post-processing step (though ``QuantileSorter`` is still applied
downstream as a safeguard).

Choosing Between the Two Combiners
-----------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Property
     - WeightsCombiner
     - StackingCombiner
   * - Combination mechanism
     - Classifier selects or weights base models
     - Meta-regressor maps base outputs to target
   * - Interpretability
     - High — feature importances show model preference
     - Moderate — standard regressor importances
   * - Training data needed
     - Moderate (classification labels from error ranking)
     - Higher (regression target required per quantile)
   * - Bias correction
     - Limited — inherits base model biases
     - Strong — meta-regressor can correct systematic errors
   * - Quantile calibration
     - Relies on base model calibration
     - Each quantile trained independently
   * - Recommended when
     - Base models are well-calibrated; you want explainability
     - Base models have complementary biases; accuracy is paramount

As a practical starting point, ``learned_weights`` with ``combiner_model="lgbm"`` is
a good default. Switch to ``stacking`` when you observe that the weighted average
still carries systematic bias — for example, consistent over-prediction during
morning ramp-up periods.

Configuring Base Models
-----------------------

The ``base_models`` field accepts any combination of ``"lgbm"``, ``"gblinear"``,
``"xgboost"``, and ``"lgbm_linear"``. Diversity matters: combining two gradient
boosting variants (``lgbm`` + ``xgboost``) provides less benefit than combining a
tree-based model with a linear one (``lgbm`` + ``gblinear``), because the latter pair
makes different structural assumptions about the data.

.. code-block:: python

    # High-diversity ensemble: tree + linear + another tree variant
    config = EnsembleForecastingWorkflowConfig(
        model_id="high_diversity_ensemble",
        ensemble_type="stacking",
        base_models=["lgbm", "gblinear", "xgboost"],
        combiner_model="lgbm",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
    )

.. warning::

   Adding more base models increases training time roughly linearly and raises the
   risk of overfitting in the combiner if training data is limited. With fewer than
   ~6 months of 15-minute data, prefer two base models and ``learned_weights``.

Ensembles vs Single Models
--------------------------

Ensembles are not always the right choice. Consider a single model when:

- **Data is scarce.** A combiner trained on limited data may overfit to the
  training split of base model errors, producing worse out-of-sample performance
  than a single well-tuned model.
- **Latency is critical.** Running N base forecasters plus a combiner at inference
  time takes N+1 times the compute of a single model. For very short inference
  budgets, a single optimised model is preferable.
- **The problem is well-understood.** If domain knowledge strongly favours one
  model type (e.g. a purely linear load profile), the overhead of an ensemble
  adds complexity without benefit.

Ensembles add the most value when:

- Multiple weather regimes or demand patterns are present in the data.
- Probabilistic forecasts (multiple quantiles) are required and calibration matters.
- The forecast horizon spans both short-term (intra-day) and medium-term (day-ahead)
  windows, where different models may excel at different horizons.

For the feature engineering that feeds into both base models and the combiner, see
:doc:`feature_engineering`. For how quantile outputs from the ensemble are
interpreted downstream, see :doc:`quantiles_and_confidence`.