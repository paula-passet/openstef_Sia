Model Selection Guide
=====================

Choosing the right forecasting model is critical for balancing accuracy, training time, and operational complexity. OpenSTEF provides three gradient boosting implementations optimized for short-term energy forecasting: XGBoost, LightGBM, and GBLinear. Each has distinct performance characteristics based on real production deployments.

This guide helps you select the appropriate model for your use case by comparing their strengths, trade-offs, and when to use each.

Available Model Types
---------------------

OpenSTEF implements three forecasting models, all based on gradient boosting but with different underlying approaches:

**XGBoostForecaster**
   Tree-based gradient boosting using XGBoost. The most widely tested model in production environments, offering strong performance across diverse load patterns. Supports GPU acceleration for faster training on large datasets.

**LGBMForecaster** and **LGBMLinearForecaster**
   Tree-based models using LightGBM with optional linear leaves. LightGBM uses histogram-based learning that can be faster than XGBoost on large datasets. The linear variant adds linear models at leaf nodes for smoother predictions.

**GBLinearForecaster**
   Linear model using XGBoost's gblinear booster. Instead of trees, this uses boosted linear regression. Simpler model structure with fewer hyperparameters, making it easier to tune and interpret.

All models support multi-quantile probabilistic forecasting, which is essential for uncertainty quantification in energy systems. See :doc:`quantiles_and_confidence` for details on probabilistic forecasts.

When to Use Each Model
----------------------

**Use XGBoostForecaster when:**

- You need proven performance across diverse scenarios
- GPU acceleration is available for large-scale training
- You have computational resources for hyperparameter tuning
- Your load patterns have complex non-linear relationships

XGBoost is the default choice for most production deployments. It handles complex interactions between features well and has extensive tuning options.

**Use LGBMForecaster or LGBMLinearForecaster when:**

- Training speed is a priority with large datasets
- Memory efficiency matters (histogram-based approach uses less memory)
- You want smoother predictions (use LGBMLinearForecaster)
- Your infrastructure supports LightGBM dependencies

LightGBM can be significantly faster on datasets with millions of rows. The linear variant is particularly useful when you expect smooth load curves without abrupt changes.

**Use GBLinearForecaster when:**

- Model interpretability is important
- You have limited data or simple load patterns
- You want faster training with fewer hyperparameters to tune
- Linear relationships dominate your forecasting problem

Linear models are easier to explain to stakeholders and require less tuning effort. They work well for loads with strong linear dependencies on features like temperature or time of day.

Model Configuration
-------------------

Each model has its own hyperparameter class for configuration. Here's how to instantiate and configure the three main models:

.. code-block:: python

   from openstef_models.models.forecasting import (
       XGBoostForecaster,
       LGBMForecaster,
       GBLinearForecaster,
   )
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMHyperParams
   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearHyperParams

   # XGBoost with custom hyperparameters
   xgb_hyperparams = XGBoostHyperParams(
       n_estimators=200,
       max_depth=8,
       learning_rate=0.1,
       reg_alpha=0.1,
       reg_lambda=1.0,
       subsample=0.8,
   )
   xgb_model = XGBoostForecaster(
       hyperparams=xgb_hyperparams,
       quantiles=[0.1, 0.5, 0.9],
       device="cuda",  # Use GPU if available
       n_jobs=-1,
   )

   # LightGBM with default hyperparameters
   lgbm_model = LGBMForecaster(
       quantiles=[0.1, 0.5, 0.9],
       n_jobs=-1,
   )

   # GBLinear for interpretable forecasts
   gblinear_hyperparams = GBLinearHyperParams(
       n_estimators=100,
       learning_rate=0.05,
   )
   gblinear_model = GBLinearForecaster(
       hyperparams=gblinear_hyperparams,
       quantiles=[0.1, 0.5, 0.9],
   )

All models follow the same training and prediction interface, making it easy to swap between them during experimentation.

Performance Trade-offs
----------------------

**Accuracy vs Speed**

Tree-based models (XGBoost, LightGBM) generally achieve higher accuracy on complex load patterns but require more training time. Linear models (GBLinear) train faster but may underperform on highly non-linear relationships.

In production benchmarks, XGBoost and LightGBM typically achieve similar accuracy, with differences often within measurement noise. The choice between them often comes down to training speed and infrastructure preferences.

**Memory vs Complexity**

LightGBM's histogram-based approach uses less memory than XGBoost's exact tree construction, making it suitable for memory-constrained environments. However, XGBoost's exact method can capture finer patterns in the data.

GBLinear has the smallest memory footprint since it doesn't build tree structures. This makes it ideal for embedded systems or edge deployments.

**Tuning Effort**

Tree-based models have many hyperparameters that interact in complex ways. Key parameters include:

- ``n_estimators``: Number of boosting rounds (more trees = longer training)
- ``max_depth``: Tree depth (deeper = more complex patterns but higher overfitting risk)
- ``learning_rate``: Step size for each boosting iteration (lower = more stable but slower convergence)
- ``reg_alpha``, ``reg_lambda``: Regularization to prevent overfitting
- ``subsample``, ``colsample_bytree``: Feature/sample sampling ratios

GBLinear has fewer hyperparameters, primarily ``n_estimators`` and ``learning_rate``, making it easier to tune. Start with defaults and adjust only if needed.

Automatic Model Selection
--------------------------

OpenSTEF supports automatic model selection based on validation performance. When enabled, the library compares old and new models using a configurable metric and automatically selects the better performer.

.. code-block:: python

   from openstef_core.workflows import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_selection_enable=True,
       model_selection_metric=("Q(0.5)", "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
   )

The ``model_selection_old_model_penalty`` parameter biases selection toward newer models. For "higher is better" metrics, the old model's score is divided by the penalty, effectively lowering the bar for the new model. This prevents sticking with old models due to minor random fluctuations.

For example, with a penalty of 1.2 and R² as the metric, a new model with R² = 0.85 would replace an old model with R² = 0.90 (since 0.85 ≥ 0.90/1.2 = 0.75).

Practical Recommendations
--------------------------

**Start with XGBoost defaults**

For most energy forecasting applications, begin with ``XGBoostForecaster`` using default hyperparameters. This provides a strong baseline with proven production performance.

**Experiment with LightGBM for large datasets**

If you're training on millions of data points or need faster iteration cycles, try ``LGBMForecaster``. Compare results against XGBoost on your validation set.

**Use GBLinear for simple loads or interpretability**

For loads with strong linear patterns (e.g., temperature-driven residential heating) or when you need to explain predictions to non-technical stakeholders, ``GBLinearForecaster`` is a good choice.

**Tune conservatively**

Avoid aggressive hyperparameter tuning unless you have strong evidence of improvement on held-out validation data. Overfitting to validation sets is a common pitfall. Focus on:

1. ``n_estimators`` and ``learning_rate`` (control training convergence)
2. ``max_depth`` (control model complexity)
3. Regularization parameters (``reg_alpha``, ``reg_lambda``) if overfitting is observed

**Monitor production performance**

Model selection shouldn't end at deployment. Use OpenSTEF's benchmarking tools to continuously monitor performance and detect degradation. See the benchmarking documentation for setting up automated performance tracking.

Next Steps
----------

- :doc:`feature_engineering` - Learn which features improve model performance
- :doc:`quantiles_and_confidence` - Understand probabilistic forecasts and quantile selection
- :doc:`reliability_and_fallback` - Implement fallback strategies when models fail