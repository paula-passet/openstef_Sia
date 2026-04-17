Ensemble Forecasting
====================

Short-term energy forecasting is a hard regression problem: load curves are shaped by weather, human behaviour, market prices, and calendar effects simultaneously. No single model architecture dominates across all these drivers. The ``openstef-meta`` package addresses this by letting you train several *base forecasters* in parallel and then combine their predictions with a learned *combiner*. This page explains why that helps, how the two built-in combiners work, and when the overhead is worth it.

Why Ensembles Help
------------------

A single model commits to one inductive bias. A gradient-boosted tree, for example, excels at capturing non-linear interactions between weather variables but can struggle with smooth, slowly-varying trends that a linear model handles naturally. When you stack multiple architectures, their errors tend to be *uncorrelated*: on a given timestep the tree may over-predict while the linear model under-predicts, and a combiner that has seen both can learn to hedge.

The practical gains in energy forecasting come from three sources:

- **Variance reduction** — averaging over diverse models smooths out the spiky errors that any individual model produces on unusual days (heat waves, public holidays, grid events).
- **Bias correction** — a meta-learner can detect systematic patterns in which base model is wrong and in which direction, then correct for them.
- **Better calibrated quantiles** — probabilistic forecasts benefit especially from ensembling because the spread of base-model predictions is itself informative about uncertainty. See :doc:`quantiles_and_confidence` for background on quantile forecasting.

.. note:: [DIAGRAM: Data flow from raw time-series input through common preprocessing, into N parallel base forecasters, then into the combiner layer, and finally to the output forecast dataset]

The ``EnsembleForecastingModel``
---------------------------------

The central class is ``EnsembleForecastingModel``. It owns:

1. A shared preprocessing pipeline applied to every base forecaster.
2. A dictionary of named base ``Forecaster`` instances, each optionally with its own model-specific preprocessing.
3. A ``ForecastCombiner`` that receives all base predictions and produces the final output.

.. code-block:: python

    from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
    from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_core.mixins.transform import TransformPipeline

    forecasters = {
        "lgbm": LGBMForecaster(quantiles=quantiles, horizons=horizons),
        "xgboost": XGBoostForecaster(quantiles=quantiles, horizons=horizons),
    }

    combiner = StackingCombiner(
        meta_forecaster=LGBMForecaster(quantiles=quantiles, horizons=horizons),
        quantiles=quantiles,
    )

    model = EnsembleForecastingModel(
        preprocessing=TransformPipeline(transforms=[...]),
        forecasters=forecasters,
        combiner=combiner,
        target_column="load",
    )

During ``fit``, each base forecaster is trained independently on the training split. The combiner is then trained on a *held-out validation split*, receiving the base forecasters' predictions as its input features. This two-stage training prevents the combiner from over-fitting to the training residuals of the base models.

The ``WeightsCombiner``
-----------------------

``WeightsCombiner`` frames combination as a *classification* problem: for each timestep and quantile, it asks "which base forecaster should I trust most right now?" and assigns a soft probability to each candidate. The final prediction is a weighted average of the base forecasters' outputs, where the weights are those probabilities.

Internally, one classifier is trained per quantile. Four classifier backends are available out of the box:

- ``LogisticCombinerHyperParams`` — logistic regression; fast, interpretable, good baseline.
- ``XGBCombinerHyperParams`` — XGBoost classifier; captures non-linear selection rules.
- ``RFCombinerHyperParams`` — random forest classifier; robust to outliers in the meta-features.
- ``LGBMCombinerHyperParams`` — LightGBM classifier; efficient on large validation sets.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
        WeightsCombiner,
        XGBCombinerHyperParams,
    )

    combiner = WeightsCombiner(
        hparams=XGBCombinerHyperParams(n_estimators=100, max_depth=4),
        quantiles=quantiles,
    )

**Hard vs. soft selection.** When the classifier is very confident (one probability close to 1.0), the combiner effectively performs *hard selection* — it picks a single base forecaster and ignores the rest. When probabilities are spread across candidates, the output is a genuine weighted blend. In practice the combiner learns to be selective during unusual conditions (e.g., a cold snap where the weather-aware model clearly dominates) and to blend during typical operating conditions.

The ``predict_contributions`` method returns the per-forecaster weights at each timestep, which is useful for diagnosing which model drives the ensemble on specific days.

.. note:: [VISUALIZATION: Stacked area chart showing per-forecaster weight contributions over a week-long forecast horizon, illustrating how the WeightsCombiner shifts trust between models across different weather regimes]

The ``StackingCombiner``
------------------------

``StackingCombiner`` takes a different approach: it trains a separate *meta-regressor* for each quantile. The meta-regressor receives the base forecasters' quantile predictions as input features and learns a direct mapping to the final quantile output. This is classical stacking (also called *blending* when a held-out fold is used for the meta-training data).

.. code-block:: python

    from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

    # The meta_forecaster is cloned once per quantile
    combiner = StackingCombiner(
        meta_forecaster=LGBMForecaster(quantiles=quantiles, horizons=horizons),
        quantiles=quantiles,
    )

Because each quantile has its own meta-model, ``StackingCombiner`` can learn quantile-specific combination rules. For example, the p10 (lower tail) combiner might learn to weight the most conservative base model more heavily, while the p90 combiner weights the most volatile one. This makes ``StackingCombiner`` particularly well-suited to producing calibrated prediction intervals — see :doc:`quantiles_and_confidence` for how interval calibration is evaluated.

The ``additional_features`` argument to both ``fit`` and ``predict`` lets you pass extra context (e.g., weather forecasts, calendar flags) directly to the combiner, on top of the base predictions. This is optional but can improve combination quality when the combiner needs to know *why* conditions are unusual.

Choosing Between the Two Combiners
------------------------------------

Both combiners are trained on the same held-out validation data and expose the same ``fit`` / ``predict`` interface, so switching between them is a one-line change. The practical differences are:

**WeightsCombiner** is the right default when:

- You want interpretable, per-timestep model attribution (the weights are directly readable).
- Your base forecasters are already well-calibrated individually and you mainly want to select the best one dynamically.
- Training data for the combiner is limited — a logistic or random-forest classifier generalises well with fewer samples than a full meta-regressor.

**StackingCombiner** is the right default when:

- You want the combiner to *correct* systematic biases in the base forecasters, not just select between them.
- Quantile calibration is a primary concern and you are willing to train one meta-model per quantile.
- Your base forecasters are diverse enough that a linear combination would leave residual structure on the table.

.. note::

   Both combiners require a validation split that is *temporally disjoint* from the training split. Using in-sample predictions to train the combiner leads to over-fitting and inflated performance metrics. The ``EnsembleForecastingModel`` handles this split automatically when you provide ``data_val`` to ``fit``.

Using the Preset Workflow
--------------------------

For most production use cases, the ``EnsembleForecastingWorkflowConfig`` preset in ``openstef_meta.presets.forecasting_workflow`` assembles the full pipeline — base forecasters, preprocessing, combiner, and postprocessing — from a declarative configuration object. This is the recommended entry point rather than constructing ``EnsembleForecastingModel`` by hand.

.. code-block:: python

    from openstef_meta.presets.forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        ensemble_type="stacking",        # or "weights"
        base_models=["lgbm", "xgboost", "lgbm_linear"],
        combiner_model="lgbm",
        horizons=horizons,
        quantiles=quantiles,
        target_column="load_mw",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        temperature_column="temperature_2m",
    )

    workflow = create_ensemble_forecasting_workflow(config)

The ``base_models`` list controls which architectures are instantiated. The ``ensemble_type`` and ``combiner_model`` fields map directly to the combiner classes described above. Feature engineering (weather lags, datetime encodings, rolling aggregates) is configured through the same object — see :doc:`feature_engineering` for the full list of available predictors.

Trade-offs in Production
-------------------------

Ensembles improve accuracy but they are not free:

- **Training time** scales linearly with the number of base forecasters, plus the combiner. For a three-model ensemble with a stacking combiner, expect roughly 4× the training time of a single model.
- **Inference latency** is similarly multiplied, though base forecasters run independently and can be parallelised.
- **Fallback complexity** increases: if one base forecaster fails at inference time, the combiner receives an incomplete input. The ``openstef-meta`` ensemble model handles missing base predictions gracefully by masking the absent forecaster's contribution, but you should verify this behaviour matches your reliability requirements. See :doc:`reliability_and_fallback` for production fallback strategies.
- **Debugging** is harder because errors can originate in any base forecaster or in the combiner. The ``predict_contributions`` method on both combiners is the primary diagnostic tool.

For substations with very short history (less than a few months of training data), a single well-regularised model often outperforms an ensemble because the combiner cannot learn reliable selection rules from limited validation data. Ensembles pay off most when you have at least 90 days of clean training data and a meaningful held-out validation period.

.. note:: [VISUALIZATION: Scatter plot comparing single-model vs. ensemble RMSE across a set of substations, showing the accuracy gain as a function of available training data length]

Related Topics
--------------

- :doc:`forecasting_basics` — the fundamentals of short-term load forecasting that ensembles build on.
- :doc:`quantiles_and_confidence` — how probabilistic outputs are defined and evaluated; relevant to understanding why per-quantile combiners matter.
- :doc:`feature_engineering` — the predictors fed into each base forecaster.
- :doc:`reliability_and_fallback` — what happens when one or more ensemble components fail in production.