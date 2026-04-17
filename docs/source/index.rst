OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term load forecasts in the energy domain. It provides complete
machine learning pipelines — from data preprocessing and feature engineering through model
training, probabilistic forecasting, and evaluation — so that data scientists and grid
operators can focus on their use case rather than boilerplate infrastructure.

Who Is It For?
--------------

OpenSTEF is built for data scientists, ML engineers, and researchers working on energy
forecasting problems. Whether you are forecasting grid load for congestion management,
estimating EV charging capacity, or predicting grid losses, OpenSTEF gives you a
model-agnostic framework with domain knowledge already baked in — including energy-specific
feature engineering such as deriving PV generation estimates from solar radiation and
temperature data.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through installation
and your first forecast in minutes. From there, the **User Guide** covers the core concepts
in depth: how prediction jobs are structured, how the training and inference pipelines work,
and how to extend the library with custom models or features. The **API Reference** provides
full documentation of every public class and function. If you want to see OpenSTEF applied
to a real dataset, the **Tutorials** section contains end-to-end notebooks you can run
locally or in the cloud.

.. note::

   OpenSTEF is a library, not a hosted service. You integrate it into your own Python
   environment and infrastructure.

Community & Support
-------------------

OpenSTEF is a `LF Energy <https://lfenergy.org/>`_ project developed openly on GitHub.

- **GitHub:** https://github.com/OpenSTEF/openstef — source code, issues, and releases
- **Slack:** https://slack.lfenergy.org/ — join the OpenSTEF channel for questions and discussion
- **Email:** openstef@lfenergy.org
- **Community meetings:** https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting

Contributions are welcome — bug reports, feature requests, and pull requests all help the
project grow.

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
