
=========
Changelog
=========

This page summarises what changed in each release of the OpenSTEF library — new features,
bug fixes, deprecations, and breaking changes. Entries are listed in reverse-chronological
order so the most recent release is always at the top.

For step-by-step instructions on upgrading between major versions, see the
:doc:`user_guide/migration` guide.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. A **major** version bump
   signals breaking API changes; a **minor** bump adds backward-compatible features; a
   **patch** bump contains backward-compatible bug fixes only.

   To check which version you have installed:

   .. code-block:: bash

      pip show openstef

   To subscribe to release notifications, watch the
   `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

----

Version 4.0
-----------

*Major release — breaking changes from 3.x*

Version 4.0 is a ground-up architectural refactor of the OpenSTEF library. The primary
goals were to make the library genuinely modular, remove hard-coded assumptions tied to a
single operator's infrastructure, improve type safety throughout the codebase, and broaden
applicability beyond the Dutch DSO context. Users upgrading from 3.x should read the
:doc:`user_guide/migration` guide before updating.

New Features
^^^^^^^^^^^^

**Modular mono-repo package structure**

The library is now distributed as a set of independently installable packages rather than
a single monolith. You can install only the components you need:

- ``openstef-core`` — shared data types, interfaces, base classes, and testing utilities.
  All other packages depend on this foundation.
- ``openstef-models`` — forecasting models, data preprocessing pipelines,
  energy-specific feature transformations, explainability helpers, and presets for common
  use cases.
- ``openstef-meta`` — advanced ensemble and meta-learning model architectures.
- ``openstef-beam`` — the **B**\ acktesting, **E**\ valuation, **A**\ nalysis and
  **M**\ etrics framework. Provides rigorous tooling to answer the question *"are my model
  changes statistically significant?"*, including regression testing against benchmarks.

A convenience meta-package ``openstef`` installs the full stack:

.. code-block:: bash

   # Full installation
   pip install openstef

   # Models only — no evaluation framework overhead
   pip install openstef-models

   # Evaluation framework only
   pip install openstef-beam

**Python 3.12+ and full type safety**

The minimum supported Python version is now 3.12 (Python 3.13 is also supported). The
entire codebase has been annotated with strict type hints, enabling static analysis tools
such as ``mypy`` and ``pyright`` to catch errors before runtime.

.. note::

   If you require Python 3.10 or 3.11 support, remain on OpenSTEF 3.x. The 3.x branch
   continues to receive critical bug fixes.

**Decoupled external dependencies**

Hard runtime dependencies on MLflow, ``openstef-dbc``, and specific XGBoost booster
variants have been removed from the core packages. These are now optional extras:

.. code-block:: bash

   # Install with MLflow experiment tracking support
   pip install "openstef-models[mlflow]"

MLflow integration is available through ``openstef_models.integrations.mlflow`` when the
extra is installed:

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

   # Attach MLflow tracking to a training run without changing model code
   callback = MLFlowStorageCallback(experiment_name="my_forecast_experiment")

**Generalised domain support**

Version 4.0 removes assumptions that were specific to the Netherlands and Alliander's
grid. Configurable holiday calendars, flexible input data schemas, and customisable energy
pricing weights mean the library can now be used for forecasting in any geography or
energy domain — including district heating and non-DSO applications.

**Extensibility interfaces**

Clear, documented interfaces allow custom models, preprocessing transforms, and evaluation
metrics to be plugged in without modifying library code. The ``openstef-core`` package
defines the contracts; ``openstef-models`` provides the reference implementations.

.. code-block:: python

   from openstef_core.datasets import ForecastDataset, ForecastInputDataset
   from openstef_models.models.forecasting.forecaster import Forecaster

   # Subclass Forecaster to register a custom model with the full pipeline
   class MyCustomForecaster(Forecaster):
       ...

**Centralised preprocessing**

Data validation and preprocessing logic that was previously duplicated across model
classes and pipeline steps has been consolidated into a single preprocessing layer within
``openstef-models``. This makes it easier to audit data transformations and reduces
inconsistencies between training and inference paths.

**Improved XGBoost integration**

The XGBoost model now exposes a rich ``XGBoostHyperParams`` class (backed by Pydantic)
covering tree structure, regularisation, sampling strategies, and custom loss functions.
All hyperparameters are validated at construction time:

.. code-block:: python

   from openstef_models.models.forecasting.xgboost import XGBoostHyperParams

   params = XGBoostHyperParams(
       max_depth=6,
       learning_rate=0.05,
       n_estimators=500,
       subsample=0.8,
   )

Breaking Changes
^^^^^^^^^^^^^^^^

The following changes require code updates when upgrading from 3.x. See the
:doc:`user_guide/migration` guide for detailed before/after examples.

- **Package rename and split.** The single ``openstef`` package has been split into
  ``openstef-core``, ``openstef-models``, ``openstef-meta``, and ``openstef-beam``.
  Top-level import paths have changed accordingly.
- **Python version floor raised.** Python 3.10 and 3.11 are no longer supported.
- **MLflow is now optional.** Code that previously imported MLflow utilities from
  ``openstef`` directly must now install ``openstef-models[mlflow]`` and update import
  paths to ``openstef_models.integrations.mlflow``.
- **``openstef-dbc`` removed from core.** Database connector logic is no longer bundled.
  Users who relied on ``openstef-dbc`` must manage that dependency separately.
- **Hard-coded Dutch holiday calendar removed.** Any pipeline that relied on the default
  calendar must now supply a calendar explicitly via the new configuration interface.
- **Input data schema relaxed but changed.** Some previously required columns are now
  optional, and column naming conventions have been updated. See the migration guide for
  the full mapping.

Bug Fixes
^^^^^^^^^

- Fixed an edge case where the preprocessing pipeline could silently drop rows with
  ``NaN`` values in weather feature columns rather than raising a descriptive error.
- Resolved an issue where model serialisation round-trips could produce slightly different
  predictions due to floating-point state not being fully captured in the saved artefact.
- Corrected quantile forecast output ordering when non-standard quantile lists were
  supplied.
- Fixed ``NotFittedError`` not being raised consistently across all model classes when
  ``predict`` was called before ``fit``.

----

Version 3.x
------------

*Previous stable series*

The 3.x series established OpenSTEF as a production-ready short-term energy forecasting
library used in grid operations. It introduced the pipeline-based training and inference
API, quantile forecasting, and the ``PredictionJobManager`` abstraction for batch
operations.

Notable 3.x milestones
^^^^^^^^^^^^^^^^^^^^^^^

**3.4 — Quantile forecasting improvements**

- Extended quantile forecast support to all gradient boosting model backends.
- Added ``rCRPS`` (Continuous Ranked Probability Score) as a built-in evaluation metric,
  enabling probabilistic forecast quality assessment.
- Improved feature importance reporting for quantile models.

**3.3 — Explainability**

- Introduced SHAP-based feature contribution output alongside point forecasts.
- Added ``ContributionsMixin`` to the model interface, making it straightforward to attach
  explainability to any model that supports it.

**3.2 — Performance and stability**

- Reduced peak memory usage during large backtests by streaming intermediate results
  rather than accumulating them in memory.
- Stabilised the ``PredictionJob`` configuration schema and deprecated several
  undocumented keyword arguments that had accumulated over time.

**3.1 — Weather feature pipeline**

- Formalised the weather feature engineering pipeline, including wind-speed
  transformations, solar irradiance proxies, and temperature lag features.
- Added support for multiple weather data sources per prediction job.

**3.0 — Initial pipeline API (major release)**

- Introduced the high-level ``train_model_pipeline`` and ``create_forecast_pipeline``
  functions as the primary entry points for the library.
- Bundled MLflow as a first-class dependency for experiment tracking and model storage.
- Included ``openstef-dbc`` for database connectivity in the reference implementation.
- Required Python 3.8+.

.. note::

   The 3.x series is in maintenance mode. Only critical security and bug fixes will be
   backported. New feature development targets 4.x exclusively.

----

Version 2.x
------------

*Legacy — end of life*

The 2.x series predates the pipeline API and required users to assemble training and
inference workflows manually from lower-level building blocks. It is no longer maintained.
Users on 2.x should migrate to 4.x; the :doc:`user_guide/migration` guide covers the
key patterns.

----

Staying Up to Date
------------------

The recommended way to track new releases is to watch the
`OpenSTEF GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_, which
publishes release notes for every version including patch releases not listed here.

To upgrade to the latest stable release:

.. code-block:: bash

   pip install --upgrade openstef

To pin to a specific major version while still receiving patch updates, use a compatible
release specifier in your ``requirements.txt`` or ``pyproject.toml``:

.. code-block:: text

   # requirements.txt — accept any 4.x patch release
   openstef>=4.0,<5.0

.. code-block:: toml

   # pyproject.toml
   [project]
   dependencies = [
       "openstef>=4.0,<5.0",
   ]