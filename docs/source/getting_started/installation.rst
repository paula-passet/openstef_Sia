Installation
============

This page covers everything you need to install OpenSTEF on your system: the recommended
installation path, individual package options, optional model backends, and how to verify
that your environment is set up correctly. If you run into problems, the
:ref:`troubleshooting` section at the bottom addresses the most common issues.

Once your installation is working, head over to :doc:`quickstart` for the fastest path
to your first forecast, or :doc:`first_forecast` for a more detailed walkthrough.

.. contents:: On this page
   :local:
   :depth: 2

System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python** 3.12 or later (Python < 3.12 is not supported)
- **pip** 21.0 or later (for reliable dependency resolution)
- A virtual environment is strongly recommended (``venv``, ``conda``, or similar)

OpenSTEF is a pure-Python library and has no mandatory system-level dependencies beyond
a working Python installation.

.. note::

   Python 3.12 is the minimum supported version. If you are running an older Python,
   upgrade before proceeding — the library will not install correctly on earlier versions.

Recommended Installation
------------------------

The simplest way to get started is to install the ``openstef`` meta-package, which pulls
in the complete framework in a single command:

.. code-block:: bash

   pip install openstef

This installs four coordinated packages:

- **openstef-core** — shared data structures, utilities, and base interfaces
- **openstef-models** — forecasting model implementations (LightGBM, XGBoost, and more)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-model layer that combines the above

For most users this is the right choice. The individual packages are only worth
considering if you have strict dependency budgets or are building a specialised
integration.

Installing Individual Packages
------------------------------

If you only need part of the framework, each package can be installed on its own:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Forecasting models (requires openstef-core)
   pip install openstef-models

   # Backtesting and evaluation tools (requires openstef-core)
   pip install openstef-beam

   # Meta-models (requires openstef-beam, openstef-core, and openstef-models)
   pip install openstef-meta

The dependency graph flows in one direction — ``openstef-core`` has no OpenSTEF
dependencies, while ``openstef-meta`` sits at the top and depends on everything else.
Installing a higher-level package will automatically pull in the packages it needs.

**[DIAGRAM: Package dependency graph showing openstef-core at the base, openstef-models and openstef-beam depending on it, openstef-meta depending on all three, and the openstef meta-package installing all four]**

Optional Dependencies
---------------------

Several model backends are optional and must be explicitly requested. This keeps the
base installation lean for environments where only specific backends are needed.

Model backends for ``openstef-models``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # LightGBM backend
   pip install "openstef-models[lgbm]"

   # XGBoost backend (CPU-optimised build on Linux and Windows)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU support
   pip install "openstef-models[xgb-gpu]"

   # Install the full openstef suite with LightGBM included
   pip install "openstef[lgbm]"

If you try to instantiate a model whose backend is not installed, OpenSTEF raises a
``MissingExtraError`` with a clear message telling you exactly which extra to install:

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

   forecaster = LGBMForecaster(...)
   # MissingExtraError: Install 'lightgbm' via: pip install openstef-models[lgbm]

This means you can safely import model classes without the backend present — the error
only surfaces when you actually try to train or predict.

Extras for ``openstef-beam``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Baseline models (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # S3 filesystem support plus baselines
   pip install "openstef-beam[all]"

Installing in a Virtual Environment
------------------------------------

Working inside a virtual environment avoids dependency conflicts with other projects.
Here is a minimal setup using the standard library ``venv`` module:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # On Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install "openstef[lgbm]"

For ``conda`` users:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install "openstef[lgbm]"

.. note::

   Prefer ``pip`` over ``conda install`` for OpenSTEF itself — the packages are
   published to PyPI and the conda-forge recipe may lag behind the latest release.

Verifying Your Installation
----------------------------

After installation, run the following snippet to confirm that the core packages are
importable and report their versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam

   print("openstef-core   :", openstef_core.__version__)
   print("openstef-models :", openstef_models.__version__)
   print("openstef-beam   :", openstef_beam.__version__)

You should see three version strings printed without any import errors.

To verify that an optional backend is available, try importing it directly:

.. code-block:: python

   # Check LightGBM backend
   try:
       import lightgbm
       print("LightGBM available:", lightgbm.__version__)
   except ImportError:
       print("LightGBM not installed — run: pip install openstef-models[lgbm]")

   # Check XGBoost backend
   try:
       import xgboost
       print("XGBoost available:", xgboost.__version__)
   except ImportError:
       print("XGBoost not installed — run: pip install openstef-models[xgb-cpu]")

.. _troubleshooting:

Troubleshooting
---------------

**Python version error during install**

   If pip reports a ``Requires-Python`` conflict, your active Python is older than 3.12.
   Check with ``python --version`` and upgrade or switch to a compatible interpreter.

**Dependency resolver conflicts**

   Large environments with many pre-installed packages can produce resolver conflicts.
   The safest fix is to install OpenSTEF into a fresh virtual environment rather than
   a shared or system Python.

**``MissingExtraError`` at runtime**

   This error means a model backend (LightGBM, XGBoost, etc.) is not installed. The
   error message will tell you the exact ``pip install`` command to run. See
   :ref:`optional-dependencies` above for the full list of extras.

**``ImportError`` for ``openstef_beam``, ``openstef_core``, or ``openstef_models``**

   These packages use underscores in their import names but hyphens in their PyPI names
   (``openstef-beam`` → ``import openstef_beam``). If you see an ``ImportError``, confirm
   the package is actually installed:

   .. code-block:: bash

      pip show openstef-beam

   If the command returns nothing, the package is missing — install it with
   ``pip install openstef-beam`` or ``pip install openstef``.

**Slow installation due to large optional dependencies**

   XGBoost and LightGBM are not small packages. If you are in a bandwidth-constrained
   environment and do not need GPU support, prefer ``openstef-models[xgb-cpu]`` over
   ``openstef-models[xgb-gpu]``.

**Stale cache causing unexpected versions**

   If you are upgrading and the old version persists, clear pip's cache:

   .. code-block:: bash

      pip install --upgrade --no-cache-dir openstef

Next Steps
----------

With OpenSTEF installed you are ready to start forecasting:

- :doc:`quickstart` — run a minimal forecast in under five minutes
- :doc:`first_forecast` — a step-by-step tutorial explaining each part of the workflow
- :doc:`backtesting` — evaluate a trained model on historical data
- :doc:`advanced_customization` — customise models, features, and pipelines for production use