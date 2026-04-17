Energy Component Splitting
==========================

Grid operators and energy analysts rarely observe individual generation sources directly — what a meter records is the *aggregate* load: the net sum of consumption, solar generation, wind generation, and everything else flowing through a connection point. Energy component splitting is the process of decomposing that single aggregate signal into its constituent parts.

This page explains why that decomposition matters, how OpenSTEF models it through the ``ComponentSplitter`` interface, and which implementations are available out of the box.

.. note::

   Component splitting is concerned with *understanding what has already happened* in a historical or near-real-time signal. If you are looking for how OpenSTEF produces future load forecasts, see :doc:`forecasting_basics`.

Why Split Components?
---------------------

A substation that hosts both a large solar park and industrial consumers will show a load curve that is the algebraic sum of both. Treating that combined signal as a single entity creates several practical problems:

- **Forecast accuracy degrades.** A model trained on net load must implicitly learn the solar profile embedded in the target variable. Separating the solar component first lets a dedicated solar model handle that physics, and a separate consumption model handle the rest.
- **Operational decisions require component visibility.** Grid planners need to know how much of the observed load reduction during a sunny afternoon is due to solar generation versus genuine demand reduction.
- **Feature engineering benefits.** Downstream forecasting pipelines can use split components as additional features, improving predictions for adjacent time steps.

OpenSTEF treats component splitting as a first-class modelling step, providing a consistent interface so that different splitting strategies — from simple fixed ratios to pre-trained linear models — can be swapped without changing the surrounding pipeline code.

**[DIAGRAM: Data flow showing aggregate load time series entering a ComponentSplitter, which outputs separate wind, solar, and other component time series that feed into downstream forecasting pipelines]**

The ``ComponentSplitter`` Interface
------------------------------------

All component splitters in OpenSTEF inherit from the abstract base class ``ComponentSplitter``, defined in ``openstef_models.models.component_splitting``. The interface follows the same ``Predictor`` contract used throughout the library:

.. code-block:: python

   from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

The base configuration class ``ComponentSplitterConfig`` captures two fundamental parameters shared by every implementation:

- ``source_column`` — the column in the input ``TimeSeriesDataset`` that holds the aggregate load (defaults to ``"load"``).
- ``components`` — the list of ``EnergyComponentType`` values to produce (defaults to all known types: ``wind``, ``solar``, ``other``).

Every concrete splitter must implement three members:

- ``config`` — a property returning the splitter's configuration object.
- ``fit(data, data_val=None)`` — trains the splitter on historical data (may be a no-op for parameter-free splitters).
- ``predict(data) -> EnergyComponentDataset`` — performs the actual decomposition, returning an ``EnergyComponentDataset`` whose columns correspond to the requested components.

A key invariant enforced by the interface is that the predicted component columns must sum back to the original source values. This ensures that no energy is created or destroyed by the splitting step.

Input and Output Data Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Splitters consume a ``TimeSeriesDataset`` and produce an ``EnergyComponentDataset``. The output dataset validates at construction time that columns for all ``EnergyComponentType`` members are present, so a splitter that omits a required component will raise an error immediately rather than silently producing incomplete data.

``EnergyComponentType`` is a ``StrEnum`` with members ``wind``, ``solar``, and ``other``. The string values are used directly as DataFrame column names, making it straightforward to inspect results with standard pandas tooling.

Available Implementations
--------------------------

OpenSTEF ships two concrete splitters covering the most common use cases.

``ConstantComponentSplitter``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest possible splitter: it multiplies the source column by a fixed ratio for each component. No training is required — the ratios are supplied at construction time and must sum to exactly 1.0.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import EnergyComponentType
   from openstef_models.models.component_splitting.constant_component_splitter import (
       ConstantComponentSplitter,
       ConstantComponentSplitterConfig,
   )

   # Build a minimal time series with aggregate load
   df = pd.DataFrame(
       {"load": [100.0, 120.0, 95.0, 110.0]},
       index=pd.date_range("2024-06-01", periods=4, freq="15min"),
   )
   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   # Configure a mixed solar/wind site: 60% solar, 40% wind
   config = ConstantComponentSplitterConfig(
       source_column="load",
       components=[EnergyComponentType.SOLAR, EnergyComponentType.WIND],
       component_ratios={
           EnergyComponentType.SOLAR: 0.6,
           EnergyComponentType.WIND: 0.4,
       },
   )

   splitter = ConstantComponentSplitter(config)
   components = splitter.predict(dataset)

   print(components.data)

**[VISUALIZATION: Table showing the resulting EnergyComponentDataset with solar and wind columns, values summing to the original load column at each timestamp]**

Because ``ConstantComponentSplitter.is_fitted`` always returns ``True``, there is no training step — you can call ``predict`` immediately after construction.

For the two most common single-source scenarios, the class provides convenience factory methods that pre-configure the ratios:

.. code-block:: python

   from openstef_models.models.component_splitting.constant_component_splitter import (
       ConstantComponentSplitter,
   )

   # A connection point that is purely a solar park
   solar_splitter = ConstantComponentSplitter.known_solar_park()

   # A connection point that is purely a wind farm
   wind_splitter = ConstantComponentSplitter.known_wind_farm()

Both factory methods set the corresponding component ratio to 1.0, assigning the entire load to that single source. This is useful as a quick baseline or when the site composition is unambiguous.

When to use it:
   Use ``ConstantComponentSplitter`` when you have reliable domain knowledge about the energy mix at a location — for example, a substation that exclusively serves a known solar installation — or when you need a fast, interpretable baseline to compare against more sophisticated methods.

``LinearComponentSplitter``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``LinearComponentSplitter`` applies a pre-trained linear model (loaded from a ``joblib`` file) to decompose the aggregate load into wind, solar, and other components. Unlike the constant splitter, it uses additional time series features — specifically solar irradiance (``radiation``) and wind speed at 100 m (``windspeed_100m``) — to make the decomposition physically informed.

.. code-block:: python

   from openstef_models.models.component_splitting.linear_component_splitter import (
       LinearComponentSplitter,
       LinearComponentSplitterConfig,
   )

   config = LinearComponentSplitterConfig()
   splitter = LinearComponentSplitter(config)

   # The splitter loads a bundled pre-trained model; no fit() call is needed
   components = splitter.predict(dataset_with_weather_features)

.. note::

   The ``LinearComponentSplitter`` requires the input ``TimeSeriesDataset`` to contain ``radiation`` and ``windspeed_100m`` columns in addition to the load column. Training is not currently supported — the splitter uses a model bundled with the package, derived from OpenSTEF v3.4.24.

When to use it:
   Use ``LinearComponentSplitter`` when weather data is available alongside the load measurements and you want a physically grounded decomposition without providing explicit ratios. It is the recommended default for general-purpose component splitting.

Implementing a Custom Splitter
-------------------------------

Because ``ComponentSplitter`` is an abstract base class, you can implement your own splitting strategy by subclassing it. The only hard requirements are:

1. Provide a ``config`` property returning a ``ComponentSplitterConfig`` (or a subclass).
2. Implement ``fit`` (even if it is a no-op).
3. Implement ``predict`` such that the returned ``EnergyComponentDataset`` columns sum to the source column values.

.. code-block:: python

   from typing import override
   from openstef_core.datasets import EnergyComponentDataset, TimeSeriesDataset
   from openstef_models.models.component_splitting.component_splitter import (
       ComponentSplitter,
       ComponentSplitterConfig,
   )

   class MyCustomSplitter(ComponentSplitter):

       def __init__(self, config: ComponentSplitterConfig) -> None:
           super().__init__()
           self._config = config

       @property
       @override
       def config(self) -> ComponentSplitterConfig:
           return self._config

       @property
       @override
       def is_fitted(self) -> bool:
           return True  # or track training state

       @override
       def fit(self, data: TimeSeriesDataset, data_val: TimeSeriesDataset | None = None) -> None:
           # Implement training logic here, or leave as no-op
           pass

       @override
       def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
           # Implement your decomposition logic here
           ...

Choosing the Right Splitter
----------------------------

The table below summarises the trade-offs between the two built-in implementations:

+------------------------------+---------------------------+------------------------------+
| Criterion                    | ConstantComponentSplitter | LinearComponentSplitter      |
+==============================+===========================+==============================+
| Training required            | No                        | No (pre-trained)             |
+------------------------------+---------------------------+------------------------------+
| Additional features needed   | No                        | Yes (radiation, windspeed)   |
+------------------------------+---------------------------+------------------------------+
| Interpretability             | High                      | Moderate                     |
+------------------------------+---------------------------+------------------------------+
| Accuracy on mixed sites      | Depends on ratio quality  | Generally higher             |
+------------------------------+---------------------------+------------------------------+
| Best for                     | Known single-source sites | General-purpose splitting    |
+------------------------------+---------------------------+------------------------------+

If neither built-in splitter fits your use case, the ``ComponentSplitter`` abstract base class makes it straightforward to plug in a custom implementation while remaining compatible with the rest of the OpenSTEF pipeline.

Related Topics
--------------

Component splitting is one step in a broader forecasting workflow. Once you have decomposed your load signal, the individual components can serve as targets or features for the forecasting models described in :doc:`forecasting_basics`. If your pipeline produces probabilistic outputs from the split components, see :doc:`quantiles_and_confidence` for how OpenSTEF represents uncertainty. For information on how weather variables like irradiance and wind speed are incorporated as features more broadly, refer to :doc:`feature_engineering`.