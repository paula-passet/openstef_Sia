Model Selection
================

Choosing the right forecasting model is critical for accurate energy predictions. OpenSTEF provides multiple model types, each with distinct characteristics that make them suitable for different forecasting scenarios. This guide helps you understand when to use each model type and how to configure them effectively.

Available Model Types
---------------------

OpenSTEF offers three primary model types for short-term energy forecasting:

**XGBoost (Gradient Boosted Trees)**

The default and most widely used model in OpenSTEF. XGBoost uses gradient boosting with decision trees to capture complex non-linear relationships in energy data. It excels at handling interactions between features like weather conditions, time patterns, and historical load.

**LightGBM (Light Gradient Boosting Machine)**

An alternative gradient boosting implementation optimized for speed and memory efficiency. LightGBM uses leaf-wise tree growth rather than level-wise, which can lead to faster training on large datasets.

**GBLinear (Gradient Boosted Linear)**

A linear model implemented using XGBoost's linear booster. This model learns linear relationships between features and the target, making it more interpretable but less flexible than tree-based models.

When to Use Each Model
----------------------

**Choose XGBoost when:**

- You need the best possible forecast accuracy
- Your dataset contains complex non-linear patterns
- Feature interactions are important (e.g., temperature effects varying by time of day)
- You have sufficient training data (typically weeks to months)
- Training time is not a critical constraint

XGBoost is the recommended starting point for most energy forecasting applications. It has proven effective across diverse deployment scenarios and handles the typical characteristics of energy load data well.

**Choose LightGBM when:**

- You have very large datasets (millions of rows)
- Training speed is critical
- Memory usage is constrained
- You need similar accuracy to XGBoost but faster iteration

LightGBM typically achieves comparable accuracy to XGBoost but trains significantly faster on large datasets. The trade-off is slightly different hyperparameter behavior that may require retuning.

**Choose GBLinear when:**

- Interpretability is more important than accuracy
- You need to explain model decisions to stakeholders
- Your data has primarily linear relationships
- You have limited training data
- You want a simpler model as a baseline

Linear models are easier to understand and debug but typically achieve lower accuracy than tree-based models for energy forecasting. They work best for simple load patterns without complex interactions.

Model Configuration
-------------------

Each model type accepts hyperparameters that control its learning behavior. Here's how to configure them:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
   from openstef_models.types import Quantile, LeadTime
   from datetime import timedelta
   
   # Configure XGBoost with custom hyperparameters
   hyperparams = XGBoostHyperParams(
       n_estimators=150,        # Number of trees
       max_depth=6,             # Maximum tree depth
       learning_rate=0.1,       # Step size for updates
       subsample=0.8,           # Fraction of samples per tree
       colsample_bytree=0.8,    # Fraction of features per tree
       reg_alpha=0.1,           # L1 regularization
       reg_lambda=1.0,          # L2 regularization
   )
   
   # Create forecaster with configuration
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=hyperparams,
   )

For LightGBM, the configuration is similar but uses ``LGBMForecaster`` and ``LGBMHyperParams``:

.. code-block:: python

   from openstef_models.models.forecasting import LGBMForecaster
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMHyperParams
   
   hyperparams = LGBMHyperParams(
       n_estimators=150,
       max_depth=6,
       learning_rate=0.1,
       num_leaves=31,           # LightGBM-specific parameter
   )
   
   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=hyperparams,
   )

For linear models:

.. code-block:: python

   from openstef_models.models.forecasting import GBLinearForecaster
   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearHyperParams
   
   hyperparams = GBLinearHyperParams(
       n_estimators=100,
       learning_rate=0.1,
       reg_alpha=0.1,
       reg_lambda=1.0,
   )
   
   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=hyperparams,
   )

Key Hyperparameters
-------------------

Understanding the most important hyperparameters helps you tune models effectively:

**n_estimators**

The number of boosting rounds (trees for tree-based models). More trees can improve accuracy but increase training time and risk overfitting. Start with 100-200 and adjust based on validation performance.

**learning_rate (eta)**

Controls how much each tree contributes to the final prediction. Lower values (0.01-0.1) require more trees but often achieve better accuracy. Higher values (0.1-0.3) train faster but may miss optimal solutions.

**max_depth**

Maximum depth of each tree. Deeper trees capture more complex patterns but risk overfitting. For energy forecasting, values between 4-8 typically work well.

**subsample and colsample_bytree**

Control randomness by sampling data and features. Values like 0.8 introduce regularization that prevents overfitting while maintaining accuracy.

**reg_alpha and reg_lambda**

L1 and L2 regularization terms. Higher values constrain model complexity. Start with small values (0.1-1.0) and increase if you observe overfitting.

Performance Characteristics
---------------------------

Based on real-world deployments, here's what to expect from each model type:

**Accuracy**

XGBoost and LightGBM typically achieve similar accuracy, with R² scores above 0.9 for well-behaved load patterns. GBLinear usually scores 5-15% lower but remains useful for baseline comparisons.

**Training Time**

LightGBM trains 2-5x faster than XGBoost on large datasets. GBLinear is fastest but the difference matters less for typical dataset sizes (thousands to hundreds of thousands of rows).

**Prediction Speed**

All three models predict quickly enough for operational forecasting. XGBoost and LightGBM take microseconds per prediction. GBLinear is slightly faster but the difference is negligible in practice.

**Memory Usage**

Tree-based models store the entire tree structure, requiring more memory than linear models. LightGBM uses less memory than XGBoost due to its optimized tree representation.

Automatic Model Selection
--------------------------

OpenSTEF workflows support automatic model selection based on validation performance. When enabled, the system compares old and new models using a specified metric and selects the better performer:

.. code-block:: python

   from openstef_workflows.config import ForecastingWorkflowConfig
   from openstef_models.types import Quantile as Q
   
   config = ForecastingWorkflowConfig(
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,  # Bias toward new models
   )

The ``model_selection_old_model_penalty`` parameter biases selection toward newer models. A value of 1.2 means the new model is selected if its metric is at least 1/1.2 (≈83%) of the old model's metric for "higher_is_better" metrics, or at most 1.2x for "lower_is_better" metrics.

This prevents model degradation over time while avoiding unnecessary model changes from minor performance fluctuations.

Practical Recommendations
--------------------------

**Start with XGBoost defaults**

The default XGBoost configuration works well for most energy forecasting scenarios. Begin with these defaults and only tune hyperparameters if you observe clear issues like overfitting or underfitting.

**Use validation data**

Always evaluate models on held-out validation data that represents future forecasting conditions. Training metrics can be misleading due to overfitting.

**Monitor multiple metrics**

Don't rely solely on R². Also examine quantile coverage, pinball loss, and error distributions across different conditions (weekday/weekend, seasons, weather extremes).

**Consider operational constraints**

The "best" model balances accuracy with practical concerns like training time, explainability requirements, and computational resources.

**Iterate systematically**

Change one aspect at a time when tuning. This makes it easier to understand what improves performance and what doesn't.

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding short-term energy forecasting fundamentals
- :doc:`quantiles_and_confidence` - Interpreting probabilistic forecasts from these models
- :doc:`feature_engineering` - Preparing input features that drive model performance
- :doc:`reliability_and_fallback` - Handling model failures in production systems