Ensemble Forecasting
====================

Short-term energy forecasting is a hard regression problem: load curves are shaped by weather, human behaviour, market prices, and calendar effects that interact in non-linear ways. No single model architecture dominates across all conditions. The ``openstef-meta`` package addresses this by letting you train several *base forecasters* in parallel and then combine their predictions with a learned *combiner* — a meta-ensemble.

This page explains why that helps, how the two built-in combiners work, and when the extra complexity is worth it.

.. mermaid:: /diagrams/concepts/meta_ensembles_diagram_1.mmd

Why Combine Multiple Forecasters?
----------------------------------

Individual models make different kinds of errors. A gradient-boosted tree with linear booster (GBLinear) captures long-range linear trends well; a full LightGBM or XGBoost model captures short-range non-linear spikes. When electricity demand is driven primarily by temperature on a cold winter morning, the tree model may win; during a public holiday with unusual consumption patterns, a model trained with heavier recent-sample weighting may be more reliable.

Combining predictions reduces *variance* — the tendency of any single model to overfit to the quirks of its training window — without necessarily increasing bias. In practice, ensembles on energy load data consistently outperform their best individual member on held-out periods, particularly at longer forecast horizons where uncertainty is higher.

The ``openstef-meta`` ensemble is not a simple average. Both built-in combiners *learn* how to weight or blend base forecaster outputs from data, so the combination adapts to which models are trustworthy in which regimes.

Architecture Overview
---------------------

The central class is :class:`EnsembleForecastingModel <openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel>`. It orchestrates:

1. **Common preprocessing** — feature engineering and cleaning applied to all data before any model sees it.
2. **N base forecasters** — each with optional model-specific preprocessing (e.g. different sample weighting schemes).
3. **A combiner** — receives the stacked predictions from all base forecasters as an :class:`EnsembleForecastDataset <openstef_core.datasets.validated_datasets.EnsembleForecastDataset>` and produces the final :class:`ForecastDataset <openstef_core.datasets.ForecastDataset>`.
4. **Common postprocessing** — e.g. sorting quantiles to enforce monotonicity.

Both combiners share the abstract :class:`ForecastCombiner <openstef_meta.models.forecast_combiners.forecast_combiner.ForecastCombiner>` interface, so they are interchangeable in the workflow.

The WeightsCombiner
-------------------

The :class:`WeightsCombiner <openstef_meta.models.forecast_combiners.learned_weights_combiner.WeightsCombiner>` treats combination as a *classification* problem. For each quantile and each time step, it trains a classifier to select (or soft-weight) which base forecaster to trust.

**Hard vs soft selection**

In hard mode the classifier picks one forecaster per time step — the final prediction is taken entirely from the winner. In soft mode the classifier outputs class probabilities that are used as convex weights, blending all base forecasters proportionally. Soft selection is generally smoother and more robust; hard selection can be useful when one model is clearly superior in a specific regime and you want interpretable switching behaviour.

**Supported classifier backends**

The combiner accepts any of the following hyperparameter classes, each wrapping a different sklearn-compatible classifier:

- :class:`XGBCombinerHyperParams <openstef_meta.models.forecast_combiners.learned_weights_combiner.XGBCombinerHyperParams>` — XGBoost classifier
- :class:`LGBMCombinerHyperParams <openstef_meta.models.forecast_combiners.learned_weights_combiner.LGBMCombinerHyperParams>` — LightGBM classifier
- :class:`RFCombinerHyperParams <openstef_meta.models.forecast_combiners.learned_weights_combiner.RFCombinerHyperParams>` — Random Forest classifier
- :class:`LogisticCombinerHyperParams <openstef_meta.models.forecast_combiners.learned_weights_combiner.LogisticCombinerHyperParams>` — Logistic Regression

A separate classifier is trained per quantile, so the combiner can, for example, prefer a different base model when estimating the 5th percentile (downside risk) than when estimating the 95th percentile (upside risk).

.. code-block:: python

    from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
        WeightsCombiner,
        XGBCombinerHyperParams,
    )

    combiner = WeightsCombiner(
        hparams=XGBCombinerHyperParams(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
        ),
        quantiles=[0.05, 0.50, 0.95],
        soft_weights=True,   # blend rather than hard-select
    )

After fitting, :meth:`predict_contributions` returns a :class:`TimeSeriesDataset` showing each base forecaster's weight over time — useful for diagnosing which model dominates in which season or hour of day.

.. note:: [VISUALIZATION: Stacked area chart of per-forecaster weights over a week, showing how the WeightsCombiner shifts reliance between GBLinear and LightGBM across different demand regimes]

The StackingCombiner
--------------------

The :class:`StackingCombiner <openstef_meta.models.forecast_combiners.stacking_combiner.StackingCombiner>` takes a different approach: it trains a *meta-regressor* on top of the base forecasters' outputs. The meta-regressor sees the predictions from all base models as input features and learns a mapping to the final forecast value.

One meta-regressor is trained **per quantile**. This is important for probabilistic forecasting: the optimal blend for the median prediction is not necessarily the same as for the tails. A meta-regressor at the 95th quantile can learn, for instance, that during high-wind periods the XGBoost model systematically underestimates peak demand and should be up-weighted.

The ``meta_forecaster`` argument accepts any :class:`Forecaster <openstef_models.models.forecasting.forecaster.Forecaster>` instance as a template; the combiner clones it once per quantile.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
    from openstef_models.models.forecasting.lgbm_hyperparams import LGBMHyperParams

    meta_forecaster = LGBMForecaster(
        hyperparams=LGBMHyperParams(n_estimators=50, num_leaves=16),
        quantiles=[0.05, 0.50, 0.95],
        horizons=[1, 4, 24],
    )

    combiner = StackingCombiner(
        meta_forecaster=meta_forecaster,
        quantiles=[0.05, 0.50, 0.95],
    )

Because the meta-regressor is itself a full forecaster, it can also receive *additional features* (e.g. weather variables, calendar flags) alongside the base predictions. This lets the stacking layer learn context-dependent blending without the classification framing of the WeightsCombiner.

Putting It Together: EnsembleForecastingModel
---------------------------------------------

Both combiners plug into :class:`EnsembleForecastingModel <openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel>` in the same way. The recommended entry point for a complete workflow is the preset factory :func:`create_ensemble_forecasting_workflow <openstef_meta.presets.forecasting_workflow.create_ensemble_forecasting_workflow>`, which wires up preprocessing, base forecasters, and the combiner from a single configuration object.

.. code-block:: python

    from openstef_meta.presets.forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        ensemble_type="stacking",       # or "weights"
        base_models=["gblinear", "lgbm", "xgboost"],
        combiner_model="lgbm",          # meta-regressor backend for stacking
        horizons=[1, 4, 24, 48],
        quantiles=[0.05, 0.25, 0.50, 0.75, 0.95],
        temperature_column="temperature_2m",
        wind_speed_column="wind_speed_80m",
        radiation_column="shortwave_radiation",
        energy_price_column="EPEX_NL",
    )

    workflow = create_ensemble_forecasting_workflow(config)

The workflow object is a standard ``CustomForecastingWorkflow`` that exposes ``fit`` and ``predict`` methods and integrates with the OpenSTEF backtesting and MLflow tracking infrastructure.

.. note::

   The combiner is trained on *validation-fold* predictions from the base forecasters, not on their training-fold outputs. This prevents the combiner from learning to trust a model that simply memorised its training data. The data splitter in the config controls how these folds are constructed.

WeightsCombiner vs StackingCombiner: When to Use Which
-------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Criterion
     - WeightsCombiner
     - StackingCombiner
   * - **Interpretability**
     - High — weights show which model is active
     - Lower — meta-regressor is a black box
   * - **Flexibility**
     - Moderate — convex combination only
     - High — meta-regressor can learn non-linear blends
   * - **Data requirement**
     - Lower — classifier trains quickly
     - Higher — meta-regressor needs sufficient validation data
   * - **Tail quantile accuracy**
     - Good with per-quantile classifiers
     - Often better — separate regressor per quantile
   * - **Regime switching**
     - Natural fit (hard selection)
     - Possible but implicit
   * - **Training cost**
     - Low
     - Moderate (one model per quantile)

As a rule of thumb: start with the ``WeightsCombiner`` in soft mode when you want fast iteration and interpretable diagnostics. Switch to ``StackingCombiner`` when you need the best possible tail quantile accuracy and have at least several months of validation data for the meta-regressor to learn from.

Practical Trade-offs for Energy Forecasting
-------------------------------------------

**Training data volume**
Both combiners train on the *outputs* of base forecasters, not raw features, so their effective input dimensionality is low (number of base models × number of quantiles). This means they generalise well even with modest validation sets — typically a few weeks of 15-minute data is sufficient for the WeightsCombiner; a few months is safer for StackingCombiner.

**Computational cost**
Base forecasters train in parallel. The combiner adds one additional training pass over the validation predictions. Total wall-clock time is dominated by the base forecasters, so adding a combiner is cheap relative to the base training cost.

**Overfitting risk**
The main risk is the combiner learning to exploit artefacts in the validation fold rather than genuine model quality differences. Mitigations include: using a generous validation window, regularising the combiner (e.g. shallow trees, low ``n_estimators``), and monitoring combiner feature importances for unexpected patterns.

**Fallback behaviour**
If one base forecaster fails to produce predictions at inference time, the combiner receives a partial ``EnsembleForecastDataset``. How gracefully this degrades depends on the combiner type. For production reliability considerations — including what happens when the ensemble itself cannot produce a forecast — see :doc:`reliability_and_fallback`.

**Probabilistic calibration**
Stacking can improve quantile calibration because the meta-regressor directly optimises a quantile loss. The ``ConfidenceIntervalApplicator`` in the postprocessing step provides an additional safety net by enforcing that the output confidence interval is at least as wide as a minimum threshold. For background on what quantile forecasts mean and how to evaluate them, see :doc:`quantiles_and_confidence`.

Feature Importances and Explainability
---------------------------------------

Both combiners implement :meth:`feature_importances` and :meth:`predict_contributions`, surfacing which base forecasters drive the final prediction. For the WeightsCombiner, contributions are the per-forecaster weights at each time step. For the StackingCombiner, contributions are SHAP values from the meta-regressor (when the underlying forecaster supports SHAP).

.. code-block:: python

    # After fitting, inspect which base model the combiner relies on most
    importances = combiner.feature_importances()
    print(importances)
    # Returns a DataFrame indexed by base forecaster name,
    # with columns for each quantile.

.. note:: [VISUALIZATION: Bar chart of WeightsCombiner feature importances per quantile, showing relative reliance on GBLinear vs LightGBM vs XGBoost for the 0.05, 0.50, and 0.95 quantiles]

Related Topics
--------------

- :doc:`forecasting_basics` — foundational concepts behind short-term energy forecasting and why probabilistic outputs matter.
- :doc:`quantiles_and_confidence` — how quantile forecasts are defined, evaluated, and calibrated.
- :doc:`feature_engineering` — the weather and calendar features that feed into the base forecasters.
- :doc:`reliability_and_fallback` — production strategies when one or more ensemble components fail.
- :doc:`component_splitting` — decomposing aggregate load into sub-components before or after ensembling.