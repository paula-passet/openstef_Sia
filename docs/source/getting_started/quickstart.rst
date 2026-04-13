Quickstart
==========

Get a forecast running in under five minutes. This page is a minimal, copy-paste-ready example — no theory, no deep-dives. If you want explanations of what each step does, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

.. mermaid:: diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

Make sure OpenSTEF is installed before running the example below:

.. code-block:: bash

   pip install openstef

See :doc:`installation` for virtual-environment setup and optional dependencies.

Complete Example
----------------

The following script runs end-to-end: it generates synthetic load data, builds a forecasting pipeline, trains the model, and produces a forecast. Copy the entire block into a file (e.g. ``my_first_forecast.py``) and run it with ``python my_first_forecast.py``.

.. code-block:: python

   # SPDX-FileCopyrightText: 2025 Contributors to the OpenSTEF project
   # SPDX-License-Identifier: MPL-2.0

   from datetime import timedelta

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.preprocessing.lags import LagsAdder

   # ── 1. Load data ──────────────────────────────────────────────────────────────
   # create_synthetic_forecasting_dataset returns a TimeSeriesDataset with a
   # 'load' target column and optional weather features.
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=90),
       sample_interval=timedelta(hours=1),
   )

   # ── 2. Create the model ───────────────────────────────────────────────────────
   # ForecastingModel wires together preprocessing → forecaster → postprocessing.
   horizons = [timedelta(hours=h) for h in range(1, 25)]  # 1-hour to 24-hour ahead

   preprocessing = [
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           add_trivial_lags=True,
           target_column="load",
       )
   ]

   forecaster = ConstantMedianForecaster(
       horizons=horizons,
   )

   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=preprocessing,
       postprocessing=[],
       target_column="load",
       cutoff_history=timedelta(days=14),  # matches the longest lag above
   )

   # ── 3. Train ──────────────────────────────────────────────────────────────────
   prediction_train, prediction_val, prediction_test, fit_result = model.fit(
       data=dataset
   )
   print("Training complete.")
   print(f"  Train R²: {fit_result.metrics_train.r2:.3f}")

   # ── 4. Forecast ───────────────────────────────────────────────────────────────
   forecast = model.predict(data=dataset)

   # ── 5. Inspect output ─────────────────────────────────────────────────────────
   print(forecast.to_dataframe().head())

Expected output looks similar to:

.. code-block:: text

   Training complete.
     Train R²: 0.812
                              forecast
   timestamp
   2025-07-28 01:00:00+00:00   142.37
   2025-07-28 02:00:00+00:00   138.91
   2025-07-28 03:00:00+00:00   135.04
   2025-07-28 04:00:00+00:00   133.60
   2025-07-28 05:00:00+00:00   136.22

.. note::

   ``ConstantMedianForecaster`` is a simple baseline that predicts the historical
   median per horizon. It requires no external dependencies and is ideal for
   verifying your setup. Swap it for ``XGBoostForecaster`` or ``GBLinearForecaster``
   when you are ready to improve accuracy — see :doc:`first_forecast` for guidance.

Step-by-Step Breakdown
-----------------------

If the full script ran successfully, here is what each numbered section did.

**1 — Load data**
   ``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` with
   realistic load patterns. Replace this call with
   ``VersionedTimeSeriesDataset.from_dataframe(your_df, sample_interval)`` to use
   your own data.

**2 — Create the model**
   ``ForecastingModel`` is the central pipeline class. It accepts lists of
   preprocessing transforms, a forecaster, and postprocessing transforms.
   ``cutoff_history`` tells the model to skip the first 14 days of training rows
   where lag features are incomplete.

**3 — Train**
   ``model.fit()`` runs the full preprocessing pipeline, fits the forecaster, and
   returns in-sample predictions together with a ``ModelFitResult`` that contains
   train/validation/test metrics.

**4 — Forecast**
   ``model.predict()`` applies the same preprocessing pipeline to new data and
   returns a ``ForecastDataset``.

**5 — Inspect output**
   ``forecast.to_dataframe()`` converts the result to a standard pandas
   ``DataFrame`` indexed by timestamp.

Saving and Reloading a Model
-----------------------------

Use ``LocalModelStorage`` to persist a trained model to disk and reload it later:

.. code-block:: python

   from pathlib import Path
   from openstef_models.storage.local import LocalModelStorage

   storage = LocalModelStorage(path=Path("./models"))

   # Save after training
   storage.save(model=model, model_id="my_first_model")

   # Reload in a later session
   loaded_model = storage.load(model_id="my_first_model")
   forecast = loaded_model.predict(data=dataset)

Using Your Own Data
--------------------

Replace the synthetic dataset with a pandas ``DataFrame`` that has a
``DatetimeIndex`` and at least one target column:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   df = pd.read_csv("load_data.csv", index_col="timestamp", parse_dates=True)
   # df must have a DatetimeIndex and a column named 'load'

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data=df,
       sample_interval=timedelta(hours=1),
   )

The rest of the pipeline is identical to the complete example above.

.. note::

   Your ``DataFrame`` index must be timezone-aware (e.g. ``UTC``). Add a timezone
   with ``df.index = df.index.tz_localize("UTC")`` if it is not already set.

Troubleshooting
----------------

- **ImportError** — confirm the package is installed in the active environment:
  ``pip show openstef-models``.
- **Horizon mismatch error** — the ``horizons`` list passed to ``LagsAdder`` and
  to the forecaster must be identical.
- **NaN-heavy forecasts** — increase ``history_available`` in ``LagsAdder`` or
  reduce the lag window so there is enough history to fill all lag features.
- **Timezone errors** — ensure your ``DatetimeIndex`` is timezone-aware before
  wrapping it in a dataset.

Next Steps
----------

- :doc:`first_forecast` — the same workflow explained in depth, with weather
  features and a gradient-boosted model.
- :doc:`backtesting` — evaluate model quality on historical periods before
  deploying.
- :doc:`advanced_customization` — write custom transforms, forecasters, and
  postprocessing steps.