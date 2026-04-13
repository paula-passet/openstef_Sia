Model Selection
===============

OpenSTEF provides several forecasting model implementations, each with different strengths. Choosing the right model — or letting the library choose for you — has a meaningful impact on forecast accuracy, training speed, and operational robustness. This page explains the available models, their trade-offs, and how to configure model selection in your workflows.

For background on what short-term energy forecasting involves, see :doc:`forecasting_basics`. For details on probabilistic outputs such as quantile forecasts, see :doc:`quantiles_and_confidence`.

Available Model Types
---------------------

OpenSTEF ships four core forecaster implementations, all found in ``openstef_models.models.forecasting``:

- **XGBoostForecaster** — gradient-boosted decision trees using XGBoost. The general-purpose workhorse for non-linear load patterns.
- **LGBMForecaster** — gradient-boosted trees with linear leaves using LightGBM. Faster to train than XGBoost and often competitive in accuracy.
- **GBLinearForecaster** — a linear booster using XGBoost's ``gblinear`` backend. Suited to loads with predominantly linear relationships.
- **LGBMLinearForecaster** — LightGBM with linear leaf estimation. Combines the speed of LightGBM with linear inductive bias.

All four implement the same ``Forecaster`` base interface, so they are interchangeable in any workflow configuration. Each supports multi-quantile output for probabilistic forecasting.

.. note::
   XGBoost and LightGBM are optional dependencies. Install them with
   ``pip install openstef-models[xgboost]`` and ``pip install openstef-models[lightgbm]``
   respectively.

Model Characteristics at a Glance
----------------------------------

.. mermaid:: /diagrams/concepts/model_selection_diagram_1.mmd

The tree-based models (``XGBoostForecaster``, ``LGBMForecaster``) capture complex non-linear interactions between features — for example, the combined effect of temperature and time-of-day on residential load. They are the right default choice for most substations and grid connections where load behaviour is driven by multiple interacting factors.

The linear boosters (``GBLinearForecaster``, ``LGBMLinearForecaster``) impose a linear structure on the learned function. This makes them faster to train and more interpretable, but they will underfit loads with strong non-linear seasonality or weather coupling. They perform well as components in an ensemble (see below), where their linear bias complements the tree models' flexibility.

One practical constraint: ``GBLinearForecaster`` supports **only a single forecast horizon** per model instance (``max_length=1`` on its ``horizons`` field). If you need multi-horizon forecasts from a linear booster, you must train one instance per horizon.

When to Use Each Model
-----------------------

**Use XGBoostForecaster when:**

- You need a reliable, well-understood baseline.
- Your load has strong non-linear weather dependence (e.g., heat pumps, cooling loads).
- You want GPU acceleration for large datasets (set ``device="cuda"``).
- Training time is not a bottleneck.

**Use LGBMForecaster when:**

- Training speed matters — LightGBM is typically 3–5× faster than XGBoost on the same data.
- You are retraining frequently (e.g., daily retraining pipelines).
- Accuracy requirements are similar to XGBoost but you want lower compute cost.

**Use GBLinearForecaster or LGBMLinearForecaster when:**

- The load is largely linear in its predictors (e.g., industrial processes with stable operating schedules).
- You are building an ensemble and want a model with different inductive bias to improve diversity.
- Interpretability is important and you want to inspect feature weights directly.

Configuring a Single Model
---------------------------

Each forecaster is configured via a Pydantic model. The following example trains an ``XGBoostForecaster`` directly:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import Quantile as Q, LeadTime
   from openstef_models.models.forecasting.xgboost import XGBoostForecaster, XGBoostHyperParams

   forecaster = XGBoostForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=24)),
       ],
       hyperparams=XGBoostHyperParams(
           n_estimators=200,
           max_depth=6,
           learning_rate=0.05,
       ),
       device="cpu",
       n_jobs=-1,
   )

   forecaster.fit(training_data)
   predictions = forecaster.predict(test_data)

Switching to LightGBM requires only changing the import and class name — the rest of the interface is identical:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm import LGBMForecaster, LGBMHyperParams

   forecaster = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=LGBMHyperParams(
           n_estimators=200,
           max_depth=6,
           learning_rate=0.05,
       ),
   )

Ensemble Workflows and Automatic Model Selection
-------------------------------------------------

In production, OpenSTEF's ``EnsembleForecastingWorkflowConfig`` combines multiple base models through a learned combiner. This is the recommended approach for most deployments because it is more robust than any single model and reduces the risk of a poorly-fitting model dominating the forecast.

.. code-block:: python

   from openstef_models.workflows.ensemble_forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )
   from openstef_core.datasets import Quantile as Q
   from datetime import timedelta

   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42",
       base_models=["lgbm", "xgboost", "gblinear"],
       combiner_model="lgbm",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[timedelta(hours=h) for h in range(1, 49)],
       model_selection_enable=True,
       model_selection_metric=("Q(0.5)", "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,
   )

   workflow = create_ensemble_forecasting_workflow(config)

The ``base_models`` field accepts any combination of ``"lgbm"``, ``"xgboost"``, ``"gblinear"``, and ``"lgbm_linear"``. The combiner (``combiner_model``) learns how to weight their outputs on a held-out validation set.

Automatic Model Selection
^^^^^^^^^^^^^^^^^^^^^^^^^^

When ``model_selection_enable=True``, OpenSTEF compares the newly trained model against the previously stored model using the configured ``model_selection_metric``. The default metric is median-quantile R² (``Q(0.5), "R2", "higher_is_better"``).

A key parameter here is ``model_selection_old_model_penalty``. Set to ``1.2`` by default, it requires the new model to score at least 20% better than the incumbent before it replaces it. This prevents noisy retraining runs from deploying a worse model. You can tighten this threshold (closer to ``1.0``) if you retrain on large, stable datasets, or loosen it (e.g., ``1.5``) in volatile conditions where you want to preserve the existing model more aggressively.

.. code-block:: python

   # Conservative replacement: new model must be 30% better
   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42",
       model_selection_enable=True,
       model_selection_old_model_penalty=1.3,
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
       # ... other fields
   )

Model reuse (``model_reuse_enable=True``) complements selection: if the stored model is less than ``model_reuse_max_age`` old and still passes the selection threshold, the pipeline skips retraining entirely. This is useful in high-frequency retraining pipelines where the load pattern has not changed.

Hyperparameter Tuning
----------------------

All hyperparameter classes (``XGBoostHyperParams``, ``LGBMHyperParams``, ``GBLinearHyperParams``, ``LGBMLinearHyperParams``) are Pydantic models with validated fields. The most impactful parameters across all tree-based models are:

- ``n_estimators`` — number of boosting rounds. Higher values improve fit but increase training time and risk overfitting. Start at 100–200 and tune upward.
- ``max_depth`` — maximum tree depth. Values of 4–8 cover most energy forecasting use cases. Deeper trees capture more interactions but overfit on small datasets.
- ``learning_rate`` — shrinkage applied to each tree's contribution. Lower values (0.01–0.05) combined with more estimators generally produce better generalisation.
- ``reg_alpha`` / ``reg_lambda`` — L1 and L2 regularisation. Increase these when you have many features relative to training samples (see :doc:`feature_engineering`).

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_linear import (
       LGBMLinearForecaster,
       LGBMLinearHyperParams,
   )

   forecaster = LGBMLinearForecaster(
       quantiles=[Q(0.5)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=LGBMLinearHyperParams(
           n_estimators=200,
           max_depth=8,
           learning_rate=0.1,
           reg_alpha=0.1,
           reg_lambda=1.0,
       ),
   )

.. note::
   OpenSTEF does not currently include a built-in hyperparameter search pipeline.
   The recommended approach is to run backtests with different configurations using
   ``BacktestForecasterConfig`` and compare R² scores across the validation window.

Practical Recommendations
--------------------------

For most new deployments, start with the ensemble of ``["lgbm", "xgboost", "gblinear"]``. This combination covers non-linear and linear load patterns, trains in reasonable time, and benefits from the combiner's learned weighting. Move to a single-model configuration only if you have a specific reason — for example, strict latency constraints on training or a load that is demonstrably linear.

If you observe that one base model consistently receives near-zero weight from the combiner across many substations, it is safe to remove it from ``base_models`` to reduce training overhead. Conversely, if forecast accuracy on a particular asset is poor, adding ``"lgbm_linear"`` as a fourth base model sometimes helps by introducing additional linear diversity.

For assets where training data is sparse (fewer than 30 days), prefer ``GBLinearForecaster`` or ``LGBMLinearForecaster`` as the sole model. Tree-based models require more data to generalise well and will overfit on short histories.

When deploying in production, pair model selection with a fallback strategy so that a failed retraining run does not leave the asset without a forecast. See :doc:`reliability_and_fallback` for details on how OpenSTEF handles model failures and degraded-mode operation.