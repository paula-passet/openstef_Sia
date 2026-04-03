Installation
============

This guide covers everything you need to install OpenSTEF, a Python library for short-term energy forecasting. Whether you're setting up for production forecasting, research, or contributing to development, you'll find the right installation approach here.

System Requirements
-------------------

Before installing OpenSTEF, ensure your system meets these requirements:

- **Python 3.12 or higher** (Python 3.13 is supported)
- **64-bit operating system** (Windows, macOS, or Linux)
- **pip 21.0+** or another modern Python package manager

.. note::

   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

You can verify your Python version:

.. code-block:: bash

   python --version

Understanding OpenSTEF's Architecture
-------------------------------------

OpenSTEF 4.0 uses a modular architecture with specialized packages:

- **openstef-core**: Core utilities, data structures, and shared functionality
- **openstef-models**: Machine learning models for forecasting (XGBoost, LightGBM, etc.)
- **openstef-beam**: Backtesting and model evaluation tools
- **openstef** (meta-package): Convenient installer that bundles core and models

This modular design lets you install only what you need, keeping your environment lean for production deployments or comprehensive for research.

Quick Installation
------------------

For most users, the meta-package provides everything needed to start forecasting:

.. code-block:: bash

   pip install openstef

This installs both ``openstef-core`` and ``openstef-models``, giving you access to all forecasting models and core utilities.

To verify the installation:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

Installation Options
--------------------

Choose the installation that matches your use case.

Complete Installation
^^^^^^^^^^^^^^^^^^^^^

Install all available packages for the full OpenSTEF experience:

.. code-block:: bash

   pip install "openstef[all]"

This includes ``openstef-models`` and ``openstef-beam`` for complete forecasting and evaluation capabilities.

Individual Package Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install only specific packages when you need a minimal footprint:

.. code-block:: bash

   # Core utilities and data structures only
   pip install openstef-core

   # Forecasting models only
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

Selective Installation with Extras
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mix and match components using the meta-package extras:

.. code-block:: bash

   # Models + backtesting tools
   pip install "openstef[beam]"

   # Models + foundational models (when available)
   pip install "openstef[foundational-models]"

   # Multiple extras
   pip install "openstef[beam,foundational-models]"

Installation by Use Case
^^^^^^^^^^^^^^^^^^^^^^^^^

Here's what to install for common scenarios:

**Research & Experimentation**
   .. code-block:: bash

      pip install "openstef[all]"

   Provides the full toolkit for exploring models, backtesting, and analysis.

**Production Forecasting**
   .. code-block:: bash

      pip install openstef-models

   Lightweight installation with just the forecasting models you need in production.

**Model Evaluation**
   .. code-block:: bash

      pip install "openstef[beam]"

   Includes models plus evaluation and backtesting tools for comparing performance.

**Basic Development**
   .. code-block:: bash

      pip install openstef

   Core functionality for building applications that use OpenSTEF.

Alternative Package Managers
-----------------------------

OpenSTEF supports multiple Python package managers.

Using uv
^^^^^^^^

`uv <https://docs.astral.sh/uv/>`_ is a fast, modern Python package manager:

.. code-block:: bash

   # Basic installation
   uv add openstef

   # With all extras
   uv add "openstef[all]"

   # Specific extras
   uv add "openstef[beam]"

Using conda
^^^^^^^^^^^

Install from conda-forge:

.. code-block:: bash

   conda install -c conda-forge openstef

If conda cannot find the package, add the conda-forge channel:

.. code-block:: bash

   conda config --add channels conda-forge
   conda install openstef

Using pixi
^^^^^^^^^^

`pixi <https://pixi.sh/>`_ is a cross-platform package manager:

.. code-block:: bash

   pixi add openstef

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

   # Check available models
   from openstef_models.model.model_type import ModelType
   print(f"Available models: {[m.name for m in ModelType]}")

This confirms that packages are installed and importable.

Development Installation
------------------------

For contributors or users who want to modify OpenSTEF source code, install in development mode.

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
- Development tools (pytest, ruff, mypy)
- Pre-commit hooks for code quality

Package-Specific Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To work on individual packages within the monorepo:

.. code-block:: bash

   # Navigate to specific package
   cd packages/openstef-models

   # Install in editable mode
   uv pip install -e .

   # Or install with development dependencies
   uv sync --dev

See :doc:`../contribute/development` for detailed development setup instructions.

Troubleshooting
---------------

Common installation issues and their solutions.

Python Version Error
^^^^^^^^^^^^^^^^^^^^

If you see:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

**Solution:** Upgrade to Python 3.12 or higher. Use `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ to manage Python versions:

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
   conda config --set channel_priority strict
   conda install openstef

Import Errors
^^^^^^^^^^^^^

If you encounter import errors, ensure you're using the correct package names:

.. code-block:: python

   # Correct imports
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect (will fail)
   # from openstef.models import forecasting

OpenSTEF 4.0 uses underscores in package names (``openstef_models``), not dots.

Missing Optional Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see a ``MissingExtraError``:

.. code-block:: text

   MissingExtraError: Optional package beam is missing.

**Solution:** Install the missing extra:

.. code-block:: bash

   pip install "openstef[beam]"

Or install the specific package directly:

.. code-block:: bash

   pip install openstef-beam

Dependency Conflicts
^^^^^^^^^^^^^^^^^^^^

If you encounter dependency conflicts with existing packages:

.. code-block:: bash

   # Create a fresh virtual environment
   python -m venv openstef-env
   source openstef-env/bin/activate  # On Windows: openstef-env\Scripts\activate
   pip install openstef

Memory Issues with Large Datasets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For large datasets, consider:

- Processing data in chunks rather than loading everything into memory
- Using the streaming capabilities in ``openstef-beam``
- Increasing available system memory or using a machine with more RAM

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
- For Apple Silicon (M1/M2/M3), ensure you're using ARM64-compatible Python and packages
- If using Homebrew Python, ensure it's up to date: ``brew upgrade python``

Linux
^^^^^

Most distributions work without issues. If you encounter build errors, install development headers:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install python3-dev build-essential

   # RHEL/CentOS/Fedora
   sudo yum install python3-devel gcc gcc-c++

   # Arch Linux
   sudo pacman -S python base-devel

Staying Updated
---------------

OpenSTEF follows `semantic versioning <https://semver.org/>`_. To check your version and upgrade:

.. code-block:: bash

   # Check current version
   pip show openstef

   # Upgrade to latest version
   pip install --upgrade openstef

   # Upgrade with extras
   pip install --upgrade "openstef[all]"

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions, features, and bug fixes.

Getting Help
------------

If you encounter issues not covered here:

1. Check the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for known problems
2. Search or ask in `GitHub Discussions <https://github.com/OpenSTEF/openstef/discussions>`_
3. Review the :doc:`../contribute/index` guide for development-related issues
4. Contact the community at openstef@lfenergy.org

Next Steps
----------

Now that OpenSTEF is installed, you're ready to start forecasting:

- :doc:`quickstart` - Create your first forecast in minutes
- :doc:`first_forecast` - Detailed walkthrough of building a forecast
- :doc:`backtesting` - Learn how to evaluate and compare models
- :doc:`advanced_customization` - Customize OpenSTEF for your specific needs