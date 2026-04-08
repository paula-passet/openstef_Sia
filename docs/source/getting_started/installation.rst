Installation
============

This guide covers everything you need to install OpenSTEF, a Python library for short-term energy forecasting. OpenSTEF 4.0 uses a modular architecture that lets you install only the components you need, from a minimal core to the full suite of forecasting tools.

System Requirements
===================

Before installing OpenSTEF, ensure your system meets these requirements:

* **Python 3.12 or higher** (Python 3.13 supported)
* **64-bit operating system** (Windows, macOS, or Linux)
* **pip** or **uv** package manager

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x.

Check your Python version:

.. code-block:: bash

   python --version

If you need to upgrade Python, visit `python.org <https://www.python.org/downloads/>`_ or use your system's package manager.

Installation Options
====================

OpenSTEF's modular design provides several installation options depending on your needs.

Complete Installation (Recommended)
------------------------------------

For most users, install all OpenSTEF packages at once:

.. code-block:: bash

   pip install "openstef[all]"

This installs:

* ``openstef-core`` - Core utilities and datasets
* ``openstef-models`` - Forecasting models and training pipelines
* ``openstef-beam`` - Backtesting and evaluation tools

If you're using **uv** as your package manager:

.. code-block:: bash

   uv add "openstef[all]"

Individual Package Installation
--------------------------------

Install only what you need for your specific use case:

**Core utilities and datasets only:**

.. code-block:: bash

   pip install openstef-core

**Forecasting models only:**

.. code-block:: bash

   pip install openstef-models

This is the most common choice for production forecasting. It includes the core package as a dependency.

**Backtesting and evaluation tools:**

.. code-block:: bash

   pip install openstef-beam

Use this if you want to evaluate and compare different forecasting approaches.

**Meta-package with models (default):**

.. code-block:: bash

   pip install openstef

This installs ``openstef-models`` and its dependencies, providing a complete forecasting solution.

Selective Installation with Extras
-----------------------------------

Mix and match components using the meta-package extras:

.. code-block:: bash

   # Models + BEAM
   pip install "openstef[beam]"

   # All packages
   pip install "openstef[all]"

Optional Dependencies
=====================

Some OpenSTEF features require additional dependencies that aren't installed by default to keep the base installation lightweight.

Machine Learning Backends
--------------------------

OpenSTEF supports multiple machine learning frameworks. The default installation includes XGBoost, but you may want additional backends:

.. code-block:: bash

   # LightGBM support
   pip install lightgbm

   # TensorFlow/Keras support
   pip install tensorflow

Visualization Tools
-------------------

For plotting and visualization features:

.. code-block:: bash

   pip install matplotlib seaborn plotly

Database Connectors
-------------------

If you're loading data from databases:

.. code-block:: bash

   # PostgreSQL
   pip install psycopg2-binary

   # MySQL
   pip install pymysql

   # InfluxDB
   pip install influxdb-client

Verifying Your Installation
============================

After installation, verify that OpenSTEF is correctly installed and accessible.

Basic Verification
------------------

Import the library and check the version:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

If you installed the BEAM package:

.. code-block:: python

   import openstef_beam
   print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")

Functional Verification
-----------------------

Test that core functionality works by loading a sample dataset:

.. code-block:: python

   from openstef_models.datasets import load_aemo

   # Load a sample dataset
   data = load_aemo()
   print(f"Loaded {len(data)} rows of data")
   print(data.head())

This should display the first few rows of the AEMO dataset without errors.

Run a Quick Forecast
--------------------

Verify the complete installation by running a minimal forecast:

.. code-block:: python

   from openstef_models.datasets import load_aemo
   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   from openstef_models.preprocessing import add_features

   # Load and prepare data
   data = load_aemo()
   data = add_features(data)

   # Split into train/test
   train = data[:"2020-12-31"]
   test = data["2021-01-01":]

   # Train a model
   model = XGBQuantileOpenstfRegressor()
   model.fit(train.drop(columns=["demand"]), train["demand"])

   # Make predictions
   predictions = model.predict(test.drop(columns=["demand"]))
   print(f"Generated {len(predictions)} predictions")

If this runs without errors, your installation is working correctly. For a more detailed introduction to forecasting, see the :doc:`quickstart` guide.

Troubleshooting
===============

Common installation issues and their solutions.

ImportError: No module named 'openstef_models'
-----------------------------------------------

**Problem:** Python can't find the OpenSTEF package.

**Solutions:**

1. Verify installation in the correct environment:

   .. code-block:: bash

      pip list | grep openstef

2. Ensure you're using the correct Python interpreter:

   .. code-block:: bash

      which python
      python -m pip list | grep openstef

3. If using a virtual environment, make sure it's activated.

Version Conflicts
-----------------

**Problem:** Dependency version conflicts during installation.

**Solutions:**

1. Use a fresh virtual environment:

   .. code-block:: bash

      python -m venv openstef-env
      source openstef-env/bin/activate  # On Windows: openstef-env\Scripts\activate
      pip install "openstef[all]"

2. Upgrade pip before installing:

   .. code-block:: bash

      pip install --upgrade pip
      pip install "openstef[all]"

3. Use uv for faster dependency resolution:

   .. code-block:: bash

      pip install uv
      uv pip install "openstef[all]"

Slow Installation
-----------------

**Problem:** Installation takes a long time or appears to hang.

**Solutions:**

1. Use uv for significantly faster installation:

   .. code-block:: bash

      pip install uv
      uv pip install "openstef[all]"

2. Install binary wheels instead of building from source:

   .. code-block:: bash

      pip install --only-binary :all: "openstef[all]"

3. Use a faster PyPI mirror if you're in a region with slow connectivity.

Platform-Specific Issues
------------------------

**Windows:**

* Some scientific packages may require Microsoft Visual C++ Build Tools
* Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
* Consider using Windows Subsystem for Linux (WSL) for better compatibility

**macOS:**

* Most installations work out of the box
* For Apple Silicon (M1/M2/M3), ensure you're using Python 3.12+ with native ARM support

**Linux:**

* Install Python development headers if you encounter compilation errors:

  .. code-block:: bash

     # Ubuntu/Debian
     sudo apt-get install python3-dev

     # RHEL/CentOS/Fedora
     sudo yum install python3-devel

Memory Errors During Installation
----------------------------------

**Problem:** Installation fails with memory errors, especially on resource-constrained systems.

**Solution:** Install packages sequentially instead of all at once:

.. code-block:: bash

   pip install openstef-core
   pip install openstef-models
   pip install openstef-beam

SSL Certificate Errors
-----------------------

**Problem:** SSL errors when downloading packages.

**Solutions:**

1. Update your system's CA certificates
2. Upgrade pip:

   .. code-block:: bash

      pip install --upgrade pip certifi

3. As a last resort (not recommended for production):

   .. code-block:: bash

      pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org "openstef[all]"

Getting Help
============

If you encounter issues not covered here:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for similar problems
2. Review the :doc:`../support` page for community resources
3. Open a new issue with details about your environment and the error message

Next Steps
==========

Now that OpenSTEF is installed:

* **Quick start:** Follow the :doc:`quickstart` guide for the fastest path to your first forecast
* **Detailed tutorial:** Work through :doc:`first_forecast` for a step-by-step introduction
* **Understand the library:** Read about OpenSTEF's architecture and capabilities in the main documentation

Staying Updated
===============

OpenSTEF follows semantic versioning. To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade "openstef[all]"

Check the `release notes <https://github.com/OpenSTEF/openstef/releases>`_ for information about new features, bug fixes, and breaking changes.