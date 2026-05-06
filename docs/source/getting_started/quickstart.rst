Quickstart
==========

Get a forecast running in under five minutes. This page is a single, copy-paste-ready example — no background theory, no deep dives. If you want explanations of what each step does, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

----

Prerequisites
-------------

OpenSTEF installed and importable:

.. code-block:: python

   import openstef_models
   import openstef_core

If either import fails, follow :doc:`installation` first.

----

The Complete Example
--------------------

Copy the block below and run it as-is. It generates synthetic load data, trains a gradient-boosted model, and produces a probabilistic 48-hour forecast.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.datasets.synthetic import create_synthetic_forecasting_dataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )

   # 1. Generate synthetic training data (9 months, hourly resolution)
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=30 * 9),
       sample_interval=timedelta(hours=1),
   )

   # 2. Configure the preset workflow
   config = ForecastingWorkflowConfig(
       model_id="my-first-forecast",
       model="lgbm",
       sample_interval=timedelta(hours=1),
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       location=LocationConfig(
           name="example-site",
           country_code="NL",
       ),
   )

   # 3. Create and fit the workflow
   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)

   # 4. Predict — reuse the same dataset as the prediction window
   forecast = workflow.predict(dataset)

   print(forecast)

.. note:: [VISUALIZATION: Example forecast output — a time-series plot showing the median forecast (Q 0.5) as a solid line with Q 0.1 and Q 0.9 as a shaded confidence band over a 48-hour horizon]

----

Step-by-Step Breakdown
-----------------------

Synthetic data
^^^^^^^^^^^^^^

``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` with a realistic load signal influenced by temperature, wind, and solar radiation. It is a drop-in stand-in for real meter data during development.

.. code-block:: python

   from openstef_core.datasets.synthetic import create_synthetic_forecasting_dataset
   from datetime import timedelta

   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=30 * 9),   # training window
       sample_interval=timedelta(hours=1),
       random_seed=42,                  # reproducible results
   )

Swap this out for your own ``TimeSeriesDataset`` when you are ready to use real data.

Workflow configuration
^^^^^^^^^^^^^^^^^^^^^^

``ForecastingWorkflowConfig`` is a Pydantic model — all fields are validated on construction. The minimum required fields are ``model_id`` and ``model``:

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets.forecasting_workflow import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_id="my-first-forecast",   # unique name for this model
       model="lgbm",                   # "xgboost", "lgbm", "gblinear", or "flatliner"
       sample_interval=timedelta(hours=1),
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

The ``quantiles`` list controls probabilistic output. Use ``[Q(0.5)]`` for a point forecast only.

Creating and fitting
^^^^^^^^^^^^^^^^^^^^

``create_forecasting_workflow`` returns a ``CustomForecastingWorkflow`` instance ready to call ``.fit()``:

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow

   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)

Predicting
^^^^^^^^^^

Pass a ``TimeSeriesDataset`` covering the period you want to forecast. The workflow uses the features in that dataset to produce predictions at every configured horizon:

.. code-block:: python

   forecast = workflow.predict(dataset)

``forecast`` is a ``TimeSeriesDataset`` containing one column per quantile.

----

Choosing a Model
----------------

Swap the ``model`` field to change the underlying algorithm. All options accept the same ``fit`` / ``predict`` interface:

- ``"lgbm"`` — LightGBM gradient boosting. Good default for hourly data.
- ``"xgboost"`` — XGBoost gradient boosting. Slightly slower to train, often comparable accuracy.
- ``"gblinear"`` — Linear booster inside XGBoost. Useful as a fast baseline.
- ``"flatliner"`` — Predicts a constant value. Use as a sanity-check baseline.
- ``"median"`` — Predicts the historical median. Another simple baseline.

----

What to Do Next
---------------

- **Understand the steps** — :doc:`first_forecast` walks through the same workflow with full explanations of each component.
- **Evaluate your model** — :doc:`backtesting` shows how to measure forecast accuracy on held-out historical data before going to production.
- **Customise the pipeline** — :doc:`advanced_customization` covers adding your own transforms, custom feature engineering, and alternative model configurations.

.. note::

   The synthetic dataset used here is designed for quick experimentation. For production use, replace it with real historical load and weather data loaded into a ``TimeSeriesDataset``. See :doc:`first_forecast` for guidance on data preparation.