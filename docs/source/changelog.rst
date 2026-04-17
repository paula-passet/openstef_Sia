Changelog
=========

This page records the version history of OpenSTEF, summarising new features, bug fixes,
and breaking changes for each release. Because OpenSTEF is a Python library, "breaking
changes" refers to API-level incompatibilities that may require updates to code that
imports and calls OpenSTEF directly.

For step-by-step instructions on upgrading between major versions, see the
:doc:`/user_guide/migration` page.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. A major version bump
   (e.g. 3 → 4) signals breaking API changes. Minor and patch releases are
   backwards-compatible within the same major series.

----

Version 4.0 (2025)
-------------------

Version 4.0 is a major architectural release. The library has been restructured from a
single monolithic package into a **modular mono-repo** of focused, independently
installable packages. This redesign improves composability, reduces unnecessary
dependencies, and makes it easier to integrate individual OpenSTEF components into
existing software systems.

The top-level ``openstef`` meta-package continues to install the full stack in one
command:

.. code-block:: bash

   pip install openstef

Individual packages can also be installed on their own:

.. code-block:: bash

   pip install openstef-core      # data types, interfaces, base classes
   pip install openstef-models    # forecasting models and preprocessing
   pip install openstef-meta      # meta/ensemble models
   pip install openstef-beam      # backtesting, evaluation, analysis, metrics

New packages
^^^^^^^^^^^^

**openstef-core**
   Provides the shared foundation: data types (``TimeSeriesDataset``,
   ``VersionedTimeSeriesDataset``, ``ForecastDataset``), abstract interfaces, base
   configuration classes (``BaseConfig``), shared exceptions, and testing utilities.
   Every other package depends on ``openstef-core``; it carries minimal runtime
   dependencies (``pandas``, ``numpy``, ``pydantic``, ``pyarrow``, ``joblib``).

**openstef-models**
   Contains the forecasting model implementations, the ``ForecastingModel`` pipeline
   class, the ``FeaturePipeline`` preprocessing system (lag transforms, holiday
   features, scaling), postprocessing, explainability, and preset configurations for
   common use cases. Optional extras select the underlying gradient-boosting backend:

   .. code-block:: bash

      pip install "openstef-models[lgbm]"          # LightGBM
      pip install "openstef-models[xgb-cpu]"       # XGBoost (CPU)
      pip install "openstef-models[xgb-gpu]"       # XGBoost (GPU)

**openstef-beam** *(Backtesting, Evaluation, Analysis, Metrics)*
   A dedicated library for rigorous model evaluation. Provides backtesting pipelines,
   probabilistic scoring (CRPS, quantile metrics), benchmark comparison across multiple
   runs, and built-in visualisation via ``ForecastTimeSeriesPlotter``. Spun out from an
   internal Alliander project and now a core part of the OpenSTEF ecosystem.

**openstef-meta**
   Modern ensemble and meta-learning model architectures built on top of
   ``openstef-models`` and ``openstef-beam``.

New features
^^^^^^^^^^^^

- **``ForecastingModel`` pipeline** — a single class that orchestrates preprocessing,
  training, prediction, and postprocessing. Replaces the procedural pipeline functions
  from v3.

  .. code-block:: python

     from openstef_models.models.forecasting_model import ForecastingModel

     model = ForecastingModel(
         preprocessor=feature_pipeline,
         forecaster=my_forecaster,
         cutoff_history=cutoff,
     )
     model.fit(train_data)
     forecast = model.predict(input_data)

- **``VersionedTimeSeriesDataset``** — a lazy-composition dataset that tracks data
  availability timestamps, enabling point-in-time reconstruction for realistic
  backtesting without the O(n²) memory cost of eagerly concatenating misaligned
  DataFrames.

- **``VersionedLagsAdder``** — a lag-feature transform that respects data availability
  constraints, ensuring lag features only use data that would have been available at
  prediction time.

- **``EvaluationPipeline``** — configurable evaluation across availability times, lead
  times, and rolling windows. Always includes observed-probability calibration.

- **``BenchmarkComparisonPipeline``** — compare metric results across multiple benchmark
  runs to answer the question *"are my model changes statistically significant?"*

- **Preset workflows** — ``ForecastingWorkflowConfig`` and
  ``EnsembleForecastingWorkflowConfig`` provide opinionated defaults so new users can
  get a working pipeline with minimal configuration.

- **``BaseConfig`` YAML serialisation** — all configuration objects can be written to
  and read from YAML files:

  .. code-block:: python

     from openstef_core.base_model import BaseConfig

     config = MyConfig(param_a=1, param_b="value")
     config.write_yaml("config.yaml")

     loaded = MyConfig.read_yaml("config.yaml")

- **Full type safety** — the entire codebase is type-annotated and validated with
  Pydantic v2. Configuration errors are caught at object construction time rather than
  at runtime.

- **Python 3.12+ requirement** — the library now requires Python ≥ 3.12, < 4.0.

Breaking changes
^^^^^^^^^^^^^^^^

Version 4.0 introduces breaking changes at every layer of the API. The v3 procedural
pipeline functions (``train_model_pipeline``, ``create_forecast_pipeline``, etc.) and
the ``PredictionJob`` dataclass have been removed. The new entry points are the
``ForecastingModel`` class and the workflow configuration objects in ``openstef-models``.

Key incompatibilities:

- The single ``openstef`` package has been split; import paths have changed throughout.
  For example, model classes previously under ``openstef.model`` are now under
  ``openstef_models.models``.
- ``PredictionJob`` is replaced by typed Pydantic configuration objects.
- The ``openstef-dbc`` database connector is no longer a hard dependency; data loading
  is the caller's responsibility.
- MLflow integration is now an optional dependency (``mlflow-skinny``) pulled in by
  ``openstef-models``, not a required one.
- Holiday calendar logic is now generalised and configurable rather than hard-coded for
  the Netherlands.

.. note::

   See :doc:`/user_guide/migration` for a detailed, step-by-step guide to upgrading
   from v3 to v4, including import path mappings and code examples.

----

Version 3.x Series
-------------------

The 3.x series established OpenSTEF as a production-ready short-term energy forecasting
library used in grid operations at Alliander. It introduced the ``PredictionJob``
abstraction, MLflow-based experiment tracking, and a set of high-level pipeline
functions that covered the train/validate/forecast lifecycle.

Notable milestones in the 3.x series:

- **3.0** — Initial open-source release under the LF Energy umbrella. Introduced
  ``PredictionJob``, ``train_model_pipeline``, ``create_forecast_pipeline``, and
  ``create_basecase_forecast_pipeline``. XGBoost and LightGBM backends supported.
- **3.x patch releases** — Incremental improvements to feature engineering (lag
  features, Fourier terms, weather features), model serialisation, and MLflow
  integration. Bug fixes to data validation and outlier handling.

.. note::

   The 3.x series is no longer actively maintained. Users are encouraged to migrate to
   v4. See :doc:`/user_guide/migration` for guidance.

----

Version 2.x Series
-------------------

Version 2.x was the first publicly available release of OpenSTEF (then known internally
as *openstf*). It provided a working XGBoost-based forecasting pipeline for Dutch DSO
substations, with hard-coded assumptions around data format, holiday calendars, and
infrastructure (InfluxDB, ``openstef-dbc``).

Key characteristics of the 2.x series:

- Single-package distribution (``openstef``).
- XGBoost as the sole model backend.
- Tight coupling to Alliander's internal data infrastructure.
- Dutch public holiday calendar hard-coded into feature engineering.
- No formal public API stability guarantees.

----

Deprecation Policy
------------------

OpenSTEF follows these conventions for deprecating functionality:

- Features scheduled for removal are marked with a ``DeprecationWarning`` for at least
  one minor release before they are removed.
- Breaking changes only occur in major version bumps.
- The :doc:`/user_guide/migration` page is updated alongside every major release and
  provides concrete before/after code examples.

If you discover an undocumented breaking change in a minor or patch release, please open
an issue on the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_.

----

How to Check Your Installed Version
------------------------------------

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam

   print(openstef_core.__version__)
   print(openstef_models.__version__)
   print(openstef_beam.__version__)

Or from the command line:

.. code-block:: bash

   pip show openstef-core openstef-models openstef-beam openstef-meta