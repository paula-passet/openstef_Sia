Who is it for?
==============

OpenSTEF is built for data scientists, ML engineers, and researchers working in the
energy sector who need reliable, production-ready forecasts of electricity load, solar
generation, or related quantities over horizons of hours to days ahead. It is equally
useful for those exploring energy forecasting for the first time and for teams
integrating forecasts into operational grid-management systems.

Where to start
==============

If you are new to OpenSTEF, the **User Guide** is the best place to begin. It walks
you through installation, explains the core concepts of prediction jobs and pipelines,
and shows you how to train your first model and generate forecasts. Once you are
comfortable with the basics, the **Examples** section provides worked notebooks that
cover common use cases end-to-end.

When you need precise details on classes, functions, or parameters, the **API
Reference** documents every public interface in the library. If you want to understand
the statistical and domain-specific ideas behind the library — such as how solar
irradiance features are constructed or how uncertainty bandwidths are produced — the
**Background** material covers the methodology in depth.

Finally, if you would like to fix a bug, propose a feature, or improve these docs, the
**Contributing** guide explains how the project is structured and how to get your
changes merged.

Install
=======

.. code-block:: bash

   pip install openstef

For alternative package managers and detailed setup instructions, see the installation
guide in the User Guide.

Community & support
===================

OpenSTEF is developed in the open under the LF Energy umbrella. The best place to ask
questions, report bugs, or request features is the
`GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_. Contributions
of all kinds are welcome — code, documentation, and community support alike. See the
Contributing section to get started.

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
