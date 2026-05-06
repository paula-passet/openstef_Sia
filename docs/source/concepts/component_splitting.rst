Energy Component Splitting
==========================

Many grid connections carry a mix of energy sources — a substation might serve
both rooftop solar installations and a small wind turbine cluster, with only a
single aggregate meter reading available. Component splitting is the process of
decomposing that combined measurement into its constituent parts: how much of
the observed load comes from solar generation, how much from wind, and how much
from other sources.

This page explains why that decomposition matters, how OpenSTEF models it
through the ``ComponentSplitter`` interface, and which implementations are
available out of the box.

Why Split Components?
---------------------

Forecasting aggregate load is often sufficient for grid balancing, but several
use cases benefit from knowing the individual contributions:

- **Improved forecast accuracy** — a model trained on net load (consumption
  minus solar) is simpler to fit than one that must implicitly learn the solar
  signal buried in the aggregate. Splitting first, then forecasting each
  component separately, can reduce overall error.
- **Asset-level visibility** — operators managing distributed energy resources
  need per-source estimates to schedule dispatch or curtailment correctly.
- **Anomaly detection** — unexpected deviations in a single component (e.g.,
  a solar inverter fault) are easier to detect when that component is isolated
  rather than masked by other sources.
- **Regulatory reporting** — some grid codes require separate accounting of
  generation types connected to a single point of common coupling.

.. mermaid:: /diagrams/concepts/component_splitting_diagram_1.mmd

The ComponentSplitter Interface
--------------------------------

All component splitters in OpenSTEF implement the abstract base class
``ComponentSplitter``, found in
``openstef_models.models.component_splitting``. It extends the generic
``Predictor[TimeSeriesDataset, EnergyComponentDataset]`` mixin, so it follows
the same ``fit`` / ``predict`` contract used throughout the library.

.. code-block:: python

    from openstef_models.models.component_splitting import (
        ComponentSplitter,
        ComponentSplitterConfig,
    )

The base configuration class, ``ComponentSplitterConfig``, captures two
fundamental parameters shared by every splitter:

- ``source_column`` — the column in the input ``TimeSeriesDataset`` that holds
  the aggregate signal to decompose (defaults to ``"load"``).
- ``components`` — the list of ``EnergyComponentType`` values the splitter
  should produce. By default this is the full set of known component types.

A key invariant enforced by the interface is that the predicted component
values must sum back to the original source values. Any custom implementation
must respect this constraint.

.. code-block:: python

    from openstef_core.types import EnergyComponentType

    # EnergyComponentType is an enum covering known energy source categories,
    # for example EnergyComponentType.SOLAR and EnergyComponentType.WIND.

Implementing a custom splitter means subclassing ``ComponentSplitter`` and
providing three things: a ``config`` property, a ``fit`` method (which may be
a no-op if no training is needed), and a ``predict`` method that returns an
``EnergyComponentDataset``.

.. note::

   ``is_fitted`` must return ``True`` before ``predict`` can be called. For
   splitters that require no training, simply return ``True`` unconditionally
   from the property.

Available Implementations
--------------------------

OpenSTEF ships two concrete splitters covering the most common scenarios.

ConstantComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest approach: apply fixed, user-supplied ratios to the source column.
No training is required because the distribution of energy sources is assumed
to be known in advance. This is useful as a baseline, for locations with
stable generation mixes, or when historical sub-metering data is available to
derive reliable ratios offline.

.. code-block:: python

    from openstef_core.types import EnergyComponentType
    from openstef_models.models.component_splitting.constant_component_splitter import (
        ConstantComponentSplitter,
        ConstantComponentSplitterConfig,
    )

    config = ConstantComponentSplitterConfig(
        source_column="load",
        components=[EnergyComponentType.SOLAR, EnergyComponentType.WIND],
        component_ratios={
            EnergyComponentType.SOLAR: 0.6,
            EnergyComponentType.WIND: 0.4,
        },
    )
    splitter = ConstantComponentSplitter(config)

    # No fit step needed — is_fitted is always True
    component_dataset = splitter.predict(time_series_dataset)

The ``component_ratios`` dictionary must sum exactly to ``1.0``; the
constructor will raise a ``ValueError`` otherwise.

For common scenarios, two factory class methods provide sensible defaults
without requiring manual ratio specification:

.. code-block:: python

    # A connection that is entirely solar generation
    solar_splitter = ConstantComponentSplitter.known_solar_park()

    # A connection that is entirely wind generation
    wind_splitter = ConstantComponentSplitter.known_wind_farm()

These are convenient starting points when you know the dominant generation
type at a location but have not yet measured precise ratios.

.. note:: [VISUALIZATION: Bar chart comparing the component ratios produced by known_solar_park() and known_wind_farm() factory methods against a custom mixed-ratio configuration]

LinearComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^

When the component mix varies over time — for example, because solar output
depends on irradiance — a linear model can learn the relationship between
observable features (weather, time of day) and the contribution of each
component. ``LinearComponentSplitter`` wraps any model that satisfies the
``LinearComponentSplitterModel`` protocol, which requires a single
``predict(x)`` method returning a NumPy array.

.. code-block:: python

    from openstef_models.models.component_splitting.linear_component_splitter import (
        LinearComponentSplitter,
        LinearComponentSplitterConfig,
    )

    config = LinearComponentSplitterConfig(
        source_column="load",
        components=[EnergyComponentType.SOLAR, EnergyComponentType.WIND],
    )
    splitter = LinearComponentSplitter(config)

    # fit() currently acts as a no-op; the underlying linear model is
    # configured through the config rather than trained on the fly.
    splitter.fit(train_dataset)

    component_dataset = splitter.predict(time_series_dataset)

.. note::

   ``LinearComponentSplitter.fit()`` does not perform training in the current
   release. The linear model coefficients must be supplied through the
   configuration. Check the API reference for ``LinearComponentSplitterConfig``
   for the full set of available parameters.

Choosing Between Implementations
---------------------------------

+---------------------------+-----------------------------------+----------------------------------+
| Scenario                  | Recommended splitter              | Reason                           |
+===========================+===================================+==================================+
| Known, stable mix         | ``ConstantComponentSplitter``     | No data required; zero overhead  |
+---------------------------+-----------------------------------+----------------------------------+
| Dominant single source    | ``ConstantComponentSplitter``     | Use ``known_solar_park()`` or    |
|                           | (factory method)                  | ``known_wind_farm()`` directly   |
+---------------------------+-----------------------------------+----------------------------------+
| Mix varies with features  | ``LinearComponentSplitter``       | Captures feature-driven variance |
+---------------------------+-----------------------------------+----------------------------------+
| Novel splitting logic     | Custom ``ComponentSplitter``      | Subclass and implement interface |
+---------------------------+-----------------------------------+----------------------------------+

Writing a Custom Splitter
--------------------------

If neither built-in implementation fits your use case, subclassing
``ComponentSplitter`` is straightforward. The example below sketches a splitter
that uses a time-of-day heuristic to vary the solar fraction:

.. code-block:: python

    from openstef_core.datasets import EnergyComponentDataset, TimeSeriesDataset
    from openstef_core.types import EnergyComponentType
    from openstef_models.models.component_splitting import (
        ComponentSplitter,
        ComponentSplitterConfig,
    )
    import pandas as pd

    class TimeOfDaySplitterConfig(ComponentSplitterConfig):
        peak_solar_ratio: float = 0.8  # fraction attributed to solar at solar noon

    class TimeOfDaySplitter(ComponentSplitter):
        def __init__(self, config: TimeOfDaySplitterConfig) -> None:
            super().__init__()
            self._config = config

        @property
        def config(self) -> TimeOfDaySplitterConfig:
            return self._config

        @property
        def is_fitted(self) -> bool:
            return True  # no training required

        def fit(
            self,
            data: TimeSeriesDataset,
            data_val: TimeSeriesDataset | None = None,
        ) -> None:
            pass  # no-op

        def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
            source = data.data[self.config.source_column]
            hour = source.index.hour
            # Simple triangular solar profile peaking at noon
            solar_fraction = self.config.peak_solar_ratio * (
                1 - abs(hour - 12) / 12
            )
            solar = source * solar_fraction
            other = source - solar
            return EnergyComponentDataset(
                data=pd.DataFrame(
                    {
                        EnergyComponentType.SOLAR: solar,
                        EnergyComponentType.OTHER: other,
                    },
                    index=data.data.index,
                ),
                sample_interval=data.sample_interval,
            )

The critical constraint to remember: the columns in the returned
``EnergyComponentDataset`` must sum to the original ``source_column`` values
at every timestamp.

Related Topics
--------------

Component splitting is one step in a broader forecasting workflow. Once the
aggregate signal has been decomposed, each component can be forecast
independently using the methods described in :doc:`forecasting_basics`. Weather
features — particularly irradiance for solar and wind speed for wind — are
among the most important predictors for component-level models; see
:doc:`feature_engineering` for details on how OpenSTEF handles those inputs.
For production deployments where a splitter might fail or produce out-of-range
values, the fallback strategies in :doc:`reliability_and_fallback` apply at
the component level as well.