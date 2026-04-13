
============
Installation
============

This page covers everything you need to get OpenSTEF installed and ready to use — from system requirements and package options through to verifying your setup and resolving common problems. Once you have OpenSTEF installed, head over to :doc:`quickstart` to run your first forecast in minutes.

System Requirements
-------------------

Before installing, confirm your environment meets the following requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type-safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x instead.

You can check your current Python version with:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions on the same machine, `pyenv <https://github.com/pyenv/pyenv>`_ (Linux/macOS) or `conda <https://conda.io/>`_ (all platforms) are both good options.


Choosing What to Install
------------------------

OpenSTEF 4.0 is designed with a modular architecture. Rather than a single monolithic package, it is split into focused components that you can install independently or in combination. This lets you keep your environment lean — for example, a production forecasting service does not need the backtesting tools, and a data-science notebook does not need the distributed-evaluation infrastructure.

The available packages are:

- **openstef-core** — shared utilities and dataset helpers used by all other packages
- **openstef-models** — the core forecasting models
- **openstef-beam** — backtesting and large-scale evaluation tools (built on Apache Beam)
- **openstef** — a convenience meta-package that installs ``openstef-models`` by default

For most users, the simplest starting point is the complete installation, which pulls in everything:

.. code-block:: bash

   pip install "openstef[all]"

If you prefer `uv <https://docs.astral.sh/uv/>`_, the fast Rust-based package manager:

.. code-block:: bash

   uv add "openstef[all]"


Selective Installation
----------------------

If you know you only need specific capabilities, install individual packages directly. This is particularly useful in production environments where minimising dependencies matters.

.. code-block:: bash

   # Core utilities and dataset helpers only
   pip install openstef-core

   # Forecasting models only (no backtesting infrastructure)
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Meta-package — installs openstef-models by default
   pip install openstef

You can also use the meta-package's extras to mix and match:

.. code-block:: bash

   # Models + BEAM backtesting
   pip install "openstef[beam]"

.. note::
   If you are unsure which packages you need, start with ``pip install "openstef[all]"``. You can always slim down your dependencies later once you know which parts of the library you actually use.


Using a Virtual Environment
---------------------------

It is strongly recommended to install OpenSTEF inside a dedicated virtual environment to avoid conflicts with other packages. Here is a typical setup using the standard library's ``venv``:

.. code-block:: bash

   # Create a virtual environment
   python -m venv .venv

   # Activate it (Linux / macOS)
   source .venv/bin/activate

   # Activate it (Windows PowerShell)
   .venv\Scripts\Activate.ps1

   # Install OpenSTEF
   pip install "openstef[all]"

Alternatively, with conda:

.. code-block:: bash

   conda create -n openstef python=3.12
   conda activate openstef

   # Add conda-forge for the broadest package availability
   conda config --add channels conda-forge
   conda install openstef


Development Installation
------------------------

If you want to contribute to OpenSTEF or modify the source code, install directly from the repository in editable mode. The project uses `uv <https://docs.astral.sh/uv/>`_ as its primary development tool:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install all packages in editable mode with development dependencies
   uv sync --all-extras --dev

   # Verify the development environment
   uv run pytest

This installs all OpenSTEF packages in editable mode alongside development tools for linting, testing, and building documentation. If you only need to work on a specific sub-package:

.. code-block:: bash

   cd packages/openstef-models
   uv pip install -e .


Verifying Your Installation
---------------------------

After installation, confirm everything is working correctly by importing the packages in a Python session:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # Check for BEAM if you installed it
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed (this is fine if you didn't install it)")

A successful run with no ``ImportError`` exceptions means your installation is ready. You can now follow the :doc:`quickstart` guide to run your first forecast.


Platform-Specific Notes
-----------------------

**Windows**

- PowerShell and Command Prompt both work.
- For the smoothest experience with scientific dependencies, consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_.
- Some compiled packages may require the `Microsoft Visual C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_ if pre-built wheels are not available for your Python version.

**macOS**

- Most installations work out of the box.
- On Apple Silicon (M1/M2/M3), ensure you are using a native arm64 Python build rather than an x86_64 build running under Rosetta, as some numerical libraries have arm64-specific wheels that offer significantly better performance.

**Linux**

- Most distributions work without any extra steps.
- On Ubuntu/Debian, if you encounter build errors for compiled extensions: ``sudo apt-get install python3-dev``
- On RHEL/CentOS: ``sudo yum install python3-devel``


Troubleshooting
---------------

**Python version error**

If pip refuses to install OpenSTEF with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You are running an older Python version. Upgrade to Python 3.12 or higher, or use pyenv/conda to create an environment with the correct version (see `Using a Virtual Environment`_ above).

**Import errors after installation**

Make sure you are using the correct module names. The installed packages use underscores, not hyphens:

.. code-block:: python

   # Correct
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect — these will raise ImportError
   # from openstef.models import forecasting

Also confirm that you are running Python from the same environment where you installed OpenSTEF. A common mistake is installing into one virtual environment and then running Python from another.

**Package not found via conda**

If conda cannot locate the OpenSTEF packages, add the ``conda-forge`` channel:

.. code-block:: bash

   conda config --add channels conda-forge
   conda install openstef

**Memory errors with large datasets**

OpenSTEF's backtesting tools (``openstef-beam``) are designed for large-scale evaluation and support streaming data approaches. If you encounter memory pressure when working with large datasets, review the :doc:`backtesting` tutorial, which covers chunked and distributed evaluation patterns.

**Still stuck?**

- Search the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ — your problem may already have a solution.
- Open a new issue if you believe you have found a bug.
- Reach out at openstef@lfenergy.org for community support.


Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — the fastest path to a working forecast, with minimal setup
- :doc:`first_forecast` — a step-by-step tutorial that explains what is happening at each stage
- :doc:`backtesting` — how to evaluate and compare models on historical data
- :doc:`advanced_customization` — customising models, pipelines, and components for advanced use cases