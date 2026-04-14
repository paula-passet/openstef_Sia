Model Selection
===============

OpenSTEF provides several forecasting model implementations, each suited to different load patterns, data characteristics, and operational requirements. This page explains the available models, their trade-offs, and how to choose between them — including how OpenSTEF can automate that choice at training time.

For background on what short-term forecasting involves, see :doc:`forecasting_basics`. For details on probabilistic outputs such as quantiles, see :doc:`quantiles_and_confidence`.

Available Models
----------------

OpenSTEF ships three forecaster implementations in the ``openstef-models`` package. All implement the same ``Forecaster`` base interface, so they are interchangeable within a workflow.

**XGBoostForecaster**

The gradient-boosted tree model built on XGBoost. This is the most widely deployed model in production OpenSTEF installations and the natural starting point for most use cases. It handles non-linear relationships well, is robust to missing features, and produces reliable probabilistic outputs across a wide range of quantiles.

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_core.data_classes.quantile import Quantile
   from openstef_core.data_classes.lead_time import LeadTime
   from datetime import timedelta

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=XGBoostHyperParams(
           n_estimators=200,
           max_depth=6,
           learning_rate=0.05,
       ),
   )

Key hyperparameters: ``n_estimators``, ``max_depth``, ``learning_rate``. Supports GPU acceleration via the ``device`` field (``"cuda"`` or ``"gpu"``).

**LGBMForecaster**

A gradient-boosted tree model built on LightGBM. It trains significantly faster than XGBoost on large datasets and often achieves comparable accuracy. The speed advantage becomes meaningful when retraining frequently or when working with many prediction locations in parallel. LightGBM also supports GPU computation via the ``device`` field.

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )

   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=LGBMHyperParams(
           n_estimators=200,
           learning_rate=0.05,
       ),
       n_jobs=-1,  # use all available cores
   )

**GBLinearForecaster**

A linear model that uses XGBoost's ``gblinear`` booster rather than tree-based splitting. Despite the XGBoost backend, this model behaves like a regularised linear regression: it learns additive feature weights rather than decision trees. It is interpretable, fast to train, and well-suited to loads that follow predictable linear patterns (e.g. industrial consumers with stable schedules).

``GBLinearForecaster`` has one important constraint: it only supports a **single horizon** per instance. If you need multi-horizon forecasts with a linear model, you must train one instance per horizon.

.. code-block:: python

   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )

   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],  # single horizon only
       hyperparams=GBLinearHyperParams(),
   )

Choosing a Model
----------------

The table below summarises the practical trade-offs:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Model
     - Non-linear patterns
     - Training speed
     - Interpretability
     - Multi-horizon
   * - XGBoostForecaster
     - Excellent
     - Moderate
     - Feature importance
     - Yes
   * - LGBMForecaster
     - Excellent
     - Fast
     - Feature importance
     - Yes
   * - GBLinearForecaster
     - Limited
     - Very fast
     - High (weights)
     - Single horizon only

**Start with XGBoostForecaster or LGBMForecaster** for most residential and mixed-use grid connections. Both handle the non-linear interactions between weather, calendar effects, and load that dominate real-world energy data.

**Prefer LGBMForecaster** when training time is a constraint — for example, when retraining dozens of locations on a tight schedule, or when iterating quickly during development.

**Use GBLinearForecaster** when the load profile is well-understood and predominantly linear, or when you need to inspect model weights directly for regulatory or operational reasons. It also works well as a component inside an ensemble (see below).

.. note::

   All three models produce probabilistic forecasts across the quantiles you specify. The choice of model does not affect the quantile output interface. See :doc:`quantiles_and_confidence` for how to interpret these outputs.

Configuring Models via Workflow
-------------------------------

In practice, you will rarely instantiate a forecaster directly. Instead, you configure the model type through ``ForecastingWorkflowConfig``, which builds the complete pipeline — preprocessing, feature engineering, and postprocessing — appropriate for the chosen model:

.. code-block:: python

   from openstef_core.workflows.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model="xgboost",          # or "lgbm", "gblinear"
       model_id="my_connection",
       horizons=[timedelta(hours=1), timedelta(hours=24)],
       quantiles=[0.1, 0.5, 0.9],
       # ... location, feature columns, etc.
   )

   workflow = create_forecasting_workflow(config)

The ``model`` field accepts ``"xgboost"``, ``"lgbm"``, or ``"gblinear"``. The workflow factory automatically adjusts feature engineering for the chosen model — for example, ``GBLinearForecaster`` uses only the 7-day lag feature rather than the full lag set that tree-based models receive. This is handled internally; you do not need to configure it manually.

.. note::

   .. mermaid:: /diagrams/concepts/model_selection_diagram_1.mmd

Automatic Model Selection
-------------------------

OpenSTEF supports automatic model selection during retraining. When enabled, the library evaluates the newly trained model against the previously stored model and keeps whichever performs better on the validation set. This is controlled by three fields on the workflow configuration:

.. code-block:: python

   config = ForecastingWorkflowConfig(
       model="xgboost",
       model_id="my_connection",
       # Automatic model selection settings
       model_selection_enable=True,           # default: True
       model_selection_metric=(
           Q(0.5), "R2", "higher_is_better"  # default metric
       ),
       model_selection_old_model_penalty=1.2, # default: 1.2
       # ...
   )

The ``model_selection_old_model_penalty`` introduces a deliberate bias toward keeping the existing model: the old model's metric is multiplied by this factor before comparison. A value of ``1.2`` means the new model must outperform the old one by at least 20% on the selection metric before it replaces it. This prevents unnecessary churn from small random fluctuations in training data.

.. note::

   Automatic model selection requires MLflow storage to be configured, since the previous model must be retrievable for comparison. See :doc:`reliability_and_fallback` for how fallback behaviour interacts with model storage.

When automatic selection is disabled (``model_selection_enable=False``), every completed training run unconditionally replaces the stored model. This is appropriate during initial development or when you want deterministic retraining behaviour.

Hyperparameter Tuning
---------------------

Each model exposes its hyperparameters through a typed ``HyperParams`` class. The defaults are reasonable for most grid connections, but tuning can improve accuracy for unusual load profiles.

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams

   # Conservative settings for a stable, low-variance load
   conservative = XGBoostHyperParams(
       n_estimators=100,
       max_depth=4,       # shallower trees reduce overfitting
       learning_rate=0.1,
   )

   # Expressive settings for a volatile, weather-sensitive load
   expressive = XGBoostHyperParams(
       n_estimators=500,
       max_depth=8,
       learning_rate=0.02,
       early_stopping_rounds=20,  # stop if validation doesn't improve
   )

Use ``early_stopping_rounds`` when you have a validation set and want to avoid overfitting without manually tuning ``n_estimators``. Both ``XGBoostForecaster`` and ``LGBMForecaster`` support this parameter.

For ``GBLinearForecaster``, the hyperparameter space is smaller — primarily regularisation strength — reflecting the simpler model structure.

Ensemble Models
---------------

Beyond the three single-model forecasters, OpenSTEF also provides an ensemble workflow (``EnsembleForecastingWorkflowConfig``) that combines predictions from multiple base models using a learned combiner. Ensembles can outperform any individual model on heterogeneous portfolios where different connection types favour different model structures.

Ensemble configuration is more involved and is covered separately. The key point for model selection is that the individual forecasters described on this page serve as the building blocks of ensemble workflows — understanding their individual characteristics helps you choose which models to include.

Summary
-------

- **XGBoostForecaster**: best default choice; handles non-linear patterns, supports multiple horizons.
- **LGBMForecaster**: same capability as XGBoost with faster training; prefer for high-throughput retraining.
- **GBLinearForecaster**: interpretable linear model; use for stable loads or as an ensemble component; single horizon only.
- Configure model type via ``ForecastingWorkflowConfig(model=...)`` rather than instantiating forecasters directly.
- Enable ``model_selection_enable=True`` to let OpenSTEF automatically retain the better model across retraining runs.

For details on the features that feed these models, see :doc:`feature_engineering`. For how OpenSTEF handles model failures in production, see :doc:`reliability_and_fallback`.