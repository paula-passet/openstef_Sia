Quickstart
==========

This page shows the fastest path to your first forecast. Copy, paste, and run—no explanations, just working code.

.. mermaid::

   graph LR
       A([Synthetic Data]) --> B[Create Model]
       B --> C[Train Model]
       C --> D[Run Prediction]
       D --> E([Forecast Output])
       classDef primary fill:#00D9C5,stroke:#1E3A5F,stroke-width:2px,color:#000
       classDef secondary fill:#1E3A5F,stroke:#00D9C5,stroke-width:2px,color:#fff
       classDef accent fill:#e6f7f5,stroke:#00D9C5,stroke-width:2px,color:#000
       class B,C,D primary
       class A,E accent

For detailed explanations of each step, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

Minimal Working Example
------------------------

This example creates synthetic data, trains a model, and generates a forecast in under 20 lines of code:

.. code-block:: python

   from datetime import timedelta
   from openstef.data.test_utils import create_synthetic_forecasting_dataset
   from openstef.model.forecasting import ForecastingModel
   from openstef.model.forecaster import ConstantMedianForecaster
   from openstef.workflow.forecasting import CustomForecastingWorkflow
   from openstef.types import LeadTime, Q

   # Create synthetic data (9 months of hourly data)
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1)
   )

   # Configure model
   horizons = [LeadTime.from_string("PT24H")]
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)]
       )
   )

   # Create workflow
   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart")

   # Train and predict
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)

   # View results
   print(forecast.data.tail())

The output shows a DataFrame with three quantiles (10th, 50th, 90th percentile) for the next 24 hours:

.. code-block:: text

                            q0.10      q0.50      q0.90
   2025-09-26 00:00:00+00:00  45.23     52.14     58.92
   2025-09-26 01:00:00+00:00  43.87     51.03     57.45
   2025-09-26 02:00:00+00:00  42.15     49.78     56.21
   ...

What Just Happened?
-------------------

The code above:

1. **Generated synthetic data** with realistic patterns (temperature, wind, load)
2. **Created a forecasting model** with a simple baseline forecaster
3. **Trained the model** on historical data
4. **Generated predictions** for the next 24 hours with uncertainty quantiles

Visualizing Results
-------------------

OpenSTEF includes built-in plotting utilities. Add this to the example above:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   # Create interactive plot
   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=dataset.data["load"])
       .add_model(
           model_name="quickstart",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data
       )
       .plot()
   )

   # Save to HTML file
   fig.write_html("forecast_plot.html")

Open ``forecast_plot.html`` in your browser to see an interactive plot with historical data, forecast median, and uncertainty bands.

Using Your Own Data
-------------------

Replace the synthetic data with your own time series:

.. code-block:: python

   import pandas as pd
   from openstef.data.dataset import TimeSeriesDataset

   # Load your data (must have DatetimeIndex)
   df = pd.read_csv("your_data.csv", index_col=0, parse_dates=True)

   # Required columns: 'load' (target) and optional features
   # Example: df has columns ['load', 'temperature', 'windspeed']

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1)  # Match your data frequency
   )

   # Use same workflow as above
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)

Your data must have:

- A ``DatetimeIndex`` with timezone information
- A ``load`` column (the target variable)
- Optional: weather features like ``temperature``, ``windspeed``, ``radiation``

Saving and Loading Models
--------------------------

Persist trained models to disk:

.. code-block:: python

   from openstef.model.storage import LocalModelStorage

   # Configure storage
   storage = LocalModelStorage(base_path="./models")

   # Create workflow with storage
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="quickstart",
       storage=storage
   )

   # Train and save automatically
   workflow.fit(dataset)

   # Load later
   loaded_workflow = CustomForecastingWorkflow.from_storage(
       model_id="quickstart",
       storage=storage
   )
   forecast = loaded_workflow.predict(dataset)

Next Steps
----------

This quickstart used a simple baseline model. For production forecasting:

- **Learn the concepts**: Read :doc:`first_forecast` for detailed explanations
- **Try better models**: Use ``XGBForecaster`` or ``LGBMForecaster`` instead of ``ConstantMedianForecaster``
- **Evaluate performance**: See :doc:`backtesting` to compare models
- **Customize pipelines**: Check :doc:`advanced_customization` for feature engineering

The workflow pattern shown here scales to complex production systems—just swap the forecaster and add preprocessing steps.
