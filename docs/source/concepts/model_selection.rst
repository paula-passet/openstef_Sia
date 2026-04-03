Model Selection
===============

Choosing the right forecasting model affects both prediction accuracy and operational costs. OpenSTEF provides several model types, each with distinct characteristics that make them suitable for different forecasting scenarios. This guide helps you understand the trade-offs and select the appropriate model for your use case.

Available Model Types
---------------------

OpenSTEF includes three primary model families for energy forecasting:

**XGBoostForecaster** uses gradient boosted decision trees to capture complex non-linear relationships in energy data. This is the most commonly deployed model type in production environments, offering strong predictive performance across diverse load patterns.

**GBLinearForecaster** applies gradient boosting with linear base learners instead of trees. It provides a middle ground between pure linear models and tree-based approaches, maintaining interpretability while capturing some non-linear effects through boosting.

**LGBMLinearForecaster** uses LightGBM's linear model implementation, optimized for speed and memory efficiency. This model type works well when you need fast training times and have relatively linear relationships in your data.

All models support multi-quantile probabilistic forecasting and use magnitude-weighted pinball loss by default, which improves accuracy for energy forecasting by giving more weight to larger values.

When to Use Each Model
----------------------

The choice between model types depends on your data characteristics, computational constraints, and accuracy requirements.

Use **XGBoostForecaster** when:

- You have sufficient training data (weeks to months of historical load)
- Load patterns show complex non-linear behavior
- Accuracy is the primary concern
- You can afford longer training times (minutes to hours)
- Your deployment can handle larger model artifacts (tens to hundreds of MB)

Use **GBLinearForecaster** or **LGBMLinearForecaster** when:

- Training data is limited (days to weeks)
- Load patterns are relatively stable and linear
- You need fast training and prediction times
- Model interpretability is important
- Memory and storage constraints are tight
- You're forecasting simple loads with predictable patterns

In practice, XGBoostForecaster handles most production scenarios effectively. Linear models serve as useful baselines or for specialized cases where speed and simplicity matter more than marginal accuracy gains.

Performance Characteristics
---------------------------

Model performance varies across multiple dimensions beyond just prediction accuracy.

**Training Time**: XGBoostForecaster typically requires 2-10 minutes to train on a year of 15-minute resolution data with 50-100 features. Linear models train 5-10x faster, often completing in seconds to a minute. Training time scales roughly linearly with data volume and number of estimators.

**Prediction Speed**: All model types predict quickly once trained. XGBoostForecaster generates forecasts for hundreds of time steps in under a second. Linear models are marginally faster but the difference rarely matters in practice.

**Memory Usage**: XGBoostForecaster models range from 10-200 MB depending on hyperparameters (especially ``n_estimators`` and ``max_depth``). Linear models use 1-10 MB, making them suitable for memory-constrained environments.

**Accuracy**: XGBoostForecaster typically achieves R² scores of 0.85-0.95 on well-behaved loads with good feature engineering. Linear models often reach 0.75-0.90 on the same data. The gap widens for loads with complex patterns like weather sensitivity or irregular consumption.

Configuring Models
------------------

Each model type accepts hyperparameters that control its behavior and performance trade-offs. Here's how to configure the most common model:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
   from openstef_core.enums import Quantile, LeadTime
   
   # Configure for high accuracy (slower training)
   high_accuracy_forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=XGBoostHyperParams(
           n_estimators=500,      # More trees = better accuracy, slower training
           max_depth=8,           # Deeper trees = more complex patterns
           learning_rate=0.05,    # Lower rate = more stable, needs more estimators
           subsample=0.8,         # Regularization to prevent overfitting
           colsample_bytree=0.8,
       ),
       n_jobs=-1,  # Use all CPU cores
   )
   
   # Configure for fast training (good baseline)
   fast_forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=XGBoostHyperParams(
           n_estimators=100,      # Fewer trees = faster training
           max_depth=6,           # Shallower trees = simpler model
           learning_rate=0.1,     # Default rate
       ),
       n_jobs=-1,
   )

For linear models, the configuration is similar but with fewer relevant hyperparameters:

.. code-block:: python

   from openstef_models.models.forecasting import GBLinearForecaster
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
   
   linear_forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=XGBoostHyperParams(
           n_estimators=100,
           learning_rate=0.1,
       ),
   )

Key hyperparameters to adjust:

- ``n_estimators``: Number of boosting rounds. More estimators improve accuracy but increase training time and model size. Start with 100-200, increase to 500+ if you have time and data.
- ``max_depth``: Maximum tree depth (XGBoost only). Controls model complexity. Use 4-6 for simple patterns, 6-8 for complex loads, 8-10 for highly non-linear behavior.
- ``learning_rate``: Step size for each boosting iteration. Lower values (0.01-0.05) need more estimators but often achieve better final accuracy. Higher values (0.1-0.3) train faster but may miss optimal solutions.
- ``subsample`` and ``colsample_bytree``: Regularization parameters that randomly sample data and features. Values of 0.7-0.9 help prevent overfitting on smaller datasets.

Automatic Model Selection
--------------------------

OpenSTEF workflows support automatic model selection based on performance metrics. When enabled, the system compares newly trained models against existing ones and selects the best performer:

.. code-block:: python

   from openstef_workflows.workflows import ForecastingWorkflowConfig
   from openstef_core.enums import Quantile as Q
   
   config = ForecastingWorkflowConfig(
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,  # Bias toward new models
   )

The ``model_selection_old_model_penalty`` parameter prevents excessive switching between models. A value of 1.2 means the new model must be 20% better (by the selected metric) to replace the existing model. This reduces churn from minor performance fluctuations.

The selection metric typically uses the median quantile (0.5) and R² score, but you can specify any quantile and metric combination that matches your business objectives.

Comparing Models
----------------

To evaluate which model type works best for your data, train multiple models and compare their performance on held-out test data:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster, GBLinearForecaster
   from openstef_core.datasets import TimeSeriesDataset
   
   # Prepare your data
   train_data = TimeSeriesDataset(...)  # Your training data
   test_data = TimeSeriesDataset(...)   # Your test data
   
   # Train both model types
   xgb_model = XGBoostForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=24))],
   )
   xgb_model.fit(train_data)
   
   linear_model = GBLinearForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=24))],
   )
   linear_model.fit(train_data)
   
   # Generate predictions
   xgb_predictions = xgb_model.predict(test_data)
   linear_predictions = linear_model.predict(test_data)
   
   # Compare metrics (implement your evaluation logic)
   # Consider R², MAE, RMSE, and quantile coverage

Real-world deployments often show XGBoostForecaster outperforming linear models by 5-15% in R² score, with the gap larger for loads with strong weather dependencies or irregular patterns. However, linear models sometimes match or exceed XGBoost performance on simple, stable loads, while training much faster.

Practical Recommendations
--------------------------

Based on production experience across diverse energy forecasting scenarios:

**Start with XGBoostForecaster** using default hyperparameters. This provides a strong baseline that works well for most loads. Use ``n_estimators=100-200``, ``max_depth=6``, and ``learning_rate=0.1``.

**Monitor training time** and adjust if needed. If training takes too long for your operational constraints, reduce ``n_estimators`` or switch to a linear model for less critical forecasts.

**Use linear models for fallback**. When XGBoostForecaster training fails or times out, linear models provide reliable backup forecasts. See :doc:`reliability_and_fallback` for fallback strategies.

**Tune hyperparameters systematically**. Don't adjust all parameters at once. Change one at a time and measure the impact on validation metrics. Focus on ``n_estimators``, ``max_depth``, and ``learning_rate`` first.

**Consider ensemble approaches** for critical forecasts. Train multiple model types and combine their predictions to reduce risk from any single model's weaknesses.

**Retrain regularly**. Energy consumption patterns drift over time. Retrain models weekly or monthly to maintain accuracy. The automatic model selection feature helps manage this process.

See Also
--------

- :doc:`forecasting_basics` - Understanding short-term energy forecasting
- :doc:`feature_engineering` - Selecting and engineering features for better model performance
- :doc:`quantiles_and_confidence` - Interpreting probabilistic forecasts from different models
- :doc:`reliability_and_fallback` - Production strategies when model training fails