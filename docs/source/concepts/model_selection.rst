Model Selection
===============

Choosing the right forecasting model is critical for accurate short-term energy predictions. OpenSTEF provides multiple model types, each with distinct characteristics that make them suitable for different forecasting scenarios. This guide helps you understand when to use each model type and how to configure them for optimal performance.

Available Model Types
---------------------

OpenSTEF includes three primary forecasting models, all built on the XGBoost framework but using different underlying algorithms:

**XGBoostForecaster** - The default choice for most energy forecasting tasks. Uses gradient boosted decision trees to capture complex non-linear relationships between features and load. Excels at modeling interactions between weather variables, temporal patterns, and load dynamics. This model handles irregular patterns, sudden changes, and complex feature interactions naturally.

**GBLinearForecaster** - A linear model using gradient boosting with a linear booster. Suitable for scenarios where relationships between features and load are predominantly linear, or when model interpretability is paramount. Faster to train than tree-based models and less prone to overfitting on small datasets.

**ARForecaster** - An autoregressive model that uses historical load values as the primary predictive features. Best suited for very short-term forecasting where recent load history is the strongest predictor, or as a fallback when external features are unavailable.

When to Use Each Model
----------------------

**Use XGBoostForecaster when:**

- You have sufficient training data (typically several months to years)
- Load patterns show non-linear relationships with weather and other features
- Feature interactions are important (e.g., temperature effects varying by time of day)
- You need the highest possible accuracy for production forecasting
- Your prediction horizon ranges from 15 minutes to 48 hours ahead

This is the recommended default for most energy forecasting applications. Real-world deployments show XGBoost consistently outperforming linear models for load forecasting, particularly during extreme weather events and periods with complex load dynamics.

**Use GBLinearForecaster when:**

- Your dataset is small (less than a few months of data)
- Relationships between features and load are primarily linear
- Training time is constrained and you need faster model updates
- Model interpretability is required for regulatory or business reasons
- You want to establish a baseline before exploring more complex models

Linear models work well for stable load patterns with predictable weather sensitivity, such as residential areas with consistent heating/cooling behavior.

**Use ARForecaster when:**

- You need very short-term forecasts (minutes to a few hours ahead)
- External features like weather forecasts are unreliable or unavailable
- Load shows strong autocorrelation with minimal external influences
- You need a fast, lightweight fallback model for reliability

See :doc:`reliability_and_fallback` for strategies on using AR models as fallback options.

Model Configuration
-------------------

Each model type accepts hyperparameters that control its behavior. Here's how to configure the most commonly used XGBoostForecaster:

.. code-block:: python

    from openstef_models.models.forecasting import XGBoostForecaster
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
    from openstef_models.models.forecasting.common import LeadTime, Q
    
    # Configure hyperparameters for a balanced model
    hyperparams = XGBoostHyperParams(
        n_estimators=100,        # Number of boosting rounds
        max_depth=6,             # Maximum tree depth
        learning_rate=0.1,       # Step size for updates
        reg_alpha=0.1,           # L1 regularization
        reg_lambda=1.0,          # L2 regularization
        subsample=0.8,           # Fraction of samples per tree
        colsample_bytree=0.8,    # Fraction of features per tree
    )
    
    # Create forecaster with quantile predictions
    forecaster = XGBoostForecaster(
        horizons=[LeadTime(horizon="15min")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],  # Probabilistic forecasts
        hyperparams=hyperparams,
        n_jobs=-1,  # Use all available CPU cores
    )

For linear models, the configuration is similar but with linear-specific parameters:

.. code-block:: python

    from openstef_models.models.forecasting import GBLinearForecaster
    from openstef_models.models.forecasting.gblinear_forecaster import GBLinearHyperParams
    
    hyperparams = GBLinearHyperParams(
        n_estimators=50,         # Fewer iterations needed for linear models
        learning_rate=0.3,       # Higher learning rate acceptable
        reg_alpha=0.01,          # L1 regularization for feature selection
        reg_lambda=1.0,          # L2 regularization for stability
    )
    
    forecaster = GBLinearForecaster(
        horizons=[LeadTime(horizon="15min")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        hyperparams=hyperparams,
    )

Performance Characteristics
---------------------------

Understanding the performance trade-offs helps you make informed decisions:

**Training Time**

- GBLinearForecaster: Fastest, typically seconds to minutes
- ARForecaster: Very fast, suitable for frequent retraining
- XGBoostForecaster: Slowest, minutes to hours depending on data size and hyperparameters

**Prediction Speed**

All models provide fast inference suitable for real-time forecasting. Prediction time is typically milliseconds per forecast, making them appropriate for operational systems requiring frequent updates.

**Memory Requirements**

- GBLinearForecaster: Minimal memory footprint
- ARForecaster: Small memory requirements
- XGBoostForecaster: Larger models, especially with deep trees and many estimators

**Accuracy**

In production deployments across multiple grid operators, XGBoostForecaster consistently achieves the highest accuracy for medium-term forecasts (1-48 hours ahead). Linear models perform competitively for stable load patterns, while AR models excel at very short horizons where recent history dominates.

Hyperparameter Tuning
---------------------

The most impactful hyperparameters for XGBoostForecaster are:

**n_estimators** - Controls model complexity and training time. Start with 100 and increase if validation performance continues improving. Values of 200-500 are common for production models with large datasets.

**max_depth** - Limits tree depth to prevent overfitting. Default of 6 works well for most cases. Increase to 8-10 for very complex patterns with abundant data, decrease to 3-4 for smaller datasets.

**learning_rate** - Lower values (0.01-0.1) with more estimators often yield better results than higher values with fewer estimators. This provides more gradual learning and better generalization.

**reg_alpha and reg_lambda** - Regularization parameters that prevent overfitting. Increase these if you observe large gaps between training and validation performance.

**subsample and colsample_bytree** - Introduce randomness to improve generalization. Values of 0.8 provide a good balance between stability and diversity.

For systematic hyperparameter optimization, use the benchmarking tools to compare configurations:

.. code-block:: python

    # Example: Testing different max_depth values
    configs = [
        XGBoostHyperParams(max_depth=4),
        XGBoostHyperParams(max_depth=6),
        XGBoostHyperParams(max_depth=8),
    ]
    
    # Use benchmarking pipeline to evaluate each configuration
    # See OpenSTEF Beam documentation for complete examples

Automatic Model Selection
--------------------------

OpenSTEF supports automatic model selection based on validation performance. When retraining models, the system can compare the new model against the existing one and only deploy if performance improves:

.. code-block:: python

    from openstef_workflows.forecasting import ForecastingWorkflowConfig
    
    config = ForecastingWorkflowConfig(
        enable_model_selection=True,
        model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
        model_selection_old_model_penalty=1.2,  # Bias towards new models
    )

The ``model_selection_old_model_penalty`` parameter applies a penalty factor to the old model's metric, creating a bias toward newer models. A value of 1.2 means the new model is selected if its metric is at least 1/1.2 (≈83%) of the old model's performance. This prevents unnecessary model changes while allowing improvements to be adopted.

Practical Recommendations
--------------------------

**Start with defaults** - XGBoostForecaster with default hyperparameters provides strong baseline performance. Only tune hyperparameters after establishing that default settings are insufficient.

**Validate on held-out data** - Always evaluate model performance on data not used for training. Time series cross-validation is essential for reliable performance estimates.

**Monitor multiple metrics** - Don't optimize for a single metric. Track R², MAE, and quantile scores across different lead times to understand model behavior comprehensively. See :doc:`quantiles_and_confidence` for details on probabilistic evaluation.

**Consider operational constraints** - The "best" model balances accuracy with training time, memory requirements, and maintainability. A slightly less accurate model that trains 10x faster may be preferable for operational systems requiring frequent updates.

**Feature engineering matters more** - Investing time in better features typically yields larger improvements than extensive hyperparameter tuning. See :doc:`feature_engineering` for guidance on creating effective predictors.

Next Steps
----------

- Learn about :doc:`quantiles_and_confidence` for probabilistic forecasting
- Explore :doc:`feature_engineering` to improve model inputs
- Review :doc:`reliability_and_fallback` for production deployment strategies
- Consult the API documentation for complete model configuration options