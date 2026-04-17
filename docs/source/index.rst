OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term energy forecasts. It provides complete machine learning
pipelines — from data preprocessing and feature engineering through model training,
probabilistic forecasting, and evaluation — with domain knowledge for the power grid
built in from the start.

Who Is It For?
--------------

OpenSTEF is designed for data scientists and engineers working in the energy sector who
need reliable load forecasts hours to days ahead. Whether you are managing grid
congestion, estimating EV charging capacity, or predicting grid losses, OpenSTEF gives
you a model-agnostic framework that handles the heavy lifting so you can focus on your
use case.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. Once you are up and running, the
**User Guide** covers the core concepts in depth: how prediction jobs are structured,
how the built-in feature engineering works, and how to train and evaluate models.
The **API Reference** provides complete documentation for every public class and
function in the library. If you want to extend OpenSTEF — adding a custom model or
contributing a pipeline — the **Developer Guide** explains the architecture and
contribution workflow.

.. note::

   OpenSTEF does **not** automatically retrieve weather data. You are responsible for
   supplying weather and load time series as inputs to the pipelines.

Community & Support
-------------------

OpenSTEF is a `LF Energy <https://lfenergy.org/>`_ project developed openly on GitHub.

- **GitHub:** https://github.com/OpenSTEF/openstef — source code, issues, and releases
- **Slack:** https://slack.lfenergy.org/ — join the ``#openstef`` channel for questions and discussion
- **Email:** openstef@lfenergy.org
- **Community meetings:** `Bi-weekly open calls <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_ — all are welcome

Found a bug or have a feature request? Open an issue on
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
   contribute/index
   api/index
