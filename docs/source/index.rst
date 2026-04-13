OpenSTEF Documentation
======================

OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library that provides
complete machine learning pipelines for short-term energy load forecasting. It handles everything
from data preprocessing and feature engineering through model training, probabilistic forecasting,
and evaluation — with domain knowledge about energy systems built in from the start.

**Who is it for?** OpenSTEF is aimed at data scientists, ML engineers, and researchers working
at grid operators, utilities, or research institutions who need reliable, reproducible load
forecasts at the scale of hours to days ahead. Whether you are building a congestion management
system, estimating EV charging capacity, or researching grid loss prediction, OpenSTEF gives you
production-tested pipelines rather than a blank canvas.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through installation and
your first forecast in minutes. Once you have the basics, the **User Guide** covers the core
concepts in depth: how prediction jobs are structured, how the feature engineering pipeline works,
and how to train and deploy your own models. For a full description of every public class and
function, the **API Reference** is the authoritative source. If you want to extend OpenSTEF or
contribute back to the project, the **Developer Guide** explains the architecture, coding
conventions, and how to run the test suite.

.. note::

   OpenSTEF is a library — you integrate it into your own code and infrastructure. It does not
   ship as a standalone application or service.

Community & Support
-------------------

The OpenSTEF community is active and welcoming to newcomers.

- **Slack:** Join the ``#openstef`` channel on the `LF Energy Slack workspace <https://slack.lfenergy.org/>`_.
  If your organisation requires an invitation, email ``openstef@lfenergy.org``.
- **GitHub:** Browse the source, open bug reports, or request features on the
  `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_.
- **Community meetings:** Four-weekly open meetings and co-coding sessions are listed on the
  `LF Energy wiki <https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting>`_.
- **Project home:** `openstef.org <https://openstef.org>`_

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
