Energy Component Splitting
==========================

Grid operators and energy analysts often measure only the aggregate load at a connection point — the net sum of all generation and consumption behind the meter. When that connection serves a mix of sources, such as a rooftop solar installation alongside industrial demand, the aggregate signal alone is not enough to understand what is actually happening. Energy component splitting is the process of decomposing that single aggregate measurement into its constituent energy sources.

This page explains why component splitting matters, how OpenSTEF models it through the ``ComponentSplitter`` interface, and which implementations are available out of the box.

Why Split Components?
---------------------

Short-term load forecasting works best when the model learns from a signal that reflects a coherent physical process. A mixed signal — net load from a substation that feeds both a wind farm and a residential neighbourhood — combines two very different dynamics. Feeding that mixture directly into a forecasting model forces it to learn both patterns simultaneously, which typically degrades accuracy for both.

Splitting the aggregate into components lets you:

- Train separate, specialised forecasting models for each energy source (see :doc:`forecasting_basics` for how those models work).
- Understand the contribution of each source to the total, which is valuable for grid planning and settlement.
- Apply source-specific feature engineering — irradiance features for solar, wind-speed features for wind — without polluting the feature space of unrelated components (see :doc:`feature_engineering`).
- Produce probabilistic forecasts per component and recombine them, which gives better uncertainty estimates than forecasting the mixture directly (see :doc:`quantiles_and_confidence`).

.. mermaid:: /diagrams/concepts/component_splitting_diagram_1.mmd

The ``ComponentSplitter`` Interface
------------------------------------

All component splitters in OpenSTEF implement the abstract base class ``ComponentSplitter``, found in ``openstef_models.models.component_splitting``. It extends the generic ``Predictor[TimeSeriesDataset, EnergyComponentDataset]`` mixin, so it follows the same ``fit`` / ``predict`` contract used throughout the library.

.. code-block:: python

    from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

The base configuration class, ``ComponentSplitterConfig``, captures two fundamental parameters shared by every implementation:

- ``source_column`` — the column in the input ``TimeSeriesDataset`` that holds the aggregate load (defaults to ``"load"``).
- ``components`` — the list of ``EnergyComponentType`` values to split into (defaults to all known types).

Every concrete splitter must satisfy one invariant: the predicted component values must sum back to the original source values. This ensures that splitting is a lossless decomposition rather than an approximation of the total.

The interface contract in brief:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset, EnergyComponentDataset
    from openstef_models.models.component_splitting import ComponentSplitter

    # Any splitter follows this pattern:
    splitter: ComponentSplitter = ...          # concrete implementation
    splitter.fit(train_data)                   # may be a no-op for rule-based splitters
    components: EnergyComponentDataset = splitter.predict(data)

``is_fitted`` must return ``True`` before ``predict`` can be called. Rule-based splitters that require no training set ``is_fitted`` to ``True`` immediately on construction.

Available Implementations
--------------------------

ConstantComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest implementation. It applies fixed, user-supplied ratios to the source column — no training required. This is the right choice when you already know the energy distribution at a location from engineering data or historical analysis, or when you need a fast baseline to compare against a learned approach.

Configuration is handled through ``ConstantComponentSplitterConfig``, which validates that the supplied ratios sum to exactly ``1.0``.

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
    # No fit() call needed — is_fitted is True immediately
    components = splitter.predict(time_series_data)

For common site types, two factory class methods provide sensible defaults without manual ratio specification:

.. code-block:: python

    # A connection point that is purely solar generation
    solar_splitter = ConstantComponentSplitter.known_solar_park()

    # A connection point that is purely wind generation
    wind_splitter = ConstantComponentSplitter.known_wind_farm()

These factories are convenient when you are setting up a pipeline quickly and the site type is unambiguous.

.. note::

    ``ConstantComponentSplitter`` is entirely stateless — calling ``fit()`` is a no-op. If the actual energy mix at a location changes over time (for example, new capacity is added), you must update the ratios manually and reconstruct the splitter.

LinearComponentSplitter
^^^^^^^^^^^^^^^^^^^^^^^^

The ``LinearComponentSplitter`` uses a linear model to learn the mapping from input features to component values from data. Unlike the constant splitter, it can adapt to the actual observed distribution rather than relying on prior knowledge of the ratios.

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
    splitter.fit(train_dataset)
    components = splitter.predict(eval_dataset)

.. note::

    Training support for ``LinearComponentSplitter`` is currently limited. Consult the API reference for the current state of the ``fit()`` method before using it in a production pipeline. For production reliability considerations, see :doc:`reliability_and_fallback`.

Choosing an Implementation
---------------------------

The table below summarises when to reach for each splitter:

- **ConstantComponentSplitter** — use when the energy mix is known in advance, stable over time, and you want zero training overhead. Also the right choice as a baseline when evaluating a learned splitter.
- **LinearComponentSplitter** — use when you have labelled historical data with known component values and want the model to learn the relationship from features rather than hard-coding ratios.

If neither built-in implementation fits your use case, you can subclass ``ComponentSplitter`` directly. Implement the ``config`` property, ``fit``, ``predict``, and ``is_fitted``, and the rest of the OpenSTEF pipeline will treat your custom splitter identically to the built-in ones.

.. code-block:: python

    from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig
    from openstef_core.datasets import TimeSeriesDataset, EnergyComponentDataset

    class MyCustomSplitter(ComponentSplitter):
        def __init__(self, config: ComponentSplitterConfig) -> None:
            super().__init__()
            self._config = config

        @property
        def config(self) -> ComponentSplitterConfig:
            return self._config

        @property
        def is_fitted(self) -> bool:
            return self._fitted

        def fit(self, data: TimeSeriesDataset, data_val: TimeSeriesDataset | None = None) -> None:
            # Custom training logic here
            self._fitted = True

        def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
            # Custom splitting logic here
            ...

.. mermaid:: /diagrams/concepts/component_splitting_diagram_2.mmd

Working with ``EnergyComponentDataset``
----------------------------------------

The output of any ``predict()`` call is an ``EnergyComponentDataset``. It wraps a ``pandas.DataFrame`` whose columns correspond to the ``EnergyComponentType`` values requested in the configuration, indexed by the same timestamps as the input ``TimeSeriesDataset``.

.. code-block:: python

    from openstef_core.types import EnergyComponentType

    result: EnergyComponentDataset = splitter.predict(data)

    # Access the underlying DataFrame
    df = result.data

    # Individual component series
    solar_series = df[EnergyComponentType.SOLAR]
    wind_series  = df[EnergyComponentType.WIND]

    # Verify the decomposition is lossless
    reconstructed = df.sum(axis=1)
    original = data.data["load"]
    assert (reconstructed - original).abs().max() < 1e-9

Each component series can then be passed independently into a forecasting pipeline. This is the natural handoff point between the splitting stage and the models described in :doc:`forecasting_basics`.

.. note:: [VISUALIZATION: Stacked area chart showing an aggregate load time series decomposed into solar and wind components over a 24-hour period]

Related Topics
--------------

- :doc:`forecasting_basics` — how to build a short-term forecast once components have been separated.
- :doc:`feature_engineering` — source-specific predictors (irradiance, wind speed) that become useful after splitting.
- :doc:`quantiles_and_confidence` — producing probabilistic forecasts per component.
- :doc:`reliability_and_fallback` — handling failures in a splitting stage within a production pipeline.