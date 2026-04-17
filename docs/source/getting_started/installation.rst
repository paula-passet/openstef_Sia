Installation
============

This page covers everything you need to install OpenSTEF on your system: system
requirements, the different installation options, optional dependencies for specific
model backends, and how to verify that your installation is working correctly. If you
run into problems, the :ref:`troubleshooting` section at the bottom addresses the most
common issues.

Once you have OpenSTEF installed, head to :doc:`quickstart` for the fastest path to
your first forecast, or :doc:`first_forecast` for a more detailed walkthrough.

.. note::

   OpenSTEF is a Python library. It is designed to be imported into your own
   Python scripts, notebooks, and applications — not run as a standalone program.


System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python 3.12 or later** (Python < 3.12 is not supported)
- A supported operating system: Linux, macOS, or Windows
- ``pip`` 21.0 or later (run ``pip install --upgrade pip`` if unsure)

OpenSTEF works well inside virtual environments and conda environments. Using an
isolated environment is strongly recommended to avoid dependency conflicts.


Installing OpenSTEF
-------------------

The simplest way to get started is to install the ``openstef`` meta-package, which
pulls in the entire framework in one command:

.. code-block:: bash

   pip install openstef

This installs four packages that together make up the OpenSTEF library:

- **openstef-core** — shared data structures, datasets, exceptions, and utilities
- **openstef-models** — model implementations (XGBoost, LightGBM, and more)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-models and ensemble combiners

For most users, installing ``openstef`` is the right choice.


Installing Individual Packages
------------------------------

If you only need part of the framework — for example, you want to use the core data
structures without pulling in the full model suite — you can install packages
individually:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Model implementations (depends on openstef-core)
   pip install openstef-models

   # Backtesting and evaluation tools (depends on openstef-core)
   pip install openstef-beam

   # Meta-models and ensemble combiners (depends on openstef-beam, openstef-models)
   pip install openstef-meta

Each package declares its own dependencies, so pip will install only what is needed
for that package.


Optional Dependencies
---------------------

Some model backends are not installed by default because they have large or
platform-specific dependencies. These are available as *extras*.

**LightGBM support**

LightGBM is an optional backend for both ``openstef-models`` and the meta-model
combiners. Install it with:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

**XGBoost support (CPU)**

The CPU-optimised XGBoost build is selected automatically based on your platform
(macOS uses the standard ``xgboost`` wheel; Linux and Windows use ``xgboost-cpu``):

.. code-block:: bash

   pip install "openstef-models[xgb-cpu]"

**XGBoost support (GPU)**

If you have a CUDA-capable GPU and want GPU-accelerated training:

.. code-block:: bash

   pip install "openstef-models[xgb-gpu]"

**BEAM baselines and cloud storage**

``openstef-beam`` ships two optional feature groups:

.. code-block:: bash

   # Baseline models (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # All optional features, including S3 filesystem support
   pip install "openstef-beam[all]"

**Installing everything at once**

To install the full framework with all optional extras, combine the meta-package with
the extras you need:

.. code-block:: bash

   pip install openstef "openstef-models[lgbm,xgb-cpu]" "openstef-beam[all]"

.. note::

   GPU builds of XGBoost (``xgb-gpu``) and CPU builds (``xgb-cpu``) are mutually
   exclusive. Install only one of them in a given environment.


Verifying Your Installation
---------------------------

After installation, confirm that the packages are importable and check their versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam
   import openstef_meta

   print("openstef-core  :", openstef_core.__version__)
   print("openstef-models:", openstef_models.__version__)
   print("openstef-beam  :", openstef_beam.__version__)
   print("openstef-meta  :", openstef_meta.__version__)

You can also check installed versions from the command line:

.. code-block:: bash

   pip show openstef-core openstef-models openstef-beam openstef-meta

If all four packages are listed without errors, your installation is complete. To go
further, follow the :doc:`quickstart` guide to run a minimal forecast.


.. _troubleshooting:

Troubleshooting
---------------

**"No module named 'openstef_core'" after installation**

This usually means the package was installed into a different Python environment than
the one you are running. Check which Python interpreter is active:

.. code-block:: bash

   which python        # Linux / macOS
   where python        # Windows

Make sure you activated the correct virtual environment before installing, and that
you are running the same interpreter when importing the library.

**pip resolves to an old version of Python**

On systems where both Python 2 and Python 3 are present, ``pip`` may point to the
wrong interpreter. Use ``pip3`` explicitly, or invoke pip through the target
interpreter:

.. code-block:: bash

   python3.12 -m pip install openstef

**Dependency conflicts with an existing environment**

OpenSTEF requires Python ≥ 3.12 and recent versions of ``numpy``, ``pandas``, and
``pydantic``. If you see resolver errors, the safest fix is to create a fresh
environment:

.. code-block:: bash

   python3.12 -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   pip install --upgrade pip
   pip install openstef

**MissingExtraError at runtime**

If you see an error like::

   Optional package lgbm is missing. Please install it to use this module
   using `pip install lgbm` or install all optional features using
   `pip install openstef-models[all]`.

OpenSTEF raises ``MissingExtraError`` when code tries to use a backend that was not
installed. Install the relevant extra (e.g., ``openstef-models[lgbm]``) and the error
will go away.

**XGBoost import errors on Linux or Windows**

If you installed ``openstef-models`` without specifying a platform extra and XGBoost
fails to import, install the explicit CPU extra for your platform:

.. code-block:: bash

   pip install "openstef-models[xgb-cpu]"

**Installation is slow or stalls**

Large optional dependencies such as XGBoost and LightGBM can take time to download.
If pip appears to stall during dependency resolution, try adding ``--no-cache-dir``
or upgrading pip to the latest version:

.. code-block:: bash

   pip install --upgrade pip
   pip install openstef


Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — a minimal working example to get a forecast in minutes
- :doc:`first_forecast` — a step-by-step tutorial explaining each part of the workflow
- :doc:`backtesting` — learn how to evaluate and compare models on historical data
- :doc:`advanced_customization` — customise models, pipelines, and features for your use case