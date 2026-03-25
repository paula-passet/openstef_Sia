Quick Start Guide
=================


Installation
------------


.. code-block:: bash

   pip install openstef

   python -c "import openstef; print(f'OpenSTEF version: {openstef.__version__}')"


Load Sample Data
----------------


OpenSTEF is a forecasting library that requires input data to generate predictions. To help you get started quickly, we provide sample datasets that demonstrate the expected data format and structure. These sample datasets include forecast input data suitable for training and prediction workflows.


.. code-block:: python

   from openstef.data_classes.model_specifications import ForecastInputDataset
   from openstef.tests.unit.models.conftest import sample_forecast_input_dataset

   # Load sample dataset with energy consumption and weather features
   dataset = sample_forecast_input_dataset()

   # Display basic information about the dataset
   print(f"Dataset shape: {dataset.data.shape}")
   print(f"Features: {list(dataset.data.columns)}")
   print(f"Date range: {dataset.data.index.min()} to {dataset.data.index.max()}")

   # Show first few rows
   print(dataset.data.head())


Train Model and Create Forecast
-------------------------------


.. code-block:: python

   from openstef.model.forecasting_model import XGBQuantileOpenstfRegressor
   from openstef.data_classes.time_series_dataset import TimeSeriesDataset

   # Load your training data
   train_data = TimeSeriesDataset.from_dataframe(df_train)

   # Create and train model
   model = XGBQuantileOpenstfRegressor()
   fit_result = model.fit(train_data)

   # Make forecast
   forecast = model.predict(test_data)
   print(f"Forecast shape: {forecast.shape}")


Visualize Results
-----------------


.. code-block:: python

   import matplotlib.pyplot as plt
   import pandas as pd

   # Assuming you have forecast results from OpenSTEF
   # actual_values and predicted_values are pandas Series with datetime index

   plt.figure(figsize=(12, 6))
   plt.plot(actual_values.index, actual_values.values, label='Actual', color='blue', linewidth=2)
   plt.plot(predicted_values.index, predicted_values.values, label='Predicted', color='red', linewidth=2, linestyle='--')
   plt.xlabel('Time')
   plt.ylabel('Load (MW)')
   plt.title('OpenSTEF Forecast Results: Actual vs Predicted')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.xticks(rotation=45)
   plt.tight_layout()
   plt.show()


.. image:: _static/images/placeholder_example_forecast_plot_showing_time_series_with_confidence_intervals.png
   :alt: Example forecast plot showing time series with confidence intervals
   :align: center


Next Steps
----------


- Explore the Data Preparation Guide for input data formatting and validation

- Review Model Training Tutorials for custom forecasting workflows

- Check Advanced Configuration for hyperparameter tuning and optimization

- Visit the API Reference for detailed function documentation

- See Use Cases and Examples for real-world implementation scenarios

- Learn about Model Evaluation and Validation techniques

- Discover Integration Patterns for embedding OpenSTEF in your systems


