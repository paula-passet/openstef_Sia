Model Selection
===============

Choosing the right forecasting model is critical for accurate short-term energy predictions. OpenSTEF provides several model types, each with different strengths, computational requirements, and use cases. This guide helps you understand when to use each model and how to configure them effectively.

Available Model Types
---------------------

OpenSTEF includes three primary model types for energy forecasting:

**XGBoost Gradient Boosting (XGBoostForecaster)**

The workhorse of OpenSTEF deployments. XGBoost uses gradient boosted decision trees to learn complex, non-linear relationships between features and energy consumption. It handles multiple quantiles simultaneously and provides robust performance across diverse forecasting scenarios.

Use XGBoost when you need high accuracy, have sufficient training data (typically weeks to months), and can afford moderate training times. This is the recommended starting point for most production deployments.

**Linear Gradient Boosting (GBLinearForecaster)**

A linear model implemented using XGBoost's linear booster. It fits linear relationships between features and targets while still supporting XGBoost's quantile regression capabilities.

Use linear models when you have limited training data, need fast training times, or want interpretable coefficients. Linear models work well when relationships are approximately linear, such as temperature-driven load patterns without complex interactions.

**Baseline Models (ConstantMedianForecaster, FlatlinerForecaster)**

Simple models that predict constant values based on historical quantiles or zeros. These serve as performance baselines and educational examples rather than production forecasters.

Use baseline models to establish minimum performance thresholds and verify that more complex models provide meaningful improvements.

When to Use Each Model
----------------------

The choice between models involves trade-offs between accuracy, training time, data requirements, and interpretability.

**Start with XGBoost for most use cases**. It consistently delivers strong performance across different energy systems, weather patterns, and forecast horizons. The default hyperparameters provide a reasonable starting point:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
   from openstef_core.types import Quantile, LeadTime
   from datetime import timedelta

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=XGBoostHyperParams(
           n_estimators=100,
           max_depth=6,
           learning_rate=0.3,
       ),
   )

**Consider linear models when**:

- Training data is limited (less than a few weeks)
- Training must complete in seconds rather than minutes
- Model interpretability is critical for stakeholder communication
- The forecasting problem has predominantly linear characteristics

.. code-block:: python

   from openstef_models.models.forecasting import GBLinearForecaster
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams

   linear_forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=XGBoostHyperParams(n_estimators=50),
   )

**Use baseline models** only for establishing performance floors. If your XGBoost model doesn't significantly outperform a constant median predictor, investigate data quality, feature engineering, or hyperparameter tuning issues.

Hyperparameter Configuration
-----------------------------

XGBoost hyperparameters control the bias-variance trade-off and directly impact forecast accuracy. The three most important parameters are:

**n_estimators**: Number of boosting rounds (trees). More trees capture more patterns but increase training time and overfitting risk. Default is 100; increase to 200-500 for complex patterns with sufficient data.

**max_depth**: Maximum tree depth. Deeper trees capture complex interactions but overfit more easily. Default is 6; reduce to 2-4 for limited data or increase to 8-10 for large datasets with complex patterns.

**learning_rate**: Step size for each boosting round. Lower values (0.01-0.1) require more trees but often improve generalization. Higher values (0.3-0.5) train faster but may overfit. Default is 0.3.

Example configuration for a high-accuracy scenario with ample training data:

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams

   high_accuracy_params = XGBoostHyperParams(
       n_estimators=300,
       max_depth=8,
       learning_rate=0.1,
       subsample=0.8,
       colsample_bytree=0.8,
       reg_alpha=0.1,
       reg_lambda=1.0,
   )

Example configuration for fast training with limited data:

.. code-block:: python

   fast_training_params = XGBoostHyperParams(
       n_estimators=50,
       max_depth=3,
       learning_rate=0.3,
       min_child_weight=5,
   )

Regularization parameters (``reg_alpha``, ``reg_lambda``) control overfitting by penalizing model complexity. Subsampling parameters (``subsample``, ``colsample_bytree``) randomly sample data and features, improving generalization and reducing training time.

Performance Characteristics
---------------------------

Real-world OpenSTEF deployments demonstrate clear performance patterns across model types.

**XGBoost** typically achieves R² scores of 0.85-0.95 on the median quantile for well-behaved energy systems with good weather data. Training times range from 30 seconds to several minutes depending on data volume and hyperparameters. Prediction is fast (milliseconds for 48-hour horizons).

**Linear models** achieve R² scores of 0.70-0.85 for predominantly linear relationships. Training completes in seconds. They excel when feature engineering captures the right relationships (see :doc:`feature_engineering` for details on creating effective features).

**Baseline models** typically achieve R² scores below 0.50, confirming they provide only a performance floor.

Performance degrades when:

- Training data contains gaps or quality issues
- Weather forecasts are inaccurate or misaligned
- The forecast horizon extends beyond the model's effective range
- Feature engineering misses important predictors

Automatic Model Selection
--------------------------

OpenSTEF's workflow system includes automatic model selection that compares newly trained models against existing models. When retraining, the system evaluates both models on validation data and selects the better performer.

The selection process applies a penalty to the old model's metric, biasing selection toward newer models. This prevents stagnation while avoiding unnecessary model updates:

.. code-block:: python

   from openstef_workflows.workflows.forecasting import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_selection_enable=True,
       model_selection_metric=(Quantile(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
   )

With ``model_selection_old_model_penalty=1.2``, the new model must achieve at least 1/1.2 ≈ 83% of the old model's R² score to be selected. This 20% penalty accounts for validation noise and encourages model updates when improvements are meaningful.

Disable automatic selection (``model_selection_enable=False``) when you want full control over model deployment or are experimenting with hyperparameters.

Integrating Models into Workflows
----------------------------------

Models integrate into OpenSTEF's workflow system, which handles preprocessing, training, prediction, and postprocessing:

.. code-block:: python

   from openstef_workflows.workflows.forecasting import (
       create_forecasting_workflow,
       ForecastingWorkflowConfig,
   )
   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.types import Quantile, LeadTime
   from datetime import timedelta

   # Configure the complete workflow
   config = ForecastingWorkflowConfig(
       forecaster=XGBoostForecaster(
           quantiles=[Quantile(q) for q in [0.1, 0.3, 0.5, 0.7, 0.9]],
           horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
           hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=6),
       ),
       selected_features=["load", "temp", "windspeed", "hour", "dayofweek"],
       target_column="load",
   )

   # Create and use the workflow
   workflow = create_forecasting_workflow(config)
   workflow.fit(training_data)
   predictions = workflow.predict(forecast_input_data)

The workflow handles feature selection, data validation, and model persistence automatically. See the ``configuring_model_pipeline_example.py`` for a complete working example.

Next Steps
----------

- Understand :doc:`quantiles_and_confidence` for probabilistic forecasting
- Learn :doc:`feature_engineering` to improve model inputs
- Set up :doc:`reliability_and_fallback` for production robustness
- Review the API reference for detailed model configuration options

Model selection is just one part of building reliable forecasts. Effective feature engineering often provides larger accuracy gains than hyperparameter tuning, and robust fallback strategies ensure your system remains operational even when models fail.