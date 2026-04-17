Meta-Ensembles in OpenSTEF
==========================

.. note::

   This page covers the ``openstef-meta`` package's ensemble approach: how multiple
   base forecasters are combined and why that combination improves accuracy. For an
   introduction to probabilistic forecasting and quantiles, see
   :doc:`quantiles_and_confidence`. For production reliability considerations, see
   :doc:`reliability_and_fallback`.

No single model architecture dominates every energy forecasting scenario. A gradient-boosted
tree may excel during stable, sunny summer days while a linear model handles overnight
price-driven demand spikes more gracefully. The ``openstef-meta`` library formalises this
intuition: train several *base forecasters* in parallel, then learn a *combiner* that
decides — per timestep and per quantile — how much to trust each one.

The result is an :class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel`
that exposes the same ``fit`` / ``predict`` interface as any other OpenSTEF model, so
the ensemble is a drop-in replacement rather than a separate workflow.

**[DIAGRAM: Data flow through EnsembleForecastingModel — raw time-series enters common preprocessing, fans out to N parallel base forecasters, their predictions feed into the combiner, and a single ForecastDataset exits postprocessing]**

Why Ensembles Improve Accuracy
-------------------------------

The theoretical justification is bias-variance decomposition. A single model makes a
systematic error (bias) and a noise-driven error (variance). When several models with
*different* biases are combined, their errors partially cancel, reducing overall
prediction error — provided the models are not perfectly correlated.

In energy forecasting this correlation is naturally low because:

- Different model families (gradient boosting, linear, random forest) respond differently
  to the same features.
- Sample-weighting strategies can be varied per base forecaster, so one model may
  emphasise recent data while another treats all history equally.
- Preprocessing choices (feature selection, imputation) can differ per model, exposing
  each forecaster to a slightly different view of the same underlying signal.

The combiner then exploits these differences by learning *when* each base forecaster is
most reliable, rather than averaging blindly.

Architecture: EnsembleForecastingModel
---------------------------------------

The central class is
:class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel`.
It orchestrates three stages:

1. **Common preprocessing** — transformations applied to the raw input before any
   model sees it (checks, feature engineering, datetime features).
2. **Parallel base forecasters** — each forecaster receives the common-preprocessed
   data plus its own model-specific preprocessing pipeline and produces a full
   probabilistic forecast across all requested quantiles and horizons.
3. **Combiner** — receives the stacked base-forecaster predictions as an
   :class:`~openstef_core.datasets.validated_datasets.EnsembleForecastDataset` and
   produces the final :class:`~openstef_core.datasets.ForecastDataset`.

The two concrete combiner implementations — ``WeightsCombiner`` and
``StackingCombiner`` — differ in *how* they aggregate the base predictions.

The WeightsCombiner
--------------------

:class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.WeightsCombiner`
frames combination as a **classification problem**. For every timestep and every
quantile, a trained classifier predicts which base forecaster should be trusted most.
The classifier is trained on historical data where the "label" for each timestep is the
base forecaster that produced the lowest error.

Four classifier back-ends are available, each with its own hyperparameter class:

- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.LGBMCombinerHyperParams` — LightGBM gradient-boosted classifier (default)
- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.RFCombinerHyperParams` — LightGBM random-forest classifier
- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.XGBCombinerHyperParams` — XGBoost classifier
- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.LogisticCombinerHyperParams` — Logistic regression (interpretable baseline)

Hard vs. Soft Selection
^^^^^^^^^^^^^^^^^^^^^^^^

The ``hard_selection`` flag controls how the classifier output is used:

- **Soft selection** (``hard_selection=False``, the default) — the classifier emits
  class probabilities, and the final prediction is a weighted average of all base
  forecasters, with weights proportional to those probabilities. Every model
  contributes; the classifier merely adjusts the blend.
- **Hard selection** (``hard_selection=True``) — the classifier picks the single
  highest-probability forecaster for each timestep and uses its prediction exclusively.
  This is more interpretable but can introduce discontinuities at regime boundaries.

Soft selection is generally preferable in production because it degrades gracefully: if
the classifier is uncertain, the output naturally reverts toward an equal-weight average
rather than making a potentially wrong binary choice.

.. code-block:: python

   from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
       WeightsCombiner,
       LGBMCombinerHyperParams,
       XGBCombinerHyperParams,
   )
   from openstef_core.types import Q

   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   # Soft-selection combiner using LightGBM (default)
   soft_combiner = WeightsCombiner(
       hyperparams=LGBMCombinerHyperParams(),
       hard_selection=False,
       quantiles=quantiles,
   )

   # Hard-selection combiner using XGBoost — useful for post-hoc analysis
   hard_combiner = WeightsCombiner(
       hyperparams=XGBCombinerHyperParams(n_estimators=200),
       hard_selection=True,
       quantiles=quantiles,
   )

After fitting, ``WeightsCombiner.predict_contributions()`` returns a
:class:`~openstef_core.datasets.TimeSeriesDataset` showing each base forecaster's
contribution per timestep — useful for diagnosing which model dominates under which
conditions. ``feature_importances()`` exposes the internal classifier's feature
importances per quantile.

The StackingCombiner
---------------------

:class:`~openstef_meta.models.forecast_combiners.stacking_combiner.StackingCombiner`
uses **stacked generalisation**: instead of a classifier, it trains a separate
*meta-regressor* for each quantile. The meta-regressor takes the base forecasters'
quantile predictions as input features and learns a regression mapping to the final
output.

This is a more expressive combination strategy. The meta-regressor can learn non-linear
interactions between base forecasters and can, in principle, correct systematic biases
that a simple weighted average cannot remove. The cost is additional training data
requirements and a longer fit time.

You supply a *template* forecaster — a fully configured
:class:`~openstef_models.models.forecasting.forecaster.Forecaster` instance — and
``StackingCombiner`` clones it once per quantile:

.. code-block:: python

   from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
   from openstef_core.types import Q, LeadTime

   # Import a concrete forecaster to use as the meta-regressor template
   # (the StackingCombiner clones this once per quantile)
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

   quantiles = [Q(0.1), Q(0.5), Q(0.9)]
   horizons = [LeadTime.from_string("PT36H")]

   stacking_combiner = StackingCombiner(
       meta_forecaster=LGBMForecaster(
           horizons=horizons,
           quantiles=[quantiles[0]],   # template uses one quantile; combiner clones it
       ),
       horizons=horizons,
       quantiles=quantiles,
   )

.. note::

   The ``meta_forecaster`` template is configured with a single quantile and the
   maximum horizon. ``StackingCombiner`` handles cloning and quantile assignment
   internally — you do not need to create one forecaster per quantile yourself.

Putting It Together: The Workflow Preset
-----------------------------------------

In practice, the easiest way to build an ensemble is through the
:func:`~openstef_meta.presets.forecasting_workflow.create_ensemble_forecasting_workflow`
preset, which wires up preprocessing, base forecasters, and the combiner from a single
configuration object:

.. code-block:: python

   from datetime import timedelta
   from openstef_meta.presets.forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )
   from openstef_core.types import Q, LeadTime

   workflow_config = EnsembleForecastingWorkflowConfig(
       model_id="my_ensemble",
       # Base model pool
       ensemble_type="learned_weights",   # or "stacking"
       base_models=["lgbm", "xgboost", "gblinear"],
       # Combiner back-end
       combiner_model="lgbm",             # "lgbm", "rf", "xgboost", "logistic" for
                                          # learned_weights; "gblinear" for stacking
       horizons=[LeadTime.from_string("PT36H")],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       # Weather feature columns
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       energy_price_column="EPEX_NL",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

   workflow = create_ensemble_forecasting_workflow(workflow_config)
   # `workflow` is a CustomForecastingWorkflow with .fit() and .predict() methods

**[DIAGRAM: EnsembleForecastingWorkflowConfig fields mapping to the three internal stages — base_models/ensemble_type → base forecasters, combiner_model → combiner, shared fields → common preprocessing]**

WeightsCombiner vs. StackingCombiner: When to Use Each
--------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Criterion
     - WeightsCombiner
     - StackingCombiner
   * - **Combination mechanism**
     - Classifier selects/blends forecasters
     - Meta-regressor learns output mapping
   * - **Training data needed**
     - Moderate — one classifier per quantile
     - Higher — one regressor per quantile
   * - **Interpretability**
     - High — ``predict_contributions()`` shows per-model weights
     - Moderate — contributions reflect meta-regressor features
   * - **Bias correction**
     - Limited — blends existing predictions
     - Strong — can correct systematic errors
   * - **Fit time**
     - Fast
     - Slower (more models to train)
   * - **Recommended when**
     - Base models are well-calibrated; you want to know which model wins
     - Base models have complementary biases; you want maximum accuracy

A practical heuristic: start with ``WeightsCombiner`` (soft selection, LGBM back-end)
as a baseline. If validation metrics plateau and you have sufficient training history
(at least 90 days at 15-minute resolution), switch to ``StackingCombiner`` with a
GBLinear meta-regressor, which adds expressiveness without excessive overfitting risk.

Ensembles vs. Single Models
-----------------------------

Ensembles are not always the right choice. Consider the trade-offs:

**Prefer an ensemble when:**

- You have diverse base models that make different errors (low inter-model correlation).
- Your load profile has distinct regimes (e.g., industrial vs. residential mix) where
  different models excel.
- Probabilistic coverage (quantile calibration) is a hard requirement — stacking
  typically improves quantile sharpness.
- You can afford the additional training and inference time.

**Prefer a single model when:**

- Training data is scarce (fewer than ~60 days at 15-minute resolution). Ensembles
  need enough history to train the combiner *after* the base forecasters have been fit.
- Operational simplicity is paramount — a single model is easier to monitor, retrain,
  and debug.
- Inference latency is tightly constrained. Running N base forecasters plus a combiner
  multiplies prediction time roughly by N.

.. note::

   The ``EnsembleForecastingModel`` is designed so that the combiner is trained on a
   held-out validation split, not on the same data used to train the base forecasters.
   This prevents the combiner from simply memorising which base model happened to
   overfit the training set. Ensure your ``data_splitter`` configuration reserves
   enough validation data for the combiner to learn meaningful weights.

Practical Trade-offs for Energy Forecasting
--------------------------------------------

Energy load and generation forecasting has a few characteristics that shape ensemble
design choices:

**Seasonality and regime shifts.** Load profiles change dramatically between seasons,
weekdays and weekends, and before and after public holidays. A ``WeightsCombiner``
trained on a full year of data can learn that, say, the linear model dominates on
holiday mornings while the gradient-boosted model dominates on cold winter evenings.
See :doc:`feature_engineering` for the holiday and datetime features that make this
regime detection possible.

**Quantile asymmetry.** Upper-tail quantiles (e.g., Q0.9, Q0.95) matter most for
grid congestion management, while lower-tail quantiles matter for under-production
alerts. ``StackingCombiner`` trains a separate meta-regressor per quantile, so it can
optimise tail behaviour independently — a significant advantage over symmetric
combination strategies. See :doc:`quantiles_and_confidence` for more on why quantile
calibration matters.

**Computational budget.** Running three or four base forecasters in parallel is
feasible on a single machine for 15-minute resolution data. If you are scaling to
hundreds of grid connections simultaneously, consider the Apache Beam-based pipelines
in ``openstef-beam``, which distribute base forecaster training and inference across
workers.

**Model reuse.** The ``model_reuse_enable`` flag in
:class:`~openstef_meta.presets.forecasting_workflow.EnsembleForecastingWorkflowConfig`
allows previously trained base forecasters to be loaded from storage rather than
retrained from scratch. This is useful when the combiner needs to be updated more
frequently than the base models — for example, after a structural change in the load
profile that only affects the blending weights, not the individual model parameters.

Related Pages
--------------

- :doc:`quantiles_and_confidence` — Understanding the probabilistic forecasts that
  ensembles produce.
- :doc:`feature_engineering` — The weather, calendar, and lag features that feed into
  base forecasters and inform the combiner's regime detection.
- :doc:`reliability_and_fallback` — What happens when one or more base forecasters
  fail at prediction time, and how the ensemble degrades gracefully.
- :doc:`forecasting_basics` — Foundational concepts for short-term energy forecasting
  before diving into ensemble methods.