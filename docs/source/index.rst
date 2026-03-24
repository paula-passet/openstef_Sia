Based on the search results, I can generate the complete RST page for the OpenSTEF landing page (index.rst) following the editorial plan specifications. Here's the comprehensive documentation:

```rst
OpenSTEF Documentation
======================

OpenSTEF is an open-source Python library for short-term energy forecasting. It provides the building blocks for training and running forecasting models — it is not a deployable application or pre-trained model.

.. note::
   **OpenSTEF is a machine learning library, not a full-stack application.** You use OpenSTEF to build your own forecasting applications by integrating it into your existing systems and workflows.

What OpenSTEF Can Do
--------------------

OpenSTEF provides comprehensive tools for energy forecasting:

• **Probabilistic forecasts** with confidence intervals and quantile predictions
• **Multiple ML models** including XGBoost, LightGBM, and linear models with automatic selection
• **Custom workflows** for training, forecasting, and evaluation pipelines
• **Backtesting capabilities** for model validation and performance assessment
• **Feature engineering** with energy-specific transformations and predictors
• **Data validation** to ensure forecast quality and reliability
• **Explainability features** to understand model behavior and feature importance

.. [DIAGRAM: High-level architecture showing OpenSTEF as library component in user application]

Architecture Overview
---------------------

OpenSTEF V4 is structured as a modular mono-repo with multiple self-contained packages:

**Core Modules:**

• **openstef-core** - Data types, interfaces, and base classes
• **openstef-models** - Forecasting models and data preprocessing pipelines  
• **openstef-meta** - Modern ensemble models and advanced architectures
• **openstef-beam** - Backtesting, evaluation, analysis, and metrics

**Key Components:**

• **Prediction Jobs** - Input configuration for forecasting tasks and pipelines
• **Tasks** - Perform training, forecasting, or evaluation with database integration
• **Pipelines** - Core ML workflows that can be used directly with your own data
• **Data Validation** - Automated checks for data quality (e.g., detecting flatliners)
• **Feature Engineering** - Automatic feature selection and creation based on configuration
• **Machine Learning** - Training, forecasting, and evaluation based on prediction job settings

Getting Started
---------------

**Prerequisites:**
- Python 3.8+
- Basic knowledge of pandas and time series concepts

**Quick Links:**

• `Installation Guide <user_guide/installation.html>`_ - Install OpenSTEF and dependencies
• `Quick Start <user_guide/quick_start.html>`_ - Zero to forecast in under 10 minutes
• `Tutorials <user_guide/tutorials.html>`_ - Comprehensive step-by-step guides
• `API Reference <api/index.html>`_ - Complete API documentation
• `Use Cases <use_cases/index.html>`_ - Real-world forecasting applications
• `Examples <examples.html>`_ - Jupyter notebooks and code samples

Use Cases
---------

OpenSTEF supports diverse energy forecasting applications:

• **Congestion Management** - Predict when grid capacity will be exceeded
• **Transport Forecasts** - Total load transport prediction for grid operators
• **Grid Loss Forecasting** - Technical loss prediction with cost optimization
• **District Heating** - Thermal demand forecasting for heating systems
• **Free Space Estimation** - Available capacity on grid connections

Each use case has specific accuracy requirements, optimization targets, and aggregation characteristics tailored to different business contexts.

Installation
------------

Install OpenSTEF from PyPI:

.. code-block:: bash

   pip install openstef

For development or advanced features:

.. code-block:: bash

   # Install with optional dependencies
   pip install openstef[dev,docs]

See the `Installation Guide <user_guide/installation.html>`_ for detailed setup instructions and dependency management.

Community and Support
---------------------

**Get Help:**
- `GitHub Discussions <https://github.com/OpenSTEF/openstef/discussions>`_ - Ask questions and share ideas
- `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ - Report bugs and request features
- `LF Energy Project Page <https://www.lfenergy.org/projects/openstef/>`_ - Official project information

**Stay Connected:**
- Join our Teams channel for real-time discussions
- Watch our `project video <https://www.lfenergy.org/projects/openstef/>`_ for an overview
- Follow updates on the `project website <https://openstef.github.io/openstef/>`_

Contributing
------------

We welcome contributions! Please read:

• `CONTRIBUTING.md <https://github.com/OpenSTEF/openstef/blob/main/CONTRIBUTING.md>`_ - Development process and guidelines
• `CODE_OF_CONDUCT.md <https://github.com/OpenSTEF/openstef/blob/main/CODE_OF_CONDUCT.md>`_ - Community standards
• `PROJECT_GOVERNANCE.md <https://github.com/OpenSTEF/openstef/blob/main/PROJECT_GOVERNANCE.md>`_ - Project governance model

License
-------

This project is licensed under the Mozilla Public License, version 2.0. See `LICENSE <https://github.com/OpenSTEF/openstef/blob/main/LICENSE>`_ for details.

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: User Guide

   user_guide/index
   user_guide/installation
   user_guide/quick_start
   user_guide/tutorials

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Use Cases & Architecture

   use_cases/index
   architecture/index
   architecture/repo_structure

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Reference

   api/index
   how_to_guides/index
   concepts/index
   faq
   examples
   changelog

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Community

   contribute/index
```