Feature Engineering for Energy Forecasting
==========================================

Good forecasting models are only as good as the features they learn from. For energy load forecasting, raw measurements alone rarely capture the full picture — a model needs to understand that Tuesday at 08:00 in January behaves differently from Tuesday at 08:00 in July, that a public holiday suppresses industrial demand, and that yesterday's peak load is a strong hint about today's. This page explains the feature categories OpenSTEF uses, why each matters, and how to compose them in your own pipelines.

For background on what short-term forecasting is and why it is needed, see :doc:`forecasting_basics`. For how uncertainty is expressed in forecasts, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

Why Feature Engineering Matters for Energy
-------------------------------------------

Energy demand is driven by a small number of well-understood physical and social processes: temperature determines heating and cooling loads, daylight hours govern solar generation and lighting demand, weekly work rhythms shape industrial consumption, and recent load history carries inertia from ongoing processes. Classical ML models — XGBoost, LightGBM, linear regression — cannot discover these relationships on their own from a raw timestamp and a watt reading. Encoding domain knowledge as explicit features is what lets a gradient-boosted tree match or exceed deep-learning approaches on typical grid-operator datasets.

OpenSTEF organises its feature transforms into three broad families:

- **Time-domain features** — derived purely from the datetime index (cyclic encodings, calendar flags, holidays)
- **Energy-domain features** — derived from physical measurements (weather, wind speed, radiation)
- **Lag and rolling features** — derived from the target variable's own history

Each family is a collection of ``TimeSeriesTransform`` objects that can be composed into a preprocessing pipeline.

Time-Domain Features
--------------------

Datetime and cyclic encodings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A raw hour-of-day integer (0–23) tells a tree model nothing about the fact that hour 23 and hour 0 are adjacent. ``CyclicFeaturesAdder`` solves this by encoding periodic quantities as sine/cosine pairs, so the model sees a smooth, continuous representation of time.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.time_domain import CyclicFeaturesAdder

    data = pd.DataFrame(
        {"load": [100, 120, 110, 95, 130]},
        index=pd.date_range("2025-06-02 06:00", periods=5, freq="1h"),
    )
    dataset = TimeSeriesDataset(data, horizon=timedelta(hours=1))

    transform = CyclicFeaturesAdder(
        included_features=["time_of_day", "season", "day_of_week", "month"]
    )
    result = transform.transform(dataset)
    print(result.data.filter(like="sine").head())

The default set of cyclic features covers ``time_of_day``, ``season``, ``day_of_week``, and ``month``. Each produces a ``_sine`` and ``_cosine`` column. You can restrict the set by passing a subset to ``included_features``.

``DatetimeFeaturesAdder`` complements this with plain integer or one-hot encoded calendar fields (year, month, day, weekday) for models that benefit from explicit categorical splits.

Holiday features
^^^^^^^^^^^^^^^^

Public holidays cause load profiles that look nothing like a normal weekday or weekend. ``HolidayFeatureAdder`` adds a binary flag using a country-specific holiday calendar.

.. code-block:: python

    from openstef_models.transforms.time_domain import HolidayFeatureAdder

    holiday_transform = HolidayFeatureAdder(country_code="NL")
    result = holiday_transform.transform(dataset)

Pass the ISO 3166-1 alpha-2 country code for the grid region you are forecasting. The flag is particularly important for industrial substations where a national holiday can cut demand by 40 % or more.

Daylight features
^^^^^^^^^^^^^^^^^

Sunrise and sunset times shift throughout the year and vary with geographic location. ``DaylightFeatureAdder`` computes daylight duration and solar elevation angle from the dataset's coordinate, giving the model a physically grounded signal for lighting and solar-driven load.

.. code-block:: python

    from openstef_models.transforms.energy_domain import DaylightFeatureAdder
    from openstef_core.types import Coordinate

    daylight_transform = DaylightFeatureAdder(
        coordinate=Coordinate(lat=52.37, lon=4.90)  # Amsterdam
    )
    result = daylight_transform.transform(dataset)

Energy-Domain Features
-----------------------

Weather inputs are the single most powerful external signal for load forecasting. OpenSTEF provides dedicated transforms for each physical quantity rather than expecting you to hand-craft them.

Wind power
^^^^^^^^^^

Wind turbine output follows a non-linear power curve: below cut-in speed the turbine is idle, between cut-in and rated speed output scales roughly with the cube of wind speed, and above rated speed output is capped. ``WindPowerFeatureAdder`` applies this transformation so the model receives a physically meaningful signal instead of raw wind speed.

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    wind_transform = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_10m")
    result = wind_transform.transform(dataset)

Radiation and solar estimates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Solar irradiance drives both PV generation and cooling demand. ``RadiationDerivedFeaturesAdder`` combines measured radiation with the location's solar geometry to produce features such as clear-sky index and estimated PV output.

.. code-block:: python

    from openstef_models.transforms.energy_domain import RadiationDerivedFeaturesAdder
    from openstef_core.types import Coordinate

    radiation_transform = RadiationDerivedFeaturesAdder(
        coordinate=Coordinate(lat=52.37, lon=4.90),
        radiation_column="ghi",
    )
    result = radiation_transform.transform(dataset)

Atmospheric features
^^^^^^^^^^^^^^^^^^^^^

Temperature, pressure, and relative humidity interact in ways that affect both demand (heat pumps, air conditioning) and generation (gas turbine efficiency). ``AtmosphereDerivedFeaturesAdder`` computes derived quantities such as apparent temperature (heat index / wind chill) and dew point from these raw inputs.

.. code-block:: python

    from openstef_models.transforms.energy_domain import AtmosphereDerivedFeaturesAdder

    atm_transform = AtmosphereDerivedFeaturesAdder(
        pressure_column="pressure_hpa",
        relative_humidity_column="rh_pct",
        temperature_column="temp_c",
    )
    result = atm_transform.transform(dataset)

.. note:: [VISUALIZATION: Scatter plot of apparent temperature vs. load residuals showing the improvement in explained variance compared to using raw temperature alone]

Lag and Rolling Features
-------------------------

The load at time *t* is correlated with the load at *t − 15 min*, *t − 1 h*, *t − 24 h*, and *t − 7 days*. Lag features make these correlations explicit and are often the most predictive features in a short-term model.

Lag features
^^^^^^^^^^^^

``LagsAdder`` creates lagged copies of the target column. Three strategies are available:

- **Minute lags** — fine-grained lags within the first few hours, useful for very short horizons
- **Day lags** — lags at 24 h, 48 h, 7 days, etc., capturing daily and weekly periodicity
- **Autocorrelation lags** — data-driven: the transform analyses the autocorrelation function of the training series and selects lags at significant peaks

.. code-block:: python

    from datetime import timedelta
    from openstef_models.transforms.time_domain.lags_adder import (
        LagsAdder,
        generate_minute_lags,
        generate_day_lags,
    )

    horizons = [timedelta(hours=1), timedelta(hours=24)]

    # Combine minute-resolution and daily lags
    minute_lags = generate_minute_lags(max_horizon=timedelta(hours=24))
    day_lags = generate_day_lags(max_horizon=timedelta(hours=24), max_day_lags=7)

    lag_transform = LagsAdder(
        lags=minute_lags + day_lags,
        horizons=horizons,
    )
    result = lag_transform.fit(dataset).transform(dataset)

``LagsAdder`` is horizon-aware: it will not include a lag that would require data from the future relative to the forecast horizon. This prevents data leakage without any manual bookkeeping on your part.

For versioned datasets — where each row records the state of the world as it was known at a specific issue time — use ``VersionedLagsAdder`` from ``openstef_models.transforms.time_domain.versioned_lags_adder`` instead. It applies the same logic while respecting the availability constraints encoded in the versioned dataset.

Rolling aggregates
^^^^^^^^^^^^^^^^^^

Where lag features capture a single past value, rolling aggregates summarise recent behaviour over a window. ``RollingAggregatesAdder`` computes statistics such as mean, standard deviation, and maximum over configurable windows and horizons.

.. code-block:: python

    from openstef_models.transforms.time_domain import RollingAggregatesAdder

    rolling_transform = RollingAggregatesAdder(
        feature="load",
        aggregation_functions=["mean", "std", "max"],
        horizons=horizons,
    )
    rolling_transform.fit(dataset)
    result = rolling_transform.transform(dataset)

Rolling standard deviation is particularly useful as a proxy for load volatility — high volatility periods (storms, heatwaves) warrant wider confidence intervals. See :doc:`quantiles_and_confidence` for how uncertainty estimates are produced from the model output.

Composing a Full Feature Pipeline
-----------------------------------

In practice you chain all relevant transforms into a single preprocessing pipeline. The order matters: weather-derived features should be added before standardisation, and lag features should come after the target column is confirmed present.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.types import Coordinate
    from openstef_models.transforms.time_domain import (
        CyclicFeaturesAdder,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        RollingAggregatesAdder,
    )
    from openstef_models.transforms.energy_domain import (
        WindPowerFeatureAdder,
        AtmosphereDerivedFeaturesAdder,
        RadiationDerivedFeaturesAdder,
        DaylightFeatureAdder,
    )
    from openstef_models.transforms.time_domain.lags_adder import (
        LagsAdder,
        generate_minute_lags,
        generate_day_lags,
    )

    coordinate = Coordinate(lat=52.37, lon=4.90)
    horizons = [timedelta(hours=1), timedelta(hours=24)]

    pipeline = [
        # Weather-derived features
        WindPowerFeatureAdder(windspeed_reference_column="wind_speed_10m"),
        AtmosphereDerivedFeaturesAdder(
            pressure_column="pressure_hpa",
            relative_humidity_column="rh_pct",
            temperature_column="temp_c",
        ),
        RadiationDerivedFeaturesAdder(coordinate=coordinate, radiation_column="ghi"),
        # Time-domain features
        CyclicFeaturesAdder(),
        DaylightFeatureAdder(coordinate=coordinate),
        HolidayFeatureAdder(country_code="NL"),
        DatetimeFeaturesAdder(onehot_encode=False),
        # Lag and rolling features
        LagsAdder(
            lags=generate_minute_lags(timedelta(hours=24))
                 + generate_day_lags(timedelta(hours=24), max_day_lags=7),
            horizons=horizons,
        ),
        RollingAggregatesAdder(
            feature="load",
            aggregation_functions=["mean", "std"],
            horizons=horizons,
        ),
    ]

    # Apply sequentially
    current = dataset
    for transform in pipeline:
        if hasattr(transform, "fit"):
            transform.fit(current)
        current = transform.transform(current)

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_2.mmd

What Makes a Good Feature
---------------------------

A few practical rules of thumb for energy forecasting:

- **Causal availability** — a feature must be available at prediction time. Weather *forecasts* are available; yesterday's actual load is available; tomorrow's actual load is not. ``LagsAdder`` enforces this automatically, but custom features require manual care.
- **Physical interpretability** — prefer features grounded in physics (apparent temperature, clear-sky index) over purely statistical constructs. They generalise better across seasons and years.
- **Avoid redundancy** — highly correlated features (e.g., raw temperature and apparent temperature together) can slow training and inflate feature importance scores without improving accuracy. ``DimensionalityReducer`` from ``openstef_models.transforms.general`` can help prune redundant columns.
- **Horizon specificity** — a 15-minute-ahead model benefits from fine-grained minute lags; a 48-hour-ahead model benefits more from day-of-week and seasonal features. Tailor the lag strategy to your forecast horizon.
- **Holiday granularity** — not all holidays are equal. A bridge day between a public holiday and a weekend behaves differently from the holiday itself. Consider adding a ``days_to_next_holiday`` feature for substations with strong industrial load.

.. note::

   When a weather input column is missing at inference time, the energy-domain transforms will propagate ``NaN`` values rather than silently dropping rows. Pair your feature pipeline with a fallback strategy to handle missing weather data gracefully — see :doc:`reliability_and_fallback` for details.

Related Topics
--------------

- :doc:`forecasting_basics` — what short-term forecasting is and why the 15-minute resolution matters
- :doc:`quantiles_and_confidence` — how the feature matrix feeds into probabilistic output
- :doc:`reliability_and_fallback` — handling missing weather inputs and degraded feature sets in production
- :doc:`component_splitting` — decomposing aggregate load into sub-components, each of which may benefit from its own feature set