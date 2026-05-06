Energy Component Splitting
==========================

Many grid operators and energy analysts measure only the aggregate load at a connection point — the net sum of consumption, solar generation, wind generation, and other sources combined. While this single signal is sufficient for basic load forecasting, several use cases demand a finer view: understanding how much of the measured load originates from solar panels versus wind turbines versus baseline consumption. Energy component splitting is the process of decomposing that aggregate measurement into its constituent parts.

This page explains why component splitting matters, how OpenSTEF models the problem through the ``ComponentSplitter`` interface, and which implementations are available out of the box.

Why Split Components?
---------------------

Aggregate load measurements hide the physical reality of a connection point. A substation serving a mix of residential consumers, a solar park, and a wind farm will show a net load that can swing from strongly negative (generation exceeding consumption) to strongly positive depending on weather and time of day. Forecasting that net signal directly is harder than forecasting each source independently, because each source has a different relationship with weather features and follows a different temporal pattern.

Splitting components is particularly valuable when:

- You want to train separate, specialised forecasting models for solar, wind, and residual load rather than one model that must learn all three simultaneously.
- You need to report generation and consumption figures separately for settlement or grid planning purposes.
- Historical data contains only net metering measurements, but downstream models expect labelled component time series.

Once components are separated, each can be fed into a dedicated forecasting pipeline. See :doc:`forecasting_basics` for how those pipelines work.

The ``ComponentSplitter`` Interface
------------------------------------

All component splitters in OpenSTEF follow the same abstract base class defined in ``openstef_models.models.component_splitting``:

.. code-block:: python

   from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

``ComponentSplitter`` is a ``Predictor`` that consumes a ``TimeSeriesDataset`` and produces an ``EnergyComponentDataset``. The contract is straightforward:

- ``config`` — a property returning a ``ComponentSplitterConfig`` that declares which source column to split and which ``EnergyComponentType`` values to produce.
- ``fit(data, data_val=None)`` — trains the splitter on historical data. For rule-based splitters this is a no-op.
- ``predict(data)`` — returns an ``EnergyComponentDataset`` whose component columns sum back to the original source column values.

The invariant that predicted components must sum to the source signal is enforced by the interface contract. This ensures that no energy is created or lost during decomposition.

``ComponentSplitterConfig`` carries two base fields shared by every implementation:

.. code-block:: python

   from openstef_models.models.component_splitting import ComponentSplitterConfig
   from openstef_core.types import EnergyComponentType

   # Default configuration: split the "load" column into all known component types
   config = ComponentSplitterConfig(
       source_column="load",
       components=list(EnergyComponentType),
   )

You can restrict the output to a subset of components by passing a shorter ``components`` list.

.. mermaid:: /diagrams/concepts/component_splitting_diagram_1.mmd

Available Implementations
--------------------------

OpenSTEF ships two concrete splitters. They differ in how much prior knowledge they require and whether they use weather features.

ConstantComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``ConstantComponentSplitter`` applies fixed, user-supplied ratios to divide the source column. No fitting is needed — the ratios are set at construction time and remain constant across all time steps.

.. code-block:: python

   from openstef_models.models.component_splitting.constant_component_splitter import (
       ConstantComponentSplitter,
       ConstantComponentSplitterConfig,
   )
   from openstef_core.types import EnergyComponentType

   config = ConstantComponentSplitterConfig(
       source_column="load",
       component_ratios={
           EnergyComponentType.SOLAR: 0.6,
           EnergyComponentType.WIND: 0.4,
       },
   )
   splitter = ConstantComponentSplitter(config)

   # No training required — call predict directly
   components = splitter.predict(time_series_data)

This is the right choice when you already know the installed capacity mix at a location and want a deterministic, interpretable baseline. It is also useful for unit testing downstream pipelines before a data-driven splitter is available.

Two convenience constructors encode typical ratios for common site types:

.. code-block:: python

   # Pre-configured for a predominantly solar site
   solar_splitter = ConstantComponentSplitter.known_solar_park()

   # Pre-configured for a predominantly wind site
   wind_splitter = ConstantComponentSplitter.known_wind_farm()

These factory methods return fully initialised, ready-to-use splitters. They are a quick starting point when you do not yet have site-specific ratio measurements.

.. note::

   Because ratios are constant, the ``ConstantComponentSplitter`` cannot capture intra-day or seasonal variation in the component mix. If the solar fraction at a site varies significantly with season, a data-driven splitter will produce more accurate decompositions.

LinearComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^

The ``LinearComponentSplitter`` uses a pre-trained linear model to estimate component contributions from weather features. It requires two additional columns in the input dataset: solar irradiance (``radiation``) and wind speed at 100 m (``windspeed_100m``). The model was trained on OpenSTEF V3 data and decomposes the total load into three components: wind on-shore, solar, and other.

.. code-block:: python

   from openstef_models.models.component_splitting.linear_component_splitter import (
       LinearComponentSplitter,
       LinearComponentSplitterConfig,
   )

   config = LinearComponentSplitterConfig(
       source_column="load",
       radiation_column="radiation",
       windspeed_100m_column="windspeed_100m",
   )
   splitter = LinearComponentSplitter(config)

   # The bundled model is loaded automatically — no fit() call needed
   components = splitter.predict(time_series_data)

The ``fit()`` method is currently a no-op: the underlying linear model is bundled with the package and loaded from disk at prediction time. Custom training is not yet supported for this splitter.

The ``LinearComponentSplitter`` is more physically grounded than the constant approach because it scales solar and wind contributions with actual weather conditions. When radiation is high, the solar component grows; when wind speed is high, the wind component grows. The residual is attributed to the ``other`` category.

.. note:: [VISUALIZATION: Time series plot showing aggregate load decomposed into solar, wind, and other components over a representative week, with the solar component peaking at midday and the wind component varying with weather events]

Choosing Between Implementations
---------------------------------

The table below summarises the key trade-offs:

- **ConstantComponentSplitter** — no weather features required, fully transparent ratios, zero training cost. Best for baselines, sites with a single dominant source, or when weather data is unavailable.
- **LinearComponentSplitter** — requires ``radiation`` and ``windspeed_100m``, uses a pre-trained model, captures weather-driven variation. Best for mixed solar/wind sites where the component mix changes with conditions.

If neither implementation fits your use case — for example, you have labelled historical component data and want to train a custom model — you can subclass ``ComponentSplitter`` directly and implement ``config``, ``fit``, and ``predict``.

Implementing a Custom Splitter
-------------------------------

Subclassing ``ComponentSplitter`` requires implementing three members:

.. code-block:: python

   from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig
   from openstef_core.datasets import EnergyComponentDataset, TimeSeriesDataset

   class MyConfig(ComponentSplitterConfig):
       my_param: float = 1.0

   class MyComponentSplitter(ComponentSplitter):

       def __init__(self, config: MyConfig) -> None:
           super().__init__()
           self._config = config
           self._fitted = False

       @property
       def config(self) -> MyConfig:
           return self._config

       @property
       def is_fitted(self) -> bool:
           return self._fitted

       def fit(self, data: TimeSeriesDataset, data_val: TimeSeriesDataset | None = None) -> None:
           # Train your model here using data.data (a pandas DataFrame)
           self._fitted = True

       def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
           # Apply your model and return an EnergyComponentDataset
           # Components must sum to data.data[self.config.source_column]
           ...

The only hard constraint is the summation invariant: the values across all component columns in the returned ``EnergyComponentDataset`` must equal the source column at every time step.

.. note::

   Weather features used for component splitting — radiation, wind speed, and others — are discussed in detail on the :doc:`feature_engineering` page. Ensuring those features are present and correctly named in your ``TimeSeriesDataset`` before calling ``predict()`` is a common source of errors.

Related Topics
--------------

- :doc:`forecasting_basics` — how to use the separated component time series as inputs to short-term forecasting models.
- :doc:`feature_engineering` — weather and calendar features that drive component splitting and load forecasting.
- :doc:`reliability_and_fallback` — strategies for handling missing weather inputs or failed splitter predictions in production.