OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library
for predicting energy load hours to days ahead. It provides complete machine learning
pipelines — from data preprocessing and feature engineering through model training,
probabilistic forecasting, and evaluation — with domain knowledge for energy systems
built in from the start.

OpenSTEF is built for data scientists and engineers at energy utilities, grid operators,
and research institutions who need reliable, production-ready short-term load forecasts.
It is model-agnostic, currently supporting classical ML models such as XGBoost and
LightGBM, with deep learning support planned for future releases.

.. note:: [VISUALIZATION: OpenSTEF high-level pipeline — raw energy data in, probabilistic forecasts out]

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. From there, the **User Guide**
covers the core concepts you will use day-to-day: how pipelines are structured,
how feature engineering works, and how to configure and train models on your own data.

For teams integrating OpenSTEF into a larger system, the **Integrations** section
explains how to connect storage backends, MLflow tracking, and custom callbacks.
The full **API Reference** documents every public class and function.

If you want to understand the design decisions behind the library or contribute
to its development, the **Developer Guide** covers the architecture, contribution
workflow, and how to run the benchmark suite.

Community and Support
---------------------

OpenSTEF is a `LF Energy <https://www.lfenergy.org/projects/openstef/>`_ project
developed openly on `GitHub <https://github.com/OpenSTEF/openstef>`_. The fastest
way to get help or discuss ideas is the community **Slack workspace** at
`slack.lfenergy.org <https://slack.lfenergy.org/>`_. You can also reach the team
by email at `openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_.

The community holds open meetings every four weeks — details and the agenda are on
the `community meeting page <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_.
Bug reports and feature requests go to the
`GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   api/index
