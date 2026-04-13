Model Selection
===============

OpenSTEF provides several forecasting model implementations, each with different strengths. Choosing the right model — or letting the library choose for you — can meaningfully affect forecast accuracy, training speed, and operational robustness. This page explains the available model types, their trade-offs, and how to configure model selection in your workflows.

For background on what short-term energy forecasting involves, see :doc:`forecasting_basics`. For probabilistic output and quantile configuration, see :doc:`quantiles_and_confidence`.

Available Model Types
---------------------

OpenSTEF ships four forecaster classes, all implementing the same ``Forecaster`` base interface. This means they are interchangeable in any workflow configuration.

**LGBMForecaster** (LightGBM gradient-boosted trees)
   The default and most broadly applicable model. LightGBM trains quickly on large datasets, handles missing values gracefully, and produces competitive accuracy on typical energy load profiles. It supports multi-quantile output natively and can leverage GPU acceleration via the ``device`` parameter. Early stopping is available through ``early_stopping_rounds``, which helps prevent overfitting on noisy meter data.

**XGBoostForecaster** (XGBoost gradient-boosted trees)
   A tree-based alternative to LightGBM. XGBoost uses a ``one_output_per_tree`` multi-output strategy and applies magnitude-weighted pinball loss by default, which can improve calibration on loads with high variance. Training is generally slower than LightGBM at equivalent depth, but XGBoost is a mature library with extensive community support and is a reliable fallback when LightGBM produces unexpected results.

**GBLinearForecaster** (XGBoost with linear booster)
   A linear model built on XGBoost's ``gblinear`` booster. Unlike the tree-based models, this forecaster is constrained to a single forecast horizon (``max_length=1``). It trains fast, is highly interpretable, and generalises well on loads that are approximately linear in their features — for example, small industrial consumers or substations with stable, predictable patterns. It is often used as a base model inside ensembles precisely because its bias is structurally different from tree models.

**LGBMLinearForecaster** (LightGBM with linear booster)
   Similar in spirit to ``GBLinearForecaster`` but built on LightGBM's linear tree variant. Useful when you want the speed and ecosystem of LightGBM combined with linear inductive bias.

.. mermaid:: diagrams/concepts/model_selection_diagram_1.mmd

Instantiating Models Directly
------------------------------

Because OpenSTEF is a library, you can instantiate any forecaster directly and embed it in your own code:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.forecasters.lgbm import LGBMForecaster
   from openstef_models.forecasters.xgboost import XGBoostForecaster
   from openstef_models.forecasters.gblinear import GBLinearForecaster
   from openstef_core.quantiles import Q
   from openstef_core.lead_time import LeadTime

   # LightGBM — good general-purpose starting point
   lgbm_forecaster = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=24))],
       early_stopping_rounds=50,
       n_jobs=-1,  # use all cores
   )

   # XGBoost — tree-based alternative
   xgb_forecaster = XGBoostForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=24))],
   )

   # GBLinear — single-horizon linear model
   gblinear_forecaster = GBLinearForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=24))],  # must be exactly one horizon
   )

All three expose the same ``.fit()`` and ``.predict()`` interface, so switching between them in experiments requires only changing the instantiation line.

Workflow-Level Model Configuration
------------------------------------

When using OpenSTEF's built-in workflow classes, the model type is declared in the workflow configuration object. The ``ForecastingWorkflowConfig`` accepts a ``model_type`` field that selects the underlying forecaster:

.. code-block:: python

   from openstef_models.workflows.forecasting_workflow import ForecastingWorkflowConfig
   from openstef_core.quantiles import Q
   from openstef_core.lead_time import LeadTime
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model_type="lgbm",           # "lgbm" | "xgboost" | "gblinear" | "lgbm_linear"
       quantiles=[Q(0.05), Q(0.5), Q(0.95)],
       horizons=[LeadTime(timedelta(hours=36))],
   )

Automatic Model Selection
--------------------------

OpenSTEF can automatically compare a newly trained model against the currently deployed model and retain whichever performs better. This behaviour is controlled by three fields in the workflow configuration:

.. code-block:: python

   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model_type="lgbm",
       quantiles=[Q(0.5)],
       horizons=[LeadTime(timedelta(hours=36))],
       # Automatic model selection settings
       model_selection_enable=True,          # default: True
       model_selection_metric=(              # (quantile, metric_name, direction)
           Q(0.5), "R2", "higher_is_better"
       ),
       model_selection_old_model_penalty=1.2,  # new model must beat old by 20%
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
   )

When ``model_selection_enable=True``, the pipeline evaluates the freshly trained model against the validation set and compares its R² score to the currently stored model. The ``model_selection_old_model_penalty`` introduces a deliberate bias toward keeping the existing model: a penalty of ``1.2`` means the new model's score is multiplied by ``1/1.2`` before comparison, so it must outperform the old model by at least 20% to be promoted. This guards against deploying a model that wins on a single retraining run due to noise.

.. note::

   ``model_reuse_max_age`` sets a hard ceiling: even if the old model is still winning on metrics, it will be replaced after the configured number of days. This ensures the model stays current with seasonal patterns and grid changes.

Ensemble Models
----------------

For production deployments where accuracy is critical, OpenSTEF supports ensemble workflows that combine multiple base models. The ``EnsembleForecastingWorkflowConfig`` lets you specify a list of base models and a combiner:

.. code-block:: python

   from openstef_models.workflows.ensemble_forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
   )
   from openstef_core.quantiles import Q
   from openstef_core.lead_time import LeadTime
   from datetime import timedelta

   ensemble_config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42_ensemble",
       ensemble_type="learned_weights",   # "learned_weights" | "stacking" | "rules"
       base_models=["lgbm", "gblinear"],  # any combination of available model types
       combiner_model="lgbm",             # meta-learner that combines base predictions
       quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],
       horizons=[LeadTime(timedelta(hours=36))],
   )

The ``learned_weights`` ensemble type trains a meta-model (the ``combiner_model``) to weight the base model predictions. Pairing ``lgbm`` with ``gblinear`` is a common and effective combination: the tree model captures non-linear interactions while the linear model provides a stable, interpretable baseline. The structural difference in their biases means their errors tend to be uncorrelated, which is the core requirement for effective ensembling.

For ``stacking`` ensembles, ``gblinear`` is the recommended combiner because it produces a linear combination of base predictions, which is both interpretable and less prone to overfitting the meta-learning step.

Choosing a Model: Practical Guidance
--------------------------------------

The table below summarises the key trade-offs. "Load type" refers to the electricity load profile at the forecasting point.

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Model
     - Best for
     - Training speed
     - Interpretability
     - Multi-horizon
   * - ``lgbm``
     - Most load types; default choice
     - Fast
     - Moderate
     - Yes
   * - ``xgboost``
     - High-variance loads; XGBoost ecosystem
     - Moderate
     - Moderate
     - Yes
   * - ``gblinear``
     - Linear/stable loads; ensemble base
     - Very fast
     - High
     - No (single horizon)
   * - ``lgbm_linear``
     - Linear loads with LightGBM tooling
     - Fast
     - High
     - No (single horizon)
   * - Ensemble
     - Production; accuracy-critical sites
     - Slow (trains N+1 models)
     - Low
     - Yes

A practical decision process:

- **Start with ``lgbm``**. It is the default for good reason: fast iteration, solid accuracy across diverse load profiles, and native support for early stopping.
- **Switch to ``xgboost``** if you observe that LightGBM is poorly calibrated on your validation quantiles, or if your team already has XGBoost infrastructure.
- **Use ``gblinear`` or ``lgbm_linear`` as base models in ensembles**, not as standalone models for complex loads. Their value is in providing diverse, low-variance predictions that complement tree models.
- **Use an ensemble** when you are deploying to a high-value substation or when a single model's accuracy is insufficient after hyperparameter tuning.
- **Enable automatic model selection** in all production pipelines. The penalty factor means you lose very little by enabling it, and it prevents accidental regressions during retraining.

Hyperparameter Tuning
----------------------

Each model exposes its hyperparameters through a dedicated ``HyperParams`` class (``XGBoostHyperParams``, ``LGBMHyperParams``, ``GBLinearHyperParams``). The most impactful parameters across all tree-based models are ``n_estimators``, ``learning_rate``, and ``max_depth``. For LightGBM specifically, ``early_stopping_rounds`` is often more effective than tuning ``n_estimators`` directly, since it adapts the stopping point to each dataset.

.. code-block:: python

   from openstef_models.forecasters.lgbm import LGBMForecaster
   from openstef_models.forecasters.lgbm import LGBMHyperParams
   from openstef_core.quantiles import Q
   from openstef_core.lead_time import LeadTime
   from datetime import timedelta

   forecaster = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=24))],
       hyperparams=LGBMHyperParams(
           n_estimators=500,
           learning_rate=0.05,
           max_depth=8,
       ),
       early_stopping_rounds=30,
       random_state=42,
   )

.. note::

   Setting ``random_state`` (or ``seed`` for LightGBM) is important for reproducible experiments. Without it, small differences in training data order can produce noticeably different models across runs, making it harder to attribute accuracy changes to configuration changes.

Related Topics
--------------

- :doc:`feature_engineering` — the features fed to these models matter as much as the model choice itself; this page covers weather variables, lag features, and calendar encodings.
- :doc:`quantiles_and_confidence` — all models in OpenSTEF support probabilistic output; see this page for how to configure and interpret quantile forecasts.
- :doc:`reliability_and_fallback` — production deployments need fallback strategies for when a model fails or produces out-of-range predictions; see this page for how OpenSTEF handles that.