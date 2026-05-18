Models
======

This page provides an overview of the machine learning models available in openstef-models for short-term energy forecasting. It covers what each model offers, how they compare, and guidance on selecting the right model for your use case.

For information on how models are trained and configured within workflows, see :doc:`workflows`. For feature engineering that feeds into these models, see :doc:`features`.

Available Models
----------------

OpenSTEF provides several model types that can be used for energy load and generation forecasting. Each model is specified via the ``model`` parameter in the ``ForecastingWorkflowConfig``.

.. list-table:: Model Comparison
   :header-rows: 1
   :widths: 18 20 20 20 22

   * - Model
     - Type
     - Strengths
     - Weaknesses
     - Best For
   * - ``xgboost``
     - Gradient boosted trees
     - Captures complex nonlinear patterns; robust to outliers; handles missing values
     - Cannot extrapolate beyond training range; slower training
     - Solar/wind parks with complex weather interactions; loads with nonlinear temperature dependence
   * - ``gblinear``
     - Gradient boosted linear model
     - Better extrapolation; faster training and inference; more interpretable
     - Limited ability to capture nonlinear interactions
     - Stable industrial loads; scenarios where extrapolation matters (e.g., growing demand)
   * - ``lightgbm``
     - Gradient boosted trees (LightGBM)
     - Very fast training; memory efficient; handles large datasets well
     - Requires ``lightgbm`` extra dependency
     - Large-scale deployments; rapid iteration during development
   * - ``flatliner``
     - Baseline (constant prediction)
     - Zero training time; useful as benchmark
     - No learning capability
     - Baseline comparison; sanity checks

.. mermaid:: /diagrams/user_guide/concepts/models_diagram_1.mmd

XGBoost
^^^^^^^

XGBoost is the default and most battle-tested model in OpenSTEF. It uses an ensemble of decision trees trained via gradient boosting, making it excellent at capturing nonlinear relationships between weather variables and energy production/consumption.

Key characteristics:

- Handles interactions between features automatically (e.g., temperature × time-of-day)
- Built-in handling of missing values
- Supports probabilistic forecasting via quantile regression
- Cannot predict values outside the range seen during training

GBLinear
^^^^^^^^

GBLinear uses gradient boosting to optimize a linear model. While it cannot capture complex nonlinear patterns, it has a critical advantage: **extrapolation**. If energy demand is growing beyond historical levels, a tree-based model will plateau at the maximum seen in training, while GBLinear can project the trend forward.

Key characteristics:

- Linear model with boosted optimization
- Better generalization to unseen ranges
- Faster training and prediction
- More interpretable coefficients

LightGBM
^^^^^^^^^

LightGBM is an alternative gradient boosting framework that uses histogram-based algorithms for faster training. It requires installing the optional ``lightgbm`` dependency:

.. code-block:: bash

   pip install openstef-models[lightgbm]

Key characteristics:

- Leaf-wise tree growth (vs. level-wise in XGBoost)
- Significantly faster on large datasets
- Lower memory consumption
- Comparable accuracy to XGBoost in most energy forecasting scenarios

Configuring Models
------------------

Models are selected through the ``ForecastingWorkflowConfig``. All other configuration (features, horizons, quantiles) remains identical regardless of model choice, enabling fair comparisons:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_id="solar_park_01",
       model="xgboost",
       horizons=[0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 24.0, 48.0],
       quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

To switch models, simply change the ``model`` parameter:

.. code-block:: python

   # Create a GBLinear variant from an existing config
   gblinear_config = config.model_copy(update={"model": "gblinear"})

Comparing Models
----------------

A common workflow is benchmarking multiple models against the same dataset to determine which performs best for a specific prediction job. OpenSTEF makes this straightforward since model selection is a single parameter change:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Define model variants to compare
   model_types = ["xgboost", "gblinear"]

   base_config = ForecastingWorkflowConfig(
       model_id="benchmark_",
       model="xgboost",
       horizons=[0.25, 1.0, 4.0, 24.0, 48.0],
       quantiles=[0.1, 0.5, 0.9],
       radiation_column="shortwave_radiation",
       temperature_column="temperature_2m",
       model_reuse_enable=True,
       verbosity=0,
   )

   # Create one workflow per model type
   workflows = {}
   for model_type in model_types:
       model_config = base_config.model_copy(update={"model": model_type})
       workflows[model_type] = create_forecasting_workflow(model_config)

.. note:: [VISUALIZATION: Bar chart comparing MAE/RMSE metrics across model types for the same prediction target]

For systematic benchmarking across many targets, see the benchmarking tools in ``openstef_beam.benchmarking``.

Model Selection Guidelines
--------------------------

Use the following guidelines when choosing a model:

**Start with XGBoost** if:

- You have a solar or wind park with complex weather dependencies
- Your load has strong nonlinear patterns (e.g., heating/cooling thresholds)
- You want the most thoroughly tested option

**Choose GBLinear** if:

- Your load is growing or changing beyond historical ranges
- The relationship between features and target is approximately linear
- You need faster training for frequent retraining cycles
- Interpretability of model coefficients is important

**Choose LightGBM** if:

- You are forecasting many targets and need fast training
- Your dataset is very large (millions of rows)
- You want tree-based accuracy with better computational efficiency

**Use Flatliner** if:

- You need a naive baseline for comparison
- You want to verify your evaluation pipeline is working correctly

Probabilistic Forecasting
--------------------------

All models in OpenSTEF support **probabilistic forecasting** through quantile regression. By specifying multiple quantiles in the configuration, each model produces prediction intervals rather than just point forecasts:

.. code-block:: python

   config = ForecastingWorkflowConfig(
       model="xgboost",
       quantiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
       # ... other settings
   )

The 0.5 quantile represents the median forecast, while outer quantiles (e.g., 0.05 and 0.95) define the 90% prediction interval. This is essential for grid operations where understanding forecast uncertainty drives reserve capacity decisions.

.. note:: [VISUALIZATION: Fan chart showing probabilistic forecast with prediction intervals from multiple quantiles]

Feature Importance and Explainability
--------------------------------------

OpenSTEF models support contribution analysis through the ``predict_contributions`` method, which reveals how each feature drives individual predictions:

.. code-block:: python

   # After training a workflow
   contributions = workflow.predict_contributions(
       data=dataset,
       forecast_start=forecast_start,
   )

This is available for tree-based models (XGBoost, LightGBM) via SHAP values. For details on interpreting model outputs, see :doc:`features`.

Next Steps
----------

- :doc:`workflows` — Learn how models fit into the full forecasting pipeline
- :doc:`features` — Understand the feature engineering that feeds into models
- :doc:`/user_guide/tutorials/index` — Hands-on examples training and comparing models