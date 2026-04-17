Feature Engineering
===================

Good forecasting models are only as good as the features they learn from. In energy forecasting, raw inputs — a timestamp and a load measurement — carry surprisingly little signal on their own. The real predictive power comes from derived features that encode physical relationships, human behaviour patterns, and historical load dynamics. This page explains the feature categories that matter most for short-term energy forecasting and shows how OpenSTEF's built-in transforms let you compose them into a preprocessing pipeline.

.. note::

   This page focuses on feature construction. For an introduction to what short-term forecasting is and why it matters, see :doc:`forecasting_basics`. For how uncertainty is represented in the resulting forecasts, see :doc:`quantiles_and_confidence`.


Why Feature Engineering Matters for Energy
-------------------------------------------

Electricity demand is driven by a small number of well-understood forces: the weather, the time of day, the day of the week, and the accumulated habits of the people and machines connected to a grid. Classical ML models — XGBoost, LightGBM, linear regression — cannot discover these relationships from raw timestamps alone. They need features that make the patterns explicit.

OpenSTEF embeds domain knowledge directly into its transform library. Rather than leaving feature construction to the user, the library ships a set of composable ``TimeSeriesTransform`` classes, each responsible for one category of features. You assemble them into a ``TransformPipeline`` and attach that pipeline to your model. The result is a reproducible, serialisable preprocessing stage that travels with the model through training, validation, and inference.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd


Weather Features
----------------

Weather is the dominant external driver of electricity demand. Heating and cooling loads respond directly to temperature; solar generation depends on radiation; wind generation depends on wind speed. OpenSTEF provides three dedicated weather transforms.

**AtmosphereDerivedFeaturesAdder** derives secondary meteorological features from pressure, relative humidity, and temperature. These derived quantities — such as apparent temperature and humidity-adjusted heat indices — often correlate with demand more strongly than the raw measurements alone.

**RadiationDerivedFeaturesAdder** computes solar-geometry-aware radiation features given the geographic coordinate of the grid point. Because the angle of incidence and day length vary with latitude and season, the same radiation value carries different energy implications at different times of year. This transform makes that relationship explicit.

**WindPowerFeatureAdder** converts a wind speed measurement into features suited to wind power estimation, accounting for the non-linear relationship between wind speed and turbine output.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from openstef_models.transforms.weather_domain.daylight_feature_adder import (
       DaylightFeatureAdder,
   )
   from openstef_core.types import Coordinate

   coordinate = Coordinate(lat=52.3, lon=4.9)

   weather_transforms = [
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=coordinate,
           radiation_column="radiation",
       ),
       WindPowerFeatureAdder(
           windspeed_reference_column="wind_speed",
       ),
       DaylightFeatureAdder(
           coordinate=coordinate,
       ),
   ]

``DaylightFeatureAdder`` deserves special mention: it adds a continuous daylight signal derived from the solar position at the given coordinate. This is particularly valuable for distribution grids with significant rooftop solar, where the transition between day and night drives sharp load ramps.

.. note::

   All weather transforms require the corresponding raw columns to be present in the ``TimeSeriesDataset``. If a column is absent, the transform will raise an error at fit time rather than silently producing NaNs.


Time and Calendar Features
---------------------------

Human behaviour is strongly periodic. Demand on a Monday morning looks very different from demand on a Sunday afternoon, and both look different from demand on a public holiday. OpenSTEF captures these patterns through three complementary time-domain transforms.

**CyclicFeaturesAdder** encodes periodic time components — hour of day, day of week, day of year — as sine/cosine pairs. This is important because tree-based models have no notion of periodicity: without cyclic encoding, the model sees hour 23 and hour 0 as maximally distant, when in reality they are adjacent. The sine/cosine representation preserves the circular topology of time.

**DatetimeFeaturesAdder** adds scalar datetime features such as hour, day of week, month, and week of year. These complement the cyclic features and are particularly useful for models that benefit from ordinal representations.

**HolidayFeatureAdder** adds a binary indicator column for each public holiday in the target country. Holidays break the normal weekly pattern and are among the most common sources of large forecast errors when not explicitly modelled.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )
   from pydantic_extra_types.country import CountryAlpha2

   time_transforms = [
       CyclicFeaturesAdder(),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
   ]

``HolidayFeatureAdder`` uses the ``country_code`` to look up the correct public holiday calendar. Each holiday becomes its own binary column, allowing the model to learn that Christmas and Easter have different demand profiles.


Load History and Lag Features
------------------------------

The most powerful predictors of future load are often past load values. A grid point that was heavily loaded an hour ago is likely still heavily loaded; a point that shows a consistent morning peak every weekday will probably show one tomorrow too.

**LagsAdder** generates lag features — copies of the target column shifted back in time by a specified set of intervals. The valid lags for each forecast horizon are computed automatically: a lag that would require future information at inference time is excluded. This prevents data leakage without requiring manual bookkeeping.

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from datetime import timedelta

   lags_transform = LagsAdder(
       history_available=timedelta(days=14),
       horizons=[timedelta(minutes=15), timedelta(hours=1), timedelta(hours=24)],
       add_trivial_lags=True,
       target_column="load",
   )

Setting ``add_trivial_lags=True`` includes the most recent available observation as a feature, which is typically the single strongest predictor for short horizons.

**RollingAggregatesAdder** complements lag features by summarising recent history with statistics such as mean, median, minimum, and maximum over a rolling window. These aggregates smooth out noise and capture trend information that individual lag values may miss.

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from datetime import timedelta

   rolling_transform = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "max"],
       horizons=[timedelta(minutes=15), timedelta(hours=1)],
   )

``RollingAggregatesAdder`` also implements a fallback strategy for inference: if the target column is unavailable (as it will be for future timestamps), it forward-fills from the last computed aggregate rather than producing NaNs that would break the model.


Assembling a Feature Pipeline
------------------------------

Individual transforms become useful when composed into a ``TransformPipeline``. The pipeline applies transforms sequentially, fitting each one on the intermediate output of the previous step. The fitted pipeline is serialised alongside the model, so inference always uses the same preprocessing logic as training.

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.weather_domain.daylight_feature_adder import (
       DaylightFeatureAdder,
   )
   from openstef_core.types import Coordinate
   from pydantic_extra_types.country import CountryAlpha2
   from datetime import timedelta

   coordinate = Coordinate(lat=52.3, lon=4.9)
   horizons = [timedelta(minutes=15), timedelta(hours=1), timedelta(hours=24)]

   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=horizons,
               add_trivial_lags=True,
               target_column="load",
           ),
           AtmosphereDerivedFeaturesAdder(
               pressure_column="pressure",
               relative_humidity_column="humidity",
               temperature_column="temperature",
           ),
           RadiationDerivedFeaturesAdder(
               coordinate=coordinate,
               radiation_column="radiation",
           ),
           DaylightFeatureAdder(coordinate=coordinate),
           CyclicFeaturesAdder(),
           DatetimeFeaturesAdder(onehot_encode=False),
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           RollingAggregatesAdder(
               feature="load",
               aggregation_functions=["mean", "max"],
               horizons=horizons,
           ),
       ]
   )

   # Fit on training data and transform in one step
   train_features = preprocessing.fit_transform(data=train_dataset)

   # Transform new data using the fitted pipeline (no re-fitting)
   inference_features = preprocessing.transform(data=inference_dataset)

.. note::

   Call ``fit_transform`` only on training data. At inference time, always call ``transform`` on the fitted pipeline. Re-fitting on inference data would leak future statistics into the model.


Writing a Custom Transform
---------------------------

When the built-in transforms do not cover a domain-specific signal — for example, a local industrial calendar, a grid-specific congestion indicator, or a custom weather index — you can implement your own transform by subclassing ``TimeSeriesTransform``.

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig
   import pandas as pd

   class IndustrialShutdownAdder(BaseConfig, TimeSeriesTransform):
       """Add a binary feature for known industrial shutdown periods."""

       shutdown_dates: list[str]  # ISO date strings, e.g. ["2024-12-27", "2024-12-30"]

       def fit(self, data: TimeSeriesDataset) -> None:
           # No parameters to learn from data for this transform
           pass

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           shutdown_index = pd.DatetimeIndex(self.shutdown_dates)
           is_shutdown = data.data.index.normalize().isin(shutdown_index)
           new_data = data.data.copy()
           new_data["industrial_shutdown"] = is_shutdown.astype(float)
           return data.model_copy(update={"data": new_data})

       def features_added(self) -> list[str]:
           return ["industrial_shutdown"]

The ``features_added`` method is used by the pipeline to track which columns were introduced by each transform, enabling downstream steps such as ``EmptyFeatureRemover`` to operate correctly.


What Makes a Good Feature
--------------------------

Not every signal that correlates with load belongs in the feature set. A few principles guide good feature selection for energy forecasting:

- **Physical interpretability.** Features grounded in physical or behavioural mechanisms generalise better than purely statistical correlations. Temperature drives heating load; that relationship holds across years and locations.
- **Availability at inference time.** A feature is only useful if it can be computed when the forecast is needed. Weather forecasts are available; actual future load is not. Lag features must be constructed carefully to respect this constraint — ``LagsAdder`` handles this automatically.
- **Stability across time.** Features derived from slowly changing quantities (day length, calendar) are more stable than those derived from rapidly changing ones. Highly volatile features can introduce noise rather than signal.
- **Low redundancy.** Highly correlated features add computational cost without improving accuracy. The ``EmptyFeatureRemover`` transform removes zero-variance columns automatically; for correlation-based pruning, consider inspecting ``features_added()`` output from each transform.

The built-in OpenSTEF transforms embody these principles. They have been validated on operational energy forecasting problems and represent a strong baseline for most grid points. Custom transforms should be held to the same standard: prefer features with a clear physical or behavioural rationale over features that merely improve training-set metrics.