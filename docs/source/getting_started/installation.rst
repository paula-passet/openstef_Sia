Installation
============

This guide covers everything you need to install OpenSTEF, a Python library for short-term energy forecasting. Whether you're getting started with forecasting or setting up a production environment, you'll find the installation method that fits your needs.

System Requirements
-------------------

Before installing OpenSTEF, ensure your system meets these requirements:

- **Python 3.12 or higher** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, or Linux)
- **pip, uv, conda, or pixi** for package management

.. note::

   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

Quick Installation
------------------

For most users, the simplest approach is to install the meta-package:

.. code-block:: bash

   pip install openstef

This installs the core forecasting functionality including ``openstef-core`` and ``openstef-models``, which is sufficient for creating and running forecasts.

Alternative package managers:

.. code-block:: bash

   # Using uv (fast, modern Python package manager)
   uv add openstef

   # Using conda
   conda install -c conda-forge openstef

   # Using pixi
   pixi add openstef

Understanding the Package Structure
------------------------------------

OpenSTEF 4.0 uses a modular architecture with specialized packages:

- **openstef-core**: Core utilities, data structures, and datasets
- **openstef-models**: Machine learning models for forecasting
- **openstef-beam**: Backtesting and model evaluation tools
- **openstef**: Meta-package that bundles core and models

This modular design lets you install only what you need, keeping your environment lightweight.

Installation Options
--------------------

Choose the installation that matches your use case:

Complete Installation
^^^^^^^^^^^^^^^^^^^^^

Install everything for research, experimentation, and full functionality:

.. code-block:: bash

   pip install "openstef[all]"

This includes all packages: models, backtesting tools, and evaluation utilities.

Minimal Installation
^^^^^^^^^^^^^^^^^^^^

For production forecasting where you only need the core models:

.. code-block:: bash

   pip install openstef-models

This gives you a lightweight installation with just the forecasting models.

Selective Installation
^^^^^^^^^^^^^^^^^^^^^^

Mix and match components using extras:

.. code-block:: bash

   # Models + backtesting tools
   pip install "openstef[beam]"

   # Models + foundational models (when available)
   pip install "openstef[foundational-models]"

   # Multiple extras
   pip install "openstef[beam,foundational-models]"

Individual Packages
^^^^^^^^^^^^^^^^^^^

Install specific packages independently:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Forecasting models only
   pip install openstef-models

   # Backtesting and evaluation only
   pip install openstef-beam

Installation by Use Case
^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a quick reference for common scenarios:

- **Research & Experimentation**: ``pip install "openstef[all]"`` - Full toolkit
- **Production Forecasting**: ``pip install openstef-models`` - Lightweight models
- **Model Evaluation**: ``pip install "openstef[beam]"`` - Models + evaluation
- **Basic Development**: ``pip install openstef`` - Core functionality

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

You should see version numbers printed without errors. If you encounter import errors, see the troubleshooting section below.

Development Installation
------------------------

If you're contributing to OpenSTEF or need to modify the source code, use a development installation.

Prerequisites
^^^^^^^^^^^^^

- `uv <https://docs.astral.sh/uv/>`_ (recommended) or pip
- Git

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

Working on Individual Packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To develop a specific package:

.. code-block:: bash

   # Navigate to the package
   cd packages/openstef-models

   # Install in editable mode
   uv pip install -e .

   # Or install with development dependencies
   uv sync --dev

Troubleshooting
---------------

Python Version Error
^^^^^^^^^^^^^^^^^^^^

If you see this error:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You need Python 3.12 or higher. We recommend using `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions:

.. code-block:: bash

   # Using pyenv
   pyenv install 3.12
   pyenv local 3.12

   # Using conda
   conda create -n openstef python=3.12
   conda activate openstef

Package Not Found
^^^^^^^^^^^^^^^^^

If conda cannot find OpenSTEF:

.. code-block:: bash

   # Add conda-forge channel
   conda config --add channels conda-forge
   conda install openstef

Import Errors
^^^^^^^^^^^^^

Ensure you're using the correct package names. OpenSTEF 4.0 uses underscores in package names:

.. code-block:: python

   # Correct imports
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect (will fail)
   from openstef.models import forecasting

Missing Optional Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see a ``MissingExtraError``, you need to install additional dependencies:

.. code-block:: text

   MissingExtraError: Optional package beam is missing.

Install the missing extra:

.. code-block:: bash

   pip install "openstef[beam]"

Memory Issues with Large Datasets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For large datasets, consider:

- Processing data in chunks rather than loading everything into memory
- Using data streaming approaches
- Increasing available system memory
- Using a machine with more RAM for training

Dependency Conflicts
^^^^^^^^^^^^^^^^^^^^

If you encounter dependency conflicts with other packages:

.. code-block:: bash

   # Create a fresh virtual environment
   python -m venv openstef-env
   source openstef-env/bin/activate  # On Windows: openstef-env\Scripts\activate

   # Install OpenSTEF in the clean environment
   pip install openstef

Platform-Specific Notes
-----------------------

Windows
^^^^^^^

- Use PowerShell or Command Prompt for installation commands
- Some scientific packages may require `Microsoft Visual C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
- Consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ for best compatibility with development tools

macOS
^^^^^

- Most installations work out of the box
- For Apple Silicon (M1/M2/M3), ensure you're using compatible wheel distributions
- If using Homebrew Python, you may need to install additional dependencies

Linux
^^^^^

Most distributions work without additional setup. If you encounter build errors, install development headers:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install python3-dev

   # RHEL/CentOS/Fedora
   sudo yum install python3-devel

Keeping OpenSTEF Updated
-------------------------

OpenSTEF follows semantic versioning. Check your current version and upgrade:

.. code-block:: bash

   # Check current version
   pip show openstef

   # Upgrade to latest version
   pip install --upgrade openstef

   # Upgrade with all extras
   pip install --upgrade "openstef[all]"

Using other package managers:

.. code-block:: bash

   # uv
   uv list | grep openstef
   uv upgrade openstef

   # conda
   conda list openstef
   conda update openstef

   # pixi
   pixi list | grep openstef
   pixi upgrade openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions and features.

Getting Help
------------

If you encounter issues not covered here:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for known problems
2. Search existing issues or open a new one with details about your environment
3. Visit the project's support channels (see documentation for links)
4. Contact the team at openstef@lfenergy.org

When reporting issues, include:

- Your Python version (``python --version``)
- Your OpenSTEF version (``pip show openstef``)
- Your operating system
- The complete error message
- Steps to reproduce the problem

Next Steps
----------

Now that OpenSTEF is installed, you're ready to start forecasting:

- **Quick Start**: See :doc:`quickstart` for the fastest path to your first forecast
- **First Forecast Tutorial**: Follow :doc:`first_forecast` for a detailed walkthrough
- **Backtesting**: Learn to evaluate models in :doc:`backtesting`
- **Advanced Customization**: Explore :doc:`advanced_customization` for power user features