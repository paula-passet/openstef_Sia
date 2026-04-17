Changelog
=========

This page records what has changed across OpenSTEF releases. Each entry lists new features, bug fixes, and breaking changes for that version. Where a release requires code changes on your side, a brief summary is given here; for step-by-step migration instructions see the :doc:`/user_guide/migration` guide.

Entries are ordered newest-first.

----

Version 4.0 (Current)
---------------------

OpenSTEF 4.0 is a major architectural release. The library has been restructured from a single package into a **modular mono-repo** of self-contained packages. The primary motivation was to decouple hard-wired external dependencies, broaden applicability beyond the Dutch DSO context, and establish clear extension points for custom models, transforms, and metrics.

.. note::
   [DIAGRAM: High-level package dependency graph showing openstef-core at the base, openstef-models and openstef-meta building on top of it, and openstef-beam sitting alongside as the evaluation layer]

New packages
^^^^^^^^^^^^

``openstef-core``
   Data types, base classes, shared exceptions, and testing utilities. Every other package depends on this one. If you are building a custom integration, start here.

``openstef-models``
   Forecasting models, data-preprocessing pipelines, energy-specific transforms, explainability helpers, and presets for common use cases. This is the main package for day-to-day forecasting work.

``openstef-meta``
   Meta-learning and ensemble model architectures. Provides advanced model compositions that sit on top of ``openstef-models``.

``openstef-beam``
   Backtesting, Evaluation, Analysis, and Metrics (BEAM). Answers the question *"are my model changes statistically significant?"* by running regression tests against benchmark datasets.

New features
^^^^^^^^^^^^

- **Versioned time-series datasets** — ``VersionedTimeSeriesDataset`` tracks data availability at prediction time, enabling realistic backtesting without look-ahead bias. Internally it uses lazy composition to avoid the O(n²) space problem that arose when concatenating DataFrames with misaligned ``(timestamp, available_at)`` pairs.

  .. code-block:: python

     import pandas as pd
     from datetime import datetime, timedelta
     from openstef_core.datasets import TimeSeriesDataset
     from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

     weather_data = pd.DataFrame(
         {"temperature": [20.5], "available_at": [datetime(2025, 1, 1, 16, 0)]},
         index=pd.DatetimeIndex([datetime(2025, 1, 1, 10, 0)]),
     )
     weather_part = TimeSeriesDataset(weather_data, timedelta(hours=1))
     dataset = VersionedTimeSeriesDataset([weather_part])

     # Reconstruct the view a model would have had at a specific point in time
     snapshot = dataset.select_version(datetime(2025, 1, 1, 18, 0))

- **Versioned lag features** — ``VersionedLagsAdder`` creates lag features that respect data-availability constraints, so lag columns only reference measurements that would have been observable at inference time.

  .. code-block:: python

     from openstef_models.transforms.time_domain import VersionedLagsAdder

     adder = VersionedLagsAdder(column="load_mw", lags=[1, 2, 4, 8])
     dataset_with_lags = adder.transform(dataset)

- **Full type safety** — the codebase now carries complete type annotations throughout. ``BaseConfig`` (from ``openstef_core.base_model``) is the Pydantic-based foundation for all configurable components, enabling IDE auto-complete and runtime validation.

- **Flexible configuration** — hard-coded assumptions (holiday calendars, country-specific constants, fixed quantile sets) have been replaced by explicit configuration objects. Forecasting pipelines are no longer tied to the Netherlands or to Alliander's internal data schema.

- **Extensible interfaces** — ``VersionedTimeSeriesTransform`` and related base classes define clear contracts for adding custom transforms without modifying library code.

- **Backtesting pipeline** — ``openstef-beam`` ships a ready-to-use backtesting pipeline that runs evaluation across multiple historical windows and aggregates metrics.

  .. code-block:: python

     from openstef_beam.backtesting import Pipeline

     pipeline = Pipeline(
         dataset=dataset,
         model=my_model,
         metrics=["rMAE", "rCRPS"],
     )
     results = pipeline.run()

Breaking changes
^^^^^^^^^^^^^^^^

.. warning::
   Version 4.0 is not backwards-compatible with version 3.x. The import paths, configuration objects, and pipeline APIs have all changed. Read the :doc:`/user_guide/migration` guide before upgrading.

The most impactful changes are:

- **Package split** — ``import openstef`` no longer works as a single namespace. Code must be updated to import from the appropriate sub-package (``openstef_core``, ``openstef_models``, ``openstef_beam``, etc.).
- **Removed hard dependency on MLflow** — MLflow is now an optional integration. Experiment tracking must be wired up explicitly if required.
- **Removed hard dependency on openstef-dbc** — database connectivity is no longer bundled. Bring your own data loader and pass a ``TimeSeriesDataset`` to the pipeline.
- **Removed hard dependency on XGBoost gblinear** — the default booster configuration has changed. Existing trained models serialised with v3 are not guaranteed to load correctly.
- **Input data schema relaxed** — v3 required specific column names. v4 uses explicit column mappings in the configuration object; the old implicit schema is no longer supported.
- **Holiday calendar** — the Dutch public-holiday calendar is no longer injected automatically. Pass a calendar object in the pipeline configuration.

----

Version 3.x
-----------

Version 3 established OpenSTEF as a production-grade forecasting library and introduced the pipeline abstraction that v4 builds on. It was deployed at Alliander running more than 10,000 forecasts daily.

Key highlights from the 3.x series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Introduced the ``PredictionJob`` concept as the central unit of configuration for a single forecasting task.
- Added probabilistic forecasting via quantile regression, producing forecast intervals alongside point predictions.
- Integrated MLflow for experiment tracking and model registry out of the box.
- Shipped ``openstef-dbc`` as the reference database connector for reading measurement data and writing forecasts.
- Added feature engineering for weather variables (solar irradiance, wind speed, temperature) and calendar features (hour of day, day of week, Dutch public holidays).
- Introduced the ``RegressorMixin`` interface so custom scikit-learn-compatible models could be plugged into the standard training pipeline.
- Provided ``train_model_pipeline``, ``create_forecast_pipeline``, and ``optimize_hyperparameters_pipeline`` as the three main entry points.

Notable 3.x fixes and improvements (selected)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **3.4** — Improved handling of missing measurements during feature construction; gaps are now forward-filled up to a configurable maximum before raising an error.
- **3.3** — Added ``rMAE`` (relative Mean Absolute Error) as a first-class evaluation metric alongside RMSE.
- **3.2** — Quantile forecasts extended to support asymmetric intervals; users can now request arbitrary quantile sets rather than fixed symmetric bands.
- **3.1** — XGBoost model updated to support ``gblinear`` booster as an alternative to ``gbtree``, useful for load series with strong linear trends.
- **3.0** — Initial public release of the v3 pipeline API. Replaced the ad-hoc scripting approach of v2 with structured, testable pipeline functions.

Breaking changes in 3.0
^^^^^^^^^^^^^^^^^^^^^^^^

- The v2 ``Forecaster`` class was removed. All forecasting logic moved into the pipeline functions.
- ``PredictionJob`` became a required argument to every pipeline function; passing raw dictionaries was deprecated.
- The ``load`` column in input DataFrames was renamed to ``load`` (MW, not kW) — unit normalisation is now the caller's responsibility.

----

Version 2.x
-----------

Version 2 was the first release to package OpenSTEF as an installable Python library (previously the code was distributed as internal scripts). It introduced XGBoost as the primary model backend and established the feature-engineering conventions that carried forward into v3.

Selected highlights
^^^^^^^^^^^^^^^^^^^

- Packaged and published to PyPI as ``openstef``.
- XGBoost gradient-boosted trees as the default model.
- Lag features, rolling statistics, and calendar features added automatically from raw load measurements.
- Basic cross-validation for hyperparameter tuning.
- Initial support for solar and wind generation forecasting alongside load forecasting.

----

Version 1.x
-----------

Version 1 was the initial open-source release, extracted from Alliander's internal tooling. It provided a working end-to-end forecasting script for substation load but was not designed for external consumption. No migration path from v1 to v2 is documented; a clean start with v2 or later is recommended.

----

Versioning policy
-----------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. In summary:

- A **major** version increment (e.g. 3 → 4) signals breaking API changes. Expect to update import paths and configuration objects.
- A **minor** version increment (e.g. 4.0 → 4.1) adds new functionality in a backwards-compatible manner.
- A **patch** version increment (e.g. 4.0.0 → 4.0.1) contains backwards-compatible bug fixes only.

Pre-release versions carry a ``dev`` or ``alpha`` suffix (e.g. ``4.0.0a1``) and may change without notice.

.. note::
   The installed version is accessible at runtime:

   .. code-block:: python

      import openstef_core
      print(openstef_core.__version__)

----

See also
--------

- :doc:`/user_guide/migration` — step-by-step instructions for upgrading from v3 to v4.
- :doc:`/user_guide/installation` — supported Python versions and install options for each package.
- `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_ — full commit-level diff and release artefacts for every tagged version.