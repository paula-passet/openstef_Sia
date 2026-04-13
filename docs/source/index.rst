Who is it for?
==============

OpenSTEF is built for data scientists and engineers working at grid operators,
utilities, and energy companies who need reliable, production-ready forecasts of
electricity load, generation, or related quantities hours to days ahead. Whether you
are exploring forecasting for the first time or integrating OpenSTEF into an existing
operational system, the library is designed to be both approachable and extensible.

Getting started
===============

If you are new to OpenSTEF, the **User Guide** is the best place to begin. It walks
you through installation, explains the core concepts behind the library's pipeline
design, and shows you how to train your first model and generate forecasts. Once you
are comfortable with the basics, the **Examples** section provides worked notebooks
covering common use cases such as probabilistic forecasting, custom model integration,
and handling missing data.

When you need precise details about a class, function, or parameter, the **API
Reference** provides complete, auto-generated documentation for every public symbol in
the library.

Install
=======

.. code-block:: bash

   pip install openstef

For alternative installation methods and environment setup, see the
:doc:`installation guide <user_guide/installation>`.

Community and support
=====================

OpenSTEF is developed in the open under the `Linux Foundation Energy
<https://www.lfenergy.org/projects/openstef/>`_ umbrella. If you encounter a bug or
want to propose a new feature, please open an issue on the `GitHub issue tracker
<https://github.com/OpenSTEF/openstef/issues>`_. Contributions of all kinds — code,
documentation, examples, and feedback — are warmly welcomed; see the **Contributing**
section for how to get involved.

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
