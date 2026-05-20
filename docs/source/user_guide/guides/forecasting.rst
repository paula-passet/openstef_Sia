Forecasting
===========

This page explains how forecasting works in OpenSTEF: what you provide, what you get back, and which API level to use depending on your goals. For runnable examples, see :doc:`/tutorials/forecasting_quickstart` and :doc:`/tutorials/custom_pipeline`.

Why a Forecasting Framework?
-----------------------------

Short-term energy forecasting requires more than fitting a model to a time series. You need consistent feature engineering, horizon-aware training, quantile uncertainty estimation, and reproducible pipelines that handle real-world data quirks (missing values, timezone shifts, irregular intervals). OpenSTEF encapsulates these concerns so you can focus on the forecasting problem rather than the plumbing.

The Forecasting Lifecycle
-------------------------

Every OpenSTEF forecast follows the same conceptual lifecycle:

1. **Prepare data** — datetime-indexed DataFrame with a target column (``load`` by default) and feature columns (weather, calendar, etc.)
2. **Wrap in a dataset** — create a :class:`~openstef_core.datasets.ForecastInputDataset` that validates structure and enforces invariants
3. **Fit a model** — train on historical data, producing a fitted workflow
4. **Predict** — generate a :class:`~openstef_core.datasets.ForecastDataset` containing point forecasts and optional quantile bands

.. mermaid:: /diagrams/user_guide/guides/forecasting_diagram_1.mmd

What You Provide
----------------

OpenSTEF expects a ``pandas.DataFrame`` with:

.. list-table:: Required Data Structure
   :header-rows: 1
   :widths: 25 75

   * - Requirement
     - Details
   * - **DatetimeIndex**
     - Sorted, timezone-aware timestamps. OpenSTEF validates monotonicity and consistency.
   * - **Target column**
     - A column named ``load`` (configurable via ``target_column``). This is the value being forecasted.
   * - **Feature columns**
     - Weather variables (temperature, wind speed, irradiance), calendar features, or any exogenous predictors relevant to your use case.
   * - **Sample interval**
     - A ``timedelta`` describing the time between consecutive rows (e.g., ``timedelta(minutes=15)``). OpenSTEF uses this to detect gaps and align horizons.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import ForecastInputDataset

   dataset = ForecastInputDataset(
       data=df,  # DataFrame with DatetimeIndex, 'load', and feature columns
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )

For details on dataset types and their guarantees, see :doc:`datasets`.

Time Zones and Sample Interval
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF requires timezone-aware indices. Internally, timestamps are never silently converted — what you provide is what the model sees. The ``sample_interval`` parameter is not inferred from the data; you declare it explicitly so the framework can validate consistency and compute horizons correctly.

.. warning::

   If your data has irregular intervals or gaps, OpenSTEF will raise validation errors. Resample or fill gaps before constructing a dataset.

What You Get Back
-----------------

A successful prediction returns a :class:`~openstef_core.datasets.ForecastDataset`. This contains:

- **Point forecast** — the median prediction (accessible via ``median_series``)
- **Quantile estimates** — columns like ``quantile_P10``, ``quantile_P50``, ``quantile_P90`` representing uncertainty bands
- **Forecast metadata** — ``forecast_start``, ``sample_interval``, and the list of ``quantiles`` produced

.. code-block:: python

   forecast: ForecastDataset = workflow.predict(predict_dataset, forecast_start=train_end)
   print(forecast.quantiles)       # e.g., [0.1, 0.5, 0.9]
   print(forecast.median_series)   # pd.Series of point forecasts

The P10–P90 interval covers 80% of expected outcomes. For improving quantile reliability, see :ref:`guide_quantile_calibration`.

API Levels
----------

OpenSTEF provides multiple abstraction levels. Choose based on how much control you need:

.. list-table:: API Abstraction Levels
   :header-rows: 1
   :widths: 20 40 40

   * - Level
     - Description
     - When to Use
   * - **Preset**
     - Pre-configured workflow created from a :class:`~openstef_models.presets.forecasting_workflow.ForecastingWorkflowConfig`. Handles model creation, preprocessing, and callbacks.
     - Production deployments where you want sensible defaults and minimal code.
   * - **Workflow**
     - :class:`~openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow` — orchestrates model management, callbacks, and optional persistence.
     - Research and experimentation where you need to customize individual components.
   * - **Model**
     - :class:`~openstef_models.models.forecasting_model.ForecastingModel` — single-forecaster pipeline managing preprocessing, training, and prediction.
     - Building custom model architectures or integrating non-standard forecasters.
   * - **Forecaster**
     - The lowest level: a raw forecaster implementing fit/predict. Used inside a ``ForecastingModel``.
     - Implementing new ML algorithms to plug into the framework.

Recommended Starting Points
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **For production**: Start with :func:`~openstef_models.presets.forecasting_workflow.create_forecasting_workflow`. It wires together preprocessing, model selection, and quantile estimation from a single configuration object.
- **For research**: Use ``CustomForecastingWorkflow`` directly. This gives you full control over callbacks, transforms, and model composition while still benefiting from the framework's data validation and lifecycle management.

.. mermaid:: /diagrams/user_guide/guides/forecasting_diagram_2.mmd

Putting It Together
-------------------

A minimal production forecast uses the preset level:

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig, create_forecasting_workflow,
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)
   forecast = workflow.predict(predict_dataset, forecast_start=forecast_start)

For a complete walkthrough with real data, see :doc:`/tutorials/forecasting_quickstart`. For customizing the pipeline with your own transforms and callbacks, see :doc:`/tutorials/custom_pipeline`.

Next Steps
----------

- :doc:`datasets` — understand the dataset types that wrap your data
- :doc:`/tutorials/forecasting_quickstart` — end-to-end runnable example
- :doc:`/tutorials/custom_pipeline` — build a custom forecasting pipeline