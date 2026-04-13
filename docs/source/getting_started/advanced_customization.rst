Advanced Customization
======================

Once you're comfortable with the basics covered in :doc:`first_forecast` and :doc:`quickstart`, OpenSTEF exposes several well-defined extension points that let you adapt the library to your specific data, infrastructure, and modelling requirements. This page walks through the three main customization axes: workflow configuration, callback hooks, and feature engineering.

.. note::

   This page assumes familiarity with the core ``CustomForecastingWorkflow`` / ``ForecastingWorkflowConfig`` API. If you haven't run a basic forecast yet, start with :doc:`first_forecast` first.


Configuring the Forecasting Workflow
-------------------------------------

The simplest customization path is ``ForecastingWorkflowConfig``. Rather than subclassing anything, you compose the behaviour you want by adjusting configuration fields. The ``create_forecasting_workflow`` factory then builds a fully wired pipeline from that config.

.. code-block:: python

   from decimal import Decimal
   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Latitude, Longitude, Coordinate, CountryAlpha2, Q

   config = ForecastingWorkflowConfig(
       model_id="my_substation_001",
       run_name="lgbm-baseline-v1",
       # Choose from: "xgboost", "lgbm", "lgbmlinear", "gblinear", "flatliner", "median"
       model="lgbm",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],   # probabilistic output
       horizons=[timedelta(hours=h) for h in range(1, 49)],
       target_column="load",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       radiation_column="shortwave_radiation",
       location=LocationConfig(
           name="Amsterdam Substation",
           coordinate=Coordinate(
               latitude=Latitude(Decimal("52.3676")),
               longitude=Longitude(Decimal("4.9041")),
           ),
           country_code=CountryAlpha2("NL"),
       ),
       completeness_threshold=0.7,
       flatliner_threshold=6,
   )

   workflow = create_forecasting_workflow(config)

Key fields to know:

- **model** — selects the underlying estimator. ``"lgbm"`` and ``"xgboost"`` are the most capable; ``"gblinear"`` uses only the 7-day lag and is fast to train.
- **quantiles** — pass more than one quantile to get prediction intervals out of the box.
- **horizons** — controls which forecast lead times the lag feature adder generates. Longer horizons need more context data at prediction time.
- **completeness_threshold** — the pipeline will raise an error during training if the fraction of valid observations falls below this value.
- **country_code** — used internally to generate public-holiday indicator features.

.. note::

   ``ForecastingWorkflowConfig`` is a Pydantic model, so all fields are validated on construction. Typos in column names or out-of-range quantiles will raise a ``ValidationError`` immediately rather than failing silently at runtime.


Custom Feature Engineering
---------------------------

``create_forecasting_workflow`` automatically adds a rich set of energy-domain features — lag features, wind-power transforms, atmospheric derivatives, radiation-derived features, and calendar/holiday indicators. For most use cases you can control which features are active through the config's ``selected_features`` field, which acts as an explicit allowlist passed to a ``Selector`` transform at the head of the preprocessing chain.

When you need features that are not part of the built-in set, the recommended pattern is to compute them **before** passing data to the workflow and include the resulting columns in ``selected_features``:

.. code-block:: python

   import pandas as pd

   def add_custom_features(df: pd.DataFrame) -> pd.DataFrame:
       """Add domain-specific features before handing data to OpenSTEF."""
       # Example: industrial production index as an exogenous regressor
       df["load_per_degree"] = df["load"] / (df["temperature_2m"] + 1e-6)
       # Example: time-of-week sine/cosine encoding
       dow = df.index.dayofweek
       df["dow_sin"] = pd.Series(
           __import__("numpy").sin(2 * __import__("numpy").pi * dow / 7),
           index=df.index,
       )
       return df

   # Prepare your dataset
   raw_data = pd.read_parquet("my_data.parquet")
   enriched_data = add_custom_features(raw_data)

   # Tell the workflow to keep these columns
   config = ForecastingWorkflowConfig(
       ...,
       selected_features=[
           "load_per_degree",
           "dow_sin",
           # built-in features you still want:
           "T-1d",
           "T-2d",
           "wind_speed_80m",
       ],
   )

.. note::

   If ``selected_features`` is left empty (the default), the workflow keeps all features produced by its internal transforms. Providing an explicit list is the safest way to prevent feature leakage from columns you didn't intend to include.


Extending Workflows with Callbacks
------------------------------------

For production use — logging, metrics, model validation, integration with MLflow or other monitoring systems — OpenSTEF provides a **callback** mechanism based on the observer pattern. Callbacks are called at specific lifecycle events without you having to subclass the workflow itself.

The base class is ``ForecastingCallback`` (from ``openstef_models.workflows.custom_forecasting_workflow``). All methods have no-op default implementations, so you only override the events you care about:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       ForecastingCallback,
       CustomForecastingWorkflow,
   )
   from openstef_core.datasets import VersionedTimeSeriesDataset, ForecastDataset
   from openstef_models.mixins.callbacks import WorkflowContext

   class MetricsCallback(ForecastingCallback):
       """Log training duration and forecast statistics."""

       def on_fit_start(
           self,
           context: WorkflowContext,
           data: VersionedTimeSeriesDataset,
           data_val,
       ) -> None:
           import time
           context.data["fit_start"] = time.monotonic()
           print(f"Training started — {len(data.data)} rows")

       def on_fit_end(
           self,
           context: WorkflowContext,
           data: VersionedTimeSeriesDataset,
           data_val,
           result,
       ) -> None:
           import time
           elapsed = time.monotonic() - context.data["fit_start"]
           print(f"Training finished in {elapsed:.1f}s")

       def on_predict_end(
           self,
           context: WorkflowContext,
           data,
           result: ForecastDataset,
       ) -> None:
           print(f"Forecast produced: {result.data.shape[0]} rows")

The ``WorkflowContext`` object carries the workflow instance itself (``context.workflow``) and a free-form ``data`` dict you can use to pass state between hooks — as shown above to measure elapsed training time.

Attach one or more callbacks when you create the workflow:

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow

   workflow = create_forecasting_workflow(config)

   # Attach callbacks after construction
   workflow.callbacks.append(MetricsCallback())

   # Or pass multiple callbacks at once
   workflow = CustomForecastingWorkflow(
       model=workflow.model,
       callbacks=[MetricsCallback(), AnotherCallback()],
   )

.. note::

   Callbacks are executed in the order they are registered. If a callback raises an exception the remaining callbacks for that event are skipped, so keep individual callbacks focused and defensive.


Custom Workflow Orchestration
------------------------------

For advanced scenarios — for example, chaining a forecasting workflow with a component-splitting step, or implementing a custom training loop with early stopping — you can bypass the ``create_forecasting_workflow`` preset entirely and wire the ``CustomForecastingWorkflow`` directly.

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.workflows.custom_component_split_workflow import (
       CustomComponentSplitWorkflow,
   )
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Assume `forecasting_model` and `splitting_model` are already constructed
   forecasting_workflow = CustomForecastingWorkflow(
       model=forecasting_model,
       callbacks=[MetricsCallback()],
   )
   splitting_workflow = CustomComponentSplitWorkflow(
       model=splitting_model,
   )

   # Training
   forecasting_workflow.fit(train_dataset, data_val=val_dataset)

   # Inference: first forecast, then decompose into components
   forecasts: ForecastDataset = forecasting_workflow.predict(live_dataset)
   components = splitting_workflow.predict(live_dataset)

The ``with_run_name`` method on ``CustomForecastingWorkflow`` lets you tag a run for versioning without rebuilding the whole workflow:

.. code-block:: python

   workflow = forecasting_workflow.with_run_name("experiment-2025-Q2")

This is useful when you want to iterate on hyperparameters while keeping the same callback and model structure.


Choosing the Right Extension Point
------------------------------------

The table below summarises when to use each approach:

- **ForecastingWorkflowConfig fields** — adjust model type, quantiles, horizons, column names, data quality thresholds. No code subclassing required; covers the majority of customisation needs.
- **selected_features + pre-computed columns** — add domain-specific exogenous features that OpenSTEF doesn't generate internally.
- **Callbacks** — add logging, metrics, alerting, or external system integration without touching the core pipeline logic.
- **Direct CustomForecastingWorkflow construction** — full control over the pipeline when presets don't fit, or when you need to compose multiple workflows.

For backtesting custom configurations see :doc:`backtesting`, which shows how to evaluate different ``ForecastingWorkflowConfig`` setups against historical data.