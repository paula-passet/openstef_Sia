Forecasting Basics
==================

Short-term energy forecasting sits at the operational heart of grid management, trading desks, and demand response programs. This page explains what short-term forecasting means in practice, how it differs from longer planning horizons, and how OpenSTEF's data model maps directly onto the key concepts of horizons, lead times, and update frequency.

What Is Short-Term Forecasting?
--------------------------------

Short-term forecasting predicts energy load or generation over a window of minutes to a few days ahead. Unlike long-term capacity planning — which projects demand growth over years using demographic and economic models — short-term forecasting must be *operationally accurate*: the forecast needs to be ready before the decision it informs, and it needs to be updated continuously as conditions change.

The distinction matters because the two problem types are fundamentally different:

- **Long-term forecasting** (weeks to years) relies on trend analysis, climate projections, and economic indicators. Accuracy is measured in percentages over broad aggregates. A forecast produced once a month is sufficient.
- **Short-term forecasting** (minutes to ~48 hours) relies on recent measurements, weather nowcasts, and learned temporal patterns. Accuracy is measured in absolute power units (MW, kW) at specific timestamps. Forecasts must be refreshed every 15 minutes or every hour to remain useful.

OpenSTEF is designed exclusively for the short-term problem. Its data structures, model configurations, and workflow abstractions all assume you are producing forecasts that will be acted upon within the next few hours or days.

Horizons, Lead Times, and Update Frequency
-------------------------------------------

Three concepts govern how a short-term forecast is specified in OpenSTEF:

**Forecast horizon** is how far ahead you are predicting, measured from the moment the forecast is made. A 24-hour horizon means the forecast covers the next 24 hours. OpenSTEF represents horizons using ISO 8601 duration strings (e.g. ``PT15M``, ``PT1H``, ``PT24H``, ``PT48H``) through its ``LeadTime`` type.

**Lead time** is the gap between when input data became available and the target timestamp being predicted. If a measurement at 14:00 is used to predict the load at 16:00, the lead time for that prediction is 2 hours. Lead time is a property of each individual prediction in a dataset, not of the forecast as a whole. In OpenSTEF's ``TimeSeriesDataset``, the ``lead_time_series`` property returns this per-row gap, computed as the difference between the target timestamp and the ``available_at`` column.

**Update frequency** is how often a new forecast is produced. A system forecasting at 15-minute resolution typically re-runs every 15 minutes, so that the forecast is always anchored to the most recent available data. Higher update frequency reduces the effective lead time for near-term predictions and keeps the forecast aligned with rapidly changing conditions such as cloud cover or sudden load spikes.

.. mermaid:: diagrams/concepts/forecasting_basics_diagram_1.mmd

Why Multiple Horizons Matter
-----------------------------

A single model trained on one horizon will not generalise well across all lead times. The statistical relationship between features and load changes significantly depending on how far ahead you are predicting:

- At **15-minute** lead times, the most recent load measurements are highly predictive. The forecast is essentially a short extrapolation of the current trend.
- At **1-hour** lead times, recent load still matters, but weather forecasts begin to contribute meaningfully, particularly temperature and solar irradiance.
- At **24–48 hour** lead times, the dominant drivers shift to calendar patterns (day of week, public holidays), weather forecasts, and seasonal baselines. Recent measurements become less informative because the system state at the target time will have been reset by many intervening cycles.

OpenSTEF handles this by allowing you to configure a list of horizons per model. Each horizon can be treated as a separate prediction target, and the library selects the appropriate version of input features for each lead time based on data availability.

Representing Horizons in OpenSTEF
----------------------------------

The ``LeadTime`` class is the canonical way to express a forecast horizon. You construct one from an ISO 8601 duration string and use it throughout the configuration and data filtering APIs:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef.data_classes.lead_time import LeadTime
   from openstef.data_classes.time_series_dataset import TimeSeriesDataset

   # Define the horizons this model should produce forecasts for
   horizons = [
       LeadTime.from_string("PT15M"),   # 15 minutes ahead
       LeadTime.from_string("PT1H"),    # 1 hour ahead
       LeadTime.from_string("PT24H"),   # 24 hours ahead
       LeadTime.from_string("PT48H"),   # 48 hours ahead
   ]

   # Load a versioned dataset (with available_at column)
   df = pd.read_parquet("load_data.parquet")
   dataset = TimeSeriesDataset.from_pandas(df, sample_interval=timedelta(minutes=15))

   # Inspect which horizons are present in the dataset
   print(dataset.horizons)

   # Select only the data relevant to a specific horizon
   data_24h = dataset.select_horizon(LeadTime.from_string("PT24H"))

The ``select_horizon`` method filters the dataset to rows whose lead time matches the requested horizon. This is the mechanism by which OpenSTEF trains separate model versions for each horizon while keeping the data pipeline uniform.

Configuring Horizons in a Forecasting Workflow
-----------------------------------------------

When you configure a forecasting workflow, the ``horizons`` field on the configuration object drives both training and inference. The model will be trained once per horizon and will produce predictions at each configured lead time during inference:

.. code-block:: python

   from openstef.data_classes.lead_time import LeadTime
   from openstef.data_classes.quantile import Quantile
   from openstef.workflows.lgbm_forecasting_workflow import LGBMForecastingWorkflowConfig

   config = LGBMForecastingWorkflowConfig(
       model_id="substation_42",
       horizons=[
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT48H"),
       ],
       quantiles=[
           Quantile(0.1),
           Quantile(0.5),
           Quantile(0.9),
       ],
   )

The ``max_horizon`` property on the config returns the largest configured lead time, which the library uses internally to determine how far back in time training data must extend.

.. note::

   The ``quantiles`` field controls the probabilistic outputs of the forecast — the 10th, 50th, and 90th percentiles in the example above. Probabilistic forecasting is a separate topic; see :doc:`quantiles_and_confidence` for a full explanation.

The Role of Data Resolution
----------------------------

The ``sample_interval`` of your ``TimeSeriesDataset`` defines the temporal resolution of both inputs and outputs. A dataset with ``sample_interval=timedelta(minutes=15)`` will produce one forecast value every 15 minutes across the configured horizon. This means a 24-hour horizon at 15-minute resolution yields 96 individual predictions per forecast run.

Resolution and horizon interact in an important way: the ratio between them determines the number of prediction steps the model must produce. Very fine resolution at long horizons (e.g. 5-minute resolution at 48 hours) creates 576 steps and can significantly increase training and inference time. In practice, most grid operators use 15-minute resolution for operational forecasts and aggregate to hourly or daily resolution for planning purposes.

Relationship to Feature Engineering and Model Selection
--------------------------------------------------------

The choice of horizon directly influences which features are useful and which models perform well. Features derived from recent measurements (lagged load values, rolling averages) are most valuable at short horizons. Calendar and weather features dominate at longer horizons.

OpenSTEF's feature engineering pipeline is aware of lead time and will only include features that are causally available at the time the forecast is made — it will not inadvertently use future information. This is covered in detail in :doc:`feature_engineering`.

For guidance on which model architectures perform best at different horizon ranges, see :doc:`model_selection`. If you are deploying forecasts in a production system where data may arrive late or be missing, :doc:`reliability_and_fallback` explains how OpenSTEF handles degraded input conditions without silently producing unreliable forecasts.