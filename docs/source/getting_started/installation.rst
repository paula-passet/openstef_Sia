Installation
============

This guide covers everything you need to install OpenSTEF, a Python library for short-term energy forecasting. Whether you're getting started with a simple installation or setting up a development environment, you'll find the information you need here.

System Requirements
-------------------

Before installing OpenSTEF, ensure your system meets these requirements:

- **Python 3.12 or higher** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, or Linux)
- **pip, uv, conda, or pixi** package manager

.. note::

   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

Understanding OpenSTEF's Modular Architecture
----------------------------------------------

OpenSTEF 4.0 uses a modular design with specialized packages that can be installed independently:

- **openstef-core**: Core utilities, data structures, and datasets
- **openstef-models**: Forecasting models and training pipeline
- **openstef-beam**: Backtesting and model evaluation tools
- **openstef**: Meta-package that bundles core and models by default

This modular approach lets you install only what you need, keeping your environment lean for production deployments or comprehensive for research and development.

Quick Installation
------------------

For most users, the meta-package provides everything needed to start forecasting:

.. code-block:: bash

   pip install openstef

This installs both ``openstef-core`` and ``openstef-models``, giving you access to the core forecasting functionality.

Alternative package managers:

.. code-block:: bash

   # Using uv (fast, modern)
   uv add openstef

   # Using conda
   conda install -c conda-forge openstef

   # Using pixi
   pixi add openstef

Installation Options
--------------------

Choose Your Components
^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's modular design means you can tailor your installation to your specific needs.

**Complete Installation (Recommended for Beginners)**

Install all available packages for the full OpenSTEF experience:

.. code-block:: bash

   pip install "openstef[all]"

This includes models, backtesting tools, and all optional components.

**Individual Package Installation**

Install only specific packages when you know exactly what you need:

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

Mix and match components using extras:

.. code-block:: bash

   # Models + BEAM for backtesting
   pip install "openstef[beam]"

   # Models + Foundational models (when available)
   pip install "openstef[foundational-models]"

   # Multiple extras
   pip install "openstef[beam,foundational-models]"

Installation by Use Case
^^^^^^^^^^^^^^^^^^^^^^^^^

Here's what to install based on your use case:

- **Research & Experimentation**: ``pip install "openstef[all]"`` - Full toolkit for exploring models and evaluation
- **Production Forecasting**: ``pip install openstef-models`` - Lightweight core models without extra dependencies
- **Model Evaluation**: ``pip install "openstef[beam]"`` - Models plus backtesting and evaluation tools
- **Data Processing Only**: ``pip install openstef-core`` - Just the core utilities and datasets

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

If this runs without errors, you're ready to start forecasting. Proceed to the :doc:`quickstart` guide for a minimal working example.

Development Installation
------------------------

Contributors and advanced users who want to modify OpenSTEF's source code should use a development installation.

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

Package-Specific Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To work on individual packages within the monorepo:

.. code-block:: bash

   # Install specific package in development mode
   cd packages/openstef-models
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

Package Not Found (conda)
^^^^^^^^^^^^^^^^^^^^^^^^^^

If conda cannot find OpenSTEF:

.. code-block:: bash

   # Add conda-forge channel
   conda config --add channels conda-forge
   conda install openstef

Import Errors
^^^^^^^^^^^^^

Ensure you're using the correct package names in your imports. OpenSTEF 4.0 uses underscores in package names:

.. code-block:: python

   # Correct imports
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect (won't work)
   from openstef.models import forecasting

Missing Optional Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you encounter a ``MissingExtraError``, you're trying to use functionality that requires an optional dependency:

.. code-block:: python

   # Error message example
   MissingExtraError: Optional package beam is missing.

Install the missing extra:

.. code-block:: bash

   pip install "openstef[beam]"

Memory Issues
^^^^^^^^^^^^^

For large datasets, you may encounter memory issues. Consider:

- Processing data in smaller chunks
- Using streaming approaches for data loading
- Increasing available system memory
- Using a machine with more RAM for training

Dependency Conflicts
^^^^^^^^^^^^^^^^^^^^

If you encounter dependency conflicts with other packages:

1. Create a fresh virtual environment dedicated to OpenSTEF
2. Install OpenSTEF first before other packages
3. Check for conflicting package versions in your environment

.. code-block:: bash

   # Create a fresh environment
   python -m venv openstef-env
   source openstef-env/bin/activate  # On Windows: openstef-env\Scripts\activate
   pip install openstef

Platform-Specific Notes
-----------------------

Windows
^^^^^^^

- Use PowerShell or Command Prompt for installation commands
- Consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ for best compatibility with scientific Python packages
- Some dependencies may require Microsoft Visual C++ Build Tools. Download from `Microsoft's website <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_ if needed

macOS
^^^^^

- Most installations work out of the box
- For Apple Silicon (M1/M2/M3), ensure you're using native ARM64 Python (not Rosetta)
- Check that you have Xcode Command Line Tools installed: ``xcode-select --install``

Linux
^^^^^

Most Linux distributions work without issues. If you encounter compilation errors, install development headers:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install python3-dev build-essential

   # RHEL/CentOS/Fedora
   sudo yum install python3-devel gcc gcc-c++

Getting Help
------------

If you encounter issues not covered here:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for known problems
2. Search existing issues or create a new one with details about your environment
3. Visit the project's support resources (see documentation for contact information)
4. Email the team at openstef@lfenergy.org

When reporting issues, include:

- Your Python version (``python --version``)
- Your operating system
- The complete error message
- Installation command you used

Keeping OpenSTEF Updated
-------------------------

OpenSTEF follows semantic versioning. To upgrade to the latest version:

.. code-block:: bash

   # Using pip
   pip install --upgrade openstef

   # Using uv
   uv upgrade openstef

   # Using conda
   conda update openstef

Check your current version:

.. code-block:: bash

   # Using pip
   pip show openstef

   # Using uv
   uv list | grep openstef

   # Using conda
   conda list openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ to receive notifications about new versions, features, and bug fixes.

Next Steps
----------

Now that OpenSTEF is installed, you're ready to start forecasting:

- **New users**: Start with the :doc:`quickstart` guide for a minimal working example
- **Learn by doing**: Follow the :doc:`first_forecast` tutorial for a detailed walkthrough
- **Evaluate models**: See the :doc:`backtesting` guide to compare different approaches
- **Advanced users**: Explore :doc:`advanced_customization` for power user features