Now I'll create the complete index.rst page for OpenSTEF documentation:

==============================
OpenSTEF Documentation
==============================

Welcome to OpenSTEF, a Python machine learning library for short-term energy forecasting. OpenSTEF provides a complete framework for building, training, and deploying forecasting models that predict energy loads hours to days ahead.

What is OpenSTEF?
------------------

OpenSTEF is designed to address the growing complexity of modern electricity grids, where renewable energy sources, electric vehicles, and heat pumps create new challenges for grid operators. The library offers:

- **Complete ML Pipeline**: Data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing
- **Probabilistic Forecasts**: Generate forecasts with uncertainty bands, not just point predictions  
- **Domain-Specific Features**: Built-in energy sector knowledge, including solar radiation to PV generation estimates
- **Model Agnostic**: Works with various machine learning algorithms including XGBoost, LightGBM, and linear models
- **Multiple Use Cases**: Congestion forecasting, transport forecasts, grid loss prediction, and capacity estimation

The library handles typical machine learning tasks automatically while allowing customization for specific requirements. Whether you're forecasting load for a single transformer or managing grid-wide congestion, OpenSTEF provides the tools you need.

Getting Started
---------------

New to OpenSTEF? Start with our :doc:`getting_started/quickstart` to train your first model and create a forecast in minutes. For a deeper understanding, work through the comprehensive :doc:`getting_started/tutorials` that cover everything from basic usage to advanced customization.

If you're unsure which forecasting approach fits your needs, browse our :doc:`guides/use_cases` to compare different applications and find the right match for your project.

Installation
------------

Install OpenSTEF from PyPI:

.. code-block:: bash

   pip install openstef

For development installations and additional requirements, see the quickstart guide.

Community and Support
---------------------

OpenSTEF is developed by Alliander and the open-source community. Join our discussions, contribute to development, or get help:

- **Community Meetings**: Four-weekly meetings open to all interested users
- **Teams Channel**: Direct support and community discussion
- **GitHub Issues**: Bug reports and feature requests
- **Contributing**: Code contributions welcome - see our contributing guidelines

Find all community information and meeting links in our community documentation.

.. toctree::
   :maxdepth: 1
   :caption: Contents

   getting_started/quickstart
   getting_started/tutorials
   guides/use_cases
   guides/how_to_guides
   guides/faq
   reference/architecture
   reference/concepts
   reference/changelog
   api/index