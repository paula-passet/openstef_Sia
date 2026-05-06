Quickstart
==========

This page walks you through producing your first energy forecast with OpenSTEF in under a minute of reading. You will generate synthetic load data, configure a preset forecasting workflow, train a model, and retrieve predictions — all in a single self-contained script.

Before running the example, make sure OpenSTEF is installed. See the :doc:`installation` page if you have not done that yet.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

---

Your First Forecast
-------------------

The snippet below is copy-paste ready. It uses ``openstef_core.testing.create_synthetic_forecasting_dataset`` to avoid any dependency on real data files, so nothing needs to be downloaded or prepared in advance.

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
    from openstef_models.integrations.mlflow import MLFlowStorage

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")

    # 1. Generate synthetic hourly load data (90 days)
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=90),
        wind_influence=-10.0,
        temp_influence=5.0,
        radiation_influence=-7.0,
        stochastic_influence=2.0,
        sample_interval=timedelta(hours=1),
    )

    # 2. Configure the preset workflow
    workflow = create_forecasting_workflow(
        config=ForecastingWorkflowConfig(
            model_id="my_first_forecaster",
            model="gblinear",
            horizons=[LeadTime.from_string("PT36H")],
            quantiles=[Q(0.1), Q(0.5), Q(0.9)],
            mlflow_storage=MLFlowStorage(
                tracking_uri="mlflow_tracking",
                local_artifacts_path=Path("mlflow_tracking_artifacts"),
            ),
        )
    )

    # 3. Train
    workflow.fit(dataset)

    # 4. Predict
    forecast = workflow.predict(dataset)
    print(forecast)

Run this script from any directory. MLflow artefacts are written to ``mlflow_tracking/`` and ``mlflow_tracking_artifacts/`` relative to the working directory.

.. note:: [VISUALIZATION: Example console output showing a ForecastDataset with columns quantile_P10, quantile_P50, quantile_P90 and a DatetimeIndex covering the 36-hour horizon]

---

What Each Step Does
-------------------

**Synthetic data**

``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` whose target column is a realistic-looking load signal composed of configurable physical influences (wind, temperature, solar radiation) plus a stochastic noise term. The default start date is ``2025-01-01T00:00:00+00:00`` and the default length is nine months; the example above shortens this to 90 days to keep training fast.

**Preset configuration**

``ForecastingWorkflowConfig`` is a Pydantic model that bundles everything the workflow needs:

- ``model_id`` — a unique string identifier used to store and retrieve the trained model in MLflow.
- ``model`` — the underlying booster type. ``"gblinear"`` is a good default; other options include ``"xgb"`` and ``"lgbm"``.
- ``horizons`` — a list of :class:`LeadTime` values expressed as ISO 8601 durations (e.g. ``"PT36H"`` = 36 hours ahead). Currently one horizon per workflow is supported.
- ``quantiles`` — probability levels for uncertainty estimation. ``Q(0.5)`` is the median; ``Q(0.1)`` and ``Q(0.9)`` form an 80 % prediction interval.
- ``mlflow_storage`` — tells the workflow where to persist trained model artefacts.

**Creating the workflow**

``create_forecasting_workflow(config)`` returns a ``CustomForecastingWorkflow`` instance wired up with the feature engineering pipeline, the chosen model, and MLflow callbacks. You do not need to assemble these components manually for standard use cases.

**Fit and predict**

``workflow.fit(dataset)`` trains the model on the full dataset you pass in. ``workflow.predict(dataset)`` uses the same dataset as context and returns a ``ForecastDataset`` — a ``TimeSeriesDataset`` whose columns are named ``quantile_P10``, ``quantile_P50``, ``quantile_P90`` (matching the quantiles you configured).

---

Adjusting the Synthetic Data
-----------------------------

``create_synthetic_forecasting_dataset`` accepts several keyword arguments that let you shape the signal without touching real data:

.. code-block:: python

    from openstef_core.testing import create_synthetic_forecasting_dataset
    from datetime import datetime, timedelta, timezone

    dataset = create_synthetic_forecasting_dataset(
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        length=timedelta(days=180),
        sample_interval=timedelta(minutes=15),   # 15-minute resolution
        wind_influence=-15.0,
        temp_influence=8.0,
        radiation_influence=-10.0,
        stochastic_influence=3.0,
        include_atmosphere=True,   # adds pressure / humidity columns
        include_price=True,        # adds an electricity price column
        random_seed=0,
    )

Setting ``include_atmosphere=True`` or ``include_price=True`` adds extra feature columns that the model can exploit. The ``random_seed`` parameter makes runs reproducible.

---

Changing the Forecast Horizon
------------------------------

Swap the ``horizons`` argument to target a different look-ahead window:

.. code-block:: python

    from openstef_core.types import LeadTime

    # 24-hour horizon instead of 36
    horizons=[LeadTime.from_string("PT24H")]

    # 48-hour horizon
    horizons=[LeadTime.from_string("PT48H")]

Lead times are expressed as ISO 8601 duration strings. ``PT`` prefixes hours and minutes; ``P`` prefixes days (e.g. ``P2D`` = 48 hours).

---

Next Steps
----------

Once the basic example works, explore the rest of the getting-started section:

- **Installation** — system requirements, optional extras, and virtual-environment setup: :doc:`installation`.
- **Concepts** — understand ``TimeSeriesDataset``, ``LeadTime``, quantiles, and the workflow abstraction before customising further.
- **Tutorials** — step-by-step guides for real data ingestion, custom feature transforms, and ensemble workflows.

.. note::

   The ``MLFlowStorage`` used above writes to the local filesystem. For team or production use you will want to point ``tracking_uri`` at a remote MLflow server. See the MLflow integration documentation for details.