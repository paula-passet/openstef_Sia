User Guide Overview
===================

Welcome to the OpenSTEF user guide! This section provides everything you need to get started with OpenSTEF and use it effectively in your energy forecasting projects.

.. important::
   **OpenSTEF is a Python library, not a deployable application.** It provides the building blocks for creating energy forecasting systems, but you need to integrate it into your own applications or workflows.

What You'll Find Here
---------------------

This user guide is organized to take you from first installation to advanced usage:

**Getting Started**
   - :doc:`intro/index` - Understanding what OpenSTEF is and what it can do for you
   - :doc:`installation` - Installing OpenSTEF and its dependencies
   - :doc:`quick_start` - Your fastest path from installation to first forecast

**Learning OpenSTEF**
   - :doc:`tutorials` - Comprehensive step-by-step tutorials covering first use, backtesting, and advanced topics

**Reference Materials**
   - :doc:`../api/index` - Complete API documentation
   - :doc:`../examples` - Jupyter notebook examples
   - :doc:`../faq` - Frequently asked questions

Prerequisites
-------------

Before diving into OpenSTEF, you should have:

- **Python 3.8 or higher** installed on your system
- **Basic pandas knowledge** for data manipulation
- **Understanding of time series concepts** like forecasting horizons and temporal resolution
- **Energy domain familiarity** (helpful but not required)

Quick Navigation
----------------

.. grid:: 2

   .. grid-item-card:: New to OpenSTEF?
      :link: intro/index
      :link-type: doc

      Start here to understand what OpenSTEF is, what it's not, and how it fits into energy forecasting workflows.

   .. grid-item-card:: Ready to Code?
      :link: quick_start
      :link-type: doc

      Jump straight to creating your first forecast in under 10 minutes.

   .. grid-item-card:: Want to Learn More?
      :link: tutorials
      :link-type: doc

      Follow comprehensive tutorials covering everything from basic usage to advanced customization.

   .. grid-item-card:: Need Help?
      :link: ../faq
      :link-type: doc

      Check our FAQ for answers to common questions and troubleshooting tips.

What OpenSTEF Provides
----------------------

OpenSTEF gives you the essential components for energy forecasting:

- **Probabilistic forecasts** with quantile predictions for uncertainty estimation
- **Multiple ML models** including XGBoost, LightGBM, and linear models with automatic selection
- **Energy-specific features** like weather dependencies, temporal patterns, and load characteristics
- **Backtesting framework** for validating model performance on historical data
- **Custom workflows** for integrating with your existing data pipelines and applications

.. toctree::
   :maxdepth: 2
   :hidden:

   intro/index
   installation
   quick_start
   tutorials