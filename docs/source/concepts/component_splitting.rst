Energy Component Splitting
==========================

Grid operators and energy analysts often measure load at aggregated points — a substation serving a mix of residential consumers, a solar park, and a wind farm all appear as a single net measurement. Component splitting is the process of decomposing that aggregate signal into its constituent energy sources. This page explains why that decomposition matters, how OpenSTEF models it through the ``ComponentSplitter`` interface, and which implementations are available out of the box.

Why Split Components?
---------------------

A raw load time series at an aggregation point conflates fundamentally different physical processes. Solar generation follows irradiance; wind generation follows wind speed; base load follows human activity patterns. When these signals are mixed, a forecasting model trained on the aggregate must implicitly learn all three relationships at once — which is harder, less interpretable, and more sensitive to changes in the local generation mix.

Splitting the aggregate into components lets you:

- Train separate, specialised forecasting models for each energy source (see :doc:`forecasting_basics` for how those models work).
- Detect anomalies in a specific source without noise from the others.
- Reason about the contribution of renewables to a particular grid node.
- Produce component-level forecasts that sum back to the total, preserving energy balance.

.. mermaid:: /diagrams/concepts/component_splitting_diagram_1.mmd

The ``ComponentSplitter`` Interface
------------------------------------

All component splitters in OpenSTEF implement the abstract base class ``ComponentSplitter``, found in ``openstef_models.models.component_splitting``. It extends the generic ``Predictor[TimeSeriesDataset, EnergyComponentDataset]`` mixin, so it follows the same ``fit`` / ``predict`` contract used throughout the library.

.. code-block:: python

    from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

The base configuration class, ``ComponentSplitterConfig``, captures two fundamental parameters:

- **source_column** — the column in the input ``TimeSeriesDataset`` that holds the aggregate measurement (defaults to ``"load"``).
- **components** — the list of ``EnergyComponentType`` values to produce. By default this is the full set of known component types.

Every concrete splitter must satisfy two invariants enforced by the base class:

1. ``is_fitted`` must return ``True`` before ``predict()`` is called.
2. The component columns returned by ``predict()`` must sum back to the original source values.

The output of ``predict()`` is always an ``EnergyComponentDataset`` — a typed wrapper around a ``pandas.DataFrame`` whose columns correspond to the requested ``EnergyComponentType`` values, indexed on the same timestamps as the input.

Available Implementations
--------------------------

ConstantComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest splitter applies fixed, user-supplied ratios to the source column. Because no training is needed (``fit()`` is a no-op and ``is_fitted`` is always ``True``), it is the right choice whenever you already know the energy distribution at a location — for example, a substation that is exclusively connected to a solar park.

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.types import EnergyComponentType
    from openstef_models.models.component_splitting.constant_component_splitter import (
        ConstantComponentSplitter,
        ConstantComponentSplitterConfig,
    )

    # Build a dataset with a mixed load signal
    df = pd.DataFrame(
        {"load": [100.0, 120.0, 95.0, 110.0]},
        index=pd.date_range("2024-01-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(data=df, sample_interval=pd.Timedelta("15min"))

    # Configure a 60 % solar / 40 % wind split
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

.. note:: [VISUALIZATION: Bar chart showing the aggregate load alongside the split solar and wind components for each timestamp, illustrating that the components sum to the original signal]

The ``component_ratios`` dictionary must sum exactly to ``1.0``; the config validator raises a ``ValueError`` otherwise.

For the common case of a pure single-source site, two factory class methods are provided so you do not need to construct the config manually:

.. code-block:: python

    # A substation that is 100 % solar
    solar_splitter = ConstantComponentSplitter.known_solar_park()

    # A substation that is 100 % wind
    wind_splitter = ConstantComponentSplitter.known_wind_farm()

Both return a fully configured, ready-to-use ``ConstantComponentSplitter`` instance.

LinearComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^

The ``LinearComponentSplitter`` applies a pre-trained linear model to perform the split, rather than relying on fixed ratios. It is suited to locations where the component mix is not known in advance and must be inferred from historical data.

.. code-block:: python

    from openstef_models.models.component_splitting.linear_component_splitter import (
        LinearComponentSplitter,
    )

    # The linear splitter loads a pre-trained model internally
    splitter = LinearComponentSplitter()
    components = splitter.predict(dataset)

.. note::

   The ``LinearComponentSplitter`` ships with a pre-trained model derived from OpenSTEF v3.4.24 training data. Re-training on custom data is not currently supported. If the default model does not match your grid topology, ``ConstantComponentSplitter`` with manually tuned ratios is the recommended alternative.

The linear model accepts the same ``TimeSeriesDataset`` input and returns the same ``EnergyComponentDataset`` output, so it is a drop-in replacement for ``ConstantComponentSplitter`` in any pipeline.

Implementing a Custom Splitter
-------------------------------

If neither built-in implementation fits your use case, you can subclass ``ComponentSplitter`` directly. The only requirements are implementing the ``config`` property and the ``predict()`` method, plus ensuring ``is_fitted`` reflects the model's readiness.

.. code-block:: python

    from typing import override
    import pandas as pd
    from openstef_core.datasets import EnergyComponentDataset, TimeSeriesDataset
    from openstef_core.types import EnergyComponentType
    from openstef_models.models.component_splitting.component_splitter import (
        ComponentSplitter,
        ComponentSplitterConfig,
    )

    class MyCustomSplitter(ComponentSplitter):
        """Example splitter using a time-of-day heuristic."""

        def __init__(self, config: ComponentSplitterConfig) -> None:
            super().__init__()
            self._config = config
            self._fitted = False

        @property
        @override
        def config(self) -> ComponentSplitterConfig:
            return self._config

        @property
        @override
        def is_fitted(self) -> bool:
            return self._fitted

        @override
        def fit(
            self,
            data: TimeSeriesDataset,
            data_val: TimeSeriesDataset | None = None,
        ) -> None:
            # Insert your training logic here
            self._fitted = True

        @override
        def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
            source = data.data[self.config.source_column]
            # Naive heuristic: daytime hours attributed to solar
            is_day = source.index.hour.isin(range(7, 20))
            solar = source.where(is_day, other=0.0)
            residual = source - solar
            components = pd.DataFrame(
                {
                    EnergyComponentType.SOLAR: solar,
                    EnergyComponentType.WIND: residual,
                },
                index=data.data.index,
            )
            return EnergyComponentDataset(
                data=components,
                sample_interval=data.sample_interval,
            )

The key contract to uphold is that ``components.data.sum(axis=1)`` equals ``source`` for every timestamp. Violating this breaks energy balance and will produce incorrect downstream forecasts.

Choosing the Right Splitter
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Situation
     - Recommended splitter
     - Notes
   * - Known single-source site
     - ``known_solar_park()`` or ``known_wind_farm()``
     - Zero configuration needed
   * - Known mixed-source ratios
     - ``ConstantComponentSplitter``
     - Ratios must sum to 1.0
   * - Unknown mix, general grid
     - ``LinearComponentSplitter``
     - Uses pre-trained model
   * - Custom physics or data
     - Subclass ``ComponentSplitter``
     - Implement fit and predict

Related Topics
--------------

Once you have separated the aggregate load into components, each component can be fed into its own forecasting pipeline. See :doc:`forecasting_basics` for an introduction to how OpenSTEF builds and evaluates those models. If you are working with probabilistic outputs — for example, producing uncertainty bounds on the solar component — :doc:`quantiles_and_confidence` explains how quantile forecasts are structured. For guidance on what features drive each component's model, refer to :doc:`feature_engineering`.