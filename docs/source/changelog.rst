Changelog
=========

This page documents the version history of OpenSTEF, including new features, improvements, bug fixes, and breaking changes for each release. OpenSTEF follows `semantic versioning <https://semver.org/>`_.

For detailed migration instructions when upgrading between major versions, see the :doc:`user_guide/migration_guide`.

Version 4.0.0
-------------

**Release Date:** 2025

OpenSTEF 4.0 represents a major architectural refactor focused on modularity, type safety, and broader applicability beyond the original Dutch grid operator use case.

Breaking Changes
^^^^^^^^^^^^^^^^

**Modular Package Structure**

OpenSTEF 4.0 splits the monolithic library into focused packages:

- ``openstef-core``: Core abstractions, datasets, and base classes
- ``openstef-models``: Forecasting models and feature transforms
- ``openstef-metrics``: Evaluation metrics for time series forecasting
- ``openstef-reference``: Reference implementation and examples

Existing code importing from ``openstef`` will need to update import paths:

.. code-block:: python

   # V3 imports
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   
   # V4 imports
   from openstef_models.models.xgboost import XGBoostQuantileRegressor
   from openstef_models.transforms import FeaturePipeline

**Dataset API Redesign**

The new dataset API uses ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` classes that encapsulate data with metadata:

.. code-block:: python

   # V3: Plain DataFrames
   train_data = pd.DataFrame(...)
   model.fit(train_data)
   
   # V4: Typed dataset objects
   from openstef_core.datasets import TimeSeriesDataset
   
   train_data = TimeSeriesDataset(
       data=df,
       target_column='load',
       datetime_column='datetime'
   )
   model.fit(train_data)

**Transform Pipeline Architecture**

Feature engineering now uses explicit transform pipelines instead of monolithic functions:

.. code-block:: python

   # V4: Composable transforms
   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder, HolidayFeatureAdder
   from openstef_models.transforms import FeaturePipeline
   
   pipeline = FeaturePipeline([
       DatetimeFeaturesAdder(features=['hour', 'day_of_week']),
       HolidayFeatureAdder(country='NL')
   ])
   
   transformed_data = pipeline.fit_transform(train_data)

**Configuration System**

Hard-coded assumptions replaced with explicit configuration using Pydantic models:

.. code-block:: python

   # V4: Type-safe configuration
   from openstef_models.models.xgboost import XGBoostQuantileRegressor, XGBoostConfig
   
   model = XGBoostQuantileRegressor(
       config=XGBoostConfig(
           n_estimators=100,
           max_depth=6,
           learning_rate=0.1,
           quantiles=[0.1, 0.5, 0.9]
       )
   )

**Removed External Dependencies**

- MLflow integration moved to optional extension
- Database connectors (``openstef-dbc``) separated into standalone package
- XGBoost gblinear backend removed (use scikit-learn linear models instead)

New Features
^^^^^^^^^^^^

**Versioned Time Series Support**

Handle datasets where different data versions have different availability times:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.transforms.time_domain import VersionedLagsAdder
   
   # Data with multiple versions (e.g., forecasts updated at different times)
   versioned_data = VersionedTimeSeriesDataset(
       data=df,
       target_column='load',
       datetime_column='datetime',
       available_at_column='available_at'
   )
   
   # Automatically select appropriate data versions for each lag
   lag_transform = VersionedLagsAdder(
       columns=['load', 'temperature'],
       lags=['-PT2H', '-PT24H', '-PT168H']
   )
   
   features = lag_transform.fit_transform(versioned_data)

**Flexible Holiday Calendars**

Support for international holidays beyond the Netherlands:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder
   
   # Dutch holidays (default)
   nl_holidays = HolidayFeatureAdder(country='NL')
   
   # German holidays
   de_holidays = HolidayFeatureAdder(country='DE')
   
   # Custom holiday calendar
   custom_holidays = HolidayFeatureAdder(
       holidays=['2025-01-01', '2025-12-25']
   )

**Stateful Transform Serialization**

Save and restore fitted transforms with automatic version migration:

.. code-block:: python

   # Fit and save pipeline
   pipeline.fit(train_data)
   state = pipeline.get_state()
   
   # Later: restore pipeline
   new_pipeline = FeaturePipeline.from_state(state)
   # Automatically migrates from older versions with warnings

**Enhanced Metrics Package**

Comprehensive forecasting metrics with support for quantile evaluation:

.. code-block:: python

   from openstef_metrics import mae, rmae, crps
   
   # Standard metrics
   error = mae(y_true, y_pred)
   relative_error = rmae(y_true, y_pred)
   
   # Quantile metrics
   probabilistic_score = crps(y_true, quantile_predictions)

**Modular Model Interface**

Clear base classes for implementing custom models:

.. code-block:: python

   from openstef_core.models import TimeSeriesModel
   from openstef_core.datasets import TimeSeriesDataset
   
   class CustomModel(TimeSeriesModel):
       def fit(self, data: TimeSeriesDataset) -> None:
           # Your training logic
           pass
       
       def predict(self, data: TimeSeriesDataset) -> np.ndarray:
           # Your prediction logic
           pass

Improvements
^^^^^^^^^^^^

- **Type Safety**: Full type annotations throughout the codebase with strict mypy checking
- **Test Coverage**: Increased test coverage with faster test execution
- **Documentation**: Complete rewrite following the Diátaxis framework (tutorials, how-to guides, reference, explanation)
- **Performance**: Optimized data transformations for large datasets
- **Error Messages**: Clearer error messages with actionable guidance
- **Validation**: Improved data validation with explicit error handling

Migration Notes
^^^^^^^^^^^^^^^

Migrating from OpenSTEF 3.x to 4.0 requires code changes. Key migration steps:

1. Update package dependencies to use modular packages
2. Replace DataFrame-based APIs with ``TimeSeriesDataset`` objects
3. Convert feature engineering code to transform pipelines
4. Update model instantiation to use configuration objects
5. Review and update custom model implementations to new interfaces

See :doc:`user_guide/migration_guide` for detailed migration instructions with code examples.

Version 3.x
-----------

OpenSTEF 3.x was the production version used by Alliander and other Dutch grid operators for operational forecasting.

Version 3.0.0
^^^^^^^^^^^^^

**Release Date:** 2023

- Initial open-source release of OpenSTEF
- XGBoost-based quantile regression models
- Feature engineering pipeline for energy forecasting
- Integration with MLflow for experiment tracking
- Database connectors for operational deployment
- Validation and completeness checking
- Support for Dutch holidays and energy market conventions

Version 2.x and Earlier
-----------------------

Versions prior to 3.0 were internal releases at Alliander and are not publicly documented.

Staying Updated
---------------

To check your current version and upgrade:

.. code-block:: bash

   # Check installed version
   pip show openstef-core
   
   # Upgrade to latest version
   pip install --upgrade openstef-core openstef-models openstef-metrics

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions.

Version Support Policy
----------------------

- **Major versions**: Supported with bug fixes for 12 months after next major release
- **Minor versions**: Supported until next minor version release
- **Security patches**: Applied to current major version only

OpenSTEF 3.x will receive critical bug fixes until December 2025.

Contributing to Releases
-------------------------

OpenSTEF welcomes contributions. To propose features or report bugs for upcoming releases:

1. Check existing `GitHub issues <https://github.com/OpenSTEF/openstef/issues>`_
2. Open a new issue with detailed description and use case
3. Discuss implementation approach with maintainers
4. Submit pull request with tests and documentation

See :doc:`contributing/index` for detailed contribution guidelines.