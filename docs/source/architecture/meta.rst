The openstef_meta Package
=========================

The ``openstef_meta`` package sits at the top of the OpenSTEF dependency graph.
It composes the validated data structures from ``openstef_core``, the model
transforms and workflows from ``openstef_models``, and the distributed pipeline
infrastructure from ``openstef_beam`` into a single ensemble forecasting layer.
This page explains how the three main abstractions — ``EnsembleForecastingModel``,
the ``ForecastCombiner`` hierarchy, and the ``EnsembleForecastingWorkflowConfig``
presets — fit together and how to use them in practice.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd

Architecture overview
---------------------

``openstef_meta`` does not define new feature engineering or new ML estimators.
Instead it wires together components that already exist in the lower-level
packages:

- **openstef_core** supplies the typed dataset contracts (``TimeSeriesDataset``,
  ``ForecastInputDataset``, ``ForecastDataset``) that flow through every stage.
- **openstef_models** supplies the ``BaseForecastingModel`` interface, all
  transform primitives, and the ``CustomForecastingWorkflow`` runner.
- **openstef_beam** supplies distributed pipeline execution; the preset
  workflows in ``openstef_meta`` can be handed directly to a Beam runner.

The meta package adds one thing: a *combiner* that turns N independent
forecasts into a single, better-calibrated output.

EnsembleForecastingModel
------------------------

``EnsembleForecastingModel`` implements ``BaseForecastingModel`` from
``openstef_models``.  Its constructor receives a dictionary of named
``Forecaster`` configurations and a ``ForecastCombiner`` instance.  During
``fit`` each base forecaster is trained independently on the same dataset;
during ``predict`` their outputs are stacked and passed to the combiner.

.. code-block:: python

    from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
    from openstef_meta.models.forecast_combiners import WeightsCombiner, LGBMCombinerHyperParams

    # Two base forecasters defined elsewhere via openstef_models
    forecaster_configs = {
        "lgbm": lgbm_forecaster_config,
        "xgboost": xgb_forecaster_config,
    }

    combiner = WeightsCombiner(hyperparams=LGBMCombinerHyperParams())

    model = EnsembleForecastingModel(
        forecaster_configs=forecaster_configs,
        combiner=combiner,
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        max_horizon=LeadTime.from_string("PT48H"),
    )

    fit_result = model.fit(train_dataset)
    forecast: ForecastDataset = model.predict(input_dataset)

The ``fit_result`` is an ``EnsembleModelFitResult``, which exposes
``component_fit_results()`` — a per-forecaster breakdown of training metrics
that is useful for diagnosing which base model contributes most to overall
accuracy.

Inspecting contributions
^^^^^^^^^^^^^^^^^^^^^^^^

After fitting you can call ``predict_contributions`` to obtain a
``TimeSeriesDataset`` where each column corresponds to one base model's raw
prediction.  This is the primary tool for understanding ensemble behaviour
without reaching for external explainability libraries.

.. code-block:: python

    contributions = model.predict_contributions(input_dataset)
    # contributions is a TimeSeriesDataset; column names match forecaster_configs keys

For models that implement ``ExplainableForecaster``, ``get_explainable_components``
returns the subset of base forecasters that support SHAP-style explanations.

ForecastCombiner and its implementations
-----------------------------------------

``ForecastCombiner`` is an abstract base class (ABC) that defines a single
contract: given a stacked ``TimeSeriesDataset`` of base-model predictions,
produce a combined ``ForecastDataset``.  All combiners must implement ``fit``
and ``predict``; the meta package ships two concrete implementations.

WeightsCombiner
^^^^^^^^^^^^^^^

``WeightsCombiner`` trains a *learned weighting* model — by default LightGBM,
but XGBoost, random forest, and logistic regression are also available — that
predicts the optimal linear combination of base forecasts at each time step.
The weighting model sees the base predictions as features, so it can learn
time-of-day or horizon-dependent blending automatically.

Hyperparameter classes follow a one-to-one naming convention:

.. code-block:: python

    from openstef_meta.models.forecast_combiners import (
        WeightsCombiner,
        LGBMCombinerHyperParams,   # default
        XGBCombinerHyperParams,
        RFCombinerHyperParams,
        LogisticCombinerHyperParams,
    )

    # Switch the combiner's internal model to random forest
    combiner = WeightsCombiner(hyperparams=RFCombinerHyperParams(n_estimators=200))

StackingCombiner
^^^^^^^^^^^^^^^^

``StackingCombiner`` implements classical stacking: a meta-learner is trained
on out-of-fold predictions from the base forecasters, so the combiner never
sees in-sample data during its own training.  This reduces overfitting when
base models are expressive and the training window is short.

.. code-block:: python

    from openstef_meta.models.forecast_combiners import StackingCombiner

    combiner = StackingCombiner()  # uses default meta-learner settings

    model = EnsembleForecastingModel(
        forecaster_configs=forecaster_configs,
        combiner=combiner,
        quantiles=[Q(0.5)],
        max_horizon=LeadTime.from_string("PT24H"),
    )

Choosing between the two
^^^^^^^^^^^^^^^^^^^^^^^^

Use ``WeightsCombiner`` when you have a long training history and want the
combiner to adapt to systematic patterns (e.g. one model is better at night,
another during peak demand).  Use ``StackingCombiner`` when training data is
scarce or when base models are already highly correlated, since the
out-of-fold discipline prevents the meta-learner from memorising base-model
errors.

EnsembleForecastingWorkflowConfig presets
------------------------------------------

Constructing an ``EnsembleForecastingModel`` by hand is verbose.  The
``openstef_meta.presets`` module provides ``EnsembleForecastingWorkflowConfig``
— a Pydantic ``BaseConfig`` — that encodes sensible defaults and can be
serialised to and from JSON or YAML for reproducible experiment tracking.

.. code-block:: python

    from datetime import timedelta
    from openstef_meta.presets.forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
        create_ensemble_forecasting_workflow,
    )
    from openstef_core.types import Q, LeadTime, ModelIdentifier

    config = EnsembleForecastingWorkflowConfig(
        model_id=ModelIdentifier("substation-42"),
        ensemble_type="learned_weights",   # or "stacking" or "rules"
        base_models=["lgbm", "xgboost"],
        combiner_model="lgbm",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        sample_interval=timedelta(minutes=15),
        horizons=[LeadTime.from_string("PT48H")],
        run_name="experiment-v1",
    )

    workflow = create_ensemble_forecasting_workflow(config)

``create_ensemble_forecasting_workflow`` returns a ``CustomForecastingWorkflow``
(from ``openstef_models``) that is ready to be executed locally or handed to an
``openstef_beam`` pipeline runner.  The three ``ensemble_type`` values map
directly to combiner choices:

- ``"learned_weights"`` → ``WeightsCombiner`` with the ``combiner_model``
  backend.
- ``"stacking"`` → ``StackingCombiner``.
- ``"rules"`` → a deterministic equal-weight average, useful as a baseline.

The ``base_models`` field accepts any combination of ``"lgbm"``,
``"gblinear"``, ``"xgboost"``, and ``"lgbm_linear"``.  Each entry resolves to
a pre-configured ``Forecaster`` from ``openstef_models``, so you do not need to
specify transforms or hyperparameters unless you want to override the defaults.

.. note::

   ``EnsembleForecastingWorkflowConfig`` is the recommended entry point for
   production use.  Direct construction of ``EnsembleForecastingModel`` is
   better suited to research and custom experiments where you need fine-grained
   control over individual base-forecaster hyperparameters.

Dependency relationships
-------------------------

Because ``openstef_meta`` depends on all three other packages, it is always the
outermost layer in any import chain.  A few practical consequences:

- You can use ``openstef_core``, ``openstef_models``, or ``openstef_beam``
  independently without installing ``openstef_meta``.
- ``openstef_meta`` types (``EnsembleForecastingModel``,
  ``EnsembleModelFitResult``) are never imported by the lower-level packages,
  so there are no circular dependencies.
- Dataset utilities in ``openstef_meta.utils.datasets`` — such as
  ``combine_forecast_input_datasets`` — bridge the ``ForecastInputDataset``
  contract from ``openstef_core`` with the multi-model prediction flow,
  handling optional additional feature sets via an ``inner`` or ``outer`` join.

.. code-block:: python

    from openstef_meta.utils.datasets import combine_forecast_input_datasets

    # Merge base predictions with extra contextual features before the combiner
    combined = combine_forecast_input_datasets(
        input_data=base_predictions,
        additional_features=weather_features,
        join="inner",
    )

Related pages
--------------

- :doc:`core` — ``ForecastInputDataset``, ``TimeSeriesDataset``, and the
  validated dataset hierarchy that flows through every stage described here.
- :doc:`models` — the transform primitives and ``CustomForecastingWorkflow``
  that ``openstef_meta`` builds on top of.
- :doc:`beam` — distributed pipeline execution for running
  ``EnsembleForecastingWorkflowConfig``-based workflows at scale.