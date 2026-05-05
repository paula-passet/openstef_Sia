OpenSTEF Documentation
======================

OpenSTEF is a Python library for building short-term energy load forecasting systems.
It provides end-to-end pipelines — from feature engineering and model training to
forecast generation — designed for energy grid operators and data scientists working
with time-series power data.

.. note:: [VISUALIZATION: OpenSTEF high-level workflow showing input data flowing through training and forecast pipelines to produce load predictions with confidence intervals]

Who Is It For?
--------------

OpenSTEF is built for data scientists and engineers at energy utilities, grid operators,
and research institutions who need reliable, production-ready load forecasts. If you
work with smart meter data, weather inputs, or day-ahead electricity prices and need
to predict grid load at 15-minute to multi-hour horizons, OpenSTEF gives you the
building blocks to do it.

Getting Started
---------------

If you are new to OpenSTEF, the **Installation** page covers how to get the library
set up, and the **Quickstart** walks you through defining a prediction job, training
your first model, and generating a forecast in a few lines of code:

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

   # Define what to forecast
   pj = PredictionJobDataClass(id=1, model="xgb", horizon_minutes=47, ...)

   # Train a model on historical load data
   model, report, specs, data = train_model_pipeline_core(pj, model_specs, input_data, horizons=[0.25, 47.0])

   # Generate a forecast
   forecast = create_forecast_pipeline(pj, input_data, mlflow_tracking_uri="./mlruns")

Once you have the basics working, the **Concepts** section explains how prediction
jobs, feature engineering, and model serialization fit together. The **Pipelines**
reference documents every built-in pipeline function, and **Models** covers the
regressors and hyperparameter optimization that OpenSTEF ships with.

Community & Support
-------------------

OpenSTEF is an open-source project under the `LF Energy <https://lfenergy.org>`_
umbrella, licensed under MPL-2.0.

- **GitHub** — report issues, browse source code, and open pull requests:
  `github.com/OpenSTEF/openstef <https://github.com/OpenSTEF/openstef>`_
- **Slack (LF Energy)** — ask questions and connect with other users:
  `lfenergy.slack.com <https://lfenergy.slack.com>`_ in the ``#openstef`` channel
- **Contributing** — see the ``CONTRIBUTING.md`` in the repository for guidelines
  on submitting changes and running the test suite.

.. note::

   OpenSTEF follows `Semantic Versioning <https://semver.org>`_. Check the
   `changelog <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_
   before upgrading between minor versions.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   api/index
