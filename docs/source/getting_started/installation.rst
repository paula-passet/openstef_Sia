Installation
============

This page covers everything you need to get OpenSTEF installed: system requirements, the different ways to install the library, optional extras for specific model backends, and how to verify your setup is working.

Once installed, head to :doc:`quickstart` to run your first forecast.

System Requirements
-------------------

OpenSTEF requires **Python 3.12 or later** (Python < 4.0). No other system-level dependencies are needed beyond a working Python environment and ``pip``.

A virtual environment is strongly recommended to avoid dependency conflicts:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

Standard Installation
---------------------

The simplest way to install OpenSTEF is via the ``openstef`` meta-package, which pulls in the full framework in one step:

.. code-block:: bash

   pip install openstef

This installs four packages together:

- **openstef-core** — data structures, base classes, datasets, and shared utilities
- **openstef-models** — forecasting models (LightGBM, XGBoost, and others)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-models that combine the above

For most users this is the right starting point. If you need a leaner install or are integrating only part of the framework into an existing project, see the section below on individual packages.

Installing Individual Packages
------------------------------

Each OpenSTEF component is independently installable. Install only what you need:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Forecasting models (depends on openstef-core)
   pip install openstef-models

   # Backtesting and evaluation tools (depends on openstef-core)
   pip install openstef-beam

   # Meta-models (depends on openstef-beam, openstef-core, and openstef-models[lgbm])
   pip install openstef-meta

The dependency graph flows upward: ``openstef-core`` has no OpenSTEF dependencies, while ``openstef-meta`` sits at the top and requires everything beneath it.

.. mermaid:: /diagrams/getting_started/installation_diagram_1.mmd

Optional Dependencies
---------------------

Some model backends and storage integrations are not installed by default because they carry heavier dependencies or have platform-specific requirements. These are exposed as *extras*.

Model backends (``openstef-models``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The default ``openstef-models`` install includes LightGBM. XGBoost is available as an extra and comes in two flavours depending on whether you want GPU acceleration:

.. code-block:: bash

   # LightGBM backend (included by default)
   pip install openstef-models

   # LightGBM explicitly
   pip install "openstef-models[lgbm]"

   # XGBoost — CPU-optimised build (Linux, Windows, macOS)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost — GPU build
   pip install "openstef-models[xgb-gpu]"

You can combine extras in a single install:

.. code-block:: bash

   pip install "openstef-models[lgbm,xgb-cpu]"

Storage and baselines (``openstef-beam``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef-beam`` ships optional support for reading data from S3 and for running baseline models:

.. code-block:: bash

   # S3 filesystem support via s3fs
   pip install "openstef-beam[all]"

   # Baseline models only (pulls in openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # Everything
   pip install "openstef-beam[all]"

.. note::
   If you try to use a feature that requires a missing extra, OpenSTEF raises a ``MissingExtraError`` with an explicit message telling you exactly which ``pip install`` command to run.

Upgrading
---------

To upgrade to the latest release, pass ``--upgrade`` to pip:

.. code-block:: bash

   pip install --upgrade openstef

To upgrade a specific package:

.. code-block:: bash

   pip install --upgrade openstef-models

Verifying the Installation
--------------------------

After installing, confirm that the packages are importable and check their versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam
   import openstef_meta

   print(openstef_core.__version__)
   print(openstef_models.__version__)
   print(openstef_beam.__version__)
   print(openstef_meta.__version__)

All four lines should print a version string without raising an ``ImportError``. If any import fails, check that your virtual environment is active and that the package was installed into it rather than a different Python interpreter.

You can also verify from the command line:

.. code-block:: bash

   pip show openstef-core openstef-models openstef-beam openstef-meta

This lists the installed version, location, and dependencies for each package.

Troubleshooting
---------------

**Wrong Python version**
   OpenSTEF requires Python ≥ 3.12. Run ``python --version`` to check. If your system Python is older, use a tool such as ``pyenv`` or ``conda`` to manage multiple Python versions.

**Import works in one terminal but not another**
   You likely have multiple Python environments. Confirm which ``pip`` you are using with ``pip --version`` and ensure it points to the same environment as the ``python`` interpreter you intend to use.

**XGBoost import error on Linux or Windows**
   The ``xgb-cpu`` extra installs a CPU-optimised build (``xgboost-cpu``). If you previously installed plain ``xgboost`` alongside it, there may be a conflict. Create a fresh virtual environment and install only ``openstef-models[xgb-cpu]``.

**MissingExtraError at runtime**
   OpenSTEF raises this when you call functionality that requires an optional extra you have not installed. The error message includes the exact ``pip install`` command needed — follow it and re-run.

Next Steps
----------

With OpenSTEF installed, continue to :doc:`quickstart` to run a minimal working forecast and see the library in action.