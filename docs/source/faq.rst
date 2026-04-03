Frequently Asked Questions
==========================

This page answers common questions from new users getting started with OpenSTEF. Whether you're evaluating the library for your project or working through your first implementation, you'll find practical answers to help you understand what OpenSTEF does and how to use it effectively.

General Questions
-----------------

What is OpenSTEF?
^^^^^^^^^^^^^^^^^

OpenSTEF is a Python library for creating short-term energy forecasts. It provides machine learning models and tools specifically designed for forecasting energy loads, solar generation, wind power, and other energy-related time series over horizons ranging from 15 minutes to several days ahead.

As a library, OpenSTEF gives you the building blocks to integrate forecasting capabilities into your own applications and workflows. It's not a standalone application—you write Python code that uses OpenSTEF's models, pipelines, and utilities to solve your specific forecasting problems.

What is short-term forecasting?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Short-term forecasting predicts energy values from 15 minutes to approximately 48 hours ahead. This differs from:

- **Ultra-short-term forecasting**: Seconds to minutes ahead (not OpenSTEF's focus)
- **Medium-term forecasting**: Days to weeks ahead
- **Long-term forecasting**: Months to years ahead

Short-term forecasts are critical for operational decisions in the energy sector, including:

- Grid balancing and congestion management
- Trading on day-ahead and intraday markets
- Scheduling maintenance and resource allocation
- Managing distributed energy resources

OpenSTEF automates the machine learning workflow for these forecasting tasks, handling feature engineering, model training, and probabilistic prediction generation.

What makes OpenSTEF special?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF was built by grid operators for real-world energy forecasting. Several features distinguish it from generic forecasting libraries:

**Probabilistic forecasting by default**: OpenSTEF predicts multiple quantiles (e.g., 10th, 50th, 90th percentiles) rather than just point forecasts. This quantifies uncertainty, which is essential for risk management and decision-making in energy systems.

**Energy-specific feature engineering**: The library includes built-in transformations for weather data, calendar effects (holidays, weekends), and temporal patterns common in energy time series. You don't need to manually engineer these features.

**Multi-horizon forecasting**: OpenSTEF models can predict multiple forecast horizons simultaneously (e.g., 15 minutes, 1 hour, 6 hours ahead) in a single training run, capturing how forecast accuracy degrades over time.

**Production-ready workflows**: The library handles practical concerns like missing data, model versioning, evaluation metrics, and backtesting—not just model training and prediction.

**Battle-tested**: OpenSTEF has been used in production by multiple European grid operators, processing thousands of forecasts daily.

Installation and Setup
----------------------

What are the system requirements?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 requires:

- Python 3.12 or higher (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, or Linux)
- Standard scientific Python stack (NumPy, pandas, scikit-learn)

.. note::
   If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead. Version 4.0 requires Python 3.12+ for modern type safety features and performance improvements.

How do I install OpenSTEF?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 uses a modular architecture. For most users, start with:

.. code-block:: bash

   pip install openstef

This installs the core functionality including models. For the complete toolkit with evaluation tools:

.. code-block:: bash

   pip install "openstef[all]"

You can also install individual packages:

.. code-block:: bash

   pip install openstef-models    # Core forecasting models only
   pip install openstef-beam      # Backtesting and evaluation tools
   pip install openstef-core      # Core utilities and datasets

The modular design lets you install only what you need, keeping dependencies minimal for production deployments.

Do I need special hardware?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No. OpenSTEF runs on standard hardware—laptops, servers, or cloud instances. The XGBoost and LightGBM models it uses are computationally efficient and don't require GPUs.

For production systems forecasting hundreds or thousands of time series, you'll want adequate CPU cores and memory, but nothing exotic. A typical server with 8-16 cores and 32GB RAM can handle substantial workloads.

Models and Algorithms
---------------------

What models does OpenSTEF provide?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes several forecasting models:

**XGBoostForecaster**: Gradient boosted decision trees using XGBoost. This is the most commonly used model and provides excellent accuracy for most energy forecasting tasks. It handles non-linear relationships and interactions between features automatically.

**GBLinearForecaster**: Linear model using XGBoost's gblinear booster. Faster and more interpretable than tree-based models, suitable when relationships are approximately linear.

**LGBMForecaster**: Gradient boosted trees using LightGBM. Similar to XGBoost but can be faster on large datasets.

**FlatlinerForecaster**: Simple baseline that predicts constant values. Useful for testing and as a performance baseline.

**ConstantMedianForecaster**: Predicts historical quantile values plus an optional constant offset. Another baseline model.

All models implement the same interface, making it easy to experiment with different algorithms.

Why does OpenSTEF use XGBoost?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XGBoost (and similar gradient boosting methods) excel at energy forecasting because they:

- Handle mixed data types (continuous weather variables, categorical calendar features)
- Capture non-linear relationships and complex interactions automatically
- Provide feature importance metrics for interpretability
- Train efficiently on typical energy forecasting datasets (thousands to millions of samples)
- Support custom loss functions for quantile regression

OpenSTEF extends XGBoost with custom quantile loss functions optimized for probabilistic forecasting, allowing the model to predict multiple quantiles simultaneously.

Can I use my own models?
^^^^^^^^^^^^^^^^^^^^^^^^^

Yes. OpenSTEF's architecture is extensible. You can implement custom forecasters by inheriting from the ``Forecaster`` base class and implementing the required methods:

.. code-block:: python

   from openstef_models.models.forecasting.forecaster import Forecaster
   from openstef_core.types import Quantile
   import pandas as pd

   class MyCustomForecaster(Forecaster):
       def __init__(self, quantiles=None, **kwargs):
           super().__init__(
               quantiles=quantiles or [Quantile(0.5)],
               **kwargs
           )
           # Initialize your model
           
       def fit(self, data):
           # Train your model
           pass
           
       def predict(self, data):
           # Generate forecasts
           pass

Your custom forecaster will work with OpenSTEF's pipelines, evaluation tools, and workflows.

Working with OpenSTEF
---------------------

What does a typical workflow look like?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A basic OpenSTEF workflow involves:

1. **Prepare data**: Load your time series into a ``VersionedTimeSeriesDataset``
2. **Configure model**: Set up a ``ForecastingModel`` with preprocessing and a forecaster
3. **Train**: Call ``workflow.fit(dataset)`` to train the model
4. **Predict**: Call ``workflow.predict(dataset)`` to generate forecasts
5. **Evaluate**: Use metrics and plots to assess performance

Here's a minimal example:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_core.types import Quantile
   
   # Prepare data (assuming you have a DataFrame with datetime index)
   dataset = VersionedTimeSeriesDataset(
       data=your_dataframe,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )
   
   # Configure model
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       max_horizon=timedelta(hours=24)
   )
   
   model = ForecastingModel(forecaster=forecaster)
   
   # Create workflow
   workflow = CustomForecastingWorkflow(model=model)
   
   # Train and predict
   result = workflow.fit(dataset)
   forecast = workflow.predict(dataset)
   
   print(forecast.data)

What data do I need?
^^^^^^^^^^^^^^^^^^^^

At minimum, you need:

- **Historical time series**: The values you want to forecast (load, generation, etc.)
- **Timestamps**: Regular intervals (e.g., 15-minute or hourly data)
- **Sufficient history**: At least several weeks, preferably months or years

OpenSTEF works better with additional features:

- **Weather data**: Temperature, wind speed, solar irradiance, etc.
- **Calendar information**: Automatically generated from timestamps
- **Exogenous variables**: Anything that might influence your target (prices, events, etc.)

The library handles missing data gracefully, but more complete data yields better forecasts.

How do I handle missing data?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes built-in handling for missing data:

- **During training**: Missing values in features are handled by the underlying ML algorithms (XGBoost and LightGBM support missing values natively)
- **During prediction**: If critical data is missing, the forecaster can return ``None`` to indicate prediction isn't possible
- **Preprocessing**: You can add custom imputation steps to your feature pipeline

For target values (what you're forecasting), you should clean or interpolate missing data before training, as gaps in the target can degrade model quality.

How accurate are the forecasts?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forecast accuracy depends on:

- **Data quality**: More complete, accurate historical data improves forecasts
- **Predictability**: Some time series are inherently more predictable than others
- **Forecast horizon**: Accuracy typically decreases with longer horizons
- **Feature availability**: Weather forecasts and other predictive features help

In production use by grid operators, OpenSTEF typically achieves:

- **15-minute ahead**: 2-5% normalized mean absolute error (nMAE)
- **1-hour ahead**: 3-7% nMAE
- **24-hours ahead**: 5-15% nMAE

These are rough guidelines—your results will vary based on your specific use case.

Troubleshooting
---------------

I get an import error. What's wrong?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 uses new package names. Make sure you're importing from the correct packages:

.. code-block:: python

   # Correct imports for v4
   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_beam.evaluation import metrics
   
   # Not: from openstef.models import ...

If you see ``ModuleNotFoundError``, verify you've installed the package containing that module:

.. code-block:: bash

   pip install openstef-models  # For forecasting models
   pip install openstef-beam    # For evaluation tools
   pip install openstef-core    # For core utilities

My model training is slow. How can I speed it up?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Several options:

- **Reduce data size**: Use a subset of historical data for initial experiments
- **Limit hyperparameter search**: Reduce the number of hyperparameter combinations tried
- **Use fewer quantiles**: Train with fewer quantiles (e.g., just [0.1, 0.5, 0.9])
- **Adjust model parameters**: Reduce ``n_estimators`` or ``max_depth`` in tree-based models
- **Use GBLinearForecaster**: Linear models train faster than tree-based models

For production systems, consider parallelizing training across multiple time series using appropriate workflow orchestration.

Where can I find more examples?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The OpenSTEF repository includes example scripts in the ``examples/`` directory showing:

- Basic forecasting workflows
- Feature engineering and preprocessing
- Model configuration and hyperparameter tuning
- Evaluation and visualization
- Integration with storage backends

Check the tutorials and API documentation for detailed guidance on specific topics.

Getting Help
------------

If your question isn't answered here:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for similar questions
2. Review the tutorials and user guide for detailed examples
3. Visit the project documentation at the `LF Energy OpenSTEF page <https://www.lfenergy.org/projects/openstef/>`_
4. Contact the community at openstef@lfenergy.org

OpenSTEF is an open-source project under LF Energy. Contributions, bug reports, and questions are welcome.