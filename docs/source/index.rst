OpenSTEF Documentation
======================

OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for
building accurate short-term load forecasts in the energy domain. It provides complete
machine learning pipelines — from data preprocessing and feature engineering through
model training, probabilistic forecasting, and evaluation — so you can focus on your
forecasting problem rather than the surrounding infrastructure.

.. note::

   OpenSTEF is a **library**, not a standalone application. You import it into your
   own Python code and integrate it into your existing workflows and systems.

Who Is It For?
--------------

OpenSTEF is built for data scientists and engineers working in the energy sector —
particularly those at grid operators, utilities, or research institutions who need
reliable short-term load forecasts for use cases such as congestion management,
transport forecasting, EV charging capacity estimation, and grid loss prediction.
Familiarity with Python and basic machine learning concepts is assumed, but no
prior energy-domain expertise is required to get started.

Where to Start
--------------

If you are new to OpenSTEF, the **Getting Started** section walks you through
installation and your first forecast in minutes. The **User Guide** then covers
the library's core concepts in depth — prediction jobs, pipelines, feature
engineering, and probabilistic outputs. When you are ready to integrate OpenSTEF
into a production system, the **API Reference** provides complete documentation
for every public module, class, and function. Finally, the **Examples** section
contains end-to-end notebooks demonstrating real-world forecasting scenarios,
including the Liander 2024 Energy Forecasting Benchmark dataset.

Quick Install
-------------

.. code-block:: python

   pip install openstef

Community & Support
-------------------

OpenSTEF is developed in the open. You can find the source code, report issues,
and contribute on `GitHub <https://github.com/OpenSTEF/openstef>`_. The project
is released on `PyPI <https://pypi.org/project/openstef/>`_ and welcomes
contributions of all kinds — bug reports, feature requests, and pull requests.

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
