Changelog
=========

This page records the release history of the OpenSTEF library. Each entry describes new features,
bug fixes, and breaking changes introduced in that version. Releases are listed in reverse
chronological order so the most recent changes appear first.

For step-by-step instructions on upgrading between major versions, see the
:doc:`/user_guide/migration_guide`.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. A major version bump (e.g.
   3.x → 4.0) signals breaking API changes. Minor and patch releases are backward-compatible
   within the same major series.

----

Version 4.0
-----------

*Status: current release*

Version 4.0 is a major architectural overhaul of the OpenSTEF library. The single-package
design of the 3.x series has been replaced by a **modular mono-repo** of focused, independently
installable packages. This restructuring makes it possible to use only the parts of OpenSTEF
that are relevant to a given project — for example, pulling in ``openstef-core`` and
``openstef-models`` without taking on the full backtesting stack.

.. mermaid:: /diagrams/root/changelog_diagram_1.mmd

New packages
^^^^^^^^^^^^

The 4.0 release ships as four coordinated packages:

- **openstef-core** — data types, base classes, shared exceptions, and testing utilities.
  Every other package depends on this one.
- **openstef-models** — forecasting models (XGBoost, LightGBM, GBLinear), preprocessing
  pipelines, energy-specific feature transforms, explainability helpers, and ready-to-use
  presets for common forecasting workflows.
- **openstef-beam** — the Backtesting, Evaluation, Analysis, and Metrics framework. Provides
  realistic model evaluation using versioned data to prevent data leakage, lead-time analysis,
  and benchmarking utilities for comparing multiple models across many energy assets.
- **openstef-meta** — advanced ensemble and meta-learning model architectures (optional,
  for research and enterprise use cases).

New features
^^^^^^^^^^^^

**Versioned time-series datasets**
   The new ``VersionedTimeSeriesDataset`` type tracks when each measurement became available,
   enabling point-in-time reconstruction of the data that a model would have seen in production.
   This is the foundation for leakage-free backtesting.

   .. code-block:: python

      import pandas as pd
      from datetime import timedelta
      from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

      data = pd.DataFrame(
          {
              "available_at": pd.date_range("2025-01-01 10:00", periods=4, freq="h"),
              "load": [100.0, 110.0, 120.0, 130.0],
          },
          index=pd.date_range("2025-01-01 10:00", periods=4, freq="h"),
      )
      dataset = VersionedTimeSeriesDataset.from_dataframe(data, timedelta(hours=1))

**BEAM backtesting pipeline**
   ``openstef-beam`` provides a complete workflow — backtesting → evaluation → analysis →
   benchmarking — that replays historical data day by day, retrains models periodically, and
   scores forecasts without lookahead. Any model that implements the ``BacktestForecasterMixin``
   interface can be plugged in.

   .. code-block:: python

      from openstef_beam.backtesting.backtest_pipeline import BacktestPipeline, BacktestConfig

      config = BacktestConfig()
      pipeline = BacktestPipeline(forecaster_factory=my_factory, config=config)
      predictions = pipeline.run(
          ground_truth=versioned_ground_truth,
          predictors=versioned_predictors,
          start=None,
          end=None,
      )

**New model backends**
   Alongside the existing XGBoost forecaster, 4.0 adds first-class support for:

   - ``LGBMForecaster`` — gradient boosting trees via LightGBM.
   - ``LGBMLinearForecaster`` — LightGBM with linear leaves, useful for smoother quantile
     outputs on well-behaved load profiles.

**Versioned lag features**
   ``VersionedLagsAdder`` creates lag features that respect data-availability constraints,
   ensuring that lag values only use measurements that would have been present at prediction
   time. Feature names follow ISO 8601 duration notation (e.g. ``load_lag_-PT1H``).

   .. code-block:: python

      from datetime import timedelta
      from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder

      transform = VersionedLagsAdder(
          feature="load",
          lags=[timedelta(hours=-1), timedelta(hours=-2)],
      )
      result = transform.transform(dataset)

**Configurable holiday calendars**
   The ``HolidayFeatureAdder`` now accepts a ``country_code`` parameter, removing the
   previous hard-coded assumption that all deployments operate in the Netherlands.

**Full type safety**
   The entire codebase has been annotated with Python type hints. Pydantic v2 is used
   throughout for configuration and data validation, replacing ad-hoc dictionary-based
   configuration objects.

**Decoupled external dependencies**
   MLFlow, ``openstef-dbc``, and other infrastructure dependencies are no longer required
   by the core library. They can be added as optional extras when needed.

Breaking changes
^^^^^^^^^^^^^^^^

Version 4.0 introduces breaking changes relative to the 3.x series. The most significant are:

- **Package restructuring.** All imports have moved. The top-level ``openstef`` package no
  longer exists as a single installable unit; users must install the relevant sub-packages
  (``openstef-core``, ``openstef-models``, etc.).
- **Configuration objects.** Dictionary-based prediction-job configurations (``PredictionJob``)
  have been replaced by Pydantic model classes. Code that constructs or accesses configuration
  as a plain ``dict`` must be updated.
- **Pipeline API.** The ``run_train_pipeline`` / ``run_forecast_pipeline`` function signatures
  from 3.x have been replaced by the new ``ForecastingWorkflow`` and ``BacktestPipeline``
  classes.
- **Removed hard-coded defaults.** Several parameters that previously defaulted to
  Netherlands-specific values (holiday calendars, grid topology assumptions) now require
  explicit configuration.

.. warning::

   Upgrading from 3.x to 4.0 requires code changes. Review the
   :doc:`/user_guide/migration_guide` before upgrading a production system.

----

Version 3.x series
-------------------

The 3.x series established OpenSTEF as a general-purpose short-term energy forecasting library
and introduced the prediction-job abstraction that drove most forecasting workflows.

Version 3.4
^^^^^^^^^^^

- Added probabilistic forecasting output: models now return quantile predictions alongside
  the median, enabling uncertainty quantification in downstream applications.
- Introduced ``ConfidenceIntervalApplicator`` post-processing step to derive confidence
  intervals from quantile outputs.
- Improved feature importance reporting via SHAP values for XGBoost models.
- Bug fix: corrected an off-by-one error in lag feature alignment that caused the first
  forecast horizon to use a stale measurement.

Version 3.3
^^^^^^^^^^^

- Added GBLinear model backend (XGBoost with linear booster), providing a faster and more
  interpretable alternative for load profiles with strong linear structure.
- Extended the ``DatetimeFeaturesAdder`` transform with optional one-hot encoding of
  categorical time features (hour-of-day, day-of-week).
- Performance improvement: feature engineering pipeline now operates in-place where possible,
  reducing peak memory usage for large datasets.
- Bug fix: ``QuantileSorter`` post-processor now correctly handles edge cases where all
  quantile predictions are identical.

Version 3.2
^^^^^^^^^^^

- Introduced the ``Imputer`` transform for handling missing values in predictor time series,
  replacing the previous approach of dropping incomplete rows before model training.
- Added support for sample weights in model training, allowing recent observations to be
  weighted more heavily than older history.
- Bug fix: resolved a timezone-handling inconsistency that caused incorrect feature alignment
  when input data mixed timezone-aware and timezone-naive timestamps.

Version 3.1
^^^^^^^^^^^

- First release to support multi-horizon forecasting within a single model fit, replacing
  the earlier approach of training one model per forecast horizon.
- Added ``TargetHorizonSplitter`` to cleanly separate training data by forecast horizon.
- Improved test coverage across the preprocessing pipeline.

Version 3.0
^^^^^^^^^^^

- Major release introducing the ``PredictionJob`` configuration abstraction.
- Unified training and forecasting pipelines under ``run_train_pipeline`` and
  ``run_forecast_pipeline`` entry points.
- Added MLFlow integration for experiment tracking (optional dependency).
- Dropped support for Python 3.7; minimum supported version raised to Python 3.9.

----

Version 2.x series
-------------------

The 2.x series focused on stabilising the XGBoost-based forecasting core and building out
the feature engineering layer.

Version 2.5
^^^^^^^^^^^

- Introduced the lag-feature framework, allowing models to use historical load measurements
  as predictors.
- Added weather-feature alignment utilities to handle forecast data arriving with varying
  lead times.
- Bug fix: corrected normalisation of solar irradiance features that produced out-of-range
  values near sunrise and sunset.

Version 2.4
^^^^^^^^^^^

- Added cross-validation utilities for hyperparameter tuning.
- Introduced ``FeatureSelector`` to prune low-importance features before model training,
  reducing overfitting on sparse datasets.

Version 2.3
^^^^^^^^^^^

- First public release of the library under the MPL-2.0 licence.
- Core XGBoost forecasting model with basic datetime and weather features.
- Initial documentation and example notebooks.

----

Deprecation policy
------------------

OpenSTEF deprecates features over at least one minor release before removing them in a
subsequent major release. Deprecated APIs emit a ``DeprecationWarning`` at import or call
time, with a message indicating the replacement. Users are encouraged to address deprecation
warnings before upgrading to the next major version.

If you encounter an undocumented breaking change, please open an issue on the
`OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_.