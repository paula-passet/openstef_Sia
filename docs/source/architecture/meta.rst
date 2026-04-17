The ``openstef_meta`` Package
==============================

The ``openstef_meta`` package is the top of the OpenSTEF dependency stack. It sits above
``openstef_core``, ``openstef_models``, and ``openstef_beam``, pulling them together into a
single ensemble forecasting abstraction. Where ``openstef_models`` gives you individual
forecasters and ``openstef_beam`` gives you backtesting pipelines, ``openstef_meta`` gives
you the machinery to run *multiple* forecasters in parallel and intelligently combine their
outputs into a single, more robust prediction.

This page covers the three main building blocks of the package:

- **EnsembleForecastingModel** — the orchestrator that runs base forecasters and routes their
  predictions to a combiner.
- **ForecastCombiner** — the abstract base class (ABC) that defines how predictions are merged,
  with two concrete implementations: ``WeightsCombiner`` and ``StackingCombiner``.
- **EnsembleForecastingWorkflowConfig** — the configuration object that wires everything
  together with sensible presets.

.. note::

   [DIAGRAM: Component-level diagram of the openstef_meta package. Show three layers from left to right: (1) Base Forecasters (lgbm, gblinear, xgboost, lgbm_linear) fed by common preprocessing from openstef_models; (2) ForecastCombiner ABC with two concrete implementations — WeightsCombiner and StackingCombiner — receiving an EnsembleForecastDataset; (3) Final ensemble output (ForecastDataset) after shared postprocessing. Add dependency arrows pointing inward from openstef_core (datasets, types), openstef_models (transforms, forecasters), and openstef_beam (backtesting pipelines). Label EnsembleForecastingModel as the orchestrator spanning layers 1 and 2.]

Installation
------------

``openstef_meta`` depends on all three other packages and is installed either as part of the
full framework or on its own:

.. code-block:: bash

   # Full framework (recommended)
   pip install openstef

   # Meta package only (pulls in core, models, and beam automatically)
   pip install openstef-meta


EnsembleForecastingModel
------------------------

``EnsembleForecastingModel`` is the central class of the package. It implements the same
``BaseForecastingModel`` interface as the single-model ``ForecastingModel`` in
``openstef_models``, so it can be dropped into any workflow that already works with that
interface.

Internally, training happens in two sequential phases:

1. **Phase 1 — fit base forecasters.** Each named forecaster is trained independently on the
   shared training data. Their in-sample predictions are collected into an
   ``EnsembleForecastDataset``, which is a validated dataset type from ``openstef_core`` that
   keeps the per-forecaster columns properly namespaced.

2. **Phase 2 — fit the combiner.** The combiner is trained on the ensemble dataset produced in
   Phase 1. It learns how to weight or stack the base forecasters' outputs to minimise the
   final prediction error.

At prediction time the model runs all base forecasters in parallel, assembles their outputs
into an ``EnsembleForecastDataset``, passes that to the fitted combiner, and applies shared
postprocessing (quantile sorting, confidence interval application) before returning a
``ForecastDataset``.

The model exposes a ``component_fit_results`` property on its ``EnsembleModelFitResult``
return value, giving you per-forecaster metrics alongside the combiner's own metrics — useful
for diagnosing which base model is underperforming.

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel

   # Assume `model` is a fully configured EnsembleForecastingModel instance
   # (see EnsembleForecastingWorkflowConfig below for the recommended way to build one)

   fit_result = model.fit(data=train_dataset, data_val=val_dataset)

   # Inspect per-component metrics
   for name, result in fit_result.component_fit_results.items():
       print(name, result.metrics_to_flat_dict())

   forecast = model.predict(data=predict_dataset)


ForecastCombiner: the ABC and its implementations
--------------------------------------------------

``ForecastCombiner`` is an abstract base class that defines the contract every combiner must
satisfy. It inherits from both ``BaseConfig`` (Pydantic) and ``Predictor``, so combiners are
serialisable configuration objects as well as callable predictors.

The three abstract methods are:

- ``fit(data, data_val, additional_features)`` — train the combiner on base forecaster
  predictions.
- ``predict(data, additional_features)`` — return a ``ForecastDataset`` of combined
  predictions.
- ``predict_contributions(data, additional_features)`` — return a ``TimeSeriesDataset`` where
  each column is a base forecaster's contribution to the final prediction at each timestep.
  This is the primary explainability hook.

The ``additional_features`` argument on both ``predict`` and ``fit`` lets the combiner
consume features from the original input that were not produced by any base forecaster —
for example, weather variables or calendar features that help it decide which forecaster to
trust under which conditions.

WeightsCombiner
^^^^^^^^^^^^^^^

``WeightsCombiner`` treats combination as a *classification* problem. For each quantile it
trains a classifier (LGBM, XGBoost, Random Forest, or Logistic Regression, controlled by the
``hparams`` field) that predicts which base forecaster is likely to be most accurate for a
given input sample.

It supports two operating modes:

- **Hard selection** — the combiner picks the single best forecaster for each sample.
- **Soft selection** — the combiner uses the predicted class probabilities as mixing weights,
  producing a weighted average of all base forecasters' outputs.

The ``feature_importances`` property returns a ``pd.DataFrame`` of per-quantile feature
importances from the internal classifiers, making it straightforward to understand which
input signals drive the combiner's routing decisions.

StackingCombiner
^^^^^^^^^^^^^^^^

``StackingCombiner`` takes a more direct approach: it trains a separate meta-regressor *per
quantile* on top of the base forecasters' predictions. Rather than deciding which forecaster
to trust, it learns a regression mapping from the vector of base predictions to the final
output. This is classical stacked generalisation and tends to work well when base forecasters
have complementary error patterns.

.. code-block:: python

   from openstef_meta.models.forecast_combiners import (
       ForecastCombiner,
       WeightsCombiner,
       StackingCombiner,
       LGBMCombinerHyperParams,
   )

   # WeightsCombiner with an LGBM classifier backend
   weights_combiner = WeightsCombiner(
       horizons=[...],
       quantiles=[...],
       hparams=LGBMCombinerHyperParams(),
   )

   # StackingCombiner — uses its own default meta-regressor
   stacking_combiner = StackingCombiner(
       horizons=[...],
       quantiles=[...],
   )

In practice you will rarely construct combiners directly. The
``EnsembleForecastingWorkflowConfig`` builds the right combiner for you based on the
``ensemble_type`` field.


EnsembleForecastingWorkflowConfig
----------------------------------

``EnsembleForecastingWorkflowConfig`` is the recommended entry point for building ensemble
workflows. It is a Pydantic ``BaseConfig`` object that captures every degree of freedom in
the ensemble — which base models to use, which combiner strategy to apply, what quantiles to
predict, and how to weight training samples for each component.

Key fields
^^^^^^^^^^

- ``ensemble_type`` — one of ``"learned_weights"``, ``"stacking"``, or ``"rules"``. Selects
  the combiner class. Defaults to ``"learned_weights"`` (i.e. ``WeightsCombiner``).
- ``base_models`` — a list drawn from ``"lgbm"``, ``"gblinear"``, ``"xgboost"``, and
  ``"lgbm_linear"``. Defaults to ``["lgbm", "gblinear"]``.
- ``combiner_model`` — the classifier/regressor backend for the combiner, one of ``"lgbm"``,
  ``"rf"``, ``"xgboost"``, ``"logistic"``, or ``"gblinear"``. Defaults to ``"lgbm"``.
- ``quantiles`` — list of ``Quantile`` values for probabilistic forecasting.
- ``horizons`` — list of ``LeadTime`` values. Defaults to 48 hours.
- ``sample_interval`` — temporal resolution of the input data. Defaults to 15 minutes.
- ``forecaster_sample_weights`` — a per-forecaster ``SampleWeightConfig`` dict, letting you
  apply different recency weighting schemes to different base models.

The config object is passed to a factory function that constructs the full
``CustomForecastingWorkflow``, including all preprocessing transforms, the
``EnsembleForecastingModel``, and postprocessing steps.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef_models.transforms.preprocessing import SampleWeightConfig
   from openstef_core.types import Quantile as Q, LeadTime
   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # Import the config from openstef_models (where it is defined and re-exported)
   from openstef_models.workflows.custom_forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
   )

   config = EnsembleForecastingWorkflowConfig(
       model_id="solar_ensemble_v1",
       ensemble_type="learned_weights",
       base_models=["lgbm", "xgboost", "gblinear"],
       combiner_model="lgbm",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")],
       sample_interval=timedelta(minutes=15),
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       forecaster_sample_weights={
           "lgbm": SampleWeightConfig(weight_exponent=0.0),
           "xgboost": SampleWeightConfig(weight_exponent=0.0),
           "gblinear": SampleWeightConfig(method="exponential", weight_exponent=1.0),
       },
   )

.. note::

   ``forecaster_sample_weights`` lets you give a base model a stronger recency bias
   (``weight_exponent > 0``) without affecting the others. This is useful when one model
   architecture responds better to recent regime changes than another.

Choosing a combiner strategy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The right ``ensemble_type`` depends on your data and operational constraints:

- Use ``"learned_weights"`` when you expect the relative performance of base forecasters to
  vary with observable conditions (weather regime, time of day, season). The classifier
  learns these routing rules from data.
- Use ``"stacking"`` when base forecasters have stable but complementary biases. The
  meta-regressor can learn a fixed linear or non-linear correction on top of their outputs.
- Use ``"rules"`` for interpretable, hand-crafted combination logic when you have strong
  domain knowledge and want full transparency.


How the packages fit together
------------------------------

``openstef_meta`` depends on all three sibling packages:

- **openstef_core** supplies the validated dataset types (``EnsembleForecastDataset``,
  ``ForecastDataset``, ``TimeSeriesDataset``) and the ``BaseForecastingModel`` interface that
  ``EnsembleForecastingModel`` implements. See the :doc:`core` page for details on the
  dataset hierarchy.
- **openstef_models** provides the individual base forecasters (LGBM, XGBoost, GBLinear) and
  the full transform library (lag adders, weather feature adders, scalers, etc.) used in
  common preprocessing. See the :doc:`models` page for the transform catalogue.
- **openstef_beam** provides the backtesting and evaluation infrastructure. The
  ``EnsembleForecastingWorkflowConfig`` integrates directly with BEAM's
  ``BacktestForecasterConfig`` so you can evaluate ensemble strategies over historical windows
  with the same tooling used for single-model forecasters. See the :doc:`beam` page for
  pipeline details.