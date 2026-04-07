Model Selection Guide
=====================

Choosing the right forecasting model is one of the most impactful decisions you'll make when building an energy forecasting pipeline with OpenSTEF. This page compares the available model types, explains when each is appropriate, and describes how OpenSTEF's automatic model selection works during retraining.

For background on what short-term energy forecasting involves, see :doc:`forecasting_basics`. For details on the probabilistic output these models produce, see :doc:`quantiles_and_confidence`.

Available Model Types
---------------------

OpenSTEF provides several forecaster implementations, all sharing the same ``Forecaster`` base interface. Each model produces multi-quantile probabilistic forecasts, so the choice is about *how* those quantiles are estimated, not *whether* you get uncertainty information.

XGBoost (Gradient Boosted Trees)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``XGBoostForecaster`` uses XGBoost's tree-based gradient boosting with a ``multi_strategy="one_output_per_tree"`` approach for multi-quantile regression.

**Strengths:**

- Excellent at capturing nonlinear relationships between weather features and load
- Robust to outliers and missing feature interactions
- GPU acceleration available (``device="cuda"``)
- Well-understood hyperparameters (``n_estimators``, ``learning_rate``, ``max_depth``)

**Best for:** General-purpose load forecasting, solar generation, and scenarios with complex feature interactions.

LightGBM
^^^^^^^^^

The ``LGBMForecaster`` wraps a ``MultiQuantileRegressor`` built on LightGBM. It shares many characteristics with XGBoost but uses histogram-based splitting for faster training.

**Strengths:**

- Faster training than XGBoost on large datasets
- Lower memory usage due to histogram binning
- Native categorical feature support
- GPU support via ``device="cuda"``

**Best for:** Large-scale deployments where training speed matters, or when you have many prediction jobs to retrain frequently.

GBLinear
^^^^^^^^

The ``GBLinearForecaster`` uses XGBoost's linear booster (``gblinear``) instead of trees. This produces a linear model trained via gradient boosting, offering interpretability while still benefiting from boosting's regularization.

**Strengths:**

- Highly interpretable — coefficients map directly to features
- Fast training and prediction
- Less prone to overfitting on small datasets
- Supports SHAP-based feature contributions via ``ContributionsMixin``

**Trade-offs:**

- Cannot capture nonlinear relationships without explicit feature engineering
- Uses only a 7-day lag (no trivial lags), which simplifies the feature space

**Best for:** Wind power forecasting, situations requiring explainability, or when you have limited training data.

LGBMLinear
^^^^^^^^^^

The ``LGBMLinearForecaster`` is LightGBM's linear counterpart, analogous to GBLinear but built on the LightGBM framework. It offers similar interpretability benefits with LightGBM's training efficiency.

**Best for:** Same use cases as GBLinear, when you prefer the LightGBM ecosystem.

Ensemble Models (Stacking and Learned Weights)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF supports ensemble approaches that combine multiple base forecasters:

- **Stacking:** Trains a meta-learner (e.g., LightGBM) on the predictions of base forecasters to produce a final forecast.
- **Learned Weights:** Uses a classification approach to learn which base forecaster performs best under different conditions, then combines predictions using soft or hard selection.

**Strengths:**

- Often achieves the best accuracy by leveraging complementary model strengths
- Learned weights adapt to conditions (e.g., one model may excel in winter, another in summer)

**Trade-offs:**

- Higher computational cost (trains multiple models)
- More complex to debug and interpret
- Requires sufficient data for the combiner to learn meaningful patterns

**Best for:** High-value forecasting points where accuracy justifies the additional complexity.

Configuring a Model
-------------------

Each model is configured through its corresponding forecaster class and hyperparameters. Here's how to set up the most common models:

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # XGBoost with custom hyperparameters
   forecaster = XGBoostForecaster(
       hyperparams=XGBoostHyperParams(
           n_estimators=500,
           learning_rate=0.05,
           max_depth=6,
       ),
       n_jobs=-1,  # Use all CPU cores
       early_stopping_rounds=50,
   )

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )

   # LightGBM with early stopping
   forecaster = LGBMForecaster(
       hyperparams=LGBMHyperParams(
           n_estimators=1000,
           learning_rate=0.03,
           max_depth=8,
       ),
       early_stopping_rounds=100,
       verbosity=-1,  # Silent
   )

When using ``ForecastingWorkflowConfig``, you specify the model type as a string and the workflow factory handles instantiation:

.. code-block:: python

   from openstef_core.workflows.forecasting_workflow_config import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )

   config = ForecastingWorkflowConfig(
       model="xgboost",  # or "lgbm", "gblinear", "lgbm_linear"
       # ... other configuration
   )
   workflow = create_forecasting_workflow(config)

.. note::

   The ``model`` parameter in ``ForecastingWorkflowConfig`` controls not just which forecaster is used, but also which preprocessing steps are applied. For example, GBLinear and ensemble models use only a 7-day lag instead of the full set of trivial lags that tree-based models receive.

Automatic Model Selection
-------------------------

OpenSTEF includes a built-in model selection mechanism that runs during retraining. When ``model_selection_enable=True`` (the default), the library compares a newly trained model against the previously stored model and keeps whichever performs better.

The selection process works as follows:

1. A new model is trained on the latest data.
2. The stored (old) model is loaded from MLflow.
3. Both models are evaluated on the same validation set using the configured metric.
4. A penalty factor is applied to the old model's score to bias selection toward newer models, ensuring the system adapts to changing patterns.

.. code-block:: python

   from openstef_core.datasets.quantile import Q

   config = ForecastingWorkflowConfig(
       model="lgbm",
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
       model_reuse_enable=True,
       model_reuse_max_age="P7D",  # ISO 8601 duration: 7 days
       # ... other configuration
   )

The ``model_selection_old_model_penalty`` of ``1.2`` means the old model's R² score is effectively divided by 1.2 before comparison. This creates a bias toward adopting the newly trained model unless the old model is substantially better.

Decision Framework
------------------

Use the following guidelines to choose your starting model:

.. list-table:: Model Comparison
   :header-rows: 1
   :widths: 20 15 15 15 15 20

   * - Model
     - Training Speed
     - Accuracy
     - Interpretability
     - Data Needs
     - Recommended Use Case
   * - XGBoost
     - Medium
     - High
     - Low
     - Medium
     - General load forecasting
   * - LightGBM
     - Fast
     - High
     - Low
     - Medium
     - Large-scale deployments
   * - GBLinear
     - Very Fast
     - Medium
     - High
     - Low
     - Wind, explainability needs
   * - LGBMLinear
     - Very Fast
     - Medium
     - High
     - Low
     - Same as GBLinear
   * - Ensemble
     - Slow
     - Very High
     - Very Low
     - High
     - High-value forecast points

**Start with LightGBM** if you have no strong preference. It offers the best balance of speed and accuracy for most energy forecasting tasks. Switch to GBLinear if you need interpretability, or to an ensemble if you need maximum accuracy and can afford the computational overhead.

Practical Considerations
------------------------

**Training data volume:** Tree-based models (XGBoost, LightGBM) generally need at least several months of historical data to learn seasonal patterns. Linear models can produce reasonable results with less data but won't capture nonlinear effects.

**Retraining frequency:** Faster models (GBLinear, LGBMLinear) can be retrained more frequently, which helps them adapt to changing load patterns. If you retrain daily, training speed becomes a meaningful factor.

**GPU acceleration:** Both XGBoost and LightGBM support GPU training via ``device="cuda"``. This is most beneficial for large datasets or ensemble configurations where multiple models are trained.

**Feature engineering matters more for linear models:** Since GBLinear and LGBMLinear cannot learn nonlinear interactions, the quality of your features has an outsized impact. See :doc:`feature_engineering` for guidance on derived features like wind power curves and radiation-based features that encode domain knowledge directly.

**Production reliability:** Regardless of which model you choose, OpenSTEF's fallback mechanisms ensure forecasts are always available. See :doc:`reliability_and_fallback` for details on what happens when a model fails or produces unreasonable results.