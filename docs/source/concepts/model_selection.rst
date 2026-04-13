Model Selection
===============

Choosing the right forecasting model is one of the most consequential decisions you make when building an energy forecasting pipeline with OpenSTEF. This page compares the available model types, explains their trade-offs, and gives practical guidance on when to reach for each one.

For background on what short-term energy forecasting involves, see :doc:`forecasting_basics`. For an explanation of how models produce probabilistic outputs like quantile intervals, see :doc:`quantiles_and_confidence`.

.. mermaid:: diagrams/concepts/model_selection_diagram_1.mmd

Available Model Types
---------------------

OpenSTEF ships with four forecasting model classes in the ``openstef_models`` package. Each wraps a different underlying algorithm but exposes the same ``Forecaster`` interface, so switching between them requires only a configuration change.

**XGBoostForecaster**
   Tree-based gradient boosting using XGBoost. The general-purpose workhorse for most energy forecasting tasks. Handles non-linear relationships and interaction effects well, and produces reliable quantile forecasts through multi-output regression with one tree per quantile.

**LGBMForecaster**
   Tree-based gradient boosting using LightGBM. Architecturally similar to ``XGBoostForecaster`` but often faster to train on large datasets due to LightGBM's histogram-based algorithm and leaf-wise tree growth. Uses a ``MultiQuantileRegressor`` internally to produce all quantile outputs in a single pass.

**GBLinearForecaster**
   Linear model trained via XGBoost's ``gblinear`` booster. Fits a regularised linear function rather than trees. Useful when the relationship between features and load is approximately linear, or when you need a model that generalises well with limited training data.

**LGBMLinearForecaster**
   Linear-leaf variant of LightGBM — trees are grown in the usual way but each leaf fits a local linear model rather than a constant. This hybrid captures non-linear structure at the tree level while retaining linear interpolation within each leaf, which can improve accuracy on smooth, well-behaved load curves.

.. note::
   All four models are optional extras. Install the dependencies you need::

      pip install openstef-models[xgboost]   # XGBoostForecaster, GBLinearForecaster
      pip install openstef-models[lightgbm]  # LGBMForecaster, LGBMLinearForecaster

Instantiating a Model
---------------------

Every model is configured through a paired ``HyperParams`` dataclass. You construct the forecaster directly — there is no factory function or string registry to navigate:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_core.datasets import LeadTime, Quantile

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
       hyperparams=XGBoostHyperParams(
           n_estimators=200,
           max_depth=6,
           learning_rate=0.05,
       ),
   )

Switching to LightGBM requires only changing the import and the ``HyperParams`` type:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )

   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
       hyperparams=LGBMHyperParams(
           n_estimators=200,
           num_leaves=100,
           learning_rate=0.05,
       ),
   )

Because all models implement the same ``Forecaster`` base interface, the ``fit`` and ``predict`` calls are identical regardless of which class you choose.

Comparing the Models
--------------------

The table below summarises the key practical differences observed across production deployments:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Property
     - XGBoostForecaster
     - LGBMForecaster
     - GBLinearForecaster
     - LGBMLinearForecaster
   * - Non-linear patterns
     - ✓ Strong
     - ✓ Strong
     - ✗ Limited
     - ◑ Moderate
   * - Training speed (large data)
     - Moderate
     - Fast
     - Fast
     - Fast
   * - Small dataset generalisation
     - Moderate
     - Moderate
     - ✓ Good
     - ✓ Good
   * - Quantile calibration
     - Good
     - Good
     - Moderate
     - Good
   * - GPU support
     - ✓ Yes
     - ✓ Yes
     - ✓ Yes
     - ✓ Yes
   * - Multi-horizon support
     - ✓ Yes
     - ✓ Yes
     - Single horizon only
     - ✓ Yes

.. warning::
   ``GBLinearForecaster`` is restricted to a single forecast horizon (``max_length=1`` on the ``horizons`` field). If you need simultaneous forecasts at multiple lead times, use one of the tree-based models or train separate ``GBLinearForecaster`` instances per horizon.

When to Use Each Model
-----------------------

**Start with XGBoostForecaster or LGBMForecaster** for most new projects. Both handle the non-linear, seasonal, and weather-driven patterns typical of energy load data. If training time on large historical datasets becomes a bottleneck, prefer ``LGBMForecaster`` — LightGBM's leaf-wise growth and histogram binning are generally faster than XGBoost's level-wise approach at equivalent accuracy.

**Use GBLinearForecaster** when:

- Your training dataset is small (fewer than a few thousand observations) and tree models overfit.
- The load signal is dominated by a small number of well-understood linear drivers (e.g., a single large industrial consumer with predictable schedules).
- You need a fast, interpretable baseline to compare against more complex models.

**Use LGBMLinearForecaster** when:

- You have a moderately sized dataset and the load curve is smooth — the linear-leaf structure reduces the jagged step-function artefacts that pure tree models can produce.
- You want better interpolation between training samples than standard trees provide, without giving up the ability to model non-linear regime changes.

Hyperparameter Trade-offs
--------------------------

The most impactful hyperparameters are shared across all tree-based models, though the defaults differ:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import LGBMHyperParams

   # Conservative, regularised configuration — good starting point for new assets
   conservative = LGBMHyperParams(
       n_estimators=100,
       num_leaves=31,        # fewer leaves → simpler model
       learning_rate=0.1,
       reg_alpha=0.1,        # L1 regularisation
       reg_lambda=2.0,       # L2 regularisation
       min_data_in_bin=500,  # higher → smoother splits
   )

   # Expressive configuration — use when you have ample data
   expressive = LGBMHyperParams(
       n_estimators=500,
       num_leaves=100,       # default for LGBMForecaster
       learning_rate=0.03,
       reg_alpha=0.0,
       reg_lambda=1.0,
       colsample_bytree=0.8, # feature subsampling for variance reduction
   )

A few rules of thumb from production experience:

- **Reduce** ``num_leaves`` / ``max_depth`` and **increase** regularisation (``reg_alpha``, ``reg_lambda``) when you see the model performing well on training data but poorly on held-out periods.
- **Increase** ``n_estimators`` and **decrease** ``learning_rate`` together — a lower learning rate almost always benefits from more rounds to compensate.
- ``min_data_in_bin`` in ``LGBMLinearHyperParams`` defaults to 500, which is deliberately conservative. Lowering it can improve accuracy on assets with sharp load steps, but increases overfitting risk.
- Enable ``early_stopping_rounds`` on ``LGBMForecaster`` when you have a validation split available — it prevents over-training without requiring you to tune ``n_estimators`` manually:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster, LGBMHyperParams

   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=LGBMHyperParams(n_estimators=1000, learning_rate=0.02),
       early_stopping_rounds=50,  # stop if no improvement for 50 rounds
   )

   forecaster.fit(training_data, data_val=validation_data)

GPU Acceleration
----------------

All four models support GPU training through their ``device`` field. For large grids or frequent retraining cycles, this can reduce training time significantly:

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=1))],
       device="cuda",   # or "cuda:0" for a specific GPU
       n_jobs=-1,
   )

LightGBM accepts ``device="gpu"`` or ``device="cuda"`` depending on your LightGBM build. Check your installation's GPU support with ``lightgbm.basic.get_device_type()``.

Practical Recommendations
--------------------------

For a new forecasting project, a sensible progression is:

1. **Prototype with** ``LGBMForecaster`` using default hyperparameters. It trains quickly and the defaults are well-tuned for energy data.
2. **Benchmark** ``XGBoostForecaster`` against it on your validation set — for some asset types the XGBoost tree structure generalises better.
3. **Try** ``LGBMLinearForecaster`` if your load curve is smooth and you see the tree models producing unrealistically jagged intra-day profiles.
4. **Fall back to** ``GBLinearForecaster`` only if you have fewer than ~2,000 training samples or need a fast interpretable baseline.

When comparing models, evaluate on the pinball loss (also called quantile loss) across all forecast quantiles, not just RMSE on the median. A model that produces well-calibrated uncertainty intervals is often more valuable operationally than one with a marginally lower point-forecast error. See :doc:`quantiles_and_confidence` for how to interpret and evaluate quantile outputs.

For information on how features affect model accuracy — including which weather variables and calendar features matter most — see :doc:`feature_engineering`. For guidance on what happens when a model fails in production and how fallback strategies interact with model choice, see :doc:`reliability_and_fallback`.