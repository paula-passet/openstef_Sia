Changelog
=========

This page summarises the notable changes in each OpenSTEF release. Entries are
organised chronologically, newest first, and grouped by release series. Each
entry covers new features, bug fixes, deprecations, and breaking changes.

For step-by-step instructions on upgrading between major versions, see the
:doc:`../user_guide/migration` guide.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. A **major**
   version bump signals breaking API changes; a **minor** bump adds
   backward-compatible features; a **patch** bump contains backward-compatible
   bug fixes only.

   Subscribe to `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_
   to receive notifications when new versions are published.

----

Version 4.x Series
-------------------

The 4.x series is a major architectural overhaul that restructures OpenSTEF
from a monolithic library into a **modular monorepo** of focused, independently
installable packages. The public API has been redesigned around Pydantic-based
configuration objects, typed datasets, and composable pipeline steps.

.. mermaid:: diagrams/root/changelog_diagram_1.mmd

4.0.0 — Modular Monorepo Architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Breaking release — see the* :doc:`../user_guide/migration` *guide before upgrading from 3.x.*

**New packages**

The single ``openstef`` wheel has been replaced by a set of focused packages.
Installing the ``openstef`` meta-package pulls in the recommended defaults:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Package
     - Purpose
   * - ``openstef``
     - Meta-package; installs ``openstef-core`` and ``openstef-models``
   * - ``openstef-core``
     - Shared dataset types, base classes, interfaces, and exceptions
   * - ``openstef-models``
     - ML models, feature engineering pipelines, and presets
   * - ``openstef-beam``
     - Backtesting, Evaluation, Analysis, and Metrics (BEAM)
   * - ``openstef-compatibility``
     - Compatibility shim for 3.x code *(coming soon)*
   * - ``openstef-foundational-models``
     - Deep-learning and foundation model integrations *(coming soon)*

Install only what you need:

.. code-block:: bash

   # Full default install
   pip install openstef

   # Core types + models only
   pip install openstef-models

   # Add backtesting and evaluation tools
   pip install openstef-beam

**New features**

- **Typed dataset layer** — ``ForecastDataset``, ``ForecastInputDataset``, and
  ``TimeSeriesDataset`` (from ``openstef-core``) replace raw ``pandas``
  ``DataFrame`` objects as the primary data contract between pipeline stages.
  This enables static type checking and runtime validation throughout the
  library.

- **Pydantic-based configuration** — Model hyperparameters and pipeline
  settings are now expressed as ``HyperParams`` subclasses (Pydantic models),
  giving you IDE auto-complete, runtime validation, and clear documentation of
  every parameter.

- **Composable preprocessing pipelines** — Feature engineering is now
  expressed as ordered lists of transformer steps (e.g.
  ``HolidayFeatureAdder``, ``DatetimeFeaturesAdder``, ``Imputer``) that are
  assembled by a preset or constructed manually. This makes it straightforward
  to insert custom steps without subclassing.

- **LGBMLinear forecaster** — A new ``LGBMLinearForecaster`` that combines
  gradient-boosted trees with linear leaves, well-suited to load profiles with
  strong linear components.

- **BEAM backtesting framework** — ``openstef-beam`` introduces a
  ``BacktestPipeline`` that replays a ``VersionedTimeSeriesDataset`` through
  a forecaster, producing a ``TimeSeriesDataset`` of out-of-sample predictions
  ready for metric evaluation.

- **Explainability mixins** — ``ContributionsMixin`` and
  ``ExplainableForecaster`` (from ``openstef-models``) provide a consistent
  interface for feature-contribution analysis across all built-in model types.

- **Model state migration hooks** — Every model exposes a ``migrate_state``
  class method so that persisted model artefacts from older minor versions can
  be loaded and upgraded automatically without manual intervention.

**Breaking changes**

- The ``PredictionJobDataClass`` and the ``pipeline_api`` module from 3.x have
  been removed. Use the new preset-based API or construct a pipeline manually
  from ``openstef-models`` components.

- All public functions that previously accepted ``pd.DataFrame`` directly now
  expect the appropriate ``openstef-core`` dataset type. A compatibility shim
  (``openstef-compatibility``) will be available to ease the transition.

- Hyperparameter dictionaries passed as plain ``dict`` objects are no longer
  accepted; use the corresponding ``HyperParams`` subclass instead.

- The ``**kwargs`` configuration pattern is deprecated. Pass a typed
  configuration object to ``create_forecaster`` (or the relevant preset):

  .. code-block:: python

     # Deprecated (3.x style) — emits DeprecationWarning
     forecaster = create_forecaster("xgboost", n_estimators=100, max_depth=6)

     # Recommended (4.x style)
     from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams

     hyperparams = XGBoostHyperParams(n_estimators=100, max_depth=6)
     forecaster = XGBoostForecaster(quantiles=[0.1, 0.5, 0.9], hyperparams=hyperparams)

- Python 3.9 is no longer supported. The minimum supported version is
  **Python 3.11**.

**Bug fixes**

- Fixed a crash in the validation layer when weather feature columns were
  entirely absent from the input dataset; the pipeline now logs a warning and
  continues with the available features.

- Resolved an edge case where quantile outputs were not monotonically ordered
  after post-processing when the confidence interval applicator was disabled.
  ``QuantileSorter`` is now always appended as the final post-processing step
  in all built-in presets.

- Corrected an off-by-one error in horizon indexing that caused the last
  forecast horizon to be silently dropped when ``horizons`` was specified as a
  closed range.

**Deprecations**

- ``old_function_name`` → use ``new_function_name``. The old symbol will be
  removed in 5.0.

- Passing hyperparameters as ``**kwargs`` to ``create_forecaster`` is
  deprecated and will be removed in 5.0. Migrate to typed ``HyperParams``
  objects.

----

Version 3.x Series
-------------------

The 3.x series established OpenSTEF as a general-purpose short-term energy
forecasting library. It introduced probabilistic (quantile) forecasting, the
``PredictionJobDataClass`` configuration contract, and a growing catalogue of
gradient-boosted tree models.

3.x — Selected highlights
^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Probabilistic forecasting** — All built-in models gained multi-quantile
  output support, enabling confidence-interval generation alongside point
  forecasts.

- **XGBoost and LightGBM models** — ``XGBoostForecaster`` and
  ``LGBMForecaster`` became the primary production-grade models, with
  ``GBLinearForecaster`` available for settings where a linear base learner is
  preferred.

- **Holiday and datetime feature engineering** — Dedicated transformers for
  calendar features (day-of-week, hour-of-day, public holidays by country
  code) were added to the feature engineering layer.

- **Imputation strategies** — A configurable ``Imputer`` step with
  ``mean``, ``median``, and ``forward-fill`` strategies was introduced to
  handle missing measurements gracefully in production pipelines.

- **Structured logging** — The library adopted structured, context-rich log
  messages throughout, making it easier to trace pipeline execution in
  aggregated log systems.

- **Conventional Commits and automated releases** — The project adopted the
  `Conventional Commits <https://www.conventionalcommits.org/>`_ specification,
  enabling automated changelog generation and semantic version bumping via CI.

.. note::

   Detailed patch-level release notes for the 3.x series are available on the
   `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

----

Upgrade Notes
-------------

3.x → 4.x
^^^^^^^^^^

The 4.x release is a **major breaking change**. The key steps are:

1. Replace ``pip install openstef`` with the new meta-package (same command,
   new content).
2. Migrate ``PredictionJobDataClass`` usage to the typed configuration and
   preset API.
3. Replace raw ``pd.DataFrame`` inputs with the appropriate
   ``openstef-core`` dataset types.
4. Replace hyperparameter ``dict`` / ``**kwargs`` usage with typed
   ``HyperParams`` subclasses.

Full migration instructions, including before/after code examples, are in the
:doc:`../user_guide/migration` guide.

Checking your installed version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # pip
   pip show openstef

   # uv
   uv list | grep openstef

   # conda / pixi
   conda list openstef
   pixi list | grep openstef

Upgrading to the latest release
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # pip
   pip install --upgrade openstef

   # uv
   uv upgrade openstef

   # conda
   conda update openstef

   # pixi
   pixi upgrade openstef

----

How the Changelog Is Generated
--------------------------------

OpenSTEF uses `Conventional Commits <https://www.conventionalcommits.org/>`_
to drive automated changelog generation and semantic version bumping. Every
merged pull request carries a structured commit message of the form:

.. code-block:: text

   <type>[optional scope]: <description>

   [optional body]

   [optional footer(s)]

The ``type`` field determines how the version number is incremented:

- ``feat`` → minor version bump
- ``fix``, ``perf``, ``refactor`` → patch version bump
- Any commit with a ``!`` suffix or a ``BREAKING CHANGE:`` footer → major
  version bump

This means the changelog you see on the
`GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_ is
generated automatically from commit history and reflects the full set of
changes in each release, including scoped entries (e.g.
``feat(models): …``, ``fix(validation): …``).