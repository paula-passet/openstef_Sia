Feature Engineering for Energy Forecasting
==========================================

Good forecasts depend on good features. OpenSTEF's approach to feature engineering is grounded in a simple principle: encode what you know about the physical and social world into the model's inputs. A gradient-boosted tree cannot read a weather forecast or a calendar — but it can learn from a column called ``radiation_W_m2`` or ``is_public_holiday``. This page explains the main feature categories OpenSTEF uses, how they are constructed, and how to add your own.

All feature transforms live in ``openstef_models.transforms`` and implement the ``TimeSeriesTransform`` interface, so they compose cleanly into a preprocessing pipeline.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

----

Weather Features
----------------

Weather is the dominant driver of short-term electricity demand and generation. OpenSTEF provides dedicated transforms for the most important meteorological signals.

**Solar radiation and PV generation**

Global horizontal irradiance (GHI) is the single most important input for grids with rooftop solar. Raw irradiance is useful, but ``RadiationDerivedFeaturesAdder`` goes further: it uses the grid location's coordinates to compute sun elevation angle, clear-sky irradiance, and a cloud-cover proxy. These derived quantities give the model physical context that raw GHI alone cannot provide.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.transforms.energy_domain import RadiationDerivedFeaturesAdder
    from openstef_core.datasets import TimeSeriesDataset

    transform = RadiationDerivedFeaturesAdder(
        coordinate=(52.37, 4.90),          # Amsterdam, (lat, lon)
        radiation_column="radiation_W_m2",
    )
    dataset_with_radiation = transform.transform(dataset)

**Wind power**

``WindPowerFeatureAdder`` converts a wind-speed column into an estimated wind-power output using a standard power-curve approximation. The cubic relationship between wind speed and power is non-trivial for a linear model to learn from raw speed alone; encoding it explicitly improves accuracy on grids with significant wind generation.

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    transform = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_m_s")
    dataset_with_wind = transform.transform(dataset)

**Atmospheric conditions**

Temperature, pressure, and relative humidity interact in ways that affect both demand (heating/cooling loads) and generation efficiency. ``AtmosphereDerivedFeaturesAdder`` computes derived quantities such as dew point and apparent temperature from these raw inputs.

.. code-block:: python

    from openstef_models.transforms.energy_domain import AtmosphereDerivedFeaturesAdder

    transform = AtmosphereDerivedFeaturesAdder(
        pressure_column="pressure_hPa",
        relative_humidity_column="humidity_pct",
        temperature_column="temperature_C",
    )
    dataset_with_atmos = transform.transform(dataset)

.. note::

    Weather features are only as good as the forecast that feeds them. During training, use historical actuals. At inference time, replace them with NWP (Numerical Weather Prediction) model output. Keeping the column names identical means the same pipeline handles both cases.

----

Time Features
-------------

Energy consumption follows strong periodic patterns — daily commutes, weekly work schedules, seasonal heating demand. Encoding time explicitly lets the model learn these rhythms without having to infer them from load history alone.

**Cyclic encoding**

Hours, days, and months are circular: hour 23 is closer to hour 0 than to hour 12. Representing them as raw integers breaks this continuity. ``CyclicFeaturesAdder`` encodes each temporal dimension as a sine/cosine pair, preserving the circular structure.

.. code-block:: python

    from openstef_models.transforms.time_domain import CyclicFeaturesAdder

    # Default: encodes time_of_day, season, day_of_week, month
    transform = CyclicFeaturesAdder()
    dataset_cyclic = transform.transform(dataset)

    # Or select a subset
    transform = CyclicFeaturesAdder(included_features=["time_of_day", "day_of_week"])

The result is pairs of columns such as ``time_of_day_sine`` / ``time_of_day_cosine``. A model trained on these can smoothly interpolate across midnight or the year-end boundary.

**Discrete datetime features**

Some models — particularly tree-based ones — handle categorical splits well. ``DatetimeFeaturesAdder`` extracts discrete fields (hour of day, day of week, month, year) as plain integers, which XGBoost and LightGBM can split on directly.

.. code-block:: python

    from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

    transform = DatetimeFeaturesAdder(onehot_encode=False)
    dataset_dt = transform.transform(dataset)

**Daylight**

Sunrise and sunset times shift continuously through the year and vary with latitude. ``DaylightFeatureAdder`` computes whether each timestamp falls within daylight hours and how far into the day it sits, giving the model a physically meaningful signal for solar-driven demand patterns.

**Public holidays**

A Monday that is a public holiday looks nothing like a regular Monday. ``HolidayFeatureAdder`` adds a binary indicator using the ``holidays`` library, keyed to the grid's country code.

.. code-block:: python

    from openstef_models.transforms.time_domain import HolidayFeatureAdder

    transform = HolidayFeatureAdder(country_code="NL")
    dataset_holidays = transform.transform(dataset)

----

Load Pattern Features
---------------------

Historical load is often the strongest predictor of future load. The challenge is constructing lag features that respect the forecast horizon: you cannot use a measurement from 30 minutes ago when forecasting 4 hours ahead.

**Lag features**

``LagsAdder`` creates lagged copies of the target variable. It automatically enforces the constraint that each lag must be older than the forecast horizon, so there is no data leakage.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.transforms.time_domain import (
        # LagsAdder is in the time_domain subpackage
    )
    from openstef_models.transforms.time_domain.lags_adder import (
        LagsAdder,
        generate_minute_lags,
        generate_day_lags,
        generate_autocorr_lags,
    )

    # Minute-resolution lags (e.g. t-15min, t-30min, ...) up to the horizon
    minute_lags = generate_minute_lags(max_horizon=timedelta(hours=24))

    # Day-resolution lags (t-1day, t-2day, t-7day, ...)
    day_lags = generate_day_lags(max_horizon=timedelta(hours=24), max_day_lags=7)

    transform = LagsAdder(
        lags=minute_lags + day_lags,
        horizons=[timedelta(hours=1), timedelta(hours=24)],
    )
    dataset_lagged = transform.transform(dataset)

Three lag generation strategies are available:

- ``generate_minute_lags`` — dense, short-range lags at the data resolution. Captures the immediate trend.
- ``generate_day_lags`` — same time-of-day on previous days. Captures the daily cycle and the weekly pattern (day 7).
- ``generate_autocorr_lags`` — data-driven: finds peaks in the autocorrelation function and generates lags at those offsets. Useful when the dominant periodicity is not obvious.

**Rolling aggregates**

A single lag value is noisy. ``RollingAggregatesAdder`` computes rolling statistics (mean, standard deviation, etc.) over configurable windows and horizons, giving the model a smoothed view of recent load behaviour.

.. code-block:: python

    from openstef_models.transforms.time_domain import RollingAggregatesAdder

    transform = RollingAggregatesAdder(
        feature="load_MW",
        aggregation_functions=["mean", "std"],
        horizons=[timedelta(hours=1), timedelta(hours=24)],
    )
    dataset_rolling = transform.transform(dataset)

.. note:: [VISUALIZATION: Autocorrelation plot of a typical residential load series showing peaks at 24 h and 168 h (one week), illustrating why day-based lags are effective]

----

What Makes a Good Feature for Energy Forecasting
-------------------------------------------------

Not every column that correlates with load belongs in the model. A few principles guide feature selection in OpenSTEF:

**Physical interpretability over correlation mining.** Features derived from physical relationships — irradiance → PV output, temperature → heating load — generalise better across seasons and years than features found by scanning a large dataset for correlations. The energy-domain transforms encode this domain knowledge explicitly.

**Respect the forecast horizon.** A feature is only valid if it would be available at prediction time. Weather forecasts are available days ahead; load measurements are not. ``LagsAdder`` enforces this automatically, but custom features must be checked manually.

**Cyclic encoding for periodic signals.** Raw hour-of-day integers mislead tree models into treating hour 0 and hour 23 as far apart. Always use sine/cosine pairs for periodic quantities.

**Avoid redundancy.** Highly correlated features do not add information but do add noise and slow training. ``EmptyFeatureRemover`` and ``DimensionalityReducer`` (in ``openstef_models.transforms.general``) can prune uninformative columns after the feature adders have run.

**Normalise continuous inputs for linear models.** XGBoost and LightGBM are scale-invariant, but linear models are not. The standard pipeline includes a ``Scaler`` step that standardises all features except the target.

----

Building a Custom Feature Transform
------------------------------------

If your grid has a domain-specific signal — industrial production schedules, tidal levels, local events — you can add it by implementing ``TimeSeriesTransform``.

.. code-block:: python

    from openstef_core.base_model import BaseConfig
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform

    class IndustrialScheduleAdder(BaseConfig, TimeSeriesTransform):
        """Add a binary feature indicating planned industrial production hours."""

        schedule_column: str = "industrial_schedule"

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            df = data.data.copy()
            # Mark hours 06:00–22:00 on weekdays as production hours
            hour = df.index.hour
            weekday = df.index.weekday
            df["is_production_hour"] = (
                (hour >= 6) & (hour < 22) & (weekday < 5)
            ).astype(int)
            return TimeSeriesDataset(df, data.horizon)

        def features_added(self) -> list[str]:
            return ["is_production_hour"]

Drop this transform into the pipeline list alongside the built-in adders. Because all transforms share the same interface, the pipeline does not need to know whether a step is built-in or custom.

.. note::

    ``features_added()`` is used by downstream steps (such as ``EmptyFeatureRemover``) to know which columns were introduced by each transform. Always implement it accurately.

----

Putting It Together
-------------------

A realistic feature pipeline for an XGBoost model on a Dutch distribution grid might look like this:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.transforms.energy_domain import (
        WindPowerFeatureAdder,
        AtmosphereDerivedFeaturesAdder,
        RadiationDerivedFeaturesAdder,
    )
    from openstef_models.transforms.time_domain import (
        CyclicFeaturesAdder,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        RollingAggregatesAdder,
    )
    from openstef_models.transforms.time_domain.lags_adder import (
        LagsAdder,
        generate_minute_lags,
        generate_day_lags,
    )

    horizons = [timedelta(hours=1), timedelta(hours=24)]

    feature_pipeline = [
        # Weather
        RadiationDerivedFeaturesAdder(
            coordinate=(52.37, 4.90),
            radiation_column="radiation_W_m2",
        ),
        WindPowerFeatureAdder(windspeed_reference_column="wind_speed_m_s"),
        AtmosphereDerivedFeaturesAdder(
            pressure_column="pressure_hPa",
            relative_humidity_column="humidity_pct",
            temperature_column="temperature_C",
        ),
        # Time
        CyclicFeaturesAdder(),
        DatetimeFeaturesAdder(onehot_encode=False),
        HolidayFeatureAdder(country_code="NL"),
        # Load history
        LagsAdder(
            lags=generate_minute_lags(timedelta(hours=24))
                 + generate_day_lags(timedelta(hours=24), max_day_lags=7),
            horizons=horizons,
        ),
        RollingAggregatesAdder(
            feature="load_MW",
            aggregation_functions=["mean", "std"],
            horizons=horizons,
        ),
    ]

Each step receives a ``TimeSeriesDataset`` and returns an enriched one. The pipeline is stateless at transform time (fitting, where needed, happens in a separate ``fit`` call), so the same object can be used for both training and inference.

----

Related Topics
--------------

- :doc:`forecasting_basics` — how OpenSTEF turns these features into a probabilistic forecast
- :doc:`quantiles_and_confidence` — how uncertainty is represented in the model output
- :doc:`component_splitting` — decomposing aggregate load into solar, wind, and base-load components, each with its own feature requirements
- :doc:`reliability_and_fallback` — what happens when weather inputs are missing at inference time