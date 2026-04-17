Feature Engineering for Energy Forecasting
==========================================

Good features are the foundation of accurate energy forecasts. OpenSTEF's classical ML models — XGBoost, LightGBM, and linear variants — rely entirely on hand-crafted features rather than learning raw temporal structure from scratch. This page explains the feature categories OpenSTEF uses, why each matters for energy forecasting, and how to configure or extend them.

For background on what the forecasts themselves represent, see :doc:`forecasting_basics`. For how uncertainty is expressed on top of these features, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Feature engineering pipeline — raw inputs (weather, timestamps, historical load) flowing through transform stages into a feature matrix fed to the model]

Why Features Matter for Energy Forecasting
-------------------------------------------

Electricity consumption and generation are driven by a small set of physical and behavioural forces: the sun rises and sets, temperatures change, people follow weekly routines, and industrial loads follow shift patterns. A model that receives raw timestamps and a handful of weather readings cannot easily discover these relationships on its own. Encoding them explicitly — as lag values, cyclic time encodings, irradiance decompositions — gives tree-based models the structured signal they need to generalise well across seasons and forecast horizons.

The principle is simple: **domain knowledge embedded in features replaces model complexity**. A well-engineered feature set lets a gradient-boosted tree match or exceed deep learning approaches on typical grid-point forecasting tasks, while remaining interpretable and fast to retrain.

Weather Features
----------------

Weather is the dominant driver of both demand and renewable generation. OpenSTEF provides three dedicated transforms in ``openstef_models.transforms.weather_domain``.

**Radiation-derived features**

Raw global horizontal irradiance (GHI) is a useful input, but the angle and orientation of a solar installation means that what matters is how much radiation actually hits the panel surface. ``RadiationDerivedFeaturesAdder`` uses the site's geographic coordinates and solar position to decompose GHI into:

- **DNI** — Direct Normal Irradiance, the beam component perpendicular to the sun.
- **GTI** — Global Tilted Irradiance, the total irradiance on a tilted surface.

These derived quantities correlate far more directly with PV output than raw GHI.

.. code-block:: python

   from pydantic_extra_types.coordinate import Coordinate
   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder

   adder = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(latitude=52.1, longitude=5.1),
       radiation_column="ghi",
   )
   dataset = adder.transform(dataset)

**Atmosphere-derived features**

``AtmosphereDerivedFeaturesAdder`` computes meteorological composites from temperature, relative humidity, and pressure. These capture effects such as apparent temperature (how cold it *feels*), which correlates better with heating demand than dry-bulb temperature alone.

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder

   adder = AtmosphereDerivedFeaturesAdder(
       temperature_column="temperature",
       relative_humidity_column="humidity",
       pressure_column="pressure",
   )
   dataset = adder.transform(dataset)

**Daylight features**

``DaylightFeatureAdder`` adds binary and continuous indicators of whether it is currently daylight at the forecast location. This is especially useful as a gating feature: solar generation is structurally zero at night, and a daylight flag lets the model learn that boundary cleanly without relying on the radiation signal alone.

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder

   adder = DaylightFeatureAdder(
       coordinate=Coordinate(latitude=52.1, longitude=5.1),
   )
   dataset = adder.transform(dataset)

**Wind power features**

``WindPowerFeatureAdder`` transforms a wind speed measurement into a wind power proxy using a turbine power curve approximation. Wind speed has a cubic relationship with power output; providing the transformed value directly saves the model from having to learn that non-linearity.

.. code-block:: python

   from openstef_models.transforms.time_domain import WindPowerFeatureAdder

   adder = WindPowerFeatureAdder(windspeed_reference_column="wind_speed")
   dataset = adder.transform(dataset)

Time Features
-------------

Calendar structure is one of the strongest predictors of electricity demand. A Tuesday at 08:00 looks very different from a Sunday at 08:00, and January looks very different from July. OpenSTEF encodes this structure in two ways.

**Cyclic encoding**

Hours of the day, days of the week, and months of the year are *cyclic* — hour 23 is adjacent to hour 0, not far from it. Encoding them as plain integers misleads tree models into treating the boundary as a discontinuity. ``CyclicFeaturesAdder`` applies sine/cosine encoding to produce smooth, periodic representations:

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder

   adder = CyclicFeaturesAdder()
   dataset = adder.transform(dataset)

This produces pairs of features such as ``hour_sin`` / ``hour_cos`` and ``month_sin`` / ``month_cos``, which allow the model to correctly weight the similarity between adjacent time periods.

**Datetime features and holidays**

``DatetimeFeaturesAdder`` extracts a richer set of calendar attributes — day of week, week of year, quarter, and similar — as plain integers or one-hot encoded columns depending on the model type. ``HolidayFeatureAdder`` adds a country-specific public holiday flag, which is critical because holiday load profiles often resemble Sundays even when they fall mid-week.

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder, HolidayFeatureAdder

   dataset = DatetimeFeaturesAdder(onehot_encode=False).transform(dataset)
   dataset = HolidayFeatureAdder(country_code="NL").transform(dataset)

.. note:: [VISUALIZATION: Bar chart comparing average load profiles for weekdays, weekends, and public holidays across a full year, illustrating why holiday encoding matters]

Load Pattern Features
---------------------

Historical load is the single most informative predictor of future load. OpenSTEF captures load history through two complementary mechanisms.

**Lag features**

A lag feature is simply the load value at some fixed time in the past. ``LagsAdder`` generates a structured set of lags automatically, covering three strategies:

- **Minute-based lags** — recent history at the resolution of the time series (e.g., 15, 30, 45 minutes ago), capturing short-term momentum.
- **Day-based lags** — the same time slot on previous days and weeks (e.g., 24 h, 48 h, 168 h ago), capturing daily and weekly periodicity.
- **Autocorrelation-based lags** — peaks in the autocorrelation function of the training signal, used to identify load-specific periodicities automatically.

Lags are horizon-aware: a lag is only included if the corresponding historical observation would genuinely be available at prediction time. This prevents data leakage when training models for longer forecast horizons.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import LagsAdder

   adder = LagsAdder(
       history_available=timedelta(days=14),
       horizons=[timedelta(hours=1), timedelta(hours=24)],
       add_trivial_lags=True,
       target_column="load",
   )
   adder.fit(dataset)
   dataset = adder.transform(dataset)

The ``fit`` step inspects the training data to determine which autocorrelation-based lags are worth adding; ``transform`` then applies the same lag set consistently to new data.

**Rolling aggregates**

Where lags capture point-in-time history, rolling aggregates summarise recent behaviour over a window. ``RollingAggregatesAdder`` computes statistics such as rolling mean and standard deviation over configurable windows and horizons:

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   adder = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std"],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )
   adder.fit(dataset)
   dataset = adder.transform(dataset)

Rolling standard deviation is particularly useful as a volatility signal: periods of high variance in recent load often precede continued volatility, which matters for probabilistic forecasting.

.. note:: [VISUALIZATION: Time series plot showing load signal alongside its 24-hour rolling mean and rolling standard deviation, illustrating what these features capture]

What Makes a Good Feature
--------------------------

Not every signal that correlates with load belongs in the feature matrix. A few practical principles:

**Causal availability at prediction time.** A feature must be knowable when the forecast is made. Weather forecasts are available; actual future load is not. Lag features must respect the forecast horizon — a 1-hour-ahead model cannot use a lag of 30 minutes. OpenSTEF's ``LagsAdder`` enforces this automatically.

**Physical interpretability.** Features grounded in physical processes (irradiance decomposition, apparent temperature, wind power curves) generalise better across seasons and years than purely statistical constructs. When a feature has a clear physical meaning, it is also easier to diagnose when something goes wrong.

**Cyclic encoding for periodic signals.** Raw integer encodings of hours or months introduce artificial discontinuities. Use sine/cosine pairs for any periodic calendar variable.

**Avoid redundancy without pruning too aggressively.** Correlated features are not inherently harmful for tree models, but they can slow training and inflate feature importance scores. ``EmptyFeatureRemover`` is included in the standard pipeline to drop columns that carry no variance after preprocessing.

**Scale appropriately.** Tree-based models are scale-invariant, but linear models and distance-based methods are not. The standard pipeline applies ``Scaler`` (standard scaling) to all features except the target column.

Composing a Full Feature Pipeline
-----------------------------------

In practice, feature transforms are composed in sequence. The order matters: lag features should be added before scaling, and outlier handling should precede feature computation to avoid propagating bad values into derived features.

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.coordinate import Coordinate
   from openstef_models.transforms.time_domain import (
       LagsAdder,
       RollingAggregatesAdder,
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       WindPowerFeatureAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )

   coordinate = Coordinate(latitude=52.1, longitude=5.1)
   horizons = [timedelta(hours=1), timedelta(hours=24)]

   feature_pipeline = [
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           add_trivial_lags=True,
           target_column="load",
       ),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           temperature_column="temperature",
           relative_humidity_column="humidity",
           pressure_column="pressure",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=coordinate,
           radiation_column="ghi",
       ),
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=coordinate),
       RollingAggregatesAdder(
           feature="load",
           aggregation_functions=["mean", "std"],
           horizons=horizons,
       ),
       HolidayFeatureAdder(country_code="NL"),
       DatetimeFeaturesAdder(onehot_encode=False),
   ]

   for transform in feature_pipeline:
       transform.fit(train_dataset)

   for transform in feature_pipeline:
       train_dataset = transform.transform(train_dataset)

.. note::

   When using a built-in workflow such as ``EnsembleForecastingWorkflow``, this pipeline is assembled automatically from the workflow configuration. Manual composition is only needed when building a custom pipeline outside the standard workflow.

.. note:: [DIAGRAM: Ordered sequence of transform stages in the feature pipeline, showing data flow from raw inputs through each adder to the final feature matrix]

Related Topics
--------------

- :doc:`forecasting_basics` — what short-term energy forecasting is and why it requires specialised treatment
- :doc:`quantiles_and_confidence` — how the feature matrix feeds into probabilistic outputs and confidence intervals
- :doc:`component_splitting` — decomposing aggregate load into sub-components, each of which may benefit from its own feature set
- :doc:`reliability_and_fallback` — what happens when feature computation fails or input data is missing