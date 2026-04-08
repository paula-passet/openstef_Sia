Installation
============

This guide covers everything you need to install OpenSTEF on your system. OpenSTEF is a Python library for short-term energy forecasting, designed with a modular architecture that lets you install only the components you need.

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

Installation Options
====================

OpenSTEF's modular design allows you to install exactly what you need. The library consists of several packages that can be installed independently or together.

Quick Installation (Recommended)
---------------------------------

For most users, the simplest approach is to install all components:

.. code-block:: bash

   pip install "openstef[all]"

This installs all available packages: ``openstef-models`` and ``openstef-beam``.

If you're using uv as your package manager:

.. code-block:: bash

   uv add "openstef[all]"

Individual Package Installation
--------------------------------

Install only the packages you need:

**Core forecasting models:**

.. code-block:: bash

   pip install openstef-models

This is the main package containing forecasting algorithms and model training utilities.

**Backtesting and evaluation tools:**

.. code-block:: bash

   pip install openstef-beam

This package provides tools for comparing model performance and running backtests.

**Meta-package with models (default):**

.. code-block:: bash

   pip install openstef

This installs the base meta-package with ``openstef-models`` included.

Selective Installation with Extras
-----------------------------------

Mix and match components using the meta-package extras:

.. code-block:: bash

   # Models + BEAM
   pip install "openstef[beam]"

   # All components
   pip install "openstef[all]"

Using uv Package Manager
-------------------------

OpenSTEF 4.0 supports `uv <https://docs.astral.sh/uv/>`_, a fast Rust-based Python package manager. While pip works perfectly fine, uv offers faster dependency resolution and better reproducibility.

Install uv first:

**macOS and Linux:**

.. code-block:: bash

   curl -LsSf https://astral.sh/uv/install.sh | sh

**Windows (PowerShell):**

.. code-block:: powershell

   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

**Using pipx:**

.. code-block:: bash

   pipx install uv

Then install OpenSTEF:

.. code-block:: bash

   uv add "openstef[all]"

Virtual Environments
====================

We strongly recommend using a virtual environment to avoid dependency conflicts with other Python projects.

Using venv (Built-in)
---------------------

.. code-block:: bash

   # Create virtual environment
   python -m venv openstef-env

   # Activate on Linux/macOS
   source openstef-env/bin/activate

   # Activate on Windows
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

   # Run Python with the virtual environment
   uv run python your_script.py

Verifying Your Installation
============================

After installation, verify that OpenSTEF is working correctly:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # If you installed openstef-beam
   import openstef_beam
   print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")

Run a quick test to ensure the core functionality works:

.. code-block:: python

   from openstef_models.model.regressors.xgb import XGBOpenstfRegressor
   
   # Create a simple model instance
   model = XGBOpenstfRegressor()
   print("OpenSTEF is ready to use!")

If these commands execute without errors, your installation is successful.

Troubleshooting
===============

Common Installation Issues
--------------------------

**ImportError: No module named 'openstef'**

This usually means the installation didn't complete successfully. Try:

.. code-block:: bash

   pip install --upgrade "openstef[all]"

**Python version mismatch**

If you see errors about Python version requirements:

.. code-block:: bash

   # Check your Python version
   python --version
   
   # If you have multiple Python versions, specify explicitly
   python3.12 -m pip install "openstef[all]"

**Permission errors on Linux/macOS**

Avoid using ``sudo pip install``. Instead, use a virtual environment or install for your user:

.. code-block:: bash

   pip install --user "openstef[all]"

**SSL certificate errors**

If you encounter SSL errors during installation:

.. code-block:: bash

   pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org "openstef[all]"

**Dependency conflicts**

If pip reports dependency conflicts, try creating a fresh virtual environment:

.. code-block:: bash

   python -m venv fresh-env
   source fresh-env/bin/activate  # or fresh-env\Scripts\activate on Windows
   pip install "openstef[all]"

Platform-Specific Notes
-----------------------

**Windows**

* Use PowerShell or Command Prompt for installation commands
* Consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ for best compatibility
* Some scientific packages may require Microsoft Visual C++ Build Tools

**macOS**

* Most installations work out of the box
* For Apple Silicon (M1/M2/M3), ensure you're using compatible wheel distributions
* If you encounter issues, try installing with Rosetta 2 compatibility

**Linux**

* Most distributions work out of the box
* For Ubuntu/Debian, you may need development headers:

  .. code-block:: bash

     sudo apt-get install python3-dev

* For RHEL/CentOS:

  .. code-block:: bash

     sudo yum install python3-devel

Getting Help
------------

If you encounter issues not covered here:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for similar problems
2. Review the :doc:`../support/index` page for community resources
3. Open a new issue with details about your environment and error messages
4. Contact us at openstef@lfenergy.org

Upgrading OpenSTEF
==================

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade "openstef[all]"

To upgrade to a specific version:

.. code-block:: bash

   pip install "openstef[all]==4.1.0"

Check your installed version:

.. code-block:: python

   import openstef_models
   print(openstef_models.__version__)

.. note::
   OpenSTEF follows semantic versioning. Major version updates (e.g., 4.x to 5.x) may include breaking changes. Always review the changelog before upgrading.

Next Steps
==========

Now that OpenSTEF is installed, you're ready to start forecasting:

* **Quick start**: Follow the :doc:`quickstart` guide for the fastest path to your first forecast
* **Detailed tutorial**: Work through :doc:`first_forecast` for a step-by-step introduction with explanations
* **Explore examples**: Check out the example notebooks to see OpenSTEF in action
* **API reference**: Browse the API documentation to understand available models and utilities

For development workflows or contributing to OpenSTEF, see the development setup guide in the contributor documentation.