Model Selection
===============

OpenSTEF provides several gradient-boosted forecasting models, each with different inductive biases, computational costs, and suitability for different load profiles. This page explains the available model types, their trade-offs, and how to choose between them for your forecasting use case.

For background on what short-term forecasting involves, see :doc:`forecasting_basics`. For information on probabilistic outputs shared by all models, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/model_selection_diagram_1.mmd

Available Model Types
---------------------

OpenSTEF's ``openstef-models`` package provides four base forecaster classes, all implementing the same ``Forecaster`` interface. This means you can swap models without changing the rest of your pipeline.

**XGBoostForecaster**
   A gradient-boosted tree ensemble using XGBoost. Each quantile is predicted by a separate tree (``multi_strategy="one_output_per_tree"``). Supports GPU acceleration via the ``device`` parameter. This is the most widely used model in production deployments and a solid default choice.

**LGBMForecaster**
   A gradient-boosted tree ensemble using LightGBM. LightGBM's leaf-wise growth strategy typically trains faster than XGBoost on large datasets and can achieve comparable or better accuracy. Well-suited to datasets with many features.

**LGBMLinearForecaster**
   LightGBM with linear leaves (``linear_tree=True``). Each leaf fits a linear model rather than a constant, giving the model the ability to extrapolate linearly within leaf regions. This is particularly effective for loads that have strong linear relationships with temperature or price signals.

**GBLinearForecaster**
   XGBoost's ``gblinear`` booster, which fits a regularised linear model rather than trees. This model is fast to train, highly interpretable, and degrades gracefully on sparse data. It is the recommended choice when training data is limited or when you need a lightweight model for rapid retraining.

All four models support multi-quantile output and SHAP-based feature contributions via the ``predict_contributions`` method.

Comparing the Models
--------------------

The table below summarises the practical trade-offs observed in production deployments.

.. list-table::
   :header-rows: 1
   :widths: 20 16 16 16 16 16

   * - Model
     - Accuracy (typical)
     - Training speed
     - Inference speed
     - Interpretability
     - Data requirements
   * - ``xgboost``
     - High
     - Moderate
     - Fast
     - SHAP
     - Medium (≥ 6 months)
   * - ``lgbm``
     - High
     - Fast
     - Fast
     - SHAP
     - Medium (≥ 6 months)
   * - ``lgbm_linear``
     - High (linear loads)
     - Fast
     - Fast
     - SHAP + linear
     - Medium
   * - ``gblinear``
     - Moderate
     - Very fast
     - Very fast
     - Coefficients
     - Low (weeks)

.. note::

   "Accuracy" here reflects typical pinball loss on Dutch distribution grid data. Results on your specific load profile may differ. Always validate on a held-out test period before committing to a model type.

When to Use Each Model
-----------------------

**Use XGBoost when** you want a reliable, well-understood default. XGBoost has the largest body of production evidence in OpenSTEF deployments, supports GPU training for large datasets, and its hyperparameters are well-documented. It handles non-linear weather interactions and calendar effects naturally.

**Use LightGBM when** training time is a constraint or your feature set is large (50+ features). LightGBM's leaf-wise growth finds complex interactions faster than XGBoost's level-wise approach. It is the preferred base model in ensemble workflows because of this speed advantage.

**Use LGBMLinear when** your load has a strong linear component — for example, heat-pump-dominated residential loads where consumption scales almost linearly with heating degree days. The linear leaves allow the model to extrapolate beyond the training range of temperature, which pure tree models cannot do.

**Use GBLinear when** you have limited historical data (a few weeks to a few months), need a fast retraining cycle, or are building a fallback model. Because it is essentially a regularised linear regression boosted over residuals, it is less prone to overfitting on small datasets. See :doc:`reliability_and_fallback` for how GBLinear fits into fallback strategies.

Configuring a Single Model
---------------------------

All forecasters accept ``quantiles``, ``horizons``, and a model-specific ``hyperparams`` object. The following example trains an XGBoost forecaster directly:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import Quantile as Q, LeadTime
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # Define the model with explicit hyperparameters
   model = XGBoostForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
       hyperparams=XGBoostHyperParams(
           n_estimators=200,
           max_depth=6,
           learning_rate=0.05,
       ),
   )

   # Wrap in a workflow for training and prediction
   pipeline = CustomForecastingWorkflow(
       model_id="substation_a_xgboost",
       model=model,
   )

   pipeline.fit(dataset)
   forecast = pipeline.predict(dataset)

Switching to LightGBM requires only changing the forecaster class and its hyperparameter type — the workflow and dataset interfaces remain identical:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )

   model = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
       hyperparams=LGBMHyperParams(
           n_estimators=300,
           num_leaves=63,
           learning_rate=0.05,
       ),
   )

Using Ensemble Models
----------------------

Rather than committing to a single model type, OpenSTEF's ensemble workflow combines predictions from multiple base models using a learned combiner. This is the recommended approach for production deployments where accuracy matters more than simplicity.

.. code-block:: python

   from openstef_models.workflows.ensemble_forecasting_workflow import (
       EnsembleForecastingWorkflow,
       EnsembleForecastingWorkflowConfig,
   )
   from openstef_core.datasets import Quantile as Q
   from datetime import timedelta

   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_a_ensemble",
       base_models=["lgbm", "xgboost", "gblinear"],
       combiner_model="lgbm",
       ensemble_type="learned_weights",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )

   pipeline = EnsembleForecastingWorkflow(config=config)
   pipeline.fit(dataset)
   forecast = pipeline.predict(dataset)

The ``base_models`` list accepts any combination of ``"lgbm"``, ``"xgboost"``, ``"gblinear"``, and ``"lgbm_linear"``. The ``combiner_model`` learns to weight their predictions based on recent performance, so weaker models are automatically down-weighted when conditions favour the stronger ones.

The ``ensemble_type`` parameter controls how the combiner works:

- ``"learned_weights"`` — a secondary model learns optimal weights from base model predictions (default, highest accuracy)
- ``"stacking"`` — the combiner sees base predictions as features and can learn non-linear combinations
- ``"rules"`` — a deterministic rule-based combiner, useful for debugging or interpretability requirements

.. note::

   Including ``"gblinear"`` as a base model in an ensemble is a common pattern in OpenSTEF deployments. Even when it is less accurate on its own, it adds diversity to the ensemble and acts as a regularising influence, particularly during periods outside the training distribution.

Hyperparameter Tuning
----------------------

All hyperparameter classes are Pydantic models, so you get validation and IDE completion out of the box. The most impactful parameters across all tree-based models are:

- ``n_estimators`` — more trees improve accuracy up to a point; beyond ~300–500 the gains diminish
- ``learning_rate`` — lower values (0.01–0.05) with more estimators generalise better but train slower
- ``max_depth`` (XGBoost) / ``num_leaves`` (LightGBM) — controls model complexity; deeper trees capture more interactions but overfit on small datasets

For ``GBLinearForecaster``, the key parameters are the regularisation terms ``reg_alpha`` (L1) and ``reg_lambda`` (L2), which prevent overfitting when data is scarce.

.. code-block:: python

   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )

   # A well-regularised GBLinear model for a substation with only 2 months of data
   model = GBLinearForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=GBLinearHyperParams(
           n_estimators=100,
           learning_rate=0.3,   # Higher learning rate suits linear models
           reg_alpha=0.1,       # L1 regularisation for feature sparsity
           reg_lambda=1.0,      # L2 regularisation for coefficient stability
       ),
   )

Practical Recommendations
--------------------------

For most new deployments, the following progression works well:

1. **Start with a single LightGBM model.** It trains quickly, handles the typical OpenSTEF feature set well, and gives you a fast feedback loop during initial development.
2. **Add XGBoost as a second base model** once you have a working pipeline. The two models have different failure modes, so the ensemble is more robust than either alone.
3. **Add GBLinear** if you observe the ensemble struggling during unusual periods (extreme weather, public holidays, grid events). Its linear structure provides a stable anchor.
4. **Switch to LGBMLinear** if your load is dominated by temperature-sensitive consumption and you see systematic bias at temperature extremes.

The features fed to these models matter as much as the model choice itself. See :doc:`feature_engineering` for guidance on weather features, lag features, and calendar effects that apply across all model types.