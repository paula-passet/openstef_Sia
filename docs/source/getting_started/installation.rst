
============
Installation
============

This page covers everything you need to get OpenSTEF installed and ready to use: system requirements, the available installation options, how to verify a working setup, and solutions to the most common problems. Once you have OpenSTEF installed, head to :doc:`quickstart` for the fastest path to your first forecast, or :doc:`first_forecast` for a more guided walkthrough.

System Requirements
-------------------

Before installing, confirm your environment meets these requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux are all supported
- **pip 23+** or `uv <https://docs.astral.sh/uv/>`_ (recommended)

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x instead.

You can check your current Python version with:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions, tools like `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ make this straightforward.

Choosing an Installation
------------------------

OpenSTEF 4.0 uses a modular architecture: the library is split into focused packages that can be installed independently or together. This means you only pull in the dependencies you actually need.

The packages are:

- **openstef-core** — Core utilities, data structures, and datasets
- **openstef-models** — Forecasting models and training pipelines
- **openstef-beam** — Backtesting and evaluation tools
- **openstef** — Meta-package that includes ``openstef-models`` by default

For most users, the complete installation is the right choice.

Complete Installation
^^^^^^^^^^^^^^^^^^^^^

Install everything at once using the ``[all]`` extra:

.. code-block:: bash

   pip install "openstef[all]"

If you use ``uv`` (recommended for faster dependency resolution):

.. code-block:: bash

   uv add "openstef[all]"

This installs ``openstef-models`` and ``openstef-beam`` together, giving you the full forecasting and evaluation toolkit.

Selective Installation
^^^^^^^^^^^^^^^^^^^^^^

If you want a lighter footprint, install only the packages you need:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Forecasting models only (includes core)
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Meta-package with models (default)
   pip install openstef

You can also mix extras through the meta-package:

.. code-block:: bash

   # Models + BEAM backtesting tools
   pip install "openstef[beam]"

.. note::
   If you are only running backtesting workflows (see :doc:`backtesting`), installing ``openstef-beam`` alone is sufficient. If you are building custom pipelines (see :doc:`advanced_customization`), the full ``openstef[all]`` installation is recommended.

Installing in a Virtual Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is good practice to install OpenSTEF inside an isolated virtual environment to avoid dependency conflicts with other projects.

Using ``venv``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # On Windows: .venv\Scripts\activate
   pip install "openstef[all]"

Using ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install "openstef[all]"

.. note::
   If you install via conda and encounter a "package not found" error, add the ``conda-forge`` channel first:

   .. code-block:: bash

      conda config --add channels conda-forge
      conda install openstef

Development Installation
------------------------

If you want to contribute to OpenSTEF or modify the source code directly, install from the repository in editable mode. This requires `uv <https://docs.astral.sh/uv/>`_ and Git.

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   uv sync --all-extras --dev

This installs all OpenSTEF packages in editable mode, along with development tools (linting, testing, documentation generation) and pre-commit hooks. Verify the development setup by running the test suite:

.. code-block:: bash

   uv run pytest

To work on a single package in isolation:

.. code-block:: bash

   cd packages/openstef-models
   uv pip install -e .

Verifying Your Installation
----------------------------

After installation, confirm everything is working correctly by importing the library and checking the version:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # Check for BEAM if you installed it
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed (install with: pip install openstef-beam)")

A successful run prints the installed version numbers without any errors. If you see an ``ImportError``, review the troubleshooting section below.

Platform-Specific Notes
------------------------

**Windows**

Most installations work without additional steps. If you encounter build errors for scientific packages, install `Microsoft Visual C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_. Using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ is an alternative that avoids most Windows-specific issues.

**macOS**

Installations generally work out of the box. On Apple Silicon (M1/M2/M3), ensure you are using a Python distribution built for ``arm64`` — both ``pyenv`` and the official Python installer from python.org provide compatible builds.

**Linux**

Most distributions work without extra steps. If you see compilation errors, install the Python development headers first:

.. code-block:: bash

   # Ubuntu / Debian
   sudo apt-get install python3-dev

   # RHEL / CentOS / Fedora
   sudo yum install python3-devel

Troubleshooting
---------------

**Python version error**

If installation fails with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You are running Python 3.11 or earlier. Upgrade to Python 3.12+ using ``pyenv``, ``conda``, or the official Python installer, then retry.

**Import errors after installation**

OpenSTEF 4.0 uses new top-level package names. Make sure you are using the correct import paths:

.. code-block:: python

   # Correct
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect (OpenSTEF 3.x style — will not work in 4.0)
   # from openstef.models import forecasting

If you have both OpenSTEF 3.x and 4.x installed in the same environment, conflicts are likely. Use a fresh virtual environment for OpenSTEF 4.0.

**Memory errors on large datasets**

If you encounter out-of-memory errors when working with large datasets, consider:

- Using data streaming or chunked loading approaches
- Installing only the packages you need (avoid pulling in unnecessary heavy dependencies)
- Increasing available memory or running on a machine with more RAM

**Getting further help**

If none of the above resolves your issue:

1. Search the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ — your problem may already have a solution.
2. Open a new issue with your Python version, OS, and the full error traceback.
3. Reach out at openstef@lfenergy.org.

Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — Run a minimal working forecast in minutes
- :doc:`first_forecast` — A step-by-step tutorial explaining each part of the workflow
- :doc:`backtesting` — Learn how to evaluate and compare models
- :doc:`advanced_customization` — Customize pipelines and models for your use case