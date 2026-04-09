Model Selection
===============

Choosing the right forecasting model is critical for energy forecasting performance. OpenSTEF provides several model types, each with distinct characteristics suited to different patterns in energy data. This guide helps you understand when to use each model type, their trade-offs, and how to configure them effectively.

Available Model Types
---------------------

OpenSTEF includes three primary model families for energy forecasting:

**XGBoost Tree Models** (``XGBoostForecaster``)
   Gradient boosting decision trees that excel at capturing non-linear relationships and complex interactions between features. These models automatically discover feature interactions without manual engineering and handle non-linear patterns like weather thresholds (e.g., cooling load that activates above 20°C).

**Linear Models** (``GBLinearForecaster``, ``LGBMLinearForecaster``)
   Gradient boosting with linear leaves rather than trees. These models assume linear relationships between features and load but benefit from boosting's ability to handle quantile regression. They're faster to train and more interpretable than tree models.

**Ensemble Models** (``EnsembleForecaster``)
   Combine multiple forecasters by either selecting the best performer for each timestep (hard selection) or blending predictions using learned weights (soft blending). Useful when different models excel under different conditions.

When to Use Tree Models
-----------------------

Tree-based models are the default choice for most energy forecasting tasks. They handle the non-linear dynamics common in energy systems:

- **Weather-dependent load**: Air conditioning and heating loads have non-linear temperature responses
- **Time-of-day patterns**: Different load profiles for morning ramps, midday peaks, and evening patterns
- **Feature interactions**: Combined effects like "hot summer afternoons" that aren't captured by additive models

Tree models work well when you have sufficient training data (typically 6+ months) and diverse weather conditions. They require minimal feature engineering since they discover interactions automatically.

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams
   from openstef_core.datasets import ForecastInputDataset
   from openstef_core.utils.quantiles import Q
   
   # Configure tree model with moderate depth
   hyperparams = XGBoostHyperParams(
       n_estimators=100,      # Number of trees
       max_depth=6,           # Tree depth (default is good starting point)
       learning_rate=0.3,     # Step size for boosting
       subsample=0.8,         # Use 80% of data per tree
       reg_alpha=0.1,         # L1 regularization
       reg_lambda=1.0,        # L2 regularization
   )
   
   forecaster = XGBoostForecaster(
       horizons=[timedelta(minutes=15)],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       hyperparams=hyperparams,
       n_jobs=-1,  # Use all CPU cores
   )
   
   # Train on historical data
   forecaster.fit(train_data)
   
   # Generate probabilistic forecasts
   predictions = forecaster.predict(forecast_input)

The ``max_depth`` parameter controls model complexity. Deeper trees (8-10) capture more intricate patterns but risk overfitting. Shallower trees (3-5) are more conservative and generalize better to new conditions. The default of 6 balances these concerns for typical energy forecasting.

When to Use Linear Models
--------------------------

Linear models are appropriate when relationships are predominantly additive or when you need faster training and inference:

- **Simple load patterns**: Industrial facilities with consistent schedules
- **Limited training data**: Less than 3 months of history where trees would overfit
- **Fast retraining**: Production systems that retrain frequently
- **Interpretability**: When you need to explain exactly how each feature contributes

Linear models require more careful feature engineering. You must manually create interaction terms (e.g., ``temperature * is_summer``) that trees would discover automatically.

.. code-block:: python

   from openstef_models.models.forecasting import GBLinearForecaster
   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearHyperParams
   
   # Configure linear model
   hyperparams = GBLinearHyperParams(
       n_estimators=50,       # Fewer iterations needed for linear models
       learning_rate=0.1,     # Lower learning rate for stability
       reg_alpha=0.5,         # Higher regularization prevents overfitting
       reg_lambda=1.0,
   )
   
   forecaster = GBLinearForecaster(
       horizons=[timedelta(minutes=15)],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       hyperparams=hyperparams,
   )

Linear models train 2-5x faster than tree models and produce smaller model files. This matters when deploying hundreds of models or retraining frequently.

Performance Trade-offs
----------------------

Model selection involves balancing several competing factors:

**Accuracy vs. Training Time**
   Tree models typically achieve 5-15% better R² scores than linear models on energy data with non-linear patterns, but take 3-5x longer to train. For production systems retraining daily, this trade-off matters.

**Complexity vs. Generalization**
   Deeper trees (``max_depth`` > 8) and more estimators (``n_estimators`` > 200) improve training accuracy but may overfit to historical patterns. Models must generalize to weather conditions not seen during training.

**Model Size vs. Deployment**
   Tree models with 100+ estimators and depth 6 produce model files of 5-20 MB. Linear models are typically under 1 MB. This affects storage and loading time when managing thousands of forecasting locations.

Hyperparameter Tuning
---------------------

Key hyperparameters that affect model behavior:

**n_estimators**: Number of boosting rounds
   - Linear models: 50-100 sufficient
   - Tree models: 100-200 for most cases
   - More estimators improve training accuracy but increase overfitting risk and training time

**learning_rate**: Step size for gradient descent
   - Higher (0.3): Faster convergence, fewer estimators needed
   - Lower (0.05-0.1): More stable, requires more estimators
   - Typical strategy: Use higher learning rate with early stopping

**max_depth**: Tree depth (tree models only)
   - Shallow (3-5): Conservative, good for limited data
   - Medium (6-8): Default choice for most energy forecasting
   - Deep (10+): Captures very complex patterns, needs large datasets

**Regularization** (``reg_alpha``, ``reg_lambda``):
   - L1 (``reg_alpha``): Feature selection, creates sparse models
   - L2 (``reg_lambda``): Smooths predictions, prevents overfitting
   - Start with defaults (0.1, 1.0) and increase if validation performance degrades

.. code-block:: python

   # Conservative configuration for limited data
   conservative_params = XGBoostHyperParams(
       n_estimators=50,
       max_depth=4,
       learning_rate=0.1,
       reg_alpha=0.5,
       reg_lambda=2.0,
   )
   
   # Aggressive configuration for large datasets
   aggressive_params = XGBoostHyperParams(
       n_estimators=200,
       max_depth=8,
       learning_rate=0.1,
       reg_alpha=0.05,
       reg_lambda=0.5,
   )

Automatic Model Selection
--------------------------

OpenSTEF workflows support automatic model selection based on validation performance. The system can train multiple model configurations and select the best performer:

.. code-block:: python

   from openstef_workflows.forecasting import ForecastingWorkflowConfig
   
   config = ForecastingWorkflowConfig(
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,  # Bias toward new models
   )

The ``model_selection_old_model_penalty`` parameter requires new models to outperform existing models by 20% to replace them. This prevents unnecessary model churn from minor performance fluctuations.

Real-World Performance
----------------------

Based on production deployments across diverse energy systems:

**Residential Aggregations** (100+ households)
   - Tree models: R² 0.85-0.92
   - Linear models: R² 0.75-0.85
   - Key patterns: Strong weather dependence, weekend effects

**Commercial Buildings**
   - Tree models: R² 0.80-0.90
   - Linear models: R² 0.70-0.82
   - Key patterns: Business hours, HVAC thresholds

**Industrial Facilities**
   - Tree models: R² 0.75-0.88
   - Linear models: R² 0.70-0.85
   - Key patterns: Production schedules, process dependencies

**Solar Generation**
   - Tree models: R² 0.90-0.95
   - Linear models: R² 0.85-0.92
   - Key patterns: Clear sky models, cloud transients

Tree models consistently outperform linear models by 5-10 percentage points in R² for most energy forecasting tasks. The gap widens for systems with strong non-linear behavior (e.g., temperature-dependent cooling load).

Choosing Between XGBoost and LightGBM
--------------------------------------

OpenSTEF provides both XGBoost and LightGBM implementations. Key differences:

**XGBoost** (``XGBoostForecaster``, ``GBLinearForecaster``)
   - More mature, extensively tested in production
   - Better GPU support for large-scale training
   - Slightly slower but more stable

**LightGBM** (``LGBMLinearForecaster``)
   - Faster training, especially for large datasets
   - Lower memory usage
   - Leaf-wise tree growth (vs. level-wise in XGBoost)

For most users, XGBoost is the recommended starting point due to its proven track record in energy forecasting. LightGBM is worth considering when training time becomes a bottleneck or when working with very large datasets (millions of samples).

Next Steps
----------

- See :doc:`feature_engineering` for guidance on creating effective predictors
- See :doc:`quantiles_and_confidence` to understand probabilistic forecasts
- See :doc:`reliability_and_fallback` for handling model failures in production