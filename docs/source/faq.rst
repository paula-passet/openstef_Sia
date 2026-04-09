FAQ
===

This FAQ addresses common questions from new users about OpenSTEF, covering installation, core concepts, model choices, and getting started with the library.

General Questions
-----------------

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term energy forecasts. Short-term forecasting means predicting load hours to days ahead.
   
   OpenSTEF is not just a model—it's a complete machine learning framework providing pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. The library is model-agnostic and includes domain-specific knowledge for energy forecasting built into its feature engineering components.

.. dropdown:: What makes OpenSTEF different from other forecasting libraries?
   :icon: light-bulb

   OpenSTEF is specifically designed for energy forecasting with several unique features:
   
   - **Probabilistic forecasts**: Generates multiple quantile forecasts with uncertainty bandwidths, not just single-point predictions
   - **Domain knowledge included**: Built-in feature engineering specific to energy (e.g., solar radiation to PV generation estimates, holiday effects, weather features)
   - **Production-ready**: Developed and used by Alliander for real-world congestion management on the Dutch electricity grid
   - **Model-agnostic**: Works with different machine learning algorithms (XGBoost, LightGBM, linear models, etc.)
   - **Complete pipelines**: Handles the entire workflow from raw data to actionable forecasts

.. dropdown:: What is short-term forecasting and why is it important?
   :icon: info

   Short-term forecasting predicts energy load hours to days ahead (typically 1-48 hours). This is critical for:
   
   - **Congestion management**: Identifying when grid equipment will exceed capacity limits
   - **Grid operations**: Enabling utilities to connect new customers despite capacity constraints
   - **Proactive interventions**: Calling customers in advance to reduce consumption during peak moments
   - **EV charging capacity**: Estimating available capacity for electric vehicle charging
   - **Grid loss prediction**: Forecasting transmission and distribution losses
   
   Unlike long-term forecasting (months/years ahead for infrastructure planning), short-term forecasting enables real-time operational decisions.

Installation and Setup
----------------------

.. dropdown:: What are the system requirements for OpenSTEF?
   :icon: checklist

   OpenSTEF 4.0 requires:
   
   - Python 3.12 or higher (Python 3.13 supported)
   - 64-bit operating system (Windows, macOS, or Linux)
   
   You can check your Python version with:
   
   .. code-block:: bash
   
      python --version
   
   .. note::
   
      If you need Python 3.10/3.11 support, use OpenSTEF 3.x instead.

.. dropdown:: How do I install OpenSTEF?
   :icon: question

   The simplest way to install OpenSTEF is using pip:
   
   .. code-block:: bash
   
      pip install openstef
   
   OpenSTEF is also available through other package managers:
   
   .. code-block:: bash
   
      # Using uv
      uv add openstef
      
      # Using conda
      conda install -c conda-forge openstef
      
      # Using pixi
      pixi add openstef
   
   For detailed installation instructions including modular package installation, see :doc:`user_guide/installation`.

.. dropdown:: What is uv and do I need it?
   :icon: question

   `uv <https://docs.astral.sh/uv/>`_ is a fast, Rust-based Python package manager used for OpenSTEF development. As a library user, you don't need uv—standard pip installation works fine.
   
   uv is only required if you're contributing to OpenSTEF development or setting up a development environment. See :doc:`contribute/development_setup` for development installation instructions.

Models and Forecasting
----------------------

.. dropdown:: Which machine learning model should I use?
   :icon: question

   OpenSTEF is model-agnostic and supports multiple algorithms. The most commonly used is **XGBoost** (gradient boosting trees), which provides:
   
   - Excellent performance for energy forecasting
   - Built-in support for quantile regression (probabilistic forecasts)
   - Efficient handling of complex feature interactions
   - Good performance with default settings
   
   Other supported models include LightGBM, linear models, and custom forecasters. Start with XGBoost unless you have specific requirements.

.. dropdown:: What are quantile forecasts and why use them?
   :icon: info

   Quantile forecasts predict multiple outcomes at different probability levels, providing uncertainty estimates. For example:
   
   - 10th percentile (P10): Low-end estimate
   - 50th percentile (P50): Median/most likely estimate
   - 90th percentile (P90): High-end estimate
   
   This is crucial for energy operations because it allows you to:
   
   - Assess risk (what's the worst-case load?)
   - Make informed decisions with confidence intervals
   - Balance between over- and under-forecasting
   
   OpenSTEF generates probabilistic forecasts by default, giving you the full uncertainty picture rather than a single point estimate.

.. dropdown:: How do I create my first forecast?
   :icon: light-bulb

   Here's a minimal example using OpenSTEF's workflow pattern:
   
   .. code-block:: python
   
      from openstef_beam.models import ForecastingModel
      from openstef_beam.workflow import CustomForecastingWorkflow
      from openstef_models.models.forecasting import XGBoostQuantileForecaster
      import pandas as pd
      
      # Load your time series data
      data = pd.read_csv("your_data.csv", parse_dates=["datetime"])
      
      # Configure the model
      model = ForecastingModel(
          forecaster=XGBoostQuantileForecaster(),
          quantiles=[0.1, 0.5, 0.9]
      )
      
      # Create workflow
      workflow = CustomForecastingWorkflow(model=model)
      
      # Train and predict
      workflow.train(data)
      forecasts = workflow.predict(data)
   
   For complete examples, see the :doc:`examples` section and :doc:`user_guide/index`.

Getting Started
---------------

.. dropdown:: Where should I start learning OpenSTEF?
   :icon: question

   We recommend this learning path:
   
   1. **Installation**: Follow the :doc:`user_guide/installation` guide
   2. **Quickstart**: Try the basic examples in :doc:`examples`
   3. **Core concepts**: Read about the library architecture in :doc:`user_guide/index`
   4. **API reference**: Explore specific functions in :doc:`api/index`
   
   The library is designed to be modular—you can start with simple forecasting and gradually add complexity as needed.

.. dropdown:: Can I use OpenSTEF for non-energy forecasting?
   :icon: question

   While OpenSTEF is optimized for energy forecasting, its core machine learning pipelines can be adapted for other time series forecasting tasks. However, some built-in features are energy-specific:
   
   - Solar radiation to PV generation transformations
   - Energy-specific holiday effects
   - Grid-related feature engineering
   
   If you're forecasting non-energy time series, you may need to customize the feature engineering pipeline or skip domain-specific transformations.

.. dropdown:: How do I get help or report issues?
   :icon: info

   - **Documentation**: Check this documentation site first
   - **Examples**: Review the :doc:`examples` for common use cases
   - **GitHub Issues**: Report bugs or request features at the OpenSTEF repository
   - **Community**: Join discussions in the :doc:`project/index` section
   
   When reporting issues, include your Python version, OpenSTEF version, and a minimal reproducible example.