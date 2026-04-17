Energy Component Splitting
==========================

Grid operators and energy analysts often measure only the aggregate load at a
connection point — the net sum of solar generation, wind generation, and
residual consumption all rolled into a single number. For many forecasting and
analysis tasks that aggregate figure is not enough: you need to know *how much*
of the load is attributable to each source. Energy component splitting is the
process of decomposing that aggregate time series into its constituent parts.

This page explains why component splitting matters, describes the
``ComponentSplitter`` interface, and walks through the two built-in
implementations provided by ``openstef-models``.

.. note::
   Component splitting is a pre-processing or post-processing step, not a
   forecasting step. For the forecasting side of the pipeline see
   :doc:`forecasting_basics`.

Why Split Components?
---------------------

A substation that serves a mix of residential load, a rooftop solar installation,
and a small wind turbine will report a single net-metered value. Treating that
value as a homogeneous signal leads to models that conflate weather-driven
generation with demand-driven consumption. Separating the components lets you:

- Train dedicated forecasting models per source, each with the right feature set
  (irradiance for solar, wind speed for wind, temperature for demand).
- Diagnose anomalies more precisely — a sudden drop in the aggregate could be a
  demand reduction *or* a solar spike.
- Report generation and consumption figures independently for settlement or
  regulatory purposes.

Once split, each component column can be fed into a standard OpenSTEF forecasting
pipeline. The ``EnergyComponentDataset`` returned by a splitter is a validated
``TimeSeriesDataset`` whose columns correspond exactly to the members of
``EnergyComponentType``, so downstream code can rely on those column names being
present.

.. note:: [DIAGRAM: Data flow from a single aggregate load time series through a ComponentSplitter into separate wind, solar, and other component time series, each feeding its own forecasting model]

The ``ComponentSplitter`` Interface
------------------------------------

All splitters in OpenSTEF implement the abstract base class
``ComponentSplitter``, found in
``openstef_models.models.component_splitting``. It extends the generic
``Predictor[TimeSeriesDataset, EnergyComponentDataset]`` protocol, so it fits
naturally into any pipeline that already uses OpenSTEF predictors.

.. code-block:: python

   from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

The base configuration class ``ComponentSplitterConfig`` captures two
fundamental parameters shared by every implementation:

- ``source_column`` — the column in the input ``TimeSeriesDataset`` that holds
  the aggregate load (default: ``"load"``).
- ``components`` — the list of ``EnergyComponentType`` members to produce
  (default: all members, i.e. wind, solar, and other).

Every concrete splitter must satisfy two invariants:

1. ``is_fitted()`` must return ``True`` before ``predict()`` is called.
2. The component columns returned by ``predict()`` must sum back to the original
   ``source_column`` values — splitting is conservative by design.

The ``predict()`` method accepts a ``TimeSeriesDataset`` and returns an
``EnergyComponentDataset``. The output dataset is validated on construction, so
any splitter that produces incomplete or misnamed columns will raise immediately
rather than silently propagating bad data.

Available Implementations
--------------------------

OpenSTEF ships two concrete splitters. They cover opposite ends of the
complexity spectrum and are both importable from
``openstef_models.models.component_splitting``.

ConstantComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest possible splitter: it applies fixed, user-supplied ratios to the
aggregate load. No training is required. This is useful when the energy mix at a
location is already known from engineering data or metering records, or when you
need a fast baseline to compare against a more sophisticated approach.

.. code-block:: python

   from datetime import timedelta

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import EnergyComponentType
   from openstef_models.models.component_splitting.constant_component_splitter import (
       ConstantComponentSplitter,
       ConstantComponentSplitterConfig,
   )

   # Build a minimal time series with an aggregate load column
   index = pd.date_range("2024-01-01", periods=48, freq="15min")
   raw = pd.DataFrame({"load": [100.0] * 48}, index=index)
   dataset = TimeSeriesDataset(raw, sample_interval=timedelta(minutes=15))

   # Configure: 60 % solar, 40 % wind
   config = ConstantComponentSplitterConfig(
       source_column="load",
       component_ratios={
           EnergyComponentType.SOLAR: 0.6,
           EnergyComponentType.WIND: 0.4,
       },
   )
   splitter = ConstantComponentSplitter(config)

   components = splitter.predict(dataset)
   print(components.data.head())

.. note::
   ``ConstantComponentSplitter`` is already fitted at construction time — no
   call to ``fit()`` is needed because there are no learned parameters.

Two convenience factory methods cover the most common scenarios without
requiring manual ratio configuration:

.. code-block:: python

   # Pre-configured for a typical solar park (solar-dominant ratios)
   solar_splitter = ConstantComponentSplitter.known_solar_park()

   # Pre-configured for a typical wind farm (wind-dominant ratios)
   wind_splitter = ConstantComponentSplitter.known_wind_farm()

These are good starting points when you have no site-specific metering data.

LinearComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^

The ``LinearComponentSplitter`` uses a pre-trained linear model (bundled with
the package, originally trained on OpenSTEF v3.4.24 data) to estimate three
components — wind on-shore, solar, and other — from the aggregate load together
with two weather features: surface radiation and wind speed at 100 m.

Because the model is pre-trained, ``fit()`` is a no-op and the splitter is
always considered fitted. The weather columns must be present in the input
dataset; their names are configurable via ``LinearComponentSplitterConfig``.

.. code-block:: python

   from datetime import timedelta

   import numpy as np
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.component_splitting.linear_component_splitter import (
       LinearComponentSplitter,
       LinearComponentSplitterConfig,
   )

   index = pd.date_range("2024-06-01", periods=96, freq="15min")
   rng = np.random.default_rng(0)

   raw = pd.DataFrame(
       {
           "load": rng.uniform(80, 120, 96),
           "radiation": rng.uniform(0, 800, 96),       # W/m²
           "windspeed_100m": rng.uniform(2, 15, 96),   # m/s
       },
       index=index,
   )
   dataset = TimeSeriesDataset(raw, sample_interval=timedelta(minutes=15))

   config = LinearComponentSplitterConfig(
       source_column="load",
       radiation_column="radiation",
       windspeed_100m_column="windspeed_100m",
   )
   splitter = LinearComponentSplitter(config)

   components = splitter.predict(dataset)
   print(components.data.columns.tolist())
   # ['wind', 'solar', 'other']

.. note:: [VISUALIZATION: Stacked area chart showing the three output component time series (wind, solar, other) summing to the original aggregate load over a 24-hour period]

The linear model is loaded from a ``joblib``-serialised file bundled alongside
the source. If you need to point to a different model file — for example a
site-specific retrained version — override ``linear_model_path`` in the config:

.. code-block:: python

   from pathlib import Path

   config = LinearComponentSplitterConfig(
       linear_model_path=Path("/models/my_site_splitter.z"),
       radiation_column="rad",
       windspeed_100m_column="ws100",
   )

.. warning::
   Training a custom ``LinearComponentSplitter`` is not yet supported through
   the standard ``fit()`` interface. The bundled model was trained on a broad
   portfolio of Dutch grid connections; accuracy will vary for sites with
   significantly different generation mixes.

Choosing Between Implementations
----------------------------------

+---------------------------+---------------------------+---------------------------+
| Criterion                 | ConstantComponentSplitter | LinearComponentSplitter   |
+===========================+===========================+===========================+
| Training required         | No                        | No (pre-trained)          |
+---------------------------+---------------------------+---------------------------+
| Weather features needed   | No                        | Yes (radiation, wind)     |
+---------------------------+---------------------------+---------------------------+
| Accuracy                  | Depends on ratio quality  | Generally higher          |
+---------------------------+---------------------------+---------------------------+
| Customisable ratios       | Yes                       | Via model file override   |
+---------------------------+---------------------------+---------------------------+
| Best for                  | Known mixes, baselines    | Unknown mixes, portfolios |
+---------------------------+---------------------------+---------------------------+

Implementing a Custom Splitter
-------------------------------

If neither built-in splitter fits your use case, subclass ``ComponentSplitter``
directly. You must implement three members: the ``config`` property, ``fit()``,
and ``predict()``.

.. code-block:: python

   from typing import override
   from openstef_core.datasets import EnergyComponentDataset, TimeSeriesDataset
   from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

   class MyConfig(ComponentSplitterConfig):
       my_param: float = 1.0

   class MyComponentSplitter(ComponentSplitter):
       def __init__(self, config: MyConfig) -> None:
           super().__init__()
           self._config = config
           self._fitted = False

       @property
       @override
       def config(self) -> MyConfig:
           return self._config

       @property
       @override
       def is_fitted(self) -> bool:
           return self._fitted

       @override
       def fit(self, data: TimeSeriesDataset, data_val: TimeSeriesDataset | None = None) -> None:
           # Learn whatever parameters your method needs
           self._fitted = True

       @override
       def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
           import pandas as pd
           load = data.data[self.config.source_column]
           split = pd.DataFrame(
               {
                   "wind": load * 0.5,
                   "solar": load * 0.3,
                   "other": load * 0.2,
               },
               index=data.data.index,
           )
           return EnergyComponentDataset(split, data.sample_interval)

The ``EnergyComponentDataset`` constructor validates that all ``EnergyComponentType``
columns are present, so you will get an immediate error if your ``predict()``
returns an incomplete DataFrame.

Related Topics
--------------

- :doc:`forecasting_basics` — how to use the component columns produced here as
  targets for individual short-term forecasting models.
- :doc:`feature_engineering` — weather features such as radiation and wind speed
  that drive both splitting accuracy and forecast quality.
- :doc:`reliability_and_fallback` — strategies for handling missing weather
  inputs that the ``LinearComponentSplitter`` depends on.