Installation
============

This page covers everything you need to get OpenSTEF installed and working on your machine — from system prerequisites through optional extras, verification, and fixes for the most common installation problems. Once you have a working installation, head over to :doc:`quickstart` to run your first forecast in minutes.

System Requirements
-------------------

Before installing, confirm your environment meets these requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux are all supported

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for modern type safety features and optimal performance. If your project is constrained to Python 3.10 or 3.11, use OpenSTEF 3.x instead.

Check your Python version before proceeding:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions on the same machine, `pyenv <https://github.com/pyenv/pyenv>`_ (Linux/macOS) or `conda <https://conda.io/>`_ (cross-platform) are both good options.

Choosing an Installation
------------------------

OpenSTEF 4.0 has a modular architecture. Rather than one monolithic package, the library is split into focused sub-packages that you can install independently or in combination. This keeps your environment lean — you only pull in what you actually use.

The packages are:

- **openstef-core** — shared types, dataset types, and base utilities used by all other packages
- **openstef-models** — core forecasting models, feature engineering, and data processing pipelines
- **openstef-beam** — backtesting, evaluation, analysis, and metrics
- **openstef** — the meta-package; installs ``openstef-models`` by default and exposes extras for the rest

Recommended: Complete Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For most users, installing everything at once is the right starting point. Use the ``[all]`` extra on the meta-package:

.. code-block:: bash

   pip install "openstef[all]"

If you use `uv <https://docs.astral.sh/uv/>`_ (recommended for faster resolution and reliable lockfiles):

.. code-block:: bash

   uv add "openstef[all]"

This single command installs ``openstef-models``, ``openstef-beam``, and all their dependencies.

Selective Installation
^^^^^^^^^^^^^^^^^^^^^^

If you want a smaller footprint, install only the packages your workflow requires:

.. code-block:: bash

   # Core utilities and dataset types only
   pip install openstef-core

   # Forecasting models only (no backtesting)
   pip install openstef-models

   # Backtesting and evaluation tools only
   pip install openstef-beam

   # Meta-package (models included, beam optional)
   pip install openstef

You can also mix and match via the meta-package extras:

.. code-block:: bash

   # Models + backtesting/evaluation
   pip install "openstef[beam]"

Using a Virtual Environment
----------------------------

Always install OpenSTEF inside a virtual environment to avoid conflicts with other projects. If you are not using ``uv`` (which manages environments automatically), create one manually:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

   pip install "openstef[all]"

.. note::
   ``uv`` creates and manages a virtual environment for you automatically. If you run ``uv add "openstef[all]"`` inside a project directory, no manual activation step is needed.

Verifying the Installation
--------------------------

After installation, run a quick sanity check in Python to confirm the packages loaded correctly:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # Check for openstef-beam if you installed it
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed (install with: pip install openstef-beam)")

A successful run prints version strings without errors. If you see an ``ImportError``, revisit the installation steps or check the troubleshooting section below.

Development Installation
------------------------

If you intend to contribute to OpenSTEF or modify its source code, install directly from the repository in editable mode. ``uv`` is required for this workflow:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install all packages in editable mode with dev dependencies
   uv sync --all-extras --dev

   # Confirm everything is working
   uv run pytest

This installs every workspace package (``openstef-core``, ``openstef-models``, ``openstef-beam``) in editable mode alongside development tooling for linting, testing, and building documentation.

To work on a single sub-package in isolation:

.. code-block:: bash

   cd packages/openstef-models
   uv sync --dev

Troubleshooting
---------------

Python Version Error
^^^^^^^^^^^^^^^^^^^^

If pip refuses to install with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

Your active Python interpreter is too old. Upgrade to Python 3.12+ using ``pyenv``, ``conda``, or your system package manager, then retry. Make sure the upgraded interpreter is the one active in your virtual environment:

.. code-block:: bash

   python --version   # should show 3.12.x or higher

Dependency Conflicts
^^^^^^^^^^^^^^^^^^^^

If pip reports conflicting dependencies with packages already in your environment, the safest fix is to install OpenSTEF into a fresh virtual environment rather than an existing one:

.. code-block:: bash

   python -m venv .venv-openstef
   source .venv-openstef/bin/activate
   pip install "openstef[all]"

Alternatively, ``uv`` resolves dependency conflicts more aggressively than pip and is worth trying if you hit persistent issues:

.. code-block:: bash

   uv add "openstef[all]"

ImportError After Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If Python can import one package but not another (e.g., ``openstef_models`` imports fine but ``openstef_beam`` raises ``ImportError``), the missing package was simply not included in your install command. Install it explicitly:

.. code-block:: bash

   pip install openstef-beam
   # or, to get everything at once:
   pip install "openstef[all]"

Slow or Hanging pip Resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF has a moderately large dependency tree. If ``pip install`` hangs during dependency resolution, switching to ``uv`` typically resolves this — it uses a faster Rust-based resolver:

.. code-block:: bash

   pip install uv
   uv add "openstef[all]"

.. note::
   [DIAGRAM: Package dependency tree showing openstef meta-package → openstef-models and openstef-beam → openstef-core, with arrows indicating dependency direction]

Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — the fastest path to a working forecast, with minimal setup
- :doc:`first_forecast` — a step-by-step tutorial that walks through the full forecasting workflow with explanations
- :doc:`backtesting` — learn how to evaluate and compare models using OpenSTEF's built-in backtesting tools
- :doc:`advanced_customization` — customise models, pipelines, and feature engineering for production use cases