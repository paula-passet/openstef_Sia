Feature Engineering
===================

This guide covers feature engineering in OpenSTEF: the built-in transforms available for creating features from time series data, how they compose into pipelines, and how to write your own custom transforms.

For information on how features feed into the forecasting workflow, see :doc:`forecasting`. For details on the ``TimeSeriesDataset`` that transforms operate on, see :doc:`datasets`.

Overview
--------

OpenSTEF's feature engineering system is built around **transforms** — composable units that take a ``TimeSeriesDataset`` and return an enriched ``TimeSeriesDataset`` with additional columns. Transforms are organized into domain-specific modules and can be assembled into a ``TransformPipeline`` for sequential execution.

.. mermaid:: /diagrams/user_guide/guides/feature_engineering_diagram_1.mmd

The Transform Interface
-----------------------

All transforms implement the ``TimeSeriesTransform`` interface from ``openstef_core.transforms``. Each transform:

- Accepts a ``TimeSeriesDataset`` via its ``transform()`` method
- Returns a ``TimeSeriesDataset`` with new or modified columns
- Exposes ``features_added()`` to declare which columns it creates
- Is configured via Pydantic fields (inheriting from ``BaseConfig``)

.. code-block:: python

   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseConfig


   class MyTransform(BaseConfig, TimeSeriesTransform):
       """Example custom transform."""

       some_parameter: float = 1.0

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Add a new feature column
           df = data.to_dataframe()
           df["my_feature"] = df["load"] * self.some_parameter
           return TimeSeriesDataset.from_dataframe(df, metadata=data.metadata)

       def features_added(self) -> list[str]:
           return ["my_feature"]

Built-in Transforms
-------------------

OpenSTEF provides transforms organized into four categories:

General Transforms
^^^^^^^^^^^^^^^^^^

These are domain-agnostic utilities for data preparation and feature manipulation. Import them from ``openstef_models.transforms.general``:

- **Imputer** — Fills missing values using configurable strategies
- **OutlierHandler** — Detects and masks outliers (creates ``outlier_nan_mask_*`` columns)
- **Scaler** — Normalizes feature values
- **Selector** — Selects a subset of features for downstream use
- **Shifter** — Shifts columns forward/backward in time
- **Flagger** — Adds binary flag columns based on conditions
- **NaNDropper** — Removes rows with NaN values
- **EmptyFeatureRemover** — Drops columns that contain no useful data
- **DimensionalityReducer** — Reduces feature space dimensionality
- **SampleWeighter** — Assigns sample weights for training

.. code-block:: python

   from openstef_models.transforms.general import Imputer, OutlierHandler, Scaler

   # Configure an imputer
   imputer = Imputer(strategy="linear")

   # Apply to a dataset
   cleaned_data = imputer.transform(raw_data)

Time Domain Transforms
^^^^^^^^^^^^^^^^^^^^^^

These create features that capture temporal patterns:

- **LagsAdder** — Creates lagged copies of the target variable to capture temporal dependencies. Supports trivial lags (minute/day-based), custom lags, and autocorrelation-based adaptive lag selection.
- **VersionedLagsAdder** — Creates lag features for versioned (multi-horizon) datasets while respecting data availability constraints.

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   # Create lag features with day-based lags
   lags_adder = LagsAdder(
       lag_strategy="trivial",
       trivial_day_lags=[1, 2, 7],  # 1-day, 2-day, and 1-week lags
   )

   enriched_data = lags_adder.transform(dataset)
   print(lags_adder.features_added())

Energy Domain Transforms
^^^^^^^^^^^^^^^^^^^^^^^^

Domain-specific transforms for energy forecasting:

- **WindPowerFeatureAdder** — Computes wind power features from wind speed data using power curve relationships.

.. code-block:: python

   from openstef_models.transforms.energy_domain.wind_power_feature_adder import (
       WindPowerFeatureAdder,
   )

   wind_transform = WindPowerFeatureAdder()
   data_with_wind_power = wind_transform.transform(dataset)

Validation Transforms
^^^^^^^^^^^^^^^^^^^^^

Transforms that check data quality without modifying features:

- **CompletenessChecker** — Validates that time series load data meets completeness thresholds. Returns data unchanged or raises an error if requirements are not met.

.. code-block:: python

   from openstef_models.transforms.validation.completeness_checker import (
       CompletenessChecker,
   )

   checker = CompletenessChecker(min_completeness=0.9)
   validated_data = checker.transform(dataset)  # Raises if <90% complete

Building Transform Pipelines
-----------------------------

Individual transforms are composed into a ``TransformPipeline`` that executes them sequentially:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.general import Imputer, OutlierHandler, NaNDropper
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   # Build a preprocessing pipeline
   pipeline = TransformPipeline[TimeSeriesDataset](
       steps=[
           OutlierHandler(),
           Imputer(strategy="linear"),
           LagsAdder(lag_strategy="trivial", trivial_day_lags=[1, 7]),
           NaNDropper(),
       ]
   )

   # Apply the full pipeline
   processed_data = pipeline.transform(raw_dataset)

.. mermaid:: /diagrams/user_guide/guides/feature_engineering_diagram_2.mmd

The pipeline preserves ordering — transforms that create features (like ``LagsAdder``) should come before transforms that drop incomplete rows (like ``NaNDropper``).

Writing Custom Transforms
--------------------------

To create a custom transform, subclass both ``BaseConfig`` and ``TimeSeriesTransform``:

.. code-block:: python

   import pandas as pd
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform


   class RollingStatsAdder(BaseConfig, TimeSeriesTransform):
       """Adds rolling mean and standard deviation features."""

       window_hours: int = 24
       target_column: str = "load"

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.to_dataframe()
           window = f"{self.window_hours}h"

           df[f"{self.target_column}_rolling_mean_{self.window_hours}h"] = (
               df[self.target_column].rolling(window).mean()
           )
           df[f"{self.target_column}_rolling_std_{self.window_hours}h"] = (
               df[self.target_column].rolling(window).std()
           )

           return TimeSeriesDataset.from_dataframe(df, metadata=data.metadata)

       def features_added(self) -> list[str]:
           return [
               f"{self.target_column}_rolling_mean_{self.window_hours}h",
               f"{self.target_column}_rolling_std_{self.window_hours}h",
           ]

Use your custom transform in a pipeline just like any built-in transform:

.. code-block:: python

   pipeline = TransformPipeline[TimeSeriesDataset](
       steps=[
           Imputer(strategy="linear"),
           RollingStatsAdder(window_hours=6),
           RollingStatsAdder(window_hours=24),
           LagsAdder(lag_strategy="trivial", trivial_day_lags=[1, 7]),
           NaNDropper(),
       ]
   )

Fitted Transforms
^^^^^^^^^^^^^^^^^

Some transforms require a ``fit()`` step before they can be applied (e.g., ``VersionedLagsAdder``). These transforms have an ``is_fitted`` property:

.. code-block:: python

   from openstef_models.transforms.time_domain.versioned_lags_adder import (
       VersionedLagsAdder,
   )

   adder = VersionedLagsAdder()
   assert not adder.is_fitted

   adder.fit(training_data)
   assert adder.is_fitted

   result = adder.transform(new_data)

.. warning::

   Calling ``transform()`` on an unfitted transform that requires fitting will raise an error. Always check ``is_fitted`` or call ``fit()`` before ``transform()`` when working with stateful transforms.

Best Practices
--------------

- **Order matters**: Place imputation before lag creation, and NaN dropping last.
- **Declare features**: Always implement ``features_added()`` so downstream components know which columns were generated.
- **Use Pydantic configuration**: Define parameters as typed fields with defaults for reproducibility and serialization.
- **Respect horizons**: When creating lag features, ensure lags are valid for the forecast horizon. The ``LagsAdder`` handles this automatically via ``validate_horizons_present``.
- **Keep transforms stateless when possible**: Stateless transforms are easier to serialize and reuse across datasets.