Changelog
=========

OpenSTEF follows `semantic versioning <https://semver.org/>`_ (``MAJOR.MINOR.PATCH``). This page
summarises what changed in each release — new features, bug fixes, deprecations, and breaking changes.
For step-by-step instructions on upgrading between major versions, see the
:doc:`../user_guide/migration` guide.

To check which version you have installed:

.. code-block:: bash

   pip show openstef

Subscribe to `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_ to receive
notifications whenever a new version is published.

.. note::

   Release notes below reflect the publicly documented history of the project. For the
   complete, commit-level history see the
   `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

----

Version 4.x
-----------

4.0.0 — Monorepo Architecture & Major Refactor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Status: current major release*

Version 4.0 is a significant architectural overhaul of the library. The single-package layout of
v3 has been replaced by a **monorepo** containing focused, independently installable packages.
This restructuring improves modularity, reduces coupling to optional dependencies, and makes it
easier to integrate only the parts of OpenSTEF that a project actually needs.

**New monorepo packages**

- ``openstef-core`` — shared data types, base classes, interfaces, and utilities (including the
  new ``Stateful`` mixin for versioned serialisation). All other packages depend on this one.
- ``openstef-models`` — forecasting models, preprocessing pipelines, energy-domain transforms,
  explainability helpers, and ready-to-use workflow presets.
- ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM). Provides
  statistically rigorous tooling for answering "are my model changes significant?".
- ``openstef-meta`` *(preview)* — meta-learning and advanced ensemble architectures.

**Architectural improvements**

- *Decoupled external dependencies.* Hard dependencies on MLflow, ``openstef-dbc``, and specific
  XGBoost variants have been removed from the core packages. Integrations are now opt-in.
- *Full type safety.* The codebase has been annotated end-to-end, enabling static analysis with
  ``pyright`` and better IDE support for library consumers.
- *Versioned serialisation.* The new ``Stateful`` mixin (``openstef_core.mixins.stateful``)
  attaches a ``__version__`` integer to every saved object. When a model is loaded from an older
  serialised state, ``_migrate_state`` is called automatically, and a ``UserWarning`` is raised
  if forward-compatibility cannot be guaranteed:

  .. code-block:: python

     from openstef_core.mixins.stateful import Stateful

     class MyForecaster(Stateful):
         _VERSION = 2  # bump when state layout changes

         def _migrate_state(self, state, from_version, to_version):
             if from_version == 1:
                 # rename a key introduced in v2
                 state["new_key"] = state.pop("old_key", None)
             return state

- *Flexible configuration.* Hard-coded assumptions (holiday calendars, country-specific logic,
  fixed feature sets) have been replaced with configurable parameters, broadening applicability
  beyond the Netherlands and the DSO/TSO domain.

**New features in** ``openstef-models``

- Modular transform pipeline with composable building blocks:
  ``LagsAdder``, ``RollingAggregatesAdder``, ``CyclicFeaturesAdder``,
  ``HolidayFeatureAdder``, ``RadiationDerivedFeaturesAdder``,
  ``WindPowerFeatureAdder``, ``Imputer``, ``NaNDropper``, ``Scaler``,
  ``ConfidenceIntervalApplicator``, ``QuantileSorter``, and more.
- ``XGBoostForecaster`` with built-in SHAP-based ``predict_contributions()`` and
  ``feature_importances`` property.
- ``FeatureSelection`` helpers (``Include`` / ``Exclude``) for declarative feature management.
- ``DataSplitter`` utility for reproducible train/validation splits.
- ``LocationConfig`` preset for common single-location forecasting workflows.
- ``CompletenessChecker``, ``FlatlineChecker``, and ``InputConsistencyChecker`` validation
  transforms that can be embedded directly in a pipeline.

**Breaking changes**

.. warning::

   Version 4.0 introduces breaking changes relative to v3. Review the
   :doc:`../user_guide/migration` guide before upgrading production systems.

- The top-level ``openstef`` package namespace has changed. Imports from ``openstef.pipeline.*``
  and ``openstef.model.*`` must be updated to the new per-package namespaces
  (e.g., ``openstef_models.models.forecasting.*``).
- ``PredictionJobDataClass`` and related v3 data structures are replaced by typed datasets
  defined in ``openstef-core``.
- The monorepo ships separate packages; ``pip install openstef`` installs a meta-package that
  pulls in the standard set. Install individual packages (``openstef-models``,
  ``openstef-core``) if you need a lighter footprint.
- MLflow tracking is no longer included by default. Use the optional integration package or
  wire up your own experiment tracker.

**Deprecations**

- The legacy single-package ``openstef`` v3 layout is deprecated. It will continue to receive
  critical security fixes for a limited period but will not receive new features.

----

Version 3.x
-----------

3.x represented the production-stable generation of OpenSTEF that established the library's
core forecasting patterns: a ``PredictionJob``-driven pipeline, XGBoost as the primary model
back-end, and tight integration with Alliander's internal tooling (``openstef-dbc``, MLflow).

3.x releases are no longer actively developed. The notes below capture the most significant
milestones in the 3.x series.

3.5.x — Stability and model improvements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Improved quantile forecasting accuracy for the XGBoost back-end.
- Added ``gblinear`` booster support alongside the default ``gbtree`` booster.
- Expanded feature engineering: additional lag windows, rolling-aggregate statistics.
- Bug fixes in the confidence-interval post-processing step that could produce
  non-monotonic quantile bands under certain input distributions.
- Improved handling of missing weather forecast data (graceful degradation rather than
  pipeline failure).

3.4.x — Explainability and feature selection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Introduced SHAP-based feature-contribution reporting.
- Added automated feature-importance ranking and optional feature pruning.
- ``create_forecast`` pipeline now returns per-feature contribution columns when
  ``return_contributions=True``.
- Improved logging throughout the pipeline for easier debugging in production.

3.3.x — Holiday and calendar features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added a Dutch public-holiday feature generator backed by the ``holidays`` library.
- Cyclic encoding of hour-of-day, day-of-week, and day-of-year features to avoid
  discontinuities at period boundaries.
- Bug fix: daylight-saving-time transitions no longer produce duplicate or missing
  timestamps in the feature matrix.

3.2.x — Probabilistic forecasting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Multi-quantile output support (default quantiles: 5th, 10th, 25th, 50th, 75th, 90th,
  95th percentile).
- ``ConfidenceIntervalApplicator`` post-processor to clip and sort quantile columns.
- Introduced ``rMAE`` and ``rCRPS`` evaluation metrics alongside the existing ``MAE``
  and ``RMSE`` metrics.

3.1.x — Pipeline consolidation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Unified ``train``, ``validate``, and ``forecast`` pipelines under a single
  ``PredictionJob`` configuration object.
- Introduced ``DataSplitter`` for reproducible back-testing splits.
- MLflow experiment tracking integrated as a first-class feature.

3.0.0 — Initial open-source release
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- First public release of OpenSTEF as an open-source Python library under the
  MPL-2.0 licence.
- XGBoost-based probabilistic forecasting for electricity load at substation level.
- Weather-derived features: radiation, wind speed, temperature.
- ``openstef-dbc`` database connector for reading operational data.
- Reference implementation for Alliander's short-term energy forecasting use case.

----

Upgrade notes
-------------

Upgrading from 3.x to 4.x
^^^^^^^^^^^^^^^^^^^^^^^^^^

The v3 → v4 upgrade requires updating import paths, replacing ``PredictionJob``-style
configuration with the new typed dataset and ``LocationConfig`` approach, and opting in to
any external integrations (MLflow, database connectors) separately.

See :doc:`../user_guide/migration` for a complete walkthrough including before/after code
examples and a compatibility checklist.

Checking your installed version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import importlib.metadata

   # Check the core library version
   print(importlib.metadata.version("openstef-core"))

   # Check the models package version
   print(importlib.metadata.version("openstef-models"))

Or from the command line:

.. code-block:: bash

   pip show openstef-core openstef-models openstef-beam

Staying up to date
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Upgrade all OpenSTEF packages at once
   pip install --upgrade openstef-core openstef-models openstef-beam

   # Or, if you installed the meta-package
   pip install --upgrade openstef

Watch the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_ or subscribe
to release notifications to be informed of new versions as they are published.