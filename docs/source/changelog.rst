Changelog
=========

This page records the version history of OpenSTEF, summarising new features, bug fixes, and
breaking changes for each release. Entries are listed in reverse-chronological order so the
most recent changes are always at the top.

.. note::

   OpenSTEF is a Python **library**. Version numbers follow
   `Semantic Versioning <https://semver.org/>`_: ``MAJOR.MINOR.PATCH``.
   A major-version bump signals breaking API changes; a minor bump adds
   backwards-compatible functionality; a patch bump contains bug fixes only.

   If you are upgrading from v3 to v4, see the dedicated
   :doc:`/user_guide/migration_guide` for step-by-step instructions.

----

Version 4.0 (current)
----------------------

OpenSTEF 4.0 is a **major architectural release**. The monolithic v3 package has been
replaced by a modular mono-repo composed of several self-contained, independently
installable packages. This restructuring makes it possible to use only the parts of the
library that are relevant to your project, reduces dependency bloat, and provides clear
extension points for custom models, transforms, and metrics.

New packages
^^^^^^^^^^^^

The v4 library is distributed as five co-versioned packages:

- **openstef-core** — data types, base classes, shared exceptions, and testing utilities.
  Every other package depends on this one.
- **openstef-models** — forecasting models, energy-specific feature transforms, data
  preprocessing pipelines, explainability helpers, and ready-to-use presets.
- **openstef-meta** — meta-learning and ensemble model architectures built on top of
  ``openstef-models``.
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM). Answers the
  question *"are my model changes statistically significant?"* and provides regression
  testing against benchmarks.
- **openstef** (meta-package) — installs all of the above as a convenience.

You can install the full suite or pick individual packages:

.. code-block:: python

   # Full installation
   # pip install openstef

   # Lightweight installation — core data types and models only
   # pip install openstef-core openstef-models

New features
^^^^^^^^^^^^

**Modular, composable pipelines**

The ``ForecastingModel`` class in ``openstef-models`` combines preprocessing, prediction,
and postprocessing into a single, serialisable object. Preprocessing is expressed as a
``FeaturePipeline`` composed of individual ``Transform`` steps, making it straightforward
to add, remove, or reorder feature-engineering stages without touching model code.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.pipeline.feature_pipeline import FeaturePipeline
   from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder
   from openstef_models.storage.local_model_storage import LocalModelStorage

   # Build a feature pipeline with lag features
   feature_pipeline = FeaturePipeline(
       transforms=[
           VersionedLagsAdder(column="load", lags=[timedelta(hours=24), timedelta(hours=48)]),
       ]
   )

**Versioned time-series datasets**

``VersionedTimeSeriesDataset`` tracks *when* each measurement became available, enabling
realistic backtesting that respects data-availability constraints (e.g. delayed meter
readings, revised weather forecasts). The implementation uses lazy composition to avoid
the O(n²) space complexity that arises when naively concatenating DataFrames with
misaligned ``(timestamp, available_at)`` pairs.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Simulate a measurement that arrives six hours after the fact
   load_data = pd.DataFrame(
       {"load": [42.1, 43.5, 41.8], "available_at": [datetime(2025, 1, 1, 6, 0)] * 3},
       index=pd.DatetimeIndex([
           datetime(2025, 1, 1, 0, 0),
           datetime(2025, 1, 1, 0, 15),
           datetime(2025, 1, 1, 0, 30),
       ]),
   )
   part = TimeSeriesDataset(load_data, timedelta(minutes=15))
   dataset = VersionedTimeSeriesDataset([part])

   # Reconstruct the view of the world at a specific point in time
   snapshot = dataset.select_version(datetime(2025, 1, 1, 7, 0))

**Preset workflows**

``openstef-models`` ships with preset configurations for the most common energy-forecasting
scenarios. A preset bundles a recommended model, feature pipeline, and evaluation
configuration so you can get a working baseline with minimal boilerplate:

.. code-block:: python

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.presets import get_forecasting_preset

   dataset = create_synthetic_forecasting_dataset()
   model = get_forecasting_preset("load_forecasting")
   fit_result = model.fit(dataset)
   forecast = model.predict(dataset)

**Ensemble models (openstef-meta)**

``EnsembleForecastingModel`` in ``openstef-meta`` runs a shared preprocessing stage
followed by N independent base forecasters whose outputs are combined by a configurable
combiner. Component-level fit results and hyperparameters are accessible individually,
making it easy to inspect or replace a single component without rebuilding the whole
ensemble.

.. code-block:: python

   from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel

   ensemble = EnsembleForecastingModel(
       forecaster_configs={"xgb": xgb_forecaster, "lgbm": lgbm_forecaster},
   )
   result = ensemble.fit(dataset)
   print(result.component_fit_results())

**Backtesting and evaluation (openstef-beam)**

The ``openstef-beam`` package provides an ``EvaluationPipeline`` that runs a model over a
historical window and computes configurable metrics. Metrics are declared as
``MetricProvider`` objects, keeping evaluation logic separate from model code.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
   from openstef_beam.evaluation.metric_providers import R2Provider

   config = EvaluationConfig(metrics=[R2Provider()])
   pipeline = EvaluationPipeline(model=model, config=config)
   results = pipeline.run(dataset)

**Full type safety**

All public APIs are fully type-annotated. Pydantic v2 is used throughout for
configuration objects and data-transfer types, providing runtime validation and clear
error messages when configuration values are invalid.

**Generalised domain support**

Hard-coded assumptions tied to the Dutch energy grid (holiday calendars, specific
timezone handling, fixed input column names) have been replaced by configurable
parameters. Country codes follow the ISO 3166-1 alpha-2 standard via
``pydantic-extra-types``, and holiday calendars can be customised per deployment.

Breaking changes in 4.0
^^^^^^^^^^^^^^^^^^^^^^^^

4.0 is a **major version** and contains breaking changes relative to v3. The key
differences are:

- The single ``openstef`` package has been split into multiple packages. Direct imports
  from ``openstef.*`` no longer work; use the appropriate sub-package (``openstef_core``,
  ``openstef_models``, ``openstef_beam``, or ``openstef_meta``).
- The v3 ``PredictionJobDataClass`` and related pipeline functions
  (``run_train_pipeline``, ``run_forecast_pipeline``) have been removed. Use
  ``ForecastingModel`` and ``VersionedTimeSeriesDataset`` instead.
- MLflow and ``openstef-dbc`` are no longer hard dependencies. Model storage is handled
  through the ``ModelStorage`` interface; ``LocalModelStorage`` is provided out of the
  box.
- Hard-coded column names (``load``, ``radiation``, etc.) have been replaced by
  configurable feature names passed through the pipeline configuration.
- The ``xgboost/gblinear`` booster is no longer bundled; bring your own model by
  implementing the ``Forecaster`` interface.

.. warning::

   Upgrading from v3 to v4 requires code changes. See the
   :doc:`/user_guide/migration_guide` for a complete mapping of old APIs to their v4
   equivalents, including worked examples.

Bug fixes and quality improvements in 4.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Centralised data preprocessing logic eliminates duplicated validation code that
  previously existed in both the training and inference paths.
- Test coverage has been substantially increased; the test suite now runs in isolation
  without requiring external services.
- Coding style and docstring conventions are standardised across all packages.
- The O(n²) space complexity bug in versioned dataset concatenation has been resolved
  through lazy composition.

----

Version 3.x
-----------

Version 3 was the first publicly released series of OpenSTEF. It established the core
concept of a prediction-job-driven pipeline for short-term energy forecasting and
introduced XGBoost-based models as the primary forecasting engine.

Key highlights of the 3.x series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Prediction job abstraction** — forecasting configuration was expressed as a
  ``PredictionJobDataClass``, a dataclass describing the target location, model type,
  horizon, and feature set.
- **Pipeline functions** — ``run_train_pipeline`` and ``run_forecast_pipeline`` provided
  high-level entry points that handled data loading, feature engineering, model training,
  and result storage in a single call.
- **XGBoost and LightGBM models** — gradient-boosted tree models were the primary
  forecasting engines, with support for quantile regression.
- **MLflow integration** — model artefacts and metrics were logged to MLflow by default.
- **openstef-dbc connector** — a companion package (``openstef-dbc``) provided database
  connectivity for reading measurement data and writing forecasts.
- **Holiday and lag features** — built-in feature engineering for Dutch public holidays
  and configurable lag windows.
- **SHAP-based explainability** — feature contributions were computed using SHAP values
  and exposed through the pipeline result.

Notable 3.x patch releases
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The 3.x series received a number of patch and minor releases addressing stability and
accuracy issues. Highlights include:

- Improved handling of missing data in the feature-engineering stage, reducing silent
  NaN propagation into model inputs.
- Fixes to the quantile-regression post-processing step that could produce
  non-monotonic quantile bands under certain input distributions.
- Performance improvements to lag-feature computation for long historical windows.
- Corrections to the Dutch holiday calendar for edge cases around multi-day holidays.

.. note::

   The 3.x series is no longer actively maintained. Critical security fixes may be
   back-ported on a best-effort basis, but new features will only be developed in v4.
   Users are encouraged to migrate to v4 at their earliest convenience.

----

Version 2.x
-----------

Version 2 introduced the first stable public API for OpenSTEF and established the
prediction-job concept that carried forward into v3. It also added initial support for
probabilistic forecasting through quantile regression.

Key highlights of the 2.x series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Initial stable public release of the library.
- Introduction of the prediction-job pattern for configuring forecasting runs.
- Quantile regression support for probabilistic forecasts.
- Basic feature engineering: lag features, time-of-day, day-of-week, and seasonal
  indicators.
- Integration with the Alliander internal data infrastructure.

.. note::

   Version 2.x is end-of-life. No further releases are planned.

----

Version 1.x
-----------

Version 1 was an internal prototype used within Alliander before OpenSTEF was open-sourced
under the LF Energy umbrella. The API was not stable and is not documented here. It is
listed for completeness only.

----

Deprecation policy
------------------

OpenSTEF follows a structured deprecation process:

- Features scheduled for removal are marked with a ``DeprecationWarning`` for at least
  one minor release before they are removed.
- Breaking changes are only introduced in major-version releases.
- The :doc:`/user_guide/migration_guide` is updated alongside every major release and
  provides explicit before/after code examples for all removed or renamed APIs.

If you rely on a feature that is marked as deprecated, please open an issue on the
`OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_ to discuss
migration options before the removal release.

----

How to read this changelog
---------------------------

Each release section is organised as follows:

- **New features** — capabilities that did not exist in the previous release.
- **Breaking changes** — changes that require updates to calling code.
- **Bug fixes** — corrections to incorrect behaviour.
- **Quality improvements** — refactors, test coverage, documentation, and performance
  work that does not change the public API.

For detailed migration instructions between any two major versions, refer to the
:doc:`/user_guide/migration_guide`.