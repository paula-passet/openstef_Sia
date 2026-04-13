
============
Installation
============

This page covers everything you need to get OpenSTEF installed and ready to use — from system requirements and package options through to verifying a working installation and resolving common problems. Once you have OpenSTEF installed, head over to :doc:`quickstart` for the fastest path to your first forecast, or :doc:`first_forecast` for a more detailed walkthrough.

System Requirements
-------------------

Before installing, confirm your environment meets the following requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux are all supported
- pip 23+ or `uv <https://docs.astral.sh/uv/>`_ (recommended)

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type-safety features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x instead.

You can check your current Python version with:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions, `pyenv <https://github.com/pyenv/pyenv>`_ (Linux/macOS) or `conda <https://conda.io/>`_ (cross-platform) are both good options.

Choosing an Installation
------------------------

OpenSTEF 4.0 uses a modular architecture split across several packages. You install only what you need. The packages are:

- **openstef-core** — shared utilities, data structures, and built-in datasets
- **openstef-models** — the core forecasting models
- **openstef-beam** — backtesting and evaluation tooling
- **openstef** — a convenience meta-package that pulls in ``openstef-models`` by default

For most users, the complete installation is the right starting point:

.. code-block:: bash

   pip install "openstef[all]"

This single command installs all available packages — ``openstef-models`` and ``openstef-beam`` — and is the recommended choice if you are not sure what you need yet.

If you prefer `uv <https://docs.astral.sh/uv/>`_ (a fast, Rust-based package manager that handles both dependency resolution and virtual environments):

.. code-block:: bash

   uv add "openstef[all]"

Selective Installation
^^^^^^^^^^^^^^^^^^^^^^

If you have specific needs or want to keep your environment lean, you can install individual packages or use extras to mix and match:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Core forecasting models (no backtesting tools)
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Meta-package — models included by default
   pip install openstef

   # Meta-package with BEAM added
   pip install "openstef[beam]"

The same commands work with ``uv add`` in place of ``pip install``.

.. note::
   If you are only running forecasts and do not need backtesting, ``pip install openstef`` (or ``pip install openstef-models``) is sufficient. Add ``openstef-beam`` later if you need the evaluation tools covered in :doc:`backtesting`.

Installing in a Virtual Environment
------------------------------------

It is strongly recommended to install OpenSTEF inside a dedicated virtual environment to avoid dependency conflicts with other projects.

**Using venv (standard library):**

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows PowerShell

   pip install "openstef[all]"

**Using conda:**

.. code-block:: bash

   conda create -n openstef python=3.12
   conda activate openstef
   pip install "openstef[all]"

.. note::
   If conda cannot locate the ``openstef`` package directly, install it via pip inside the conda environment as shown above. If you prefer a pure conda workflow, add the ``conda-forge`` channel first:

   .. code-block:: bash

      conda config --add channels conda-forge
      conda install openstef

Development Installation
------------------------

If you want to contribute to OpenSTEF or modify the source code, install directly from the repository in editable mode. This requires `uv <https://docs.astral.sh/uv/>`_ and Git:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install all packages in editable mode with dev dependencies
   uv sync --all-extras --dev

   # Verify the development environment
   uv run pytest

This installs all OpenSTEF packages in editable mode, development tooling (linting, testing, documentation generation), and pre-commit hooks for code quality. To work on a single package in isolation:

.. code-block:: bash

   cd packages/openstef-models
   uv pip install -e .

Verifying the Installation
--------------------------

After installation, confirm everything is working by importing the library and checking the version:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # If you installed openstef-beam, verify it too
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed — install with: pip install openstef-beam")

A successful run prints the installed version numbers without any errors. If you see an ``ImportError``, work through the troubleshooting section below.

Platform-Specific Notes
-----------------------

**Windows**

- PowerShell or Command Prompt both work.
- For the smoothest experience, consider using `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_.
- Some scientific dependencies may require `Microsoft Visual C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_ if pre-built wheels are unavailable for your Python version.

**macOS**

- Most installations work out of the box.
- On Apple Silicon (M1/M2/M3), ensure you are using Python and wheel distributions built for ``arm64``. Both ``pyenv`` and the official python.org installer provide compatible builds.

**Linux**

- Most distributions work without extra steps.
- On Ubuntu/Debian, install the Python development headers if you encounter build errors:

  .. code-block:: bash

     sudo apt-get install python3-dev

- On RHEL/CentOS:

  .. code-block:: bash

     sudo yum install python3-devel

Troubleshooting
---------------

**Python version error**

If pip refuses to install with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You need to upgrade to Python 3.12 or higher. Use ``pyenv`` or ``conda`` to install a compatible version without affecting your system Python.

**Import errors after installation**

OpenSTEF 4.0 uses new top-level package names. Make sure you are using the correct import paths:

.. code-block:: python

   # Correct
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect (OpenSTEF 3.x style — will not work in 4.0)
   # from openstef.models import forecasting

If you have both OpenSTEF 3.x and 4.x installed in the same environment, remove the old version first:

.. code-block:: bash

   pip uninstall openstef
   pip install "openstef[all]"

**Memory errors with large datasets**

If you encounter out-of-memory errors when working with large time series:

- Consider installing only the packages you actively use to reduce overhead.
- Use data streaming or chunked loading rather than loading entire datasets at once.
- Refer to :doc:`advanced_customization` for guidance on configuring pipeline behaviour for large-scale workloads.

**Package not found via conda**

If the conda solver cannot find ``openstef``, add the ``conda-forge`` channel or install via pip inside your conda environment (see `Installing in a Virtual Environment`_ above).

Getting Help
^^^^^^^^^^^^

If the steps above do not resolve your issue:

1. Search the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ — your problem may already have a solution.
2. Open a new issue if nothing matches.
3. Reach out at openstef@lfenergy.org for direct support.

Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — run your first forecast in minutes with a minimal working example.
- :doc:`first_forecast` — a step-by-step tutorial that explains what is happening at each stage.
- :doc:`backtesting` — learn how to evaluate and compare models using ``openstef-beam``.
- :doc:`advanced_customization` — customise pipelines, models, and features for production use cases.