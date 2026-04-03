Installation
============

This guide covers everything you need to install OpenSTEF, a Python library for short-term energy forecasting. Whether you're getting started with a simple installation or setting up a development environment, you'll find the information you need here.

System Requirements
-------------------

Before installing OpenSTEF, ensure your system meets these requirements:

- **Python 3.12 or higher** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, or Linux)
- **pip** or **uv** package manager

.. note::

   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x.

You can check your Python version with:

.. code-block:: bash

   python --version

Quick Installation
------------------

For most users, the simplest way to get started is to install the meta-package:

.. code-block:: bash

   pip install openstef

This installs the ``openstef`` meta-package, which includes ``openstef-core`` and ``openstef-models`` - everything you need for basic forecasting tasks.

If you prefer using **uv** (a fast, modern Python package manager):

.. code-block:: bash

   uv add openstef

Understanding OpenSTEF's Modular Architecture
----------------------------------------------

OpenSTEF 4.0 follows a modular design with specialized packages that you can install independently or together:

- **openstef-core**: Core utilities, data structures, and datasets
- **openstef-models**: Forecasting models and training pipelines
- **openstef-beam**: Backtesting and evaluation tools (BEAM = Backtesting, Evaluation, and Monitoring)
- **openstef**: Meta-package that bundles core and models

This modular approach lets you install only what you need, keeping your environment lightweight.

Installation Options
--------------------

Choose Your Installation Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Complete Installation (Recommended for Most Users)**

Install all available packages for the full OpenSTEF experience:

.. code-block:: bash

   pip install "openstef[all]"

This installs all available packages: ``openstef-models`` and ``openstef-beam``.

**Individual Package Installation**

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

**Selective Installation with Extras**

Mix and match components using the meta-package extras:

.. code-block:: bash

   # Models + BEAM for backtesting
   pip install "openstef[beam]"

   # Models + Foundational models (when available)
   pip install "openstef[foundational-models]"

   # Multiple extras
   pip install "openstef[beam,foundational-models]"

**Installation by Use Case**

Here are recommended installations for common scenarios:

- **Research & Experimentation**: ``pip install "openstef[all]"`` - Full toolkit for analysis
- **Production Forecasting**: ``pip install openstef-models`` - Lightweight core models
- **Model Evaluation**: ``pip install "openstef[beam]"`` - Models + evaluation tools
- **Basic Development**: ``pip install openstef`` - Core functionality

Alternative Package Managers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF supports multiple package managers:

**Using conda:**

.. code-block:: bash

   conda install -c conda-forge openstef

If conda cannot find the package, add the conda-forge channel:

.. code-block:: bash

   conda config --add channels conda-forge
   conda install openstef

**Using pixi:**

.. code-block:: bash

   pixi add openstef

Development Installation
------------------------

If you want to contribute to OpenSTEF or modify the source code, you'll need a development installation.

Prerequisites
^^^^^^^^^^^^^

- **uv** (recommended) or pip - Install from https://docs.astral.sh/uv/
- **Git** for cloning the repository

Clone and Install
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install in development mode with all dependencies
   uv sync --all-extras --dev

   # Verify installation
   uv run pytest

This installs:

- All OpenSTEF packages in editable mode
- Development tools (linting, testing, documentation)
- Pre-commit hooks for code quality

Package-Specific Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To work on individual packages within the OpenSTEF monorepo:

.. code-block:: bash

   # Install specific package in development mode
   cd packages/openstef-models
   uv pip install -e .

   # Or install with development dependencies
   uv sync --dev

Verifying Your Installation
----------------------------

After installation, verify that OpenSTEF is working correctly:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # If you installed openstef-beam
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed")

You can also run a quick test to ensure the library is functioning:

.. code-block:: python

   from openstef_models.forecasting import make_forecast
   from openstef_core.datasets import load_elia

   # Load sample data
   data = load_elia()
   print(f"Loaded {len(data)} rows of sample data")
   print("Installation verified successfully!")

Troubleshooting
---------------

Common Issues
^^^^^^^^^^^^^

**Python Version Error**

If you see an error like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You need to upgrade to Python 3.12 or higher. We recommend using `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions:

.. code-block:: bash

   # Using pyenv
   pyenv install 3.12
   pyenv local 3.12

   # Using conda
   conda create -n openstef python=3.12
   conda activate openstef

**Import Errors**

If you encounter import errors, ensure you're using the correct package names. OpenSTEF 4.0 uses underscores in package names:

.. code-block:: python

   # Correct imports
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Not: from openstef.models import forecasting

**Package Not Found (conda)**

If conda cannot find the package:

.. code-block:: bash

   # Add conda-forge channel
   conda config --add channels conda-forge
   conda config --set channel_priority strict
   conda install openstef

**Memory Issues**

For large datasets, you may encounter memory issues. Consider:

- Processing data in chunks
- Using data streaming approaches
- Increasing available system memory
- Installing only the packages you need (e.g., ``openstef-models`` instead of ``openstef[all]``)

**Dependency Conflicts**

If you encounter dependency conflicts with existing packages:

.. code-block:: bash

   # Create a fresh virtual environment
   python -m venv openstef-env
   source openstef-env/bin/activate  # On Windows: openstef-env\Scripts\activate
   pip install openstef

Platform-Specific Notes
-----------------------

Windows
^^^^^^^

- Use PowerShell or Command Prompt for installation
- Consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ for best compatibility
- Some scientific packages may require Microsoft Visual C++ Build Tools, which can be installed from https://visualstudio.microsoft.com/visual-cpp-build-tools/

macOS
^^^^^

- Most installations work out of the box
- For Apple Silicon (M1/M2/M3), ensure you're using compatible wheel distributions
- If you encounter issues, try installing via conda which provides optimized builds for Apple Silicon

Linux
^^^^^

Most distributions work out of the box, but you may need development headers:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install python3-dev

   # RHEL/CentOS/Fedora
   sudo yum install python3-devel

   # Arch Linux
   sudo pacman -S python

Staying Updated
---------------

OpenSTEF follows semantic versioning. To check your current version and upgrade:

**Using pip:**

.. code-block:: bash

   # Check current version
   pip show openstef

   # Upgrade to latest version
   pip install --upgrade openstef

**Using uv:**

.. code-block:: bash

   # Check current version
   uv pip list | grep openstef

   # Upgrade to latest version
   uv pip install --upgrade openstef

**Using conda:**

.. code-block:: bash

   # Check current version
   conda list openstef

   # Upgrade to latest version
   conda update openstef

Subscribe to our `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions and features.

Getting Help
------------

If you encounter issues not covered in this guide:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for known problems and solutions
2. Search existing issues to see if others have encountered the same problem
3. Create a new issue with details about your environment and the error message
4. Contact us at openstef@lfenergy.org for support

When reporting issues, please include:

- Your Python version (``python --version``)
- Your OpenSTEF version (``pip show openstef``)
- Your operating system
- The complete error message and traceback

Next Steps
----------

Now that you have OpenSTEF installed, you're ready to start forecasting:

- **Quick Start**: Follow the :doc:`quickstart` guide for the fastest path to your first forecast
- **First Forecast Tutorial**: Work through the :doc:`first_forecast` tutorial for a detailed walkthrough
- **Understanding the Library**: Learn about OpenSTEF's capabilities and architecture in the main documentation

For advanced usage and customization, see :doc:`advanced_customization` after you're comfortable with the basics.