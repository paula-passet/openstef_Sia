OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term load forecasts in the power grid domain. It provides
complete machine learning pipelines — from data preprocessing and feature engineering
through model training, probabilistic forecasting, and evaluation — so you can focus on
your forecasting problem rather than the plumbing around it.

Who Is It For?
--------------

OpenSTEF is aimed at data scientists and engineers working in the energy sector who need
reliable, production-ready forecasting pipelines. Whether you are managing grid
congestion, estimating EV charging capacity, or predicting grid losses, OpenSTEF gives
you a model-agnostic framework with built-in energy-domain knowledge (such as solar
irradiance to PV generation estimates) and probabilistic output with uncertainty
bandwidths.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. Once you have the basics, the
**User Guide** covers the core concepts in depth: prediction jobs, pipelines, feature
engineering, and how to bring your own model. The **API Reference** provides complete
documentation for every public class and function. For real-world worked examples,
the **Tutorials** section contains end-to-end notebooks you can run locally.

.. note::
   OpenSTEF does not automatically retrieve weather data. You are responsible for
   supplying weather features to the pipelines. See the User Guide for details.

Community & Support
-------------------

OpenSTEF is developed under the `LF Energy <https://lfenergy.org/>`_ umbrella and
welcomes contributions of all kinds.

- **Slack** — join the conversation at https://slack.lfenergy.org/ (``#openstef`` channel)
- **Email** — reach the maintainers at openstef@lfenergy.org
- **Community meeting** — four-weekly open call, details at the `LF Energy wiki <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_
- **GitHub** — browse the source, open issues, or submit pull requests at https://github.com/OpenSTEF/openstef

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
