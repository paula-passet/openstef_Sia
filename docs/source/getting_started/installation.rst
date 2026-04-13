
============
Installation
============

This page covers everything you need to get OpenSTEF installed and ready to use:
system requirements, the available installation options, how to verify your setup,
and fixes for the most common problems you might encounter. Once you have a working
installation, head over to :doc:`quickstart` to run your first forecast in minutes.

System Requirements
-------------------

Before installing, confirm your environment meets these requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type
   safety features. If you need Python 3.10 or 3.11 support, consider using
   OpenSTEF 3.x instead.

To check your Python version:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions on the same machine,
`pyenv <https://github.com/pyenv/pyenv>`_ (Linux/macOS) or
`conda <https://conda.io/>`_ (all platforms) are both good options.

Choosing What to Install
------------------------

OpenSTEF 4.0 has a modular architecture. The library is split into focused packages
so you can install only what your project actually needs:

- **openstef-core** — shared utilities, data structures, and built-in datasets
- **openstef-models** — the core forecasting models and training pipelines
- **openstef-beam** — backtesting, evaluation, and large-scale experiment tooling
- **openstef** — the meta-package; installs ``openstef-models`` by default

For most users, the complete installation is the right starting point.

Complete Installation (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install everything at once using the ``all`` extra:

.. code-block:: bash

   # Using pip
   pip install "openstef[all]"

.. code-block:: bash

   # Using uv (faster dependency resolution)
   uv add "openstef[all]"

This pulls in ``openstef-models`` and ``openstef-beam`` together with all their
dependencies.

Individual Package Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have specific needs — for example, you only want to run backtests without
pulling in the full model stack — you can install packages individually:

.. code-block:: bash

   # Core utilities and built-in datasets only
   pip install openstef-core

   # Forecasting models only
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Meta-package (includes openstef-models by default)
   pip install openstef

Selective Extras via the Meta-Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also mix and match components through the meta-package's extras:

.. code-block:: bash

   # Models + BEAM backtesting
   pip install "openstef[beam]"

This approach is convenient when you want a single ``pip install`` command but
don't need the full suite.

Using a Virtual Environment
----------------------------

It is strongly recommended to install OpenSTEF inside a dedicated virtual
environment to avoid dependency conflicts with other projects.

.. code-block:: bash

   # Create and activate a virtual environment
   python -m venv .venv

   # Linux / macOS
   source .venv/bin/activate

   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1

   # Then install OpenSTEF as normal
   pip install "openstef[all]"

If you prefer ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install "openstef[all]"

.. note::
   OpenSTEF is not yet available directly from the ``conda-forge`` channel as a
   ``conda install`` target. Use ``pip`` inside your conda environment. If you
   encounter a *Package Not Found* error when trying ``conda install openstef``,
   add the conda-forge channel first and then fall back to pip:

   .. code-block:: bash

      conda config --add channels conda-forge
      pip install "openstef[all]"

Development Installation
------------------------

If you want to contribute to OpenSTEF or experiment with unreleased changes,
install directly from source:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install all packages in editable mode with dev dependencies
   uv sync --all-extras --dev

   # Verify the installation by running the test suite
   uv run pytest

This installs all OpenSTEF packages in editable mode alongside the development
toolchain (linting, testing, documentation generation) and pre-commit hooks.

To work on a single package in isolation:

.. code-block:: bash

   cd packages/openstef-models
   uv pip install -e .

Verifying Your Installation
----------------------------

After installation, confirm everything is working with a quick Python check:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # Check for BEAM if you installed it
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed (install with: pip install openstef-beam)")

A successful run prints the installed version numbers without any import errors.
If you see version numbers, you are ready to proceed to :doc:`quickstart`.

Platform-Specific Notes
------------------------

**Windows**

- PowerShell and Command Prompt both work.
- For the smoothest experience, consider using
  `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_.
- Some scientific dependencies may require the
  `Microsoft Visual C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
  if pre-built wheels are unavailable for your Python version.

**macOS**

- Most installations work out of the box.
- On Apple Silicon (M1/M2/M3), ensure you are using a native arm64 Python build
  (available from `python.org <https://www.python.org/downloads/>`_ or via
  ``brew install python``). Rosetta-emulated x86 builds can cause subtle issues
  with compiled dependencies.

**Linux**

- Most distributions work without additional steps.
- Ubuntu/Debian: ``sudo apt-get install python3-dev``
- RHEL/CentOS: ``sudo yum install python3-devel``

Troubleshooting
---------------

**Python version error**

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You are running Python 3.11 or older. Upgrade to Python 3.12+ or use
``pyenv``/``conda`` to switch versions without affecting your system Python.

**Import errors after installation**

Make sure you are using the correct module names. The importable package names
differ slightly from the PyPI distribution names:

.. code-block:: python

   # Correct
   from openstef_models import forecasting
   from openstef_beam import evaluation

   # Incorrect — this will raise an ImportError
   from openstef.models import forecasting

Also confirm that you are importing from the same environment where you ran
``pip install``. Running ``which python`` (Linux/macOS) or ``where python``
(Windows) will tell you which interpreter is active.

**Memory issues with large datasets**

If you run out of memory during training or evaluation, consider:

- Using ``openstef-beam``'s streaming evaluation utilities rather than loading
  all data at once.
- Reducing dataset size during initial experimentation and scaling up once your
  pipeline is validated.
- Configuring appropriate chunk sizes when reading data.

**Getting further help**

If none of the above resolves your issue:

1. Search the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ — your
   problem has likely been seen before.
2. Open a new issue with your Python version, OS, full error traceback, and the
   exact install command you ran.
3. Reach out at openstef@lfenergy.org.

Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — run a minimal working forecast in under five minutes.
- :doc:`first_forecast` — a step-by-step tutorial that explains what is happening
  at each stage.
- :doc:`backtesting` — learn how to evaluate and compare models on historical data.
- :doc:`advanced_customization` — extend OpenSTEF with custom models and pipelines.