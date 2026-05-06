The openstef_models Package
===========================

This page covers ``openstef_models``, the package that provides the full modelling
stack for OpenSTEF: feature-engineering transforms, forecasting and component-splitting
models, workflow presets, integrations (e.g. MLflow), mixins, and explainability
utilities.  The package depends on ``openstef-core`` for validated dataset types and
base classes, and is consumed by ``openstef-beam`` pipelines for large-scale execution.
See the :doc:`core` and :doc:`beam` sibling pages for those layers.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

Package layout
--------------

The package is organised into five top-level namespaces:

- ``openstef_models.transforms`` — domain-aware and general-purpose feature engineering
- ``openstef_models.models`` — forecasting and component-splitting model implementations
- ``openstef_models.presets`` — high-level workflow factories
- ``openstef_models.integrations`` — optional third-party integrations (MLflow)
- ``openstef_models.mixins`` — reusable behaviours for serialisation and callbacks
- ``openstef_models.explainability`` — feature-importance and contribution utilities

Transforms
----------

Transforms are scikit-learn-compatible steps that prepare a ``TimeSeriesDataset``
(defined in ``openstef-core``) before it reaches a model.  They are split into two
sub-packages reflecting their purpose.

Energy-domain transforms
^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_models.transforms.energy_domain`` contains transforms that encode
physical knowledge about the energy system.  The most commonly used example is
``WindPowerFeatureAdder``, which derives wind-power proxy features from meteorological
inputs:

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    wind_adder = WindPowerFeatureAdder()
    enriched = wind_adder.fit_transform(dataset)

Other energy-domain transforms handle solar irradiance proxies, demand-temperature
relationships, and similar physics-informed features.  Keeping these separate from
general transforms makes it straightforward to include or exclude domain knowledge
for a given asset type.

General transforms
^^^^^^^^^^^^^^^^^^

``openstef_models.transforms.general`` provides asset-agnostic preprocessing:

- ``Imputer`` — fills missing values in time-series data
- ``OutlierHandler`` — detects and clips statistical outliers
- ``Scaler`` — normalises features before tree or linear models
- ``Shifter`` — creates lag and lead copies of columns
- ``EmptyFeatureRemover`` — drops zero-variance or all-NaN columns
- ``SampleWeighter`` / ``SampleWeightConfig`` — assigns per-sample training weights,
  useful for recency weighting or event-based emphasis

A typical preprocessing chain looks like:

.. code-block:: python

    from sklearn.pipeline import Pipeline
    from openstef_models.transforms.general import (
        Imputer,
        OutlierHandler,
        Scaler,
        Shifter,
        EmptyFeatureRemover,
    )

    preprocessing = Pipeline([
        ("impute",   Imputer()),
        ("outliers", OutlierHandler()),
        ("shift",    Shifter(lags=[1, 2, 3, 24, 48])),
        ("drop",     EmptyFeatureRemover()),
        ("scale",    Scaler()),
    ])

Forecasting models
------------------

All forecasting models live under ``openstef_models.models.forecasting`` and share the
``Forecaster`` base class.  They accept a ``ForecastInputDataset`` and return
probabilistic forecasts across a configurable set of quantiles.

The available implementations fall into two categories:

**Gradient-boosted tree models** — the primary workhorses for production forecasting:

- ``XGBoostForecaster`` (``XGBoostHyperParams``) — XGBoost multi-quantile model
- ``LGBMForecaster`` (``LGBMHyperParams``) — LightGBM multi-quantile model
- ``GBLinearForecaster`` (``GBLinearHyperParams``) — gradient-boosted linear booster,
  useful when interpretability matters more than raw accuracy
- ``LGBMLinearForecaster`` (``LGBMLinearHyperParams``) — LightGBM with a linear tree
  learner, combining speed with partial linearity

**Baseline model**:

- ``BaseCaseForecaster`` (``BaseCaseForecasterHyperParams``) — lag-based heuristic
  that requires no training; useful as a fallback or benchmark

Each model exposes a ``HyperParams`` dataclass so that configuration is validated
before training begins:

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    params = XGBoostHyperParams(n_estimators=500, learning_rate=0.05)
    model = XGBoostForecaster(hyperparams=params)
    model.fit(train_dataset)
    forecast = model.predict(input_dataset)

Component splitting
-------------------

``openstef_models.models.component_splitting_model`` provides ``ComponentSplittingModel``,
a high-level pipeline that decomposes a net-load signal into its physical constituents
(e.g. solar, wind, base load).  It implements both ``BaseModel`` and
``ComponentSplitter`` from ``openstef-core``, so it integrates with the same workflow
machinery as the forecasting models.

.. code-block:: python

    from openstef_models.models.component_splitting_model import ComponentSplittingModel

    splitter = ComponentSplittingModel(config=my_splitter_config)
    splitter.fit(train_dataset)

    # Returns an EnergyComponentDataset with one column per component
    components: EnergyComponentDataset = splitter.predict(input_dataset)

The underlying ``LinearComponentSplitter`` performs the actual decomposition; the
``ComponentSplittingModel`` wrapper adds preprocessing, postprocessing, and the
standard ``is_fitted`` guard.  Training is not supported on the linear splitter
itself — coefficients are derived analytically from the configuration.

Presets and workflows
---------------------

Rather than assembling transforms and models by hand, ``openstef_models.presets``
provides factory functions that wire everything together into a ready-to-use workflow
object.

``create_forecasting_workflow`` accepts a ``ForecastingWorkflowConfig`` (which embeds
a ``LocationConfig`` for tagging) and returns a ``CustomForecastingWorkflow``:

.. code-block:: python

    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )

    config = ForecastingWorkflowConfig(
        location=LocationConfig(region="NL", asset_id="wind-farm-42"),
        model_type="xgboost",
    )

    workflow = create_forecasting_workflow(config)
    workflow.fit(train_dataset)
    forecast = workflow.predict(input_dataset)

The ``CustomForecastingWorkflow`` and ``CustomComponentSplitWorkflow`` classes (in
``openstef_models.workflows``) add callback hooks and optional persistence on top of
the underlying model.  This is the layer that ``openstef-beam`` pipelines target — see
:doc:`beam` for how these workflows are executed at scale.

Integrations
------------

MLflow
^^^^^^

``openstef_models.integrations.mlflow`` provides two classes for model lifecycle
management:

- ``MLFlowStorage`` — stores and loads serialised models from an MLflow model registry
- ``MLFlowStorageCallback`` — a ``PredictorCallback`` that automatically logs and
  registers a model after each training run

.. code-block:: python

    from openstef_models.integrations.mlflow import (
        MLFlowStorage,
        MLFlowStorageCallback,
    )
    from openstef_models.mixins import ModelIdentifier

    storage = MLFlowStorage(tracking_uri="http://mlflow.example.com")
    callback = MLFlowStorageCallback(storage=storage)

    # Pass the callback to a workflow so models are persisted automatically
    workflow = create_forecasting_workflow(config)
    workflow.fit(train_dataset, callbacks=[callback])

.. note::

   MLflow is an optional dependency.  Install it with
   ``pip install openstef-models[mlflow]`` before using this integration.

Mixins
------

``openstef_models.mixins`` provides three reusable behaviours that can be composed
into custom model or workflow classes:

- ``PredictorCallback`` — base class for lifecycle hooks (``on_fit_start``,
  ``on_fit_end``, ``on_predict_start``, ``on_predict_end``).  Both
  ``MLFlowStorageCallback`` and the component-split ``ComponentSplitCallback`` extend
  this.
- ``ModelSerializer`` — handles serialisation and deserialisation of model state,
  used internally by ``MLFlowStorage``.
- ``ModelIdentifier`` — attaches a stable identifier (region, asset, model type) to a
  model instance, which flows through to MLflow tags and experiment names.

These mixins follow a composition-over-inheritance pattern: add only the behaviours
your custom class needs.

Explainability
--------------

``openstef_models.explainability`` provides two mixins that tree-based forecasters
implement:

- ``ExplainableForecaster`` — exposes a ``feature_importances`` property returning a
  ``pd.DataFrame`` of importance scores, plus ``plot_feature_importances`` which
  renders an interactive Plotly treemap grouped by feature domain.
- ``ContributionsMixin`` — adds ``predict_contributions``, which returns a
  ``TimeSeriesDataset`` of per-sample, per-feature SHAP-style contributions.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

    model = XGBoostForecaster()
    model.fit(train_dataset)

    # Tabular importance scores
    importances = model.feature_importances()
    print(importances.head())

    # Interactive treemap (returns a plotly Figure)
    fig = model.plot_feature_importances()
    fig.show()

    # Per-sample contributions
    contributions = model.predict_contributions(input_dataset)

.. note:: [VISUALIZATION: Plotly treemap of feature importances grouped by domain (e.g. weather, lag, calendar), with node size proportional to importance score]

Both mixins are abstract — concrete forecasters must implement the underlying
computation.  ``XGBoostForecaster`` and ``LGBMForecaster`` both provide full
implementations; ``BaseCaseForecaster`` does not, since it has no learned weights.

Ensemble models are handled in ``openstef_meta`` rather than here — see :doc:`meta`
for ``EnsembleForecastingModel`` and the combiner classes that aggregate outputs from
multiple ``openstef_models`` forecasters.