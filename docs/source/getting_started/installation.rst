Installation
============

This guide covers everything you need to install OpenSTEF, a Python library for short-term energy forecasting. Whether you're installing for the first time or troubleshooting issues, you'll find the information you need here.

System Requirements
===================

Before installing OpenSTEF, ensure your system meets these requirements:

* **Python 3.12 or higher** (Python 3.13 supported)
* **64-bit operating system** (Windows, macOS, or Linux)
* **pip** or **uv** package manager

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10/3.11 support, consider using OpenSTEF 3.x.

Check your Python version:

.. code-block:: bash

   python --version

If you need to upgrade Python, visit `python.org <https://www.python.org/downloads/>`_ for installation instructions.

Quick Installation
==================

For most users, the simplest approach is to install the complete OpenSTEF package with all components:

.. code-block:: bash

   pip install "openstef[all]"

This installs all available OpenSTEF packages including forecasting models, backtesting tools, and utilities. After installation, verify it works:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

Once installed, proceed to the :doc:`quickstart` guide to create your first forecast.

Installation Options
====================

OpenSTEF's modular architecture allows you to install only what you need. The library consists of several packages that work together:

* **openstef-core**: Core utilities and datasets
* **openstef-models**: Forecasting models and pipelines
* **openstef-beam**: Backtesting and evaluation tools
* **openstef**: Meta-package that bundles components

Complete Installation
---------------------

Install everything (recommended for most users):

.. code-block:: bash

   pip install "openstef[all]"

This gives you access to all forecasting models, backtesting capabilities, and utilities.

Individual Package Installation
--------------------------------

Install only specific components:

.. code-block:: bash

   # Core forecasting models only
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Core utilities and datasets only
   pip install openstef-core

   # Meta-package with models (default)
   pip install openstef

Selective Installation with Extras
-----------------------------------

Mix and match components using the meta-package extras:

.. code-block:: bash

   # Models + BEAM
   pip install "openstef[beam]"

   # Just the models (equivalent to pip install openstef)
   pip install openstef

Using uv Package Manager
=========================

OpenSTEF 4.0 supports `uv <https://docs.astral.sh/uv/>`_, a fast Rust-based Python package manager. While pip works perfectly fine, uv offers faster dependency resolution and better reproducibility.

Installing uv
-------------

Install uv first if you want to use it:

**macOS and Linux:**

.. code-block:: bash

   curl -LsSf https://astral.sh/uv/install.sh | sh

**Windows (PowerShell):**

.. code-block:: powershell

   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

**Using pipx:**

.. code-block:: bash

   pipx install uv

**Using pip:**

.. code-block:: bash

   pip install uv

For more installation options, see the `uv installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_.

Installing OpenSTEF with uv
----------------------------

Once uv is installed, use it to install OpenSTEF:

.. code-block:: bash

   # Complete installation
   uv add "openstef[all]"

   # Individual packages
   uv add openstef-models
   uv add openstef-beam

   # Selective extras
   uv add "openstef[beam]"

Virtual Environments
====================

We strongly recommend using virtual environments to isolate OpenSTEF and its dependencies from other Python projects.

Using venv (built-in)
---------------------

.. code-block:: bash

   # Create virtual environment
   python -m venv openstef-env

   # Activate it
   # On macOS/Linux:
   source openstef-env/bin/activate
   # On Windows:
   openstef-env\Scripts\activate

   # Install OpenSTEF
   pip install "openstef[all]"

Using uv
--------

uv automatically manages virtual environments:

.. code-block:: bash

   # Create a new project with OpenSTEF
   uv init my-forecast-project
   cd my-forecast-project
   uv add "openstef[all]"

   # Run Python with the environment
   uv run python your_script.py

Verifying Your Installation
============================

After installation, verify that OpenSTEF is working correctly:

Basic Import Test
-----------------

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # If you installed openstef-beam:
   import openstef_beam
   print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")

Check Available Models
----------------------

.. code-block:: python

   from openstef_models.model.model_creator import ModelCreator

   # List available model types
   available_models = ModelCreator.get_available_models()
   print("Available models:", available_models)

Run a Simple Forecast
---------------------

.. code-block:: python

   from openstef_models.model.model_creator import ModelCreator
   import pandas as pd
   import numpy as np

   # Create sample data
   n_samples = 100
   data = pd.DataFrame({
       'load': np.random.rand(n_samples) * 100,
       'temp': np.random.rand(n_samples) * 30,
   })

   # Create and train a model
   model = ModelCreator.create_model(model_type='xgb')
   model.fit(data[['temp']], data['load'])

   # Make predictions
   predictions = model.predict(data[['temp']])
   print(f"Generated {len(predictions)} predictions")

If this runs without errors, your installation is working correctly.

Troubleshooting
===============

Installation Fails with Dependency Conflicts
---------------------------------------------

If you encounter dependency conflicts, try installing in a fresh virtual environment:

.. code-block:: bash

   # Create a new clean environment
   python -m venv fresh-env
   source fresh-env/bin/activate  # or fresh-env\Scripts\activate on Windows
   pip install --upgrade pip
   pip install "openstef[all]"

If using uv, try:

.. code-block:: bash

   uv sync --reinstall

Import Errors After Installation
---------------------------------

If you can install but can't import OpenSTEF:

1. **Check you're in the right environment:**

   .. code-block:: bash

      which python  # macOS/Linux
      where python  # Windows

2. **Verify the package is installed:**

   .. code-block:: bash

      pip list | grep openstef

3. **Try reinstalling:**

   .. code-block:: bash

      pip uninstall openstef openstef-models openstef-beam openstef-core
      pip install "openstef[all]"

Missing System Dependencies
----------------------------

Some scientific packages require system-level dependencies:

**Ubuntu/Debian:**

.. code-block:: bash

   sudo apt-get update
   sudo apt-get install python3-dev build-essential

**RHEL/CentOS:**

.. code-block:: bash

   sudo yum install python3-devel gcc gcc-c++

**macOS:**

Most installations work out of the box. If you encounter issues, ensure Xcode Command Line Tools are installed:

.. code-block:: bash

   xcode-select --install

**Windows:**

Some packages may require Microsoft Visual C++ Build Tools. Download from `Microsoft's website <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_.

Memory Errors During Installation
----------------------------------

If installation fails due to memory issues (common on small VMs):

.. code-block:: bash

   # Install with no cache
   pip install --no-cache-dir "openstef[all]"

Slow Installation
-----------------

If pip is slow, try uv for faster dependency resolution:

.. code-block:: bash

   pip install uv
   uv pip install "openstef[all]"

SSL Certificate Errors
-----------------------

If you encounter SSL errors behind a corporate firewall:

.. code-block:: bash

   # Temporary workaround (not recommended for production)
   pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org "openstef[all]"

Better solution: configure your corporate SSL certificates properly or use a package mirror.

Platform-Specific Notes
=======================

Windows
-------

* Use PowerShell or Command Prompt for installation commands
* Consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ for best compatibility with scientific Python packages
* Ensure you have Microsoft Visual C++ Build Tools if you encounter compilation errors

macOS
-----

* Most installations work out of the box
* For Apple Silicon (M1/M2/M3), all packages should work natively
* If you encounter issues, ensure you're using the native ARM64 Python, not x86_64 via Rosetta

Linux
-----

* Most distributions work out of the box
* Ensure development headers are installed (python3-dev or python3-devel)
* For containerized deployments, use official Python base images

Upgrading OpenSTEF
==================

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade "openstef[all]"

To upgrade to a specific version:

.. code-block:: bash

   pip install "openstef[all]==4.1.0"

Check your current version:

.. code-block:: python

   import openstef_models
   print(openstef_models.__version__)

.. note::
   OpenSTEF follows semantic versioning. Major version changes (e.g., 3.x to 4.x) may include breaking changes. Always check the changelog before upgrading.

Uninstalling
============

To completely remove OpenSTEF:

.. code-block:: bash

   pip uninstall openstef openstef-models openstef-beam openstef-core

Getting Help
============

If you encounter issues not covered here:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for similar problems
2. Review the :doc:`../support/index` page for community resources
3. Ask questions in our community channels
4. Contact us at openstef@lfenergy.org

Next Steps
==========

Now that OpenSTEF is installed:

* **Start forecasting**: Follow the :doc:`quickstart` guide for a minimal working example
* **Learn the basics**: Work through :doc:`first_forecast` for a detailed tutorial
* **Evaluate models**: See :doc:`backtesting` to compare different forecasting approaches
* **Customize your workflow**: Explore :doc:`advanced_customization` for power user features