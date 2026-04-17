Feature Engineering
===================

Good forecasts depend on good features. Raw time series data — a sequence of load measurements and weather observations — rarely tells a model everything it needs to know. Feature engineering bridges the gap between raw inputs and the patterns a model can learn: it encodes domain knowledge about *why* electricity demand behaves the way it does.

This page explains the feature categories OpenSTEF uses, the transforms that produce them, and how to compose or extend them for your own use case.

.. note::

   This page focuses on *what* features are and *why* they matter. For the broader forecasting workflow that uses them, see :doc:`forecasting_basics`. For how features interact with probabilistic outputs, see :doc:`quantiles_and_confidence`.


Why Features Matter for Energy Forecasting
-------------------------------------------

Energy demand is driven by human behaviour and physical processes, both of which are highly structured in time. A factory runs on a schedule. Solar panels respond to irradiance. Heat pumps switch on when temperatures drop. Classical ML models — XGBoost, LightGBM, linear regression — cannot discover these structures from a raw timestamp alone. Feature engineering makes the structure explicit, so the model can learn it efficiently from limited data.

OpenSTEF organises its feature transforms into four broad families, each targeting a different driver of load:

- **Time-domain features** — encode calendar and cyclic patterns
- **Weather-domain features** — encode meteorological drivers
- **Energy-domain features** — encode load history and derived quantities
- **Validation and standardisation transforms** — clean and scale the feature matrix before training

All transforms implement the ``TimeSeriesTransform`` interface from ``openstef_core`` and can be composed into a ``FeaturePipeline``.


Time-Domain Features
--------------------

Electricity demand follows strong cyclic rhythms: hour of day, day of week, month of year. Encoding these rhythms correctly is one of the highest-leverage things you can do for forecast accuracy.

Cyclic encoding
^^^^^^^^^^^^^^^

A naive integer encoding of hour (0–23) implies that hour 23 and hour 0 are far apart, when in reality they are adjacent. ``CyclicFeaturesAdder`` solves this by projecting each cyclic quantity onto a unit circle using sine and cosine:

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder

   adder = CyclicFeaturesAdder()
   dataset = adder.transform(dataset)
   # Adds columns such as hour_sin, hour_cos, dayofweek_sin, dayofweek_cos,
   # month_sin, month_cos, etc.

The resulting pairs of columns give the model a smooth, distance-preserving representation of time that generalises well across period boundaries.

Raw datetime features
^^^^^^^^^^^^^^^^^^^^^

When you need interpretable integer features — for example, to inspect feature importances or to use a model that handles ordinal encodings well — ``DatetimeFeaturesAdder`` extracts the raw components:

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

   adder = DatetimeFeaturesAdder(onehot_encode=False)
   dataset = adder.transform(dataset)
   # Adds: hour, dayofweek, month, quarter, year, ...

Set ``onehot_encode=True`` to get binary indicator columns instead, which can help linear models.

Holiday features
^^^^^^^^^^^^^^^^

Public holidays break the normal weekly pattern: a Tuesday that falls on a national holiday looks nothing like a regular Tuesday. ``HolidayFeatureAdder`` adds a binary indicator column for each named holiday in the target country:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder
   from pydantic_extra_types.country import CountryAlpha2

   adder = HolidayFeatureAdder(country_code=CountryAlpha2("NL"))
   dataset = adder.transform(dataset)
   # Adds one column per holiday, e.g. christmas_day, kings_day, ...

Holiday names are sanitised into valid Python identifiers so they can be used directly as column names.

Daylight features
^^^^^^^^^^^^^^^^^

Sunrise and sunset times shift throughout the year and vary with latitude. ``DaylightFeatureAdder`` computes the fraction of daylight at each timestamp given the geographic coordinate of the grid point, providing a smooth proxy for solar-driven load patterns without requiring measured irradiance:

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder
   from openstef_core.types import Coordinate

   adder = DaylightFeatureAdder(coordinate=Coordinate(lat=52.37, lon=4.90))
   dataset = adder.transform(dataset)


Weather-Domain Features
-----------------------

Weather is the dominant external driver of short-term load. OpenSTEF provides several transforms that go beyond passing raw meteorological columns straight to the model.

Wind power
^^^^^^^^^^

Wind turbine output is a non-linear function of wind speed, following a characteristic power curve with a cubic region, a rated-power plateau, and cut-in/cut-out thresholds. ``WindPowerFeatureAdder`` encodes this relationship so the model does not have to learn it from scratch:

.. code-block:: python

   from openstef_models.transforms.weather_domain import WindPowerFeatureAdder

   adder = WindPowerFeatureAdder(windspeed_reference_column="wind_speed")
   dataset = adder.transform(dataset)

Radiation and PV generation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Solar irradiance drives photovoltaic generation, but the relationship depends on panel orientation, shading, and the sun's position in the sky. ``RadiationDerivedFeaturesAdder`` combines the raw radiation measurement with the computed solar elevation angle for the grid point's location to produce features that better represent actual PV output:

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
   from openstef_core.types import Coordinate

   adder = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(lat=52.37, lon=4.90),
       radiation_column="global_radiation",
   )
   dataset = adder.transform(dataset)

Atmospheric features
^^^^^^^^^^^^^^^^^^^^

Temperature, relative humidity, and pressure interact in ways that affect both human comfort (and therefore heating/cooling demand) and equipment efficiency. ``AtmosphereDerivedFeaturesAdder`` computes derived quantities such as apparent temperature and dew point from these three inputs:

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder

   adder = AtmosphereDerivedFeaturesAdder(
       temperature_column="temperature",
       relative_humidity_column="humidity",
       pressure_column="pressure",
   )
   dataset = adder.transform(dataset)

.. note:: [DIAGRAM: Data flow from raw weather inputs (temperature, humidity, pressure, wind speed, radiation) through weather-domain transforms to derived feature columns consumed by the model]


Energy-Domain Features: Load History
--------------------------------------

Past load is one of the strongest predictors of future load. A grid point that was heavily loaded yesterday afternoon is likely to be heavily loaded again tomorrow afternoon. OpenSTEF captures this through two complementary mechanisms.

Lag features
^^^^^^^^^^^^

``LagsAdder`` creates copies of the target variable shifted back in time. The valid lags depend on the forecast horizon: you cannot use a lag that would require data from the future. OpenSTEF handles this automatically — for each horizon, only lags that are genuinely available at prediction time are included:

.. code-block:: python

   from openstef_models.transforms.time_domain import LagsAdder
   from datetime import timedelta

   adder = LagsAdder(
       target_column="load_mw",
       horizons=[timedelta(hours=1), timedelta(hours=24)],
       history_available=timedelta(days=14),
       add_trivial_lags=True,
   )
   dataset = adder.transform(dataset)

With ``add_trivial_lags=True``, the adder automatically includes lags at round intervals (15 min, 30 min, 1 h, 1 day, 1 week, etc.) that are known to carry high autocorrelation for energy data.

Rolling aggregates
^^^^^^^^^^^^^^^^^^

Single-point lags can be noisy. Rolling aggregates smooth over short-term fluctuations and expose medium-term trends. ``RollingAggregatesAdder`` computes statistics such as mean, standard deviation, and maximum over configurable windows:

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   adder = RollingAggregatesAdder(
       feature="load_mw",
       aggregation_functions=["mean", "std", "max"],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )
   dataset = adder.transform(dataset)

Rolling aggregates are particularly useful for capturing demand trends over the past few hours or the same period on previous days.


Composing a Feature Pipeline
-----------------------------

In practice you combine multiple transforms into a single pipeline. The ``FeaturePipeline`` applies them in order, passing the ``TimeSeriesDataset`` through each step:

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from openstef_models.transforms.general import EmptyFeatureRemover
   from openstef_core.types import Coordinate
   from pydantic_extra_types.country import CountryAlpha2
   from datetime import timedelta

   coordinate = Coordinate(lat=52.37, lon=4.90)

   feature_adders = [
       LagsAdder(
           target_column="load_mw",
           horizons=[timedelta(hours=1), timedelta(hours=24)],
           history_available=timedelta(days=14),
           add_trivial_lags=True,
       ),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           temperature_column="temperature",
           relative_humidity_column="humidity",
           pressure_column="pressure",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=coordinate,
           radiation_column="global_radiation",
       ),
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=coordinate),
       RollingAggregatesAdder(
           feature="load_mw",
           aggregation_functions=["mean", "std"],
           horizons=[timedelta(hours=1), timedelta(hours=24)],
       ),
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
       DatetimeFeaturesAdder(onehot_encode=False),
       EmptyFeatureRemover(),
   ]

   for transform in feature_adders:
       dataset = transform.transform(dataset)

``EmptyFeatureRemover`` drops any columns that are entirely NaN — a common occurrence when a weather feed is missing a variable — so the model never trains on uninformative inputs.

.. note:: [DIAGRAM: Sequential pipeline showing each transform step, the columns it adds, and the resulting feature matrix shape at each stage]


Adding Custom Features
-----------------------

If you have domain-specific signals — energy prices, industrial production schedules, grid topology indicators — you can inject them as additional columns in the ``TimeSeriesDataset`` before the pipeline runs, or implement a custom transform by subclassing ``TimeSeriesTransform``:

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd

   class IndustrialScheduleAdder(TimeSeriesTransform):
       """Add a binary feature indicating planned industrial activity."""

       schedule: pd.Series  # injected at construction time

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           data.dataframe["industrial_active"] = (
               self.schedule.reindex(data.dataframe.index, fill_value=0)
           )
           return data

       def features_added(self) -> list[str]:
           return ["industrial_active"]

Insert your custom transform at the appropriate position in the pipeline list. Because every transform receives and returns a ``TimeSeriesDataset``, custom and built-in transforms compose without friction.

For use cases that require a fully custom workflow — for example, a different model architecture or a non-standard preprocessing sequence — see ``CustomForecastingWorkflow`` in ``openstef_models.workflows``.


What Makes a Good Feature
--------------------------

A few practical principles guide feature selection for energy forecasting:

- **Causal plausibility.** Prefer features that have a physical or behavioural reason to influence load. Spurious correlations in training data rarely generalise.
- **Availability at prediction time.** A feature is only useful if it will be available when you need to make a forecast. Weather *forecasts* are available; weather *measurements* may not be. Lag features must respect the forecast horizon (``LagsAdder`` enforces this automatically).
- **Smooth encoding of cyclic quantities.** Use sine/cosine pairs rather than raw integers for hour, day-of-week, and month. This prevents artificial discontinuities at period boundaries.
- **Interaction terms via domain knowledge.** Rather than letting the model discover that radiation × solar elevation predicts PV output, encode it explicitly. Classical ML models benefit greatly from pre-computed interaction features.
- **Sparse holiday indicators.** One binary column per holiday is more informative than a single ``is_holiday`` flag, because different holidays have different load profiles.

.. note::

   Feature importance scores from tree-based models (available via OpenSTEF's explainability utilities) are a useful diagnostic for identifying which features are actually contributing. If a feature consistently scores near zero across multiple training runs, it is a candidate for removal.


Related Topics
--------------

- :doc:`forecasting_basics` — how features feed into the training and prediction workflow
- :doc:`quantiles_and_confidence` — how the feature matrix is used to produce probabilistic forecasts
- :doc:`component_splitting` — decomposing aggregate load into components, each of which may benefit from its own feature set
- :doc:`meta_ensembles` — how the meta-ensemble layer combines forecasts that may use different feature configurations