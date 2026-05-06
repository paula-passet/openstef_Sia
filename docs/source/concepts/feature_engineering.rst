Feature Engineering for Energy Forecasting
==========================================

Good features are the foundation of accurate energy forecasts. OpenSTEF's classical ML models — XGBoost,
LightGBM, and linear variants — rely on hand-crafted, domain-aware features rather than raw inputs alone.
This page explains the categories of features that matter most for short-term energy forecasting and shows
how to work with OpenSTEF's built-in transforms.

Feature engineering in OpenSTEF is organised into four domains, each implemented as a subpackage of
``openstef_models.transforms``:

- **time_domain** — cyclic encodings, datetime components, holidays, rolling aggregates
- **weather_domain** — radiation and atmosphere derived features, daylight
- **energy_domain** — wind power estimates, PV generation proxies
- **general** — scaling, outlier handling, dimensionality reduction, sample weighting

Every transform follows the same interface: it accepts a ``TimeSeriesDataset`` and returns an augmented
one, making transforms composable into preprocessing pipelines.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

Why Features Matter for Energy Forecasting
-------------------------------------------

Energy consumption is driven by a small number of well-understood physical and social mechanisms:
temperature determines heating and cooling demand, solar irradiance drives PV generation, and human
schedules create repeating weekly and daily patterns. A model that receives raw timestamps and raw weather
values must discover these relationships from data alone. Encoding them explicitly — as sine/cosine
cycles, as derived irradiance angles, as holiday flags — gives the model a head start and makes it far
more data-efficient.

This is especially important at low aggregation levels (individual substations, single customers) where
the signal-to-noise ratio is low and training data is limited. Well-chosen features act as regularisation:
they constrain the model to solutions that respect physical reality.


Time Features
-------------

Time features capture the repeating social and operational rhythms that dominate electricity demand.

**Cyclic encoding** is the most important time feature. Hour-of-day, day-of-week, and month-of-year are
all periodic: hour 23 is close to hour 0, not far from it. Encoding them as raw integers misleads
tree-based models. ``CyclicFeaturesAdder`` converts each periodic dimension into a sine/cosine pair,
preserving the circular distance relationship.

.. code-block:: python

    from openstef_models.transforms.time_domain import CyclicFeaturesAdder

    adder = CyclicFeaturesAdder()
    dataset = adder.transform(dataset)
    print(adder.features_added())
    # ['hour_sin', 'hour_cos', 'dayofweek_sin', 'dayofweek_cos', ...]

**Datetime components** such as hour, day-of-week, month, and quarter are also useful as raw integers
when the model can exploit monotonic relationships (e.g., summer months have higher cooling load).
``DatetimeFeaturesAdder`` adds these alongside optional one-hot encoding.

.. code-block:: python

    from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

    adder = DatetimeFeaturesAdder(onehot_encode=False)
    dataset = adder.transform(dataset)

**Holidays** break the normal weekly pattern. A public holiday on a Tuesday looks nothing like a regular
Tuesday. ``HolidayFeatureAdder`` adds a binary holiday indicator using a configurable country code, so
the model can learn holiday-specific load profiles.

.. code-block:: python

    from openstef_models.transforms.time_domain import HolidayFeatureAdder

    adder = HolidayFeatureAdder(country_code="NL")
    dataset = adder.transform(dataset)

.. note::

    Holiday calendars are configurable per location. If you are forecasting outside the Netherlands,
    pass the appropriate ISO 3166-1 alpha-2 country code.


Weather Features
----------------

Weather is the dominant driver of short-term load variability. OpenSTEF provides two layers of weather
features: raw measurements (temperature, wind speed, radiation, pressure, humidity) and derived features
that encode the physical relationship between weather and energy.

**Radiation-derived features** go beyond raw global horizontal irradiance. ``RadiationDerivedFeaturesAdder``
computes quantities such as the solar elevation angle and clear-sky irradiance based on the site's
geographic coordinates and the timestamp. These derived values are more directly related to PV output
than raw radiation alone.

.. code-block:: python

    from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder

    adder = RadiationDerivedFeaturesAdder(
        coordinate=(52.37, 4.90),   # latitude, longitude
        radiation_column="radiation",
    )
    dataset = adder.transform(dataset)

**Atmosphere-derived features** combine temperature, pressure, and relative humidity into indices that
correlate with heating and cooling demand more directly than the raw measurements.

.. code-block:: python

    from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder

    adder = AtmosphereDerivedFeaturesAdder(
        pressure_column="pressure",
        relative_humidity_column="humidity",
        temperature_column="temperature",
    )
    dataset = adder.transform(dataset)

**Daylight features** encode whether it is currently daylight at the forecast location. This is a strong
binary signal for PV-heavy grids: generation is structurally zero at night regardless of cloud cover.

.. code-block:: python

    from openstef_models.transforms.weather_domain import DaylightFeatureAdder

    adder = DaylightFeatureAdder(coordinate=(52.37, 4.90))
    dataset = adder.transform(dataset)

.. note:: [VISUALIZATION: Scatter plot of radiation_derived features vs. raw irradiance, coloured by solar elevation angle, showing the improved correlation with PV output]


Load Pattern Features
---------------------

Historical load measurements, when available, are among the most predictive features. The load at a
substation 48 hours ago is a strong predictor of the load now, because the same weekly schedule repeats.
``RollingAggregatesAdder`` computes rolling statistics (mean, standard deviation, maximum) of the target
variable over configurable windows and forecast horizons.

.. code-block:: python

    from openstef_models.transforms.time_domain import RollingAggregatesAdder

    adder = RollingAggregatesAdder(
        feature="load_mw",
        aggregation_functions=["mean", "std", "max"],
        horizons=[24, 48, 168],   # hours: yesterday, two days ago, last week
    )
    dataset = adder.transform(dataset)

The ``horizons`` parameter aligns the rolling window with the forecast horizon so that the model never
sees future values during training. This is critical: a rolling mean computed without horizon alignment
will leak future information and produce optimistic training metrics that do not generalise.

.. warning::

    Always specify ``horizons`` to match your forecast horizon. Rolling features computed without
    horizon alignment cause data leakage and will overfit.

At highly aggregated grid points (transport forecasts, grid losses), temporal patterns dominate and
rolling load features often contribute more predictive power than weather inputs. At low aggregation
levels (individual customers), the opposite is true — individual behaviour is noisy and weather effects
are relatively stronger.


Energy-Domain Features
-----------------------

The ``energy_domain`` subpackage contains transforms that encode physical knowledge about generation
technologies directly as features.

**Wind power features** convert wind speed measurements into an estimated wind power output using a
power curve approximation. Raw wind speed has a non-linear relationship with turbine output (roughly
cubic in the operating range), and encoding this relationship explicitly improves model accuracy on
grids with significant wind generation.

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    adder = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_ms")
    dataset = adder.transform(dataset)
    print(adder.features_added())
    # ['wind_power_estimate']

These domain-derived features are particularly valuable when training data is limited: the model does
not need to learn the power curve from scratch — it is already encoded in the feature.


Composing a Full Feature Pipeline
----------------------------------

In practice, transforms are composed in sequence. The order matters: validation and alignment should
come first, then feature addition, then standardisation. The following example mirrors the structure
used in OpenSTEF's built-in XGBoost preset.

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from openstef_models.transforms.weather_domain import (
        AtmosphereDerivedFeaturesAdder,
        DaylightFeatureAdder,
        RadiationDerivedFeaturesAdder,
    )
    from openstef_models.transforms.time_domain import (
        CyclicFeaturesAdder,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        RollingAggregatesAdder,
    )
    from openstef_models.transforms.general import OutlierHandler, Scaler

    coordinate = (52.37, 4.90)

    feature_pipeline = [
        # Physical / weather-derived features
        WindPowerFeatureAdder(windspeed_reference_column="wind_speed_ms"),
        AtmosphereDerivedFeaturesAdder(
            pressure_column="pressure",
            relative_humidity_column="humidity",
            temperature_column="temperature",
        ),
        RadiationDerivedFeaturesAdder(
            coordinate=coordinate,
            radiation_column="radiation",
        ),
        # Time features
        CyclicFeaturesAdder(),
        DaylightFeatureAdder(coordinate=coordinate),
        HolidayFeatureAdder(country_code="NL"),
        DatetimeFeaturesAdder(onehot_encode=False),
        # Historical load patterns
        RollingAggregatesAdder(
            feature="load_mw",
            aggregation_functions=["mean", "std"],
            horizons=[24, 48, 168],
        ),
        # Standardisation
        OutlierHandler(mode="standard"),
        Scaler(method="standard"),
    ]

    for transform in feature_pipeline:
        dataset = transform.transform(dataset)

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_2.mmd

What Makes a Good Feature
--------------------------

A few practical principles guide feature selection for energy forecasting:

- **Physical interpretability.** If you cannot explain why a feature should correlate with load, it
  probably will not generalise. Prefer features grounded in physical or social mechanisms.
- **Availability at forecast time.** A feature is only useful if it is available when you need to make
  a prediction. Weather forecasts are available; actual future measurements are not. Rolling aggregates
  must be horizon-aligned for the same reason.
- **Stability across seasons.** Features that work well in summer but not winter (or vice versa) add
  noise. Cyclic encodings and solar-angle-based radiation features are inherently seasonal and stable.
- **Low redundancy.** Highly correlated features do not add information and can slow training. The
  ``DimensionalityReducer`` transform in ``openstef_models.transforms.general`` can remove redundant
  features automatically.

The combination of classical ML models with carefully engineered, domain-specific features is the core
of OpenSTEF's forecasting approach. Deep learning modules that learn representations end-to-end are in
development, but for most operational use cases the feature-engineering approach remains competitive and
far more interpretable.


Related Topics
--------------

- :doc:`forecasting_basics` — how short-term forecasting works and what inputs it requires
- :doc:`component_splitting` — decomposing aggregate load into solar, wind, and residual components,
  each of which benefits from its own feature set
- :doc:`quantiles_and_confidence` — how features feed into probabilistic forecast outputs
- :doc:`reliability_and_fallback` — what happens when weather inputs are missing or delayed