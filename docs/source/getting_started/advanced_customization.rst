Advanced Customization
======================

This page is for users who are comfortable with the basics of OpenSTEF and want to go beyond the built-in presets. It covers the three main extension points the library exposes: writing custom data transforms, assembling bespoke pipeline configurations, and hooking into the workflow lifecycle with callbacks. If you are still working through your first forecast, start with :doc:`first_forecast` and return here once you are ready.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Overview
--------

OpenSTEF is built around a small number of composable abstractions:

- **Transform / TransformPipeline** — stateful, chainable data transformations that handle everything from validation to feature engineering.
- **ForecastingModel** — a container that wires a preprocessing pipeline, a forecaster, and a postprocessing pipeline together.
- **CustomForecastingWorkflow** — the outermost shell that manages model persistence and fires lifecycle callbacks.

Each layer is independently replaceable. You can swap in a custom transform without touching the forecaster, or attach a callback without modifying any pipeline code.

Custom Data Preparation
-----------------------

The ``Transform`` base class in ``openstef_core`` defines a simple contract: implement ``is_fitted``, ``fit``, and ``transform``. The ``fit_transform`` convenience method is provided for you.

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import Transform

    class PeakClipper(Transform[TimeSeriesDataset, TimeSeriesDataset]):
        """Clip extreme load values to a learned percentile threshold."""

        def __init__(self, upper_quantile: float = 0.99):
            self.upper_quantile = upper_quantile
            self._threshold: float | None = None

        @property
        def is_fitted(self) -> bool:
            return self._threshold is not None

        def fit(self, data: TimeSeriesDataset) -> None:
            self._threshold = float(
                data.data["load"].quantile(self.upper_quantile)
            )

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            clipped = data.data.copy()
            clipped["load"] = clipped["load"].clip(upper=self._threshold)
            return TimeSeriesDataset(clipped, data.sample_interval)

A few conventions to keep in mind:

- ``fit`` learns parameters from training data; ``transform`` applies them. Never learn parameters inside ``transform`` — the same transform instance is called on unseen data at prediction time.
- Return a *new* dataset instance rather than mutating the input. OpenSTEF pipelines assume immutability between steps.
- The type parameter ``Transform[I, O]`` can differ between input and output, which is useful for postprocessing steps that convert a ``TimeSeriesDataset`` into a ``ForecastDataset``.

Custom Feature Engineering
--------------------------

OpenSTEF ships a rich set of built-in feature transforms under ``openstef_models.transforms``, organised into sub-packages:

- ``time_domain`` — ``HolidayFeatureAdder``, ``LagsAdder``, ``DatetimeFeaturesAdder``, ``CyclicFeaturesAdder``
- ``weather_domain`` — ``WindPowerFeatureAdder``, ``AtmosphereDerivedFeaturesAdder``, ``RadiationDerivedFeaturesAdder``
- ``energy_domain`` — energy-specific derived features
- ``general`` — ``Selector``, ``Imputer``, ``NaNDropper``, ``InputConsistencyChecker``
- ``validation`` — ``FlatlineChecker``, ``CompletenessChecker``

Before writing a custom transform, check whether a combination of these covers your need. A typical preprocessing pipeline looks like this:

.. code-block:: python

    from datetime import timedelta
    from pydantic_extra_types.country import CountryAlpha2
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TransformPipeline
    from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
    from openstef_models.transforms.time_domain.lags_adder import LagsAdder
    from openstef_models.transforms.general import Imputer, NaNDropper

    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            LagsAdder(
                history_available=timedelta(days=14),
                horizons=[timedelta(hours=h) for h in range(1, 25)],
                add_trivial_lags=True,
                target_column="load",
            ),
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            Imputer(imputation_strategy="mean"),
            NaNDropper(),
        ]
    )

When you need domain-specific features that the built-ins do not cover, slot your custom transform into the same list:

.. code-block:: python

    from openstef_core.transforms import TransformPipeline
    from openstef_models.transforms.time_domain.lags_adder import LagsAdder
    from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder

    # PeakClipper defined in the previous section
    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            PeakClipper(upper_quantile=0.995),   # custom step first
            LagsAdder(
                history_available=timedelta(days=14),
                horizons=[timedelta(hours=h) for h in range(1, 25)],
                add_trivial_lags=True,
                target_column="load",
            ),
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
        ]
    )

``TransformPipeline`` fits each transform sequentially on the *output* of the previous step, so ordering matters. Validation and cleaning steps should come first; feature-adding steps should follow.

Custom Pipeline Workflows
-------------------------

A ``ForecastingModel`` is the object that owns preprocessing, a forecaster, and postprocessing. You assemble it explicitly when the built-in presets do not match your requirements:

.. code-block:: python

    from openstef_core.datasets import ForecastDataset, TimeSeriesDataset
    from openstef_core.transforms import TransformPipeline
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.transforms.postprocessing import QuantileSorter, ConfidenceIntervalApplicator
    from openstef_models.forecasters.xgboost import XGBoostForecaster
    from openstef_core.types import Q

    quantiles = [Q(0.1), Q(0.5), Q(0.9)]
    horizons = [timedelta(hours=h) for h in range(1, 25)]

    model = ForecastingModel(
        preprocessing=preprocessing,          # TransformPipeline built above
        forecaster=XGBoostForecaster(
            quantiles=quantiles,
            horizons=horizons,
        ),
        postprocessing=TransformPipeline[ForecastDataset](
            transforms=[
                QuantileSorter(),
                ConfidenceIntervalApplicator(
                    quantiles=quantiles,
                    add_quantiles_from_std=False,
                ),
            ]
        ),
        target_column="load",
    )

Once you have a ``ForecastingModel``, wrap it in a ``CustomForecastingWorkflow`` to gain model persistence and callback support:

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

    workflow = CustomForecastingWorkflow(model=model, model_id="my-custom-model")

    # Train
    workflow.fit(data=train_dataset)

    # Predict
    forecasts = workflow.predict(data=forecast_dataset)

Workflow Lifecycle Callbacks
----------------------------

``CustomForecastingWorkflow`` fires four hooks around the fit/predict cycle. Subclass ``ForecastingCallback`` and override only the methods you need — all methods have no-op defaults:

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
        ForecastingCallback,
    )
    from openstef_models.mixins.callbacks import WorkflowContext
    from openstef_core.datasets import ForecastDataset, TimeSeriesDataset, VersionedTimeSeriesDataset
    from openstef_models.models.forecasting_model import ModelFitResult
    import logging

    logger = logging.getLogger(__name__)

    class AuditCallback(ForecastingCallback):
        """Log training and prediction events for audit purposes."""

        def on_fit_start(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            data: VersionedTimeSeriesDataset | TimeSeriesDataset,
        ) -> None:
            logger.info(
                "Training started for model '%s' with %d rows.",
                context.model_id,
                len(data.data),
            )

        def on_fit_end(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            result: ModelFitResult,
        ) -> None:
            logger.info("Training complete. Metrics: %s", result.metrics)

        def on_predict_end(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            data: VersionedTimeSeriesDataset | TimeSeriesDataset,
            result: ForecastDataset,
        ) -> None:
            logger.info(
                "Forecast generated: %d rows, horizon %s to %s.",
                len(result.data),
                result.data.index.min(),
                result.data.index.max(),
            )

Pass one or more callbacks when constructing the workflow:

.. code-block:: python

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my-custom-model",
        callbacks=[AuditCallback()],
    )

Callbacks are a clean way to integrate OpenSTEF into a broader system — writing forecasts to a database, pushing metrics to a monitoring platform, or triggering downstream processes — without coupling that logic to the pipeline itself.

.. note::

   Multiple callbacks can be registered simultaneously. They are executed in list order at each hook point. If a callback raises an exception it will propagate and abort the workflow step, so keep callback logic lightweight and guard against errors where appropriate.

Putting It All Together
-----------------------

The pattern for a fully customised pipeline is always the same three steps:

1. **Build transforms** — write custom ``Transform`` subclasses and/or select from ``openstef_models.transforms``.
2. **Assemble a model** — pass your ``TransformPipeline`` instances and a forecaster to ``ForecastingModel``.
3. **Wrap in a workflow** — attach callbacks and a storage backend via ``CustomForecastingWorkflow``.

Each layer is independently testable. You can unit-test a custom transform by calling ``fit_transform`` directly on a small ``TimeSeriesDataset``, without instantiating a full workflow.

.. note::

   For ensemble models that combine multiple forecasters, OpenSTEF provides ``EnsembleForecastingModel`` with its own preprocessing and combiner configuration. The same transform and callback patterns apply.

Related Pages
-------------

- :doc:`first_forecast` — covers the basics of data loading and running a forecast before customising anything.
- :doc:`quickstart` — minimal working example if you need a quick reference.
- :doc:`backtesting` — how to evaluate your custom pipeline against historical data to validate that your changes improve accuracy.