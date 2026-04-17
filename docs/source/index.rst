OpenSTEF
========

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for building accurate short-term load forecasts in the power grid domain. It provides complete machine learning pipelines — from data preprocessing and feature engineering through model training, probabilistic forecasting, and evaluation — so energy data scientists can focus on their domain problem rather than boilerplate infrastructure.

Who is it for?
--------------

OpenSTEF is aimed at data scientists and engineers working at grid operators, utilities, and energy companies who need reliable short-term load forecasts (hours to days ahead). It is equally useful for researchers benchmarking forecasting methods on energy data.

Where to start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through installation and your first forecast in a few lines of code. Once you have the basics, the **User Guide** covers the full pipeline in depth — feature engineering, model selection, probabilistic outputs, and how to bring your own data. The **API Reference** provides complete documentation for every public class and function. If you want to contribute or understand how the project is structured, the **Developer Guide** explains the architecture and contribution workflow.

.. note::
   OpenSTEF does **not** automatically retrieve weather data. You are responsible for supplying weather features alongside your load measurements. See the User Guide for details on expected input formats.

Community and support
---------------------

OpenSTEF is a `LF Energy <https://lfenergy.org/>`_ project. The best place to ask questions and connect with other users is the **LF Energy Slack** — join at https://slack.lfenergy.org/ and find the OpenSTEF channel. You can also reach the team by email at openstef@lfenergy.org.

Bug reports and feature requests belong on the `GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_. The community holds open meetings every four weeks; details are on the `community meeting page <https://lf-energy.atlassian.net/wiki/spaces/OS/pages/32278358/OpenSTEF+four-weekly+community+meeting>`_.

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
