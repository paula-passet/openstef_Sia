Advanced Customization
======================

OpenSTEF is designed as an extensible library. While the built-in presets and pipelines cover the majority of forecasting use cases, you will eventually need to tailor data preparation, feature engineering, or pipeline composition to your specific domain. This page walks through the three main extension points: custom data transforms, custom feature pipelines, and custom workflow orchestration.

If you haven't yet run a basic forecast, start with :doc:`first_forecast` first. For comparing model variants you've built here, see :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Custom Data Transforms
----------------------

Every preprocessing and feature-engineering step in OpenSTEF is a **transform** — an object that implements the ``TimeSeriesTransform`` interface from ``openstef_core``. Transforms follow the familiar scikit-learn ``fit`` / ``transform`` pattern, but operate on ``TimeSeriesDataset`` objects rather than raw NumPy arrays.

The abstract base class requires you to implement two things:

- ``transform(data: TimeSeriesDataset) -> TimeSeriesDataset`` — apply the transformation and return the modified dataset.
- ``features_added() -> list[str]`` — declare which column names your transform introduces (used for introspection and validation).

Optionally override ``fit(data: TimeSeriesDataset)`` when your transform needs to learn parameters from training data (e.g. a scaler that computes mean and standard deviation). The default implementation is a no-op, making stateless transforms trivial to write.

Here is a minimal example that adds a rolling standard deviation feature:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform


    class RollingStdAdder(TimeSeriesTransform):
        """Adds a rolling standard-deviation feature for the target column."""

        def __init__(self, target_column: str = "load", window: int = 24):
            self.target_column = target_column
            self.window = window

        def features_added(self) -> list[str]:
            return [f"{self.target_column}_rolling_std_{self.window}h"]

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            feature_name = self.features_added()[0]
            rolling_std = (
                data.data[self.target_column]
                .rolling(self.window)
                .std()
            )
            new_data = data.data.copy()
            new_data[feature_name] = rolling_std
            return TimeSeriesDataset(new_data, data.sample_interval)

Because ``is_fitted`` defaults to ``True`` for stateless transforms, this class is immediately usable without calling ``fit``. For a stateful transform — for example one that normalises by training-set statistics — override ``is_fitted`` as a property that returns whether the learned parameters have been set, and populate them inside ``fit``.

.. note::

   OpenSTEF ships several ready-made transforms in ``openstef_models.transforms.time_domain``:
   ``HolidayFeatureAdder``, ``DatetimeFeaturesAdder``, ``CyclicFeaturesAdder``, and
   ``RollingAggregatesAdder``. Check these before writing your own — they are often
   sufficient and are already well-tested.

Custom Feature Pipelines
------------------------

Individual transforms become useful when composed into a ``TransformPipeline``. The pipeline calls each transform's ``fit_transform`` in sequence during training and ``transform`` in sequence during inference, passing the output of one step as the input to the next.

.. code-block:: python

    from openstef_models.transforms.time_domain import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
    )
    from openstef_core.transforms import TransformPipeline

    # Your custom transform from the previous section
    rolling_std = RollingStdAdder(target_column="load", window=24)

    feature_pipeline = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country="NL"),
            DatetimeFeaturesAdder(),
            CyclicFeaturesAdder(),
            rolling_std,          # plug in your custom step here
        ]
    )

The pipeline is serialisable alongside the model, so the exact preprocessing applied during training is always reproduced at prediction time — no separate preprocessing objects to track.

**Ordering matters.** Transforms that add new columns must run before transforms that consume those columns. Transforms that drop rows (such as ``NaNDropper``) should generally run last in the preprocessing stage so that earlier steps have access to the full history.

Custom Pipeline Workflows
-------------------------

Once you have a feature pipeline and a forecaster, you assemble them into a ``ForecastingModel``. This is the central composition object in OpenSTEF: it owns preprocessing, the forecaster itself, and optional postprocessing, and it exposes a unified ``fit`` / ``predict`` interface.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta

    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.constant_median_forecaster import (
        ConstantMedianForecaster,
    )
    from openstef_models.transforms.time_domain import HolidayFeatureAdder, DatetimeFeaturesAdder
    from openstef_core.transforms import TransformPipeline

    # --- Build preprocessing pipeline ---
    preprocessing = TransformPipeline(
        transforms=[
            HolidayFeatureAdder(country="NL"),
            DatetimeFeaturesAdder(),
            RollingStdAdder(target_column="load", window=24),
        ]
    )

    # --- Choose a forecaster ---
    forecaster = ConstantMedianForecaster(
        quantiles=[0.1, 0.5, 0.9],
        horizons=[timedelta(hours=h) for h in range(1, 49)],
    )

    # --- Assemble the full model ---
    model = ForecastingModel(
        preprocessing=preprocessing,
        forecaster=forecaster,
        postprocessing=None,   # add postprocessing transforms here if needed
        cutoff_history=timedelta(days=1),  # exclude NaN rows created by lag features
    )

.. note::

   Set ``cutoff_history`` to at least the longest lag window used in your preprocessing.
   OpenSTEF cannot infer this automatically — if you omit it, rows with NaN lag values
   will be passed to the forecaster during training, which degrades model quality.

Fitting and predicting then work exactly as with any built-in preset:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset

    # Assume `train_data` is a TimeSeriesDataset with a "load" column
    model.fit(train_data)

    # Predict returns a forecast dataset
    forecasts = model.predict(predict_data)

Workflow Orchestration with Callbacks
--------------------------------------

For production systems you will typically want lifecycle hooks — logging, alerting, model persistence — without coupling that logic to the model itself. OpenSTEF provides ``CustomForecastingWorkflow`` for this purpose. It wraps a ``ForecastingModel`` and fires callback methods at well-defined points in the training and prediction lifecycle.

Implement a callback by subclassing ``ForecastCallback``:

.. code-block:: python

    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
        ForecastCallback,
    )

    class AuditCallback(ForecastCallback):
        """Log key metrics at each stage of the workflow."""

        def on_train_start(self, pipeline, dataset):
            print(f"Training started on {len(dataset.data)} rows")

        def on_train_end(self, pipeline, dataset):
            print("Training complete")

        def on_predict_end(self, pipeline, dataset, forecasts):
            print(f"Generated {len(forecasts.data)} forecast rows")


    workflow = CustomForecastingWorkflow(
        model=model,
        callbacks=AuditCallback(),
    )

    # The workflow exposes the same fit/predict interface as ForecastingModel
    workflow.fit(train_data)
    forecasts = workflow.predict(predict_data)

You can pass multiple callbacks as a list. Callbacks are executed in order and receive references to the pipeline and dataset, giving you full access to model internals for metrics, serialisation, or alerting.

To add **model persistence**, pass a storage backend when constructing the workflow:

.. code-block:: python

    from openstef_models.storage import LocalModelStorage

    storage = LocalModelStorage(path="/models/my_forecast_model")

    workflow = CustomForecastingWorkflow(
        model=model,
        callbacks=AuditCallback(),
        storage=storage,
    )

    # fit() now automatically saves the trained model to disk
    workflow.fit(train_data)

    # A later process can reload and predict without re-training
    workflow.predict(predict_data)

Putting It All Together
-----------------------

The pattern across all three extension points is consistent:

- **Transforms** are the atomic unit — implement ``TimeSeriesTransform`` to add any data manipulation step.
- **Pipelines** compose transforms into ordered sequences for preprocessing and postprocessing.
- **ForecastingModel** assembles a pipeline and a forecaster into a single, serialisable object.
- **CustomForecastingWorkflow** wraps the model with lifecycle hooks and optional persistence.

You can customise at any level without touching the others. A team that only needs a new feature can write one transform and slot it into an existing preset pipeline. A team building a production system can leave the model untouched and add all operational concerns in a callback.

For a worked end-to-end example using a preset configuration as a starting point, see the ``examples/configuring_model_pipeline_example.py`` file in the repository. To evaluate the impact of your customisations against a baseline, see :doc:`backtesting`.