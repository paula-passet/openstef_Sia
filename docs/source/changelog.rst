Changelog
=========

This page documents the version history of OpenSTEF, a Python library for short-term energy forecasting. Each release includes new features, bug fixes, and breaking changes organized chronologically.

OpenSTEF follows `semantic versioning <https://semver.org/>`_. Version numbers follow the pattern MAJOR.MINOR.PATCH where:

- **MAJOR** versions introduce breaking changes that require code updates
- **MINOR** versions add new features while maintaining backward compatibility
- **PATCH** versions fix bugs without changing the API

For detailed migration instructions when upgrading between major versions, see the :doc:`user_guide/migration` guide.

Version 4.x
-----------

Version 4.0.0 (2025)
^^^^^^^^^^^^^^^^^^^^

**Major Release - Breaking Changes**

This release represents a complete architectural redesign of OpenSTEF, introducing a modular package structure and modern Python patterns.

Breaking Changes
""""""""""""""""

**Package Structure**

The library has been split into multiple focused packages:

- ``openstef-core``: Core abstractions, datasets, and base classes
- ``openstef-models``: Forecasting models and feature transforms
- ``openstef-metrics``: Evaluation metrics and validation tools
- ``openstef-tasks``: High-level forecasting workflows

Code that imported from ``openstef`` directly will need updates:

.. code-block:: python

   # Old (v3.x)
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.feature_adder import add_features
   
   # New (v4.x)
   from openstef_models.models.regressors.xgb import XGBQuantileRegressor
   from openstef_models.transforms import FeatureAdder

**Dataset API**

The data handling has been redesigned around ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``:

.. code-block:: python

   # Old (v3.x)
   data = pd.DataFrame(...)
   model.fit(data)
   
   # New (v4.x)
   from openstef_core.datasets import TimeSeriesDataset
   
   dataset = TimeSeriesDataset(data, target="load")
   model.fit(dataset)

**Transform Pipeline**

Feature engineering now uses a composable transform pipeline:

.. code-block:: python

   # New (v4.x)
   from openstef_models.transforms import (
       FeatureAdder,
       LagAdder,
       RollingAggregator
   )
   
   pipeline = FeatureAdder() | LagAdder() | RollingAggregator()
   transformed = pipeline.fit_transform(dataset)

**Model Interface**

Models now implement a consistent interface with versioned state management:

.. code-block:: python

   # New (v4.x)
   from openstef_models.models.regressors.xgb import XGBQuantileRegressor
   
   model = XGBQuantileRegressor(quantiles=[0.1, 0.5, 0.9])
   model.fit(train_dataset)
   predictions = model.predict(test_dataset)
   
   # Save/load with automatic version migration
   state = model.__getstate__()
   model.__setstate__(state)

New Features
""""""""""""

**Versioned Time Series Support**

Track data availability over time for realistic backtesting:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Create versioned dataset with availability tracking
   versioned = VersionedTimeSeriesDataset(
       data,
       target="load",
       available_at_column="available_at"
   )
   
   # Filter by availability for point-in-time reconstruction
   historical_view = versioned.filter_by_availability(
       reference_datetime=pd.Timestamp("2024-01-01")
   )

**Pydantic Configuration**

All models and transforms use Pydantic for type-safe configuration:

.. code-block:: python

   from openstef_models.models.regressors.xgb import XGBQuantileRegressor
   
   # Type-checked configuration with validation
   model = XGBQuantileRegressor(
       quantiles=[0.1, 0.5, 0.9],
       max_depth=6,
       learning_rate=0.1
   )
   
   # Serialize configuration to JSON
   config_dict = model.model_dump()

**State Versioning and Migration**

Automatic migration of saved model states across versions:

.. code-block:: python

   # Models track their version
   model = XGBQuantileRegressor()
   state = model.__getstate__()
   # state contains: {"__version__": 1, "state": {...}}
   
   # Automatic migration when loading older versions
   model.__setstate__(old_state)  # Migrates if needed

**Enhanced Transform System**

Composable transforms with fit/transform pattern:

.. code-block:: python

   from openstef_models.transforms import (
       FeatureAdder,
       LagAdder,
       CompletenessChecker
   )
   
   # Compose transforms with pipe operator
   pipeline = (
       CompletenessChecker(min_completeness=0.9) |
       FeatureAdder() |
       LagAdder(lags=[1, 2, 24])
   )
   
   # Fit on training data, transform test data
   pipeline.fit(train_dataset)
   test_transformed = pipeline.transform(test_dataset)

**Improved Type Safety**

Full type hints throughout the library with runtime validation:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.regressors.xgb import XGBQuantileRegressor
   
   # Type checkers understand the API
   dataset: TimeSeriesDataset = TimeSeriesDataset(data, target="load")
   model: XGBQuantileRegressor = XGBQuantileRegressor()
   predictions: TimeSeriesDataset = model.predict(dataset)

Bug Fixes
"""""""""

- Fixed handling of missing weather data in validation transforms
- Corrected lag feature calculation for irregular time series
- Resolved timezone handling issues in versioned datasets
- Fixed quantile crossing in XGBoost quantile regression
- Improved memory efficiency for large time series datasets

Deprecations
""""""""""""

The following v3.x APIs are removed in v4.0:

- ``openstef.model.regressors.*`` - Use ``openstef_models.models.regressors.*``
- ``openstef.feature_engineering.*`` - Use ``openstef_models.transforms.*``
- ``openstef.validation.*`` - Use ``openstef_metrics.*``
- Direct DataFrame-based model APIs - Use ``TimeSeriesDataset`` wrapper

Version 3.x
-----------

Version 3.2.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added support for Python 3.11
- Improved XGBoost quantile regression with monotone constraints
- Enhanced feature importance visualization
- Added rolling window cross-validation utilities

Bug Fixes
"""""""""

- Fixed edge cases in holiday feature generation
- Corrected handling of daylight saving time transitions
- Improved error messages for invalid input data

Version 3.1.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added LightGBM as alternative gradient boosting backend
- Implemented automatic hyperparameter tuning with Optuna
- Enhanced weather feature engineering with derived variables
- Added support for multiple forecast horizons in single model

Bug Fixes
"""""""""

- Fixed memory leak in long-running forecast loops
- Corrected quantile calculation for sparse predictions
- Improved handling of missing historical data

Version 3.0.0
^^^^^^^^^^^^^

**Major Release - Breaking Changes**

Breaking Changes
""""""""""""""""

- Minimum Python version increased to 3.8
- Removed deprecated ``old_model_trainer`` module
- Changed default feature set to include more weather variables
- Updated quantile regression API for consistency

New Features
""""""""""""

- Introduced component-based forecasting for complex loads
- Added probabilistic forecast evaluation metrics
- Implemented automatic feature selection
- Enhanced documentation with more examples

Version 2.x
-----------

Version 2.5.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added support for custom feature engineering functions
- Implemented forecast combination methods
- Enhanced model persistence with pickle protocol 5
- Added utilities for forecast visualization

Bug Fixes
"""""""""

- Fixed issue with categorical feature encoding
- Corrected timezone-aware datetime handling
- Improved numerical stability in quantile loss

Version 2.4.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added support for external regressor variables
- Implemented sliding window validation
- Enhanced error handling and logging
- Added configuration validation utilities

Bug Fixes
"""""""""

- Fixed edge case in lag feature generation
- Corrected handling of leap years in date features
- Improved performance for large datasets

Version 2.3.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added quantile regression for probabilistic forecasts
- Implemented automatic outlier detection
- Enhanced feature engineering with interaction terms
- Added model explainability tools

Bug Fixes
"""""""""

- Fixed issue with missing data imputation
- Corrected calculation of rolling statistics
- Improved handling of short time series

Version 2.2.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added support for multiple target variables
- Implemented ensemble forecasting methods
- Enhanced cross-validation utilities
- Added forecast bias correction

Bug Fixes
"""""""""

- Fixed memory usage in feature engineering
- Corrected handling of categorical features
- Improved error messages for invalid configurations

Version 2.1.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added support for custom loss functions
- Implemented early stopping for model training
- Enhanced feature importance analysis
- Added utilities for data quality checks

Bug Fixes
"""""""""

- Fixed issue with datetime parsing
- Corrected handling of missing weather data
- Improved performance of lag feature generation

Version 2.0.0
^^^^^^^^^^^^^

**Major Release - Breaking Changes**

Breaking Changes
""""""""""""""""

- Redesigned model training API for consistency
- Changed default hyperparameters for XGBoost models
- Removed support for Python 3.6
- Updated feature engineering to use pandas 1.0+

New Features
""""""""""""

- Introduced pipeline-based workflow
- Added comprehensive validation framework
- Implemented automatic feature generation
- Enhanced documentation and examples

Version 1.x
-----------

Version 1.3.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added support for weather forecast integration
- Implemented basic feature engineering utilities
- Added model evaluation metrics
- Enhanced logging capabilities

Bug Fixes
"""""""""

- Fixed issues with time zone handling
- Corrected lag feature calculation
- Improved error handling

Version 1.2.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added XGBoost quantile regression support
- Implemented basic cross-validation
- Added forecast horizon configuration
- Enhanced model serialization

Bug Fixes
"""""""""

- Fixed memory leaks in training loop
- Corrected handling of missing data
- Improved numerical stability

Version 1.1.0
^^^^^^^^^^^^^

**Minor Release**

New Features
""""""""""""

- Added support for multiple prediction quantiles
- Implemented basic feature selection
- Added configuration file support
- Enhanced error messages

Bug Fixes
"""""""""

- Fixed datetime indexing issues
- Corrected feature scaling
- Improved handling of edge cases

Version 1.0.0
^^^^^^^^^^^^^

**Initial Release**

First stable release of OpenSTEF as an open-source library.

Features
""""""""

- XGBoost-based regression models
- Basic feature engineering for time series
- Training and prediction workflows
- Model persistence and loading
- Evaluation metrics for forecast quality

Staying Updated
---------------

To check your current version and upgrade:

.. code-block:: bash

   # Check installed version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions.

For migration guidance between major versions, consult the :doc:`user_guide/migration` guide.