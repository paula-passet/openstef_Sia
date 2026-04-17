Meta Ensembles
==============

Short-term energy forecasting is a genuinely hard regression problem. Load curves
are shaped by weather, human behaviour, market prices, and calendar effects — no
single model architecture captures all of these equally well across every horizon
and every season. The ``openstef-meta`` package addresses this by providing a
*meta-ensemble* layer: several independently trained base forecasters whose
predictions are combined by a learned combiner into a single, more accurate
probabilistic forecast.

This page explains why that combination helps, how the two built-in combiners
work, and how to choose between them for your use case.

.. note::

   ``openstef-meta`` is a library component. It does not run autonomously; you
   compose it with base forecasters and wire it into a training/inference
   workflow of your own design, or use the
   :class:`~openstef_meta.presets.forecasting_workflow.EnsembleForecastingWorkflowConfig`
   preset to get started quickly.

For background on probabilistic forecasts and quantiles, see
:doc:`quantiles_and_confidence`. For the features fed into each base forecaster,
see :doc:`feature_engineering`.

----

Why Ensembles Improve Accuracy
-------------------------------

A single model trained on historical load data will inevitably have blind spots.
A gradient-boosted tree excels at capturing non-linear interactions between
weather variables but may underfit smooth, slowly varying trends. A linear model
handles those trends well but struggles with sharp, weather-driven spikes. When
the two are combined, their errors are partially uncorrelated, and the combined
forecast is more accurate than either alone — a well-established result in
statistical learning theory known as the *bias-variance trade-off*.

In energy forecasting, this diversity is especially valuable because:

- **Regime changes.** Demand patterns shift across seasons, holidays, and
  market conditions. Different model families generalise differently across
  these regimes.
- **Horizon sensitivity.** A model tuned for 15-minute-ahead forecasts may
  degrade faster at 36-hour horizons than a model with smoother inductive
  biases.
- **Probabilistic coverage.** When quantile estimates from multiple models are
  combined, the resulting prediction intervals tend to be better calibrated
  than those from any single model.

The ``openstef-meta`` library formalises this intuition through the
:class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel`,
which orchestrates a set of base forecasters and delegates the combination step
to a pluggable :class:`~openstef_meta.models.forecast_combiners.forecast_combiner.ForecastCombiner`.

[DIAGRAM: Architecture of EnsembleForecastingModel — shared preprocessing feeds N parallel base forecasters, each producing per-quantile predictions; an EnsembleForecastDataset collects all base outputs; the ForecastCombiner (WeightsCombiner or StackingCombiner) produces the final ForecastDataset]

----

The EnsembleForecastingModel
-----------------------------

:class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel`
is the central orchestrator. It holds:

- A shared **preprocessing pipeline** applied to all base forecasters.
- A dictionary of **base forecasters**, each optionally with its own
  model-specific preprocessing.
- A **combiner** that learns how to aggregate base predictions.
- Shared **postprocessing** (e.g., quantile sorting, confidence-interval
  clipping) applied after combination.

The model exposes the standard ``fit`` / ``predict`` interface, so it integrates
naturally with the rest of the OpenSTEF ecosystem.

----

WeightsCombiner: Learned Classifier Weights
--------------------------------------------

The :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.WeightsCombiner`
treats combination as a *classification* problem. For each timestep it asks:
"which base forecaster should be trusted most right now?" A classifier — trained
on the base forecasters' predictions and any additional context features — learns
to answer that question.

Internally, the combiner trains one classifier **per quantile**. At inference
time, the classifier produces a probability distribution over the base
forecasters. Depending on the ``hard_selection`` flag, the combiner then either:

- **Soft selection** (``hard_selection=False``, the default): blends the base
  forecasters' predictions using the predicted probabilities as weights. This
  produces smooth, continuous output and is generally preferred.
- **Hard selection** (``hard_selection=True``): picks the single highest-
  probability forecaster for each timestep. This is interpretable and fast but
  can introduce discontinuities at regime boundaries.

Four classifier backends are available, each with its own hyperparameter class:

- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.LGBMCombinerHyperParams`
  — LightGBM gradient-boosted trees (default).
- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.RFCombinerHyperParams`
  — LightGBM random forest.
- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.XGBCombinerHyperParams`
  — XGBoost classifier.
- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.LogisticCombinerHyperParams`
  — Logistic regression (L1/L2/ElasticNet regularisation).

.. code-block:: python

   from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
       WeightsCombiner,
       LGBMCombinerHyperParams,
       LogisticCombinerHyperParams,
   )
   from openstef_core.types import Q

   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   # Default: LGBM classifier, soft blending
   combiner = WeightsCombiner(
       hyperparams=LGBMCombinerHyperParams(),
       hard_selection=False,
   )

   # Alternative: logistic regression with L1 regularisation, hard selection
   combiner_hard = WeightsCombiner(
       hyperparams=LogisticCombinerHyperParams(penalty="l1", c=0.5),
       hard_selection=True,
   )

The ``predict_contributions`` method returns per-timestep model weights, making
it straightforward to audit which base forecaster dominated a given period.

----

StackingCombiner: Per-Quantile Meta-Regressors
-----------------------------------------------

The :class:`~openstef_meta.models.forecast_combiners.stacking_combiner.StackingCombiner`
takes a different approach. Rather than classifying which forecaster to trust, it
trains a dedicated **meta-regressor** on top of the base forecasters' outputs for
each quantile. This is the classical *stacking* (or *super-learner*) technique
from ensemble learning.

You supply a single *template* forecaster instance. The combiner clones it once
per quantile, so each quantile gets an independently trained meta-model. The
template must be a fully configured
:class:`~openstef_models.models.forecasting.forecaster.Forecaster` instance; the
combiner handles the cloning and per-quantile training loop automatically.

.. code-block:: python

   from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
   from openstef_core.types import Q, LeadTime

   # Import a concrete forecaster to use as the meta-model template
   # (GBLinear or LGBM are typical choices for the stacking layer)
   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearForecaster

   quantiles = [Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)]
   horizons = [LeadTime.from_string("PT36H")]

   template = GBLinearForecaster(
       horizons=[max(horizons)],
       quantiles=[quantiles[0]],   # cloned per-quantile by StackingCombiner
   )

   combiner = StackingCombiner(
       meta_forecaster=template,
       horizons=horizons,
       quantiles=quantiles,
   )

Because each meta-regressor is itself a quantile forecaster, the stacking layer
can learn non-linear relationships between base predictions and the true target —
something a simple weighted average cannot do.

----

Putting It Together: the Workflow Preset
-----------------------------------------

For most use cases, the fastest path to a working ensemble is the
:class:`~openstef_meta.presets.forecasting_workflow.EnsembleForecastingWorkflowConfig`
preset. It wires up base forecasters, preprocessing, the combiner, and
postprocessing from a single configuration object.

.. code-block:: python

   from openstef_meta.presets.forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )
   from openstef_core.types import Q, LeadTime

   config = EnsembleForecastingWorkflowConfig(
       model_id="grid_connection_A",
       # Base model pool
       ensemble_type="learned_weights",   # or "stacking"
       base_models=["gblinear", "lgbm", "xgboost"],
       # Combiner backend
       combiner_model="lgbm",             # "lgbm", "rf", "xgboost", "logistic"
                                          # or "gblinear" for stacking
       horizons=[LeadTime.from_string("PT36H")],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       # Weather columns
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       energy_price_column="EPEX_NL",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

   workflow = create_ensemble_forecasting_workflow(config)
   # workflow is a CustomForecastingWorkflow ready for fit() / predict()

The ``ensemble_type`` and ``combiner_model`` fields together select the combiner:
``"learned_weights"`` with any of ``"lgbm"``, ``"rf"``, ``"xgboost"``, or
``"logistic"`` instantiates a ``WeightsCombiner``; ``"stacking"`` with
``"gblinear"`` or ``"lgbm"`` instantiates a ``StackingCombiner``.

----

Choosing Between WeightsCombiner and StackingCombiner
------------------------------------------------------

Neither combiner is universally superior. The right choice depends on your data
volume, interpretability requirements, and the diversity of your base forecasters.

**WeightsCombiner is a good default when:**

- You want interpretable output — ``predict_contributions`` directly shows which
  model was trusted at each timestep.
- Your base forecasters are already well-calibrated individually; the combiner
  only needs to route between them.
- You have limited combiner training data, because a classifier is a simpler
  model than a full meta-regressor stack.
- Hard selection is acceptable or even desirable (e.g., for operational
  transparency).

**StackingCombiner is worth trying when:**

- Your base forecasters have complementary but non-trivial error structures that
  a linear blend cannot capture.
- You have sufficient training data for the meta-regressors to generalise (a
  rule of thumb: at least as much data as you would use to train a single base
  model).
- Probabilistic calibration is critical — per-quantile meta-regressors can
  correct systematic quantile biases in the base layer.

**Single model vs. ensemble:**

Ensembles add training complexity, inference latency, and storage cost. For
simple, stable load profiles with abundant training data, a single well-tuned
model may match or exceed ensemble accuracy. Consider an ensemble when:

- You observe high variance in single-model performance across retraining runs.
- Your load profile has distinct operating regimes (e.g., industrial vs.
  residential mix, seasonal HVAC dominance).
- You need well-calibrated prediction intervals, not just point forecasts.

For production reliability considerations — including what happens when one base
forecaster fails to produce a prediction — see :doc:`reliability_and_fallback`.

----

Explainability and Feature Importances
---------------------------------------

Both combiners implement the
:class:`~openstef_models.explainability.mixins.ExplainableForecaster` interface.
The ``feature_importances`` property returns a ``pd.DataFrame`` of importances
from the internal classifier or meta-regressor models, broken down per quantile.
For ``WeightsCombiner``, ``predict_contributions`` returns per-timestep model
weights, giving a direct answer to "which base forecaster drove this forecast?"

[VISUALIZATION: Stacked bar chart showing per-timestep WeightsCombiner model weights across a one-week forecast window, illustrating how the combiner shifts trust between base forecasters during a weather event]

----

Summary
-------

- ``openstef-meta`` provides a meta-ensemble layer on top of OpenSTEF base
  forecasters, implemented in
  :class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel`.
- :class:`~openstef_meta.models.forecast_combiners.learned_weights_combiner.WeightsCombiner`
  uses a per-quantile classifier to blend or select base forecasters; it is
  interpretable and data-efficient.
- :class:`~openstef_meta.models.forecast_combiners.stacking_combiner.StackingCombiner`
  trains a per-quantile meta-regressor on base outputs; it is more expressive
  but requires more data.
- The
  :class:`~openstef_meta.presets.forecasting_workflow.EnsembleForecastingWorkflowConfig`
  preset assembles the full pipeline from a single configuration object.
- Ensembles are most valuable for diverse load profiles, well-calibrated
  probabilistic forecasts, and situations where single-model variance is high.