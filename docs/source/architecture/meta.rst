openstef_meta: Ensemble Forecasting
====================================

The ``openstef_meta`` package is the top-level orchestration layer of OpenSTEF. It
combines the validated data structures from ``openstef_core``, the model transforms
from ``openstef_models``, and the pipeline infrastructure from ``openstef_beam`` into
a single, coherent ensemble forecasting system. This page covers the three central
abstractions: :class:`EnsembleForecastingModel`, the :class:`ForecastCombiner`
hierarchy, and the :class:`EnsembleForecastingWorkflowConfig` preset system.

.. note::

   [DIAGRAM: Component-level diagram of the openstef_meta package. Show three layers from left to right: (1) "Base Forecasters" box containing individual model nodes (lgbm, xgboost, gblinear, lgbm_linear); (2) "EnsembleForecastDataset" as an intermediate aggregation node; (3) "ForecastCombiner" box containing WeightsCombiner and StackingCombiner nodes leading to a single "Ensemble Output" node. Below the diagram, show dependency arrows pointing down-left from openstef_meta to openstef_core, openstef_models, and openstef_beam, labelled "datasets/types", "transforms/workflows", and "evaluation metrics" respectively.]

For the dataset abstractions that flow through this package, see :doc:`core`.
For the transforms and individual model building blocks, see :doc:`models`.
For the distributed pipeline execution layer, see :doc:`beam`.


How the Ensemble Works
-----------------------

Training an ensemble in ``openstef_meta`` is a two-phase process managed by
:class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel`.

**Phase 1 — Base forecaster training.** Each named base forecaster is trained
independently on the input :class:`~openstef_core.datasets.TimeSeriesDataset`. After
fitting, every forecaster generates in-sample predictions, which are collected into an
:class:`~openstef_core.datasets.EnsembleForecastDataset` — a dataset whose columns are
the per-quantile outputs of each base model, plus the original target series.

**Phase 2 — Combiner training.** The :class:`~openstef_meta.models.forecast_combiners.ForecastCombiner`
is then trained on that ``EnsembleForecastDataset``. It learns how to aggregate the
base forecasters' predictions into a single, final :class:`~openstef_core.datasets.ForecastDataset`.
At inference time the same two-step flow is replayed: base forecasters predict first,
then the combiner merges their outputs.

This clean separation means you can swap combiners without retraining base models, and
you can inspect each base model's contribution independently via
:meth:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel.predict_contributions`.


EnsembleForecastingModel
-------------------------

:class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel` is
the main entry point for ensemble forecasting. It holds a dictionary of named base
forecasters and a single combiner, and exposes the standard OpenSTEF
``fit`` / ``predict`` interface.

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel

   # model is typically constructed via the preset (see below),
   # but can also be assembled manually for experimentation:
   result = model.fit(data=train_dataset, data_val=val_dataset)

   forecast = model.predict(data=live_dataset)

   # Inspect how much each base model contributed to the final prediction
   contributions = model.predict_contributions(data=live_dataset)

The ``EnsembleModelFitResult`` returned by ``fit`` bundles the individual
``ModelFitResult`` objects from every base forecaster together with the combiner's own
fit result, giving you a single artefact that captures the full training history.


The ForecastCombiner Abstraction
---------------------------------

:class:`~openstef_meta.models.forecast_combiners.ForecastCombiner` is an abstract base
class (ABC) that defines the contract every combiner must satisfy. It extends both
``BaseConfig`` (making it a Pydantic-validated configuration object) and
``Predictor[EnsembleForecastDataset, ForecastDataset]``, so it fits naturally into the
broader OpenSTEF predictor protocol.

Key interface points:

- ``fit(data, data_val, additional_features)`` — train the combiner on base-forecaster
  predictions.
- ``predict(data, additional_features)`` — produce the merged ``ForecastDataset``.
- ``predict_contributions(data, additional_features)`` — return per-quantile feature
  importances or contribution weights as a ``TimeSeriesDataset``.
- ``hparams`` — exposes the combiner's hyperparameters as a typed ``HyperParams``
  object.
- ``with_horizon(horizon)`` — create a copy configured for a different lead time,
  enabling horizon-specific combiner variants.

Two concrete implementations ship with the library.

WeightsCombiner
^^^^^^^^^^^^^^^^

:class:`~openstef_meta.models.forecast_combiners.WeightsCombiner` trains a lightweight
regression model — your choice of LightGBM, XGBoost, Random Forest, or Logistic
Regression — to learn a *weighted combination* of the base forecasters' outputs. One
model is trained per quantile, so the weights can differ across the forecast
distribution. The hyperparameter classes (``LGBMCombinerHyperParams``,
``XGBCombinerHyperParams``, ``RFCombinerHyperParams``,
``LogisticCombinerHyperParams``) are all exported from the same module and can be
passed directly to the combiner.

This combiner is the default choice. It is fast to train, interpretable through feature
importances, and robust when base forecasters are already well-calibrated.

StackingCombiner
^^^^^^^^^^^^^^^^^

:class:`~openstef_meta.models.forecast_combiners.StackingCombiner` trains a
*meta-regressor per quantile* on top of the base forecasters' predictions — a classic
stacking approach. The meta-regressor sees the full vector of base-model outputs and
learns a non-linear combination. This can capture interactions between base models that
a simple weighted average would miss, at the cost of slightly higher training complexity.

.. code-block:: python

   from openstef_meta.models.forecast_combiners import (
       StackingCombiner,
       WeightsCombiner,
       LGBMCombinerHyperParams,
   )

   # Swap the combiner on an existing model
   lgbm_hparams = LGBMCombinerHyperParams(n_estimators=200, learning_rate=0.05)
   weights_combiner = WeightsCombiner(hparams=lgbm_hparams, quantiles=[0.1, 0.5, 0.9])

   stacking_combiner = StackingCombiner(quantiles=[0.1, 0.5, 0.9])


EnsembleForecastingWorkflowConfig
-----------------------------------

Rather than assembling ``EnsembleForecastingModel`` instances by hand,
``openstef_meta`` ships a preset system built around
:class:`~openstef_meta.presets.forecasting_workflow.EnsembleForecastingWorkflowConfig`.
This Pydantic config class encodes every decision needed to build a complete
``CustomForecastingWorkflow`` — preprocessing, base forecasters, combiner, and
postprocessing — in a single, serialisable object.

Key fields:

- ``ensemble_type`` — one of ``"learned_weights"``, ``"stacking"``, or ``"rules"``.
  Selects which :class:`ForecastCombiner` implementation is instantiated.
- ``base_models`` — list of base model keys (``"lgbm"``, ``"gblinear"``,
  ``"xgboost"``, ``"lgbm_linear"``). Defaults to ``["lgbm", "gblinear"]``.
- ``combiner_model`` — the regression algorithm used inside ``WeightsCombiner``
  (``"lgbm"``, ``"rf"``, ``"xgboost"``, ``"logistic"``, ``"gblinear"``).
- ``quantiles`` — list of quantiles for probabilistic forecasting.
- ``horizons`` — list of :class:`~openstef_core.types.LeadTime` values; a separate
  model is trained per horizon.
- ``sample_interval`` — cadence of the input data (default 15 minutes).
- ``location`` — a ``LocationConfig`` used for holiday feature generation.

.. code-block:: python

   from datetime import timedelta
   from openstef_meta.presets.forecasting_workflow import EnsembleForecastingWorkflowConfig
   from openstef_core.types import LeadTime, Q

   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42",
       ensemble_type="learned_weights",
       base_models=["lgbm", "xgboost", "gblinear"],
       combiner_model="rf",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")],
       sample_interval=timedelta(minutes=15),
   )

Once you have a config, the preset function converts it into a ready-to-run
``CustomForecastingWorkflow``:

.. code-block:: python

   from openstef_meta.presets.forecasting_workflow import build_ensemble_forecasting_workflow

   workflow = build_ensemble_forecasting_workflow(config)

   # The workflow is a standard openstef_models CustomForecastingWorkflow —
   # hand it to an openstef_beam pipeline for distributed execution.
   fit_result = workflow.fit(train_dataset, val_dataset=val_dataset)
   forecast = workflow.predict(live_dataset)

.. note::

   The preset wires together a full preprocessing pipeline automatically: completeness
   and flatline checks, lag and datetime feature adders, holiday features (using the
   ``location.country_code``), outlier handling, scaling, and postprocessing steps such
   as ``QuantileSorter`` and ``ConfidenceIntervalApplicator``. You only need to override
   these if you have domain-specific requirements.

[VISUALIZATION: Side-by-side forecast plots for a 48-hour horizon showing the median prediction (Q50) and the 10th–90th percentile band from a three-model ensemble (lgbm + xgboost + gblinear with WeightsCombiner), compared against observed values.]


Dependency on the Other Packages
----------------------------------

``openstef_meta`` is intentionally the *last* layer to depend on. It imports from all
three sibling packages:

- **openstef_core** — for ``TimeSeriesDataset``, ``EnsembleForecastDataset``,
  ``ForecastDataset``, ``LeadTime``, ``Quantile``, and the ``BaseConfig`` / predictor
  protocols. See :doc:`core` for details on the dataset hierarchy.
- **openstef_models** — for the individual base forecaster implementations, all
  transform classes (``Scaler``, ``LagsAdder``, ``DatetimeFeaturesAdder``, etc.), and
  the ``CustomForecastingWorkflow`` that the preset produces. See :doc:`models` for the
  transform catalogue.
- **openstef_beam** — for evaluation metric providers (``R2Provider``,
  ``ObservedProbabilityProvider``) that are embedded in the workflow config and used
  during training to score each horizon. See :doc:`beam` for how these workflows are
  executed at scale.

This layered dependency structure means you can use ``openstef_core`` and
``openstef_models`` independently in lightweight scripts, and only pull in
``openstef_meta`` (and ``openstef_beam``) when you need full ensemble orchestration or
distributed execution.