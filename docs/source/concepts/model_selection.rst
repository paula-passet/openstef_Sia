Model Selection
================

Choosing the right forecasting model is critical for balancing prediction accuracy, computational cost, and operational reliability. OpenSTEF provides several model types optimized for short-term energy forecasting, each with distinct characteristics and use cases. This guide helps you select the appropriate model based on your requirements and data characteristics.

Available Model Types
----------------------

OpenSTEF offers four primary forecasting models, ranging from simple baselines to sophisticated machine learning approaches:

**XGBoostForecaster** is the flagship model for production forecasting. It uses gradient boosting trees to capture complex non-linear relationships between features and energy load. This model excels at learning interactions between weather variables, temporal patterns, and historical load data. XGBoost handles missing data gracefully, provides feature importance insights, and supports probabilistic forecasting through quantile regression.

**LGBMForecaster** provides an alternative gradient boosting implementation using LightGBM. It offers similar capabilities to XGBoost but with different performance characteristics—typically faster training on large datasets and lower memory usage. LightGBM uses a leaf-wise tree growth strategy compared to XGBoost's depth-wise approach, which can lead to better accuracy on some datasets.

**BaseCaseForecaster** implements a simple persistence model using lag features. It predicts future load by assuming weekly periodicity—for example, predicting tomorrow's 14:00 load using last week's 14:00 load. This model serves as a baseline for evaluating more sophisticated approaches and provides a reliable fallback when complex models fail.

**FlatlinerForecaster** predicts constant values (typically zero or median load). It's designed for edge cases where measurements show flatline behavior, such as during sensor failures or when assets are offline. While not useful for normal forecasting, it prevents system failures when data quality issues occur.

When to Use Each Model
----------------------

**Use XGBoostForecaster when:**

- You need production-grade accuracy for operational forecasting
- Your dataset has sufficient history (at least several months)
- You have weather forecasts and other exogenous features available
- Computational resources allow training times of minutes to hours
- You need probabilistic forecasts with multiple quantiles
- Explainability through feature importance is valuable

XGBoost is the default choice for most energy forecasting applications. It consistently delivers strong performance across diverse load patterns and has been validated in real-world grid operations.

**Use LGBMForecaster when:**

- You have very large datasets (millions of samples)
- Training time or memory constraints favor faster algorithms
- You want to experiment with an alternative to XGBoost
- Your data has many categorical features (LightGBM handles these efficiently)

LGBMForecaster and XGBMForecaster often produce similar accuracy, so the choice may depend on infrastructure considerations or personal preference.

**Use BaseCaseForecaster when:**

- You need a simple, interpretable baseline for comparison
- Your system requires an ultra-reliable fallback model
- You're forecasting loads with strong weekly periodicity
- You want to validate that complex models add value
- Computational resources are extremely limited

BaseCaseForecaster is particularly valuable in production systems as a fallback—it rarely fails and provides reasonable predictions when more sophisticated models encounter issues.

**Use FlatlinerForecaster when:**

- You detect flatline behavior in recent measurements
- You need to handle sensor failures gracefully
- Your reliability strategy requires predictions even with degraded data

This model is typically selected automatically by reliability checks rather than chosen explicitly. See :doc:`reliability_and_fallback` for details on automatic model selection based on data quality.

Model Configuration
-------------------

Each model exposes hyperparameters that control its behavior. Here's how to configure XGBoostForecaster for typical energy forecasting:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
   from openstef_core.enums import Quantile
   from datetime import timedelta
   
   # Configure hyperparameters for production forecasting
   hyperparams = XGBoostHyperParams(
       n_estimators=100,           # Number of trees
       max_depth=6,                # Tree depth (controls complexity)
       learning_rate=0.3,          # Step size for boosting
       subsample=0.8,              # Fraction of samples per tree
       colsample_bytree=0.8,       # Fraction of features per tree
       reg_alpha=0.1,              # L1 regularization
       reg_lambda=1.0,             # L2 regularization
   )
   
   # Create forecaster for probabilistic predictions
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=hyperparams,
       n_jobs=-1,  # Use all CPU cores
   )

The hyperparameters balance model complexity against overfitting risk:

- **n_estimators** controls the number of boosting rounds. More trees improve training accuracy but increase computation time and overfitting risk. Values between 50-200 work well for most energy forecasting tasks.

- **max_depth** limits tree depth. Deeper trees capture more complex interactions but overfit more easily. Values of 4-8 are typical for energy forecasting.

- **learning_rate** (eta) controls how aggressively the model learns. Lower values (0.01-0.1) require more trees but often generalize better. Higher values (0.3) train faster but may miss optimal solutions.

- **subsample** and **colsample_bytree** introduce randomness by using subsets of data and features. This regularization prevents overfitting. Values of 0.7-0.9 work well.

- **reg_alpha** and **reg_lambda** add L1 and L2 regularization penalties. These help prevent overfitting, especially with many features.

For BaseCaseForecaster, configuration is simpler—you only specify which lag features to use:

.. code-block:: python

   from openstef_models.models.forecasting import BaseCaseForecaster
   from openstef_models.models.forecasting.base_case_forecaster import BaseCaseHyperParams
   
   # Use 7-day and 14-day lags for weekly patterns
   hyperparams = BaseCaseHyperParams(
       lag_days=[7, 14]
   )
   
   forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=hyperparams,
   )

Performance Characteristics
---------------------------

Model performance varies across several dimensions beyond just prediction accuracy:

**Training Time:**

- XGBoostForecaster: Minutes to hours depending on dataset size and hyperparameters
- LGBMForecaster: Typically 2-5x faster than XGBoost on large datasets
- BaseCaseForecaster: Seconds (just identifies lag columns)
- FlatlinerForecaster: Instant (no training required)

**Prediction Speed:**

All models generate predictions in seconds for typical forecast horizons (47 hours ahead). Gradient boosting models are slightly slower but still fast enough for operational use.

**Memory Usage:**

- XGBoostForecaster: Moderate (model size typically 1-10 MB)
- LGBMForecaster: Lower than XGBoost for equivalent performance
- BaseCaseForecaster: Minimal (no trained parameters)
- FlatlinerForecaster: Minimal

**Accuracy:**

Based on real-world deployments across diverse energy forecasting applications:

- XGBoostForecaster: Typically achieves R² of 0.85-0.95 for well-behaved loads
- LGBMForecaster: Similar to XGBoost (±1-2% difference)
- BaseCaseForecaster: R² of 0.70-0.85 for loads with strong weekly patterns
- FlatlinerForecaster: Not applicable (used only for degraded data)

Accuracy depends heavily on data quality, feature engineering, and load characteristics. See :doc:`feature_engineering` for guidance on improving model performance through better features.

**Robustness:**

- XGBoostForecaster: Handles missing features and outliers well
- LGBMForecaster: Similar robustness to XGBoost
- BaseCaseForecaster: Very robust (simple logic, few failure modes)
- FlatlinerForecaster: Maximally robust (always produces predictions)

Model Selection in Production
------------------------------

Production systems often use multiple models with automatic selection based on performance and data quality. OpenSTEF's workflow system supports comparing old and new models during retraining:

.. code-block:: python

   from openstef_workflows.configs import ForecastingWorkflowConfig
   
   config = ForecastingWorkflowConfig(
       model_type="xgboost",
       model_selection_enable=True,
       model_selection_metric=(Quantile(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
   )

The ``model_selection_old_model_penalty`` parameter biases selection toward newer models—the new model only needs to achieve 1/1.2 ≈ 83% of the old model's performance to be selected. This prevents stagnation while avoiding unnecessary model changes.

For reliability-based model selection (e.g., falling back to BaseCaseForecaster when data quality degrades), see :doc:`reliability_and_fallback`.

Hyperparameter Tuning
---------------------

Default hyperparameters work well for most energy forecasting tasks, but tuning can improve performance by 5-15%. Focus on these high-impact parameters:

1. **n_estimators and learning_rate:** Trade off training time against accuracy. Try (n_estimators=50, learning_rate=0.3) for fast training or (n_estimators=200, learning_rate=0.1) for maximum accuracy.

2. **max_depth:** Start with 6. Increase to 8 if you have complex interactions and abundant data. Decrease to 4 if you see overfitting.

3. **subsample and colsample_bytree:** Start with 0.8. Lower to 0.6-0.7 if overfitting occurs.

4. **reg_alpha and reg_lambda:** Start with (0.1, 1.0). Increase if overfitting persists after adjusting other parameters.

Evaluate hyperparameter changes using holdout validation on recent data—not the training set. See OpenSTEF's evaluation metrics for proper validation procedures.

.. note::

   Hyperparameter tuning has diminishing returns. Investing in better features (weather forecasts, calendar effects, lag features) typically improves accuracy more than extensive hyperparameter optimization.

Next Steps
----------

- Learn about probabilistic forecasting in :doc:`quantiles_and_confidence`
- Improve model performance through :doc:`feature_engineering`
- Understand production reliability in :doc:`reliability_and_fallback`
- See :doc:`forecasting_basics` for foundational concepts