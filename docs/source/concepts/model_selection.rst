Model Selection
===============

OpenSTEF provides several forecasting model types, each suited to different signal characteristics and operational requirements. Choosing the right model is one of the most consequential decisions when deploying a forecasting pipeline — the wrong choice can leave accuracy on the table or introduce unnecessary complexity. This page compares the available model types, explains when each is appropriate, and walks through how to configure them in practice.

For background on what short-term forecasting involves, see :doc:`forecasting_basics`. For details on probabilistic outputs such as quantiles, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Decision tree showing model selection flow — signal type (linear vs. non-linear, stable vs. dynamic) leading to recommended model choices]

Available Model Types
---------------------

OpenSTEF exposes four primary forecasting model types through the ``model_type`` field of the forecasting configuration. The valid string identifiers are:

- ``"xgboost"`` — gradient-boosted trees via XGBoost
- ``"gblinear"`` — linear booster via XGBoost
- ``"lgbm"`` — gradient-boosted trees via LightGBM
- ``"lgbmlinear"`` — gradient-boosted trees with linear leaves via LightGBM
- ``"median"`` — autoregressive median regressor
- ``"flatliner"`` — constant zero (or median) predictor

Each model implements the same ``Forecaster`` interface, so switching between them requires only a configuration change — no pipeline code needs to change.

XGBoost Tree Model (``xgboost``)
---------------------------------

The XGBoost tree model is the most widely used choice for general-purpose energy load forecasting. It builds an ensemble of decision trees using gradient boosting and handles non-linear relationships between features and load naturally. It supports multi-quantile output by training one tree per quantile, controlled by the ``multi_strategy="one_output_per_tree"`` setting internally.

**When to use it:**

- The load signal has clear non-linear structure (e.g., temperature response curves, day-of-week patterns)
- You have a rich feature set including weather, calendar, and lag features
- You want well-calibrated probabilistic forecasts across multiple quantiles
- Training data is plentiful (weeks to years of history)

**Key hyperparameters:**

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams

   hyperparams = XGBoostHyperParams(
       n_estimators=200,
       max_depth=6,
       learning_rate=0.05,
   )

The ``max_depth`` parameter is particularly important: deeper trees capture more complex interactions but risk overfitting on smaller datasets. A depth of 4–6 is a reasonable starting point for most grid connection forecasting tasks.

LightGBM Tree Model (``lgbm``)
-------------------------------

The LightGBM model is functionally similar to XGBoost but uses a leaf-wise tree growth strategy that tends to produce faster training and competitive accuracy on large datasets. Like the XGBoost model, it supports multi-quantile regression.

**When to use it over** ``xgboost``:

- Training datasets are large (months of 15-minute data across many assets)
- Training time is a constraint in your pipeline
- You want to experiment with quantile calibration — LightGBM's quantile loss implementation can behave differently from XGBoost's at the tails

In practice, ``lgbm`` and ``xgboost`` often produce similar accuracy on the same dataset. It is worth benchmarking both when setting up a new forecasting deployment.

LightGBM with Linear Leaves (``lgbmlinear``)
---------------------------------------------

This variant combines gradient-boosted trees with linear models at the leaf nodes. The result is a model that can represent both non-linear global structure (captured by the tree splits) and smooth linear relationships within each leaf region.

**When to use it:**

- The load signal has a mix of non-linear regime changes and locally linear behaviour
- You observe that pure tree models produce blocky, step-like forecasts that do not reflect the smooth underlying dynamics
- Extrapolation beyond the training range matters — linear leaves generalise better outside seen feature values than piecewise-constant leaves

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import LGBMLinearHyperParams

   hyperparams = LGBMLinearHyperParams(
       n_estimators=200,
       max_depth=8,
       learning_rate=0.1,
       reg_alpha=0.1,
       reg_lambda=1.0,
   )

GBLinear Model (``gblinear``)
------------------------------

The ``gblinear`` model uses XGBoost's linear booster rather than tree-based learners. Each boosting round fits a linear model, and the final prediction is a sum of linear models — effectively a regularised linear regression trained with gradient boosting. It supports only a single forecast horizon per model instance (``max_length=1`` on the ``horizons`` field).

**When to use it:**

- The load signal is well-described by a linear combination of features
- You need a model that extrapolates predictably beyond the training range (important for new grid connections or assets with limited history)
- Interpretability is a priority — feature contributions are directly proportional to feature values
- You are forecasting a signal where non-linear tree splits would overfit noise

**Key hyperparameters:**

.. code-block:: python

   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearHyperParams

   hyperparams = GBLinearHyperParams(
       n_steps=500,
       learning_rate=0.15,
       reg_alpha=0.1,
       reg_lambda=1.0,
       updater="shotgun",
   )

The ``n_steps`` parameter plays the role that ``n_estimators`` plays in tree models. Regularisation via ``reg_alpha`` (L1) and ``reg_lambda`` (L2) is especially important here because the model is otherwise prone to overfitting when features are correlated.

.. note::

   ``gblinear`` accepts only a single horizon per instance. If you need forecasts at multiple lead times, instantiate one ``gblinear`` model per horizon or use an ensemble workflow.

Median Model (``median``)
--------------------------

The median model is an autoregressive forecaster that predicts future load based on the median of recent observations. It does not use external features such as weather. This makes it robust to feature data quality issues but limits its accuracy when the load is driven by external conditions.

The model is specifically designed for two signal types described in its documentation:

- **Slow-dynamics signals** — load that changes very slowly relative to the sampling interval, possibly with a lot of noise (e.g., a baseload with random fluctuations)
- **State-switching signals** — load that alternates between a small number of discrete states in a way that is random or depends on unknown features, but tends to be stable within each state (e.g., waste heat from an industrial process)

**When to use it:**

- No reliable feature data is available
- The load is nearly constant or switches between known states
- You want a simple, robust baseline to benchmark other models against

**Configuration tip:** Set lag features to be evenly spaced and matched to the sampling frequency of your input data to get the best hysteresis behaviour from the median window.

Flatliner Model (``flatliner``)
--------------------------------

The flatliner forecaster predicts a constant value — either zero or the median of recent observations — for all future timesteps. It is not a general-purpose forecasting model. Its primary uses are:

- As a **fallback** when a flatline measurement is detected in the input data and expected to continue (e.g., a metering fault that produces a stuck value)
- As a **baseline** to establish a lower bound on what any real model should beat
- For assets that are genuinely offline or decommissioned

The ``FlatlinerForecaster`` can optionally detect non-zero flatlines (controlled by ``detect_non_zero_flatliner``), in which case it predicts the median of the recent stuck value rather than zero.

See :doc:`reliability_and_fallback` for how the flatliner model fits into production fallback strategies.

Configuring the Model Type
--------------------------

All model types are selected through the ``model_type`` field of the forecasting workflow configuration. The corresponding hyperparameter block is also specified there:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile as Q
   from openstef_models.workflows.forecasting_workflow import ForecastingWorkflowConfig

   # XGBoost configuration — suitable for most general-purpose load forecasting
   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model_type="xgboost",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       sample_interval=timedelta(minutes=15),
       horizons=[LeadTime.from_string("PT48H")],
   )

Switching to LightGBM requires only changing ``model_type``:

.. code-block:: python

   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model_type="lgbm",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       sample_interval=timedelta(minutes=15),
       horizons=[LeadTime.from_string("PT48H")],
   )

To customise hyperparameters, pass the appropriate hyperparameter object:

.. code-block:: python

   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearHyperParams

   config = ForecastingWorkflowConfig(
       model_id="linear_asset",
       model_type="gblinear",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       sample_interval=timedelta(minutes=15),
       horizons=[LeadTime.from_string("PT24H")],
       gblinear_hyperparams=GBLinearHyperParams(
           n_steps=600,
           learning_rate=0.1,
           reg_lambda=2.0,
       ),
   )

Ensemble Models
---------------

When no single model type dominates across all conditions, OpenSTEF supports ensemble forecasting that combines predictions from multiple base models. A common pattern is combining ``gblinear`` and ``lgbm``: the linear model handles extrapolation and regime changes well, while the tree model captures non-linear patterns in well-represented training conditions.

.. code-block:: python

   from openstef_models.workflows.ensemble_forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
   )

   ensemble_config = EnsembleForecastingWorkflowConfig(
       model_id="ensemble_substation",
       ensemble_type="learned_weights",
       base_models=["gblinear", "lgbm"],
       combiner_model="lgbm",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime.from_string("PT36H")],
   )

The ``learned_weights`` ensemble type trains a combiner model (here another LightGBM) to weight the base model predictions dynamically based on input conditions.

Practical Selection Guide
--------------------------

The following table summarises the key trade-offs:

+----------------+------------------+------------------+-------------------+-------------------+
| Model          | Non-linear       | Extrapolation    | Multi-horizon     | Feature-free      |
+================+==================+==================+===================+===================+
| ``xgboost``    | ✓ Strong         | ✗ Poor           | ✓                 | ✗                 |
+----------------+------------------+------------------+-------------------+-------------------+
| ``lgbm``       | ✓ Strong         | ✗ Poor           | ✓                 | ✗                 |
+----------------+------------------+------------------+-------------------+-------------------+
| ``lgbmlinear`` | ✓ Moderate       | ✓ Moderate       | ✓                 | ✗                 |
+----------------+------------------+------------------+-------------------+-------------------+
| ``gblinear``   | ✗ Weak           | ✓ Strong         | ✗ Single horizon  | ✗                 |
+----------------+------------------+------------------+-------------------+-------------------+
| ``median``     | N/A              | ✓ (by design)    | ✓                 | ✓                 |
+----------------+------------------+------------------+-------------------+-------------------+
| ``flatliner``  | N/A              | ✓ (trivially)    | ✓                 | ✓                 |
+----------------+------------------+------------------+-------------------+-------------------+

A few rules of thumb from production deployments:

- **Start with** ``xgboost`` or ``lgbm`` for any asset with at least a few months of history and weather features available. These models are the most robust general-purpose choice.
- **Use** ``gblinear`` for new assets, assets with limited history, or any signal where you have reason to believe the relationship between load and features is approximately linear.
- **Use** ``lgbmlinear`` when tree models produce forecasts that are too "blocky" or when you need better behaviour at the edges of the feature distribution.
- **Use** ``median`` when feature data is unavailable or unreliable, particularly for slow-moving or state-switching signals.
- **Reserve** ``flatliner`` for fallback scenarios — it should not be the primary model for any asset where accurate forecasting matters.
- **Consider an ensemble** when you have enough training data to support a combiner model and when single-model accuracy has plateaued.

.. note::

   Model selection interacts closely with feature engineering. A ``gblinear`` model with well-constructed lag and calendar features can outperform a poorly configured ``xgboost`` model. See :doc:`feature_engineering` for guidance on building effective feature sets.

Related Pages
-------------

- :doc:`forecasting_basics` — Introduction to short-term forecasting and how OpenSTEF pipelines work
- :doc:`quantiles_and_confidence` — How probabilistic outputs are produced and interpreted across model types
- :doc:`feature_engineering` — Building the feature set that feeds into these models
- :doc:`reliability_and_fallback` — How the flatliner and median models fit into production fallback strategies