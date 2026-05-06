OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
building and running short-term energy load forecasts — predicting grid load hours to
days ahead. It provides end-to-end ML pipelines covering data preprocessing, feature
engineering, model training, probabilistic forecasting, and evaluation, with built-in
domain knowledge for energy systems such as PV generation estimates from solar radiation
and temperature data.

OpenSTEF is built for **data scientists and ML engineers** working at grid operators,
energy companies, or research institutions who need reliable, production-ready forecasting
infrastructure without building it from scratch.

.. note:: [VISUALIZATION: OpenSTEF high-level pipeline — raw energy data in, probabilistic load forecast out]

Getting Started
---------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. From there, the **User Guide** covers
the core concepts in depth: how pipelines are structured, how models are trained and
stored, and how to configure forecasting for your own grid locations.

For a complete reference of every class, function, and parameter, the **API Reference**
is generated directly from the source code. If you want to extend OpenSTEF — adding a
custom model, a new feature set, or an integration with an external system — the
**Developer Guide** explains the architecture and contribution workflow.

Community & Support
-------------------

OpenSTEF is a `LF Energy <https://www.lfenergy.org/projects/openstef/>`_ project
developed openly on `GitHub <https://github.com/OpenSTEF/openstef>`_. The fastest way
to get help or discuss ideas is the community **Slack workspace** at
`slack.lfenergy.org <https://slack.lfenergy.org/>`_. You can also reach the team by
email at `openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_.

The community holds open bi-weekly meetings — details and calendar invites are on the
`community meeting page <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_.
Bug reports and feature requests go to
`GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_.

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
