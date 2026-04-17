Energy Component Splitting
==========================

When a grid connection serves a mix of generation and consumption — a substation
feeding both a solar park and a wind farm, for example — the metered load signal
is the *net* of all those sources. Forecasting that aggregate signal directly is
possible, but it discards information: a model that knows how much of the load is
solar-driven can exploit radiation forecasts far more effectively than one that
treats the total as a black box.

Energy component splitting is the process of decomposing an aggregate load
measurement into its constituent energy sources (solar, wind, and residual
"other"). OpenSTEF provides a dedicated interface for this, along with two
ready-to-use implementations.

.. note:: [DIAGRAM: Data flow showing aggregate load time series entering a ComponentSplitter and producing separate wind, solar, and other component time series]

Why Split Components?
---------------------

Component splitting is most valuable when:

- **Training per-component forecasters.** A solar forecaster trained on the
  isolated solar signal learns a much cleaner relationship with irradiance than
  one trained on a noisy aggregate. See :doc:`forecasting_basics` for how
  component-level signals feed into the broader forecasting pipeline.

- **Interpretability and reporting.** Grid operators often need to report
  generation by source. Splitting lets you attribute measured energy to each
  technology without separate sub-meters.

- **Ensemble disaggregation.** The meta-ensemble approach described in
  :doc:`meta_ensembles` can combine per-component forecasts back into a total
  load forecast, improving accuracy when each component has distinct drivers.

Component splitting is *not* required for every forecasting task. If your
measurement point is a pure load (no embedded generation), there is nothing to
split.

The ``ComponentSplitter`` Interface
------------------------------------

All splitters in OpenSTEF inherit from the abstract base class
``ComponentSplitter``, found in ``openstef_models.models.component_splitting``.
It follows the same ``Predictor`` contract used throughout the library:

.. code-block:: python

    from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

The base configuration class ``ComponentSplitterConfig`` captures two
fundamental settings shared by every implementation:

- ``source_column`` — the column in the input ``TimeSeriesDataset`` that holds
  the aggregate load (default: ``"load"``).
- ``components`` — the list of ``EnergyComponentType`` values to produce
  (default: all defined types).

Every concrete splitter must implement three members:

- ``config`` — a property returning the splitter's configuration object.
- ``fit(data, data_val=None)`` — trains the splitter (may be a no-op for
  ratio-based methods).
- ``predict(data) -> EnergyComponentDataset`` — performs the decomposition and
  returns a dataset whose columns correspond to each ``EnergyComponentType``.

A key invariant enforced by the interface: the component columns returned by
``predict`` must sum back to the original ``source_column`` values. This
conservation property ensures that downstream forecasters working on individual
components remain consistent with the measured total.

``EnergyComponentDataset``, the return type of ``predict``, is a validated
``TimeSeriesDataset`` that requires columns for every ``EnergyComponentType``
(``wind``, ``solar``, ``other``). It is imported from ``openstef_core.datasets``.

Available Implementations
--------------------------

OpenSTEF ships two concrete splitters. They cover opposite ends of the
complexity spectrum and are both found under
``openstef_models.models.component_splitting``.

ConstantComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest possible splitter: it applies fixed, user-supplied ratios to the
aggregate load at every time step. No training is needed.

This is the right choice when:

- You already know the approximate generation mix at a location (e.g., a
  substation that is 60 % solar, 40 % wind by installed capacity).
- You need a fast, transparent baseline to compare against a data-driven method.
- You have too little historical data to fit a model.

.. code-block:: python

    from openstef_models.models.component_splitting.constant_component_splitter import (
        ConstantComponentSplitter,
        ConstantComponentSplitterConfig,
    )
    from openstef_core.types import EnergyComponentType

    # Define fixed ratios — they must sum to 1.0
    config = ConstantComponentSplitterConfig(
        source_column="load",
        component_ratios={
            EnergyComponentType.SOLAR: 0.6,
            EnergyComponentType.WIND: 0.4,
        },
    )
    splitter = ConstantComponentSplitter(config)

    # predict() is available immediately — no fit() call required
    components = splitter.predict(time_series_data)

Two convenience constructors are available for common site types:

.. code-block:: python

    # Pre-configured for a typical solar park
    solar_splitter = ConstantComponentSplitter.known_solar_park()

    # Pre-configured for a typical wind farm
    wind_splitter = ConstantComponentSplitter.known_wind_farm()

These factory methods encode sensible default ratios so you can get started
without looking up typical generation mixes.

LinearComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^

The ``LinearComponentSplitter`` uses a pre-trained linear model (shipped with
the package) to estimate the wind, solar, and other components from the
aggregate load together with meteorological features. It was trained on data
from OpenSTEF v3.4.24 and is ready to use out of the box.

Because the model is pre-trained, ``fit()`` is currently a no-op — you cannot
retrain it on your own data. This makes it straightforward to deploy but means
its accuracy depends on how well the bundled model generalises to your site.

The splitter requires two additional columns in the input dataset beyond the
aggregate load:

- ``radiation`` — surface solar irradiance.
- ``windspeed_100m`` — wind speed at 100 m hub height.

These are the same meteorological features discussed in :doc:`feature_engineering`.

.. code-block:: python

    from openstef_models.models.component_splitting.linear_component_splitter import (
        LinearComponentSplitter,
        LinearComponentSplitterConfig,
    )

    config = LinearComponentSplitterConfig(
        source_column="load",
        # radiation_column and windspeed_100m_column default to
        # "radiation" and "windspeed_100m" respectively
    )
    splitter = LinearComponentSplitter(config)

    # The bundled model is loaded automatically; no fit() call needed
    components = splitter.predict(time_series_data)

The returned ``EnergyComponentDataset`` contains three columns — ``wind``,
``solar``, and ``other`` — whose values at every timestamp sum to the original
``load`` value.

.. note:: [VISUALIZATION: Time series plot showing aggregate load decomposed into wind, solar, and other components over a 48-hour window]

If the input dataset is missing the ``radiation`` or ``windspeed_100m`` columns,
``predict()`` raises a ``ValueError`` with a descriptive message.

Choosing Between Implementations
---------------------------------

+---------------------------+---------------------------+---------------------------+
| Criterion                 | ConstantComponentSplitter | LinearComponentSplitter   |
+===========================+===========================+===========================+
| Training required         | No                        | No (pre-trained)          |
+---------------------------+---------------------------+---------------------------+
| Meteorological inputs     | None                      | Radiation, wind speed     |
+---------------------------+---------------------------+---------------------------+
| Temporal variation        | None (fixed ratios)       | Yes (driven by features)  |
+---------------------------+---------------------------+---------------------------+
| Best for                  | Known mix, baselines      | General-purpose splitting |
+---------------------------+---------------------------+---------------------------+
| Custom retraining         | N/A (ratio-based)         | Not yet supported         |
+---------------------------+---------------------------+---------------------------+

Start with ``ConstantComponentSplitter`` when you have domain knowledge about
the site. Switch to ``LinearComponentSplitter`` when you have the required
meteorological features and want the split to reflect actual weather-driven
variation throughout the day.

Writing a Custom Splitter
--------------------------

If neither built-in implementation fits your needs, you can subclass
``ComponentSplitter`` directly. The only requirements are implementing
``config``, ``fit``, and ``predict``, and ensuring that the output components
sum to the source column.

.. code-block:: python

    from typing import override
    from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig
    from openstef_core.datasets import EnergyComponentDataset, TimeSeriesDataset


    class MyConfig(ComponentSplitterConfig):
        my_param: float = 0.5


    class MySplitter(ComponentSplitter):

        def __init__(self, config: MyConfig) -> None:
            super().__init__()
            self._config = config

        @property
        @override
        def config(self) -> MyConfig:
            return self._config

        @override
        def fit(
            self,
            data: TimeSeriesDataset,
            data_val: TimeSeriesDataset | None = None,
        ) -> None:
            # Implement training logic here
            self._fitted = True

        @override
        def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
            # Implement splitting logic here; result must sum to source column
            ...

.. note::

   The ``is_fitted`` invariant must hold: ``predict()`` should raise if called
   before ``fit()`` on splitters that require training. For ratio-based or
   pre-trained splitters, ``is_fitted`` can return ``True`` unconditionally.

Related Topics
--------------

- :doc:`forecasting_basics` — how component-level signals are used as inputs to
  short-term forecasters.
- :doc:`feature_engineering` — meteorological features (radiation, wind speed)
  that the ``LinearComponentSplitter`` depends on.
- :doc:`meta_ensembles` — combining per-component forecasts into a total load
  forecast using the ensemble approach.