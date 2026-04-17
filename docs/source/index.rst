OpenSTEF Documentation
======================

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term load forecasts in the power grid domain. It provides
complete machine learning pipelines — from data preprocessing and feature engineering
through model training, probabilistic forecasting, and evaluation — so you can focus on
your forecasting problem rather than the plumbing around it.

Who is it for?
--------------

OpenSTEF is built for data scientists and engineers working at grid operators, energy
companies, or research institutions who need reliable, production-ready forecasting
pipelines. If you are managing grid congestion, estimating EV charging capacity, or
predicting grid losses, OpenSTEF gives you the domain-specific tooling to do it without
starting from scratch.

Getting started
---------------

If you are new to OpenSTEF, the **Installation** page covers how to get the library set
up, followed by the **Quickstart** guide which walks through training your first model
and generating a forecast in a few lines of code.

Once you are comfortable with the basics, the **User Guide** explains the core concepts
in depth — prediction jobs, pipelines, feature engineering, and probabilistic output.
The **API Reference** provides complete documentation for every public module and
function.

For those looking to extend or contribute to the library, the **Contributing** section
describes the development workflow and coding standards.

.. note::
   OpenSTEF generates probabilistic forecasts — each prediction comes with uncertainty
   bandwidths, not just a single-point estimate. Weather data is not fetched
   automatically; you supply it as part of your input.

Community and support
---------------------

OpenSTEF is a `LF Energy <https://lfenergy.org>`_ project. The best place to ask
questions and connect with other users is the **LF Energy Slack workspace** at
`slack.lfenergy.org <https://slack.lfenergy.org/>`_ (join the ``#openstef`` channel).
You can also reach the team by email at `openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_
or open an issue on `GitHub <https://github.com/OpenSTEF/openstef/issues>`_.
Community meetings are held regularly and are open to everyone — see the
`meeting page <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_
for the schedule.

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
