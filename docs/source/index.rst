OpenSTEF Documentation
======================

OpenSTEF is a Python library for building short-term energy load forecasting systems.
It provides end-to-end pipelines — from feature engineering and model training to
forecast generation — so that energy grid operators and data scientists can deploy
production-ready forecasts without building the underlying ML infrastructure from scratch.

Who is it for?
--------------

OpenSTEF is aimed at **data scientists and engineers** working in the energy sector who
need reliable, repeatable load forecasts at the substation or portfolio level. It is
equally useful for researchers exploring forecasting methods and for operations teams
integrating forecasts into grid management workflows.

Getting Started
---------------

If you are new to OpenSTEF, the **Installation** page covers how to add the library to
your project. The **Concepts** section explains the two central abstractions —
*PredictionJobs* and *Pipelines* — that everything else builds on. Once those are clear,
the **Tutorials** walk you through training your first model and generating a forecast
with real data.

For a quick taste, training a model and producing a forecast takes only a few lines:

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Train a model for a prediction job
   model, report, model_specs, datasets = train_model_pipeline_core(
       pj, model_specs, input_data, horizons=[0.25, 47.0]
   )

   # Generate a forecast using the trained model
   forecast = create_forecast_pipeline(pj, input_data, mlflow_tracking_uri="./mlruns")

The **API Reference** provides full documentation for every public module, and the
**How-to Guides** cover common tasks such as hyperparameter optimisation, backtesting,
and adding custom regressors.

.. note::

   OpenSTEF follows a *prediction job* model: each forecast target (e.g. a substation)
   is described by a ``PredictionJobDataClass`` that carries its location, horizon,
   model type, and other settings. All pipelines accept this object as their first
   argument.

Community and Support
---------------------

OpenSTEF is an open-source project hosted under the
`LF Energy foundation <https://lfenergy.org>`_.
Source code, issue tracking, and pull requests live on
`GitHub <https://github.com/OpenSTEF/openstef>`_.
For questions and discussion, join the community on the
`LF Energy Slack <https://slack.lfenergy.org>`_ in the **#openstef** channel.
Contributions are welcome — see the ``CONTRIBUTING.md`` file in the repository for
guidelines.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   api/index
