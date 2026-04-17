Models
======

This page covers the ``openstef_models`` package — the model layer of OpenSTEF. It describes how feature transforms are organised by domain, which forecasting and component-splitting models are available, how presets and workflows compose everything together, and how integrations (MLflow), mixins, and explainability fit into the picture.

For the validated dataset hierarchy that all models consume, see :doc:`core`. For the Beam-based batch pipelines that run these models at scale, see :doc:`beam`. For ensemble models built on top of ``openstef_models``, see :doc:`meta`.

.. note:: [DIAGRAM: Module map showing transforms (energy_domain, temporal, and other domain sub-packages) feeding into two model families (forecasting models and component-splitting models). Presets/workflows sit as top-level orchestration above both families. Integrations (MLflow, Joblib) hang off the side as persistence/tracking backends. Mixins (ModelSerializer, PredictorCallback) and explainability (ExplainableForecaster, ContributionsMixin) are cross-cutting concerns attached to the model classes.]

Package layout
--------------

``openstef_models`` is structured around four concerns:

- **Transforms** — stateless and stateful feature-engineering steps, grouped by domain.
- **Models** — forecasting estimators and component-splitting models that consume transformed data.
- **Presets & workflows** — high-level configuration objects that wire transforms and models into a ready-to-run pipeline.
- **Integrations, mixins, and explainability** — cross-cutting utilities for persistence, callbacks, and interpretability.

All data flowing through the package is expressed in the ``openstef_core`` dataset types (``TimeSeriesDataset``, ``ForecastInputDataset``, ``ForecastDataset``). The package depends on ``openstef-core`` for those types and on ``openstef-beam`` when transforms or models are embedded inside distributed pipelines.

Transforms
----------

Transforms live under ``openstef_models.transforms`` and are grouped into domain sub-packages. This grouping keeps energy-specific logic separate from generic time-series logic and makes it straightforward to add new domains without touching existing code.

Energy domain
^^^^^^^^^^^^^

``openstef_models.transforms.energy_domain`` contains transforms that encode knowledge specific to power-grid forecasting: solar irradiance features, wind-speed normalisation, electricity-price lags, and rolling aggregate statistics over load measurements. These transforms expect column names that match the ``ForecastInputDataset`` schema defined in ``openstef_core``.

Temporal domain
^^^^^^^^^^^^^^^

Temporal transforms encode calendar and clock information — hour-of-day, day-of-week, month, public-holiday flags, and forecast-horizon offsets. Because these features are derived purely from the timestamp index they are cheap to compute and are almost always included.

Other domains
^^^^^^^^^^^^^

Additional sub-packages (e.g. meteorological post-processing, market-price features) follow the same pattern: a sub-package under ``transforms/`` with its own ``__init__.py`` that re-exports the public transform classes.

Transforms are ordinary Python callables that accept and return ``TimeSeriesDataset`` objects, so they compose naturally with ``openstef_beam`` transform steps and with scikit-learn-style pipelines.

Forecasting models
------------------

Forecasting models live under ``openstef_models.models.forecasting``. All of them implement the ``Forecaster`` base class, which in turn satisfies the ``openstef_core`` predictor protocol. The current catalogue includes:

**Gradient-boosted tree models**

- ``XGBoostForecaster`` — XGBoost trees; handles complex non-linear load patterns well.
- ``LGBMForecaster`` — LightGBM trees; typically faster to train than XGBoost on large datasets.
- ``LGBMLinearForecaster`` — LightGBM with linear leaves; better extrapolation outside the training distribution, useful for novel grid conditions.

**Baseline / reference models**

- ``FlatlinerForecaster`` — predicts a constant value; used as a sanity-check baseline in benchmarks.

All forecasting models produce **probabilistic outputs**: they return a ``ForecastDataset`` containing one column per requested quantile (e.g. ``q0.1``, ``q0.5``, ``q0.9``). Quantiles are configured at workflow level and passed through to the underlying multi-quantile regressor.

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_core.datasets import ForecastInputDataset

   model = LGBMForecaster()
   model.fit(train_dataset)
   forecast: ForecastDataset = model.predict(input_dataset)
   # forecast contains columns q0.1, q0.5, q0.9 (or whichever quantiles were set)

Component splitting
-------------------

Component-splitting models decompose a total load signal into interpretable sub-components — for example, separating base load from solar back-feed or wind generation. They live under ``openstef_models.models.component_splitting`` and share the same ``Forecaster`` interface, so they can be slotted into any workflow that expects a standard predictor.

Component splitting is particularly valuable when downstream consumers need to reason about individual generation or consumption sources rather than the net grid load.

Presets and workflows
---------------------

The presets layer is the recommended entry point for most users. Rather than assembling transforms and models by hand, you describe what you want in a ``ForecastingWorkflowConfig`` and call ``create_forecasting_workflow``.

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model="lgbm",
       horizons=[1, 4, 24, 48],          # forecast horizons in hours
       quantiles=[0.1, 0.5, 0.9],
       # weather feature column mappings
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       # optional: electricity price feature
       energy_price_column="EPEX_NL",
       rolling_aggregate_features=["mean", "median", "max", "min"],
       mlflow_storage=None,               # set to an MLFlowStorage instance to enable tracking
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)
   forecast = workflow.predict(input_dataset)

``ForecastingWorkflowConfig`` is a Pydantic ``BaseConfig`` (from ``openstef_core``), so all fields are validated at construction time and the config can be serialised to JSON for reproducibility.

``LocationConfig`` is a companion config that attaches geographic metadata (substation name, region, coordinates) to a workflow. Its ``tags`` property returns a ``dict[str, str]`` suitable for passing directly to MLflow as run tags.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import LocationConfig

   location = LocationConfig(name="Amsterdam_Noord", region="Noord-Holland", lat=52.4, lon=4.9)
   print(location.tags)
   # {'location.name': 'Amsterdam_Noord', 'location.region': 'Noord-Holland', ...}

Integrations
------------

MLflow
^^^^^^

``openstef_models.integrations.mlflow`` provides two classes:

- ``MLFlowStorage`` — a storage backend that serialises trained models, logs metrics and hyperparameters, and manages the MLflow experiment/run lifecycle. It normalises local file paths to ``file:///`` URIs automatically.
- ``MLFlowStorageCallback`` — a ``PredictorCallback`` (see Mixins below) that triggers ``MLFlowStorage`` operations at the right points in the training loop, so you do not need to call storage methods manually.

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

   storage = MLFlowStorage(tracking_uri="http://mlflow.internal:5000")
   callback = MLFlowStorageCallback(storage=storage)

   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model="lgbm",
       horizons=[1, 24],
       quantiles=[0.1, 0.5, 0.9],
       mlflow_storage=storage,
   )
   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)   # model is logged to MLflow automatically

.. note::

   MLflow is an optional dependency. Install it with ``pip install openstef-models[mlflow]``. If MLflow is not installed and you pass an ``MLFlowStorage`` instance, an ``MissingExtraError`` is raised at runtime.

Joblib
^^^^^^

``openstef_models.integrations.joblib`` provides ``JoblibModelSerializer``, a lightweight serialiser used by ``MLFlowStorage`` internally to pickle model objects. You rarely need to use it directly.

Mixins
------

``openstef_models.mixins`` provides building blocks for model management:

- ``ModelSerializer`` — abstract interface for saving and loading a fitted model. Concrete implementations (``JoblibModelSerializer``, ``MLFlowStorage``) implement this interface.
- ``ModelIdentifier`` — a value object that uniquely identifies a model by ``model_id`` and optional version metadata. Used as a key when retrieving models from a registry.
- ``PredictorCallback`` — an abstract callback interface with hooks called before and after fit/predict. ``MLFlowStorageCallback`` is the main concrete implementation, but you can write custom callbacks for monitoring, alerting, or custom serialisation.

.. code-block:: python

   from openstef_models.mixins import PredictorCallback, ModelIdentifier

   class MetricsCallback(PredictorCallback):
       def on_fit_end(self, model, dataset, metrics):
           print(f"Training MAE: {metrics['mae']:.4f}")

Explainability
--------------

``openstef_models.explainability`` provides two mixins that forecasting models can implement:

``ExplainableForecaster``
^^^^^^^^^^^^^^^^^^^^^^^^^

Adds a ``feature_importances`` property (returns a ``pd.DataFrame``) and a ``plot_feature_importances`` method (returns a Plotly ``go.Figure`` treemap). All gradient-boosted tree models in ``openstef_models`` implement this mixin.

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)

   importances = workflow.model.feature_importances   # pd.DataFrame
   fig = workflow.model.plot_feature_importances()    # interactive Plotly treemap
   fig.show()

.. note:: [VISUALIZATION: Plotly treemap showing feature importance scores grouped by domain (energy, temporal, weather), with tile size proportional to importance and colour indicating the quantile for which importance was computed.]

``ContributionsMixin``
^^^^^^^^^^^^^^^^^^^^^^

Adds ``predict_contributions``, which returns a ``TimeSeriesDataset`` where each column is the contribution of one feature to the final prediction for each sample. This is useful for debugging unexpected forecast behaviour on specific time windows.

.. code-block:: python

   contributions: TimeSeriesDataset = workflow.model.predict_contributions(input_dataset)
   # contributions.columns == model.feature_names_in_

.. note::

   ``predict_contributions`` can be computationally expensive for large datasets. Consider running it on a representative subset when exploring model behaviour interactively.

Patterns and relationships
--------------------------

A few design patterns are worth noting:

**Transforms are domain-pure.** Energy-domain transforms know nothing about model internals; they only manipulate ``TimeSeriesDataset`` columns. This means the same transform can be reused in a Beam pipeline (see :doc:`beam`) or in a local workflow without modification.

**Models are quantile-native.** Rather than training a separate model per quantile, ``openstef_models`` uses a ``MultiQuantileRegressor`` wrapper internally. All quantiles are produced in a single ``predict`` call, which keeps inference latency low.

**Presets encode best practices.** ``ForecastingWorkflowConfig`` captures the column-mapping conventions, rolling-feature choices, and model defaults that have been validated on real grid data. Using presets means you inherit those defaults; you can still override any field for custom use cases.

**Callbacks decouple side effects.** Storage, logging, and monitoring are all expressed as ``PredictorCallback`` implementations. The core training loop in ``Forecaster`` never imports MLflow directly — it just calls registered callbacks at defined hook points.

**Explainability is opt-in via mixins.** Not every model needs to support ``predict_contributions`` (it requires SHAP or equivalent). The mixin pattern lets models advertise their capabilities through the type system without forcing a common implementation on all estimators.