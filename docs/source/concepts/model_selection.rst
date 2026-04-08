Model Selection
===============

Choosing the right forecasting model is critical for balancing accuracy, training time, and operational complexity. OpenSTEF provides several model types optimized for short-term energy forecasting, each with distinct characteristics suited to different use cases.

This guide helps you understand the available models, when to use each one, and the trade-offs involved based on real-world deployment experience.

Available Model Types
---------------------

OpenSTEF includes four primary model types for energy forecasting:

**Gradient Boosting Tree Models**

- **XGBoost** (``xgboost``): Industry-standard gradient boosting with excellent accuracy and speed. The default choice for most forecasting tasks.
- **LightGBM** (``lgbm``): Microsoft's gradient boosting implementation, optimized for large datasets with faster training than XGBoost.

**Linear Models with Boosting**

- **GBLinear** (``gblinear``): XGBoost's linear booster, providing interpretable linear relationships while maintaining the XGBoost framework.
- **LGBMLinear** (``lgbmlinear``): LightGBM with linear leaves instead of decision trees, combining linear interpretability with gradient boosting.

All models support multi-quantile probabilistic forecasting out of the box, making them suitable for uncertainty estimation in energy systems.

When to Use Each Model Type
----------------------------

**Use XGBoost (default) when:**

- You need proven accuracy across diverse forecasting scenarios
- Training time is reasonable (typically minutes for hourly data)
- You want strong community support and extensive documentation
- GPU acceleration is available for large-scale deployments
- Non-linear relationships between features are expected (weather interactions, load patterns)

XGBoost has been extensively validated in production energy forecasting systems and provides the best balance of accuracy and reliability for most use cases.

**Use LightGBM when:**

- You have very large datasets (millions of samples)
- Training speed is critical (LightGBM can be 2-3x faster than XGBoost)
- Memory efficiency matters (LightGBM uses histogram-based splitting)
- You're forecasting at scale across many prediction locations

**Use GBLinear or LGBMLinear when:**

- Model interpretability is essential for stakeholder communication
- You need to explain exact feature contributions
- Relationships are primarily linear (simple load patterns, temperature sensitivity)
- Regulatory requirements demand transparent models
- You're starting with a baseline before exploring non-linear models

Linear models trade some accuracy for interpretability. They work well when the underlying physical relationships are approximately linear, such as temperature-driven load changes.

Model Configuration Example
----------------------------

Here's how to configure different model types in OpenSTEF:

.. code-block:: python

    from openstef_models.models.forecasting import (
        XGBoostForecaster,
        LGBMForecaster,
        GBLinearForecaster,
        LGBMLinearForecaster,
    )
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMHyperParams
    from openstef_core.quantiles import Q
    
    # XGBoost with custom hyperparameters (recommended starting point)
    xgb_model = XGBoostForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        hyperparams=XGBoostHyperParams(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
        ),
        n_jobs=-1,  # Use all CPU cores
    )
    
    # LightGBM for faster training on large datasets
    lgbm_model = LGBMForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        hyperparams=LGBMHyperParams(
            n_estimators=100,
            num_leaves=100,
            learning_rate=0.1,
            colsample_bytree=0.8,
        ),
        n_jobs=-1,
    )
    
    # Linear model for interpretability
    linear_model = GBLinearForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        hyperparams=XGBoostHyperParams(
            n_estimators=50,  # Fewer iterations needed for linear models
            learning_rate=0.05,
            reg_alpha=0.1,  # L1 regularization for feature selection
            reg_lambda=1.0,  # L2 regularization to prevent overfitting
        ),
    )

Performance Trade-offs
----------------------

Based on production deployments, here are typical performance characteristics:

**Accuracy**

Tree-based models (XGBoost, LightGBM) generally achieve 5-15% better accuracy than linear models on complex energy forecasting tasks with non-linear patterns. However, for simple load profiles with strong linear temperature relationships, linear models can match tree-based performance.

**Training Time**

- Linear models: Fastest, typically 10-30 seconds for hourly data
- LightGBM: 2-3x faster than XGBoost, typically 1-3 minutes
- XGBoost: Moderate, typically 2-5 minutes for standard configurations
- GPU acceleration: Can reduce XGBoost training time by 5-10x

**Inference Speed**

All models provide fast predictions (milliseconds for single forecasts). Tree-based models with many estimators may be slightly slower, but this is rarely a bottleneck in practice.

**Memory Usage**

LightGBM uses less memory than XGBoost due to histogram-based splitting. Linear models have minimal memory footprint. For most energy forecasting applications, memory is not a limiting factor.

Automatic Model Selection
--------------------------

OpenSTEF workflows support automatic model selection based on validation performance. The system can compare newly trained models against existing ones and choose the best performer:

.. code-block:: python

    from openstef_workflows.workflows.forecasting import ForecastingWorkflowConfig
    from openstef_core.quantiles import Q
    
    config = ForecastingWorkflowConfig(
        model_type="xgboost",
        model_selection_enable=True,
        model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
        model_selection_old_model_penalty=1.2,  # Bias toward new models
        model_reuse_enable=True,
        model_reuse_max_age=timedelta(days=7),
    )

The ``model_selection_old_model_penalty`` parameter applies a penalty to the old model's metric, encouraging the system to adopt new models unless the old model is significantly better. This prevents model stagnation while avoiding unnecessary changes.

Hyperparameter Tuning Considerations
-------------------------------------

When tuning hyperparameters, focus on these key parameters by model type:

**Tree-based models (XGBoost, LightGBM):**

- ``n_estimators``: More trees improve accuracy but increase training time (typical range: 50-200)
- ``max_depth`` / ``num_leaves``: Controls model complexity (deeper = more complex, higher overfitting risk)
- ``learning_rate``: Lower values require more estimators but often improve generalization (typical: 0.05-0.2)
- ``subsample`` / ``colsample_bytree``: Regularization through sampling (typical: 0.7-1.0)

**Linear models:**

- ``n_estimators``: Fewer iterations needed (typical: 20-100)
- ``reg_alpha`` / ``reg_lambda``: Critical for preventing overfitting in linear models
- ``learning_rate``: Often lower than tree models (typical: 0.01-0.1)

Start with default hyperparameters and adjust based on validation metrics. Overfitting is common in energy forecasting due to seasonal patterns—always validate on held-out time periods, not random splits.

Comparing Models in Practice
-----------------------------

To compare models systematically, train multiple model types on the same data and evaluate on a validation set:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.metrics import compute_metrics
    from openstef_core.quantiles import Q
    
    # Train multiple models
    models = {
        "xgboost": XGBoostForecaster(quantiles=[Q(0.5)]),
        "lgbm": LGBMForecaster(quantiles=[Q(0.5)]),
        "linear": GBLinearForecaster(quantiles=[Q(0.5)]),
    }
    
    results = {}
    for name, model in models.items():
        # Fit model
        fit_result = model.fit(train_data)
        
        # Make predictions
        predictions = model.predict(validation_data)
        
        # Compute metrics
        metrics = compute_metrics(
            y_true=validation_data["load"],
            y_pred=predictions,
            quantiles=[Q(0.5)],
        )
        
        results[name] = metrics
    
    # Compare R² scores
    for name, metrics in results.items():
        r2 = metrics[Q(0.5)]["R2"]
        print(f"{name}: R² = {r2:.3f}")

This systematic comparison helps identify the best model for your specific forecasting context.

Next Steps
----------

- Learn about :doc:`feature_engineering` to improve model inputs
- Understand :doc:`quantiles_and_confidence` for probabilistic forecasting
- Explore :doc:`reliability_and_fallback` for production deployments
- See :doc:`forecasting_basics` for foundational concepts