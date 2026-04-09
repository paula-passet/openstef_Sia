Installation
============

This guide covers how to install OpenSTEF, a Python library for short-term energy forecasting. OpenSTEF 4.0 features a modular architecture that lets you install only the components you need, from core utilities to complete forecasting pipelines.

System Requirements
===================

Before installing OpenSTEF, ensure your system meets these requirements:

* **Python 3.12 or higher** (Python 3.13 supported)
* **64-bit operating system** (Windows, macOS, or Linux)
* **pip** or **uv** package manager

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

Check your Python version:

.. code-block:: bash

   python --version

If you need to upgrade Python, download the latest version from `python.org <https://www.python.org/downloads/>`_ or use your system's package manager.

Installation Methods
====================

OpenSTEF can be installed using either **pip** (the standard Python package manager) or **uv** (a faster, Rust-based alternative). Both methods are fully supported.

Quick Install
-------------

For most users, the recommended approach is to install all OpenSTEF components:

.. code-block:: bash

   pip install "openstef[all]"

This installs the complete OpenSTEF suite including:

* ``openstef-core``: Core utilities and datasets
* ``openstef-models``: Forecasting models and training pipelines
* ``openstef-beam``: Backtesting and evaluation tools

After installation, verify it works:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

Once installed, see the :doc:`quickstart` guide for your first forecast.

Modular Installation
====================

OpenSTEF's modular design allows fine-grained control over what you install. This is useful for production environments, containerized deployments, or when you only need specific functionality.

Individual Packages
-------------------

Install only the packages you need:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Core forecasting models only
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Meta-package with models (default)
   pip install openstef

The meta-package ``openstef`` installs ``openstef-models`` by default. Use extras to add more components.

Selective Installation with Extras
-----------------------------------

Mix and match components using the meta-package with extras:

.. code-block:: bash

   # Models + BEAM (backtesting)
   pip install "openstef[beam]"

   # Models + Foundational models (when available)
   pip install "openstef[foundational]"

   # Everything
   pip install "openstef[all]"

This approach is ideal when you want the core forecasting functionality plus specific additional tools.

Using uv (Alternative)
======================

`uv <https://docs.astral.sh/uv/>`_ is a fast, modern Python package manager that OpenSTEF 4.0 uses internally for development. It's optional for end users but offers faster dependency resolution and better reproducibility.

Installing uv
-------------

Install uv using the recommended method for your platform:

**macOS and Linux:**

.. code-block:: bash

   curl -LsSf https://astral.sh/uv/install.sh | sh

**Windows:**

.. code-block:: powershell

   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

**Using pipx:**

.. code-block:: bash

   pipx install uv

**Using pip:**

.. code-block:: bash

   pip install uv

For more options, see the `uv installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_.

Installing OpenSTEF with uv
----------------------------

Once uv is installed, use it to add OpenSTEF to your project:

.. code-block:: bash

   # Complete installation
   uv add "openstef[all]"

   # Individual packages
   uv add openstef-core
   uv add openstef-models
   uv add openstef-beam

   # With extras
   uv add "openstef[beam]"

The ``uv add`` command automatically manages your project's dependencies and virtual environment.

Verifying Your Installation
============================

After installation, verify that OpenSTEF is working correctly:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # If you installed openstef-beam
   import openstef_beam
   print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")

   # If you installed openstef-core
   import openstef_core
   print(f"OpenSTEF Core version: {openstef_core.__version__}")

You can also run a quick smoke test to ensure the library can train a model:

.. code-block:: python

   from openstef_models.model.regressors.xgb import XGBOpenstfRegressor
   from openstef_core.datasets import load_elia

   # Load sample data
   data = load_elia()
   
   # Create and verify model
   model = XGBOpenstfRegressor()
   print(f"Model created: {model.__class__.__name__}")

If these commands run without errors, your installation is ready. Continue to the :doc:`quickstart` guide to make your first forecast.

Troubleshooting
===============

This section covers common installation issues and their solutions.

Import Errors After Installation
---------------------------------

**Problem:** You get ``ModuleNotFoundError`` when importing OpenSTEF packages.

**Solution:** Ensure you're using the correct Python environment where OpenSTEF was installed. Check your active environment:

.. code-block:: bash

   python -c "import sys; print(sys.prefix)"

If you're using virtual environments, activate the correct one before importing.

Dependency Conflicts
--------------------

**Problem:** pip reports dependency conflicts during installation.

**Solution:** Create a fresh virtual environment to avoid conflicts with existing packages:

.. code-block:: bash

   python -m venv openstef-env
   source openstef-env/bin/activate  # On Windows: openstef-env\Scripts\activate
   pip install "openstef[all]"

Alternatively, use uv which has better dependency resolution:

.. code-block:: bash

   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv add "openstef[all]"

Python Version Mismatch
-----------------------

**Problem:** Installation fails with messages about Python version requirements.

**Solution:** OpenSTEF 4.0 requires Python 3.12 or higher. Check your version:

.. code-block:: bash

   python --version

If you have an older version, either upgrade Python or use OpenSTEF 3.x which supports Python 3.10 and 3.11.

Missing Optional Dependencies
------------------------------

**Problem:** You get ``MissingExtraError`` when using certain features.

**Solution:** Some OpenSTEF features require optional dependencies. Install the relevant extra:

.. code-block:: bash

   # If you need backtesting tools
   pip install "openstef[beam]"

   # Or install all optional dependencies
   pip install "openstef[all]"

The error message will indicate which extra is needed.

Installation Hangs or Is Very Slow
-----------------------------------

**Problem:** pip takes a very long time to resolve dependencies.

**Solution:** Use uv instead, which is significantly faster:

.. code-block:: bash

   pip install uv
   uv add "openstef[all]"

Alternatively, upgrade pip to the latest version:

.. code-block:: bash

   pip install --upgrade pip

Permission Errors
-----------------

**Problem:** Installation fails with permission denied errors.

**Solution:** Don't use ``sudo`` with pip. Instead, install in a virtual environment or use the ``--user`` flag:

.. code-block:: bash

   pip install --user "openstef[all]"

Better practice is to always use virtual environments:

.. code-block:: bash

   python -m venv myenv
   source myenv/bin/activate
   pip install "openstef[all]"

Development Installation
========================

If you want to modify OpenSTEF's source code or contribute to the project, you'll need a development installation. This is different from a regular installation and includes additional tools for testing and documentation.

Prerequisites
-------------

* `uv <https://docs.astral.sh/uv/>`_ (recommended) or pip
* Git

Clone and Install
-----------------

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install in development mode with all dependencies
   uv sync --all-extras --dev

   # Verify installation
   uv run pytest

This installs:

* All OpenSTEF packages in editable mode
* Development tools (linting, testing, documentation)
* Pre-commit hooks for code quality

Package-Specific Development
-----------------------------

To work on individual packages within the monorepo:

.. code-block:: bash

   # Install specific package in development mode
   cd packages/openstef-models
   uv pip install -e .

   # Or install with development dependencies
   uv sync --dev

For detailed contribution guidelines, see the project's ``CONTRIBUTING.md`` file in the repository.

Next Steps
==========

Now that OpenSTEF is installed, you're ready to start forecasting:

* **Quick start:** See the :doc:`quickstart` guide for the fastest path to your first forecast
* **Detailed tutorial:** Follow the :doc:`first_forecast` guide for a step-by-step walkthrough with explanations
* **Evaluate models:** Learn how to compare different forecasting approaches in the :doc:`backtesting` tutorial
* **Advanced usage:** Explore customization options in the :doc:`advanced_customization` guide