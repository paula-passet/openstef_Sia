The openstef_models Package
===========================

This page covers the ``openstef_models`` package — the central library for feature
engineering, forecasting models, component splitting, workflow orchestration, model
persistence, and explainability in OpenSTEF. It sits between the validated data
structures provided by :doc:`core` and the large-scale pipeline execution described
in :doc:`beam`.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

---

Transforms
----------

Transforms are scikit-learn–compatible steps that prepare a ``TimeSeriesDataset``
for model training or inference. They are organised into two sub-packages.

**General transforms** handle domain-agnostic preprocessing:

- ``Imputer`` — fills missing values in time series data
- ``OutlierHandler`` — detects and removes statistical outliers
- ``Scaler`` — normalises feature columns
- ``Shifter`` — creates time-shifted copies of columns (lag features)
- ``EmptyFeatureRemover`` — drops columns that carry no information
- ``SampleWeighter`` / ``SampleWeightConfig`` — assigns per-sample training weights

**Energy-domain transforms** encode physical knowledge about the power system:

- ``WindPowerFeatureAdder`` — derives wind power proxy features from meteorological
  inputs such as wind speed and direction

The split between general and domain-specific transforms is intentional: general
transforms can be reused across any time-series problem, while energy-domain
transforms encode assumptions that are specific to electricity forecasting.

.. code-block:: python

    from openstef_models.transforms.general import (
        Imputer,
        OutlierHandler,
        Scaler,
        Shifter,
        EmptyFeatureRemover,
        SampleWeighter,
        SampleWeightConfig,
    )
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    # Transforms are composed inside a model or workflow — see the
    # `Presets and Workflows`_ section for how they are wired together automatically.

---

Forecasting Models
------------------

All forecasting models live under ``openstef_models.models.forecasting`` and share
the ``Forecaster`` base class. They produce probabilistic (multi-quantile) forecasts
over a ``ForecastInputDataset`` and return a ``TimeSeriesDataset``.

**Gradient-boosted tree models** are the primary workhorses:

- ``XGBoostForecaster`` (``XGBoostHyperParams``) — XGBoost with quantile regression
- ``LGBMForecaster`` (``LGBMHyperParams``) — LightGBM with quantile regression
- ``GBLinearForecaster`` (``GBLinearHyperParams``) — gradient-boosted linear model,
  useful when interpretability matters more than raw accuracy
- ``LGBMLinearForecaster`` (``LGBMLinearHyperParams``) — hybrid combining LightGBM
  trees with a linear head

**Baseline model:**

- ``BaseCaseForecaster`` (``BaseCaseForecasterHyperParams``) — lag-based heuristic
  that requires no training; useful as a sanity-check baseline or cold-start fallback

Each model class is paired with a ``HyperParams`` dataclass (a ``BaseConfig``
subclass from ``openstef_core``) so hyperparameters are validated at construction
time and can be serialised alongside the model.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    hyper_params = XGBoostHyperParams(n_estimators=300, learning_rate=0.05)
    model = XGBoostForecaster(hyper_params=hyper_params)

    model.fit(train_dataset)
    forecast = model.predict(input_dataset)

.. note::

    Ensemble and meta-learning combiners (``StackingCombiner``,
    ``WeightsCombiner``, etc.) are provided by the ``openstef_meta`` package and
    are documented on the :doc:`meta` page.

---

Component Splitting
-------------------

Energy load can be decomposed into physical components (e.g. base load, wind
contribution, solar contribution). The ``ComponentSplittingModel`` orchestrates this
decomposition as a self-contained pipeline.

.. code-block:: python

    from openstef_models.models.component_splitting_model import ComponentSplittingModel

    model = ComponentSplittingModel(config=splitter_config)
    model.fit(train_dataset)

    # Returns an EnergyComponentDataset with one column per component
    components: EnergyComponentDataset = model.predict(input_dataset)

Internally ``ComponentSplittingModel`` composes preprocessing transforms, a
``LinearComponentSplitter`` (which does not support re-training — it relies on
physical coefficients), and postprocessing steps. The ``is_fitted`` property
reflects whether the pipeline is ready to predict.

The high-level workflow counterpart is ``CustomComponentSplitWorkflow`` (see
`Presets and Workflows`_), which adds callback hooks and optional persistence around
the same model.

---

Presets and Workflows
---------------------

Presets are the highest-level entry point in ``openstef_models``. They assemble
transforms, a forecasting model, and a workflow into a single configured object so
callers do not need to wire components together manually.

``create_forecasting_workflow`` accepts a ``ForecastingWorkflowConfig`` and returns
a ``CustomForecastingWorkflow``:

.. code-block:: python

    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )

    location = LocationConfig(
        region="nl",
        substation="amsterdam_west",
        resolution_minutes=15,
    )

    config = ForecastingWorkflowConfig(
        location=location,
        model_type="xgboost",
        quantiles=[0.1, 0.5, 0.9],
    )

    workflow = create_forecasting_workflow(config)
    workflow.fit(train_dataset)
    forecast = workflow.predict(input_dataset)

``LocationConfig`` also exposes a ``tags`` property that returns a dictionary
suitable for passing directly to MLflow as run tags, keeping location metadata
attached to every tracked experiment.

The analogous ``CustomComponentSplitWorkflow`` follows the same pattern for
component splitting, accepting a ``ComponentSplitterConfig`` and exposing the same
``fit`` / ``predict`` interface.

---

Mixins
------

Three mixins in ``openstef_models.mixins`` provide reusable cross-cutting behaviour
that can be composed into any workflow class.

``ModelIdentifier``
   Attaches a stable, human-readable identifier to a model instance. Used by
   ``ModelSerializer`` to locate the correct artefact in a model store.

``ModelSerializer``
   Handles serialisation and deserialisation of model objects. Workflows that
   inherit from ``ModelSerializer`` can persist and reload themselves without
   coupling to a specific storage backend.

``PredictorCallback``
   A generic callback interface parameterised over the workflow type, input type,
   training return type, and prediction return type. Subclassing
   ``PredictorCallback`` lets you inject logic at any lifecycle stage — before
   training, after prediction, on error — without modifying the workflow itself.

.. code-block:: python

    from openstef_models.mixins import PredictorCallback
    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )
    from openstef_core.datasets import ForecastInputDataset, TimeSeriesDataset

    class MetricsLogger(
        PredictorCallback[
            CustomForecastingWorkflow,
            ForecastInputDataset,
            None,
            TimeSeriesDataset,
        ]
    ):
        def on_predict_end(self, ctx, result):
            print(f"Forecast produced {len(result)} rows")

---

MLflow Integration
------------------

The ``openstef_models.integrations.mlflow`` package bridges OpenSTEF workflows with
MLflow's experiment tracking and model registry.

``MLFlowStorage``
   Implements the ``ModelSerializer`` storage protocol backed by an MLflow model
   registry. Models are versioned automatically on each save.

``MLFlowStorageCallback``
   A ``PredictorCallback`` that calls ``MLFlowStorage`` at the end of a training
   run, logging hyperparameters, metrics, and the serialised model artefact in a
   single MLflow run.

.. code-block:: python

    from openstef_models.integrations.mlflow import (
        MLFlowStorage,
        MLFlowStorageCallback,
    )

    storage = MLFlowStorage(tracking_uri="http://mlflow.example.com")
    callback = MLFlowStorageCallback(storage=storage, experiment_name="load_forecast")

    workflow = create_forecasting_workflow(config)
    workflow.fit(train_dataset, callbacks=[callback])

.. note::

    MLflow is an optional dependency. Install it with
    ``pip install openstef-models[mlflow]`` before using this integration.

The ``LocationConfig.tags()`` property is designed to slot directly into MLflow's
``mlflow.set_tags()`` call, so every run is tagged with the location metadata
defined in the workflow configuration.

---

Explainability
--------------

Two mixins in ``openstef_models.explainability.mixins`` add interpretability to
forecasting models.

``ExplainableForecaster``
   Exposes a ``feature_importances`` property returning a ``pd.DataFrame`` of
   importance scores, and a ``plot_feature_importances`` method that produces an
   interactive Plotly treemap grouped by feature category.

``ContributionsMixin``
   Adds ``predict_contributions``, which returns a ``TimeSeriesDataset`` where each
   column is the contribution of one feature to the final prediction for every
   sample. This is useful for debugging unexpected forecast behaviour.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # XGBoostForecaster implements ExplainableForecaster and ContributionsMixin
    model = XGBoostForecaster(hyper_params=XGBoostHyperParams())
    model.fit(train_dataset)

    importances = model.feature_importances  # pd.DataFrame
    fig = model.plot_feature_importances()   # plotly Figure
    fig.show()

.. note:: [VISUALIZATION: Plotly treemap of feature importances grouped by domain (weather, lag, calendar), with colour intensity proportional to importance score]

.. code-block:: python

    contributions = model.predict_contributions(input_dataset)
    # contributions is a TimeSeriesDataset with one column per feature

Not all forecasting models implement both mixins. ``BaseCaseForecaster``, for
example, does not support contribution analysis because it has no learned weights.

---

Putting It Together
-------------------

A typical production setup combines a preset workflow, an MLflow callback, and
explainability in a few lines:

.. code-block:: python

    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )
    from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

    config = ForecastingWorkflowConfig(
        location=LocationConfig(region="nl", substation="rotterdam_south"),
        model_type="lgbm",
        quantiles=[0.05, 0.5, 0.95],
    )

    storage = MLFlowStorage(tracking_uri="http://mlflow.example.com")
    callback = MLFlowStorageCallback(storage=storage, experiment_name="nl_load")

    workflow = create_forecasting_workflow(config)
    workflow.fit(train_dataset, callbacks=[callback])

    forecast = workflow.predict(live_input_dataset)

For large-scale batch execution of these workflows across many locations and time
windows, see :doc:`beam`. For ensemble strategies that combine multiple
``CustomForecastingWorkflow`` instances, see :doc:`meta`.