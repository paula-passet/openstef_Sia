Who is it for?
==============

OpenSTEF is built for data scientists and engineers working in the energy domain who
need reliable, repeatable short-term forecasts (hours to days ahead) for use cases such
as congestion management, transport forecasting, EV charging capacity estimation, and
grid loss prediction. Familiarity with Python and basic machine learning concepts is
assumed; deep expertise in energy systems is not required.

Getting started
===============

If you are new to OpenSTEF, the **User Guide** is the best place to begin. It walks you
through installation, explains the core concepts behind prediction jobs and pipelines,
and includes worked examples to get your first forecast running quickly.

Once you are comfortable with the basics, the **API Reference** provides complete,
auto-generated documentation for every public class and function in the library.

The **Examples** section contains self-contained notebooks demonstrating common
workflows, and the **Changelog** records what has changed between releases.

Install
=======

.. code-block:: bash

   pip install openstef

For alternative installation methods and environment setup, see the installation guide
in the User Guide.

Community & support
===================

OpenSTEF is developed in the open under the `LF Energy <https://lfenergy.org/>`_
umbrella. The fastest way to get help is to join the **#openstef** channel on the
`LF Energy Slack workspace <https://slack.lfenergy.org/>`_. For bugs and feature
requests, use the `GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_.
The project also hosts four-weekly community meetings — details and invite links are on
the `OpenSTEF wiki <https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting>`_.

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
