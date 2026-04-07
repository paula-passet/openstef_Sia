Reliability and Fallback Strategies
====================================

Production energy forecasting systems must produce predictions continuously, even when
conditions are imperfect. Models may encounter missing input data, stale weather
forecasts, or training failures. This page covers the strategies OpenSTEF provides for
handling these situations gracefully, so your forecasting pipeline degrades smoothly
rather than failing silently or catastrophically.

For background on how forecasting models work in OpenSTEF, see :doc:`forecasting_basics`.
For details on choosing between models, see :doc:`model_selection`.


Why Fallback Strategies Matter
------------------------------

In energy grid operations, a missing forecast can be worse than an imperfect one.
Operators need *some* prediction to make scheduling and balancing decisions. OpenSTEF
is designed with this reality in mind, providing multiple layers of defense:

- **Input validation** catches bad data before it reaches models
- **Completeness checking** ensures sufficient data quality for reliable predictions
- **Base case forecasters** provide simple but robust fallback predictions
- **Structured exceptions** let you build targeted recovery logic


Input Validation and Data Quality
---------------------------------

The first line of defense is catching problems in your input data before they propagate
through the forecasting pipeline.

Completeness Checking
^^^^^^^^^^^^^^^^^^^^^

The ``CompletenessChecker`` transform verifies that your time series data has enough
non-missing values to produce reliable forecasts. It calculates the ratio of non-null
values to total values and raises an exception if the data falls below a configurable
threshold:

.. code-block:: python

   from datetime import timedelta
   import numpy as np
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker

   # Create a dataset with significant gaps
   data = pd.DataFrame({
       "radiation": [100, np.nan, np.nan, np.nan],
       "temperature": [20, np.nan, 24, np.nan],
       "wind_speed": [np.nan, np.nan, np.nan, np.nan],
   }, index=pd.date_range("2025-01-01", periods=4, freq="15min"))

   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   # Configure completeness requirements
   checker = CompletenessChecker(
       completeness_threshold=0.5,  # Require at least 50% non-null values
       columns=["radiation", "temperature", "wind_speed"],
   )

   # This will raise InsufficientlyCompleteError (completeness is 0.25)
   checker.transform(dataset)

You can also assign weights to columns, making certain features (like load or
temperature) more important than others in the completeness calculation:

.. code-block:: python

   checker = CompletenessChecker(
       completeness_threshold=0.5,
       columns=["temperature", "wind_speed", "radiation"],
       weights={"temperature": 2.0, "wind_speed": 1.0, "radiation": 1.0},
   )

Input Consistency Checking
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``InputConsistencyChecker`` ensures that the features available at prediction time
match those seen during training. This catches a common production issue: schema drift
where columns are added, removed, or renamed between training and inference. The checker
logs warnings for extra columns and removes them, while raising errors for missing
required features.

.. note::

   Consistency checking is especially important when weather data providers change their
   API schemas or when new data sources are integrated into your pipeline.


The Base Case Forecaster: Your Safety Net
-----------------------------------------

When a sophisticated ML model fails — whether due to missing features, a corrupted model
artifact, or an unexpected input distribution — you need a prediction that is simple
enough to almost always succeed. OpenSTEF's ``BaseCaseForecaster`` fills this role.

The base case forecaster operates on a straightforward principle: energy consumption
patterns tend to repeat weekly. It takes the load values from one week ago and repeats
them as the forecast. If last week's data is also unavailable, it falls back to two
weeks ago.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   # Default: 7-day primary lag, 14-day fallback
   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
   )

   # Custom lag configuration for domains with different periodicity
   custom_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

The base case forecaster also calculates confidence intervals from hourly standard
deviations, so you still get uncertainty estimates even in fallback mode. For more on
how quantile predictions work, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Fallback chain showing: ML Model prediction → (on failure) → Base Case Forecaster with 7-day lag → (on failure) → Base Case Forecaster with 14-day lag → (on failure) → raise error]


Structured Exception Handling
-----------------------------

OpenSTEF defines a hierarchy of domain-specific exceptions that let you build precise
recovery logic. Rather than catching generic ``Exception`` types, you can target exactly
the failure mode you want to handle:

.. list-table:: Key Exception Types
   :header-rows: 1
   :widths: 35 65

   * - Exception
     - When It's Raised
   * - ``InsufficientlyCompleteError``
     - Input data has too many missing values
   * - ``PredictError``
     - An error occurs during the forecasting operation
   * - ``ModelLoadingError``
     - A saved model fails to load (corruption, version mismatch)
   * - ``NotFittedError``
     - A model or transform is used before being fitted
   * - ``FlatlinerDetectedError``
     - Input data contains constant (flatline) values, indicating sensor failure
   * - ``InputValidationError``
     - General input validation failures
   * - ``ModelNotFoundError``
     - A requested model does not exist in storage

Building a Fallback Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here is a pattern for combining these exceptions into a robust prediction pipeline:

.. code-block:: python

   from openstef_core.exceptions import (
       InsufficientlyCompleteError,
       ModelLoadingError,
       NotFittedError,
       PredictError,
   )

   def predict_with_fallback(primary_model, fallback_model, dataset):
       """Attempt prediction with primary model, fall back if it fails."""
       try:
           forecast = primary_model.predict(dataset)
           return forecast, "primary"
       except (PredictError, NotFittedError, ModelLoadingError) as e:
           logging.warning("Primary model failed: %s. Using fallback.", e)
       except InsufficientlyCompleteError as e:
           logging.warning("Data quality too low for primary model: %s", e)

       # Fall back to base case forecaster
       try:
           forecast = fallback_model.predict(dataset)
           return forecast, "fallback"
       except Exception as e:
           logging.error("Fallback model also failed: %s", e)
           raise

.. warning::

   Always log which model produced a given forecast. When the fallback model activates,
   downstream systems should be aware that prediction quality may be reduced. Include
   the model source in your forecast metadata.


Detecting Model Staleness
--------------------------

A model that was trained weeks or months ago may no longer reflect current conditions.
Seasonal shifts, new equipment installations, or changes in consumer behavior can all
cause model performance to degrade over time. While OpenSTEF does not enforce a single
staleness policy, you should implement checks in your operational pipeline:

.. code-block:: python

   from datetime import datetime, timedelta

   def check_model_staleness(model_metadata, max_age=timedelta(days=14)):
       """Check if a model needs retraining based on its age.

       Args:
           model_metadata: Dictionary with model training information.
           max_age: Maximum acceptable age before the model is considered stale.

       Returns:
           True if the model is stale and should be retrained.
       """
       trained_at = model_metadata.get("trained_at")
       if trained_at is None:
           return True  # No training date recorded — treat as stale

       age = datetime.now() - trained_at
       if age > max_age:
           logging.warning(
               "Model is %d days old (threshold: %d days). Consider retraining.",
               age.days,
               max_age.days,
           )
           return True
       return False

Combine staleness detection with your fallback strategy: if the primary model is stale,
you might still use it but flag the forecast as lower confidence, or switch to the base
case forecaster while triggering an automatic retraining job.


Handling Flatline Data
----------------------

Sensor failures often manifest as constant (flatline) readings rather than obvious
missing values. A temperature sensor stuck at 20°C or a load meter reporting zero will
produce data that *looks* valid but leads to poor forecasts. OpenSTEF raises
``FlatlinerDetectedError`` when this pattern is detected, allowing you to intercept
the problem:

.. code-block:: python

   from openstef_core.exceptions import FlatlinerDetectedError

   try:
       forecast = model.predict(dataset)
   except FlatlinerDetectedError:
       logging.warning("Flatline detected in input data — sensor may be faulty.")
       # Option 1: Use fallback model
       # Option 2: Interpolate from neighboring sensors
       # Option 3: Alert operations team
       forecast = fallback_model.predict(dataset)


Best Practices for Production Reliability
-----------------------------------------

Based on patterns from real-world energy forecasting deployments:

- **Layer your defenses.** Validate inputs, then try the primary model, then fall back.
  Don't rely on a single check.

- **Monitor fallback activation rate.** If your base case forecaster is running more
  than occasionally, something systemic needs attention — investigate data pipelines
  or retrain models.

- **Set completeness thresholds per use case.** A 50% threshold might be acceptable for
  day-ahead forecasts where some interpolation is fine, but intraday forecasts for grid
  balancing may need 90%+.

- **Log everything.** Record which model produced each forecast, what data quality
  looked like, and whether any fallback was activated. This is invaluable for
  post-incident analysis.

- **Test your fallback paths.** Deliberately inject missing data and model failures in
  staging environments to verify that degradation is truly graceful.

- **Keep fallback models simple.** The base case forecaster works precisely because it
  has minimal dependencies. A complex fallback model that fails for the same reasons as
  your primary model provides no safety.