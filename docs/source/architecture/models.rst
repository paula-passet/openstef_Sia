The openstef_models Package
===========================

This page covers the ``openstef_models`` package — the central hub for feature engineering,
forecasting models, component splitting, workflow presets, integrations, and explainability
in OpenSTEF. It depends on ``openstef-core`` for validated dataset types and base classes,
and its workflows are executed at scale by ``openstef-beam`` (see the :doc:`beam` page).

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

Transforms
----------

Transforms are scikit-learn-compatible pipeline steps that prepare a
``TimeSeriesDataset`` for training or inference. They are organised into two
sub-packages.

**General transforms** handle concerns that apply to any time-series problem:

- ``Imputer`` — fills missing values using configurable strategies
- ``OutlierHandler`` — detects and clips or removes anomalous samples
- ``Scaler`` — normalises features before passing them to gradient-boosted models
- ``Shifter`` — creates time-shifted copies of columns (lag features)
- ``EmptyFeatureRemover`` — drops columns that carry no information after imputation
- ``SampleWeighter`` / ``SampleWeightConfig`` — assigns per-sample training weights

**Energy-domain transforms** encode physical knowledge about the power system:

- ``WindPowerFeatureAdder`` — derives wind-power proxy features from meteorological inputs

Domain transforms are intentionally thin: they add columns to the dataset rather than
replacing it, so they compose cleanly with general transforms in a pipeline.

.. code-block:: python

    from openstef_models.transforms.general import Imputer, OutlierHandler, Shifter
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from sklearn.pipeline import Pipeline

    feature_pipeline = Pipeline([
        ("impute",   Imputer()),
        ("outliers", OutlierHandler()),
        ("wind",     WindPowerFeatureAdder()),
        ("lags",     Shifter(shifts=[1, 2, 3, 24, 48])),
    ])

    prepared = feature_pipeline.fit_transform(train_dataset)


Forecasting Models
------------------

All forecasting models implement the ``Forecaster`` base class and produce
probabilistic (multi-quantile) outputs over a ``ForecastInputDataset``.

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Class
     - Backend
     - Notes
   * - ``XGBoostForecaster``
     - XGBoost
     - Gradient-boosted trees; default choice for most load-forecasting tasks
   * - ``LGBMForecaster``
     - LightGBM
     - Faster training on large datasets; comparable accuracy to XGBoost
   * - ``GBLinearForecaster``
     - XGBoost (linear booster)
     - Regularised linear model inside the XGBoost framework
   * - ``LGBMLinearForecaster``
     - LightGBM (linear booster)
     - LightGBM variant with a linear booster
   * - ``BaseCaseForecaster``
     - Statistical
     - Lag-based baseline; useful as a sanity-check benchmark

Each model ships with a typed ``HyperParams`` dataclass (e.g. ``XGBoostHyperParams``,
``LGBMHyperParams``) that validates configuration at construction time via Pydantic.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    params = XGBoostHyperParams(n_estimators=500, learning_rate=0.05)
    model = XGBoostForecaster(hyperparams=params)
    model.fit(train_dataset)

    forecast = model.predict(input_dataset)   # returns ForecastDataset


Component Splitting
-------------------

Energy load can be decomposed into physical components (e.g. base load, wind
generation, solar generation). ``ComponentSplittingModel`` orchestrates this
decomposition as a self-contained pipeline:

.. code-block:: python

    from openstef_models.models.component_splitting_model import ComponentSplittingModel

    splitter = ComponentSplittingModel(config=splitter_config)
    splitter.fit(train_dataset)

    components = splitter.predict(input_dataset)
    # components is an EnergyComponentDataset with one column per component

Internally the model chains preprocessing transforms, a ``LinearComponentSplitter``
(which has no ``fit`` step — the split coefficients are derived analytically), and
postprocessing. The high-level ``ComponentSplittingModel`` exposes the same
``fit`` / ``predict`` interface as the forecasting models, so it slots into the
same workflow machinery.

The full production workflow is ``CustomComponentSplitWorkflow``, which adds
callback hooks and optional persistence around the model:

.. code-block:: python

    from openstef_models.workflows.custom_component_split_workflow import (
        CustomComponentSplitWorkflow,
        ComponentSplitCallback,
    )

    class LoggingCallback(ComponentSplitCallback):
        def on_predict_end(self, workflow, result):
            print(f"Split complete, components: {list(result.columns)}")

    workflow = CustomComponentSplitWorkflow(
        model=splitter,
        callbacks=[LoggingCallback()],
    )
    components = workflow.predict(input_dataset)


Presets and Workflows
---------------------

Presets are opinionated factory functions that wire together transforms, a
forecasting model, and a workflow from a single configuration object — the
recommended starting point for new deployments.

.. code-block:: python

    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )

    config = ForecastingWorkflowConfig(
        location=LocationConfig(name="Amsterdam", region="NL"),
        model_type="xgboost",
        horizon_hours=48,
    )

    workflow = create_forecasting_workflow(config)
    workflow.fit(train_dataset)
    forecast = workflow.predict(input_dataset)

``create_forecasting_workflow`` returns a ``CustomForecastingWorkflow`` instance.
The workflow exposes the same ``fit`` / ``predict`` surface as the underlying model
but adds callback hooks at every lifecycle stage (fit start/end, predict start/end,
error). This is the extension point for logging, alerting, and persistence — see
the Integrations section below.

.. note::

   ``openstef-beam`` uses these workflows as the unit of work inside its distributed
   pipelines. See the :doc:`beam` page for how ``CustomForecastingWorkflow`` is
   executed across many locations in parallel.


Integrations
------------

MLflow
^^^^^^

The ``openstef_models.integrations.mlflow`` sub-package provides two classes:

- ``MLFlowStorage`` — a ``ModelSerializer`` implementation that saves and loads
  models from an MLflow model registry.
- ``MLFlowStorageCallback`` — a ``PredictorCallback`` that calls ``MLFlowStorage``
  automatically at the end of a training run.

.. code-block:: python

    from openstef_models.integrations.mlflow import (
        MLFlowStorage,
        MLFlowStorageCallback,
    )
    from openstef_models.mixins import ModelIdentifier

    storage = MLFlowStorage(tracking_uri="http://mlflow.example.com")
    identifier = ModelIdentifier(name="load-forecast-amsterdam", version="latest")

    # Attach to a workflow so every successful fit is persisted automatically
    workflow = create_forecasting_workflow(config)
    workflow.add_callback(MLFlowStorageCallback(storage=storage, identifier=identifier))

    workflow.fit(train_dataset)   # model is logged to MLflow on completion

.. note::

   MLflow is an optional dependency. Install it with
   ``pip install openstef-models[mlflow]``.


Mixins
------

Three mixins in ``openstef_models.mixins`` provide reusable behaviour across
models and workflows:

- **``ModelIdentifier``** — a lightweight value object (name + version) that
  uniquely addresses a model in a registry. Used by ``MLFlowStorage`` and any
  custom storage backend.
- **``ModelSerializer``** — abstract interface for save/load operations.
  Implement this to plug in a custom storage backend (e.g. Azure Blob, GCS).
- **``PredictorCallback``** — generic callback protocol parameterised over the
  workflow type, input type, fit result type, and predict result type. Subclass
  it to hook into any stage of a workflow's lifecycle without modifying the
  workflow itself.

.. code-block:: python

    from openstef_models.mixins import PredictorCallback

    class MetricsCallback(PredictorCallback):
        def on_fit_end(self, workflow, result):
            # push training metrics to your observability stack
            ...

        def on_predict_end(self, workflow, result):
            # record prediction latency or output statistics
            ...


Explainability
--------------

Two mixins in ``openstef_models.explainability.mixins`` add interpretability to
any forecasting model that implements them:

- **``ExplainableForecaster``** — exposes a ``feature_importances`` property
  (returns a ``pd.DataFrame``) and a ``plot_feature_importances`` method that
  produces an interactive Plotly treemap.
- **``ContributionsMixin``** — adds ``predict_contributions``, which returns a
  ``TimeSeriesDataset`` of per-sample feature contributions (SHAP-style).

``XGBoostForecaster`` and ``LGBMForecaster`` both implement both mixins.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

    model = XGBoostForecaster()
    model.fit(train_dataset)

    # Tabular feature importances
    importances = model.feature_importances   # pd.DataFrame

    # Interactive treemap (returns plotly Figure)
    fig = model.plot_feature_importances()
    fig.show()

    # Per-sample contributions
    contributions = model.predict_contributions(input_dataset)

.. note:: [VISUALIZATION: Plotly treemap of feature importances grouped by domain (weather, lag, calendar), with colour intensity proportional to importance score.]

Feature contributions are particularly useful for debugging unexpected forecasts:
compare the contribution columns against the raw feature values to identify which
input drove an anomalous prediction.


Related Pages
-------------

- :doc:`core` — ``TimeSeriesDataset``, ``EnergyComponentDataset``, and the
  ``BaseModel`` contract that all models in this package implement.
- :doc:`beam` — distributed execution of ``CustomForecastingWorkflow`` across
  many locations using Apache Beam.
- :doc:`meta` — ``EnsembleForecastingModel`` and forecast combiners that wrap
  the models described here.