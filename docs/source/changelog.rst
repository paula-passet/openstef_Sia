Changelog
=========

This page summarises the notable changes in each OpenSTEF release. Entries are listed in reverse-chronological order so the most recent changes are always at the top. For every release, changes are grouped into **New Features**, **Bug Fixes**, **Performance**, and **Breaking Changes** where applicable.

If a release introduces breaking changes, a short summary is provided here and a dedicated migration guide is linked from the :doc:`user_guide/migration` page.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_ (``MAJOR.MINOR.PATCH``).
   A bump in the **major** version signals breaking API changes.
   A bump in the **minor** version adds backwards-compatible functionality.
   A bump in the **patch** version contains backwards-compatible bug fixes only.

   Subscribe to `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_ to receive
   notifications whenever a new version is published.

---

Version 4.x
-----------

4.0.0 — 2025 (Current)
^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 is a major release that restructures the library as a **modular monorepo**. The
single ``openstef`` package has been replaced by a family of focused, independently-installable
packages. This makes it possible to depend on only the components your project actually needs,
and allows each package to evolve at its own pace.

**New Features**

- **Monorepo package structure.** The library is now distributed as four packages:

  - ``openstef-core`` — shared data types, base classes, interfaces, and exceptions that all
    other packages build on.
  - ``openstef-models`` — ML models, feature engineering pipelines, energy-specific
    transformations, and forecasting presets.
  - ``openstef-beam`` — Backtesting, Evaluation, Analysis, and Metrics (BEAM) tooling for
    answering "are my model changes significant?".
  - ``openstef`` — convenience meta-package that installs ``openstef-core`` and
    ``openstef-models`` together.

  Installing the meta-package is the recommended starting point for new projects:

  .. code-block:: bash

     pip install openstef

- **``VersionedTimeSeriesDataset``.** A new dataset type that tracks data-availability
  constraints explicitly. This is essential for energy forecasting where measurements and
  weather forecasts arrive with varying delays. The dataset prevents accidental look-ahead
  leakage during training.

- **``ForecastingModel`` pipeline.** A composable pipeline object that combines a
  ``FeaturePipeline`` (preprocessing) with an estimator and optional postprocessing. The
  pipeline is serialisable and can be stored and loaded via ``LocalModelStorage``.

  .. code-block:: python

     from openstef_models.model.forecasting_model import ForecastingModel
     from openstef_models.pipeline.feature_pipeline import FeaturePipeline
     from openstef_models.transforms.time_domain.lags_adder import LagsAdder
     from openstef_models.transforms.calendar.holiday_adder import HolidayAdder
     from openstef_models.storage.local_model_storage import LocalModelStorage

     feature_pipeline = FeaturePipeline(
         transforms=[
             HolidayAdder(country="NL"),
             LagsAdder(lags=["PT15M", "PT1H", "P1D", "P7D"]),
         ]
     )

     model = ForecastingModel(
         feature_pipeline=feature_pipeline,
         estimator=my_estimator,
     )

     storage = LocalModelStorage(path="./models")
     storage.save(model, name="grid_connection_123")

- **``VersionedLagsAdder`` transform.** Creates lag features while respecting data-availability
  constraints stored in a ``VersionedTimeSeriesDataset``. Lag windows that would introduce
  look-ahead are automatically excluded.

- **Forecasting presets.** High-level preset classes provide sensible defaults for common
  energy-forecasting scenarios, reducing boilerplate for new users while remaining fully
  configurable.

- **``openstef-beam`` backtesting framework.** A dedicated package for rigorous model
  evaluation. Supports walk-forward backtesting, regression testing against benchmark models,
  and statistical significance testing of model improvements.

- **``CustomForecastingWorkflow``.** A high-level orchestration class that coordinates data
  loading, feature engineering, training, and prediction in a single, reproducible workflow.

- **Python 3.12 and 3.13 support.** OpenSTEF 4.0 requires Python ≥ 3.12 and is tested on
  Python 3.13. Modern type annotations are used throughout the codebase.

**Breaking Changes**

OpenSTEF 4.0 introduces significant API changes compared to 3.x. The most important ones are:

- The single ``openstef`` package is replaced by the monorepo package family described above.
  Import paths have changed across the board.
- The ``PredictionJobDataClass`` and related 3.x pipeline entry points have been removed.
  Forecasting is now expressed through ``ForecastingModel`` and ``CustomForecastingWorkflow``.
- Python 3.10 and 3.11 are no longer supported. Use OpenSTEF 3.x if you need those runtimes.

.. note::

   An ``openstef-compatibility`` package providing a shim layer for 3.x code is planned for a
   future 4.x release. See the :doc:`user_guide/migration` page for step-by-step instructions
   on migrating from 3.x to 4.x.

---

Version 3.x
-----------

3.4.x — Patch Series
^^^^^^^^^^^^^^^^^^^^^

The 3.4 patch series focused on stability and incremental improvements to the existing
single-package architecture.

**Bug Fixes**

- Fixed an edge case where the validation step would raise an unhandled exception when all
  weather feature columns contained ``NaN`` values. The validator now logs a warning and
  continues with the remaining available features.
- Resolved a race condition in concurrent training runs that could corrupt the serialised
  model artefact on shared file systems.
- Corrected an off-by-one error in the multi-horizon forecast index alignment that caused the
  last forecast horizon to be dropped silently.
- Fixed ``TypeError`` when passing a ``pandas.DataFrame`` with a timezone-aware index to the
  feature engineering step on Windows.

**Performance**

- Reduced peak memory usage during feature engineering by processing lag windows lazily
  instead of materialising all intermediate frames at once.
- The gradient-boosting estimator now uses histogram-based tree construction by default,
  cutting training time by roughly 30 % on large datasets.

3.4.0 — Feature Release
^^^^^^^^^^^^^^^^^^^^^^^^

**New Features**

- **Confidence interval estimation.** Two methods are now available for producing probabilistic
  forecasts: a quantile-regression approach and a conformal-prediction approach. Both are
  accessible through the same ``predict`` interface; the method is selected via a parameter on
  the prediction job.
- **Holiday feature support.** Built-in calendar transforms now cover public holidays for
  multiple European countries. Country codes follow the ISO 3166-1 alpha-2 standard.
- **Extended lag feature set.** The lag feature generator was extended to support arbitrary
  ISO 8601 duration strings (e.g. ``"PT15M"``, ``"P7D"``), replacing the previous integer-only
  interface.
- **Improved explainability output.** SHAP-based feature importance values are now included in
  the training artefact and can be retrieved without re-running inference.

**Bug Fixes**

- Fixed a memory leak in the SHAP explainability component that occurred when training many
  models in the same Python process.
- Corrected the normalisation of cyclic time features (hour-of-day, day-of-week) so that the
  sine/cosine encoding wraps correctly at period boundaries.

3.3.0 — Feature Release
^^^^^^^^^^^^^^^^^^^^^^^^

**New Features**

- **Single-shot multi-horizon forecasting.** The train and predict methodology was updated to
  produce forecasts for all required horizons in a single model call, rather than training one
  model per horizon. This substantially reduces training time for high-resolution grids.
- **Automated retraining triggers.** The pipeline gained configurable thresholds for
  automatically scheduling a model retrain when forecast quality degrades below a defined
  metric threshold.
- **``PredictionJobDataClass`` validation.** Input validation on prediction job configuration
  was tightened; invalid configurations now raise descriptive errors at construction time
  rather than failing silently mid-pipeline.

**Bug Fixes**

- Fixed incorrect feature alignment when the input time series contained gaps longer than the
  maximum lag window.
- Resolved a serialisation issue with custom estimators that implemented ``__reduce__``
  differently from scikit-learn conventions.

3.2.0 — Feature Release
^^^^^^^^^^^^^^^^^^^^^^^^

**New Features**

- **XGBoost and LightGBM estimators.** Both gradient-boosting frameworks are now first-class
  supported estimators, selectable by name in the prediction job configuration.
- **Weather feature integration.** Standardised connectors for ingesting numerical weather
  prediction (NWP) data were added to the feature engineering pipeline.
- **Backtesting utilities.** A lightweight walk-forward backtesting helper was introduced,
  allowing users to evaluate model quality on historical data without writing custom loops.

**Breaking Changes**

- The ``model_type`` field in ``PredictionJobDataClass`` now accepts a string enum value
  (``"xgb"``, ``"lgb"``, ``"linear"``) rather than a bare class reference. Existing
  configuration files must be updated accordingly.

3.1.0 — Feature Release
^^^^^^^^^^^^^^^^^^^^^^^^

**New Features**

- Initial public release of the ``openstef`` library on PyPI under the
  `MPL-2.0 <https://www.mozilla.org/en-US/MPL/2.0/>`_ licence.
- Core train/predict pipeline with scikit-learn-compatible interface.
- Feature engineering for time-series data: lag features, cyclic calendar encodings, and
  rolling statistics.
- ``PredictionJobDataClass`` as the central configuration object for a forecasting task.
- Local and remote model storage backends.
- Basic SHAP-based feature importance reporting.

---

Checking Your Installed Version
--------------------------------

You can inspect the version of each installed OpenSTEF package at any time:

.. code-block:: python

   import openstef_core
   import openstef_models

   print(openstef_core.__version__)
   print(openstef_models.__version__)

Or from the command line:

.. code-block:: bash

   pip show openstef openstef-core openstef-models openstef-beam

Upgrading to the latest release:

.. code-block:: bash

   # pip
   pip install --upgrade openstef

   # uv
   uv upgrade openstef

---

Contributing to the Changelog
------------------------------

OpenSTEF uses `Conventional Commits <https://www.conventionalcommits.org/>`_ to keep the
commit history machine-readable. The changelog is generated from commit messages at release
time. When contributing a change, use the appropriate commit type prefix:

- ``feat:`` — a new feature visible to library users
- ``fix:`` — a bug fix
- ``perf:`` — a performance improvement
- ``refactor:`` — internal restructuring with no user-visible effect
- ``docs:`` — documentation-only changes
- ``feat!:`` or ``fix!:`` — any change that breaks backwards compatibility

Breaking changes must include a ``BREAKING CHANGE:`` footer in the commit body describing
what changed and how users should update their code. See the
:doc:`contributing/commit_conventions` page for the full commit message specification.