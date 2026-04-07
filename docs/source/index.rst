Welcome to OpenSTEF
===================

OpenSTEF is a Python library for creating short-term energy forecasts. It provides a complete machine learning pipeline—from data preprocessing and feature engineering to model training, forecasting, and evaluation—designed specifically for the energy sector. Short-term forecasting means predicting load hours to days ahead, enabling grid operators to manage congestion, plan transport capacity, and optimize operations.

OpenSTEF is model-agnostic and generates probabilistic forecasts with uncertainty estimates, not just single-point predictions. The library includes domain-specific feature engineering, such as transforming solar radiation and temperature data into photovoltaic generation estimates.

Who is OpenSTEF for?
---------------------

This library is built for data scientists, engineers, and researchers working in the energy sector. Whether you're at a distribution system operator managing grid congestion, a transmission operator coordinating transport forecasts, or a research team exploring forecasting methods, OpenSTEF provides the tools to build production-ready forecasting pipelines.

Getting started
---------------

If you're new to OpenSTEF, begin with the installation guide to set up the library in your environment. The user guide walks through core concepts and common workflows, while the examples demonstrate practical applications like congestion management and transport forecasting. For detailed technical information, consult the API reference.

Contributors can find guidance in the contributing section, including development workflows and coding standards. The community section provides information about the project's governance, maintainers, and how to connect with other users.

Community and support
---------------------

OpenSTEF is an LF Energy project maintained by a community of contributors. Report bugs or request features through the `GitHub issue tracker <https://github.com/OpenSTEF/openstef/issues>`_. Join the conversation in the OpenSTEF Slack workspace or attend bi-weekly community meetings, which are open to everyone. For more information about the project, visit the `LF Energy project page <https://www.lfenergy.org/projects/openstef/>`_.

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
