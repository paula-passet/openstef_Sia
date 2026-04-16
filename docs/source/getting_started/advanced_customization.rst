Advanced Customization
======================

This page is for users who are comfortable with the basics of OpenSTEF and want to go beyond the defaults. It covers the three main extension points the library provides: building custom data preparation transforms, composing custom pipeline workflows, and writing your own feature engineering. If you are still working through your first forecast, start with :doc:`first_forecast` before continuing here.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Overview
--------

OpenSTEF is designed around a layered composition model. At the lowest level, individual ``Transform`` subclasses encapsulate a single data operation. These are assembled into ``TransformPipeline`` objects that handle preprocessing and postprocessing. A ``ForecastingModel`` then wraps a pipeline together with a forecaster, and a ``CustomForecastingWorkflow`` adds lifecycle management on top. You can replace or extend any of these layers without touching the others.

The three patterns covered here are:

- **Custom transforms** — implement ``TimeSeriesTransform`` to add your own feature engineering or data cleaning step.
- **Custom pipelines** — compose built-in and custom transforms into a ``TransformPipeline`` and wire it into a ``ForecastingModel``.
- **Custom workflow callbacks** — hook into the training and prediction lifecycle via ``ForecastingCallback`` without subclassing the workflow itself.

Custom Feature Engineering
--------------------------

All feature engineering in OpenSTEF is expressed as a ``TimeSeriesTransform``. The interface follows the familiar scikit-learn fit/transform pattern, but operates on ``TimeSeriesDataset`` objects rather than raw arrays. Stateless transforms (those that do not learn parameters from data) only need to implement ``transform``; stateful transforms should also implement ``fit``.

The abstract base class lives in ``openstef_core.transforms``:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform


    class PeakHourIndicator(TimeSeriesTransform):
        """Adds a binary column that is 1 during morning and evening peak hours."""

        def features_added(self) -> list[str]:
            return ["is_peak_hour"]

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            index = data.data.index
            hour = index.hour
            peak_mask = ((hour >= 7) & (hour <= 9)) | ((hour >= 17) & (hour <= 19))
            new_data = data.data.copy()
            new_data["is_peak_hour"] = peak_mask.astype(float)
            return TimeSeriesDataset(new_data, data.sample_interval)

The ``features_added`` method is used by the pipeline to track which columns were introduced by each transform, which is important for downstream dimensionality reduction and model explainability.

For transforms that need to learn parameters from training data — for example, a scaler that computes the training-set maximum — override ``fit`` as well:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform


    class MaxScaler(TimeSeriesTransform):
        """Scales all feature columns by the training-set maximum."""

        def __init__(self):
            self.scale_factor = None

        @property
        def is_fitted(self) -> bool:
            return self.scale_factor is not None

        def fit(self, data: TimeSeriesDataset) -> None:
            self.scale_factor = data.data.max().max()

        def features_added(self) -> list[str]:
            return []

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            scaled = data.data / self.scale_factor
            return TimeSeriesDataset(scaled, data.sample_interval)

.. note::

   The base ``TimeSeriesTransform`` sets ``is_fitted`` to ``True`` by default, so you only need to override it when your transform has a genuine unfitted state.

Built-in transforms you can use directly or as reference implementations include:

- ``openstef_models.transforms.time_domain.HolidayFeatureAdder`` — adds binary holiday indicator columns for a given country.
- ``openstef_models.transforms.time_domain.LagsAdder`` — creates lagged copies of the target variable.
- ``openstef_models.transforms.general.Scaler`` — normalises feature columns.
- ``openstef_models.transforms.general.Imputer`` — fills missing values.
- ``openstef_models.transforms.general.OutlierHandler`` — clips or removes statistical outliers.
- ``openstef_models.transforms.general.NaNDropper`` — removes rows with remaining NaN values after imputation.

Composing a Custom Pipeline
---------------------------

Once you have your transforms, you assemble them into a ``TransformPipeline`` and pass it to ``ForecastingModel`` as the ``preprocessing`` or ``postprocessing`` argument. The pipeline applies transforms in order, calling ``fit`` on each during training and ``transform`` on each during both training and inference.

The following example builds a preprocessing pipeline that adds holiday features, lag features, and then drops any rows that still contain NaN values — a common pattern when lag windows extend beyond the start of the training data:

.. code-block:: python

    from datetime import timedelta

    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.transforms import TransformPipeline
    from openstef_models.transforms.general import NaNDropper, Scaler
    from openstef_models.transforms.time_domain import HolidayFeatureAdder, LagsAdder

    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country=CountryAlpha2("NL")),
            LagsAdder(lags=[timedelta(hours=24), timedelta(hours=48), timedelta(days=7)]),
            NaNDropper(),
            Scaler(),
        ]
    )

With a preprocessing pipeline in hand, you can wire it into a ``ForecastingModel``:

.. code-block:: python

    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.constant_median_forecaster import (
        ConstantMedianForecaster,
    )
    from openstef_core.types import LeadTime, Q

    horizons = [LeadTime("PT1H"), LeadTime("PT24H")]

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(
            horizons=horizons,
            quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        ),
        # cutoff_history excludes the lag warm-up period from training
        cutoff_history=timedelta(days=7),
    )

.. note::

   Set ``cutoff_history`` to at least the length of your longest lag. Without it, the rows produced by the lag warm-up period — which contain NaN targets — will be included in training and degrade model quality.

Custom Workflow Callbacks
-------------------------

``CustomForecastingWorkflow`` is the top-level orchestrator. Rather than subclassing it, OpenSTEF exposes lifecycle hooks through ``ForecastingCallback``. Subclass ``ForecastingCallback`` and override only the methods you need; all methods have no-op defaults.

.. code-block:: python

    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback


    class MetricsLogger(ForecastingCallback):
        """Logs a summary after each training run."""

        def on_fit_start(self, pipeline, dataset):
            print(f"Training started — {len(dataset.data)} rows in dataset")

        def on_fit_end(self, context, result):
            print(f"Training complete — metrics: {result.metrics}")

        def on_predict_end(self, pipeline, dataset, forecasts):
            print(f"Forecast generated — {len(forecasts.data)} rows")


    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="custom_pipeline_v1",
        callbacks=[MetricsLogger()],
    )

    # Train and forecast as normal
    result = workflow.fit(train_dataset)
    forecasts = workflow.predict(forecast_dataset)

Available callback hooks are:

- ``on_fit_start(pipeline, dataset)`` — called before training begins.
- ``on_fit_end(context, result)`` — called after training completes, receives the ``ModelFitResult``.
- ``on_predict_end(pipeline, dataset, forecasts)`` — called after prediction, receives the ``ForecastDataset``.

Callbacks are the right place to add logging, metric emission, model validation checks, or integration with external systems. They keep that logic separate from the model and pipeline definitions, making both easier to test independently.

Putting It All Together
-----------------------

The following condensed example combines all three extension points: a custom transform, a composed pipeline, and a callback-equipped workflow.

.. code-block:: python

    from datetime import timedelta
    from pathlib import Path

    from pydantic_extra_types.country import CountryAlpha2

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform, TransformPipeline
    from openstef_core.types import LeadTime, Q
    from openstef_models.models.forecasting.constant_median_forecaster import (
        ConstantMedianForecaster,
    )
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.transforms.general import NaNDropper, Scaler
    from openstef_models.transforms.time_domain import HolidayFeatureAdder, LagsAdder
    from openstef_models.workflows import CustomForecastingWorkflow
    from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback


    # 1. Custom transform
    class PeakHourIndicator(TimeSeriesTransform):
        def features_added(self) -> list[str]:
            return ["is_peak_hour"]

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            hour = data.data.index.hour
            peak = ((hour >= 7) & (hour <= 9)) | ((hour >= 17) & (hour <= 19))
            new_data = data.data.copy()
            new_data["is_peak_hour"] = peak.astype(float)
            return TimeSeriesDataset(new_data, data.sample_interval)


    # 2. Composed pipeline
    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country=CountryAlpha2("NL")),
            PeakHourIndicator(),
            LagsAdder(lags=[timedelta(hours=24), timedelta(days=7)]),
            NaNDropper(),
            Scaler(),
        ]
    )

    horizons = [LeadTime("PT1H"), LeadTime("PT24H")]

    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=ConstantMedianForecaster(
            horizons=horizons,
            quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        ),
        cutoff_history=timedelta(days=7),
    )


    # 3. Callback
    class MetricsLogger(ForecastingCallback):
        def on_fit_end(self, context, result):
            print(f"Training complete — metrics: {result.metrics}")


    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="custom_pipeline_v1",
        callbacks=[MetricsLogger()],
    )

    # workflow.fit(train_dataset)
    # workflow.predict(forecast_dataset)

.. note::

   For a runnable version of this pattern with synthetic data, see the ``configuring_model_pipeline_example`` in the ``examples/`` directory of the repository.

Next Steps
----------

- :doc:`backtesting` — once your custom pipeline is working, use the backtesting framework to measure how it performs against historical data.
- :doc:`quickstart` — a minimal working example if you want a simpler reference point.