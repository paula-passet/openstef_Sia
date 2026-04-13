Your Forecast in Five Steps
===========================

This tutorial walks you through producing your first energy forecast with OpenSTEF from
scratch. By the end, you will have loaded time series data, assembled a preprocessing
pipeline, trained a model, generated predictions, and inspected the results — with a
clear explanation of *why* each step matters, not just *what* to call.

If you want the absolute shortest path to a working forecast without explanation, see
:doc:`quickstart`. For comparing multiple models against historical data, see
:doc:`backtesting`.

.. note:: [DIAGRAM: Step-by-step flowchart showing the five stages of an OpenSTEF
   forecast — (1) Data Preparation → (2) Feature Engineering → (3) Model Training →
   (4) Prediction → (5) Evaluation — connected by arrows. Decision points shown at
   "Data valid?" (between stages 1 and 2, looping back on failure) and "Model
   acceptable?" (between stages 3 and 4, looping back to re-train with different
   hyperparameters on failure).]


Overview
--------

OpenSTEF is a **library**: you compose its building blocks inside your own Python code
rather than running a standalone application. The core abstraction is the
``ForecastingModel``, a pipeline that chains preprocessing transforms, a forecaster,
and postprocessing transforms into a single object with ``fit()`` and ``predict()``
methods. Wrapping that model in a ``CustomForecastingWorkflow`` adds lifecycle hooks
and optional model persistence.

The five steps below mirror the stages in the diagram above.


Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects time series data wrapped in a ``VersionedTimeSeriesDataset``. The
"versioned" part means the dataset can track *when* each observation became available,
which is important for realistic backtesting and avoiding look-ahead bias. For a first
forecast you can ignore that subtlety and load a plain DataFrame.

Your DataFrame must have:

- A ``pd.DatetimeIndex`` named ``"timestamp"``
- A target column (typically ``"load"``) containing the values you want to forecast
- Optional exogenous columns such as weather variables

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Build 90 days of synthetic 15-minute load data with a temperature covariate.
   rng = np.random.default_rng(42)
   n_samples = 90 * 24 * 4  # 15-minute intervals

   index = pd.date_range("2024-01-01", periods=n_samples, freq="15min", name="timestamp")

   raw = pd.DataFrame(
       {
           "load": 200 + 50 * np.sin(2 * np.pi * np.arange(n_samples) / (24 * 4))
                   + rng.standard_normal(n_samples) * 10,
           "temperature": 10 + 5 * np.cos(2 * np.pi * np.arange(n_samples) / (24 * 4 * 7))
                          + rng.standard_normal(n_samples),
       },
       index=index,
   )

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw,
       sample_interval=timedelta(minutes=15),
   )

   print(f"Dataset: {len(raw)} rows, columns: {list(raw.columns)}")

``from_dataframe`` is the simplest constructor. It wraps your DataFrame in a single
``TimeSeriesDataset`` part and records the sample interval, which downstream transforms
use to compute lag offsets correctly.

.. note::

   Real-world data often has gaps and flatlines. OpenSTEF provides
   ``CompletenessChecker`` and ``FlatlineChecker`` transforms that you can add to your
   preprocessing pipeline (Step 2) to catch these problems early rather than silently
   training on bad data.


Step 2 — Configure Feature Engineering
---------------------------------------

Raw load and weather values alone are rarely enough for a good short-term forecast.
OpenSTEF ships a library of *transforms* — stateless or stateful objects with
``fit()`` / ``transform()`` methods — that you chain together in a
``TransformPipeline``.

The most important transforms for a first forecast are:

- ``HolidayFeatureAdder`` — adds binary flags for public holidays by country
- ``DatetimeFeaturesAdder`` — adds hour-of-day, day-of-week, and similar cyclic features
- ``LagsAdder`` — creates lagged copies of the target column at specified offsets
- ``Scaler`` — standardises feature columns so gradient-boosted trees converge faster

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.general import Scaler
   from openstef_models.utils.feature_selection import Exclude

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code="NL"),
           DatetimeFeaturesAdder(onehot_encode=False),
           LagsAdder(
               feature="load",
               lags=[timedelta(hours=24), timedelta(hours=48), timedelta(days=7)],
           ),
           Scaler(selection=Exclude("load"), method="standard"),
       ]
   )

The order matters: ``LagsAdder`` must run after the target column is present, and
``Scaler`` should run last so it sees the final feature set.

.. note::

   ``LagsAdder`` introduces NaN rows at the start of the dataset — one row per lag
   offset. When you build the ``ForecastingModel`` in Step 3, set ``cutoff_history``
   to a ``timedelta`` that covers your longest lag so those incomplete rows are
   excluded from training. For a 7-day lag, use ``cutoff_history=timedelta(days=7)``.


Step 3 — Build and Train the Model
------------------------------------

A ``ForecastingModel`` combines your preprocessing pipeline, a forecaster, and an
optional postprocessing pipeline. The forecaster is the component that actually learns
from data; OpenSTEF provides XGBoost, LightGBM, and simpler baselines out of the box.

For a first forecast, ``XGBoostForecaster`` is a solid default. You specify the
*horizons* — how far ahead you want to predict — and the *quantiles* for probabilistic
output.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_models.transforms.postprocessing import (
       ConfidenceIntervalApplicator,
       QuantileSorter,
   )

   horizons = [
       LeadTime.from_string("PT1H"),
       LeadTime.from_string("PT6H"),
       LeadTime.from_string("PT24H"),
   ]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       preprocessing=preprocessing,          # pipeline from Step 2
       forecaster=XGBoostForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
       postprocessing=TransformPipeline(
           transforms=[
               QuantileSorter(),
               ConfidenceIntervalApplicator(
                   quantiles=quantiles,
                   add_quantiles_from_std=False,
               ),
           ]
       ),
       target_column="load",
       cutoff_history=timedelta(days=7),     # exclude rows with incomplete lags
   )

Now wrap the model in a ``CustomForecastingWorkflow`` and call ``fit()``:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_first_forecast",
   )

   fit_result = workflow.fit(dataset)
   print("Training complete.")

``fit()`` runs the full pipeline: it fits the preprocessing transforms on the training
split, trains the XGBoost forecaster, and stores the fitted state inside the workflow.
The ``fit_result`` object contains training metrics and metadata you can inspect or log.

.. note::

   By default, ``CustomForecastingWorkflow`` splits your dataset internally into
   training and validation sets. You can customise the split strategy by passing a
   ``DataSplitter`` instance to ``ForecastingModel``. See :doc:`advanced_customization`
   for details.


Step 4 — Generate Forecasts
----------------------------

Once the workflow is fitted, call ``predict()`` with the same (or newer) dataset.
OpenSTEF applies the fitted preprocessing transforms to the input data, runs the
forecaster, and applies postprocessing to produce a ``ForecastDataset``.

.. code-block:: python

   forecasts = workflow.predict(dataset)

   # Convert to a plain DataFrame for inspection
   forecast_df = forecasts.data
   print(forecast_df.head())
   print(f"\nForecast columns: {list(forecast_df.columns)}")

The output DataFrame is indexed by timestamp and contains one column per quantile
(e.g. ``q_0.1``, ``q_0.5``, ``q_0.9``) plus a ``horizon`` column indicating the
lead time for each row. The ``q_0.5`` column is the point forecast; the outer quantiles
form a prediction interval.

.. note::

   ``predict()`` requires that the input dataset contains enough history to compute
   the lag features configured in Step 2. If you pass a dataset that starts at the
   same timestamp as your training data, this is satisfied automatically. When
   deploying in production, ensure your inference dataset always includes at least
   ``cutoff_history`` of historical observations before the forecast origin.


Step 5 — Evaluate the Results
-------------------------------

A forecast is only useful if you know how good it is. The simplest evaluation is to
compare the ``q_0.5`` point forecast against held-out actuals using standard metrics.

.. code-block:: python

   from sklearn.metrics import mean_absolute_error, r2_score

   # Use the last 24 hours as a held-out evaluation window
   eval_start = raw.index[-24 * 4]
   actuals = raw.loc[eval_start:, "load"]

   # Align forecast to the same window (24-hour horizon)
   point_forecast = (
       forecast_df[forecast_df["horizon"] == "PT24H"]
       .loc[eval_start:]
       ["q_0.5"]
       .reindex(actuals.index)
   )

   mae = mean_absolute_error(actuals.dropna(), point_forecast.dropna())
   r2 = r2_score(actuals.dropna(), point_forecast.dropna())

   print(f"MAE : {mae:.2f} MW")
   print(f"R²  : {r2:.4f}")

A good short-term load forecast typically achieves R² > 0.95 on clean data. If your
score is lower, common causes are:

- **Too little training data** — XGBoost needs at least several weeks of data to learn
  weekly seasonality. Aim for 90 days or more.
- **Missing weather features** — temperature alone can explain a large fraction of load
  variance. Add wind speed, solar radiation, or humidity if available.
- **Stale lags** — if your lag offsets do not align with the dominant periodicities in
  your data (daily, weekly), the model cannot exploit autocorrelation effectively.

For a rigorous comparison of model configurations over a long historical window, see
:doc:`backtesting`.


Persisting the Model
--------------------

In a real deployment you will want to save the trained model and reload it later.
``CustomForecastingWorkflow`` supports file-based persistence through
``LocalModelStorage``:

.. code-block:: python

   from pathlib import Path
   from openstef_models.storage.local_model_storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))

   # Save
   storage.save(model_id="my_first_forecast", model=workflow.model)

   # Load later
   loaded_model = storage.load(model_id="my_first_forecast")
   loaded_workflow = CustomForecastingWorkflow(
       model=loaded_model,
       model_id="my_first_forecast",
   )
   new_forecasts = loaded_workflow.predict(dataset)

For production systems that need versioning, experiment tracking, and model selection,
OpenSTEF integrates with MLflow via ``MLFlowStorageCallback``. See
:doc:`advanced_customization` for a full walkthrough.


Putting It All Together
-----------------------

Here is the complete, self-contained script for reference:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.mixins import TransformPipeline
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.general import Scaler
   from openstef_models.transforms.postprocessing import (
       ConfidenceIntervalApplicator,
       QuantileSorter,
   )
   from openstef_models.utils.feature_selection import Exclude
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from sklearn.metrics import mean_absolute_error, r2_score

   # --- 1. Data ---
   rng = np.random.default_rng(42)
   n_samples = 90 * 24 * 4
   index = pd.date_range("2024-01-01", periods=n_samples, freq="15min", name="timestamp")
   raw = pd.DataFrame(
       {
           "load": 200 + 50 * np.sin(2 * np.pi * np.arange(n_samples) / (24 * 4))
                   + rng.standard_normal(n_samples) * 10,
           "temperature": 10 + 5 * np.cos(2 * np.pi * np.arange(n_samples) / (24 * 4 * 7))
                          + rng.standard_normal(n_samples),
       },
       index=index,
   )
   dataset = VersionedTimeSeriesDataset.from_dataframe(raw, sample_interval=timedelta(minutes=15))

   # --- 2. Preprocessing ---
   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code="NL"),
           DatetimeFeaturesAdder(onehot_encode=False),
           LagsAdder(
               feature="load",
               lags=[timedelta(hours=24), timedelta(hours=48), timedelta(days=7)],
           ),
           Scaler(selection=Exclude("load"), method="standard"),
       ]
   )

   # --- 3. Model ---
   horizons = [LeadTime.from_string("PT1H"), LeadTime.from_string("PT24H")]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=XGBoostForecaster(horizons=horizons, quantiles=quantiles),
       postprocessing=TransformPipeline(
           transforms=[
               QuantileSorter(),
               ConfidenceIntervalApplicator(quantiles=quantiles, add_quantiles_from_std=False),
           ]
       ),
       target_column="load",
       cutoff_history=timedelta(days=7),
   )

   workflow = CustomForecastingWorkflow(model=model, model_id="my_first_forecast")
   workflow.fit(dataset)

   # --- 4. Predict ---
   forecasts = workflow.predict(dataset)
   forecast_df = forecasts.data

   # --- 5. Evaluate ---
   eval_start = raw.index[-24 * 4]
   actuals = raw.loc[eval_start:, "load"]
   point_forecast = (
       forecast_df[forecast_df["horizon"] == "PT24H"]
       .loc[eval_start:]["q_0.5"]
       .reindex(actuals.index)
   )
   mae = mean_absolute_error(actuals.dropna(), point_forecast.dropna())
   r2 = r2_score(actuals.dropna(), point_forecast.dropna())
   print(f"MAE={mae:.2f}  R²={r2:.4f}")


Next Steps
----------

- :doc:`backtesting` — evaluate your model rigorously over a long historical window
  and compare it against alternative configurations.
- :doc:`advanced_customization` — write custom transforms, swap in a different
  forecaster, or integrate MLflow for experiment tracking.
- :doc:`installation` — if you hit import errors, revisit the installation guide to
  ensure all optional dependencies are present.