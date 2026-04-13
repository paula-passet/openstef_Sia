Changelog
=========

This page summarises what changed in each release of OpenSTEF. Entries are listed in reverse chronological order — most recent first. For guidance on updating your code between major versions, see the :doc:`/user_guide/migration` page.

OpenSTEF follows `semantic versioning <https://semver.org/>`_: a ``MAJOR.MINOR.PATCH`` scheme where breaking changes increment the major version, new backward-compatible features increment the minor version, and bug fixes increment the patch version.

.. note::

   The authoritative list of individual commits and pull requests is on the
   `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.
   This changelog highlights the changes most relevant to library users.

----

Version 4.x
-----------

4.0.0 — 2025 (Current)
^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 is a major release that restructures the library as a **modular monorepo**. The single ``openstef`` package has been split into focused, independently installable packages. Most users should install the ``openstef`` meta-package, which pulls in the core components automatically.

**New packages**

- ``openstef-core`` — shared data types, base classes, interfaces, and exceptions that underpin all other packages.
- ``openstef-models`` — ML models, feature engineering pipelines, energy-specific transforms, and explainability tools.
- ``openstef-beam`` — Backtesting, Evaluation, Analysis, and Metrics. Answers the question *"are my model changes statistically significant?"* with a regression-testing framework spun out of an internal Alliander project.
- ``openstef`` — meta-package that installs ``openstef-core`` and ``openstef-models`` together, providing the same entry point as before.

Two further packages are planned but not yet released:

- ``openstef-compatibility`` — a compatibility shim for code written against the OpenSTEF 3.x API.
- ``openstef-foundational-models`` — deep-learning and foundation model integrations.

**Architecture changes**

The library is now built around a small set of composable abstractions defined in ``openstef-core``:

- ``TimeSeriesDataset`` — a typed wrapper around a ``pandas.DataFrame`` that carries sample-interval metadata and enforces a ``DatetimeIndex``.
- ``VersionedTimeSeriesDataset`` — a lazy-composition dataset that tracks *when* each measurement became available. This solves the O(n²) space-complexity problem that arose in v3 when concatenating DataFrames with misaligned ``(timestamp, available_at)`` pairs, and enables realistic point-in-time backtesting.
- ``BaseForecastingModel`` / ``ForecastingModel`` — abstract and concrete base classes that orchestrate the full prediction pipeline.
- ``TransformPipeline`` mixin — a composable pipeline interface used by both models and transforms.

**New features**

- *Versioned lag features* — ``VersionedLagsAdder`` creates lag features that respect data-availability constraints, so a model trained on historical data cannot accidentally look ahead at measurements that would not yet have arrived at inference time.
- *Presets* — ``openstef_models.presets`` ships ready-to-use workflow configurations for XGBoost, GBLinear, and Flatliner models, each bundled with a sensible preprocessing pipeline. A preset is a plain Pydantic model, so it can be serialised to JSON/YAML and stored alongside your experiment artefacts.
- *MLflow integration* — ``MLFlowStorage`` and ``MLFlowStorageCallback`` in ``openstef_models.integrations.mlflow`` provide first-class MLflow experiment tracking and model storage without requiring any glue code.
- *Probabilistic forecasting* — multi-quantile output is now a first-class concept throughout the API. Quantile targets are expressed using the ``Quantile`` and ``QuantileOrGlobal`` types from ``openstef_core.types``.
- *BEAM evaluation* — ``openstef-beam`` ships metric providers (``R2Provider``, ``ObservedProbabilityProvider``, and others) and a backtesting harness that can compare two model versions over the same historical window.

**Breaking changes**

The v4 API is substantially different from v3. The top-level pipeline functions (``train_model_pipeline``, ``create_forecast_pipeline``, etc.) that were the primary entry points in v3 have been replaced by the class-based ``ForecastingModel`` API. See :doc:`/user_guide/migration` for a detailed mapping of old calls to new equivalents.

A minimal v4 workflow now looks like this:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_models.presets import XGBoostForecastingWorkflow

   # Load your data as a pandas DataFrame with a DatetimeIndex
   data = pd.read_parquet("my_load_data.parquet")

   # Configure a preset — all fields are Pydantic-validated
   workflow = XGBoostForecastingWorkflow(
       sample_interval=timedelta(minutes=15),
       horizon=timedelta(hours=48),
   )

   # Train and generate forecasts
   model = workflow.train(data)
   forecast = model.predict(data)

**Dependency changes**

- Python ≥ 3.11 is now required (up from 3.9 in v3).
- ``pydantic`` v2 is now a core dependency; v1 compatibility is dropped.
- ``pydantic-extra-types`` is used for geographic coordinate and country-code fields in workflow configurations.
- ``apache-beam`` is an optional dependency, required only if you install ``openstef-beam``.

.. note::

   If you are upgrading from v3, read the :doc:`/user_guide/migration` guide before
   updating. The v3 ``PredictionJobDict`` and pipeline-function API are not present
   in v4 by default; they will be available through the forthcoming
   ``openstef-compatibility`` package.

----

Version 3.x
-----------

3.x was the previous stable series and the version most existing deployments run today. The notes below capture the most significant milestones in that series.

3.4.x — Stability and performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Improved handling of missing weather data: validation now logs a warning and continues with available features rather than raising an unhandled exception.
- Reduced memory usage during feature engineering for large training windows.
- ``PredictionJobDict`` validation errors now include the offending field name in the error message.
- Various fixes to the confidence-interval calculation for probabilistic forecasts.

3.3.x — Explainability
^^^^^^^^^^^^^^^^^^^^^^^^

- Added SHAP-based feature-importance reporting to the training pipeline. After training, ``model.feature_importance`` returns a ``pandas.DataFrame`` ranking features by their mean absolute SHAP value.
- New ``plot_feature_importance`` utility in ``openstef.plotting`` for quick visual inspection of trained models.
- The ``create_forecast_pipeline`` function gained an optional ``return_confidence_interval`` flag (default ``False``) to include quantile bounds in the returned forecast ``DataFrame``.

3.2.x — Model zoo expansion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Added ``LinearQuantileRegressor`` as a built-in estimator, complementing the existing XGBoost and LightGBM options.
- ``OpenstfRegressor`` base class formalised the interface that all built-in estimators must satisfy, making it straightforward to register a custom estimator.
- Training pipelines gained automatic detection of *flatliner* targets — load series that are constant for extended periods — and substitute a simpler model to avoid overfitting artefacts.

3.1.x — Operational improvements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``train_model_pipeline`` now saves a serialised model artefact to the configured model storage backend after every successful training run.
- Added ``MLflowSerializer`` as a first-party model storage backend (previously only filesystem storage was built in).
- Horizon-specific feature sets: features that are only meaningful at short lead times (e.g., recent-lag features) are automatically excluded when training models for longer horizons.

3.0.0 — Pipeline-first API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 3.0 introduced the high-level pipeline functions that became the defining API of the v3 series:

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Train
   model, report = train_model_pipeline(prediction_job, data)

   # Forecast
   forecast = create_forecast_pipeline(prediction_job, data, model)

Key changes from v2:

- The ``PredictionJobDict`` typed dictionary replaced the earlier ad-hoc ``dict`` configuration, providing IDE autocompletion and runtime validation.
- Feature engineering was moved into the pipeline functions, removing the need for callers to construct feature matrices manually.
- LightGBM support was added alongside the existing XGBoost backend.
- A standardised ``ModelSerialiser`` interface replaced the previous bespoke serialisation code, enabling pluggable storage backends.

----

Version 2.x
-----------

2.x established the core concepts that carried forward into v3 and v4: the separation between feature engineering, model training, and forecast generation; the use of quantile regression for probabilistic output; and the focus on 15-minute resolution load forecasting as the primary use case.

Notable milestones:

- **2.3** — Introduced the ``OpenstfRegressor`` abstraction, allowing XGBoost to be swapped for other scikit-learn-compatible regressors.
- **2.1** — Added support for weather-feature integration (temperature, irradiance, wind speed) as first-class input columns.
- **2.0** — First public open-source release under the Apache 2.0 licence, contributed to the LF Energy foundation.

----

Deprecation policy
------------------

OpenSTEF follows a two-major-version deprecation window. A feature deprecated in v3 will emit a ``DeprecationWarning`` throughout the v3 series and will be removed no earlier than v5. Where a direct replacement exists, the warning message names it explicitly.

To surface all active deprecation warnings in your test suite, add the following to your ``pytest.ini`` or ``pyproject.toml``:

.. code-block:: ini

   # pytest.ini
   [pytest]
   filterwarnings =
       error::DeprecationWarning
       error::PendingDeprecationWarning

----

Staying current
---------------

Subscribe to `GitHub release notifications <https://github.com/OpenSTEF/openstef/releases>`_ to be notified of new versions. To check which version you have installed and upgrade to the latest:

.. code-block:: bash

   # Check installed version
   pip show openstef

   # Upgrade
   pip install --upgrade openstef

If you use ``uv``:

.. code-block:: bash

   uv list | grep openstef
   uv upgrade openstef

For a full list of commits and pull requests associated with each release, see the `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.