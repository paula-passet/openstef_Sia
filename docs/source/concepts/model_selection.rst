Model Selection
===============

Choosing the right forecasting model is critical for balancing accuracy, training time, and operational costs. OpenSTEF provides several model types optimized for short-term energy forecasting, each with distinct characteristics that make them suitable for different scenarios.

This guide helps you understand the available models, their trade-offs, and when to use each based on real-world deployment experience.

Available Model Types
---------------------

OpenSTEF includes three primary model families for energy forecasting:

**Gradient Boosting Models**

The library provides two gradient boosting implementations that represent the state-of-the-art for energy forecasting:

- **XGBoostForecaster**: Uses XGBoost for gradient boosted tree models with quantile regression support. Offers GPU acceleration and is widely used in production deployments.
- **LGBMForecaster**: Uses LightGBM for gradient boosted trees. Generally faster training than XGBoost with comparable accuracy, especially on large datasets.
- **LGBMLinearForecaster**: Gradient boosting trees with linear leaves, combining tree-based feature interactions with linear modeling at the leaf level.

**Linear Models**

- **GBLinearForecaster**: XGBoost-based linear model using gradient boosting optimization. Provides interpretable coefficients while maintaining the quantile regression capabilities needed for probabilistic forecasting.

**Baseline Models**

- **ConstantMedianForecaster**: Returns the median of training data. Useful as a baseline for comparison and for fallback scenarios when more sophisticated models fail.

When to Use Each Model
----------------------

The choice between models depends on your specific requirements around accuracy, speed, interpretability, and operational constraints.

**Use XGBoostForecaster when:**

- Maximum accuracy is the priority
- You have GPU resources available for training acceleration
- Training time is not a critical constraint
- You need robust handling of non-linear relationships and complex feature interactions
- Your deployment can handle larger model sizes (typically 5-50 MB)

XGBoost has proven highly effective in production for solar, wind, and load forecasting where capturing weather-load relationships is critical.

**Use LGBMForecaster when:**

- You need fast training times with accuracy comparable to XGBoost
- Working with large datasets (millions of rows)
- Memory efficiency is important
- CPU-only environments where LightGBM's optimizations shine
- You're training many models in parallel (e.g., hundreds of substations)

LightGBM typically trains 2-5x faster than XGBoost on CPU while achieving similar accuracy, making it the preferred choice for large-scale deployments.

**Use LGBMLinearForecaster when:**

- You want gradient boosting performance with more linear behavior
- Feature interactions are important but you want some model interpretability
- Your data has strong linear trends that pure tree models might overfit

**Use GBLinearForecaster when:**

- Model interpretability is required (e.g., for regulatory compliance)
- You need to understand feature importance with coefficient values
- Your forecasting problem has strong linear relationships
- Model size must be minimal (linear models are typically <1 MB)
- Fast prediction time is critical (linear models predict 10-100x faster than tree models)

**Use ConstantMedianForecaster when:**

- Establishing baseline performance metrics
- Implementing fallback strategies (see :doc:`reliability_and_fallback`)
- Testing pipeline infrastructure without model complexity
- Handling edge cases where insufficient training data exists

Performance Characteristics
---------------------------

Based on production deployments across multiple grid operators, here are typical performance profiles:

**Training Time** (on 2 years of 15-minute data, ~70,000 samples):

- LGBMForecaster: 10-30 seconds
- XGBoostForecaster (CPU): 30-90 seconds  
- XGBoostForecaster (GPU): 5-15 seconds
- GBLinearForecaster: 5-10 seconds
- LGBMLinearForecaster: 15-40 seconds

**Prediction Time** (for 48-hour forecast):

- All gradient boosting models: 50-200 ms
- Linear models: 5-20 ms
- ConstantMedianForecaster: <1 ms

**Accuracy** (typical R² on validation data):

- XGBoostForecaster / LGBMForecaster: 0.85-0.95 for load, 0.75-0.90 for solar
- LGBMLinearForecaster: 0.80-0.92 for load, 0.70-0.85 for solar
- GBLinearForecaster: 0.75-0.88 for load, 0.65-0.80 for solar
- ConstantMedianForecaster: 0.20-0.50 (baseline)

Actual performance varies significantly based on data quality, feature engineering (see :doc:`feature_engineering`), and the specific forecasting problem.

Configuring Models
------------------

All forecasting models in OpenSTEF share a common configuration pattern using hyperparameters:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster, LGBMForecaster
   from openstef_models.models.forecasting import GBLinearForecaster
   
   # Configure XGBoost with custom hyperparameters
   xgb_model = XGBoostForecaster(
       hyperparams={
           "n_estimators": 100,
           "max_depth": 6,
           "learning_rate": 0.1,
           "subsample": 0.8,
       },
       n_jobs=-1,  # Use all CPU cores
       device="cuda",  # Enable GPU acceleration
   )
   
   # Configure LightGBM for faster training
   lgbm_model = LGBMForecaster(
       hyperparams={
           "n_estimators": 100,
           "num_leaves": 31,
           "learning_rate": 0.1,
       },
       n_jobs=-1,
   )
   
   # Configure linear model for interpretability
   linear_model = GBLinearForecaster(
       hyperparams={
           "n_estimators": 50,
           "learning_rate": 0.05,
       }
   )

Each model type has specific hyperparameters optimized for its underlying algorithm. The defaults are tuned for typical energy forecasting scenarios but should be adjusted based on your data characteristics.

Model Selection in Workflows
-----------------------------

OpenSTEF's workflow system includes automatic model selection that compares new models against existing ones based on validation metrics:

.. code-block:: python

   from openstef_workflows.workflows import ForecastingWorkflowConfig
   from openstef_core.enums import Q
   
   config = ForecastingWorkflowConfig(
       model_type="xgb",
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
   )

The ``model_selection_old_model_penalty`` parameter biases selection toward newer models by requiring them to be only slightly better (e.g., 1/1.2 = 83% of old model performance) rather than strictly better. This prevents model stagnation while avoiding frequent switches that could destabilize forecasts.

When ``model_selection_enable=True``, the workflow automatically:

1. Trains a new model on recent data
2. Evaluates both old and new models on validation data
3. Compares performance using the specified metric
4. Selects the better model accounting for the penalty factor
5. Stores the selected model for production use

This automated selection is particularly valuable when retraining models regularly (e.g., daily or weekly) as data patterns evolve.

Switching Between Models
-------------------------

You can easily switch model types by changing the configuration without modifying your pipeline code:

.. code-block:: python

   from openstef_workflows.workflows import create_forecasting_workflow
   
   # Start with XGBoost for maximum accuracy
   config = ForecastingWorkflowConfig(
       model_type="xgb",
       target_column="load",
   )
   workflow = create_forecasting_workflow(config)
   
   # Later switch to LightGBM for faster training
   config.model_type = "lgbm"
   workflow = create_forecasting_workflow(config)
   
   # Or use linear model for interpretability
   config.model_type = "linear"
   workflow = create_forecasting_workflow(config)

All models support the same quantile forecasting interface (see :doc:`quantiles_and_confidence`), so switching models doesn't require changes to downstream code that consumes predictions.

Practical Recommendations
--------------------------

Based on operational experience, here are guidelines for common scenarios:

**Starting a new forecasting project:**

Begin with ``LGBMForecaster`` with default hyperparameters. It provides excellent accuracy with fast iteration cycles during development. Once your pipeline is stable, experiment with ``XGBoostForecaster`` if you need the last few percentage points of accuracy.

**Large-scale deployments (100+ models):**

Use ``LGBMForecaster`` for training speed and memory efficiency. Consider training models in parallel using workflow orchestration. Monitor training times and set appropriate timeouts to prevent resource exhaustion.

**Regulatory or audit requirements:**

Use ``GBLinearForecaster`` to provide interpretable feature coefficients. Document the relationship between weather variables and load predictions using the model's linear weights. Combine with feature importance analysis for comprehensive explainability.

**Resource-constrained environments:**

Use ``GBLinearForecaster`` for minimal model size and fast predictions. If accuracy is insufficient, try ``LGBMForecaster`` with reduced ``n_estimators`` (e.g., 50 instead of 100) to balance performance and resource usage.

**High-frequency retraining:**

Enable automatic model selection to prevent performance degradation while avoiding unnecessary model updates. Set ``model_selection_old_model_penalty`` between 1.1-1.3 to balance stability and adaptation to changing patterns.

Next Steps
----------

- Learn about :doc:`feature_engineering` to improve model accuracy regardless of model type
- Understand :doc:`quantiles_and_confidence` for probabilistic forecasting with all model types
- Implement :doc:`reliability_and_fallback` strategies for production deployments
- Explore :doc:`forecasting_basics` for foundational concepts

Remember that model selection is just one aspect of forecasting performance. High-quality features, proper data preprocessing, and robust operational practices often matter more than the specific algorithm choice.