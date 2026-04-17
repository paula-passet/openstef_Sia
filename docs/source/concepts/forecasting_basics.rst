Forecasting Basics
==================

Short-term energy forecasting is the practice of predicting electricity load, generation, or price over a near-future window — typically from minutes to a few days ahead. This page explains what short-term forecasting means in the context of OpenSTEF, how the key temporal concepts relate to one another, and why these distinctions matter when you configure and deploy a forecasting model.

For probabilistic aspects of forecasts (quantiles, prediction intervals), see :doc:`quantiles_and_confidence`. For the input features that drive forecast accuracy, see :doc:`feature_engineering`.

What Is Short-Term Forecasting?
--------------------------------

Energy systems require continuous balancing of supply and demand. Grid operators, traders, and asset managers all need to know — with reasonable confidence — what load or generation will look like in the near future. Short-term forecasting covers the window where operational decisions are still actionable: you can still dispatch a generator, adjust a bid, or schedule a curtailment.

OpenSTEF is a library purpose-built for this operational window. It does not attempt to model seasonal capacity planning or multi-year trends. Instead, it focuses on the hours and days ahead where machine learning models, trained on historical patterns and real-time weather data, consistently outperform simpler heuristics.

The practical upper boundary of "short-term" in OpenSTEF is typically 48 hours. Beyond that, forecast uncertainty grows rapidly and the models are no longer calibrated for reliable operational use.

Horizons, Lead Times, and Availability
----------------------------------------

Three temporal concepts govern every forecast in OpenSTEF. Understanding how they interact is essential before configuring any model.

**Lead time** is the distance between when a forecast is *generated* and the timestamp it is *predicting*. A lead time of ``PT1H`` means the model is predicting one hour into the future from the moment the forecast is produced. OpenSTEF represents lead times using the ``LeadTime`` type, which accepts ISO 8601 duration strings:

.. code-block:: python

    from openstef_core.types import LeadTime

    # Common lead times used in operational forecasting
    lead_1h  = LeadTime.from_string("PT1H")   # 1 hour ahead
    lead_24h = LeadTime.from_string("PT24H")  # day-ahead
    lead_36h = LeadTime.from_string("PT36H")  # typical day-ahead gate closure
    lead_48h = LeadTime.from_string("PT48H")  # two days ahead

**Horizon** is the full set of lead times a model is configured to predict. A model with ``horizons=[PT1H, PT24H, PT48H]`` produces three separate predictions for each target timestamp — one from each lookahead distance. In OpenSTEF, some model architectures handle multiple horizons in a single unified model, while others train a separate model per lead time. The library abstracts this difference behind a consistent interface.

**Available at** (``AvailableAt``) captures *when* a forecast becomes usable. This is distinct from when it was generated: a forecast produced at 06:00 for the following day is "available at" 06:00 on day D-1. This concept is critical for realistic backtesting — it prevents the model from accidentally using data that would not have been available at prediction time in production.

.. code-block:: python

    from openstef_core.types import LeadTime
    from openstef_core.datasets import ForecastDataset

    # Filter a forecast dataset to only the 24h-ahead predictions
    # that were available before a given operational cutoff
    predictions_24h = forecast_dataset.filter_by_lead_time(
        lead_time=LeadTime.from_string("PT24H")
    ).select_version()

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

Forecast Frequency and Update Cycles
--------------------------------------

Short-term forecasts are not produced once and held fixed. In operational energy systems, forecasts are refreshed continuously as new observations arrive — updated meter readings, revised weather data, and real-time grid signals all improve accuracy. OpenSTEF is designed around this rolling-update model.

The **prediction sample interval** controls the temporal resolution of the output: how finely the forecast is discretised in time. A 15-minute interval produces 96 forecast points per day; an hourly interval produces 24. This is set at the dataset level:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    # A dataset with 15-minute resolution
    dataset = VersionedTimeSeriesDataset.from_pandas(
        df,
        sample_interval=timedelta(minutes=15),
    )

The **predict interval** controls how often the forecasting pipeline runs and issues a fresh set of predictions. In a production deployment you might retrain weekly but re-forecast every 15 minutes or every hour, incorporating the latest available inputs each time.

The **train interval** controls how often the underlying model is retrained from scratch on accumulated history. Retraining is computationally heavier than inference, so it happens less frequently — typically daily or weekly.

These three intervals are independent and can be tuned separately to balance computational cost against forecast freshness.

How Short-Term Differs from Long-Term Forecasting
---------------------------------------------------

The distinction is not merely one of timescale — it reflects fundamentally different modelling assumptions and data requirements.

Long-term forecasting (months to years) relies on structural drivers: economic growth, demographic change, technology adoption curves, and policy scenarios. These models are typically statistical or econometric, updated infrequently, and used for capacity planning rather than operational dispatch.

Short-term forecasting, by contrast, is dominated by:

- **Weather** — temperature, solar irradiance, and wind speed drive load and renewable generation on timescales of minutes to hours.
- **Calendar patterns** — time of day, day of week, and public holidays create strong, learnable periodicities.
- **Recent history** — the last few hours of observed load are among the most predictive features for the next few hours.

These characteristics make short-term forecasting well-suited to machine learning. Models can learn complex, non-linear interactions between weather and load without requiring explicit physical equations. OpenSTEF's feature engineering pipeline is designed to extract exactly these signals automatically — see :doc:`feature_engineering` for details.

A practical consequence is that short-term models degrade gracefully as lead time increases. A model that is highly accurate at PT1H will be less accurate at PT24H and less still at PT48H, because weather forecast uncertainty compounds and the recent-history signal weakens. OpenSTEF's multi-horizon architecture makes this degradation explicit and measurable: you can evaluate accuracy separately at each lead time and make informed decisions about which horizons are operationally useful.

Configuring a Multi-Horizon Forecast
--------------------------------------

The following example shows how to configure a complete forecasting workflow in OpenSTEF with multiple lead times. The library handles the complexity of training and predicting across horizons behind a single, consistent interface:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    workflow = create_forecasting_workflow(
        config=ForecastingWorkflowConfig(
            model_id="load_forecast_demo",
            model="gblinear",

            # Define the lead times this model will predict
            horizons=[
                LeadTime.from_string("PT1H"),   # intraday
                LeadTime.from_string("PT24H"),  # day-ahead
                LeadTime.from_string("PT48H"),  # two-day-ahead
            ],

            # Probabilistic output: median plus 80% prediction interval
            quantiles=[Q(0.1), Q(0.5), Q(0.9)],

            target_column="load",
            temperature_column="temperature_2m",
            wind_speed_column="wind_speed_10m",
            radiation_column="shortwave_radiation",
        )
    )

Here, ``horizons`` is the central configuration knob for temporal scope. Each ``LeadTime`` entry tells the model how far ahead it must predict, and the library ensures that features are constructed and data is filtered appropriately for each horizon — preventing any leakage of future information.

.. note::

   Multi-horizon models like ``gblinear`` share parameters across all configured lead times, which is efficient but requires that the model architecture can handle the varying feature availability at different lookahead distances. Single-horizon architectures train one model per lead time and are simpler but more expensive to run. The OpenSTEF library supports both patterns through the same ``horizons`` interface.

Practical Guidance on Choosing Horizons
-----------------------------------------

Not every use case needs every horizon. A few rules of thumb:

- **Intraday balancing** (PT15M to PT4H): Prioritise low latency and high update frequency. Use short training windows and retrain frequently.
- **Day-ahead markets** (PT12H to PT36H): The most common operational horizon. Weather forecasts are the dominant driver; model accuracy is strongly correlated with weather forecast quality.
- **Two-day-ahead planning** (PT36H to PT48H): Useful for unit commitment and outage scheduling. Expect meaningfully higher uncertainty than day-ahead; always use probabilistic outputs (see :doc:`quantiles_and_confidence`).

When a model or data source fails at a given horizon, OpenSTEF provides fallback mechanisms to ensure operational continuity — these are covered in :doc:`reliability_and_fallback`.