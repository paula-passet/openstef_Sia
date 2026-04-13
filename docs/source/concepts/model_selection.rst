Choosing the Right Forecasting Model
=====================================

OpenSTEF provides several forecasting model implementations, each with different inductive biases and performance characteristics. This page explains what each model does, when to prefer it, and how to configure it — so you can make an informed choice rather than defaulting to the first option you encounter.

For background on what short-term energy forecasting involves, see :doc:`forecasting_basics`. For details on probabilistic outputs that all models support, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Decision tree — data size and linearity assumptions leading to model recommendations]

Available Model Types
---------------------

OpenSTEF exposes four single-model forecasters and a flexible ensemble layer on top of them. All models implement the same ``Forecaster`` interface, so swapping between them requires only a configuration change.

**Single models**

- ``XGBoostForecaster`` — gradient-boosted decision trees via XGBoost
- ``GBLinearForecaster`` — linear booster via XGBoost (``gblinear`` booster)
- ``LGBMForecaster`` — gradient-boosted trees via LightGBM
- ``LGBMLinearForecaster`` — gradient-boosted trees with linear leaves via LightGBM

**Ensemble**

- ``EnsembleForecastingModel`` — combines any subset of the above using ``learned_weights``, ``stacking``, or ``rules`` strategies

The sections below discuss each in turn.

XGBoostForecaster
-----------------

``XGBoostForecaster`` builds an ensemble of decision trees using XGBoost's ``gbtree`` booster. It is the most widely used starting point for grid-connected load forecasting because it handles non-linear interactions between weather features and calendar patterns without manual feature engineering.

Key characteristics:

- Supports multi-quantile output via a ``one_output_per_tree`` multi-strategy, so a single training run produces the full predictive distribution.
- Accepts a ``device`` parameter (``"cpu"``, ``"cuda"``, ``"cuda:<ordinal>"``) for GPU acceleration on large datasets.
- Parallelises tree construction with ``n_jobs``; set to ``-1`` to use all available cores.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.models.forecasters.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    forecaster = XGBoostForecaster(
        hyperparams=XGBoostHyperParams(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
        ),
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT24H")],
        device="cpu",
        n_jobs=-1,
    )

**When to choose XGBoost:** It is a safe default for substations and grid connections with at least several months of historical data. The tree structure captures threshold effects (e.g. temperature below which heating load switches on) that linear models miss.

GBLinearForecaster
------------------

``GBLinearForecaster`` uses XGBoost's ``gblinear`` booster, which fits a regularised linear model at each boosting round rather than a tree. The result is a globally linear predictor with L1/L2 regularisation, trained through gradient boosting.

Key characteristics:

- Accepts only a **single horizon** (``max_length=1`` on the ``horizons`` field). If you need multiple horizons, train separate instances or use an ensemble.
- Applies an internal ``StandardScaler`` to the target before training, which improves numerical stability for load series with large absolute values.
- Much faster to train than tree-based models and produces compact, interpretable weight vectors.

.. code-block:: python

    from openstef_models.models.forecasters.gblinear_forecaster import (
        GBLinearForecaster,
        GBLinearHyperParams,
    )

    forecaster = GBLinearForecaster(
        hyperparams=GBLinearHyperParams(
            n_estimators=200,
            reg_alpha=0.1,   # L1 regularisation
            reg_lambda=1.0,  # L2 regularisation
        ),
        quantiles=[Q(0.5)],
        horizons=[LeadTime.from_string("PT24H")],
    )

**When to choose GBLinear:** Prefer this model when load behaviour is predominantly linear with respect to weather and calendar features, when training time is constrained, or when you need interpretable feature weights. It also works well as one component in an ensemble alongside a tree-based model.

.. note::

   Because ``GBLinearForecaster`` accepts only one horizon, it is most commonly used inside an ensemble rather than as a standalone model.

LGBMForecaster and LGBMLinearForecaster
----------------------------------------

LightGBM-based models often train faster than their XGBoost equivalents on large datasets because LightGBM grows trees leaf-wise rather than level-wise. OpenSTEF provides two variants:

- **LGBMForecaster** — standard gradient-boosted trees via LightGBM, analogous to ``XGBoostForecaster``.
- **LGBMLinearForecaster** — gradient-boosted trees with *linear leaves*, meaning each leaf fits a local linear model rather than a constant. This hybrid captures both non-linear splits and smooth linear trends within each leaf.

``LGBMLinearForecaster`` uses a ``MultiQuantileRegressor`` wrapper to produce simultaneous quantile outputs in a single pass, which is efficient when forecasting a wide quantile fan (e.g. nine quantiles for confidence bands).

.. code-block:: python

    from openstef_models.models.forecasters.lgbm_linear_forecaster import (
        LGBMLinearForecaster,
        LGBMLinearHyperParams,
    )

    forecaster = LGBMLinearForecaster(
        hyperparams=LGBMLinearHyperParams(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
        ),
        quantiles=[Q(0.05), Q(0.5), Q(0.95)],
        horizons=[LeadTime.from_string("PT36H")],
    )

**When to choose LGBM variants:** LightGBM models are a good choice when training throughput matters — for example, when retraining many assets on a schedule. ``LGBMLinearForecaster`` is particularly useful for solar and wind profiles where load within a regime (e.g. daytime) follows a smooth linear relationship with irradiance or wind speed.

Ensemble Models
---------------

The ``EnsembleForecastingWorkflowConfig`` lets you combine any subset of the four base models. The ensemble trains each base model independently, then uses a *combiner* to merge their predictions. Three combination strategies are available:

- **``learned_weights``** — a secondary model (``lgbm``, ``xgboost``, ``rf``, or ``logistic``) learns how to weight each base model's output. This is the most flexible option and generally performs best when base models have complementary strengths.
- **``stacking``** — a ``gblinear`` combiner is used, producing a linear combination of base model outputs. More constrained than ``learned_weights`` but less prone to overfitting the combination.
- **``rules``** — deterministic combination rules without a learned combiner. Useful when you want predictable, auditable blending behaviour.

.. code-block:: python

    from openstef_models.workflows.ensemble_forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
    )
    from openstef_core.types import LeadTime, Q

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42_ensemble",
        ensemble_type="learned_weights",
        base_models=["lgbm", "gblinear", "xgboost"],
        combiner_model="lgbm",
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
    )

The ``forecaster_sample_weights`` parameter in ``EnsembleForecastingWorkflowConfig`` controls how much each base model emphasises recent observations during training. An exponential weighting scheme (``method="exponential"``) makes a model more sensitive to recent load patterns, which is useful for assets undergoing structural change.

.. code-block:: python

    from openstef_models.workflows.ensemble_forecasting_workflow import SampleWeightConfig

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42_ensemble",
        ensemble_type="learned_weights",
        base_models=["lgbm", "gblinear", "xgboost", "lgbm_linear"],
        combiner_model="lgbm",
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.5)],
        forecaster_sample_weights={
            "gblinear": SampleWeightConfig(method="exponential", weight_exponent=1.0),
            "lgbm": SampleWeightConfig(weight_exponent=0.0),
            "xgboost": SampleWeightConfig(weight_exponent=0.0),
            "lgbm_linear": SampleWeightConfig(weight_exponent=0.0),
        },
    )

**When to choose an ensemble:** Ensembles consistently outperform single models on diverse asset portfolios in production, at the cost of longer training time and more complex debugging. Start with a single model during development; move to an ensemble once you have a stable data pipeline and want to squeeze out the last percentage points of accuracy.

Comparing the Models
--------------------

The table below summarises the practical trade-offs. Numbers are indicative — actual performance depends heavily on data quality, feature set, and hyperparameter tuning.

.. list-table::
   :header-rows: 1
   :widths: 20 16 16 16 16 16

   * - Model
     - Non-linear patterns
     - Multi-horizon
     - Training speed
     - Interpretability
     - Best for
   * - XGBoostForecaster
     - ✓ Strong
     - ✓ Yes
     - Moderate
     - Medium
     - General-purpose load
   * - GBLinearForecaster
     - ✗ Linear only
     - ✗ Single only
     - Fast
     - High
     - Linear loads, ensembles
   * - LGBMForecaster
     - ✓ Strong
     - ✓ Yes
     - Fast
     - Medium
     - High-throughput retraining
   * - LGBMLinearForecaster
     - ✓ Hybrid
     - ✓ Yes
     - Fast
     - Medium
     - Solar/wind smooth profiles
   * - Ensemble
     - ✓ Strong
     - ✓ Yes
     - Slow
     - Low
     - Production accuracy

Hyperparameter Guidance
-----------------------

All models share a common set of core hyperparameters. The defaults are reasonable starting points, but the following adjustments are worth considering:

**Tree depth (``max_depth``):** Deeper trees capture more complex interactions but overfit on small datasets. For substations with fewer than six months of 15-minute data, keep ``max_depth`` at 4–6. For large industrial consumers with clear non-linear weather dependencies, values of 8–10 are appropriate.

**Learning rate and estimators (``learning_rate``, ``n_estimators``):** Lower learning rates require more estimators but generalise better. A common production setting is ``learning_rate=0.05`` with ``n_estimators=300–500``. Avoid ``learning_rate > 0.2`` in production — it tends to overfit recent anomalies.

**Regularisation (``reg_alpha``, ``reg_lambda``):** L1 regularisation (``reg_alpha``) drives sparse feature weights and is useful when you have many correlated weather features. L2 regularisation (``reg_lambda``) smooths weight magnitudes. For ``GBLinearForecaster``, always set at least a small ``reg_lambda`` (e.g. ``1.0``) to prevent the linear booster from fitting noise.

.. note::

   OpenSTEF does not currently expose an automated hyperparameter search workflow out of the box. Tuning is the caller's responsibility. A practical approach is to run a time-series cross-validation loop over a grid of ``max_depth`` and ``n_estimators`` values using the ``BacktestForecasterConfig`` workflow.

Practical Recommendations
--------------------------

If you are starting a new forecasting project:

1. **Prototype with** ``XGBoostForecaster`` using default hyperparameters. It is the most battle-tested option and gives a reliable accuracy baseline.
2. **Add** ``GBLinearForecaster`` as a second base model once your data pipeline is stable. The two models have complementary biases and combining them in a ``learned_weights`` ensemble typically reduces RMSE by 3–8% compared to either alone.
3. **Switch to** ``LGBMForecaster`` or ``LGBMLinearForecaster`` if retraining latency becomes a bottleneck — LightGBM trains noticeably faster on datasets with millions of rows.
4. **Use a full ensemble** (all four base models) only in production, where the accuracy gain justifies the added operational complexity.

For assets with highly irregular load profiles (e.g. industrial consumers with batch processes), no single model architecture has a clear advantage. In these cases, invest in better :doc:`feature_engineering` before changing the model type — the feature set matters more than the algorithm.

For information on what happens when a model fails to produce a forecast, see :doc:`reliability_and_fallback`.