Meta Models and Ensemble Architectures
=======================================

The ``openstef_meta`` package extends OpenSTEF's forecasting capabilities with ensemble and meta-learning techniques. Where ``openstef_models`` provides individual forecasters, ``openstef_meta`` orchestrates *collections* of them — training base models in parallel, then learning how to combine their outputs into a single, more robust prediction. This page covers the design of that ensemble pipeline, the combiner strategies available, and how to assemble them in your own code.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd

For the individual ``Forecaster`` implementations and the transforms module that feeds into this pipeline, see the :doc:`models` sibling page. For backtesting and evaluating ensemble models at scale, see :doc:`beam`.

The Core Abstraction: ``EnsembleForecastingModel``
--------------------------------------------------

The central class in ``openstef_meta`` is ``EnsembleForecastingModel``. It implements the same ``BaseForecastingModel`` interface as any single-model forecaster, so the rest of your code does not need to know whether it is dealing with one model or ten. Internally it coordinates three stages:

1. **Common preprocessing** — a ``TransformPipeline`` applied to the raw ``TimeSeriesDataset`` before any base model sees it.
2. **Parallel base forecasters** — each named ``Forecaster`` may additionally receive its own model-specific pre- and post-processing pipeline.
3. **Combining** — a ``ForecastCombiner`` receives an ``EnsembleForecastDataset`` (the stacked predictions of all base models) and produces the final ``ForecastDataset``.

The model exposes its constituent forecasters through the ``forecaster_configs`` property (a ``dict[str, Forecaster]`` keyed by name) and supports ``predict_contributions``, which returns a ``TimeSeriesDataset`` where each column is one base model's contribution to the combined output.

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel

   # Inspect which base forecasters are registered
   model: EnsembleForecastingModel = ...  # obtained from a workflow
   print(model.forecaster_names)
   # ['lgbm', 'gblinear', 'xgboost']

   # After fitting, generate predictions
   forecast = model.predict(data=ts_dataset)

   # Decompose the combined prediction into per-model contributions
   contributions = model.predict_contributions(data=ts_dataset)
   # contributions is a TimeSeriesDataset; each column corresponds to one base model

Forecast Combiners
------------------

The combiner is the "meta" in meta-learning: it is a second-level model that learns *from the base models' predictions* rather than from raw features. All combiners share the ``ForecastCombiner`` base class and expose a consistent ``fit`` / ``predict`` / ``predict_contributions`` interface operating on ``EnsembleForecastDataset``.

``openstef_meta`` ships three concrete combiners, importable from the same sub-package:

.. code-block:: python

   from openstef_meta.models.forecast_combiners import (
       ForecastCombiner,
       StackingCombiner,
       WeightsCombiner,
       LGBMCombinerHyperParams,
       XGBCombinerHyperParams,
       RFCombinerHyperParams,
       LogisticCombinerHyperParams,
   )

Stacking Combiner
^^^^^^^^^^^^^^^^^

``StackingCombiner`` trains one independent meta-regressor *per quantile* on top of the base forecasters' outputs. You supply a template ``Forecaster`` instance; the combiner clones it once per quantile during ``model_post_init``. At prediction time each cloned regressor maps the stacked base-model predictions to a final quantile estimate.

This approach is well-suited when the relative skill of base models varies across quantiles — for example, a gradient-boosted model may be more accurate at the median while a linear model better captures tail behaviour.

.. code-block:: python

   from openstef_meta.models.forecast_combiners import StackingCombiner
   from openstef_models.models.forecasting.forecaster import Forecaster

   # Provide a configured base forecaster as the meta-regressor template
   meta_forecaster = Forecaster(...)  # e.g. an LGBMForecaster preset

   combiner = StackingCombiner(meta_forecaster=meta_forecaster)

   # The combiner is fitted on the ensemble predictions from the training split
   combiner.fit(data=ensemble_train_dataset)
   final_forecast = combiner.predict(data=ensemble_val_dataset)

   # Feature importances are aggregated across all per-quantile meta-regressors
   importances = combiner.feature_importances  # pd.DataFrame

Learned Weights Combiner
^^^^^^^^^^^^^^^^^^^^^^^^

``WeightsCombiner`` takes a classification approach. For each quantile it trains a classifier that predicts *which base forecaster is likely to perform best* for a given input. It supports two operating modes:

- **Hard selection** — the base forecaster with the highest predicted probability is chosen outright.
- **Soft selection** — predicted probabilities are used as continuous weights, blending all base forecasters proportionally.

The classifier backend is configurable via hyperparameter classes. All four options are thin wrappers that expose a ``get_classifier()`` factory method:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Hyperparams class
     - Underlying classifier
   * - ``LGBMCombinerHyperParams``
     - LightGBM gradient-boosted classifier
   * - ``RFCombinerHyperParams``
     - LightGBM random-forest classifier
   * - ``XGBCombinerHyperParams``
     - XGBoost classifier
   * - ``LogisticCombinerHyperParams``
     - Scikit-learn logistic regression

.. code-block:: python

   from openstef_meta.models.forecast_combiners import WeightsCombiner, LGBMCombinerHyperParams

   combiner = WeightsCombiner(hparams=LGBMCombinerHyperParams())
   combiner.fit(data=ensemble_train_dataset)

   # predict_contributions shows per-model weights for each sample
   weights = combiner.predict_contributions(data=ensemble_val_dataset)

Using the Preset Workflow
-------------------------

Assembling preprocessing pipelines, base forecasters, and a combiner by hand is verbose. The ``openstef_meta.presets`` module provides ``EnsembleForecastingWorkflowConfig`` and ``create_ensemble_forecasting_workflow`` as a high-level entry point that wires everything together from a declarative configuration object.

.. code-block:: python

   from datetime import timedelta
   from openstef_meta.presets.forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )
   from openstef_core.types import Q

   config = EnsembleForecastingWorkflowConfig(
       model_id="solar_ensemble_v1",
       # Choose base models and combiner strategy
       ensemble_type="stacking",          # or "learned_weights"
       base_models=["lgbm", "gblinear", "xgboost"],
       combiner_model="lgbm",
       # Forecast settings
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       sample_interval=timedelta(minutes=15),
       # Weather feature columns present in your dataset
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
   )

   workflow = create_ensemble_forecasting_workflow(config)

The returned ``CustomForecastingWorkflow`` object contains a fully configured ``EnsembleForecastingModel`` and is ready to be passed directly to a training or backtesting pipeline. The ``ensemble_type`` field accepts ``"stacking"``, ``"learned_weights"``, or ``"rules"``; the ``base_models`` field accepts any combination of ``"lgbm"``, ``"gblinear"``, ``"xgboost"``, and ``"lgbm_linear"``.

.. note::

   ``EnsembleForecastingWorkflowConfig`` also accepts per-forecaster ``SampleWeightConfig`` entries under ``forecaster_sample_weights``. This lets you apply exponential recency weighting to specific base models independently — for instance, giving a linear model more weight on recent data while keeping a tree model's weighting flat.

Data Flow and the ``EnsembleForecastDataset``
---------------------------------------------

Understanding how data moves through the pipeline helps when debugging or extending it. After common preprocessing, each base forecaster produces a ``ForecastDataset``. These are collected and merged into an ``EnsembleForecastDataset`` — a validated container whose columns are named ``<forecaster_name><sep><quantile>`` — which is then passed to the combiner.

The combiner never sees raw input features directly; it only sees the base models' predictions (and optionally ``additional_features`` passed explicitly). This clean separation means you can swap combiners without touching the base forecasters, and vice versa.

.. code-block:: python

   from openstef_core.datasets.validated_datasets import EnsembleForecastDataset

   # Manually inspect what the combiner receives during training
   ensemble_ds = EnsembleForecastDataset.from_forecast_datasets(
       forecasts={"lgbm": lgbm_forecast, "gblinear": gblinear_forecast},
       target_series=ts_dataset.data["load"],
   )
   print(ensemble_ds.data.columns.tolist())
   # ['lgbm||0.5', 'gblinear||0.5', 'load']

Explainability
--------------

Both ``StackingCombiner`` and ``WeightsCombiner`` implement ``feature_importances`` as a ``pd.DataFrame`` property. For the stacking combiner the importances are aggregated across all per-quantile meta-regressors; for the weights combiner they come from the per-quantile classifiers. ``EnsembleForecastingModel.predict_contributions`` delegates to the combiner's ``predict_contributions`` method, so the final contribution columns map back to named base forecasters rather than raw feature names — making it straightforward to answer "which model drove this prediction?".

.. code-block:: python

   # After fitting
   contributions = model.predict_contributions(data=ts_dataset)
   # Each column is a base forecaster's signed contribution to the combined output
   print(contributions.data.columns.tolist())
   # ['lgbm', 'gblinear', 'xgboost', 'load']

.. note::

   ``predict_contributions`` raises ``NotImplementedError`` if the underlying combiner does not implement the ``ContributionsMixin``. Check ``isinstance(combiner, ContributionsMixin)`` before calling it on a custom combiner.

Related Pages
-------------

- :doc:`models` — the ``Forecaster`` implementations and transform pipelines that serve as base models inside the ensemble.
- :doc:`core` — the ``TimeSeriesDataset`` and ``ForecastDataset`` types that flow through every stage of the pipeline.
- :doc:`beam` — backtesting and statistical evaluation of ensemble models, including significance testing of model changes.