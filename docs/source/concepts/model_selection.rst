Choosing the Right Forecasting Model
=====================================

OpenSTEF provides several forecasting model types, each with different strengths. Picking the right one — or the right combination — has a meaningful impact on forecast accuracy, training speed, and how well the model generalises to unusual conditions. This page compares the available model types, explains when each is appropriate, and shows how to configure them in code.

For background on what short-term energy forecasting involves, see :doc:`forecasting_basics`. For details on probabilistic outputs and quantiles, see :doc:`quantiles_and_confidence`.

Available Model Types
---------------------

OpenSTEF's ``openstef-models`` package provides four forecaster classes, all implementing the same ``Forecaster`` interface:

- **XGBoostForecaster** — gradient-boosted decision trees via XGBoost
- **LGBMForecaster** — gradient-boosted trees via LightGBM
- **LGBMLinearForecaster** — LightGBM with linear leaves (tree + linear hybrid)
- **GBLinearForecaster** — a linear model trained with XGBoost's ``gblinear`` booster

Each produces multi-quantile probabilistic forecasts. The choice between them is primarily about the complexity of the patterns in your data, the amount of training data available, and your tolerance for training time.

.. note:: [DIAGRAM: Decision tree showing model selection path: data volume → pattern complexity → training budget → recommended model type]

XGBoostForecaster
-----------------

``XGBoostForecaster`` uses standard gradient-boosted decision trees and is the most general-purpose option. It handles non-linear relationships well, is robust to outliers, and benefits from XGBoost's mature hyperparameter ecosystem. It supports GPU acceleration via the ``device`` field, which is useful when training over long historical windows.

**When to use it:**

- You have at least several months of historical data at your target resolution
- The load profile has clear non-linear structure (e.g., industrial sites with threshold effects)
- You want GPU-accelerated training

**Trade-offs:**

- Slower to train than LightGBM on large datasets
- Deeper trees can overfit on small datasets without careful regularisation

.. code-block:: python

    from datetime import timedelta
    from openstef_models.models.forecasting.xgboost import XGBoostForecaster, XGBoostHyperParams
    from openstef_core.datasets import LeadTime
    from openstef_core.quantiles import Quantile as Q

    forecaster = XGBoostForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime(timedelta(hours=24))],
        hyperparams=XGBoostHyperParams(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
        ),
        device="cpu",   # set to "cuda" for GPU
        n_jobs=-1,
    )

LGBMForecaster and LGBMLinearForecaster
----------------------------------------

LightGBM's leaf-wise tree growth makes ``LGBMForecaster`` significantly faster than XGBoost on large datasets while achieving comparable accuracy. It is the default choice in most OpenSTEF ensemble configurations.

``LGBMLinearForecaster`` extends this with linear leaves: each terminal node fits a linear model rather than a constant. This hybrid captures both the tree's ability to partition the feature space and linear trends within each partition. It tends to perform better on load profiles with strong linear relationships to temperature or time-of-day, while remaining competitive on non-linear data.

**When to use LGBMForecaster:**

- Large datasets (years of sub-hourly data)
- Training speed is a constraint
- General-purpose residential or commercial load profiles

**When to use LGBMLinearForecaster:**

- Strong linear relationships are present (e.g., heating/cooling loads tightly coupled to temperature)
- You want the flexibility of tree partitioning with smoother interpolation within partitions

.. code-block:: python

    from openstef_models.models.forecasting.lgbm import LGBMForecaster
    from openstef_models.models.forecasting.lgbm_linear import (
        LGBMLinearForecaster,
        LGBMLinearHyperParams,
    )

    # Standard LightGBM
    lgbm_forecaster = LGBMForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime(timedelta(hours=24))],
    )

    # LightGBM with linear leaves — useful for temperature-sensitive loads
    lgbm_linear_forecaster = LGBMLinearForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime(timedelta(hours=24))],
        hyperparams=LGBMLinearHyperParams(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
        ),
    )

GBLinearForecaster
------------------

``GBLinearForecaster`` uses XGBoost's ``gblinear`` booster, which fits a regularised linear model rather than trees. It is the simplest model in the library and trains very quickly. Its feature preprocessing pipeline deliberately excludes one-hot encoded holiday and datetime columns (which create near-singular design matrices for linear models) and uses only the 7-day lag as its primary temporal feature.

**When to use it:**

- Data is sparse or covers a short history (weeks rather than months)
- The load profile is well-approximated by a linear combination of features
- You want a fast, interpretable baseline
- It is used as a component in an ensemble alongside tree-based models

**Trade-offs:**

- Cannot capture non-linear interactions between features
- Accuracy degrades on complex industrial or mixed-use profiles
- Limited to a single forecast horizon per instance (``max_length=1`` on the ``horizons`` field)

.. code-block:: python

    from openstef_models.models.forecasting.gblinear import GBLinearForecaster, GBLinearHyperParams

    gblinear_forecaster = GBLinearForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime(timedelta(hours=24))],
        hyperparams=GBLinearHyperParams(),
        device="cpu",
    )

.. note::

   ``GBLinearForecaster`` accepts exactly one horizon. If you need multi-horizon forecasts,
   instantiate one ``GBLinearForecaster`` per horizon or use it inside an ensemble workflow.

Ensemble Models
---------------

The most robust production configuration is an ensemble that combines multiple base models. OpenSTEF's ``EnsembleForecastingWorkflowConfig`` supports three ensemble strategies:

- ``"learned_weights"`` — a combiner model (e.g., LightGBM) learns how to weight base model predictions
- ``"stacking"`` — the combiner sees base model predictions as features and learns a meta-model
- ``"rules"`` — a rule-based combiner (useful when interpretability of the combination step matters)

The default base model set is ``["lgbm", "gblinear"]``, which pairs a strong non-linear learner with a fast linear baseline. Adding ``"xgboost"`` or ``"lgbm_linear"`` increases diversity at the cost of training time.

.. code-block:: python

    from openstef_models.workflows.ensemble_forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )
    from openstef_core.quantiles import Quantile as Q
    from openstef_core.datasets import LeadTime
    from datetime import timedelta

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        ensemble_type="learned_weights",
        base_models=["lgbm", "gblinear", "xgboost"],
        combiner_model="lgbm",
        horizons=[LeadTime(timedelta(hours=h)) for h in [1, 4, 24]],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        # Automatic model selection: keep the new model only if it beats
        # the incumbent by more than the penalty factor
        model_selection_enable=True,
        model_selection_metric=("Q0.5", "R2", "higher_is_better"),
        model_selection_old_model_penalty=1.2,
    )

    workflow = create_ensemble_forecasting_workflow(config)

The ``model_selection_enable`` flag activates automatic model selection at retraining time: the newly trained model is only promoted to production if its validation metric exceeds the incumbent's score divided by the penalty factor. This prevents regressions caused by data quality issues or distribution shifts. See :doc:`reliability_and_fallback` for more on fallback strategies.

Automatic Model Selection
--------------------------

When using MLflow-backed storage, OpenSTEF can compare a freshly trained model against the currently deployed version before promoting it. The relevant configuration fields are:

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Field
     - Default
     - Description
   * - ``model_selection_enable``
     - ``True``
     - Enable/disable automatic selection
   * - ``model_selection_metric``
     - ``(Q(0.5), "R2", "higher_is_better")``
     - Quantile, metric name, and direction
   * - ``model_selection_old_model_penalty``
     - ``1.2``
     - Multiplier applied to the old model's score; new model must exceed this threshold

A penalty of ``1.2`` means the new model must score at least 20% better than the incumbent to be promoted. Raising this value makes promotion more conservative; setting it to ``1.0`` promotes any improvement.

Choosing a Starting Point
--------------------------

The following heuristics reflect patterns observed across production deployments:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Situation
     - Recommended starting model
   * - New site, limited history (< 3 months)
     - ``GBLinearForecaster`` or ``LGBMForecaster`` with conservative depth
   * - Residential aggregated load
     - ``LGBMForecaster`` or ensemble ``["lgbm", "gblinear"]``
   * - Temperature-sensitive load (heat pumps, HVAC)
     - ``LGBMLinearForecaster`` or ensemble including ``"lgbm_linear"``
   * - Industrial / complex non-linear profile
     - ``XGBoostForecaster`` or ensemble ``["xgboost", "lgbm", "gblinear"]``
   * - Production with retraining pipeline
     - Ensemble with ``model_selection_enable=True``

Start with the simplest model that fits your data characteristics. A well-tuned ``LGBMForecaster`` often matches or exceeds a poorly tuned ``XGBoostForecaster``, and the ensemble's combiner can compensate for individual model weaknesses. The feature engineering choices described in :doc:`feature_engineering` typically have a larger impact on accuracy than the choice between XGBoost and LightGBM.

.. note::

   All model types in OpenSTEF produce probabilistic forecasts across the quantiles you specify.
   There is no separate step to add uncertainty estimates — quantile regression is built into every
   forecaster. See :doc:`quantiles_and_confidence` for how to interpret and use these outputs.