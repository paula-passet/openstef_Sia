The openstef_meta Package
=========================

The ``openstef_meta`` package is the integration layer of OpenSTEF. It composes
base forecasters from ``openstef_models`` and ``openstef_core`` into ensemble
models, provides combiners that learn how to merge those forecasts, and exposes
high-level workflow presets that wire everything together. If you are building a
production forecasting system and want more than a single model, this is the
package you reach for.

This page covers the three central abstractions: ``EnsembleForecastingModel``,
the ``ForecastCombiner`` hierarchy, and the ``EnsembleForecastingWorkflowConfig``
preset system.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd

How the ensemble is structured
-------------------------------

``EnsembleForecastingModel`` follows a three-stage pipeline:

1. **Common preprocessing** — shared feature engineering applied once before
   any base model sees the data.
2. **Parallel base forecasters** — each named forecaster runs independently and
   produces its own set of predictions.
3. **Combination** — a ``ForecastCombiner`` merges the per-model predictions
   into a single output.

The model is configured entirely through a dictionary of ``Forecaster`` objects
(one per base model) and a ``ForecastCombiner`` instance. There is no subclassing
required; behaviour is composed at construction time.

.. code-block:: python

    from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
    from openstef_meta.models.forecast_combiners import WeightsCombiner, LGBMCombinerHyperParams

    # Two base forecasters defined elsewhere (openstef_models Forecaster objects)
    forecasters = {
        "lgbm": lgbm_forecaster,
        "xgboost": xgb_forecaster,
    }

    combiner = WeightsCombiner(hyperparams=LGBMCombinerHyperParams())

    model = EnsembleForecastingModel(
        forecasters=forecasters,
        combiner=combiner,
    )

    fit_result = model.fit(train_dataset)
    forecast = model.predict(test_dataset)

After fitting, ``fit_result.component_fit_results`` gives you per-model metrics
so you can inspect how each base forecaster performed individually before
combination.


ForecastCombiner: the ABC and its implementations
---------------------------------------------------

``ForecastCombiner`` is an abstract base class that defines a single contract:
given a dataset of stacked base-model predictions, produce a combined forecast.
The two concrete implementations cover the most common ensemble strategies.

WeightsCombiner
^^^^^^^^^^^^^^^

``WeightsCombiner`` trains a *meta-learner* that assigns weights to base model
outputs. The meta-learner itself is configurable — you can back it with LightGBM,
XGBoost, a random forest, or logistic regression by swapping the hyperparams
object:

.. code-block:: python

    from openstef_meta.models.forecast_combiners import (
        WeightsCombiner,
        LGBMCombinerHyperParams,
        XGBCombinerHyperParams,
        RFCombinerHyperParams,
        LogisticCombinerHyperParams,
    )

    # LightGBM-backed combiner (default)
    lgbm_combiner = WeightsCombiner(hyperparams=LGBMCombinerHyperParams())

    # Random forest-backed combiner
    rf_combiner = WeightsCombiner(hyperparams=RFCombinerHyperParams())

The combiner is fitted on the same training data as the base models, learning
which model to trust more under different conditions (time of day, season,
load level, etc.).

StackingCombiner
^^^^^^^^^^^^^^^^

``StackingCombiner`` implements classic stacked generalisation. Base model
predictions become features for a second-level model. Unlike ``WeightsCombiner``,
stacking allows the meta-learner to exploit non-linear interactions between base
model outputs:

.. code-block:: python

    from openstef_meta.models.forecast_combiners import StackingCombiner

    stacking_combiner = StackingCombiner()

    model = EnsembleForecastingModel(
        forecasters=forecasters,
        combiner=stacking_combiner,
    )

Choosing between the two is an empirical question. ``WeightsCombiner`` is a
reasonable default because it is faster to train and easier to interpret via
feature importances. ``StackingCombiner`` can outperform it when base models
make systematically different errors that a linear combination cannot capture.

Inspecting contributions
^^^^^^^^^^^^^^^^^^^^^^^^

Both combiners support ``predict_contributions``, which returns a
``TimeSeriesDataset`` where each column is one base model's contribution to the
final forecast. This is useful for debugging and for explaining forecasts to
stakeholders:

.. code-block:: python

    contributions = model.predict_contributions(test_dataset)
    # contributions is a TimeSeriesDataset with columns ["lgbm", "xgboost"]

.. note:: [VISUALIZATION: Stacked area chart showing per-model contributions over a 48-hour forecast horizon, with the combined ensemble output overlaid as a line.]


EnsembleForecastingWorkflowConfig presets
------------------------------------------

Constructing ``EnsembleForecastingModel`` manually is flexible but verbose.
``EnsembleForecastingWorkflowConfig`` is a Pydantic config object that encodes
the most common ensemble patterns as named presets, and
``create_ensemble_forecasting_workflow`` turns that config into a ready-to-run
``CustomForecastingWorkflow``.

.. code-block:: python

    from datetime import timedelta
    from openstef_meta.presets.forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )
    from openstef_core.config import ModelIdentifier, LeadTime, Quantile as Q

    config = EnsembleForecastingWorkflowConfig(
        model_id=ModelIdentifier("my-wind-farm"),
        ensemble_type="learned_weights",   # or "stacking" / "rules"
        base_models=["lgbm", "xgboost"],
        combiner_model="lgbm",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        sample_interval=timedelta(minutes=15),
        horizons=[LeadTime.from_string("PT48H")],
    )

    workflow = create_ensemble_forecasting_workflow(config)

The three ``ensemble_type`` values map directly to combiner choices:

- ``"learned_weights"`` — ``WeightsCombiner`` with the ``combiner_model``
  backend (``lgbm``, ``rf``, ``xgboost``, ``logistic``, or ``gblinear``).
- ``"stacking"`` — ``StackingCombiner``; ``combiner_model`` selects the
  second-level learner.
- ``"rules"`` — a deterministic combiner for cases where you want explicit,
  hand-crafted combination logic rather than a learned one.

``base_models`` accepts any combination of ``"lgbm"``, ``"gblinear"``,
``"xgboost"``, and ``"lgbm_linear"``. The default pair ``["lgbm", "gblinear"]``
balances tree-based and linear inductive biases, which tends to reduce variance
on unseen load patterns.

.. note::

   ``run_name`` is an optional free-text field on the config. Set it to a
   version string or experiment tag so that model artefacts stored downstream
   (e.g. via ``openstef_beam`` pipelines) are traceable back to the config that
   produced them.


Dependency relationships
-------------------------

``openstef_meta`` sits at the top of the OpenSTEF dependency graph. It imports
from all three other packages:

- **openstef_core** — for ``ForecastInputDataset``, ``TimeSeriesDataset``,
  ``ModelIdentifier``, ``LeadTime``, and the validated dataset hierarchy that
  base forecasters consume. See the :doc:`core` page for details.
- **openstef_models** — for ``BaseForecastingModel``, the transform library,
  and ``CustomForecastingWorkflow`` that the preset system builds on. See the
  :doc:`models` page.
- **openstef_beam** — the ``EnsembleForecastingWorkflow`` produced by
  ``create_ensemble_forecasting_workflow`` can be handed directly to Beam
  pipelines for distributed training and inference. See the :doc:`beam` page.

Because ``openstef_meta`` depends on all three, it is the natural entry point
for end-to-end ensemble workflows, but it is not required if you only need a
single-model forecaster — ``openstef_models`` alone is sufficient for that case.


Combining datasets across base forecasters
-------------------------------------------

When base forecasters require different feature sets, ``openstef_meta`` provides
``combine_forecast_input_datasets`` to merge a primary ``ForecastInputDataset``
with an additional feature dataset before passing data to the ensemble:

.. code-block:: python

    from openstef_meta.utils.datasets import combine_forecast_input_datasets

    enriched = combine_forecast_input_datasets(
        input_data=base_input,
        additional_features=weather_features,
        join="inner",   # or "outer" / "left"
    )

    forecast = model.predict(enriched)

This is particularly useful when one base model relies on NWP weather features
while another uses only historical load, and you want a single dataset object
to flow through the ensemble without manually aligning columns.