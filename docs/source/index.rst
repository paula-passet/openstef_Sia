OpenSTEF Documentation
======================

OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term energy forecasts in the power grid domain. It provides
complete machine learning pipelines — from data preprocessing and feature engineering
through model training, probabilistic forecasting, and evaluation — so that data
scientists and grid operators can focus on their domain problem rather than boilerplate
infrastructure.

.. note::

   OpenSTEF is a **library**, not an application. You integrate it into your own
   Python code and workflows.

Who Is It For?
--------------

OpenSTEF is designed for data scientists, ML engineers, and researchers working on
energy forecasting problems — particularly those involving grid congestion management,
transport forecasting, EV charging capacity estimation, and grid loss prediction. It
assumes familiarity with Python and basic machine learning concepts, but no prior
energy-domain expertise is required: domain knowledge is embedded directly in the
library's feature engineering.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast end-to-end. Once you have the basics, the
**User Guide** covers the core concepts in depth: prediction jobs, pipelines, feature
engineering, and probabilistic output. The **API Reference** provides complete
documentation for every public class and function. If you want to contribute or
understand the project roadmap, the **Developer Guide** is the right place to look.

Community and Support
---------------------

OpenSTEF is a `LF Energy <https://lfenergy.org/>`_ project. The best place to ask
questions and connect with other users is the community Slack workspace — join at
`slack.lfenergy.org <https://slack.lfenergy.org/>`_ and find the OpenSTEF channel.
You can also reach the team by email at `openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_
or attend the open community meetings held every four weeks
(`meeting page <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_).

Bug reports and feature requests go to the
`GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_.
The main repository is at `github.com/OpenSTEF/openstef <https://github.com/OpenSTEF/openstef>`_.

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
