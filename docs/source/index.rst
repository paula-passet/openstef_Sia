OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
predicting electricity load hours to days ahead. It provides complete machine learning
pipelines — from data preprocessing and feature engineering through model training,
probabilistic forecasting, and evaluation — with domain knowledge for energy systems
built in from the start.

OpenSTEF is built for **data scientists and engineers at grid operators, utilities, and
energy companies** who need reliable, production-ready forecasting across many grid
locations. It is model-agnostic, ships with XGBoost and LightGBM out of the box, and
produces probabilistic forecasts with uncertainty bandwidths rather than single-point
predictions.

.. note:: [VISUALIZATION: Example probabilistic load forecast showing predicted load with uncertainty bandwidth over a 48-hour horizon]

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. From there, the **User Guide** covers
the core concepts you will use day-to-day: how pipelines are structured, how to bring
your own data, and how to configure and train models for your grid locations.

For a deeper look at specific capabilities — backtesting, feature engineering, model
storage with MLflow, or deploying forecasts at scale with ``openstef-beam`` — the
**How-To Guides** provide focused, task-oriented walkthroughs. The **API Reference**
gives complete, auto-generated documentation for every public class and function in the
library.

Community and Support
---------------------

OpenSTEF is a `LF Energy <https://www.lfenergy.org/projects/openstef/>`_ project
developed openly on `GitHub <https://github.com/OpenSTEF/openstef>`_. Bug reports and
feature requests go through
`GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_.

For questions and discussion, join the community on
`Slack <https://slack.lfenergy.org/>`_ or reach out by email at
`openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_. The team holds open community
meetings every four weeks — details on the
`meeting page <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_
— and co-coding sessions every eight weeks. New contributors are welcome; look for
**good first issues** on GitHub to get started.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   api/index
