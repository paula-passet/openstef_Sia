Energy Component Splitting
==========================

When a grid connection serves multiple generation sources — a rooftop solar installation alongside a wind turbine, for example — the meter records only their combined net output. Energy component splitting is the process of decomposing that aggregate measurement back into its constituent parts: how much came from solar, how much from wind, and how much from other sources. This page explains why that decomposition matters, how OpenSTEF models it through the ``ComponentSplitter`` interface, and which implementations are available out of the box.

.. note::

   Component splitting is a pre-processing or analysis step, not a forecasting step. The resulting per-component time series can then feed into component-specific forecasting pipelines. See :doc:`forecasting_basics` for how those forecasts are constructed.

Why Decompose Aggregate Load?
-----------------------------

Aggregate load measurements are convenient to collect but difficult to forecast accurately when the underlying mix of generation sources changes over time. A model trained on a combined solar-plus-wind signal will struggle whenever the ratio between the two shifts — a new turbine is commissioned, a panel array is expanded, or seasonal patterns diverge. Splitting the signal first lets you:

- Train separate, specialised models for each energy source, each with its own relevant features (irradiance for solar, wind speed at hub height for wind).
- Detect anomalies in individual components without them being masked by compensating changes in another source.
- Attribute forecast errors to a specific source, making model diagnostics far more actionable.
- Combine component forecasts back into a total using a controlled aggregation step, rather than hoping a single model learns the mixture implicitly.

The ``ComponentSplitter`` Interface
------------------------------------

OpenSTEF represents every component splitter as a subclass of ``ComponentSplitter``, defined in ``openstef_models.models.component_splitting``. The class follows the same ``Predictor`` contract used throughout the library: configure, fit (if required), then predict.

.. code-block:: python

   from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

The base configuration class, ``ComponentSplitterConfig``, captures two fundamental parameters:

- **source_column** — the column in the input ``TimeSeriesDataset`` that holds the aggregate load signal (defaults to ``"load"``).
- **components** — the list of ``EnergyComponentType`` values to split into (defaults to all known types: ``wind``, ``solar``, ``other``).

Every concrete splitter must satisfy the following invariants:

- ``is_fitted()`` returns ``True`` before ``predict()`` may be called.
- The columns in the returned ``EnergyComponentDataset`` sum back to the original source column values — splitting is conservative by construction.

``predict()`` always accepts a ``TimeSeriesDataset`` and returns an ``EnergyComponentDataset``, a specialised dataset that validates the presence of all required component columns.

[DIAGRAM: Class hierarchy showing ComponentSplitter as abstract base, with ConstantComponentSplitter and LinearComponentSplitter as concrete subclasses, each paired with their respective Config class]

Available Implementations
--------------------------

OpenSTEF ships two concrete splitters covering the most common operational scenarios.

ConstantComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest possible splitter: it applies fixed, user-supplied ratios to divide the aggregate signal. No training data is required — the ratios are baked into the configuration. This makes it ideal when the energy mix at a location is already well characterised (for example, a dedicated solar park where essentially all generation is photovoltaic) or when you need a fast, interpretable baseline to compare against a learned model.

.. code-block:: python

   from datetime import timedelta

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import EnergyComponentType
   from openstef_models.models.component_splitting.constant_component_splitter import (
       ConstantComponentSplitter,
       ConstantComponentSplitterConfig,
   )

   # Build a small synthetic load series
   index = pd.date_range("2024-06-01", periods=96, freq="15min")
   df = pd.DataFrame({"load": 100 + 20 * pd.Series(range(96), index=index).apply(lambda x: x % 24) / 24}, index=index)
   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   # Configure with explicit ratios — must sum to 1.0
   config = ConstantComponentSplitterConfig(
       source_column="load",
       component_ratios={
           EnergyComponentType.SOLAR: 0.6,
           EnergyComponentType.WIND: 0.4,
       },
   )
   splitter = ConstantComponentSplitter(config)

   # No fit() call needed — the splitter is immediately ready
   components = splitter.predict(dataset)
   print(components.data.head())

For the two most common single-technology sites, the library provides named constructors that set sensible default ratios without requiring manual configuration:

.. code-block:: python

   # Convenience constructors for common site types
   solar_splitter = ConstantComponentSplitter.known_solar_park()
   wind_splitter = ConstantComponentSplitter.known_wind_farm()

   solar_components = solar_splitter.predict(dataset)
   wind_components = wind_splitter.predict(dataset)

LinearComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^

The ``LinearComponentSplitter`` uses a pre-trained linear model (loaded from a ``joblib`` file) to infer component contributions from physical features in the input data. Rather than assuming fixed ratios, it exploits the correlation between the aggregate load and observable quantities — most importantly solar irradiance and wind speed at 100 m hub height — to produce time-varying estimates of each component.

.. code-block:: python

   from openstef_models.models.component_splitting.linear_component_splitter import (
       LinearComponentSplitter,
       LinearComponentSplitterConfig,
   )

   config = LinearComponentSplitterConfig(
       source_column="load",
   )
   splitter = LinearComponentSplitter(config)

   # The pre-trained model is loaded automatically; no fit() call is needed.
   # The input dataset must contain 'load', 'radiation', and 'windspeed_100m' columns.
   components = splitter.predict(dataset_with_weather)

.. note::

   The ``LinearComponentSplitter`` currently does not support re-training. It ships with a model derived from OpenSTEF v3.4.24 and is intended as a production-ready default for mixed solar/wind/other sites. If your site has unusual characteristics, ``ConstantComponentSplitter`` with tuned ratios or a custom ``ComponentSplitter`` subclass may be more appropriate.

The input ``TimeSeriesDataset`` passed to ``LinearComponentSplitter.predict()`` must include the following columns alongside the aggregate load:

- ``radiation`` — surface solar irradiance (W/m²)
- ``windspeed_100m`` — wind speed at 100 m height (m/s)

These are the same weather features used throughout OpenSTEF's forecasting pipelines. See :doc:`feature_engineering` for guidance on sourcing and preparing weather inputs.

Choosing a Splitter
--------------------

The right choice depends on how much you know about the site and what data is available:

- **Known single-technology site** (pure solar park, pure wind farm): use ``ConstantComponentSplitter.known_solar_park()`` or ``ConstantComponentSplitter.known_wind_farm()``. Zero configuration, immediately interpretable.
- **Mixed site with known historical mix**: use ``ConstantComponentSplitter`` with manually calibrated ratios derived from metered sub-component data.
- **Mixed site with weather data available**: use ``LinearComponentSplitter`` for time-varying estimates that respond to actual meteorological conditions.
- **Custom requirements**: subclass ``ComponentSplitter``, implement ``config``, ``fit()``, and ``predict()``, and plug the result into any pipeline that accepts the ``ComponentSplitter`` protocol.

Writing a Custom Splitter
--------------------------

Because ``ComponentSplitter`` is an abstract base class, extending it requires only three methods. The example below sketches a splitter that delegates to a scikit-learn model you have trained externally:

.. code-block:: python

   from typing import override
   import pandas as pd
   from openstef_core.datasets import EnergyComponentDataset, TimeSeriesDataset
   from openstef_models.models.component_splitting.component_splitter import (
       ComponentSplitter,
       ComponentSplitterConfig,
   )

   class MyCustomSplitterConfig(ComponentSplitterConfig):
       model_path: str = "my_splitter_model.joblib"

   class MyCustomSplitter(ComponentSplitter):

       def __init__(self, config: MyCustomSplitterConfig) -> None:
           super().__init__()
           self._config = config
           self._model = None

       @property
       @override
       def config(self) -> MyCustomSplitterConfig:
           return self._config

       @property
       @override
       def is_fitted(self) -> bool:
           return self._model is not None

       @override
       def fit(self, data: TimeSeriesDataset, data_val: TimeSeriesDataset | None = None) -> None:
           import joblib
           self._model = joblib.load(self._config.model_path)

       @override
       def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
           from datetime import timedelta
           from openstef_core.types import EnergyComponentType
           if self._model is None:
               raise ValueError("Call fit() or load a model before predict().")
           features = data.data[["radiation", "windspeed_100m"]].values
           raw = self._model.predict(features)
           result = pd.DataFrame(
               raw,
               index=data.data.index,
               columns=[c.value for c in self._config.components],
           )
           return EnergyComponentDataset(result, sample_interval=data.sample_interval)

.. warning::

   Your ``predict()`` implementation is responsible for ensuring that the component columns sum to the original source column. OpenSTEF does not enforce this automatically for custom subclasses, but violating the invariant will produce inconsistent results in downstream forecasting pipelines.

Related Topics
--------------

- :doc:`forecasting_basics` — how component time series feed into short-term forecasting models.
- :doc:`feature_engineering` — sourcing and preparing the weather features (irradiance, wind speed) that the ``LinearComponentSplitter`` depends on.
- :doc:`reliability_and_fallback` — strategies for handling missing weather inputs or model load failures in production.