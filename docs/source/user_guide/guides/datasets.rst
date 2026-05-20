Datasets
========

This page explains why OpenSTEF provides its own dataset abstractions on top of pandas DataFrames, and how they solve critical problems in energy forecasting pipelines — particularly around temporal data availability and forecast versioning.

.. contents:: On this page
   :local:
   :depth: 2

Why Not Just Use DataFrames?
----------------------------

A raw pandas DataFrame carries data but not *context*. In energy forecasting, the pipeline needs to know:

- **What is the sampling interval?** A 15-minute resolution dataset behaves differently from an hourly one, and mixing them silently produces wrong results.
- **Which data was available when?** Weather forecasts for Monday issued on Saturday differ from those issued on Sunday. The pipeline must know which version was available at prediction time to avoid data leakage.
- **What are features vs. metadata?** Columns like ``available_at`` or ``horizon`` are not features to train on — they are structural metadata.

OpenSTEF's dataset types encode these invariants directly, so every downstream component (transforms, model training, backtesting) can rely on them without re-deriving context from raw column names.

TimeSeriesDataset
-----------------

:class:`~openstef_core.datasets.TimeSeriesDataset` is the foundational data container. It wraps a pandas DataFrame with a ``DatetimeIndex`` and guarantees:

- **Sorted temporal order** — data is always ascending by timestamp.
- **Consistent sample interval** — validated on construction, preventing silent misalignment.
- **Feature name extraction** — metadata columns (``available_at``, ``horizon``, columns prefixed with ``__``) are excluded from the feature list automatically.
- **Versioning detection** — the dataset knows whether it carries versioned data based on column presence.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))
   dataset.feature_names   # ['temperature', 'load'] — no metadata columns
   dataset.is_versioned    # True/False based on available_at or horizon column

Key properties:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Purpose
   * - ``sample_interval``
     - Fixed time between consecutive data points
   * - ``feature_names``
     - Column names excluding system/metadata columns
   * - ``is_versioned``
     - Whether the dataset tracks temporal data availability
   * - ``index``
     - The ``DatetimeIndex`` of all timestamps

The dataset also provides ``filter_by_range()``, ``copy_with()``, and persistence methods. See the :class:`~openstef_core.datasets.TimeSeriesDataset` API reference for the full interface.

VersionedTimeSeriesDataset
--------------------------

:class:`~openstef_core.datasets.VersionedTimeSeriesDataset` models the reality that **data arrives over time in versions**. This is the central abstraction for handling temporal data availability.

The Problem: Forecast Versioning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Consider weather forecasts for a target hour (e.g., Monday 14:00):

- The forecast issued Saturday 06:00 predicts 18°C
- The forecast issued Sunday 12:00 predicts 20°C
- The forecast issued Monday 06:00 predicts 19.5°C

Each is a *version* of the same target timestamp. When training a model or running a backtest, the pipeline must use only the version that was **actually available at prediction time**. Using a later version constitutes data leakage and produces unrealistically optimistic results.

.. mermaid:: /diagrams/user_guide/guides/datasets_diagram_1.mmd

How Versioning Works
^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` uses **lazy composition** to avoid the O(n²) space complexity that would result from eagerly joining all (timestamp, available_at) pairs. It stores data as a list of :class:`~openstef_core.datasets.TimeSeriesDataset` parts and delays concatenation until version selection.

Each ``TimeSeriesDataset`` part tracks availability through one of two mechanisms:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Versioning Mode
     - Description
   * - ``available_at`` column
     - Records the wall-clock time when each observation became known
   * - ``horizon`` column
     - Records the lead time (as timedelta) between issuance and target

Creating a Versioned Dataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset

   # Weather data with availability tracking
   weather_part = TimeSeriesDataset(weather_df, timedelta(hours=1))
   dataset = VersionedTimeSeriesDataset([weather_part])

For simpler cases, use the convenience constructor:

.. code-block:: python

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data, timedelta(minutes=15)
   )

.. note::

   All data parts in a ``VersionedTimeSeriesDataset`` must have identical sample intervals and disjoint feature sets. The combined index is the union of all part indices.

Version Resolution Strategies
-----------------------------

The key operation on a versioned dataset is **selecting which version to use** for each target timestamp. This is done via ``select_version()``, which reconstructs a point-in-time view of the data.

Point-in-Time Selection
^^^^^^^^^^^^^^^^^^^^^^^

Given a prediction time, ``select_version()`` returns a regular ``TimeSeriesDataset`` containing only the data that was available at that moment. This is essential for:

- **Realistic backtesting** — simulating what the model would have seen historically
- **Correct lag computation** — :class:`~openstef_models.transforms.time_domain.versioned_lags_adder.VersionedLagsAdder` uses versioning to compute lags from only actually-available data
- **Multi-horizon training** — ``to_horizons()`` converts versioned data into horizon-based format for training models at multiple lead times

.. code-block:: python

   # Select the latest available version for each timestamp
   snapshot = dataset.select_version()

   # Convert to multi-horizon format
   from openstef_core.types import LeadTime
   horizons = [LeadTime(hours=1), LeadTime(hours=6), LeadTime(hours=24)]
   multi_horizon_ds = dataset.to_horizons(horizons)

Preventing Data Leakage
^^^^^^^^^^^^^^^^^^^^^^^^

The versioning system is OpenSTEF's primary defense against temporal data leakage. Without it, a naive approach might:

1. Join the *latest* weather forecast to each historical timestamp — using information that wasn't available at the time.
2. Compute lags from future-revised data — e.g., using a corrected measurement that arrived hours after the fact.

``VersionedTimeSeriesDataset`` makes the correct behavior the default behavior.

.. warning::

   If your input data lacks ``available_at`` or ``horizon`` columns, the dataset is treated as non-versioned. This is appropriate for measurements that are available in real-time, but dangerous for forecast inputs. Always ensure forecast data carries availability metadata.

Integration with Transforms
----------------------------

Versioned datasets integrate directly with OpenSTEF's transform system. For example, :class:`~openstef_models.transforms.time_domain.versioned_lags_adder.VersionedLagsAdder` computes lag features while respecting temporal availability:

.. code-block:: python

   from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder

   versioned_lags = VersionedLagsAdder(
       feature="temperature_forecast",
       lags=[timedelta(hours=-2), timedelta(hours=-6)],
   )
   result = versioned_lags.transform(versioned_ds)

This ensures that lag features only reference data that was genuinely available at each point in time — standard lag operations on plain DataFrames cannot provide this guarantee.

When to Use Which Dataset
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Dataset Type
     - Use When
     - Examples
   * - ``TimeSeriesDataset``
     - Data is available in real-time or has a single version per timestamp
     - Load measurements, static calendar features
   * - ``VersionedTimeSeriesDataset``
     - Data arrives in multiple versions over time for the same target
     - Weather forecasts, price forecasts, revised measurements

Related Pages
-------------

- :doc:`/user_guide/guides/forecasting` — how datasets flow through the forecasting lifecycle
- :class:`~openstef_core.datasets.TimeSeriesDataset` — full API reference
- :class:`~openstef_core.datasets.VersionedTimeSeriesDataset` — full API reference