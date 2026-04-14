Who is it for?
==============

OpenSTEF is built for data scientists, ML engineers, and researchers working on energy
grid problems: congestion management, transport forecasting, EV charging capacity
estimation, grid loss prediction, and similar use cases. If you need accurate,
uncertainty-aware load forecasts hours to days ahead, OpenSTEF gives you the domain
knowledge and tooling to get there quickly.

Getting started
===============

If you are new to OpenSTEF, the **User Guide** is the best place to begin. It walks you
through installation, explains core concepts such as prediction jobs and pipelines, and
shows you how to train your first model and generate forecasts. Once you are comfortable
with the basics, the **API Reference** provides complete documentation for every public
module, class, and function in the library. Worked **Examples** demonstrate end-to-end
workflows for common use cases, and the **Changelog** tracks what has changed between
releases.

Install
=======

.. code-block:: bash

   pip install openstef

For alternative package managers and detailed setup instructions, see the
:doc:`user_guide/installation` page.

Community & support
===================

OpenSTEF is developed in the open under the `LF Energy <https://lfenergy.org/>`_
umbrella. The quickest way to get help is the **#openstef** channel on the
`LF Energy Slack workspace <https://slack.lfenergy.org/>`_. Bugs and feature requests
are tracked on `GitHub <https://github.com/OpenSTEF/openstef/issues>`_. The team also
hosts four-weekly community meetings — details and invite links are on the
`project wiki <https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting>`_.
If you would like to contribute code, documentation, or examples, see the
**Contributing** section.

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
