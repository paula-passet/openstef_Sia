OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term load forecasts in the power grid domain. It provides
complete, end-to-end machine learning pipelines — from data preprocessing and feature
engineering through model training, probabilistic forecasting, and evaluation — so that
energy data scientists can focus on results rather than boilerplate.

.. note::

   OpenSTEF is a **library**, not an application. You integrate it into your own
   Python projects and workflows.

Who Is It For?
--------------

OpenSTEF is designed for data scientists, ML engineers, and researchers working on
energy grid problems: load forecasting, congestion management, transport forecasts, EV
charging capacity estimation, and grid loss prediction. Familiarity with Python and
basic machine learning concepts is assumed; no prior energy-domain expertise is required
to get started.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. The **User Guide** then covers the
core concepts — prediction jobs, pipelines, and the model framework — in depth. When
you are ready to go further, the **Examples & Tutorials** section provides runnable
notebooks on real datasets, and the **API Reference** gives complete details on every
public class and function.

.. code-block:: python

   import openstef

   # Train a model and generate a probabilistic forecast in a few lines
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

Community & Support
-------------------

OpenSTEF is developed under the `LF Energy <https://lfenergy.org/>`_ umbrella and
welcomes contributions from the community.

- **Slack:** Join the conversation at https://slack.lfenergy.org/
- **Email:** openstef@lfenergy.org
- **Community meetings:** https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting
- **GitHub:** https://github.com/OpenSTEF/openstef
- **Bug reports & feature requests:** https://github.com/OpenSTEF/openstef/issues

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   user_guide/index
   concepts/index
   architecture/index
   faq
   changelog
   contribute/index
   api/index
