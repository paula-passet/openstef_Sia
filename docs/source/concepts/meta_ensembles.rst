Ensemble Forecasting
====================

Short-term energy forecasting is a hard regression problem: load curves shift with weather, season, day-of-week, and unexpected events. No single model architecture dominates across all these conditions. A gradient-boosted tree may track slow seasonal drift well but miss sharp intra-day spikes; a linear model may extrapolate cleanly at long horizons but underfit complex non-linear patterns. The ``openstef-meta`` package addresses this by layering a *combiner* on top of several independently trained *base forecasters*, letting the ensemble exploit the complementary strengths of each member.

This page explains the design rationale, the two main combiners (``WeightsCombiner`` and ``StackingCombiner``), and the practical trade-offs you face when choosing between them. For background on probabilistic forecasts and quantiles, see :doc:`quantiles_and_confidence`. For how individual base models are built and what features they consume, see :doc:`feature_engineering`.

Why Ensembles?
--------------

The core argument for ensembling is *variance reduction*. When base forecasters make uncorrelated errors, averaging their predictions reduces the overall error even if no individual member is best. In energy forecasting this matters because:

- **Regime changes** — a model trained mostly on mild weather may degrade in extreme cold; a second model with different inductive bias may handle it better.
- **Horizon heterogeneity** — accuracy at a 1-hour horizon and a 36-hour horizon often favours different architectures.
- **Quantile coverage** — tail quantiles (e.g. Q0.05, Q0.95) are harder to calibrate from a single model; a combiner can re-weight base outputs to improve coverage.

The gain is not free. Ensembles require more training data, more compute, and more careful validation. The sections below describe when the trade-off is worthwhile.

.. mermaid:: /diagrams/concepts/meta_ensembles_diagram_1.mmd

Architecture Overview
---------------------

``openstef-meta`` structures the ensemble as two distinct stages:

1. **Base forecasters** — any number of independently trained ``Forecaster`` instances (e.g. ``LGBMForecaster``, ``XGBoostForecaster``, ``GBLinearForecaster``). Each produces its own set of quantile predictions.
2. **Combiner** — a ``ForecastCombiner`` that receives the stacked base predictions as an ``EnsembleForecastDataset`` and outputs a single ``ForecastDataset``.

Both stages are wired together through ``EnsembleForecastingWorkflowConfig``, which keeps configuration declarative and reproducible.

.. code-block:: python

    from datetime import timedelta
    from openstef_meta.workflows.config import EnsembleForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    config = EnsembleForecastingWorkflowConfig(
        model_id="grid_connection_42",
        ensemble_type="learned_weights",   # or "stacking"
        base_models=["lgbm", "gblinear"],  # base forecaster architectures
        combiner_model="lgbm",             # classifier/regressor inside the combiner
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
    )

The ``base_models`` field accepts ``"lgbm"``, ``"gblinear"``, ``"xgboost"``, and ``"lgbm_linear"``. The ``combiner_model`` field controls the internal learner used by the combiner — its valid values depend on the chosen ``ensemble_type``.

WeightsCombiner — Learned Classifier Weights
--------------------------------------------

``WeightsCombiner`` (``ensemble_type="learned_weights"``) treats combiner selection as a *classification* problem. For each quantile it trains a classifier whose job is to predict which base forecaster will produce the smallest error on a given input instance. At inference time the classifier's output probabilities become the mixing weights.

**Hard selection** assigns the full weight to the single forecaster with the highest predicted probability:

.. code-block:: text

    weights = one_hot(argmax(probabilities))

**Soft selection** uses the raw probabilities directly:

.. code-block:: text

    final_prediction = sum(prob_i * prediction_i  for each base forecaster i)

Soft selection is the default and is almost always preferable: it degrades gracefully when the classifier is uncertain and produces smoother transitions between regimes.

The classifier itself is configurable via ``combiner_model``. Supported options are ``"lgbm"``, ``"xgboost"``, ``"rf"`` (random forest), and ``"logistic"``. LGBM is a sensible default — it handles mixed feature types well and trains quickly.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.learned_weights_combiner import WeightsCombiner
    from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
        XGBoostCombinerHyperParams,
    )

    combiner = WeightsCombiner(
        hparams=XGBoostCombinerHyperParams(),
        quantiles=config.quantiles,
        horizons=config.horizons,
    )

    # fit expects an EnsembleForecastDataset (base forecaster outputs + actuals)
    combiner.fit(data=train_ensemble_dataset, data_val=val_ensemble_dataset)
    forecast = combiner.predict(data=test_ensemble_dataset)

After fitting you can inspect which base forecasters the classifier relies on most:

.. code-block:: python

    importances = combiner.feature_importances()
    print(importances)  # DataFrame indexed by quantile, columns are base forecaster names

.. note:: [VISUALIZATION: Bar chart of feature importances per quantile showing relative contribution of each base forecaster]

The classifier is trained with balanced class weights (``compute_sample_weight`` from scikit-learn), so a dominant base forecaster does not crowd out the others during training.

StackingCombiner — Per-Quantile Meta-Regressors
-----------------------------------------------

``StackingCombiner`` (``ensemble_type="stacking"``) takes a different approach: instead of classifying which forecaster to trust, it trains a *regression* meta-model for each quantile. The meta-model's inputs are the base forecaster predictions for that quantile, optionally augmented with additional features from the original input dataset.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
    from openstef_models.models.hyperparameters.lgbm import LGBMHyperParams

    # Provide a template forecaster; StackingCombiner clones it once per quantile
    meta_forecaster_template = LGBMForecaster(
        hyperparams=LGBMHyperParams(),
        quantiles=config.quantiles,
        horizons=config.horizons,
    )

    combiner = StackingCombiner(
        meta_forecaster=meta_forecaster_template,
        quantiles=config.quantiles,
        horizons=config.horizons,
    )

    combiner.fit(data=train_ensemble_dataset, additional_features=train_input_dataset)
    forecast = combiner.predict(
        data=test_ensemble_dataset,
        additional_features=test_input_dataset,
    )

The ``additional_features`` argument passes the original ``ForecastInputDataset`` through to each meta-regressor, giving it access to weather variables, calendar features, and any other predictors beyond the raw base forecaster outputs. This is the key advantage of stacking over weight-based combination: the meta-model can learn *why* one base forecaster is better in a given context, not just *that* it is.

The ``combiner_model`` field for stacking accepts ``"gblinear"`` and ``"lgbm"``. ``"gblinear"`` is a natural fit because the meta-model's job is essentially a weighted linear combination of its inputs, and a linear model is interpretable and resistant to overfitting on the (relatively small) stacking training set.

.. note::

   ``StackingCombiner`` clones the template forecaster once per quantile during ``model_post_init``. If you configure seven quantiles, you get seven independent meta-regressors. This increases training time proportionally but ensures each quantile's tail behaviour is modelled independently — important for well-calibrated prediction intervals. See :doc:`quantiles_and_confidence` for more on quantile calibration.

Comparing the Two Combiners
---------------------------

The table below summarises the practical differences:

.. list-table::
   :header-rows: 1
   :widths: 25 37 38

   * - Property
     - WeightsCombiner
     - StackingCombiner
   * - Combiner task
     - Classification (which forecaster wins?)
     - Regression (what is the best blend?)
   * - Output
     - Weighted average of base predictions
     - Direct regression output per quantile
   * - Additional features
     - Optional (passed to classifier)
     - Strongly recommended (richer meta-model)
   * - Training data needed
     - Moderate (classifier is lightweight)
     - More (regression meta-model is richer)
   * - Interpretability
     - ``feature_importances()`` shows forecaster weights
     - ``feature_importances()`` shows full feature set
   * - Best for
     - Regime-switching, fast training
     - Maximum accuracy, rich feature context

When to Use Ensembles vs. Single Models
----------------------------------------

Ensembles are not always the right choice. Consider the following:

**Use an ensemble when:**

- You have at least 6–12 months of historical data per connection, giving the combiner enough examples of different operating regimes.
- Your load profile has distinct seasonal or weather-driven regimes where different model architectures excel.
- You need well-calibrated tail quantiles for risk management or grid planning.
- You can afford the additional training and inference compute (roughly proportional to the number of base models plus one combiner pass).

**Stick with a single model when:**

- Training data is sparse — a combiner trained on too few examples will overfit and underperform a well-tuned single model.
- Latency is critical — each base forecaster runs independently, so wall-clock inference time scales with the number of members unless you parallelise.
- The connection's load profile is simple and stable — a single LGBM model is already near the accuracy ceiling.

.. note::

   For production deployments, reliability matters as much as accuracy. If a base forecaster fails to produce predictions, the combiner receives an incomplete ``EnsembleForecastDataset``. See :doc:`reliability_and_fallback` for how OpenSTEF handles missing base forecaster outputs gracefully.

Practical Configuration Tips
-----------------------------

A few patterns that work well in practice:

**Diverse base models beat many similar ones.** Combining ``"lgbm"`` and ``"gblinear"`` gives more complementary predictions than combining three LGBM variants with slightly different hyperparameters. Diversity in inductive bias is what drives the ensemble gain.

**Start with ``learned_weights`` + ``"lgbm"`` combiner.** This is the fastest path to a working ensemble and a good baseline. Switch to ``StackingCombiner`` if you observe systematic bias at specific quantiles or horizons.

**Use sample weights on base forecasters.** The ``forecaster_sample_weights`` field in ``EnsembleForecastingWorkflowConfig`` accepts per-model ``SampleWeightConfig`` objects. Exponential decay (``method="exponential"``) is useful for base models that should emphasise recent data, while a flat weight (``weight_exponent=0.0``) suits models intended to capture long-run seasonality.

.. code-block:: python

    from openstef_meta.workflows.config import EnsembleForecastingWorkflowConfig, SampleWeightConfig

    config = EnsembleForecastingWorkflowConfig(
        model_id="grid_connection_42",
        ensemble_type="stacking",
        base_models=["lgbm", "gblinear", "xgboost"],
        combiner_model="gblinear",
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.05), Q(0.5), Q(0.95)],
        forecaster_sample_weights={
            "gblinear": SampleWeightConfig(method="exponential", weight_exponent=1.0),
            "lgbm":     SampleWeightConfig(weight_exponent=0.0),
            "xgboost":  SampleWeightConfig(weight_exponent=0.0),
        },
    )

**Validate the combiner on a held-out period, not the base forecaster training set.** The combiner must learn from errors it has not already seen. Pass a separate ``data_val`` argument to ``combiner.fit()`` to enable early stopping in gradient-boosted combiners.

Related Pages
-------------

- :doc:`quantiles_and_confidence` — understanding the probabilistic outputs that ensembles produce
- :doc:`feature_engineering` — the predictors available to base forecasters and meta-models
- :doc:`reliability_and_fallback` — what happens when a base forecaster is unavailable at inference time
- :doc:`forecasting_basics` — foundational concepts for short-term energy forecasting