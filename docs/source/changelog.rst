Changelog
=========

OpenSTEF follows `semantic versioning <https://semver.org/>`_ and uses
`Conventional Commits <https://www.conventionalcommits.org/>`_ to drive automated
changelog generation. This page summarises the most significant changes in each
release. For a complete, commit-level history see the
`GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

If a release introduces breaking changes, a migration summary is included below.
Full step-by-step migration instructions live in the User Guide under
:doc:`/user_guide/migration`.

.. note::

   OpenSTEF is a **Python library**, not a deployable application. Version numbers
   follow the individual packages in the monorepo (``openstef-core``,
   ``openstef-models``, ``openstef-beam``, ``openstef-meta``). Major releases
   align across all packages; patch releases may be staggered.

----

Version 4.0 (2025)
------------------

Version 4.0 is a major architectural release. The library has been restructured
from a single package into a **modular monorepo** of focused, independently
installable packages. The primary goals of this release are improved modularity,
stronger type safety, decoupled external dependencies, and broader applicability
beyond the original Alliander/Netherlands use case.

.. mermaid:: /diagrams/root/changelog_diagram_1.mmd

New packages
^^^^^^^^^^^^

The single ``openstef`` package has been split into four packages:

- **openstef-core** — Shared data types, base interfaces, exceptions, and testing
  utilities. Every other package depends on this foundation.
- **openstef-models** — Forecasting models, data preprocessing pipelines,
  energy-specific feature transformations, explainability helpers, and
  ready-to-use presets.
- **openstef-meta** — Meta-learning layer with modern ensemble models and advanced
  model architectures (e.g., ``LGBMCombiner``).
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics (BEAM).
  Answers the question *"are my model changes statistically significant?"* through
  regression testing against benchmarks.

You can install only the packages you need:

.. code-block:: bash

   # Core data types and interfaces only
   pip install openstef-core

   # Forecasting models (pulls in openstef-core automatically)
   pip install openstef-models

   # Full stack including backtesting and meta-learning
   pip install openstef-models openstef-meta openstef-beam

New dataset types (openstef-core)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ad-hoc ``pandas.DataFrame`` convention used in v3 has been replaced by a
hierarchy of validated dataset classes in ``openstef_core.datasets``:

.. code-block:: python

   from openstef_core.datasets import (
       TimeSeriesDataset,
       VersionedTimeSeriesDataset,
       ForecastInputDataset,
       ForecastDataset,
       EnsembleForecastDataset,
       EnergyComponentDataset,
   )

Each class validates its contents on construction, catching data-quality issues
(missing columns, invalid horizons, wrong dtypes) before they propagate into
model training or inference.

``VersionedTimeSeriesDataset`` is a new addition that tracks *when* each
observation became available. This enables realistic backtesting that respects
data-availability constraints — for example, delayed smart-meter reads or
delayed weather-forecast delivery.

New model API (openstef-models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Models now expose a consistent interface through the ``Forecaster`` base class and
use ``HyperParams`` (Pydantic models) for configuration, giving full type safety
and IDE auto-completion:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import (
       LGBMForecaster,
       LGBMHyperParams,
   )

   hyperparams = LGBMHyperParams(
       n_estimators=200,
       max_depth=8,
       learning_rate=0.05,
       reg_alpha=0.1,
       reg_lambda=1.0,
   )

   model = LGBMForecaster(hyperparams=hyperparams)

Quantile regression is built in — pass a list of quantiles at fit time rather
than training separate models:

.. code-block:: python

   from openstef_core.types import Quantile

   quantiles: list[Quantile] = [0.1, 0.5, 0.9]
   model.fit(train_dataset, quantiles=quantiles)
   forecast = model.predict(input_dataset)

Explainability (openstef-models)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Models that mix in ``ContributionsMixin`` and ``ExplainableForecaster`` expose
feature-contribution decomposition out of the box, without requiring a separate
SHAP post-processing step.

Backtesting and evaluation (openstef-beam)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The new ``openstef-beam`` package provides a structured evaluation harness:

- Run backtests that respect data-availability windows via
  ``VersionedTimeSeriesDataset``.
- Compare model versions against stored benchmarks to detect regressions.
- Compute energy-domain metrics: rMAE, rCRPS, rMAE@50th-quantile-at-peaks.

Generalised domain support
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Hard-coded assumptions tied to the Netherlands (holiday calendars, grid topology,
specific column names) have been removed or made configurable. OpenSTEF 4.0 is
designed to support congestion management, transport forecasting, grid-losses
forecasting, district heating, and other energy domains without requiring
source-code modifications.

Breaking changes in 4.0
^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

   Version 4.0 contains **significant breaking changes**. Code written against
   v3 will not run without modification. See :doc:`/user_guide/migration` for
   full migration instructions.

Key breaking changes at a glance:

- **Package rename / split.** ``import openstef`` no longer works. Replace with
  the appropriate sub-package (``openstef_core``, ``openstef_models``, etc.).
- **DataFrame inputs removed.** Pipeline entry points now require typed dataset
  objects (``ForecastInputDataset``, etc.) instead of bare ``pandas.DataFrame``.
- **MLflow dependency decoupled.** MLflow is no longer a required dependency.
  Experiment tracking is opt-in via a callback/plugin interface.
- **openstef-dbc removed from core.** Database connectivity has been extracted;
  bring your own data-loading layer.
- **XGBoost gblinear removed from defaults.** The default model preset is now
  LightGBM-based. XGBoost remains available as an optional extra.
- **HyperParams are Pydantic models.** Dictionary-based hyperparameter passing is
  no longer supported; use the typed ``HyperParams`` classes.
- **Holiday calendar is configurable.** The Dutch holiday calendar is no longer
  hard-coded; pass a calendar object at pipeline construction time.

----

Version 3.x
-----------

Version 3 established OpenSTEF as a production-ready forecasting library used
inside Alliander's grid operations. The series focused on stability, MLflow
integration, and expanding the set of supported model types.

Version 3.x highlights
^^^^^^^^^^^^^^^^^^^^^^^

- Gradient-boosted tree models (XGBoost, LightGBM) as primary forecasters.
- Integrated MLflow experiment tracking and model registry.
- ``openstef-dbc`` connector for reading from and writing to Alliander's internal
  data platform.
- Quantile forecasting via multi-quantile regression wrappers.
- SHAP-based feature importance and explainability.
- Automated retraining pipelines triggered by model-quality degradation.
- Dutch national holiday calendar built into the feature-engineering layer.
- ``PredictionJobList`` abstraction for managing multiple concurrent forecasting
  tasks.

Notable 3.x patch releases
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **3.x.y** — Improved handling of missing weather data; validation now logs a
  warning and continues rather than raising an unhandled exception.
- **3.x.y** — Performance improvements to the feature-engineering pipeline,
  reducing training time on large datasets.
- **3.x.y** — Extended quantile support to cover the full ``[0.01, 0.99]`` range.
- **3.x.y** — Added ``rMAE`` and ``skill score`` metrics alongside the existing
  MAE/RMSE reporting.

.. note::

   Detailed patch-level notes for the 3.x series are available on the
   `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

----

Version 2.x
-----------

Version 2 introduced the pipeline abstraction that became the foundation for all
later work, and was the first release made publicly available under an open-source
licence.

Version 2.x highlights
^^^^^^^^^^^^^^^^^^^^^^^

- ``create_forecast_pipeline`` and ``train_model_pipeline`` as the primary public
  API surface.
- XGBoost as the default model backend.
- Weather-feature integration (temperature, irradiance, wind speed).
- Lag-feature engineering for short-term temporal patterns.
- Initial quantile forecasting support (fixed set of quantiles).
- ``PredictionJob`` dataclass for describing a forecasting task.
- First public release on PyPI.

----

Staying current
---------------

OpenSTEF publishes releases to PyPI. To check your installed version and upgrade:

.. code-block:: bash

   # Check what is installed
   pip show openstef-models

   # Upgrade to the latest release
   pip install --upgrade openstef-models openstef-core

Subscribe to `GitHub release notifications
<https://github.com/OpenSTEF/openstef/releases>`_ to be notified when new
versions are published.

For projects that need to pin a version, all packages declare their dependencies
with lower and upper bounds so that ``pip``/``uv`` constraint solving works
reliably across the monorepo packages.

----

Deprecation policy
------------------

OpenSTEF follows these conventions for managing deprecations:

- A feature marked ``deprecated`` in release ``N`` will emit a
  ``DeprecationWarning`` at runtime.
- The feature will be **removed no earlier than release** ``N+1`` for minor
  deprecations, or ``N+2`` for features that require significant migration effort.
- Breaking changes are only introduced in **major version bumps** (i.e., the
  ``MAJOR`` component of the ``MAJOR.MINOR.PATCH`` version number).
- All deprecations are noted in this changelog and, where migration effort is
  non-trivial, documented in :doc:`/user_guide/migration`.

If you encounter an undocumented breaking change, please
`open an issue <https://github.com/OpenSTEF/openstef/issues>`_ so it can be
documented and, where possible, mitigated.