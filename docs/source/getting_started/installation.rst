
============
Installation
============

This page covers everything you need to get OpenSTEF installed and ready to use: system requirements, the available installation options, how to verify a working setup, and solutions to common problems. Once you have OpenSTEF installed, head to :doc:`quickstart` to run your first forecast in minutes, or follow the more detailed walkthrough in :doc:`first_forecast`.

System Requirements
-------------------

Before installing, confirm your environment meets these requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux are all supported
- **pip** (bundled with Python) or `uv <https://docs.astral.sh/uv/>`_ (recommended for faster installs)

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x instead.

You can check your Python version with:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions, `pyenv <https://github.com/pyenv/pyenv>`_ (Linux/macOS) or `conda <https://conda.io/>`_ (cross-platform) are both good options.


Choosing What to Install
------------------------

OpenSTEF 4.0 uses a modular architecture. Rather than one monolithic package, the library is split into focused components that you can install independently. This keeps your environment lean — you only pull in what you actually need.

The packages are:

- **openstef-core** — shared utilities, data structures, and bundled datasets
- **openstef-models** — the core forecasting models (depends on ``openstef-core``)
- **openstef-beam** — backtesting and evaluation tools (depends on ``openstef-core``)
- **openstef** — a convenience meta-package that installs ``openstef-models`` by default

For most users, the complete installation is the right starting point.


Complete Installation
---------------------

Install everything at once using the ``[all]`` extra:

.. code-block:: bash

   pip install "openstef[all]"

If you use ``uv`` (recommended for speed):

.. code-block:: bash

   uv add "openstef[all]"

This installs ``openstef-models`` and ``openstef-beam`` together, giving you access to all forecasting, backtesting, and evaluation functionality.


Selective Installation
----------------------

If you want a smaller footprint, install only the packages you need.

**Core library only** (utilities and datasets, no models):

.. code-block:: bash

   pip install openstef-core

**Forecasting models only** (the most common choice):

.. code-block:: bash

   pip install openstef-models
   # or equivalently:
   pip install openstef

**Backtesting and evaluation tools only**:

.. code-block:: bash

   pip install openstef-beam

**Models plus backtesting** (without using ``[all]``):

.. code-block:: bash

   pip install "openstef[beam]"

.. note::
   ``openstef-models`` and ``openstef-beam`` both depend on ``openstef-core``, so it is always installed automatically as a transitive dependency. You never need to install ``openstef-core`` explicitly unless you want *only* the core utilities.


Installing in a Virtual Environment
------------------------------------

It is strongly recommended to install OpenSTEF inside a virtual environment to avoid conflicts with other packages. Using the standard library ``venv``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows PowerShell

   pip install "openstef[all]"

With ``uv``, environment creation and package installation are handled together:

.. code-block:: bash

   uv venv
   uv add "openstef[all]"

With ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install "openstef[all]"

.. note::
   If conda cannot locate the ``openstef`` package directly, add the ``conda-forge`` channel and try again:

   .. code-block:: bash

      conda config --add channels conda-forge
      conda install openstef


Development Installation
------------------------

If you intend to contribute to OpenSTEF or modify the source code, install from the repository in editable mode:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install all packages in editable mode with dev tools
   uv sync --all-extras --dev

   # Verify the installation by running the test suite
   uv run pytest

This sets up all OpenSTEF packages in editable mode along with linting, testing, and documentation tooling.


Verifying Your Installation
----------------------------

After installation, open a Python interpreter and confirm the packages import correctly:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # Check for openstef-beam if you installed it
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed (install with: pip install openstef-beam)")

A successful run prints the version numbers without errors. If you see an ``ImportError``, review the troubleshooting section below.


Platform-Specific Notes
------------------------

**Windows**

- Use PowerShell or Command Prompt. Windows Subsystem for Linux (WSL) often provides better compatibility for scientific Python packages.
- Some compiled dependencies may require `Microsoft Visual C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_.

**macOS**

- Most installations work out of the box.
- On Apple Silicon (M1/M2/M3), ensure you are using a native arm64 Python build (e.g., from `python.org <https://www.python.org/downloads/>`_ or Homebrew) to get compatible wheel distributions.

**Linux**

- Most distributions work without additional steps.
- On Ubuntu/Debian, install the Python development headers if you encounter build errors: ``sudo apt-get install python3-dev``
- On RHEL/CentOS: ``sudo yum install python3-devel``


Troubleshooting
---------------

**Python version error**

If pip rejects the package with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

Your active Python interpreter is too old. Upgrade to Python 3.12 or higher, or use ``pyenv``/``conda`` to switch to a compatible version without affecting your system Python.

**Import errors after installation**

OpenSTEF 4.0 uses different import paths than earlier versions. Use the correct module names:

.. code-block:: python

   # Correct
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect (OpenSTEF 3.x style — will raise ImportError)
   # from openstef.models import forecasting

If you have an older version of OpenSTEF installed alongside 4.0, namespace collisions can cause unexpected import errors. Use a fresh virtual environment to avoid this.

**Package not found in conda**

If ``conda install openstef`` reports the package as unavailable, add the ``conda-forge`` channel:

.. code-block:: bash

   conda config --add channels conda-forge
   conda install openstef

**Memory issues with large datasets**

For very large datasets, consider:

- Installing only the packages you need (smaller dependency footprint)
- Using data streaming or chunked loading approaches
- Reviewing the :doc:`advanced_customization` page for guidance on configuring chunk sizes and memory-efficient pipelines

**Getting further help**

If none of the above resolves your issue:

1. Search the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ — your problem may already have a solution.
2. Open a new issue with your Python version, OS, and the full error traceback.
3. Reach out at openstef@lfenergy.org.


Staying Up to Date
------------------

OpenSTEF follows semantic versioning. To upgrade to the latest release:

.. code-block:: bash

   pip install --upgrade "openstef[all]"
   # or
   uv add "openstef[all]"

Check the project's `changelog <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_ before upgrading between major versions, as breaking changes may require updates to your code.


Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — the fastest path to a working forecast, with minimal setup
- :doc:`first_forecast` — a step-by-step tutorial that explains what is happening at each stage
- :doc:`backtesting` — learn how to evaluate and compare models on historical data
- :doc:`advanced_customization` — customise models, pipelines, and components for advanced use cases