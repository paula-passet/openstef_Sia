Forecasting
===========

This guide covers the complete forecasting lifecycle in OpenSTEF: from preparing input data through training a model to generating predictions. You will learn how to configure a forecasting workflow, understand data requirements, and run both the fit and predict steps.

.. mermaid:: /diagrams/user_guide/guides/forecasting_diagram_1.mmd

Overview
--------

OpenSTEF's forecasting pipeline is built around the concept of a **workflow** that orchestrates preprocessing, model training, and prediction. The key components are:

- **ForecastingWorkflowConfig** — a configuration object that defines the entire pipeline
- **CustomForecastingWorkflow** — the orchestrator that ties preprocessing, model, and postprocessing together
- **ForecastingModel** — the trained model that exposes ``fit`` and ``predict`` methods
- **TimeSeriesDataset** — the standard data container (see :doc:`datasets` for details)

Data Requirements
-----------------

Input data must be provided as a ``TimeSeriesDataset`` with a DatetimeIndex. The minimum requirements are:

- A **target column** containing the values to forecast (e.g., load in MW)
- A **consistent time frequency** (e.g., 15-minute intervals)
- **Sufficient history** for lag feature computation (typically at least 7 days)
- Timestamps should be timezone-aware (UTC recommended)

Additional feature columns (weather forecasts, calendar features) improve accuracy but are not strictly required — the pipeline can generate many features automatically.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   # Load your data with a DatetimeIndex
   df = pd.read_csv("load_data.csv", parse_dates=["datetime"], index_col="datetime")
   df.index = df.index.tz_localize("UTC")

   dataset = TimeSeriesDataset(df, frequency=pd.Timedelta("15min"))

For forecasting-specific validation (target column checks, forecast start detection), wrap your data in a ``ForecastInputDataset``:

.. code-block:: python

   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   forecast_dataset = ForecastInputDataset.from_timeseries(
       dataset, target_column="load"
   )

See :doc:`datasets` for more on dataset creation and manipulation.

Configuring the Pipeline
------------------------

The ``ForecastingWorkflowConfig`` centralizes all pipeline settings: model type, horizons, feature engineering options, and data quality thresholds.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )

   config = ForecastingWorkflowConfig(
       target_column="load",
       model="xgboost",
       horizons=[timedelta(hours=h) for h in [1, 6, 12, 24, 48]],
       predict_history=timedelta(days=14),
       completeness_threshold=0.8,
       flatliner_threshold=24,
       detect_non_zero_flatliner=True,
       max_day_lags=14,
   )

Key configuration options:

- ``model`` — the forecasting algorithm (``"xgboost"``, ``"gblinear"``, ``"stacking"``, ``"learned_weights"``)
- ``horizons`` — list of lead times to forecast
- ``predict_history`` — how much historical data is needed at prediction time
- ``completeness_threshold`` — minimum fraction of non-missing values required
- ``flatliner_threshold`` — number of consecutive identical values that triggers a data quality warning
- ``max_day_lags`` — maximum number of daily lags to generate as features

Data Validation
---------------

Before training, the pipeline automatically applies a series of data quality checks:

1. **InputConsistencyChecker** — verifies column types and index structure
2. **FlatlineChecker** — detects periods where the target is suspiciously constant
3. **CompletenessChecker** — ensures enough data points are present

These checks raise errors for critical issues and log warnings for minor ones. You can adjust sensitivity through the configuration thresholds shown above.

Feature Engineering
-------------------

The pipeline automatically generates features based on your configuration. Key feature types include:

- **Lag features** — historical values at various offsets (e.g., same hour yesterday, same hour last week)
- **Wind power features** — derived from wind speed/direction columns
- **Holiday features** — country-specific calendar information

For ``"gblinear"`` and ``"stacking"`` models, only 7-day lags are used. For tree-based models like ``"xgboost"``, a richer set of lags is generated automatically.

See :doc:`feature_engineering` for a detailed guide on available features and customization.

Training (Fit)
--------------

Create the workflow and call ``fit`` on your training data:

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow

   # Build the workflow from config
   workflow = create_forecasting_workflow(config)

   # Train the model
   fit_result = workflow.model.fit(training_dataset)

The ``fit`` method returns a ``ModelFitResult`` containing training metrics and metadata. The trained model is stored within the workflow and can be persisted using model storage.

Model Persistence
-----------------

Use ``LocalModelStorage`` to save and reload trained models:

.. code-block:: python

   from pathlib import Path
   from openstef_models.storage import LocalModelStorage

   storage = LocalModelStorage(Path("./models"))

   # Save after training
   storage.save(workflow.model, model_id="my_load_forecast")

   # Load for prediction
   loaded_model = storage.load(model_id="my_load_forecast")

Prediction
----------

To generate forecasts, provide a dataset covering the required history window:

.. code-block:: python

   from datetime import datetime

   # Prepare input data up to the forecast start
   forecast_start = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)

   # Run prediction
   predictions = workflow.model.predict(
       prediction_dataset,
       forecast_start=forecast_start,
   )

The output is a ``TimeSeriesDataset`` containing forecasted values at each configured horizon.

Feature Contributions
^^^^^^^^^^^^^^^^^^^^^

To understand which features drive a particular forecast, use ``predict_contributions``:

.. code-block:: python

   contributions = workflow.model.predict_contributions(
       prediction_dataset,
       forecast_start=forecast_start,
   )

This returns a dataset where each column represents the contribution of that feature to the final prediction — useful for explainability and debugging.

Complete Example
----------------

Putting it all together:

.. code-block:: python

   from datetime import timedelta, datetime, timezone
   from pathlib import Path

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )

   # 1. Load and prepare data
   df = pd.read_csv("load_data.csv", parse_dates=["datetime"], index_col="datetime")
   df.index = df.index.tz_localize("UTC")
   dataset = TimeSeriesDataset(df, frequency=pd.Timedelta("15min"))

   # 2. Configure the pipeline
   config = ForecastingWorkflowConfig(
       target_column="load",
       model="xgboost",
       horizons=[timedelta(hours=1), timedelta(hours=24), timedelta(hours=48)],
       predict_history=timedelta(days=14),
       completeness_threshold=0.8,
       flatliner_threshold=24,
       max_day_lags=14,
   )

   # 3. Create workflow and train
   workflow = create_forecasting_workflow(config)
   fit_result = workflow.model.fit(dataset)

   # 4. Generate predictions
   forecast_start = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
   predictions = workflow.model.predict(dataset, forecast_start=forecast_start)

.. note:: [VISUALIZATION: Time series plot showing historical load data, the forecast start point, and predicted values at multiple horizons with confidence intervals]

Tips and Best Practices
-----------------------

- **Always use timezone-aware timestamps.** UTC is recommended to avoid daylight saving time ambiguities.
- **Provide more history than the minimum.** While ``predict_history`` defines the minimum, more data improves lag feature quality.
- **Monitor data quality metrics.** The validation checks catch common issues, but reviewing completeness and flatline reports helps identify upstream data problems early.
- **Start with default features.** The automatic lag and calendar features provide a strong baseline. Add custom features only after establishing this baseline.
- **Use appropriate horizons.** More horizons increase computation time. Choose horizons that match your operational decision points.

.. warning::

   If your input data has gaps larger than the configured frequency, the completeness checker will reject the dataset. Ensure your data pipeline fills or interpolates small gaps before passing data to OpenSTEF.

Next Steps
----------

- :doc:`feature_engineering` — customize and extend the feature pipeline
- :doc:`datasets` — learn about ``TimeSeriesDataset`` creation and manipulation