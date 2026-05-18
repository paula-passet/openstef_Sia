Feature Engineering
===================

This guide covers how feature engineering works in OpenSTEF: the built-in transforms available, how they compose into pipelines, and how to write your own custom feature transformations.

Feature engineering in OpenSTEF is built around the ``TimeSeriesTransform`` interface. Each transform takes a ``TimeSeriesDataset``, adds or modifies features, and returns the enriched dataset. Transforms are composable—you chain them into a ``TransformPipeline`` that applies each step sequentially.

.. mermaid:: /diagrams/user_guide/guides/feature_engineering_diagram_1.mmd

Core Concepts
-------------

Every transform in OpenSTEF inherits from two base classes:

- ``BaseConfig`` — provides Pydantic-based configuration and serialization
- ``TimeSeriesTransform`` — defines the ``fit()`` / ``transform()`` interface

This design means transforms are both configurable (with validated parameters) and stateful (they can learn from data during ``fit``).

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig

   class MyTransform(BaseConfig, TimeSeriesTransform):
       """A custom transform skeleton."""

       def is_fitted(self) -> bool:
           return True

       def fit(self, data: TimeSeriesDataset) -> None:
           pass

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Add features to data here
           return data

       def features_added(self) -> list[str]:
           return []


Built-in Transforms
-------------------

OpenSTEF ships with transforms organized into domain-specific modules.

Time Domain Transforms
^^^^^^^^^^^^^^^^^^^^^^

These transforms capture temporal patterns in the target signal.

**LagsAdder**

The most fundamental feature transform for time series forecasting. It creates lagged copies of the target variable to capture temporal dependencies.

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import (
       LagsAdder,
       generate_minute_lags,
       generate_day_lags,
   )
   from datetime import timedelta

   # Create a lags adder with automatic lag generation
   lags_adder = LagsAdder(
       min_horizon=timedelta(hours=1),
       max_day_lags=7,
   )

   # Or inspect what lags would be generated
   minute_lags = generate_minute_lags(min_horizon=timedelta(hours=1))
   day_lags = generate_day_lags(min_horizon=timedelta(hours=1), max_day_lags=7)

The ``LagsAdder`` is horizon-aware: it ensures that lag features only use data that would have been available at prediction time. For multi-horizon forecasting, different horizons may receive different subsets of lags.

Key properties:

- ``lags`` — all configured lag durations, sorted descending
- ``horizon_lags`` — mapping of each forecast horizon to its valid lag features
- ``min_horizon`` — shortest forecast horizon, determining minimum lag requirements

**VersionedLagsAdder**

For versioned time series datasets where data availability constraints must be preserved:

.. code-block:: python

   from openstef_models.transforms.time_domain.versioned_lags_adder import VersionedLagsAdder
   from datetime import timedelta

   versioned_lags = VersionedLagsAdder(
       column="load",
       lags=[timedelta(hours=24), timedelta(hours=48)],
   )

   # Fit learns availability patterns
   versioned_lags.fit(versioned_dataset)
   enriched = versioned_lags.transform(versioned_dataset)

This transform ensures lag features only reference data that would have been available at the time of each forecast version—critical for realistic backtesting.

Energy Domain Transforms
^^^^^^^^^^^^^^^^^^^^^^^^

These transforms encode domain knowledge specific to energy systems.

**WindPowerFeatureAdder**

Computes wind power features from wind speed data using physical relationships:

.. code-block:: python

   from openstef_models.transforms.energy_domain.wind_power_feature_adder import WindPowerFeatureAdder

   wind_transform = WindPowerFeatureAdder()
   enriched_data = wind_transform.transform(dataset)

   # See what features were created
   print(wind_transform.features_added())

Validation Transforms
^^^^^^^^^^^^^^^^^^^^^

These transforms don't add features but enforce data quality constraints within the pipeline.

**CompletenessChecker**

Checks that the input time series has sufficient data coverage before proceeding:

.. code-block:: python

   from openstef_models.transforms.validation.completeness_checker import CompletenessChecker

   checker = CompletenessChecker()
   # Raises an error if data is incomplete; otherwise passes through unchanged
   validated_data = checker.transform(dataset)


Composing a Transform Pipeline
-------------------------------

Individual transforms are composed into a ``TransformPipeline`` that applies them sequentially:

.. code-block:: python

   from openstef_models.transforms import TransformPipeline
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.energy_domain.wind_power_feature_adder import WindPowerFeatureAdder
   from datetime import timedelta

   pipeline = TransformPipeline(steps=[
       WindPowerFeatureAdder(),
       LagsAdder(min_horizon=timedelta(hours=1), max_day_lags=7),
   ])

   # Fit all transforms
   pipeline.fit(training_data)

   # Transform new data
   enriched = pipeline.transform(training_data)

.. note::

   Order matters. Place transforms that create new columns (like ``WindPowerFeatureAdder``) before transforms that may lag those columns (like ``LagsAdder``).


Writing Custom Transforms
--------------------------

To create a custom feature transform, implement the ``TimeSeriesTransform`` interface with ``BaseConfig``:

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig
   from pydantic import Field
   import numpy as np

   class TemperatureInteractionAdder(BaseConfig, TimeSeriesTransform):
       """Adds temperature interaction features for heating/cooling load modeling."""

       heating_threshold: float = Field(default=15.0, description="Temperature below which heating demand increases")
       cooling_threshold: float = Field(default=25.0, description="Temperature above which cooling demand increases")

       def is_fitted(self) -> bool:
           return True  # No fitting needed for this transform

       def fit(self, data: TimeSeriesDataset) -> None:
           pass

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.to_dataframe()

           # Heating degree feature
           df["heating_degrees"] = np.maximum(self.heating_threshold - df["temperature"], 0)

           # Cooling degree feature
           df["cooling_degrees"] = np.maximum(df["temperature"] - self.cooling_threshold, 0)

           # Squared terms for non-linear response
           df["heating_degrees_sq"] = df["heating_degrees"] ** 2
           df["cooling_degrees_sq"] = df["cooling_degrees"] ** 2

           return TimeSeriesDataset(df)

       def features_added(self) -> list[str]:
           return [
               "heating_degrees",
               "cooling_degrees",
               "heating_degrees_sq",
               "cooling_degrees_sq",
           ]

Key implementation guidelines:

- Use Pydantic ``Field`` for configurable parameters with defaults and descriptions
- Implement ``features_added()`` to declare what columns your transform creates—this enables pipeline introspection
- Keep transforms stateless when possible (``is_fitted`` returns ``True``)
- For stateful transforms, store learned state in private attributes using ``PrivateAttr``


Stateful Transforms
^^^^^^^^^^^^^^^^^^^

Some transforms need to learn parameters from training data. Use Pydantic's ``PrivateAttr`` for internal state:

.. code-block:: python

   from pydantic import PrivateAttr
   from typing import Optional

   class NormalizingTransform(BaseConfig, TimeSeriesTransform):
       """Normalizes a column using statistics learned during fit."""

       column: str = "load"
       _mean: Optional[float] = PrivateAttr(default=None)
       _std: Optional[float] = PrivateAttr(default=None)

       def is_fitted(self) -> bool:
           return self._mean is not None and self._std is not None

       def fit(self, data: TimeSeriesDataset) -> None:
           df = data.to_dataframe()
           self._mean = df[self.column].mean()
           self._std = df[self.column].std()

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           if not self.is_fitted():
               raise RuntimeError("Transform must be fitted before calling transform()")
           df = data.to_dataframe()
           df[f"{self.column}_normalized"] = (df[self.column] - self._mean) / self._std
           return TimeSeriesDataset(df)

       def features_added(self) -> list[str]:
           return [f"{self.column}_normalized"]

.. warning::

   Stateful transforms must be fitted before calling ``transform()``. When using a ``TransformPipeline``, calling ``pipeline.fit()`` handles this automatically for all steps.


Autocorrelation-Based Lag Selection
------------------------------------

For adaptive feature engineering, OpenSTEF provides ``generate_autocorr_lags`` which selects lag features based on the autocorrelation structure of the signal:

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import generate_autocorr_lags
   from datetime import timedelta
   import pandas as pd

   # Automatically detect significant lags from the signal
   significant_lags = generate_autocorr_lags(
       signal=load_series,
       min_horizon=timedelta(hours=1),
       height_threshold=0.1,
   )

This is useful when you don't know the dominant periodicities in advance—the function identifies peaks in the autocorrelation function and returns corresponding lag durations.


Best Practices
--------------

- **Feature naming**: Use descriptive, consistent names. The ``features_added()`` method should return exactly the columns your transform creates.
- **Idempotency**: Running a transform twice should not create duplicate columns or corrupt data.
- **Horizon awareness**: For forecasting features, always consider whether the data would be available at prediction time. Use ``min_horizon`` parameters to enforce this.
- **Validation early**: Place ``CompletenessChecker`` and similar validation transforms at the start of your pipeline to fail fast on bad data.
- **Serialization**: Because transforms inherit from ``BaseConfig``, they serialize cleanly to JSON/YAML for experiment tracking and reproducibility.

.. seealso::

   - :doc:`model_training` for how feature pipelines integrate with model training
   - :doc:`forecasting` for using trained models with feature pipelines in production
   - :doc:`data_preparation` for preparing raw data before feature engineering