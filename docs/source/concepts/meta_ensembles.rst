Meta Ensembles
==============

OpenSTEF's ``openstef-meta`` package extends the core forecasting library with a
**meta-ensemble layer**: instead of relying on a single model, it trains several
independent base forecasters in parallel and then combines their predictions
through a learned combiner. This page explains why that helps, how the two
built-in combiners work, and when the added complexity is worth it.

For background on probabilistic forecasts and quantiles referenced throughout
this page, see :doc:`quantiles_and_confidence`. For the features fed into each
base model, see :doc:`feature_engineering`.

Why Ensembles?
--------------

Any single model makes assumptions about the data-generating process. A gradient
boosting tree handles non-linear interactions well but can struggle with smooth
extrapolation; a linear model generalises cleanly outside the training range but
misses local patterns. In energy forecasting these failure modes are not
hypothetical: a heat-wave pushes load into a regime the tree has rarely seen,
while a public holiday creates a structural shift that a purely linear model
handles more gracefully.

Combining several models reduces this risk in two complementary ways:

- **Variance reduction** – independent errors partially cancel when predictions
  are averaged or blended.
- **Bias hedging** – a combiner can learn *which* base model is most reliable
  under specific conditions (time of day, season, weather regime) and up-weight
  it accordingly.

Empirically, well-tuned ensembles in short-term load forecasting consistently
outperform the best individual model, particularly at the tails of the
distribution where accurate quantile estimates matter most for grid operations.

.. note:: [DIAGRAM: Data flow from raw time-series through common preprocessing, into N parallel base forecasters, then into the combiner layer, and finally to the probabilistic forecast output]

Architecture Overview
---------------------

The central class is ``EnsembleForecastingModel``. It owns:

1. A **common preprocessing pipeline** applied to all data before it reaches any
   model.
2. **N base forecasters**, each with its own optional model-specific
   preprocessing.
3. A **ForecastCombiner** that receives every base forecaster's per-quantile
   predictions and produces the final forecast.
4. Optional postprocessing (e.g. ``QuantileSorter`` to enforce monotonicity).

.. code-block:: python

    from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
    from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
    from openstef_core.mixins.transform import TransformPipeline

    model = EnsembleForecastingModel(
        preprocessing=common_preprocessing,          # shared TransformPipeline
        model_specific_preprocessing={"gblinear": gblinear_pipe, "lgbm": lgbm_pipe},
        combiner_preprocessing=combiner_pipe,
        postprocessing=common_postprocessing,
        model_specific_postprocessing=TransformPipeline(transforms=[]),
        combiner_postprocessing=combiner_postprocessing,
        forecasters={"gblinear": gblinear_forecaster, "lgbm": lgbm_forecaster},
        combiner=StackingCombiner(meta_forecaster=meta_model, quantiles=quantiles),
        target_column="load",
        data_splitter=splitter,
        cutoff_history=cutoff,
        evaluation_metrics=metrics,
    )

In practice you rarely build ``EnsembleForecastingModel`` by hand. The
``create_ensemble_forecasting_workflow`` preset factory does it for you from a
single ``EnsembleForecastingWorkflowConfig`` object (see `The Workflow Preset`_
below).

The Two Combiners
-----------------

``openstef-meta`` ships two concrete ``ForecastCombiner`` implementations with
different inductive biases.

WeightsCombiner
^^^^^^^^^^^^^^^

``WeightsCombiner`` treats combination as a **classification problem**. For each
quantile it trains a classifier whose job is to select (or weight) the best base
forecaster at each time step. The classifier receives the base forecasters'
predictions as features and outputs either a hard selection (one winner) or a
soft probability distribution over forecasters that is used to form a weighted
average.

Four classifier back-ends are available, each with its own hyperparameter class:

- ``LogisticCombinerHyperParams`` – logistic regression; fast, interpretable,
  good baseline.
- ``XGBCombinerHyperParams`` – XGBoost classifier; captures non-linear
  selection rules.
- ``RFCombinerHyperParams`` – random forest; robust to outliers in the
  meta-feature space.
- ``LGBMCombinerHyperParams`` – LightGBM; efficient on large datasets.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.learned_weights_combiner import (
        WeightsCombiner,
        XGBCombinerHyperParams,
    )

    combiner = WeightsCombiner(
        hparams=XGBCombinerHyperParams(n_estimators=100, max_depth=4),
        quantiles=[0.1, 0.5, 0.9],
    )

**Hard vs soft selection.** In hard mode the classifier picks exactly one base
forecaster per time step; the ensemble output equals that forecaster's
prediction. In soft mode the class probabilities become mixing weights, producing
a convex combination of all base forecasters. Soft selection is generally
smoother and more robust; hard selection can be useful when one model is clearly
dominant and interpretability of the selection rule matters.

.. note::

   ``WeightsCombiner`` exposes ``predict_contributions``, which returns the
   per-forecaster weight at each time step. This is useful for diagnosing which
   model the combiner relies on during unusual operating conditions.

StackingCombiner
^^^^^^^^^^^^^^^^

``StackingCombiner`` treats combination as a **regression problem**. It trains
one independent meta-regressor *per quantile* on top of the stacked base
forecaster outputs. Each meta-regressor sees the full vector of base predictions
for its quantile and learns an arbitrary (potentially non-linear) mapping to the
final forecast value.

The meta-regressor is any ``Forecaster`` instance — you pass a fully configured
template and the combiner clones it for each quantile:

.. code-block:: python

    from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

    meta_model = LGBMForecaster(
        hyperparams=lgbm_hparams,
        quantiles=[0.1, 0.5, 0.9],
        horizons=horizons,
    )

    combiner = StackingCombiner(
        meta_forecaster=meta_model,
        quantiles=[0.1, 0.5, 0.9],
    )

Because each quantile has its own model, ``StackingCombiner`` can learn
asymmetric combination rules: it might weight the linear model more heavily for
the upper tail (where load spikes are hard to predict) while trusting the tree
model more for the median. This flexibility makes stacking particularly effective
when the base forecasters have complementary strengths across the quantile
spectrum.

.. note:: [DIAGRAM: StackingCombiner detail — base forecaster outputs for quantile q stacked as columns, fed into a single meta-regressor that outputs the final q-th quantile prediction]

Choosing Between the Two
^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Property
     - WeightsCombiner
     - StackingCombiner
   * - Combination mechanism
     - Classifier selects/weights forecasters
     - Regressor blends forecaster outputs
   * - Per-quantile models
     - Yes (one classifier per quantile)
     - Yes (one regressor per quantile)
   * - Interpretability
     - High — feature importances show selection drivers
     - Moderate — depends on meta-model choice
   * - Training data needed
     - Moderate
     - Higher (meta-model needs sufficient out-of-fold predictions)
   * - Best when
     - One model dominates in identifiable regimes
     - Base models are complementary across quantiles

The Workflow Preset
-------------------

For most use cases, ``create_ensemble_forecasting_workflow`` is the recommended
entry point. It builds the full ``EnsembleForecastingModel`` — including
preprocessing, base forecasters, and combiner — from a single configuration
object.

.. code-block:: python

    from openstef_meta.presets.forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )
    from datetime import timedelta

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        ensemble_type="stacking",          # or "weights"
        base_models=["gblinear", "lgbm"],  # base forecaster names
        combiner_model="lgbm",             # meta-regressor back-end
        horizons=[timedelta(minutes=15 * h) for h in range(1, 97)],
        quantiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
        temperature_column="temperature_2m",
        wind_speed_column="wind_speed_80m",
        radiation_column="shortwave_radiation",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        energy_price_column="EPEX_NL",
    )

    workflow = create_ensemble_forecasting_workflow(config)

The returned ``workflow`` object is a standard ``CustomForecastingWorkflow`` that
can be passed directly to an ``openstef-beam`` pipeline for training and
backtesting.

.. note::

   ``ensemble_type="stacking"`` pairs with ``combiner_model`` to select the
   meta-regressor back-end. ``ensemble_type="weights"`` uses ``combiner_model``
   to select the classifier back-end (``"logistic"``, ``"xgboost"``, ``"rf"``,
   or ``"lgbm"``).

When to Use Ensembles vs Single Models
---------------------------------------

Ensembles are not always the right choice. Consider the trade-offs:

**Use an ensemble when:**

- You need calibrated probabilistic forecasts across a wide quantile range and
  no single model reliably covers all quantiles.
- The load series exhibits distinct operating regimes (e.g. industrial vs
  residential mix, seasonal HVAC patterns) where different model families
  excel.
- You have enough historical data to train the meta-layer without overfitting —
  as a rough guide, at least several months of 15-minute data after the
  out-of-fold split.
- Forecast accuracy improvements justify the higher training and inference cost.

**Stick with a single model when:**

- Data is scarce (short history, many missing values). The meta-layer will
  overfit.
- Latency is critical and the marginal accuracy gain does not justify running
  multiple models in parallel.
- The forecasting target is simple and one model already achieves near-optimal
  performance.
- Operational simplicity and explainability outweigh accuracy gains — a single
  model's feature importances are easier to communicate to stakeholders.

See :doc:`reliability_and_fallback` for how OpenSTEF handles the case where one
or more base forecasters fail at inference time, and :doc:`forecasting_basics`
for a broader discussion of the forecasting problem this ensemble layer is
designed to solve.

Practical Considerations
------------------------

**Out-of-fold predictions for the combiner.** The combiner must be trained on
predictions the base forecasters made on data they did *not* see during their own
training. ``EnsembleForecastingModel`` handles this automatically through its
``data_splitter`` — the base models are trained on the training fold, their
predictions on the validation fold become the combiner's training features, and
the combiner is then fitted on those out-of-fold predictions. Skipping this step
leads to a combiner that over-trusts whichever base model memorises the training
data best.

**Quantile monotonicity.** Stacking meta-regressors are trained independently
per quantile, so their raw outputs can occasionally cross (the 0.9 quantile
predicted lower than the 0.5 quantile). The ``QuantileSorter`` postprocessing
step in the default workflow corrects this automatically. See
:doc:`quantiles_and_confidence` for more on why monotonic quantiles matter.

**Feature importances.** Both combiners expose a ``feature_importances``
property that returns a ``pd.DataFrame`` indexed by base forecaster name and
quantile. Monitoring this over time reveals model drift: if the combiner
progressively down-weights a base forecaster, that model may need retraining or
replacement.

.. note:: [VISUALIZATION: Bar chart of combiner feature importances per quantile, showing relative weight assigned to each base forecaster across the quantile range]

**Computational cost.** Training N base forecasters plus a combiner takes
roughly N+1 times the wall-clock time of a single model (assuming parallelism is
available). Inference cost is similar. For very short retraining windows or
resource-constrained deployments, profile the pipeline before committing to a
large ensemble.