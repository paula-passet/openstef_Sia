OpenSTEF Documentation
======================

OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term energy forecasts. It provides complete machine learning
pipelines — from data preprocessing and feature engineering through model training,
probabilistic forecasting, and evaluation — with domain knowledge for the power grid
built in. If you need to predict electrical load hours to days ahead, OpenSTEF gives
you the tools to do it without starting from scratch.

.. note::

   OpenSTEF is a **library**, not a standalone application. You integrate it into
   your own Python code and workflows.

Who Is OpenSTEF For?
--------------------

OpenSTEF is designed for data scientists and engineers working in the energy sector
who need reliable short-term load forecasts — for congestion management, transport
forecasting, EV charging capacity estimation, or grid loss prediction. It assumes
familiarity with Python and basic machine learning concepts, but handles the
energy-domain complexity for you.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. Once you have the basics, the
**User Guide** covers the core concepts in depth: how prediction jobs are structured,
how the built-in feature engineering works, and how to train and run models using the
standard pipelines. The **API Reference** provides complete documentation for every
public class and function in the library. For real-world examples and benchmark
experiments, see the **Tutorials** section.

Community and Support
---------------------

OpenSTEF is a `LF Energy <https://lfenergy.org>`_ project developed openly on GitHub.

- **GitHub:** https://github.com/OpenSTEF/openstef — source code, issues, and pull requests
- **Slack:** https://slack.lfenergy.org/ — join the OpenSTEF channel for questions and discussion
- **Email:** openstef@lfenergy.org
- **Community meetings:** https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting — open to everyone, held every four weeks

Contributions are welcome. Whether you are fixing a bug, adding a model, or improving
the docs, please open an issue or pull request on GitHub to get started.

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
