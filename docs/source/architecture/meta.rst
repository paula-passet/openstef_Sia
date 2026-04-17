Meta Models and Ensemble Architectures
=======================================

The ``openstef_meta`` package extends OpenSTEF's forecasting capabilities beyond single-model pipelines. It provides the building blocks for **ensemble forecasting**: running multiple base forecasters in parallel, then learning how to combine their predictions into a single, higher-quality output. This page covers the design of that ensemble architecture, the available combination strategies, and how to wire them together in your own code.

For the base forecasting models and transform pipelines that serve as inputs to the ensemble, see the :doc:`models` page. For backtesting and evaluating ensemble performance, see the :doc:`beam` page.

.. note:: [DIAGRAM: Component-level diagram of the Meta workflow. Shows a ``TimeSeriesDataset`` flowing into a shared ``Preprocessing`` block, whose output fans out in parallel to N independent ``Forecaster`` instances (e.g., XGBoost, LGBMLinear). Each forecaster produces quantile predictions that are collected into an ``EnsembleForecastDataset``. This dataset feeds into a ``ForecastCombiner`` (either ``WeightsCombiner`` or ``StackingCombiner``), which outputs the final ``ForecastDataset``. A ``Postprocessing`` block sits after the combiner on the way to the final output.]


The Two-Phase Training Contract
--------------------------------

The central class in ``openstef_meta`` is ``EnsembleForecastingModel``. Its design enforces a clean two-phase training contract that mirrors how ensemble learning works in theory:

**Phase 1 — fit base forecasters.** Each configured forecaster is trained independently on the historical ``TimeSeriesDataset``. Their in-sample predictions are collected and assembled into an ``EnsembleForecastDataset`` — a specialised dataset type (defined in ``openstef_core``) that holds the stacked outputs of all base models alongside the original target.

**Phase 2 — fit the combiner.** The ``ForecastCombiner`` is trained on the ``EnsembleForecastDataset`` produced in Phase 1. It learns how to weight or re-model the base forecasters' outputs to minimise error on the training (and optionally validation) data.

This separation is important: the combiner never sees raw features directly — it only sees what the base forecasters predict. This keeps the combination layer focused on correcting systematic biases and disagreements between models rather than re-learning the underlying signal.

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel

   # After construction (see below), training is a single call:
   fit_result = model.fit(data=train_dataset, data_val=val_dataset)

   # fit_result carries metrics for every component
   print(fit_result.metrics_to_flat_dict())
   # -> {"mae": ..., "xgboost_mae": ..., "lgbm_mae": ...}

The ``EnsembleModelFitResult`` returned by ``fit()`` aggregates metrics from both the combiner and each individual base forecaster, making it straightforward to diagnose which component is underperforming.


Constructing an Ensemble Model
-------------------------------

``EnsembleForecastingModel`` is a Pydantic model, so all configuration is passed at construction time. The key fields are:

- ``forecasters`` — a ``dict[str, Forecaster]`` mapping a name to each base forecaster instance.
- ``combiner`` — a ``ForecastCombiner`` instance that defines the combination strategy.
- ``preprocessing`` — shared preprocessing applied to the input before any forecaster sees it.
- ``model_specific_preprocessing`` — a ``dict[str, list[Transform]]`` for per-forecaster transforms applied on top of the shared preprocessing.
- ``combiner_preprocessing`` — transforms applied to the ensemble dataset before the combiner is trained.
- ``target_column`` — the name of the target column in the dataset.
- ``data_splitter`` — controls how training data is split for validation.

A minimal working example using two base forecasters and a learned-weights combiner:

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
   from openstef_meta.models.forecast_combiners import WeightsCombiner, XGBCombinerHyperParams
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_models.models.forecasting.lgbm_linear_forecaster import LGBMLinearForecaster
   from openstef_core.types import Quantile

   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   horizons = [1, 4, 8, 24]  # lead times in hours

   forecasters = {
       "xgboost": XGBoostForecaster(quantiles=quantiles, horizons=horizons),
       "lgbm": LGBMLinearForecaster(quantiles=quantiles, horizons=horizons),
   }

   combiner = WeightsCombiner(
       quantiles=quantiles,
       horizons=horizons,
       hparams=XGBCombinerHyperParams(),
   )

   model = EnsembleForecastingModel(
       forecasters=forecasters,
       combiner=combiner,
       target_column="load",
       quantiles=quantiles,
   )

   fit_result = model.fit(data=train_dataset, data_val=val_dataset)
   forecast = model.predict(data=predict_dataset)


Forecast Combiners
-------------------

The ``openstef_meta.models.forecast_combiners`` module provides the combination strategies. All combiners inherit from the abstract ``ForecastCombiner`` base class, which itself implements ``ExplainableForecaster`` — meaning every combiner can report feature importances and prediction contributions, treating the base forecasters' outputs as its "features".

Two concrete combiners are available out of the box:

**WeightsCombiner**

Trains a lightweight classifier (XGBoost, LGBM, Random Forest, or Logistic Regression) per quantile to learn a weighted combination of base forecaster outputs. This is the lower-complexity option: the meta-model is intentionally simple, so it generalises well when training data is limited. The combiner family is selected via the hyperparameter class passed at construction:

.. code-block:: python

   from openstef_meta.models.forecast_combiners import (
       WeightsCombiner,
       LGBMCombinerHyperParams,
       RFCombinerHyperParams,
   )

   # LGBM-based weights combiner
   lgbm_combiner = WeightsCombiner(
       quantiles=quantiles,
       horizons=horizons,
       hparams=LGBMCombinerHyperParams(),
   )

   # Random Forest-based weights combiner
   rf_combiner = WeightsCombiner(
       quantiles=quantiles,
       horizons=horizons,
       hparams=RFCombinerHyperParams(),
   )

**StackingCombiner**

Implements full stacking: a separate meta-regressor is trained per quantile on the base forecasters' out-of-fold predictions. The meta-regressor is itself a ``Forecaster`` instance, so it can be any model supported by ``openstef_models``. This gives the combiner the full expressive power of a forecasting model, at the cost of requiring more training data to avoid overfitting.

.. code-block:: python

   from openstef_meta.models.forecast_combiners import StackingCombiner
   from openstef_models.models.forecasting.lgbm_linear_forecaster import LGBMLinearForecaster

   # The template forecaster is cloned once per quantile internally
   meta_forecaster = LGBMLinearForecaster(quantiles=quantiles, horizons=horizons)

   stacking_combiner = StackingCombiner(
       quantiles=quantiles,
       horizons=horizons,
       meta_forecaster=meta_forecaster,
   )

The ``StackingCombiner`` also supports ``predict_contributions()``, which traces how much each base forecaster contributed to the final prediction for any given time step — useful for debugging and model auditing.

.. note::

   Both combiners operate on ``EnsembleForecastDataset`` objects, not raw ``TimeSeriesDataset`` objects. You do not construct these manually; ``EnsembleForecastingModel`` assembles them internally during ``fit()`` and ``predict()``.


Preprocessing Layers
---------------------

``EnsembleForecastingModel`` supports four distinct preprocessing hooks, giving fine-grained control over the data flow:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Applied to
   * - ``preprocessing``
     - Shared input, before any base forecaster
   * - ``model_specific_preprocessing``
     - Per-forecaster, after shared preprocessing
   * - ``combiner_preprocessing``
     - Ensemble dataset, before the combiner is trained
   * - ``postprocessing`` / ``combiner_postprocessing``
     - Final predictions, after the combiner

This layered design means you can, for example, apply a common imputation step to all forecasters while still giving the XGBoost branch a sample-weighting transform that the LGBM branch does not receive.

.. code-block:: python

   from openstef_models.pipeline.transform import Imputer, NaNDropper, SampleWeighter

   common_preprocessing = [Imputer(imputation_strategy="mean"), NaNDropper()]
   model_specific_preprocessing = {
       "xgboost": [SampleWeighter(decay=0.95)],
       "lgbm": [],
   }

   model = EnsembleForecastingModel(
       forecasters=forecasters,
       combiner=combiner,
       preprocessing=common_preprocessing,
       model_specific_preprocessing=model_specific_preprocessing,
       target_column="load",
       quantiles=quantiles,
   )


Explainability
---------------

Because ``ForecastCombiner`` implements ``ExplainableForecaster``, the ensemble model exposes the same explainability interface as any single ``ForecastingModel`` in ``openstef_models``. You can retrieve feature importances and per-prediction contributions from the combiner layer:

.. code-block:: python

   # Feature importances from the combiner (base forecasters as "features")
   importances = model.get_explainable_components()

   # Per-prediction contributions (StackingCombiner only)
   contributions = stacking_combiner.predict_contributions(
       data=ensemble_dataset
   )

The ``EnsembleForecastingModel.get_explainable_components()`` method returns a ``dict[str, ExplainableForecaster]`` keyed by forecaster name, letting you drill into the explainability of each base model independently.


Choosing a Combination Strategy
---------------------------------

The right combiner depends on your data volume and the diversity of your base forecasters:

- **Use WeightsCombiner** when training data is limited, when you want a fast and interpretable combination, or when your base forecasters are already well-calibrated and you mainly need to blend their quantile estimates.
- **Use StackingCombiner** when you have sufficient historical data, when base forecasters have complementary strengths across different conditions (e.g., one model excels at peak loads, another at off-peak), and when you need the combiner to learn non-linear interactions between forecaster outputs.

In both cases, the combiner benefits from diverse base forecasters. Running two instances of the same model type with the same hyperparameters provides little benefit — the combiner has nothing to learn from their agreement.

.. note::

   The ``openstef_meta.presets`` module provides pre-configured ``EnsembleForecastingModel`` instances for common use cases, so you do not always need to assemble the components manually. Consult the API reference for available presets.


Related Pages
--------------

- :doc:`models` — The base ``Forecaster`` classes and transform pipelines used as inputs to the ensemble.
- :doc:`core` — The ``TimeSeriesDataset`` and ``EnsembleForecastDataset`` types that flow through the pipeline.
- :doc:`beam` — Backtesting and benchmarking tools for evaluating whether an ensemble genuinely outperforms its base models.