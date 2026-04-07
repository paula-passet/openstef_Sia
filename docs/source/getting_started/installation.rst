Installation
============

This guide covers everything you need to install OpenSTEF, from system requirements to troubleshooting common issues. Whether you're installing for the first time or setting up a specific configuration, you'll find the information you need here.

System Requirements
===================

Before installing OpenSTEF, ensure your system meets these requirements:

* **Python 3.12 or higher** (Python 3.13 supported)
* **64-bit operating system** (Windows, macOS, or Linux)
* **pip** or **uv** package manager

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x.

You can check your Python version with:

.. code-block:: bash

   python --version

Basic Installation
==================

The quickest way to get started is to install the complete OpenSTEF package with all components:

.. code-block:: bash

   pip install "openstef[all]"

This installs all available packages: ``openstef-core``, ``openstef-models``, and ``openstef-beam``.

If you prefer using uv (a fast, Rust-based Python package manager):

.. code-block:: bash

   uv pip install "openstef[all]"

Modular Installation
====================

OpenSTEF's modular architecture allows you to install only the components you need. This is useful for production environments where you want to minimize dependencies, or when you only need specific functionality.

Individual Packages
-------------------

Install packages individually based on your needs:

**Core utilities and datasets only:**

.. code-block:: bash

   pip install openstef-core

**Core forecasting models only:**

.. code-block:: bash

   pip install openstef-models

**Backtesting and evaluation tools only:**

.. code-block:: bash

   pip install openstef-beam

**Meta-package with models (default):**

.. code-block:: bash

   pip install openstef

Selective Installation with Extras
-----------------------------------

Mix and match components using the meta-package with extras:

.. code-block:: bash

   # Models + BEAM
   pip install "openstef[beam]"

   # All components
   pip install "openstef[all]"

This approach gives you fine-grained control over which components are installed while maintaining a single package reference.

Using uv Package Manager
========================

OpenSTEF 4.0 supports uv, a fast Python package manager that handles both dependency resolution and virtual environments. While pip works perfectly well, uv offers significantly faster installation times.

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

For more installation options, see the `uv installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_.

Using uv with OpenSTEF
----------------------

Once uv is installed, you can use it to install OpenSTEF:

.. code-block:: bash

   # Complete installation
   uv pip install "openstef[all]"

   # Individual packages
   uv pip install openstef-models
   uv pip install openstef-beam

   # In a project with uv
   uv add "openstef[all]"

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

You can also run a quick test to ensure the library is functioning:

.. code-block:: python

   from openstef_models.model.regressors.xgb import XGBOpenstef
   
   # Create a model instance
   model = XGBOpenstef()
   print("OpenSTEF is ready to use!")

Development Installation
========================

If you plan to contribute to OpenSTEF or modify the source code, you'll need a development installation. This installs the library in editable mode along with development tools.

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

To work on individual packages:

.. code-block:: bash

   # Install specific package in development mode
   cd packages/openstef-models
   uv pip install -e .

   # Or install with development dependencies
   uv sync --dev

Troubleshooting
===============

This section covers common installation issues and their solutions.

Missing Optional Dependencies
------------------------------

If you see an error like ``MissingExtraError: Optional package X is missing``, you need to install additional dependencies:

.. code-block:: bash

   # Install all optional features
   pip install "openstef[all]"

   # Or install the specific extra mentioned in the error
   pip install "openstef[beam]"

Python Version Issues
---------------------

**Error:** ``Requires Python >=3.12``

**Solution:** OpenSTEF 4.0 requires Python 3.12 or higher. Check your Python version:

.. code-block:: bash

   python --version

If you have an older version, either upgrade Python or use OpenSTEF 3.x which supports Python 3.10+.

Dependency Conflicts
--------------------

**Error:** Pip reports conflicting dependencies

**Solution:** Try installing in a clean virtual environment:

.. code-block:: bash

   # Create a new virtual environment
   python -m venv openstef-env
   
   # Activate it (Linux/macOS)
   source openstef-env/bin/activate
   
   # Activate it (Windows)
   openstef-env\Scripts\activate
   
   # Install OpenSTEF
   pip install "openstef[all]"

Alternatively, use uv which has better dependency resolution:

.. code-block:: bash

   uv venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   uv pip install "openstef[all]"

Installation Timeout
--------------------

**Error:** Installation times out or is very slow

**Solution:** Try using uv for faster installation:

.. code-block:: bash

   pip install uv
   uv pip install "openstef[all]"

Or increase pip's timeout:

.. code-block:: bash

   pip install --timeout=300 "openstef[all]"

Import Errors After Installation
---------------------------------

**Error:** ``ModuleNotFoundError: No module named 'openstef_models'``

**Solution:** Ensure you're using the correct Python environment where OpenSTEF was installed:

.. code-block:: bash

   # Check which Python is being used
   which python  # Linux/macOS
   where python  # Windows
   
   # Verify OpenSTEF is installed
   pip list | grep openstef

If the package isn't listed, reinstall it in the current environment.

Platform-Specific Issues
------------------------

**macOS:** If you encounter issues with XGBoost or other compiled dependencies, ensure you have Xcode command line tools:

.. code-block:: bash

   xcode-select --install

**Windows:** Some dependencies may require Microsoft Visual C++ Build Tools. Download from the `Microsoft website <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_.

**Linux:** Ensure you have Python development headers:

.. code-block:: bash

   # Debian/Ubuntu
   sudo apt-get install python3-dev
   
   # Red Hat/CentOS
   sudo yum install python3-devel

Next Steps
==========

Now that OpenSTEF is installed, you're ready to create your first forecast:

* **Quick Start:** See the :doc:`quickstart` guide for the fastest path to your first forecast
* **Detailed Tutorial:** Follow the :doc:`first_forecast` tutorial for a step-by-step walkthrough
* **API Reference:** Explore the full API documentation for detailed information on all components

If you encounter issues not covered in this guide, please check the `GitHub issues <https://github.com/OpenSTEF/openstef/issues>`_ or open a new issue with details about your environment and the error you're experiencing.