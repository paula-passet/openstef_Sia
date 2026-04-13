The Models Package
==================

The ``openstef_models`` package is the forecasting engine of OpenSTEF. It sits above ``openstef_core`` in the dependency hierarchy and provides three interlocking layers: a rich library of domain-specific **transforms** for feature engineering, concrete **forecasting model** implementations, and **explainability** tools for interpreting what those models have learned. This page explains how those layers are designed, how they relate to each other, and how you compose them into a working forecasting pipeline.

For the foundational data types (``TimeSeriesDataset``, interfaces, base classes) that this package builds on, see the :doc:`core` sibling page. For backtesting and evaluation tooling, see :doc:`beam`.

.. note:: [DIAGRAM: Component-level diagram showing three horizontal layers stacked vertically. Bottom layer: openstef_core (TimeSeriesDataset, TimeSeriesTransform, TransformPipeline, BaseConfig). Middle layer: openstef_models.transforms (five domain subpackages: validation, general, time_domain, weather_domain, energy_domain). Top layer split into two columns — left: openstef_models.models (XGBoostForecaster, GBLinear, Flatliner) with ExplainableForecaster / ContributionsMixin mixins; right: openstef_models.explainability (FeatureImportancePlotter, plotters). Arrows show upward dependency from core to transforms to models/explainability.]

-----------

The Transforms Layer
--------------------

Every feature engineering step in OpenSTEF is expressed as a ``TimeSeriesTransform`` — a stateful, scikit-learn-style object with ``fit``, ``transform``, and ``fit_transform`` methods that operate on ``TimeSeriesDataset`` instances. The contract is defined in ``openstef_core``; the implementations live in ``openstef_models.transforms``.

The subpackage is divided along domain lines:

- **validation** — data quality guards (``CompletenessChecker``, ``FlatlineChecker``, ``InputConsistencyChecker``)
- **general** — model-agnostic preprocessing (``Imputer``, ``NaNDropper``, ``Clipper``, ``Scaler``, ``Selector``, ``SampleWeighter``, ``EmptyFeatureRemover``)
- **time_domain** — calendar and lag features (``DatetimeFeaturesAdder``, ``CyclicFeaturesAdder``, ``HolidayFeatureAdder``, ``LagsAdder``, ``RollingAggregatesAdder``)
- **weather_domain** — meteorological derived features (``DaylightFeatureAdder``, ``RadiationDerivedFeaturesAdder``, ``AtmosphereDerivedFeaturesAdder``)
- **energy_domain** — power-system physics (``WindPowerFeatureAdder``)

This domain split is a deliberate design choice. A solar-heavy grid and a wind-heavy grid need different feature sets; by selecting subsets of transforms, you build a pipeline that matches the physics of the site you are forecasting.

Composing a Pipeline
^^^^^^^^^^^^^^^^^^^^

Transforms are assembled into a ``TransformPipeline`` from ``openstef_core``. The pipeline fits and transforms sequentially — each step receives the output of the previous one — so ordering matters.

.. code-block:: python

    from openstef_core.mixins import TransformPipeline
    from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker
    from openstef_models.transforms.general import Imputer, NaNDropper, Scaler
    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
        LagsAdder,
        HolidayFeatureAdder,
    )
    from openstef_models.transforms.weather_domain import (
        DaylightFeatureAdder,
        RadiationDerivedFeaturesAdder,
    )

    preprocessing = TransformPipeline(
        transforms=[
            # 1. Validate before touching the data
            CompletenessChecker(),
            FlatlineChecker(),
            # 2. Repair missing values
            Imputer(),
            NaNDropper(),
            # 3. Enrich with features
            DatetimeFeaturesAdder(),
            CyclicFeaturesAdder(),
            HolidayFeatureAdder(country="NL"),
            DaylightFeatureAdder(),
            RadiationDerivedFeaturesAdder(),
            LagsAdder(lags=[1, 2, 3, 48]),   # 15-min resolution: 1-hour and 12-hour lags
            # 4. Scale for gradient-based models
            Scaler(),
        ]
    )

    # Fit on training data, then reuse the fitted state for inference
    preprocessing.fit(train_dataset)
    enriched_train = preprocessing.transform(train_dataset)
    enriched_forecast = preprocessing.transform(forecast_dataset)

Because every transform is a ``BaseConfig`` subclass (Pydantic-backed), the entire pipeline can be serialised to JSON and reloaded — a property that the presets and MLflow integration exploit for reproducible experiments.

Energy-Domain Transforms
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``energy_domain`` subpackage contains transforms that encode physical knowledge. ``WindPowerFeatureAdder`` is a good example: it derives wind power output from raw wind speed measurements using a power curve model, adding the computed column to the dataset and advertising which columns it added via ``features_added()``.

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    wind_transform = WindPowerFeatureAdder()
    enriched = wind_transform.fit_transform(dataset)
    print(wind_transform.features_added())
    # ['wind_power']

This pattern — a transform that knows its own output schema — allows downstream steps (such as ``Selector``) to operate on named feature sets without hard-coding column names.

-----------

The Models Layer
----------------

``openstef_models.models`` provides concrete forecasting implementations. All models follow the ``ForecastingModel`` interface from ``openstef_core``, which standardises ``fit``, ``predict``, and (optionally) probabilistic output. The current built-in implementations include:

- **XGBoostForecaster** — gradient boosted trees with multi-quantile output, the workhorse for most energy forecasting tasks
- **GBLinear** — a gradient boosted linear model, useful when interpretability or linear extrapolation is preferred
- **Flatliner** — a persistence/baseline model that predicts a constant, used as a sanity-check benchmark

Models and transforms are deliberately separate. A model does not own its preprocessing; the caller assembles the pipeline and passes enriched data to the model. This separation means you can swap the model without touching the feature engineering, or swap the feature engineering without retraining the model architecture.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )
    from openstef_core.types import Q

    hyperparams = XGBoostHyperParams(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
    )

    model = XGBoostForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        hyperparams=hyperparams,
    )

    model.fit(enriched_train)
    forecast = model.predict(enriched_forecast)

The ``quantiles`` argument drives probabilistic forecasting: the model trains a separate estimator per quantile and returns a ``TimeSeriesDataset`` with one column per quantile. Downstream, ``ConfidenceIntervalApplicator`` and ``QuantileSorter`` (in ``transforms.postprocessing``) clean up the output before it reaches consumers.

-----------

Explainability
--------------

Understanding *why* a model made a particular forecast is as important as the forecast itself. ``openstef_models.explainability`` provides two complementary mechanisms, both implemented as mixins so they can be attached to any compatible forecasting model.

``ExplainableForecaster``
^^^^^^^^^^^^^^^^^^^^^^^^^

Any model that mixes in ``ExplainableForecaster`` exposes a ``feature_importances`` property returning a ``pd.DataFrame`` indexed by feature name with quantile columns. The companion ``plot_feature_importances`` method builds an interactive Plotly treemap — no external visualisation library required.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

    model = XGBoostForecaster(quantiles=[Q(0.1), Q(0.5), Q(0.9)])
    model.fit(enriched_train)

    # Tabular importance scores
    importances = model.feature_importances
    print(importances.head())

    # Interactive treemap (returns a plotly Figure — display in Jupyter or save to HTML)
    fig = model.plot_feature_importances(quantile=Q(0.5))
    fig.show()

The treemap groups features by their domain prefix (e.g. ``lag_*``, ``radiation_*``, ``holiday_*``), giving an immediate visual summary of which feature families drive the model.

``ContributionsMixin``
^^^^^^^^^^^^^^^^^^^^^^

For per-sample attribution — answering "why did the model predict this value at this timestamp?" — models that implement ``ContributionsMixin`` expose ``predict_contributions``:

.. code-block:: python

    contributions = model.predict_contributions(forecast_input_dataset)
    # Returns a TimeSeriesDataset where each column is a feature's additive
    # contribution to the prediction at that timestep.

This is particularly useful for debugging anomalous forecasts: you can inspect which features pushed the prediction high or low at a specific moment.

The ``FeatureImportancePlotter`` class in ``openstef_models.explainability.plotters`` is the underlying engine for the treemap visualisation. You can instantiate it directly if you want to plot importance scores that come from a source other than a built-in model:

.. code-block:: python

    from openstef_models.explainability.plotters import FeatureImportancePlotter

    plotter = FeatureImportancePlotter()
    fig = plotter.plot(scores=my_importance_dataframe, quantile=Q(0.5))

-----------

Presets: Putting It Together
-----------------------------

For common use cases, ``openstef_models.presets`` ships ready-made workflow configurations that wire transforms, models, data splitters, and evaluation metrics into a single ``LocationConfig``. These presets are the fastest path from raw data to a working forecast, and they serve as authoritative examples of the compositional patterns described above.

.. code-block:: python

    from openstef_models.presets.forecasting_workflow import LocationConfig

    config = LocationConfig(
        location_id="substation_42",
        country="NL",
        coordinate=(52.37, 4.90),
    )
    # config bundles a TransformPipeline, an XGBoostForecaster,
    # a DataSplitter, and metric providers — ready to hand to a workflow runner.

Presets are not magic: they are ordinary Python objects assembled from the same public classes described on this page. Reading the preset source code is a good way to understand the intended composition patterns before building a custom pipeline.

.. note::

   If the built-in presets do not match your use case, copy the relevant preset as a starting point and replace individual transforms or the model. Because every component is independently configurable, you rarely need to modify the library itself.

-----------

Design Principles
-----------------

A few patterns recur throughout ``openstef_models`` and are worth making explicit:

- **Transforms own their state.** A ``Clipper`` fitted on training data remembers the observed min/max values and applies them at inference time. This prevents data leakage and makes serialisation straightforward.
- **Models are stateless with respect to preprocessing.** The model receives an already-enriched ``TimeSeriesDataset``; it does not call transforms internally. This keeps the model–transform boundary clean.
- **Explainability is opt-in via mixins.** Not every model needs SHAP-style attribution. By expressing explainability as mixins (``ExplainableForecaster``, ``ContributionsMixin``), the library avoids forcing all models to carry the overhead.
- **Pydantic configuration throughout.** Every configurable object (transforms, models, hyperparameters) is a ``BaseConfig`` subclass. This gives you free validation, serialisation, and IDE autocompletion.