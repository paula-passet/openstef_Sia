OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
predicting electricity load hours to days ahead. It provides end-to-end machine learning
pipelines — from data preprocessing and feature engineering through model training,
probabilistic forecasting, and evaluation — with built-in domain knowledge for energy
systems. OpenSTEF is model-agnostic and produces uncertainty bandwidths alongside
point forecasts, making it suitable for operational decision-making.

Who is it for?
--------------

OpenSTEF is built for data scientists and ML engineers working on energy grid problems:
congestion management, transport forecasting, EV charging capacity estimation, and grid
loss prediction. It is used in production at Alliander across 10,000+ grid locations,
but the library is designed to be reusable by any organisation working with short-term
energy time series.

Where to start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast. The **User Guide** covers the core concepts in
depth — prediction jobs, pipelines, feature engineering, and model management — and is
the right place to understand how the pieces fit together before writing production code.
The **API Reference** provides the full technical specification for every public class
and function. If you want to extend or contribute to the library, the **Developer Guide**
explains the architecture, contribution workflow, and testing strategy.

.. note::
   OpenSTEF does **not** automatically retrieve weather data. You are responsible for
   supplying weather features to the forecasting pipelines.

Community and support
---------------------

OpenSTEF is a `LF Energy <https://www.lfenergy.org/projects/openstef/>`_ project.
The primary support channel is **Slack** — join at https://slack.lfenergy.org/ and find
the OpenSTEF workspace. You can also reach the team by email at openstef@lfenergy.org.
The community holds a four-weekly open meeting; details are on the
`community meeting page <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_.

Bug reports and feature requests go to the
`GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_.
The repository also maintains a public backlog with labelled *good first issues* for
new contributors.

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
