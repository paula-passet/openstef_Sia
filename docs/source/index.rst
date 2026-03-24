OpenSTEF Documentation
=====================

.. toctree::
   :maxdepth: 2
   :hidden:

   user_guide/index
   use_cases/index
   architecture/index
   how_to_guides/index
   concepts/index
   api/index
   examples
   faq
   changelog
   contribute/index

What is OpenSTEF?
=================

**OpenSTEF is an open-source Python library for short-term energy forecasting.** It provides the building blocks for training and running forecasting models — it is not a deployable application or pre-trained model.

.. [DIAGRAM: High-level architecture showing OpenSTEF as library component in user application]

OpenSTEF enables you to:

* Create **probabilistic forecasts** with quantile predictions (P10, P50, P90)
* Use multiple **machine learning models** (XGBoost, LightGBM, Linear) with automatic selection
* Build **custom forecasting workflows** tailored to your energy systems
* Perform comprehensive **backtesting** to validate model performance over historical data
* Leverage **energy-specific feature engineering** including weather dependencies and calendar effects

.. warning::
   **OpenSTEF is a library, not an application.** You need to write Python code to use it. If you're looking for a ready-to-deploy forecasting service, you'll need to build that using OpenSTEF as a component.

Key Use Cases
=============

* **Grid Congestion Management** — Predict when electrical grid capacity will be exceeded
* **Free Space Estimation** — Calculate available capacity on grid connections
* **Load Forecasting** — Forecast electrical demand at various aggregation levels
* **District Heating** — Predict thermal demand for heating networks
* **Grid Loss Prediction** — Estimate technical losses in electrical networks

Get Started
===========

Installation
------------

.. code-block:: bash

   pip install openstef

Quick Example
-------------

.. code-block:: python

   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Load your time series data
   # train_data = your pandas DataFrame with datetime index
   
   # Configure prediction job
   pj = PredictionJobDataClass(
       name="my_forecast",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9]
   )
   
   # Train and create forecast
   # forecast = create_forecast(pj, train_data)

.. note::
   This is a simplified example. See the :doc:`user_guide/quick_start` for a complete working tutorial.

What OpenSTEF is NOT
=====================

* ❌ **Not a deployed application** — You cannot just install and run OpenSTEF as a service
* ❌ **Not a pre-trained model** — You must train models on your own historical data  
* ❌ **Not a complete forecasting system** — You need to handle data ingestion, storage, and serving
* ❌ **Not plug-and-play** — Requires Python programming and time series forecasting knowledge

Navigation
==========

📚 **Learning OpenSTEF**
   :doc:`user_guide/index` | :doc:`user_guide/quick_start` | :doc:`user_guide/tutorials` | :doc:`examples`

🎯 **Understanding Applications**
   :doc:`use_cases/index` | :doc:`concepts/index`

🏗️ **Implementation**
   :doc:`architecture/index` | :doc:`how_to_guides/index` | :doc:`api/index`

❓ **Getting Help**
   :doc:`faq` | `GitHub Discussions <https://github.com/OpenSTEF/openstef/discussions>`_

Technical Requirements
======================

* **Python 3.8+**
* **pandas** for time series data manipulation
* Basic understanding of **time series forecasting** concepts
* Historical energy data with regular timestamps (typical: 15-minute intervals)

Community & Support
====================

* **GitHub Repository**: https://github.com/OpenSTEF/openstef
* **Community Discussions**: https://github.com/OpenSTEF/openstef/discussions  
* **LF Energy Project**: https://lfenergy.org/projects/openstef/
* **Issues & Bug Reports**: https://github.com/OpenSTEF/openstef/issues

OpenSTEF is developed by Alliander and maintained as an LF Energy project with contributions from the energy forecasting community.

Recent Updates
==============

**Version 4.0.0** — Latest release with improved API design and enhanced model capabilities.

See the :doc:`changelog` for complete release history and :doc:`contribute/index` to get involved in development.