OpenSTEF Documentation
======================

OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for
predicting electricity load hours to days ahead. It provides complete machine learning
pipelines — from data preprocessing and feature engineering through model training,
probabilistic forecasting, and evaluation — with domain knowledge for energy systems
built in. OpenSTEF is developed by `Alliander <https://www.alliander.com>`_ and is a
`Linux Foundation Energy <https://lfenergy.org>`_ project.

Who is it for?
--------------

OpenSTEF is aimed at data scientists and engineers working at grid operators, energy
retailers, or research institutions who need reliable short-term load forecasts.
Whether you are running congestion management for thousands of grid locations or
experimenting with a single solar park, OpenSTEF gives you the modelling infrastructure
so you can focus on your data and use case rather than pipeline boilerplate.

Where to start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in a few lines of code. Once you are up and
running, the **User Guide** covers the core concepts in depth: how prediction jobs are
defined, how feature engineering works, and how to interpret probabilistic forecast
outputs. The **API Reference** provides complete, auto-generated documentation for every
public module and function. If you want to deploy OpenSTEF in a production environment
— scheduled jobs, cloud platforms, or orchestration tools such as Dagster — the
**Deployment** section has reference patterns to get you there.

Community and support
---------------------

OpenSTEF is community-driven. Development is coordinated through a public backlog on
`GitHub <https://github.com/OpenSTEF/openstef>`_, and the team holds bi-weekly open
community meetings alongside regular co-coding sessions. The best place to ask
questions or share ideas is the `LF Energy Slack <https://slack.lfenergy.org/>`_
(``#openstef`` channel). You can also reach the maintainers by email at
`openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_. Bug reports and feature
requests go to the
`GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_.

.. note::

   OpenSTEF is currently in **V4 Alpha**. The API is stabilising but may still change
   before the stable release. Check the changelog before upgrading.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   api/index
