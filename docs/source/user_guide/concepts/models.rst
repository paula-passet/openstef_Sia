Models
======

This page provides an overview of all forecasting models available in OpenSTEF, their characteristics, and guidance on selecting the right model for your use case. For background on what short-term forecasting is and why it matters, see :doc:`short_term_forecasting`.

Available Models
----------------

OpenSTEF provides seven model types, configured via the ``model`` parameter in ``ForecastingWorkflowConfig``. These range from sophisticated machine learning models to simple baseline models useful for benchmarking.

.. list-table:: Model Comparison
   :header-rows: 1
   :widths: 18 15 15 15 15 22

   * - Model
     - Type
     - Non-linear
     - Extrapolation
     - Speed
     - Best For
   * - ``xgboost``
     - Gradient boosted trees
     - ✓
     - Limited
     - Medium
     - Complex load patterns, solar/wind
   * - ``gblinear``
     - Gradient boosted linear
     - ✗
     - Good
     - Fast
     - Stable linear relationships
   * - ``lgbm``
     - LightGBM trees
     - ✓
     - Limited
     - Fast
     - Large datasets, high cardinality features
   * - ``lgbmlinear``
     - LightGBM linear
     - ✗
     - Good
     - Fast
     - Linear patterns with LightGBM ecosystem
   * - ``flatliner``
     - Baseline (flat)
     - ✗
     - N/A
     - Instant
     - Baseline comparison
   * - ``median``
     - Baseline (median)
     - ✗
     - N/A
     - Instant
     - Baseline comparison
   * - ``constant_quantile``
     - Baseline (quantile)
     - ✗
     - N/A
     - Instant
     - Probabilistic baseline

.. mermaid:: /diagrams/user_guide/concepts/models_diagram_1.mmd

Tree-Based Models
-----------------

XGBoost
^^^^^^^

The default and most versatile model in OpenSTEF. XGBoost uses gradient boosted decision trees to capture complex non-linear relationships between features (weather, time-of-day, calendar effects) and energy load.

**Strengths:**

- Handles non-linear interactions between features automatically
- Robust to outliers and missing values
- Strong performance on solar and wind forecasting where weather interactions are complex

**Limitations:**

- Cannot extrapolate beyond the range of training data
- Slower to train than linear alternatives
- May overfit on small datasets without careful hyperparameter tuning

LightGBM
^^^^^^^^^

LightGBM (``lgbm``) is an alternative tree-based model that uses histogram-based splitting for faster training. It is particularly effective on large datasets with many features.

**Strengths:**

- Faster training than XGBoost on large datasets
- Lower memory usage
- Handles high-cardinality categorical features natively

**Limitations:**

- Similar extrapolation limitations as XGBoost
- May be less stable on very small datasets

Linear Models
-------------

GBLinear
^^^^^^^^

A gradient boosted linear model built on the XGBoost framework. Instead of trees, it uses linear base learners, making it better suited for problems where the relationship between features and load is approximately linear.

**Strengths:**

- Better extrapolation to unseen conditions (e.g., extreme temperatures)
- Faster training and inference than tree-based models
- More interpretable coefficients

**Limitations:**

- Cannot capture non-linear feature interactions
- May underperform on solar/wind where weather effects are highly non-linear

.. note::

   GBLinear internally applies target scaling (``StandardScaler``) to improve convergence. This is handled automatically by the ``GBLinearForecaster``.

LightGBM Linear
^^^^^^^^^^^^^^^^

The ``lgbmlinear`` model provides linear forecasting within the LightGBM framework. It shares the same advantages as GBLinear but uses LightGBM's optimization routines.

Baseline Models
---------------

Baseline models produce naive forecasts and are essential for benchmarking. A machine learning model that cannot outperform a baseline is not adding value.

- **flatliner** — Produces a constant (zero or flat) forecast. Useful as a lower-bound reference.
- **median** — Predicts the historical median value. A stronger baseline for stationary time series.
- **constant_quantile** — Produces constant quantile predictions based on historical data. Useful for evaluating probabilistic forecast skill.

Configuring a Model
--------------------

Select a model by setting the ``model`` field in ``ForecastingWorkflowConfig``:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.data_classes import LeadTime, Quantile as Q

   config = ForecastingWorkflowConfig(
       model_id="solar_park_001",
       model="xgboost",
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       radiation_column="shortwave_radiation",
       temperature_column="temperature_2m",
   )

To switch models, simply change the ``model`` parameter:

.. code-block:: python

   # Use GBLinear for a load with stable linear behavior
   config_linear = ForecastingWorkflowConfig(
       model_id="industrial_load_042",
       model="gblinear",
       horizons=[LeadTime.from_string("P3D")],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       temperature_column="temperature_2m",
   )

Hyperparameters
^^^^^^^^^^^^^^^

Each model type has its own hyperparameter configuration class:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_id="tuned_model",
       model="xgboost",
       xgboost_hyperparams={"n_estimators": 500, "max_depth": 6, "learning_rate": 0.05},
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.5)],
   )

The available hyperparameter fields are:

- ``xgboost_hyperparams`` — for the ``xgboost`` model
- ``gblinear_hyperparams`` — for the ``gblinear`` model
- ``lgbm_hyperparams`` — for the ``lgbm`` model
- ``lgbmlinear_hyperparams`` — for the ``lgbmlinear`` model

Model Selection and Reuse
--------------------------

OpenSTEF supports automatic model selection, where multiple models are trained and the best-performing one is kept:

.. code-block:: python

   config = ForecastingWorkflowConfig(
       model_id="auto_select_example",
       model="xgboost",
       model_selection_enable=True,
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
       model_reuse_enable=True,
       model_reuse_max_age="P7D",
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.5)],
   )

Key parameters:

- ``model_selection_enable`` — When ``True``, a newly trained model is compared against the existing model before replacing it.
- ``model_selection_metric`` — The metric used for comparison (quantile, metric name, direction).
- ``model_selection_old_model_penalty`` — A multiplier (>1.0) applied to the old model's score, biasing selection toward newer models to prevent staleness.
- ``model_reuse_enable`` — Reuse a previously trained model if it is still recent enough.
- ``model_reuse_max_age`` — Maximum age before a model must be retrained.

Benchmarking Models
-------------------

To compare models fairly, use identical configurations and change only the ``model`` field. The benchmark examples in OpenSTEF demonstrate this pattern:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.data_classes import LeadTime, Quantile as Q

   # Shared settings
   common_kwargs = dict(
       model_id="benchmark_",
       horizons=[LeadTime.from_string("P3D")],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       model_reuse_enable=True,
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

   # Create model-specific configs
   config_xgboost = ForecastingWorkflowConfig(model="xgboost", **common_kwargs)
   config_gblinear = ForecastingWorkflowConfig(model="gblinear", **common_kwargs)

.. note:: [VISUALIZATION: Bar chart comparing rMAE and rCRPS metrics across model types for different load categories (transformer, MV feeder, wind, solar)]

Choosing the Right Model
-------------------------

Use the following guidelines:

- **Solar generation forecasting** — Start with ``xgboost``. Solar output has strong non-linear dependence on radiation, cloud cover, and panel angle effects that trees capture well.
- **Wind generation forecasting** — Start with ``xgboost``. Wind power curves are highly non-linear (cubic relationship with wind speed, cut-in/cut-out thresholds).
- **Stable industrial loads** — Consider ``gblinear`` or ``lgbmlinear``. Industrial loads often follow predictable schedules with linear temperature sensitivity.
- **Residential aggregations** — Start with ``xgboost`` or ``lgbm``. Residential load has complex interactions between time-of-day, temperature, and calendar effects.
- **Quick prototyping** — Use ``gblinear`` for fast iteration, then compare against ``xgboost`` once the pipeline is validated.
- **Large-scale deployments** — Consider ``lgbm`` for its speed advantage when training hundreds of models in parallel.

.. warning::

   Always compare your chosen model against at least one baseline (``flatliner`` or ``median``) to verify it adds predictive value. A model that cannot beat the median baseline on your data likely has a data quality or feature engineering issue.