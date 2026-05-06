OpenSTEF Documentation
======================

OpenSTEF is a Python library for generating short-term forecasts of energy load, solar, and wind production. It provides a collection of machine learning pipelines — for training models, creating forecasts, and optimising hyperparameters — built on top of scikit-learn-compatible regressors and MLflow model management.

Who is it for?
--------------

OpenSTEF is aimed at data scientists and energy system engineers who need to build and operate short-term energy forecasting systems. It is particularly well-suited for grid operators and energy companies that manage multiple forecasting locations and need a structured, reproducible workflow from raw time-series data to production-ready predictions.

Where to start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through installation and your first forecast in a few lines of code. From there, the **User Guide** covers the core concepts you will encounter throughout the library: prediction jobs, the training and forecast pipelines, feature engineering, and model serialisation with MLflow.

Once you are comfortable with the basics, the **API Reference** provides complete documentation for every public module, from ``openstef.pipeline`` and ``openstef.model`` to the data classes and post-processing utilities. The **Tutorials** section offers end-to-end worked examples for common tasks such as training a custom model, backtesting a forecast, and splitting a net load signal into its solar and wind components.

.. note::
   OpenSTEF is a `LF Energy <https://lfenergy.org>`_ project, licensed under the Mozilla Public License 2.0.

A quick taste
-------------

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline_core
   from openstef.pipeline.train_model import train_model_pipeline_core

   # Train a model and generate a forecast for a prediction job
   model, model_specs, _, _ = train_model_pipeline_core(pj, training_data)
   forecast = create_forecast_pipeline_core(pj, input_data, model, model_specs)

Community and support
---------------------

OpenSTEF is developed in the open. The source code, issue tracker, and contribution guidelines are all hosted on `GitHub <https://github.com/OpenSTEF/openstef>`_. Bug reports and feature requests are welcome via GitHub Issues. For broader discussion and questions, the project participates in the `LF Energy community <https://lfenergy.org/community/>`_. Contributions of all kinds — code, documentation, and examples — are encouraged; see the contributing guide for details.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   api/index
