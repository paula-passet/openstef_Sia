
============
Installation
============

This page covers everything you need to get OpenSTEF installed and ready to use — from system requirements and package options through to verifying your setup and resolving common problems. Once you have the library installed, head over to :doc:`quickstart` for a minimal working example, or :doc:`first_forecast` for a guided walkthrough.

System Requirements
-------------------

Before installing, confirm your environment meets these requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type-safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x instead.

If you are unsure which Python version you have, check it from the command line:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions side by side, tools like `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_ make this straightforward.


Choosing What to Install
------------------------

OpenSTEF 4.0 is built around a modular architecture. Rather than one monolithic package, the library is split into focused components that you can install independently or together. This keeps your environment lean when you only need a subset of the functionality.

The available packages are:

- **openstef-core** — Core utilities and dataset helpers shared across the library.
- **openstef-models** — The main forecasting models and training pipelines.
- **openstef-beam** — Backtesting and evaluation tools.
- **openstef** — A meta-package that pulls in ``openstef-models`` by default, with optional extras.

For most users, the complete installation is the right starting point:

.. code-block:: bash

   pip install "openstef[all]"

This single command installs ``openstef-models`` and ``openstef-beam`` together. If you prefer `uv <https://docs.astral.sh/uv/>`_, the fast Rust-based package manager:

.. code-block:: bash

   uv add "openstef[all]"


Selective Installation
----------------------

If you have specific needs — for example, you only want the forecasting models without the backtesting tools — you can install individual packages directly:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Forecasting models only
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Meta-package with models (default extras)
   pip install openstef

You can also mix and match using the meta-package's extras syntax:

.. code-block:: bash

   # Models + BEAM backtesting tools
   pip install "openstef[beam]"


Using a Virtual Environment
---------------------------

It is strongly recommended to install OpenSTEF inside a dedicated virtual environment to avoid dependency conflicts with other projects. Using the standard library ``venv``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # On Windows: .venv\Scripts\activate
   pip install "openstef[all]"

With ``uv``, environment creation and package installation are handled together:

.. code-block:: bash

   uv venv
   source .venv/bin/activate
   uv add "openstef[all]"

With ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install "openstef[all]"

.. note::
   If conda cannot locate the ``openstef`` package directly, add the ``conda-forge`` channel first:

   .. code-block:: bash

      conda config --add channels conda-forge
      conda install openstef


Development Installation
------------------------

If you intend to contribute to OpenSTEF or modify its source code, install from a local clone of the repository in editable mode. This requires `uv <https://docs.astral.sh/uv/>`_ and Git:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   uv sync --all-extras --dev

This installs all OpenSTEF packages in editable mode, along with development tools (linting, testing, documentation) and pre-commit hooks. To run the test suite and confirm everything is working:

.. code-block:: bash

   uv run pytest

To work on a single sub-package in isolation:

.. code-block:: bash

   cd packages/openstef-models
   uv pip install -e .


Verifying Your Installation
---------------------------

After installation, open a Python interpreter and confirm the packages import correctly:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # Check for BEAM if you installed it
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed")

A successful run prints the installed version numbers without errors. If you see an ``ImportError``, review the troubleshooting section below.


Platform-Specific Notes
-----------------------

**Windows**

Most installations work with standard pip. For best compatibility, consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_. Some scientific packages may require Microsoft Visual C++ Build Tools to be installed first.

**macOS**

Installations generally work out of the box. If you are on Apple Silicon (M1/M2/M3), ensure you are downloading compatible wheel distributions — recent versions of pip handle this automatically.

**Linux**

Most distributions work without extra steps. If you encounter build errors related to missing headers, install the Python development package for your distribution:

.. code-block:: bash

   # Ubuntu / Debian
   sudo apt-get install python3-dev

   # RHEL / CentOS
   sudo yum install python3-devel


Troubleshooting
---------------

**Python version error**

If installation fails with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You need to upgrade to Python 3.12 or higher. Use ``pyenv`` or ``conda`` to install and activate a compatible version without affecting your system Python.

**Import errors after installation**

OpenSTEF 4.0 uses distinct package names that differ from earlier versions. Make sure you are using the correct import paths:

.. code-block:: python

   # Correct
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect (OpenSTEF 3.x style — will not work in 4.0)
   # from openstef.models import forecasting

**Package not found via conda**

If conda reports that ``openstef`` cannot be found, add the ``conda-forge`` channel as described in the `Using a Virtual Environment`_ section above.

**Memory issues with large datasets**

If you encounter out-of-memory errors when working with large time series, consider using data streaming approaches or configuring appropriate chunk sizes. The :doc:`advanced_customization` page covers strategies for scaling to larger workloads.

**Still stuck?**

1. Search the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ — your problem may already have a solution.
2. Open a new issue if nothing matches.
3. Reach out at openstef@lfenergy.org.


Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — Run your first forecast in minutes with a minimal example.
- :doc:`first_forecast` — A step-by-step tutorial that explains what is happening at each stage.
- :doc:`backtesting` — Learn how to evaluate and compare models on historical data.
- :doc:`advanced_customization` — Customise models, pipelines, and components for production use cases.