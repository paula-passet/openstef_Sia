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
you a production-ready framework rather than a blank canvas. Familiarity with Python and
basic machine learning concepts is assumed; deep expertise in energy systems is not
required.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. Once you have the basics, the
**User Guide** covers the core concepts in depth — prediction jobs, pipelines, feature
engineering, and probabilistic output. The **API Reference** provides complete
documentation for every public class and function in the library. If you want to
contribute or understand how the project is governed, the **Contributing** section has
everything you need.

.. note::

   OpenSTEF does **not** automatically retrieve weather data. You are responsible for
   supplying weather features alongside your load measurements. See the User Guide for
   details on expected input formats.

Community and Support
---------------------

OpenSTEF is a `LF Energy <https://lfenergy.org/>`_ project developed in the open.

- **Slack** — join the community at https://slack.lfenergy.org/ (``#openstef`` channel)
- **Email** — reach the maintainers at openstef@lfenergy.org
- **GitHub** — browse the source, open issues, or submit pull requests at
  https://github.com/OpenSTEF/openstef
- **Community meetings** — open to everyone; details at
  https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting

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
