Changelog
=========

This page summarises the changes introduced in each release of the OpenSTEF library. Entries are listed in reverse-chronological order. For step-by-step instructions on upgrading between major versions, see the :doc:`../user_guide/migration` guide.

OpenSTEF follows `semantic versioning <https://semver.org/>`_. In short: a change in the **major** number signals breaking API changes, a change in the **minor** number adds backward-compatible functionality, and a change in the **patch** number covers backward-compatible bug fixes.

To check which version you currently have installed:

.. code-block:: bash

   pip show openstef

To upgrade to the latest release:

.. code-block:: bash

   pip install --upgrade openstef

You can also subscribe to `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_ to receive notifications whenever a new version is published.

----

Version 4.0
-----------

*Status: current stable release*

Version 4.0 is a major architectural overhaul of the OpenSTEF library. The primary goal was to transform OpenSTEF from a tightly-coupled, single-package library into a modular, composable toolkit that works cleanly in a wide range of deployment contexts — from research notebooks to enterprise forecasting pipelines.

.. warning::

   Version 4.0 contains breaking changes relative to 3.x. The ``PredictionJob``-based API, the
   ``openstef-dbc`` database connector, and several hard-coded preprocessing assumptions have been
   removed or restructured. See the :doc:`../user_guide/migration` guide for a full list of changes
   and upgrade instructions.

Monorepo and package structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The library is now distributed as a collection of focused packages within a single monorepo. Each package can be installed independently or together via the ``openstef`` meta-package.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Package
     - Purpose
   * - ``openstef``
     - Meta-package; installs ``openstef-core`` and ``openstef-models``
   * - ``openstef-core``
     - Data types, base classes, shared exceptions, and testing utilities
   * - ``openstef-models``
     - ML models, feature engineering, preprocessing pipelines, explainability, and presets
   * - ``openstef-beam``
     - Backtesting, Evaluation, Analysis, and Metrics (BEAM)
   * - ``openstef-compatibility``
     - Compatibility shim for OpenSTEF 3.x code *(coming soon)*
   * - ``openstef-foundational-models``
     - Deep-learning and foundational model architectures *(coming soon)*

New forecasting workflow API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``PredictionJob`` dictionary-based configuration from 3.x has been replaced by a typed ``ForecastingWorkflow`` API built around composable ``TransformPipeline`` objects. Preprocessing, forecasting, and postprocessing steps are now explicit and independently testable.

.. code-block:: python

   from openstef_models.workflows import ForecastingWorkflowConfig
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.pipelines import TransformPipeline

   config = ForecastingWorkflowConfig(
       model="xgb",
       model_id="my_substation",
       run_name="example_run",
   )

The workflow object returned by a preset or custom factory exposes a consistent ``.fit()`` / ``.predict()`` interface regardless of the underlying model type.

Full type safety
^^^^^^^^^^^^^^^^^

The entire codebase now requires **Python 3.12 or higher** and is fully type-annotated. This enables static analysis tools (``mypy``, ``pyright``) to catch integration errors before runtime. If you need Python 3.10 or 3.11 support, remain on OpenSTEF 3.x.

Decoupled external dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Several dependencies that were previously hard requirements are now optional:

- **MLflow** — model tracking and storage is available via ``openstef_models.integrations.mlflow`` but is not required to train or run forecasts.
- **openstef-dbc** — the Alliander-specific database connector is no longer part of the core library. Users bring their own data loading logic.
- **XGBoost gblinear** — the gblinear booster is now a configurable option rather than a default assumption.

To use MLflow tracking, install the optional extra and configure it through the workflow:

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

   storage = MLFlowStorage(
       tracking_uri="./mlflow_tracking",
       local_artifacts_path="./mlflow_tracking_artifacts",
   )
   callback = MLFlowStorageCallback(storage=storage)

Generalised domain support
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Hard-coded assumptions tied to the Netherlands (Dutch public holidays, Alliander grid topology, fixed timezone) have been removed. Users can now supply custom holiday calendars and location metadata, making the library suitable for forecasting applications outside the original DSO context — including district heating, transport forecasting, and grid-loss estimation in other regions.

Improved preprocessing architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Data preprocessing logic is now centralised in a ``TransformPipeline`` that applies transforms sequentially and is fully serialisable. This replaces scattered, duplicated preprocessing code that previously lived in both validation and model components. Pipelines can be inspected, extended, and unit-tested in isolation.

BEAM evaluation framework
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``openstef-beam`` package introduces a structured backtesting and evaluation framework. It answers the question *"are my model changes statistically significant?"* by running regression tests against stored benchmarks and computing a standard suite of metrics (rMAE, rCRPS, rMAE@peak quantile).

Other improvements
^^^^^^^^^^^^^^^^^^^

- Standardised coding conventions and documentation style across all packages.
- Expanded test coverage with faster, parallelisable test execution.
- Flexible callback mechanism for hooking into training and prediction events without modifying core code.
- Clear interfaces for registering custom models, transforms, and metrics.

----

Version 3.x
-----------

*Status: maintenance mode — critical bug fixes only*

Version 3.x established OpenSTEF as a practical short-term energy forecasting library used in production at Alliander. The series introduced the ``PredictionJob`` abstraction as a self-contained configuration object for a forecasting task, a set of built-in XGBoost and LightGBM models, and integration with ``openstef-dbc`` for data retrieval.

Key characteristics of the 3.x series:

- **PredictionJob API** — a dictionary-like object carrying model type, feature flags, and hyperparameter overrides for a single forecasting point.
- **Pipeline functions** — top-level functions such as ``run_train_pipeline`` and ``run_forecast_pipeline`` that accepted a ``PredictionJob`` and a ``DataBase`` connector.
- **MLflow integration** — built-in, always-on experiment tracking via MLflow.
- **openstef-dbc coupling** — data retrieval was tightly coupled to the ``openstef-dbc`` connector, making it difficult to use the library with other data sources.
- **Python 3.10 / 3.11 support** — the 3.x series supports older Python versions that 4.0 has dropped.

.. note::

   The 3.x ``PredictionJob`` API and ``run_*_pipeline`` functions are not available in 4.0.
   A compatibility shim (``openstef-compatibility``) is planned to ease the transition.
   In the meantime, refer to the :doc:`../user_guide/migration` guide for equivalent 4.0 patterns.

Selected 3.x release highlights
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**3.4** — Introduced probabilistic forecasting with configurable quantile outputs. Added support for
LightGBM alongside the existing XGBoost models.

**3.3** — Added feature importance reporting and basic explainability tooling. Improved handling of
missing measurements in the input time series.

**3.2** — Expanded the built-in feature set with additional lag features and rolling-window statistics.
Improved cross-validation splitting for time-series data.

**3.1** — Performance improvements to the training pipeline. Reduced peak memory usage during
hyperparameter optimisation.

**3.0** — First stable public release. Established the ``PredictionJob`` / ``DataBase`` API contract,
bundled XGBoost as the primary model backend, and published the library to PyPI.

----

Upgrade notes
-------------

Upgrading from 3.x to 4.0
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The 3.x → 4.0 transition is a **breaking change**. The most significant differences are:

- The ``PredictionJob`` object and ``run_*_pipeline`` functions no longer exist.
- Data loading is the caller's responsibility; there is no built-in database connector.
- MLflow is optional and configured explicitly via a callback.
- Python 3.12 or higher is required.

A concise mapping of old patterns to new equivalents is maintained in the :doc:`../user_guide/migration` guide. If you encounter a pattern that is not yet covered, please open an issue on `GitHub <https://github.com/OpenSTEF/openstef/issues>`_.

Staying on 3.x
^^^^^^^^^^^^^^^

If you cannot migrate immediately, pin your dependency to the latest 3.x release:

.. code-block:: bash

   pip install "openstef<4.0"

The 3.x series will continue to receive critical security and bug fixes for a limited period, but no new features will be backported.

----

.. note::

   For the full commit-level history, see the
   `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_ and the repository
   `CHANGELOG.md <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_.