Quickstart
==========

This page gets you from zero to a working energy forecast as fast as possible. Every
code block is copy-paste ready. For explanations of *why* things work the way they do,
see :doc:`first_forecast`. For installation help, see :doc:`installation`.

.. note::

   This guide assumes you have already installed OpenSTEF. If not, run
   ``pip install openstef`` first. See :doc:`installation` for details.


Prerequisites
-------------

Make sure you can import the library:

.. code-block:: python

   import openstef_models
   import openstef_core
   print("OpenSTEF is ready.")

If this fails, revisit :doc:`installation`.


Step 1: Create Synthetic Data
-----------------------------

OpenSTEF works with time series data indexed by datetime. For this quickstart, we'll
generate synthetic energy load data so you don't need any external files or databases.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   # Generate 30 days of hourly energy load data
   np.random.seed(42)
   n_hours = 30 * 24
   timestamps = pd.date_range(
       start="2024-01-01",
       periods=n_hours,
       freq="h",
       tz="UTC",
   )

   # Simulate a realistic daily pattern with noise
   hour_of_day = timestamps.hour
   daily_pattern = 50 + 20 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
   noise = np.random.normal(0, 3, size=n_hours)
   load = daily_pattern + noise

   data = pd.DataFrame({"load": load}, index=timestamps)
   data.index.name = "datetime"

   print(data.head())
   print(f"Shape: {data.shape}")


Step 2: Configure the Forecaster
---------------------------------

OpenSTEF uses a layered architecture. At the core is a **Forecaster** — the statistical
or ML model that produces predictions. The simplest built-in option is
``ConstantMedianForecaster``, which predicts the median of the training data. It's a
useful baseline and perfect for verifying your pipeline works.

.. code-block:: python

   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_core.types import LeadTime

   forecaster = ConstantMedianForecaster(
       horizons=[LeadTime.from_string("PT36H")],
   )

The ``horizons`` parameter defines how far ahead the model predicts. ``"PT36H"`` means
36 hours ahead — a common horizon for day-ahead energy forecasting.


Step 3: Build the Forecasting Model
------------------------------------

The ``ForecastingModel`` wraps a forecaster with preprocessing and postprocessing into
a complete pipeline. This is the main object you interact with for training and
prediction.

.. code-block:: python

   from openstef_models.models import ForecastingModel

   model = ForecastingModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=14),
   )

The ``cutoff_history`` parameter controls how much historical data the model uses. Set
it to at least match the maximum lag in your preprocessing pipeline. For this minimal
example, 14 days is sufficient.


Step 4: Train the Model
-----------------------

Call ``fit()`` with your training data:

.. code-block:: python

   model.fit(data)

That's it. The model computes the statistics it needs from the training data and is
ready to generate forecasts.


Step 5: Generate Forecasts
--------------------------

Pass new data to ``predict()`` to get forecasts:

.. code-block:: python

   # Use the most recent data as input for prediction
   recent_data = data.tail(48)  # Last 48 hours
   forecasts = model.predict(recent_data)

   print(forecasts)

The output is a ``TimeSeriesDataset`` containing the predicted values for each
timestamp in the forecast horizon.


Complete Working Example
------------------------

Here is the entire quickstart as a single, self-contained script:

.. code-block:: python

   """OpenSTEF Quickstart — minimal working example."""
   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models import ForecastingModel
   from openstef_core.types import LeadTime

   # --- 1. Create synthetic data ---
   np.random.seed(42)
   n_hours = 30 * 24
   timestamps = pd.date_range(
       start="2024-01-01", periods=n_hours, freq="h", tz="UTC"
   )
   hour_of_day = timestamps.hour
   daily_pattern = 50 + 20 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
   noise = np.random.normal(0, 3, size=n_hours)
   load = daily_pattern + noise

   data = pd.DataFrame({"load": load}, index=timestamps)
   data.index.name = "datetime"

   # --- 2. Configure forecaster and model ---
   forecaster = ConstantMedianForecaster(
       horizons=[LeadTime.from_string("PT36H")],
   )
   model = ForecastingModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=14),
   )

   # --- 3. Train ---
   model.fit(data)

   # --- 4. Predict ---
   forecasts = model.predict(data.tail(48))
   print("Forecasts:")
   print(forecasts)
   print("Done.")


What's Happening Under the Hood
-------------------------------

Even in this minimal example, OpenSTEF is doing real work:

- **Data validation** — the input is checked for correct types, missing values, and
  sufficient history.
- **Preprocessing** — the ``ForecastingModel`` applies any configured transforms
  before passing data to the forecaster.
- **Prediction** — the forecaster generates point and/or quantile forecasts.
- **Postprocessing** — results are formatted into a consistent ``TimeSeriesDataset``
  with proper timestamps and metadata.

The ``ConstantMedianForecaster`` is intentionally simple. It exists as a baseline and
for pipeline verification. For real forecasting performance, you'll want to use more
sophisticated models.


Common Issues
-------------

**ImportError: No module named 'openstef_models'**
   OpenSTEF is not installed. See :doc:`installation`.

**Empty or None forecasts**
   The model returns ``None`` when it determines there is insufficient data to make a
   reliable prediction. Ensure your training data has enough history (at least
   ``cutoff_history`` worth of data).

**Timezone-naive timestamps**
   OpenSTEF expects timezone-aware datetime indices. Always set a timezone on your
   data:

   .. code-block:: python

      data.index = data.index.tz_localize("UTC")


Next Steps
----------

Now that you have a working forecast, here's where to go next:

- :doc:`first_forecast` — understand each component in detail, use real-world data
  patterns, and configure feature engineering with ``FeaturePipeline``
- :doc:`backtesting` — compare different models and evaluate forecast accuracy
  systematically
- :doc:`advanced_customization` — build custom forecasters, transforms, and workflows