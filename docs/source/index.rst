OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
predicting electricity load hours to days ahead. It provides end-to-end machine learning
pipelines — from data preprocessing and feature engineering through model training,
probabilistic forecasting, and evaluation — with built-in domain knowledge for energy
systems such as PV generation estimates and weather-driven features.

OpenSTEF is built for data scientists and engineers working on grid management, congestion
forecasting, EV charging capacity estimation, and related energy use cases. It is
model-agnostic and designed to scale: Alliander runs it in production across more than
10,000 grid locations.

Getting Started
---------------

If you are new to OpenSTEF, the **Getting Started** section walks you through installation
and your first forecast. From there, the **User Guide** covers the core concepts —
prediction jobs, pipelines, feature engineering, and probabilistic outputs — with
worked examples you can run immediately.

For a deeper look at the library's internals, the **API Reference** documents every public
module, class, and function. If you want to extend OpenSTEF — adding a custom model,
integrating a new data source, or contributing a pipeline — the **Developer Guide**
explains the architecture and contribution workflow.

.. note::
   OpenSTEF V4 is currently in alpha. The API is stabilising but may change before the
   final release. See the changelog for details on what is new compared to V3.

Community & Support
-------------------

OpenSTEF is developed in the open under the LF Energy umbrella. The fastest way to get
help or share ideas is the **#openstef** channel on the `LF Energy Slack <https://slack.lfenergy.org/>`_.
You can also reach the team by email at `openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_
or join the `four-weekly community meeting <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_
open to everyone.

Bug reports and feature requests go to the `GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_.
The repository also maintains a public backlog with labelled *good first issues* for new
contributors.

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
