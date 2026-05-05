OpenSTEF Documentation
======================

OpenSTEF is a modular Python library for short-term energy forecasting in the power grid domain. It provides the full pipeline — from raw time series data to trained models and probabilistic forecasts — so that grid operators and data scientists can focus on their domain rather than boilerplate ML infrastructure.

Who is it for?
--------------

OpenSTEF is built for data scientists and engineers working on energy grid operations. If you need to forecast load, generation, or net offtake at substations or grid connections — and want a production-ready framework rather than a collection of scripts — OpenSTEF is designed for you.

Getting started
---------------

The best place to begin is the **Installation** page, which covers ``pip install openstef`` and the individual sub-packages (``openstef-core``, ``openstef-models``, ``openstef-beam``, and ``openstef-meta``) for when you only need part of the stack. From there, the **Quickstart** tutorial walks through a complete forecast from data loading to evaluation in a single notebook.

Once you are comfortable with the basics, the **User Guide** explains the core concepts — prediction jobs, feature engineering, model training, and backtesting — in depth. The **API Reference** provides the full, auto-generated documentation for every public class and function.

If you want to see realistic, runnable code before reading the narrative docs, head to the **Examples** section. Each example is a self-contained notebook using real benchmark data.

.. note::
   OpenSTEF requires Python >=3.12. See the Installation page for system requirements and optional dependencies such as LightGBM and XGBoost.

Community and support
---------------------

OpenSTEF is an open-source project hosted under the `LF Energy <https://lfenergy.org>`_ foundation.

- **Source code and issues:** `github.com/OpenSTEF <https://github.com/OpenSTEF>`_
- **Questions and discussion:** reach the team at `openstef@lfenergy.org <mailto:openstef@lfenergy.org>`_
- **Contributing:** see the ``CONTRIBUTING.md`` file in the repository for guidelines on submitting issues, pull requests, and new model integrations.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   getting_started/index
   api/index
