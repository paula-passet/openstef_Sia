Changelog
=========

This page records the version history of the OpenSTEF library, summarising new features, bug fixes,
and breaking changes for each release. Entries are listed in reverse chronological order so the most
recent changes appear first.

For step-by-step instructions on upgrading between major versions, see the
:doc:`/user_guide/migration_guide`.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. A major version bump (e.g. 3.x → 4.0)
   signals breaking API changes. Minor and patch releases are backward-compatible within the same major
   series.

----

Version 4.0 (Current)
----------------------

OpenSTEF 4.0 is a major architectural release. The library has been restructured from a single
monolithic package into a **modular mono-repo** of focused, independently installable packages.
This is the most significant change since the project's inception and affects every part of the
public API.

New Packages
^^^^^^^^^^^^

The single ``openstef`` package has been split into five co-ordinated packages. You can install
them individually or pull everything in at once:

.. code-block:: bash

   # Install the full framework
   pip install openstef

   # Or install only what you need
   pip install openstef-core
   pip install openstef-models
   pip install openstef-beam
   pip install openstef-meta

The packages and their responsibilities are:

- **openstef-core** — Data types, base classes, shared exceptions, and testing utilities.
  Every other package depends on this foundation.
- **openstef-models** — Forecasting models, feature engineering pipelines, energy-specific
  transforms, explainability helpers, and ready-to-use presets.
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics (BEAM). Answers the
  question *"are my model changes statistically significant?"* and provides regression testing
  against benchmarks.
- **openstef-meta** — Meta-learning and modern ensemble architectures built on top of the
  core and models packages.
- **openstef** — Convenience meta-package that installs all of the above.

New Features
^^^^^^^^^^^^

**Modular, composable pipeline API**

The new ``ForecastingModel`` and ``FeaturePipeline`` classes let you assemble preprocessing,
forecasting, and postprocessing steps independently and combine them into a single object:

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.presets import CustomForecastingWorkflow
   from openstef_models.storage import LocalModelStorage

   # Build a workflow from a declarative configuration
   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       run_name="v4-demo",
       model="gblinear",
       horizons=[timedelta(hours=24), timedelta(hours=48)],
       quantiles=[0.1, 0.5, 0.9],
       mlflow_storage=None,
   )

   storage = LocalModelStorage(base_path=Path("./models"))
   workflow = CustomForecastingWorkflow(config=config, model_storage=storage)

   dataset = create_synthetic_forecasting_dataset()
   result = workflow.fit(dataset)
   forecast = workflow.predict(dataset)

**VersionedTimeSeriesDataset**

A new dataset type that tracks *when* each measurement became available, enabling realistic
point-in-time backtesting without look-ahead bias. The design avoids the O(n²) space complexity
that arose from naively concatenating DataFrames with misaligned ``(timestamp, available_at)``
pairs by using lazy composition:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

   data = pd.DataFrame(
       {"load": [100.0, 110.0, 120.0, 130.0],
        "available_at": pd.date_range("2025-01-01 10:00", periods=4, freq="h")},
       index=pd.date_range("2025-01-01 10:00", periods=4, freq="h"),
   )
   dataset = VersionedTimeSeriesDataset.from_dataframe(data, timedelta(hours=1))
   snapshot = dataset.select_version()

**Versioned model state and automatic migration**

All serialisable objects now carry an integer ``__version__`` field in their persisted state.
When loading a model saved by an older release, ``_migrate_state`` is called automatically to
bring the state up to the current schema. A ``UserWarning`` is raised when loading legacy objects
that pre-date the versioning system, and again when a saved version is *newer* than the running
code (forward compatibility is not guaranteed).

**Lag features with data-availability constraints**

``VersionedLagsAdder`` creates lag features that respect the ``available_at`` timestamps in a
``VersionedTimeSeriesDataset``, preventing accidental use of data that would not yet have arrived
at prediction time:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import VersionedLagsAdder

   transform = VersionedLagsAdder(
       feature="load",
       lags=[timedelta(hours=-1), timedelta(hours=-2)],
   )
   result = transform.transform(dataset)

**Built-in visualisation via openstef-beam**

Interactive forecast plots are provided by ``ForecastTimeSeriesPlotter`` in
``openstef_beam.analysis.plots``, removing the need to reach for external plotting libraries
for routine inspection:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=snapshot.data["load"])
       .add_model(
           model_name="gblinear",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot()
   )
   fig.write_html("forecast_plot.html")

**Decoupled optional dependencies**

XGBoost, LightGBM, and MLflow are now optional extras rather than hard requirements. Install
only what your environment needs:

.. code-block:: bash

   pip install "openstef-models[xgb-cpu]"   # XGBoost on CPU
   pip install "openstef-models[xgb-gpu]"   # XGBoost with GPU support
   pip install "openstef-models[lgbm]"      # LightGBM

**Broader domain support**

Hard-coded assumptions tied to the Dutch grid (Alliander-specific holiday calendars, fixed
energy-price columns, rigid input schemas) have been replaced with configurable parameters.
OpenSTEF 4.0 is designed to support congestion management, transport forecasting, grid-losses
forecasting, district heating, and other energy domains out of the box.

**Full type safety**

The entire codebase now carries complete type annotations. Pydantic v2 is used for all
configuration and data-model classes, providing runtime validation and clear error messages.
Python 3.12 or later is required.

Breaking Changes
^^^^^^^^^^^^^^^^

.. warning::

   Version 4.0 introduces breaking changes across the entire public API. Upgrading from 3.x
   requires code changes. See the :doc:`/user_guide/migration_guide` for detailed steps.

The most significant breaking changes are:

- **Package rename and split.** The old ``openstef`` single-package imports (e.g.
  ``from openstef.pipeline import ...``) no longer exist. All imports must be updated to the
  new package names (``openstef_core``, ``openstef_models``, ``openstef_beam``, ``openstef_meta``).
- **Python version.** Python 3.11 and earlier are no longer supported. Python ≥ 3.12 is required.
- **``openstef-dbc`` removed from core.** Database connectivity (previously bundled via
  ``openstef-dbc``) is no longer a dependency of the main packages. Users who relied on this
  must manage the dependency themselves or adapt to the new storage abstractions.
- **MLflow is optional.** Code that assumed MLflow was always present will need to guard against
  its absence or explicitly install ``openstef-models`` with the ``mlflow-skinny`` dependency
  (included by default) or configure ``mlflow_storage=None`` to disable tracking.
- **Input data schema relaxed but changed.** The rigid ``PredictionJobDataClass`` from v3 has
  been replaced by ``ForecastingWorkflowConfig`` (Pydantic-based). Field names and types differ;
  consult the API reference for the new schema.
- **Serialised model format.** Models saved with v3 cannot be loaded directly by v4. The new
  versioned-state system requires a one-time re-training or manual state migration.

Bug Fixes
^^^^^^^^^

- Resolved O(n²) memory growth when concatenating versioned datasets with many misaligned
  ``available_at`` timestamps.
- Fixed incorrect lag feature values when a ``VersionedTimeSeriesDataset`` contained rows
  with mixed horizons.
- Corrected forward-compatibility warning logic: the warning is now raised only when the saved
  version is strictly greater than the current ``_VERSION``, not when they are equal.

----

Version 3.x Series
-------------------

The 3.x series was the last release of the original monolithic ``openstef`` package. It
established the core forecasting workflow — prediction jobs, XGBoost/GBLinear models, MLflow
experiment tracking, and the ``openstef-dbc`` database connector — that underpins the 4.0
redesign.

Notable milestones in the 3.x series included:

- Introduction of probabilistic forecasting with configurable quantiles.
- XGBoost and GBLinear model support with automated hyperparameter optimisation.
- MLflow integration for experiment tracking and model registry.
- The ``PredictionJobDataClass`` configuration schema.
- Initial support for solar and wind feature engineering via ``pvlib``.

.. note::

   Detailed patch-level release notes for the 3.x series are maintained in the
   `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_ of the legacy
   repository.

----

Deprecation Policy
------------------

OpenSTEF follows a two-release deprecation cycle for non-breaking changes:

1. A feature or API is marked deprecated in release *N* with a ``DeprecationWarning`` and a
   note in the changelog.
2. The deprecated item is removed no earlier than release *N+2*.

Breaking changes that cannot follow this cycle (such as the v3 → v4 architectural split) are
announced in advance via GitHub Discussions and documented in the
:doc:`/user_guide/migration_guide`.

----

How to Read This Changelog
---------------------------

Each release section is organised as follows:

- **New Features** — additions that are backward-compatible.
- **Bug Fixes** — corrections to existing behaviour.
- **Breaking Changes** — changes that require action from library users.
- **Deprecations** — features scheduled for removal in a future release.

For the complete commit-level history, see the
`GitHub repository <https://github.com/OpenSTEF/openstef>`_.