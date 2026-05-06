Quickstart
==========

This page gets you from a fresh install to a working forecast in under five minutes. There are no explanations of *why* things work — just the minimal steps to run them. For a guided walkthrough with commentary, see :doc:`first_forecast`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF installed and importable. If not, see :doc:`installation` first.

.. code-block:: python

    import openstef_models
    import openstef_core

No errors? You're ready.

Step 1 — Generate synthetic data
---------------------------------

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets.timeseries_dataset import create_synthetic_forecasting_dataset

    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=270),   # ~9 months of hourly data
        sample_interval=timedelta(hours=1),
        random_seed=42,
    )

    print(dataset)

``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` with a ``load`` target column and weather-like features (wind, temperature, radiation) already attached. It is a drop-in stand-in for real meter data.

Step 2 — Split into train and forecast sets
--------------------------------------------

.. code-block:: python

    from datetime import datetime, timezone

    cutoff = datetime(2025, 9, 1, tzinfo=timezone.utc)

    train_data = dataset.slice_time(end=cutoff)
    forecast_data = dataset.slice_time(start=cutoff)

    print(f"Training rows : {len(train_data)}")
    print(f"Forecast rows : {len(forecast_data)}")

Step 3 — Configure the preset workflow
----------------------------------------

.. code-block:: python

    from datetime import timedelta
    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )
    from openstef_core.types import Q

    config = ForecastingWorkflowConfig(
        model_id="quickstart-demo",
        model="xgboost",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        sample_interval=timedelta(hours=1),
        location=LocationConfig(
            name="Demo Site",
            description="Synthetic load site for quickstart",
        ),
    )

    workflow = create_forecasting_workflow(config)

``ForecastingWorkflowConfig`` is the single object that controls everything: model type, quantiles, feature engineering, and location metadata. ``create_forecasting_workflow`` wires it into a ready-to-use ``CustomForecastingWorkflow``.

Step 4 — Fit
-------------

.. code-block:: python

    workflow.fit(train_data)

Training runs synchronously. On the synthetic 270-day dataset this takes a few seconds on a laptop.

Step 5 — Predict
-----------------

.. code-block:: python

    forecast = workflow.predict(forecast_data)

    print(forecast.head())

``predict`` returns a ``ForecastDataset``. The columns include the median forecast (``q0.5``) and any additional quantiles you requested in the config.

.. note:: [VISUALIZATION: Line chart showing actual load vs. predicted quantile bands (q0.1, q0.5, q0.9) over the forecast horizon]

Complete script
---------------

Copy-paste the full working example:

.. code-block:: python

    from datetime import datetime, timedelta, timezone

    from openstef_core.datasets.timeseries_dataset import create_synthetic_forecasting_dataset
    from openstef_core.types import Q
    from openstef_models.presets.forecasting_workflow import (
        ForecastingWorkflowConfig,
        LocationConfig,
        create_forecasting_workflow,
    )

    # --- Data ---
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=270),
        sample_interval=timedelta(hours=1),
        random_seed=42,
    )

    cutoff = datetime(2025, 9, 1, tzinfo=timezone.utc)
    train_data = dataset.slice_time(end=cutoff)
    forecast_data = dataset.slice_time(start=cutoff)

    # --- Config ---
    config = ForecastingWorkflowConfig(
        model_id="quickstart-demo",
        model="xgboost",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        sample_interval=timedelta(hours=1),
        location=LocationConfig(
            name="Demo Site",
            description="Synthetic load site for quickstart",
        ),
    )

    # --- Workflow ---
    workflow = create_forecasting_workflow(config)
    workflow.fit(train_data)
    forecast = workflow.predict(forecast_data)

    print(forecast.head())

Next steps
----------

- **Understand what just happened** — :doc:`first_forecast` walks through each step with explanations.
- **Evaluate forecast quality** — :doc:`backtesting` shows how to measure accuracy on historical data.
- **Swap in real data or a custom model** — :doc:`advanced_customization` covers feature engineering, custom transforms, and model configuration.