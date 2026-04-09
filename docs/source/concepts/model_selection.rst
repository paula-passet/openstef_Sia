Choosing the Right Forecasting Model
=====================================

OpenSTEF provides several forecasting models optimized for short-term energy prediction. This guide helps you understand the available options, their trade-offs, and when to use each model type based on real-world deployment experience.

Understanding Model Types
--------------------------

OpenSTEF includes three primary categories of forecasting models:

**Gradient Boosting Models** are the workhorses of energy forecasting. These models excel at capturing complex non-linear relationships between weather, time patterns, and energy consumption. OpenSTEF provides two gradient boosting implementations:

- **XGBoostForecaster**: Uses XGBoost for gradient boosting with tree-based models. Offers GPU acceleration and is well-suited for large datasets.
- **LGBMForecaster**: Uses LightGBM for faster training on CPU and lower memory usage. Generally preferred for production systems with frequent retraining.

**Linear Models with Gradient Boosting** combine the interpretability of linear models with the power of boosting:

- **XGBoostLinearForecaster**: XGBoost with linear leaves instead of trees (``booster='gblinear'``).
- **LGBMLinearForecaster**: LightGBM with linear leaves, providing faster training than tree-based models while maintaining some non-linearity.

**Baseline Models** provide simple, robust predictions:

- **ConstantMedianForecaster**: Returns the median of recent historical values. Useful as a fallback or benchmark.

All models support multi-quantile forecasting, producing probabilistic predictions across multiple quantiles simultaneously (e.g., 0.1, 0.5, 0.9). See :doc:`quantiles_and_confidence` for details on probabilistic forecasting.

When to Use Each Model
-----------------------

**Use LGBMForecaster for most production deployments.** This is the default choice for energy forecasting at scale. LightGBM provides:

- Fast training times (typically 10-30 seconds for hourly retraining)
- Low memory footprint suitable for containerized deployments
- Strong performance across diverse load patterns
- Efficient CPU-only operation

**Use XGBoostForecaster when you have GPU resources** or need maximum predictive accuracy for critical forecasts. XGBoost can leverage GPU acceleration for faster training on large datasets, but requires more infrastructure setup.

**Use linear models (LGBMLinearForecaster or XGBoostLinearForecaster) when**:

- Interpretability is critical for regulatory or business requirements
- You have limited training data (linear models generalize better with small datasets)
- Your load patterns are relatively simple and linear relationships dominate

**Use ConstantMedianForecaster as a fallback** when primary models fail or during system initialization. This model requires no training and provides reasonable predictions based on recent history. See :doc:`reliability_and_fallback` for fallback strategies.

Model Performance Characteristics
----------------------------------

Based on production deployments across diverse energy systems, here are typical performance characteristics:

**Training Time** (on a typical 2-year hourly dataset with ~50 features):

- LGBMForecaster: 10-30 seconds
- XGBoostForecaster (CPU): 30-90 seconds
- XGBoostForecaster (GPU): 5-15 seconds
- Linear models: 5-15 seconds
- ConstantMedianForecaster: <1 second (no training required)

**Prediction Accuracy** (measured by R² on holdout data):

- LGBMForecaster: 0.85-0.95 for typical loads
- XGBoostForecaster: 0.85-0.96 (slightly better than LGBM)
- Linear models: 0.75-0.90 (depends heavily on feature engineering)
- ConstantMedianForecaster: 0.50-0.70 (baseline)

**Memory Usage** (during training):

- LGBMForecaster: 500MB-2GB
- XGBoostForecaster: 1GB-4GB
- Linear models: 200MB-1GB
- ConstantMedianForecaster: <100MB

These numbers vary significantly based on dataset size, number of features, and hyperparameter settings. Always benchmark on your specific data.

Creating and Comparing Models
------------------------------

Here's how to instantiate different model types and compare their performance:

.. code-block:: python

   from openstef_models.models.forecasting import (
       LGBMForecaster,
       XGBoostForecaster,
       LGBMLinearForecaster,
   )
   from openstef_core.datasets import ForecastDataset
   
   # Create models with default hyperparameters
   lgbm_model = LGBMForecaster()
   xgb_model = XGBoostForecaster()
   linear_model = LGBMLinearForecaster()
   
   # Train on your dataset
   # Assume 'train_data' is a ForecastDataset with features and target
   lgbm_model.fit(train_data)
   xgb_model.fit(train_data)
   linear_model.fit(train_data)
   
   # Generate predictions for comparison
   lgbm_forecast = lgbm_model.predict(test_data)
   xgb_forecast = xgb_model.predict(test_data)
   linear_forecast = linear_model.predict(test_data)
   
   # Evaluate using OpenSTEF metrics
   from openstef_core.metrics import r_squared, mean_absolute_error
   
   print(f"LGBM R²: {r_squared(test_data.target, lgbm_forecast['q_0.5']):.3f}")
   print(f"XGBoost R²: {r_squared(test_data.target, xgb_forecast['q_0.5']):.3f}")
   print(f"Linear R²: {r_squared(test_data.target, linear_forecast['q_0.5']):.3f}")

Customizing Hyperparameters
----------------------------

Each model type has its own hyperparameter class for tuning performance:

.. code-block:: python

   from openstef_models.models.forecasting import LGBMForecaster
   from openstef_models.models.forecasting.lgbm import LGBMHyperParams
   
   # Create custom hyperparameters for deeper trees
   hyperparams = LGBMHyperParams(
       n_estimators=200,      # More boosting rounds
       max_depth=8,           # Deeper trees (default: 6)
       learning_rate=0.05,    # Slower learning (default: 0.1)
       num_leaves=64,         # More leaf nodes (default: 31)
       min_child_samples=30,  # Minimum samples per leaf
   )
   
   # Create model with custom hyperparameters
   model = LGBMForecaster(hyperparams=hyperparams)
   model.fit(train_data)

Key hyperparameters to tune:

- **n_estimators**: Number of boosting rounds. More rounds improve accuracy but increase training time and risk overfitting.
- **max_depth**: Maximum tree depth. Deeper trees capture more complex patterns but are prone to overfitting.
- **learning_rate**: Step size for each boosting round. Lower values require more estimators but often improve generalization.
- **num_leaves** (LightGBM) / **max_leaves** (XGBoost): Controls tree complexity. More leaves capture finer patterns.

For linear models, focus on regularization parameters:

.. code-block:: python

   from openstef_models.models.forecasting import LGBMLinearForecaster
   from openstef_models.models.forecasting.lgbm_linear import LGBMLinearHyperParams
   
   hyperparams = LGBMLinearHyperParams(
       n_estimators=100,
       learning_rate=0.1,
       reg_alpha=0.1,    # L1 regularization
       reg_lambda=1.0,   # L2 regularization
   )
   
   linear_model = LGBMLinearForecaster(hyperparams=hyperparams)

Automatic Model Selection
--------------------------

OpenSTEF workflows support automatic model selection based on performance metrics. When retraining models, the system can compare the new model against the previous version and only deploy if performance improves:

.. code-block:: python

   from openstef_core.workflows import ForecastingWorkflowConfig
   from openstef_core.metrics import Q
   
   config = ForecastingWorkflowConfig(
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,  # New model must be 20% better
   )

The ``model_selection_old_model_penalty`` parameter biases selection toward newer models. For "higher_is_better" metrics like R², the old model's metric is divided by the penalty (making it easier for the new model to win). For "lower_is_better" metrics like MAE, the old model's metric is multiplied by the penalty.

This prevents unnecessary model updates when performance differences are negligible, reducing deployment churn and maintaining system stability.

Model-Specific Considerations
------------------------------

**GPU Acceleration**: XGBoostForecaster supports GPU training via the ``device`` parameter:

.. code-block:: python

   model = XGBoostForecaster(device="cuda")  # Use first GPU
   # or
   model = XGBoostForecaster(device="cuda:1")  # Use specific GPU

GPU acceleration provides 3-5x speedup on large datasets but requires CUDA-compatible hardware and drivers.

**Parallel Training**: Both XGBoost and LightGBM support multi-threaded training:

.. code-block:: python

   model = LGBMForecaster(n_jobs=-1)  # Use all available CPU cores

Be cautious with ``n_jobs=-1`` in containerized environments where CPU limits may not match available cores.

**Early Stopping**: Prevent overfitting by stopping training when validation performance plateaus:

.. code-block:: python

   model = LGBMForecaster(early_stopping_rounds=10)
   model.fit(train_data, validation_data=val_data)

Training stops if validation metrics don't improve for 10 consecutive rounds.

Next Steps
----------

- Learn about :doc:`feature_engineering` to improve model performance through better input features
- Understand :doc:`quantiles_and_confidence` for interpreting probabilistic forecasts
- Set up :doc:`reliability_and_fallback` strategies for production deployments
- Explore the API reference for detailed model parameters and methods