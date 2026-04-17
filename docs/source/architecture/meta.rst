The openstef_meta Package
=========================

The ``openstef_meta`` package builds ensemble forecasting on top of the three
other OpenSTEF packages. It introduces a two-phase training loop — fit N
independent base forecasters, then fit a combiner on their in-sample
predictions — and exposes the whole thing through a single
``EnsembleForecastingWorkflowConfig`` preset that mirrors the single-model
workflow from ``openstef_models``.

.. note:: [DIAGRAM: Component-level diagram of the meta package. Left column shows base forecasters (Forecaster 1 … Forecaster N) fed by common preprocessing from openstef_core. Arrows from each base forecaster flow into a ForecastCombiner (centre). The combiner produces the final EnsembleForecastDataset output (right). Dependency arrows point from the meta package down to openstef_core (types, datasets, transforms), openstef_models (base Forecaster implementations), and openstef_beam (evaluation metric providers used by the preset).]

The package is organised into three layers:

- ``openstef_meta.models`` — ``EnsembleForecastingModel`` and the
  ``ForecastCombiner`` hierarchy.
- ``openstef_meta.presets`` — ``EnsembleForecastingWorkflowConfig`` and
  ``create_ensemble_forecasting_workflow``.
- ``openstef_meta.utils`` — dataset helpers such as
  ``combine_forecast_input_datasets``.


EnsembleForecastingModel
------------------------

``EnsembleForecastingModel`` is a sibling of ``ForecastingModel`` from
``openstef_models`` — it shares the same ``BaseForecastingModel`` base class
but is not a subclass of it. The key structural difference is the
``forecaster_configs`` field: a dictionary that maps a name to a configured
``Forecaster`` object, rather than holding a single model.

Training happens in two sequential phases:

1. **Base forecaster phase** — every forecaster in ``forecaster_configs`` is
   trained independently on the same ``TimeSeriesDataset``. Their in-sample
   predictions are collected into an ``EnsembleForecastDataset``.
2. **Combiner phase** — the ``ForecastCombiner`` is trained on those
   in-sample predictions, learning how to blend the individual outputs into
   a single ``ForecastDataset``.

The ``preprocessing`` field (inherited from ``BaseForecastingModel``) holds
transforms that run *before* any base forecaster sees the data.
``model_specific_preprocessing`` adds per-forecaster transforms on top of
that shared pipeline.

.. code-block:: python

    from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
    from openstef_meta.models.forecast_combiners import WeightsCombiner
    from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig

    # Build two base forecasters using the openstef_models preset
    xgb_forecaster = create_forecasting_workflow(
        ForecastingWorkflowConfig(model="xgb", quantiles=[0.1, 0.5, 0.9])
    ).forecaster

    lgbm_forecaster = create_forecasting_workflow(
        ForecastingWorkflowConfig(model="lgbm", quantiles=[0.1, 0.5, 0.9])
    ).forecaster

    ensemble = EnsembleForecastingModel(
        forecaster_configs={
            "xgb": xgb_forecaster,
            "lgbm": lgbm_forecaster,
        },
        combiner=WeightsCombiner(),
        quantiles=[0.1, 0.5, 0.9],
    )

    fit_result = ensemble.fit(train_dataset, data_val=val_dataset)
    forecast = ensemble.predict(forecast_input)

``fit_result`` is an ``EnsembleModelFitResult``, which extends
``ModelFitResult`` with a ``component_fit_results`` property — a dictionary
of per-forecaster ``ModelFitResult`` objects. Calling
``fit_result.metrics_to_flat_dict()`` returns a single flat dictionary where
each base forecaster's metrics are prefixed with its name (e.g.
``xgb_r2``, ``lgbm_r2``), making it straightforward to log everything to an
experiment tracker in one call.


ForecastCombiner
----------------

``ForecastCombiner`` is an abstract base class that defines the contract for
the combining step. It extends both ``BaseConfig`` (Pydantic) and
``Predictor[EnsembleForecastDataset, ForecastDataset]``, so it is
serialisable and follows the same ``fit`` / ``predict`` interface used
throughout OpenSTEF.

.. code-block:: python

    from openstef_meta.models.forecast_combiners import ForecastCombiner

    class ForecastCombiner(ABC):
        def fit(
            self,
            data: EnsembleForecastDataset,
            data_val: EnsembleForecastDataset | None = None,
            additional_features: ForecastInputDataset | None = None,
        ) -> None: ...

        def predict(
            self,
            data: EnsembleForecastDataset,
            additional_features: ForecastInputDataset | None = None,
        ) -> ForecastDataset: ...

The ``additional_features`` argument lets you pass raw input features
alongside the base forecaster predictions — useful when the combiner itself
benefits from knowing the original covariates (e.g. weather variables).

Two concrete implementations are shipped out of the box.

WeightsCombiner
^^^^^^^^^^^^^^^

``WeightsCombiner`` trains a lightweight learned model — logistic regression,
random forest, XGBoost, or LightGBM — to assign per-quantile weights to the
base forecasters. The underlying algorithm is selected through a
hyperparameter dataclass:

.. code-block:: python

    from openstef_meta.models.forecast_combiners import (
        WeightsCombiner,
        LGBMCombinerHyperParams,
        XGBCombinerHyperParams,
        RFCombinerHyperParams,
        LogisticCombinerHyperParams,
    )

    # Default: logistic regression weights
    simple_combiner = WeightsCombiner()

    # Switch to a gradient-boosted combiner
    lgbm_combiner = WeightsCombiner(hparams=LGBMCombinerHyperParams())

``WeightsCombiner`` is the right choice when you expect the base forecasters
to have stable, complementary strengths — for example, one model that
performs well at short horizons and another that generalises better at longer
horizons.

StackingCombiner
^^^^^^^^^^^^^^^^

``StackingCombiner`` trains a separate meta-regressor *per quantile* on top
of the base forecasters' predictions. This is classic stacking: the combiner
has more expressive power than a weighted average and can learn non-linear
relationships between the base outputs.

.. code-block:: python

    from openstef_meta.models.forecast_combiners import StackingCombiner

    stacking = StackingCombiner()

    ensemble = EnsembleForecastingModel(
        forecaster_configs={"xgb": xgb_forecaster, "lgbm": lgbm_forecaster},
        combiner=stacking,
        quantiles=[0.1, 0.5, 0.9],
    )

Because ``StackingCombiner`` fits one model per quantile, it requires more
training data than ``WeightsCombiner``. Prefer it when you have a long
history and the base forecasters show complex, quantile-dependent
disagreements.

.. note::

   Both combiners implement ``ExplainableForecaster``, so you can call
   ``get_feature_importances()`` on the ``EnsembleForecastingModel`` to
   inspect which base forecaster contributes most to each quantile.


EnsembleForecastingWorkflowConfig
----------------------------------

The preset layer mirrors the ``ForecastingWorkflowConfig`` / ``create_forecasting_workflow``
pattern from ``openstef_models`` (see :doc:`models`). Instead of configuring
a single model, you configure a list of base workflow configs and choose a
combiner strategy.

.. code-block:: python

    from openstef_meta.presets import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )
    from openstef_models.presets import ForecastingWorkflowConfig
    from openstef_meta.models.forecast_combiners import StackingCombiner

    config = EnsembleForecastingWorkflowConfig(
        base_workflow_configs=[
            ForecastingWorkflowConfig(model="xgb", quantiles=[0.1, 0.5, 0.9]),
            ForecastingWorkflowConfig(model="lgbm", quantiles=[0.1, 0.5, 0.9]),
            ForecastingWorkflowConfig(model="linear", quantiles=[0.1, 0.5, 0.9]),
        ],
        combiner=StackingCombiner(),
        quantiles=[0.1, 0.5, 0.9],
    )

    workflow = create_ensemble_forecasting_workflow(config)

``create_ensemble_forecasting_workflow`` returns a ``CustomForecastingWorkflow``
— the same type returned by ``create_forecasting_workflow`` — so it slots
directly into any ``openstef_beam`` pipeline without modification. The beam
pipelines described in :doc:`beam` do not need to know whether the underlying
workflow wraps a single model or an ensemble.

.. note::

   The preset pulls evaluation metric providers directly from
   ``openstef_beam.evaluation.metric_providers`` (``R2Provider``,
   ``ObservedProbabilityProvider``, etc.), which is why ``openstef_beam`` is
   listed as a dependency of ``openstef_meta`` even though the meta package
   does not run Beam pipelines itself.


Dependency Relationships
------------------------

``openstef_meta`` sits at the top of the OpenSTEF dependency graph:

- **openstef_core** supplies the foundational types (``Quantile``,
  ``LeadTime``), dataset classes (``TimeSeriesDataset``,
  ``ForecastInputDataset``), and the ``TransformPipeline`` used for shared
  preprocessing. See :doc:`core` for details.
- **openstef_models** provides the concrete ``Forecaster`` implementations
  that populate ``forecaster_configs``. The preset layer imports
  ``ForecastingWorkflowConfig`` directly. See :doc:`models`.
- **openstef_beam** contributes metric providers consumed by the preset's
  evaluation configuration. The resulting workflow objects are designed to
  run inside beam pipelines. See :doc:`beam`.

Because ``openstef_meta`` depends on all three other packages, it should be
installed last and treated as the integration layer. If you only need a
single-model workflow, ``openstef_models`` alone is sufficient.

.. note::

   When using lag-based features, the ``cutoff_history`` parameter on
   ``EnsembleForecastingModel`` is critical. It controls how much historical
   data is retained when generating the in-sample predictions used to train
   the combiner. Setting it too small will cause the combiner to train on
   predictions that had insufficient lag context, leading to optimistic
   in-sample performance that does not generalise.