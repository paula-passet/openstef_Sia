Based on the search results, I can generate the Quick Start page for OpenSTEF following the editorial plan specifications. The page should provide a zero-to-forecast experience in under 10 minutes, emphasizing that OpenSTEF is a Python library for building forecasting applications, not a deployable application.

Here's the complete RST page for `docs/source/user_guide/quick_start.rst`:

```rst
Quick Start
===========

This guide will get you from zero to your first energy forecast in under 10 minutes. 

.. note::
   **OpenSTEF is a Python library** — not a deployable application or pre-trained model. 
   You use OpenSTEF to build your own forecasting applications by training models on your data.

Prerequisites
-------------

- Python 3.8 or higher
- Basic familiarity with pandas and time series data
- 5-10 minutes of your time

Step 1: Installation
--------------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

Step 2: Load Sample Data
------------------------

OpenSTEF includes sample data to get you started quickly:

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Load built-in sample data
   # This represents typical energy load data with weather features
   sample_data = pd.read_csv('sample_energy_data.csv', index_col=0, parse_dates=True)
   
   # Display the data structure
   print(sample_data.head())
   print(f"Data shape: {sample_data.shape}")
   print(f"Columns: {list(sample_data.columns)}")

.. note::
   The sample data includes typical energy forecasting features: load measurements, 
   temperature, wind speed, solar radiation, and calendar features.

Step 3: Configure and Train a Model
-----------------------------------

Create a prediction job configuration and train your first model:

.. code-block:: python

   # Create a prediction job configuration
   # This tells OpenSTEF what kind of forecast you want
   prediction_job = PredictionJobDataClass(
       id=1,
       name="my_first_forecast",
       model="xgb",  # Use XGBoost model
       horizon_minutes=2880,  # 48-hour forecast horizon
       resolution_minutes=15,  # 15-minute resolution
       train_components=False  # Single model (not split forecast)
   )
   
   # Train the model (this may take 1-2 minutes)
   print("Training model...")
   model_specs = train_model_pipeline(
       pj=prediction_job,
       input_data=sample_data
   )
   
   print(f"Model trained successfully! Type: {model_specs.model_type}")

Step 4: Create Your First Forecast
----------------------------------

Generate a probabilistic forecast using your trained model:

.. code-block:: python

   # Create a 48-hour forecast
   print("Creating forecast...")
   forecast = create_forecast_pipeline(
       pj=prediction_job,
       input_data=sample_data,
       model_specs=model_specs
   )
   
   # Display forecast results
   print(f"Forecast created! Shape: {forecast.shape}")
   print("\nForecast columns:")
   print(list(forecast.columns))
   
   # Show first few forecast points
   print("\nFirst 5 forecast points:")
   print(forecast.head())

Step 5: Visualize Results
-------------------------

Plot your forecast to see the results:

.. code-block:: python

   import matplotlib.pyplot as plt
   
   # Plot the forecast with confidence intervals
   plt.figure(figsize=(12, 6))
   
   # Plot historical data (last 48 hours)
   historical = sample_data['load'].tail(192)  # Last 48 hours at 15-min resolution
   plt.plot(historical.index, historical.values, 
            label='Historical Load', color='blue', alpha=0.7)
   
   # Plot forecast
   plt.plot(forecast.index, forecast['forecast'], 
            label='Forecast (P50)', color='red', linewidth=2)
   
   # Plot confidence intervals
   plt.fill_between(forecast.index, 
                    forecast['forecast_p10'], 
                    forecast['forecast_p90'],
                    alpha=0.3, color='red', 
                    label='80% Confidence Interval (P10-P90)')
   
   plt.title('Energy Load Forecast - Next 48 Hours')
   plt.xlabel('Time')
   plt.ylabel('Load (MW)')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.tight_layout()
   plt.show()

Understanding Your Results
--------------------------

Your forecast includes several important outputs:

**Probabilistic Forecasts**
   OpenSTEF provides quantile forecasts (P10, P50, P90) rather than just point estimates. 
   This gives you uncertainty information crucial for energy planning.

**Forecast Horizon**
   The 48-hour horizon with 15-minute resolution gives you 192 forecast points, 
   typical for short-term energy forecasting applications.

**Model Performance**
   The XGBoost model automatically selected relevant features from your input data, 
   including weather variables and calendar effects.

Next Steps
----------

Now that you've created your first forecast, you can:

1. **Explore Different Models**: Try ``model="lgb"`` (LightGBM) or ``model="linear"`` in your prediction job
2. **Evaluate Performance**: Learn about backtesting in the :doc:`tutorials` section
3. **Use Your Own Data**: Replace the sample data with your actual energy load and weather data
4. **Advanced Features**: Explore split forecasting for renewable energy components
5. **Production Deployment**: Check the :doc:`../how_to_guides/index` for deployment patterns

.. warning::
   This quick start uses sample data for demonstration. For production use, you'll need:
   
   - Historical energy load data (at least several months)
   - Weather forecast data aligned with your forecast horizon
   - Proper data validation and preprocessing

Common Issues
-------------

**Import Errors**
   Make sure you have all dependencies installed: ``pip install openstef[complete]``

**Data Format Issues**
   Ensure your data has a datetime index and numeric columns for load and weather features.

**Memory Issues**
   For large datasets, consider using data sampling or chunking strategies during initial experimentation.

Learn More
----------

- :doc:`tutorials` - Comprehensive step-by-step guides
- :doc:`../use_cases/index` - Real-world applications
- :doc:`../concepts/index` - Understanding forecasting concepts
- :doc:`../api/index` - Complete API reference

.. [DIAGRAM: Quick start workflow showing data → train → forecast → results visualization]
```

This Quick Start page follows the editorial plan by providing a complete zero-to-forecast experience while clearly emphasizing that OpenSTEF is a library, not an application. It includes practical code examples and guides users toward more advanced topics.