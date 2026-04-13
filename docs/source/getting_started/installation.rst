
============
Installation
============

This page covers everything you need to get OpenSTEF installed in your Python environment — from system requirements and package options through to verifying a working installation and resolving common problems. Once you have OpenSTEF installed, head to :doc:`quickstart` for the fastest path to your first forecast, or :doc:`first_forecast` for a guided walkthrough.

System Requirements
-------------------

Before installing, confirm your environment meets the following requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x instead.

You can check your current Python version with:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions on the same machine, `pyenv <https://github.com/pyenv/pyenv>`_ (Linux/macOS) or `conda <https://conda.io/>`_ are both good options.

Package Structure
-----------------

OpenSTEF is a modular library. Rather than one monolithic package, it ships as several focused packages that can be installed independently or together:

- **openstef-core** — shared utilities, data structures, and built-in datasets
- **openstef-models** — the core forecasting models (depends on ``openstef-core``)
- **openstef-beam** — backtesting and evaluation tools (depends on ``openstef-core``)
- **openstef** — a convenience meta-package that installs ``openstef-models`` by default

This design means you only pull in what you actually need. A project that only runs backtests, for example, does not need to carry the full model dependency tree.

Installing OpenSTEF
-------------------

Recommended: complete installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For most users, the simplest approach is to install the ``openstef`` meta-package with the ``[all]`` extra, which brings in every available component:

.. code-block:: bash

   pip install "openstef[all]"

If you use `uv <https://docs.astral.sh/uv/>`_ as your package manager (recommended for its speed and reliable dependency resolution):

.. code-block:: bash

   uv add "openstef[all]"

Installing individual packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you prefer a leaner installation, install only the packages your project requires:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Forecasting models (includes core)
   pip install openstef-models

   # Backtesting and evaluation tools (includes core)
   pip install openstef-beam

   # Meta-package — installs models by default
   pip install openstef

Selective extras via the meta-package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also use the meta-package's extras to mix and match components without listing individual package names:

.. code-block:: bash

   # Models + BEAM backtesting tools
   pip install "openstef[beam]"

Using a virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is strongly recommended to install OpenSTEF inside an isolated virtual environment rather than into your system Python. This avoids dependency conflicts with other projects:

.. code-block:: bash

   # Create and activate a virtual environment
   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows PowerShell

   # Then install as normal
   pip install "openstef[all]"

With ``uv``, environment management is handled automatically when you run ``uv add``.

Development Installation
------------------------

If you want to contribute to OpenSTEF or modify the source code, install directly from the repository in editable mode:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install all packages in editable mode with development dependencies
   uv sync --all-extras --dev

   # Verify the development environment
   uv run pytest

This installs all OpenSTEF packages in editable mode alongside development tooling (linting, testing, documentation generation) and pre-commit hooks for code quality.

To work on a single sub-package in isolation:

.. code-block:: bash

   cd packages/openstef-models
   uv pip install -e .

Verifying Your Installation
---------------------------

After installation, confirm everything is working by importing the relevant packages in a Python session:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # Check for BEAM if you installed it
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed — install with: pip install openstef-beam")

If both imports succeed and version strings are printed, your installation is ready. You can now follow the :doc:`quickstart` guide to run your first forecast.

Platform-Specific Notes
------------------------

Windows
^^^^^^^

- PowerShell and Command Prompt both work.
- For the smoothest experience, consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_.
- Some scientific dependencies may require **Microsoft Visual C++ Build Tools** if pre-built wheels are not available for your Python version.

macOS
^^^^^

- Most installations work out of the box.
- On **Apple Silicon (M1/M2/M3)**, ensure you are using a native arm64 Python build (available from `python.org <https://www.python.org/downloads/>`_ or via ``brew install python``). Rosetta 2 emulation works but is slower.

Linux
^^^^^

- Most distributions work without extra steps.
- On **Ubuntu/Debian**, install the Python development headers if you encounter build errors:

  .. code-block:: bash

     sudo apt-get install python3-dev

- On **RHEL/CentOS/Fedora**:

  .. code-block:: bash

     sudo yum install python3-devel

Troubleshooting
---------------

Python version error
^^^^^^^^^^^^^^^^^^^^

If pip refuses to install with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

Your active Python interpreter is too old. Upgrade to Python 3.12 or higher, or use ``pyenv``/``conda`` to switch to a compatible version before installing.

Package not found (conda)
^^^^^^^^^^^^^^^^^^^^^^^^^

If you are using conda and the package cannot be found, add the ``conda-forge`` channel:

.. code-block:: bash

   conda config --add channels conda-forge
   conda install openstef

Import errors
^^^^^^^^^^^^^

OpenSTEF 4.0 uses a different import structure from earlier versions. If you see ``ModuleNotFoundError``, check that you are using the correct package names:

.. code-block:: python

   # Correct — use the sub-package names directly
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect — the old monolithic import path no longer exists
   # from openstef.models import forecasting

Memory issues with large datasets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you encounter out-of-memory errors when working with large datasets, consider:

- Using ``openstef-beam``'s streaming evaluation utilities rather than loading all data at once.
- Configuring appropriate chunk sizes when reading input data.
- Running on a machine with more RAM, or using a cloud environment.

.. note::
   If none of the above resolves your issue, search the `GitHub Issues tracker <https://github.com/OpenSTEF/openstef/issues>`_ — there is a good chance someone has encountered the same problem. You can also reach the maintainers at openstef@lfenergy.org.

Staying Updated
---------------

OpenSTEF follows semantic versioning. To upgrade to the latest release:

.. code-block:: bash

   pip install --upgrade "openstef[all]"

   # or with uv
   uv add "openstef[all]"

Check the project's `changelog <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_ before upgrading across major versions, as breaking changes may require adjustments to your code.

Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — a minimal working example to get a forecast in minutes
- :doc:`first_forecast` — a step-by-step tutorial that explains each part of the workflow
- :doc:`backtesting` — learn how to evaluate and compare models on historical data
- :doc:`advanced_customization` — customise models, pipelines, and components for your specific use case