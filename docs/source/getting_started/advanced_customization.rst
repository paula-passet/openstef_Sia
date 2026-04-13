Advanced Customization
======================

This page covers the main extension points available to power users of the OpenSTEF library: writing custom data transforms, assembling bespoke preprocessing and postprocessing pipelines, and hooking into the workflow lifecycle with callbacks. If you are still working through the basics, read :doc:`first_forecast` first and return here when the built-in defaults no longer meet your needs.

.. note:: [DIAGRAM: Three-layer architecture — TransformPipeline (preprocessing) → Forecaster → TransformPipeline (postprocessing) — with callback hooks shown at fit_start, fit_end, predict_start, predict_end]

Custom Feature Engineering with ``TimeSeriesTransform``
--------------------------------------------------------

Every preprocessing and postprocessing step in OpenSTEF is a ``TimeSeriesTransform``. The abstract base class lives in ``openstef_core`` and requires you to implement exactly one method — ``transform`` — while ``fit`` and ``is_fitted`` have sensible defaults for stateless transforms.

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.base import TimeSeriesTransform


    class PeakHourFlagTransform(TimeSeriesTransform):
        """Adds a binary column that flags morning and evening peak hours."""

        def features_added(self) -> list[str]:
            return ["is_peak_hour"]

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            df = data.data.copy()
            hour = df.index.hour
            df["is_peak_hour"] = ((hour >= 7) & (hour <= 9) | (hour >= 17) & (hour <= 19)).astype(float)
            return TimeSeriesDataset(df, data.sample_interval)

The ``features_added`` method is used by the pipeline for introspection and logging — always implement it, even if it returns an empty list.

For transforms that need to *learn* parameters from training data (e.g. computing a scaling factor), override ``fit`` and track fitted state via ``is_fitted``:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.base import TimeSeriesTransform


    class LoadNormalizer(TimeSeriesTransform):
        """Normalises the load column by the 99th-percentile observed during training."""

        def __init__(self):
            self._scale: float | None = None

        @property
        def is_fitted(self) -> bool:
            return self._scale is not None

        def features_added(self) -> list[str]:
            return []

        def fit(self, data: TimeSeriesDataset) -> None:
            self._scale = float(data.data["load"].quantile(0.99))

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            if not self.is_fitted:
                raise RuntimeError("Call fit before transform.")
            df = data.data.copy()
            df["load"] = df["load"] / self._scale
            return TimeSeriesDataset(df, data.sample_interval)

.. note::

   ``fit_transform`` is provided for free by the base class: it calls ``fit`` only when ``is_fitted`` is ``False``, then delegates to ``transform``. You do not need to override it.

Assembling a ``TransformPipeline``
-----------------------------------

Individual transforms become useful when composed into a ``TransformPipeline``. The pipeline applies each transform in sequence, passing the output of one as the input to the next. Fitting is incremental: each transform is fitted on the data as it emerges from the previous step.

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.pipeline import TransformPipeline
    from openstef_models.transforms.general.clipper import Clipper

    # Mix built-in and custom transforms freely
    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            LoadNormalizer(),
            PeakHourFlagTransform(),
            Clipper(features=["load"], quantile=0.001),
        ]
    )

    # During training
    processed_train = preprocessing.fit_transform(train_dataset)

    # During inference — uses the parameters learned during fit
    processed_inference = preprocessing.transform(inference_dataset)

An empty pipeline (``transforms=[]``) is a valid no-op, which is the default when you construct a ``ForecastingModel`` without specifying preprocessing or postprocessing.

Building a Custom Forecasting Workflow
---------------------------------------

The ``ForecastingModel`` class is the central composition point. It wires together a preprocessing pipeline, a forecaster, and a postprocessing pipeline under a single ``fit`` / ``predict`` interface:

.. code-block:: python

    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.transforms.pipeline import TransformPipeline
    from openstef_models.transforms.energy_domain.wind_power_feature_adder import WindPowerFeatureAdder
    from openstef_models.transforms.general.clipper import Clipper
    from openstef_core.datasets import TimeSeriesDataset, EnergyComponentDataset

    model = ForecastingModel(
        preprocessing=TransformPipeline[TimeSeriesDataset](
            transforms=[
                WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
                PeakHourFlagTransform(),
            ]
        ),
        forecaster=my_forecaster,          # any object implementing the Forecaster protocol
        postprocessing=TransformPipeline[TimeSeriesDataset](
            transforms=[
                Clipper(features=["forecast"], quantile=0.001),
            ]
        ),
        target_column="load",
    )

    model.fit(train_dataset)
    forecasts = model.predict(inference_dataset)

Wrap the ``ForecastingModel`` in a ``CustomForecastingWorkflow`` when you need persistence, MLflow tracking, or lifecycle callbacks:

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my-custom-wind-model",
        run_name="experiment-v1",
        callbacks=[],          # see the next section
    )

    workflow.fit(versioned_train_dataset)
    result = workflow.predict(versioned_inference_dataset)

Extending Behaviour with Callbacks
------------------------------------

Callbacks let you inject logic at four points in the workflow lifecycle without subclassing or modifying the core workflow. Subclass ``ForecastingCallback`` and override only the hooks you need — all methods have no-op defaults.

.. code-block:: python

    from openstef_models.workflows.forecasting_callback import ForecastingCallback
    from openstef_models.mixins.callbacks import WorkflowContext
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_core.datasets.validated_datasets import ForecastDataset
    from openstef_models.models.forecasting_model import ModelFitResult
    import logging

    logger = logging.getLogger(__name__)


    class AuditCallback(ForecastingCallback):
        """Logs training and prediction events for auditing purposes."""

        def on_fit_start(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            data,
        ) -> None:
            logger.info(
                "Training started",
                extra={"model_id": context.workflow.model_id, "rows": len(data.data)},
            )

        def on_fit_end(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            result: ModelFitResult,
        ) -> None:
            logger.info("Training complete", extra={"metrics": result.metrics})

        def on_predict_end(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            data,
            result: ForecastDataset,
        ) -> None:
            logger.info(
                "Forecast generated",
                extra={"forecast_rows": len(result.data)},
            )


    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="my-custom-wind-model",
        callbacks=[AuditCallback()],
    )

The four available hooks are:

- ``on_fit_start`` — before training begins; useful for input validation or setup.
- ``on_fit_end`` — after training completes; useful for saving metrics or triggering downstream jobs.
- ``on_predict_start`` — before prediction; useful for validating inference inputs.
- ``on_predict_end`` — after prediction; useful for saving forecasts or alerting on anomalies.

You can pass multiple callbacks as a list; they are executed in order.

.. note::

   OpenSTEF ships a ``DataSaveCallback`` (``openstef_models.workflows.callbacks.data_save``) that persists intermediate datasets to Parquet files. Use it during development to inspect what data looks like at each pipeline stage before writing your own transforms.

Putting It All Together
------------------------

A complete custom workflow typically follows this pattern:

1. **Define transforms** — subclass ``TimeSeriesTransform`` for any domain-specific feature engineering not covered by the built-in transforms in ``openstef_models.transforms``.
2. **Compose pipelines** — assemble ``TransformPipeline`` instances for preprocessing and postprocessing, mixing your custom transforms with built-ins like ``Clipper``, ``WindPowerFeatureAdder``, or ``LagsAdder``.
3. **Build the model** — pass the pipelines and a forecaster to ``ForecastingModel``.
4. **Wrap in a workflow** — use ``CustomForecastingWorkflow`` for production use, attaching callbacks for observability and persistence.

.. code-block:: python

    from openstef_models.transforms.pipeline import TransformPipeline
    from openstef_models.transforms.energy_domain.wind_power_feature_adder import WindPowerFeatureAdder
    from openstef_models.transforms.general.clipper import Clipper
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback
    from openstef_core.datasets import TimeSeriesDataset

    preprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[
            WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
            PeakHourFlagTransform(),   # custom transform defined earlier
            LoadNormalizer(),           # custom transform defined earlier
        ]
    )

    postprocessing = TransformPipeline[TimeSeriesDataset](
        transforms=[Clipper(features=["forecast"], quantile=0.001)]
    )

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=my_forecaster,
        postprocessing=postprocessing,
        target_column="load",
    )

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="wind-site-alpha",
        callbacks=[
            DataSaveCallback(output_dir="/tmp/pipeline-debug"),
            AuditCallback(),
        ],
    )

    workflow.fit(train_dataset)
    forecasts = workflow.predict(inference_dataset)

Next Steps
----------

- :doc:`backtesting` — once your custom pipeline is built, use backtesting to compare it objectively against the default configuration.
- :doc:`first_forecast` — revisit the step-by-step tutorial if you need a refresher on how training data is structured and how ``TimeSeriesDataset`` is constructed.