Forecasting
===========

This guide covers the practical aspects of running the OpenSTEF forecasting pipeline: preparing your data, training models, and generating predictions. It walks through the complete lifecycle from raw time series data to forecast output.

For information on available model types, see :doc:`models`. For feature engineering details, see :doc:`feature_engineering`.

.. mermaid:: /diagrams/user_guide/guides/forecasting_diagram_1.mmd

Overview
--------

The OpenSTEF forecasting pipeline follows a two-phase pattern:

- **Fit phase**: Train a model on historical data, learning patterns and relationships
- **Predict phase**: Generate forecasts using the trained model on new input data

The core abstraction is the ``ForecastingModel``, which encapsulates the full pipeline: preprocessing → forecaster → postprocessing. A higher-level ``CustomForecastingWorkflow`` orchestrates training, evaluation, and persistence.


Data Requirements
-----------------

Input data format
^^^^^^^^^^^^^^^^^

OpenSTEF expects time series data as a pandas DataFrame wrapped in a ``VersionedTimeSeriesDataset`` or ``TimeSeriesDataset``. The DataFrame must have:

- A **DatetimeIndex** (timezone-aware, typically UTC)
- A **target column** (default: ``"load"``) containing the values to forecast
- Any additional feature columns (weather, calendar, etc.)

The ``ForecastInputDataset`` requires columns matching ``EnergyComponentType`` values when used for energy forecasting, plus ``horizon`` and ``available_at`` columns for temporal alignment.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta

   # Example: create a simple time series dataset
   index = pd.date_range("2024-01-01", periods=96*30, freq="15min", tz="UTC")
   data = pd.DataFrame({"load": range(len(index))}, index=index)

Sample interval
^^^^^^^^^^^^^^^

Datasets are configured with a ``sample_interval`` (default: 15 minutes). This must match the resolution of your input data:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import ForecastDataset

   # For 15-minute resolution data
   dataset = VersionedTimeSeriesDataset(data=data, sample_interval=timedelta(minutes=15))


Building a Forecasting Model
-----------------------------

A ``ForecastingModel`` combines preprocessing, a forecaster, and postprocessing into a single pipeline:

.. code-block:: python

   from openstef_core.models import ForecastingModel

   model = ForecastingModel(
       forecaster=my_forecaster,
       feature_pipeline=my_feature_pipeline,
       target_column="load",
   )

The model exposes key properties:

- ``model.quantiles`` — the quantile levels produced by the forecaster
- ``model.max_horizon`` — maximum lead time the model can predict
- ``model.is_fitted`` — whether the model has been trained


Training (Fit)
--------------

Call ``fit()`` on the model or workflow with your training dataset. The method returns a ``ModelFitResult`` containing evaluation metrics:

.. code-block:: python

   result = model.fit(data=training_dataset)

   # Inspect training metrics
   if result is not None:
       print(result.metrics_full.to_dataframe())
       if result.metrics_test is not None:
           print(result.metrics_test.to_dataframe())

You can optionally provide validation and test splits:

.. code-block:: python

   result = model.fit(
       data=training_dataset,
       data_val=validation_dataset,
       data_test=test_dataset,
   )


Generating Predictions
----------------------

Once trained, call ``predict()`` to generate forecasts:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   forecast: ForecastDataset = model.predict(data=input_dataset)

   # Access the median forecast
   print(forecast.median_series)

   # Access quantile forecasts
   print(forecast.quantiles_data)

   # View raw forecast DataFrame
   print(forecast.data.tail())

You can specify a ``forecast_start`` to control the prediction origin:

.. code-block:: python

   from datetime import datetime

   forecast = model.predict(
       data=input_dataset,
       forecast_start=datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc),
   )


Complete Workflow Example
-------------------------

The recommended pattern uses ``CustomForecastingWorkflow`` to handle model persistence and orchestration:

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   from openstef_core.datasets import ForecastDataset
   from openstef_core.models import ForecastingModel
   from openstef_core.workflows import CustomForecastingWorkflow
   from openstef_core.storage import MLFlowStorage, MLFlowStorageCallback

   logger = logging.getLogger(__name__)
   workspace_dir = Path("./workspace")

   # Configure the workflow with model storage
   workflow = CustomForecastingWorkflow(
       model_id="my_forecaster_v1",
       model=model,
       callbacks=[
           MLFlowStorageCallback(
               storage=MLFlowStorage(
                   tracking_uri=str(workspace_dir / "mlflow_tracking"),
                   local_artifacts_path=workspace_dir / "mlflow_tracking_artifacts",
               ),
               model_reuse_enable=False,
           )
       ],
   )

   # Train
   logger.info("Starting model training")
   result = workflow.fit(dataset)

   # Predict
   logger.info("Starting forecasting")
   forecast: ForecastDataset = workflow.predict(dataset)
   print(forecast.data.tail())

.. note:: [VISUALIZATION: Time series plot showing historical measurements overlaid with forecast median and quantile bands]

To visualize results:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=dataset.select_version().data["load"])
       .add_model(
           model_name="my_model",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot()
   )
   fig.write_html("forecast_plot.html")


Model Scoring
-------------

Evaluate a trained model on a dataset without retraining:

.. code-block:: python

   metrics = model.score(data=evaluation_dataset)
   print(metrics)


Feature Contributions
---------------------

For explainability, compute per-sample feature contributions:

.. code-block:: python

   contributions = model.predict_contributions(data=input_dataset)
   print(contributions.data.head())

This returns a ``TimeSeriesDataset`` where each column represents the contribution of a feature to the prediction.


Input Preparation
-----------------

The ``prepare_input()`` method applies preprocessing and filtering to produce a ``ForecastInputDataset`` ready for the forecaster:

.. code-block:: python

   from datetime import datetime, timezone

   prepared = model.prepare_input(
       data=input_dataset,
       forecast_start=datetime(2024, 6, 1, tzinfo=timezone.utc),
   )

This is useful for debugging or inspecting what the model sees after feature engineering.


Key Considerations
------------------

- **Time zones**: Always use timezone-aware DatetimeIndex (UTC recommended). The ``available_at`` and ``horizon`` columns in ``ForecastInputDataset`` handle temporal alignment.
- **Missing data**: Ensure your input data has no large gaps. The feature pipeline expects continuous time series at the configured sample interval.
- **Model persistence**: Use ``MLFlowStorageCallback`` or ``LocalModelStorage`` to save and reload trained models between sessions.
- **Retraining**: Periodically retrain models as new data becomes available to maintain forecast accuracy.

.. seealso::

   - :doc:`feature_engineering` — configuring the feature pipeline (holidays, lags, scaling)
   - :doc:`models` — available forecaster types and hyperparameters
   - :doc:`evaluation` — detailed metrics and backtesting