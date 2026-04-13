Quickstart
==========

Get your first forecast running in under five minutes. This page is intentionally minimal — copy the code, run it, see output. For explanations of what each step does, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF and its model library must be installed before running the examples below. See :doc:`installation` if you haven't done this yet.

.. code-block:: python

   pip install openstef openstef-models

Minimal Working Example
-----------------------

The following self-contained script generates synthetic hourly load data, trains a forecasting model, and produces a 24-hour-ahead forecast. No external data files or database connections are required.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.types import LeadTime, Q

   # ── 1. Create sample data ────────────────────────────────────────────────────
   rng = np.random.default_rng(42)
   n_samples = 24 * 90  # 90 days of hourly observations

   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h")
   temp      = rng.standard_normal(size=n_samples)
   wind      = rng.standard_normal(size=n_samples)
   radiation = rng.standard_normal(size=n_samples)

   load = wind * -10 + temp * -3 + radiation * -5 + rng.standard_normal(size=n_samples) * 2

   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {"load": load, "temp": temp, "wind": wind, "radiation": radiation},
           index=timestamps,
       ),
       sample_interval=timedelta(hours=1),
   )

   # ── 2. Define the model ──────────────────────────────────────────────────────
   horizons = [LeadTime.from_string("PT24H")]

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       ),
       target_column="load",
   )

   # ── 3. Create a workflow and train ───────────────────────────────────────────
   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart_model")
   workflow.fit(dataset)

   # ── 4. Generate a forecast ───────────────────────────────────────────────────
   forecast = workflow.predict(dataset)

   # ── 5. Inspect the output ────────────────────────────────────────────────────
   print(forecast.data.head(10))

Running this script prints the first ten rows of the forecast ``DataFrame``, with one column per requested quantile (``q0.1``, ``q0.5``, ``q0.9``) and a ``DatetimeIndex`` covering the next 24 hours.

.. note::

   ``ConstantMedianForecaster`` is a lightweight baseline model — ideal for
   verifying your setup. Swap it for ``GBLinearForecaster`` or another
   ``openstef-models`` estimator when you are ready to move beyond the baseline.
   See :doc:`first_forecast` for guidance on choosing a model.

Step-by-Step Breakdown
----------------------

If the script above ran successfully, here is what each numbered block did:

1. **Load data** — ``TimeSeriesDataset`` wraps a ``pandas.DataFrame`` together with a ``sample_interval``. The index must be a ``DatetimeIndex`` and the target column (``"load"``) must be present.

2. **Define the model** — ``ForecastingModel`` is the central pipeline object. It composes optional preprocessing, a core forecaster, and optional postprocessing. ``horizons`` controls how far ahead the model learns to predict.

3. **Create a workflow and train** — ``CustomForecastingWorkflow`` orchestrates ``fit`` and ``predict`` calls, handles model persistence, and provides a callback hook system. Calling ``workflow.fit(dataset)`` trains the model in-place.

4. **Generate a forecast** — ``workflow.predict(dataset)`` returns a ``ForecastDataset`` whose ``.data`` attribute is a ``DataFrame`` indexed by forecast timestamp.

5. **Inspect the output** — The forecast ``DataFrame`` contains one column per quantile. The median column (``q0.5``) is your point forecast; the others give a probabilistic interval.

Switching to a More Powerful Model
-----------------------------------

Replace ``ConstantMedianForecaster`` with ``GBLinearForecaster`` for a gradient-boosted model with feature engineering:

.. code-block:: python

   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )
   from openstef_models.preprocessing.transforms import Scaler, HolidayFeatureAdder
   from openstef_models.preprocessing.pipeline import TransformPipeline
   from openstef_models.preprocessing.feature_selection import FeatureSelection
   from openstef_models.types import CountryAlpha2

   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(
                   method="standard",
                   selection=FeatureSelection(include={"temp", "wind", "radiation"}),
               ),
               HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           ]
       ),
       forecaster=GBLinearForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           hyperparams=GBLinearHyperParams(n_steps=500, learning_rate=0.1),
       ),
       target_column="load",
   )

   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart_gblinear")
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)
   print(forecast.data.head(10))

The rest of the workflow is identical — only the ``model`` object changes.

Saving and Reloading a Model
-----------------------------

To persist a trained model to disk and reload it later:

.. code-block:: python

   from openstef_models.storage.local_model_storage import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(base_path=Path("./models"))

   # Save after training
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="quickstart_gblinear",
       storage=storage,
   )
   workflow.fit(dataset)   # model is automatically saved via storage

   # Reload and predict without re-training
   loaded_workflow = CustomForecastingWorkflow.from_storage(
       model_id="quickstart_gblinear",
       storage=storage,
   )
   forecast = loaded_workflow.predict(dataset)

.. note::

   ``LocalModelStorage`` writes models to the local filesystem. OpenSTEF's
   storage interface is pluggable — you can implement a custom backend (e.g.
   cloud object storage) by subclassing ``BaseModelStorage``.

Common Issues
-------------

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Symptom
     - Fix
   * - ``ModuleNotFoundError: openstef_models``
     - Run ``pip install openstef-models`` and verify your virtual environment is active.
   * - ``ValueError`` on ``TimeSeriesDataset`` construction
     - Ensure the ``DataFrame`` index is a ``DatetimeIndex`` with uniform frequency matching ``sample_interval``.
   * - Forecast ``DataFrame`` is empty
     - The dataset must contain enough history relative to the requested horizon. Use at least 30 days of data for a 24-hour horizon.
   * - ``NotImplementedError: does not support contributions``
     - ``ConstantMedianForecaster`` does not implement ``predict_contributions``. Switch to a model that supports it, or remove the contributions call.

Next Steps
----------

- :doc:`first_forecast` — the same workflow with full explanations, feature engineering details, and interpretation of results.
- :doc:`backtesting` — evaluate forecast accuracy on historical data before deploying a model.
- :doc:`advanced_customization` — custom preprocessors, callbacks, and storage backends.