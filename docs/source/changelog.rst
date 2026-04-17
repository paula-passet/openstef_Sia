Changelog
=========

This page records the version history of OpenSTEF, summarising new features, bug fixes,
and breaking changes for each release. Entries are listed in reverse-chronological order
so the most recent changes are always at the top.

.. note::

   If you are upgrading from an earlier version and need step-by-step instructions for
   adapting your code, see the :doc:`../user_guide/migration` guide.

----

Version 4.0 (Current)
----------------------

OpenSTEF 4.0 is a major architectural release. The library has been restructured from a
single monolithic package into a **modular mono-repo** of focused, independently
installable packages. This is the most significant change since the project's inception
and touches every layer of the codebase — from data types and transforms through to
model pipelines and evaluation tooling.

**[DIAGRAM: OpenSTEF v4 package dependency graph — openstef-core at the base, openstef-models and openstef-beam building on top, openstef-meta at the apex, and the openstef meta-package pulling them all together]**

New packages
^^^^^^^^^^^^

The single ``openstef`` package has been replaced by five independently installable
packages. You can install only what you need, or pull everything in at once:

.. code-block:: bash

   # Install the full library (all packages)
   pip install openstef

   # Install individual packages as needed
   pip install openstef-core
   pip install openstef-models
   pip install openstef-beam
   pip install openstef-meta

The packages and their responsibilities are:

- **openstef-core** — Data types (``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``,
  ``ForecastDataset``), base classes, shared exceptions, and testing utilities. This is
  the foundation that all other packages depend on.
- **openstef-models** — Forecasting model pipelines, energy-specific feature transforms,
  preprocessing, postprocessing, explainability, and presets for common use cases.
- **openstef-beam** — Backtesting, evaluation, analysis, and metrics (the *BEAM* acronym).
  Answers the question "are my model changes statistically significant?" and provides
  regression testing against benchmarks.
- **openstef-meta** — Meta-learning and advanced ensemble model architectures built on
  top of ``openstef-models``.
- **openstef** — Convenience meta-package that installs all of the above.

New features
^^^^^^^^^^^^

**Versioned time series datasets**

A new ``VersionedTimeSeriesDataset`` type tracks *when* each measurement became
available, not just when it was observed. This is essential for realistic backtesting
where measurements arrive with delays or are revised over time. The implementation uses
lazy composition to avoid the O(n²) space complexity that arises when naively
concatenating DataFrames with misaligned ``(timestamp, available_at)`` pairs.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

   # Build a simple versioned dataset from a DataFrame that includes
   # an 'available_at' column recording when each row was published.
   data = pd.DataFrame(
       {
           "available_at": pd.date_range("2025-01-01 10:00", periods=4, freq="h"),
           "load": [100.0, 110.0, 120.0, 130.0],
       },
       index=pd.date_range("2025-01-01 10:00", periods=4, freq="h"),
   )
   dataset = VersionedTimeSeriesDataset.from_dataframe(data, timedelta(hours=1))

   # Select a point-in-time snapshot — only data available at 11:00 is visible
   snapshot = dataset.select_version(available_at=pd.Timestamp("2025-01-01 11:00"))

**Versioned lag features**

The new ``VersionedLagsAdder`` transform creates lag features while respecting data
availability constraints, so lag values only use measurements that would have been
observable at prediction time:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder

   transform = VersionedLagsAdder(
       feature="load",
       lags=[timedelta(hours=-1), timedelta(hours=-2)],
   )
   result = transform.transform(dataset)
   snapshot = result.select_version()
   print(snapshot.data[["load_lag_-PT1H", "load_lag_-PT2H"]])

**[VISUALIZATION: Example output showing lag feature columns alongside the original load series, with NaN values correctly placed at the start of the series]**

**Modular forecasting pipeline**

The ``ForecastingModel`` class in ``openstef-models`` provides a clean
``preprocessing → forecaster → postprocessing`` pipeline with explicit fit/predict
semantics:

.. code-block:: python

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.presets import get_preset

   # Load a ready-made preset — the fastest way to get started
   model = get_preset("xgb")

   train_data, val_data, test_data = create_synthetic_forecasting_dataset()
   fit_result = model.fit(train_data, data_val=val_data, data_test=test_data)

   forecast = model.predict(val_data)

**[VISUALIZATION: Time series plot of forecast vs. actuals produced by the preset model on the synthetic dataset]**

**MLflow integration as an optional dependency**

MLflow is no longer a hard runtime dependency. The ``MLFlowStorage`` and
``MLFlowStorageCallback`` classes are available under
``openstef_models.integrations.mlflow`` and are only required when you explicitly opt
into experiment tracking:

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

**Versioned model serialisation**

All serialisable objects now carry a ``__version__`` integer in their persisted state.
When loading a saved model, OpenSTEF automatically migrates state from older versions
via ``_migrate_state``, and emits a ``UserWarning`` when forward-compatibility cannot be
guaranteed:

.. code-block:: python

   import warnings

   # Loading a model saved with an older version emits a clear warning
   with warnings.catch_warnings(record=True) as caught:
       warnings.simplefilter("always")
       model = storage.load("my_model")

   for w in caught:
       print(w.message)
   # UserWarning: Loading legacy ConstantMedianForecaster without version metadata.

**Type safety throughout**

The entire codebase now carries full static type annotations. Pydantic v2 is used for
configuration objects, providing runtime validation and clear error messages when
configuration values are invalid.

**Flexible configuration**

Hard-coded assumptions (holiday calendars, country-specific constants, fixed quantile
sets) have been replaced by Pydantic-validated configuration objects. Country codes use
``pydantic_extra_types.country.CountryAlpha2``, making it straightforward to deploy
OpenSTEF outside the Netherlands.

Breaking changes
^^^^^^^^^^^^^^^^

.. warning::

   Version 4.0 contains breaking changes at every layer of the API. A full migration
   guide with before/after code examples is available at
   :doc:`../user_guide/migration`.

The most impactful changes are summarised here:

- **Package restructure.** All imports from the old ``openstef.*`` namespace are broken.
  Code must be updated to import from the appropriate sub-package
  (``openstef_core``, ``openstef_models``, ``openstef_beam``, or ``openstef_meta``).
- **``openstef-dbc`` removed from core.** Database connector logic is no longer bundled
  with the library. Users who relied on ``openstef-dbc`` must integrate their own data
  access layer.
- **MLflow is optional.** Projects that previously relied on implicit MLflow tracking
  must explicitly install ``openstef-models`` with the MLflow dependency and update
  their storage configuration.
- **Prediction interface changed.** The old task-based pipeline functions
  (``run_train_pipeline``, ``run_forecast_pipeline``) are replaced by the
  ``ForecastingModel.fit()`` / ``ForecastingModel.predict()`` API.
- **Input data format.** The library no longer enforces a rigid column-naming convention
  inherited from the Alliander internal schema. Column names are configured explicitly
  on the dataset and transform objects.
- **Holiday calendar.** The default holiday calendar is no longer hard-coded to the
  Netherlands. You must pass a ``CountryAlpha2`` code (or a custom calendar) when
  constructing feature pipelines that include holiday features.

Bug fixes
^^^^^^^^^

- Fixed O(n²) memory growth when building versioned datasets from many small data parts.
- Corrected lag feature boundary conditions that previously produced off-by-one NaN
  placements at the start of a series.
- Resolved a serialisation round-trip failure that occurred when saving models trained
  with optional postprocessing steps.

----

Version 3.x
-----------

Version 3 was the last release of the original monolithic ``openstef`` package. It
introduced the XGBoost and LightGBM model backends, quantile forecasting, and the
``PredictionJobList`` abstraction for batch forecasting across many grid connection
points.

Key highlights from the 3.x series:

- Quantile regression support for probabilistic forecasts.
- LightGBM backend alongside XGBoost.
- ``openstef-dbc`` integration for direct database access.
- MLflow experiment tracking enabled by default.
- Improved feature engineering: Fourier terms, rolling statistics, and calendar features.
- ``run_train_pipeline`` and ``run_forecast_pipeline`` convenience functions.

.. note::

   Active development on the 3.x series has ended. Critical security fixes may still be
   backported on a best-effort basis, but all new features are developed exclusively on
   the 4.x line.

----

Version 2.x
-----------

Version 2 established the core forecasting loop that persisted through version 3. It
introduced the ``PredictionJob`` data structure, the first XGBoost-based model, and
automated feature selection based on feature importance scores.

Key highlights from the 2.x series:

- ``PredictionJob`` configuration object for per-connection-point model settings.
- XGBoost gradient-boosted tree model as the primary forecaster.
- Automated feature importance-based feature selection.
- Basic lag and calendar feature engineering.
- Initial support for solar irradiance features via ``pvlib``.

----

Version 1.x
-----------

The initial public release of OpenSTEF. Version 1 provided a proof-of-concept
forecasting library targeting Dutch distribution system operator (DSO) use cases, with
a linear regression baseline and a first-generation feature engineering pipeline.

----

Versioning policy
-----------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_ (SemVer):

- **Major version** increments signal breaking API changes. Upgrading across a major
  version boundary requires consulting the :doc:`../user_guide/migration` guide.
- **Minor version** increments add new functionality in a backwards-compatible manner.
- **Patch version** increments contain backwards-compatible bug fixes only.

Pre-release versions (alpha, beta, release candidates) are published to PyPI with the
standard PEP 440 suffixes (``a``, ``b``, ``rc``). Documentation built from a pre-release
or development checkout will display a ``dev`` version banner.

----

How to report issues
--------------------

If you encounter a regression or unexpected behaviour in any supported release, please
open an issue on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_
and include:

- The OpenSTEF package version (``pip show openstef``).
- A minimal reproducible example.
- The full traceback if an exception is raised.