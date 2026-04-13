Model Selection
===============

OpenSTEF provides several forecasting model types, each with different strengths. Choosing the right model — or letting the library choose for you — can meaningfully affect forecast accuracy and training efficiency. This page explains the available model types, their trade-offs, and how to configure automatic model selection in your workflows.

For background on what short-term forecasting is and why it matters, see :doc:`forecasting_basics`. For details on how models produce probabilistic outputs, see :doc:`quantiles_and_confidence`.

Available Model Types
---------------------

OpenSTEF ships with four core forecaster implementations in ``openstef-models``. All of them support multi-quantile probabilistic forecasting and share a common interface, so they are interchangeable within a workflow configuration.

**XGBoost** (``"xgboost"``)
   The default and most battle-tested option. Uses gradient-boosted decision trees via the XGBoost library. Produces one tree per quantile per horizon (``multi_strategy="one_output_per_tree"``), which makes it straightforward to interpret and tune. Supports GPU acceleration via the ``device`` field (``"cpu"``, ``"cuda"``, ``"cuda:<ordinal>"``).

**LightGBM** (``"lgbm"``)
   A gradient-boosted tree model using the LightGBM backend. Generally trains faster than XGBoost on large datasets due to histogram-based splitting, and can be more memory-efficient. A good first alternative when XGBoost training time becomes a bottleneck.

**LightGBM with Linear Leaves** (``"lgbm_linear"``)
   Combines gradient-boosted trees with linear models at the leaves. This hybrid approach can capture both non-linear interactions (via the tree structure) and smooth linear trends within each leaf. Particularly useful for load series that exhibit strong linear relationships with temperature or price signals.

**GBLinear / XGBoost Linear** (``"gblinear"``)
   Uses XGBoost's ``gblinear`` booster, which fits a regularised linear model at each boosting round rather than trees. The resulting model is effectively a regularised linear regression with boosting. It trains quickly, generalises well on small datasets, and is the most interpretable of the four. The preprocessing pipeline for this model automatically removes one-hot encoded and cyclic datetime features to avoid near-singular design matrices.

.. mermaid:: diagrams/concepts/model_selection_diagram_1.mmd

Preprocessing Differences
--------------------------

The model type you choose also determines which preprocessing steps are applied automatically by the ``create_forecasting_workflow`` factory. This is worth understanding because it affects which features reach the model.

For ``"gblinear"``, the workflow strips holiday indicator columns and one-hot/cyclic datetime features before training. These create near-singular design matrices for linear solvers and degrade rather than improve linear model performance. Tree-based models (``"xgboost"``, ``"lgbm"``, ``"lgbm_linear"``) receive the full feature set including these columns.

See :doc:`feature_engineering` for a full description of the features OpenSTEF constructs and which ones matter most for each model family.

Configuring a Model in Code
----------------------------

The simplest way to specify a model is through ``ForecastingWorkflowConfig``. The ``model_type`` field accepts one of the string identifiers listed above:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model_type="lgbm_linear",          # choose your model here
       horizons=[0.25, 1.0, 4.0, 24.0],  # forecast horizons in hours
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

   workflow = create_forecasting_workflow(config)

Switching between model types requires only changing the ``model_type`` string. Hyperparameters are model-specific and live in dedicated fields (``xgboost_hyperparams``, ``lgbmlinear_hyperparams``, etc.), so they do not interfere with each other when you switch.

To customise hyperparameters for a specific model:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_models.models.forecasting.lgbm_linear import LGBMLinearHyperParams
   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model_type="lgbm_linear",
       horizons=[0.25, 1.0, 4.0, 24.0],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       lgbmlinear_hyperparams=LGBMLinearHyperParams(
           n_estimators=200,
           max_depth=8,
           learning_rate=0.1,
           reg_alpha=0.1,
           reg_lambda=1.0,
       ),
   )

   workflow = create_forecasting_workflow(config)

Automatic Model Selection
--------------------------

Rather than fixing a model type upfront, OpenSTEF can automatically compare a newly trained model against the currently deployed one and keep whichever performs better. This is controlled by three fields on ``ForecastingWorkflowConfig``:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model_type="xgboost",
       horizons=[0.25, 1.0, 4.0, 24.0],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       # Automatic model selection
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
       # Model reuse: skip retraining if the stored model is recent enough
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
   )

   workflow = create_forecasting_workflow(config)

``model_selection_enable`` (default ``True``) activates the comparison logic. ``model_selection_metric`` is a three-tuple of ``(quantile, metric_name, direction)`` — the example above uses median R² as the selection criterion. ``model_selection_old_model_penalty`` biases the comparison in favour of the incumbent model: the challenger must beat the stored model's score by a factor of 1.2 before it replaces it. This prevents unnecessary churn from noise in the evaluation data.

.. note::

   Automatic model selection operates on the validation split produced during training. It does not run a separate held-out evaluation. For rigorous comparison across model types, use the benchmarking utilities in ``openstef-beam``.

When to Use Each Model
-----------------------

The table below summarises practical guidance drawn from real grid operator deployments:

.. list-table::
   :header-rows: 1
   :widths: 20 30 30 20

   * - Model
     - Best suited for
     - Watch out for
     - Typical training speed
   * - ``xgboost``
     - General-purpose; large datasets; GPU available
     - Slower training on CPU for very large grids
     - Medium (fast on GPU)
   * - ``lgbm``
     - Large datasets; training time is a constraint
     - Slightly less tuning literature than XGBoost
     - Fast
   * - ``lgbm_linear``
     - Series with strong linear weather/price relationships
     - Requires more careful regularisation tuning
     - Fast
   * - ``gblinear``
     - Small datasets; interpretability required; quick iteration
     - Limited capacity for non-linear interactions
     - Very fast

A reasonable starting workflow is to begin with ``"xgboost"`` and enable ``model_selection_enable=True``. Once you have a baseline, you can introduce ``"lgbm_linear"`` as a challenger and let the selection mechanism decide per-substation which model to retain. This is the approach used in the benchmarks shipped with ``openstef-beam``.

Ensemble Workflows
------------------

For the highest accuracy, OpenSTEF also supports ensemble workflows that train multiple base models and combine their predictions with a meta-learner. The ``EnsembleForecastingWorkflowConfig`` (in ``openstef-meta``) accepts a ``base_models`` list that can include any combination of the four model types:

.. code-block:: python

   from openstef_meta.presets import EnsembleForecastingWorkflowConfig
   from openstef_models.presets.forecasting_workflow import SampleWeightConfig
   from openstef_core.types import Q

   config = EnsembleForecastingWorkflowConfig(
       model_id="ensemble_substation",
       base_models=["xgboost", "lgbm", "lgbm_linear"],
       horizons=[0.25, 1.0, 4.0, 24.0],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       forecaster_sample_weights={
           "xgboost":     SampleWeightConfig(weight_exponent=0.0),
           "lgbm":        SampleWeightConfig(weight_exponent=0.0),
           "lgbm_linear": SampleWeightConfig(weight_exponent=0.0),
       },
   )

Each base model trains independently with its own preprocessing pipeline. A combiner model (by default an XGBoost classifier/regressor) then learns how to weight each base model's predictions, potentially varying its preference by horizon or time of day.

.. note::

   Ensemble workflows require the ``openstef-meta`` package in addition to ``openstef-models``. They increase training time roughly linearly with the number of base models.

Hyperparameter Tuning
----------------------

All four model types expose their hyperparameters as typed Pydantic models (``XGBoostHyperParams``, ``LGBMLinearHyperParams``, etc.) with documented defaults. The defaults are tuned for typical grid connection load series and are a reasonable starting point for most deployments. If you need to optimise further, these objects can be passed directly to any hyperparameter search framework since they are plain Python dataclasses with typed fields.

Key hyperparameters shared across tree-based models:

- ``n_estimators`` — number of boosting rounds; increase if the model underfits, decrease to speed up training
- ``max_depth`` — maximum tree depth; deeper trees capture more interactions but overfit more easily
- ``learning_rate`` — step size per round; lower values require more estimators but often generalise better
- ``reg_alpha`` / ``reg_lambda`` — L1 and L2 regularisation; increase when features are correlated or the dataset is small

For production deployments where models retrain on a schedule, consider setting ``model_reuse_enable=True`` with an appropriate ``model_reuse_max_age`` to avoid retraining when the existing model is still fresh. See :doc:`reliability_and_fallback` for how OpenSTEF handles model failures and fallback strategies when a retrained model does not pass the selection threshold.