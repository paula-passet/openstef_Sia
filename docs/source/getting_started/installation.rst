Installation
============

This guide covers everything you need to install OpenSTEF, a Python library for short-term energy forecasting. Whether you're setting up for production forecasting, research, or development, you'll find the right installation approach here.

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

OpenSTEF 4.0 uses a modular design with specialized packages that can be installed independently or together:

- **openstef-core**: Core utilities and datasets
- **openstef-models**: Forecasting models and algorithms
- **openstef-beam**: Backtesting and model evaluation tools
- **openstef**: Meta-package that bundles core and models

This modular approach lets you install only what you need, keeping your environment lightweight for production deployments while offering full functionality for research and development.

Quick Installation
------------------

For most users, the meta-package provides everything needed to start forecasting:

.. code-block:: bash

   pip install openstef

This installs both ``openstef-core`` and ``openstef-models``, giving you access to all forecasting functionality.

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

Choose Your Installation
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's modular design supports different use cases:

**Complete Installation (Recommended for Research)**

Install all available packages for full functionality:

.. code-block:: bash

   pip install "openstef[all]"

This includes ``openstef-models`` and ``openstef-beam`` for comprehensive forecasting, backtesting, and evaluation capabilities.

**Individual Package Installation**

Install only specific packages for lightweight deployments:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Core forecasting models only
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

**Selective Installation with Extras**

Mix and match components using the meta-package extras:

.. code-block:: bash

   # Models + BEAM for evaluation
   pip install "openstef[beam]"

   # Models + Foundational models (when available)
   pip install "openstef[foundational-models]"

   # Multiple extras
   pip install "openstef[beam,foundational-models]"

Installation by Use Case
^^^^^^^^^^^^^^^^^^^^^^^^^

Choose the right installation for your needs:

+---------------------------+-----------------------------------+--------------------------------+
| Use Case                  | Installation Command              | What You Get                   |
+===========================+===================================+================================+
| Research & Experimentation| ``pip install "openstef[all]"``   | Full toolkit for analysis      |
+---------------------------+-----------------------------------+--------------------------------+
| Production Forecasting    | ``pip install openstef-models``   | Lightweight core models        |
+---------------------------+-----------------------------------+--------------------------------+
| Model Evaluation          | ``pip install "openstef[beam]"``  | Models + evaluation tools      |
+---------------------------+-----------------------------------+--------------------------------+
| Basic Development         | ``pip install openstef``          | Core functionality             |
+---------------------------+-----------------------------------+--------------------------------+

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

Run a quick test to ensure the library functions:

.. code-block:: python

   from openstef_models.forecasting import make_forecast
   from openstef_core.data import load_example_data

   # Load example data
   data = load_example_data()
   
   # Verify data loaded successfully
   print(f"Loaded {len(data)} rows of example data")

If this runs without errors, your installation is ready to use.

Development Installation
------------------------

For contributors or users who want to modify OpenSTEF's source code, install in development mode.

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

Ensure you're using the correct package names in your imports:

.. code-block:: python

   # Correct imports
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Not: from openstef.models import forecasting

Note the underscore (``_``) in package names, not a dot (``.``).

Dependency Conflicts
^^^^^^^^^^^^^^^^^^^^

If you encounter dependency conflicts with existing packages:

.. code-block:: bash

   # Create a fresh virtual environment
   python -m venv openstef-env
   source openstef-env/bin/activate  # On Windows: openstef-env\Scripts\activate
   pip install openstef

Virtual environments isolate OpenSTEF's dependencies from other projects.

Memory Issues with Large Datasets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For large-scale forecasting, consider:

- Using streaming approaches for data loading
- Installing with memory-optimized configurations
- Configuring appropriate chunk sizes in your forecasting pipeline

See the :doc:`first_forecast` tutorial for guidance on handling large datasets efficiently.

Platform-Specific Notes
-----------------------

Windows
^^^^^^^

- Use PowerShell or Command Prompt for installation commands
- Consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ for best compatibility
- Some scientific packages may require Microsoft Visual C++ Build Tools. Download from `Microsoft's website <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_

macOS
^^^^^

- Most installations work out of the box
- For Apple Silicon (M1/M2/M3), ensure you're using native ARM64 Python and compatible wheel distributions
- If using Homebrew Python, ensure it's up to date: ``brew upgrade python``

Linux
^^^^^

Most distributions work without additional setup. For specific distributions:

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

.. code-block:: bash

   # Check current version
   pip show openstef

   # Upgrade to latest version
   pip install --upgrade openstef

With other package managers:

.. code-block:: bash

   # uv
   uv upgrade openstef

   # conda
   conda update openstef

   # pixi
   pixi upgrade openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions and features.

Getting Help
------------

If you encounter issues not covered here:

1. Check `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for known problems
2. Review the contribution guide for development setup questions
3. Contact us at openstef@lfenergy.org

Next Steps
----------

Now that OpenSTEF is installed, you're ready to start forecasting:

- :doc:`quickstart` - Get your first forecast running in minutes
- :doc:`first_forecast` - Detailed walkthrough of creating forecasts
- :doc:`backtesting` - Learn to evaluate and compare models