Installation
============

This page covers everything you need to install OpenSTEF: system requirements,
installation options ranging from a single meta-package to individual components,
optional feature extras, and steps to verify your environment is working correctly.
Once installed, head to :doc:`quickstart` for the fastest path to your first forecast.

.. note::

   OpenSTEF requires **Python 3.12 or later** (Python < 4.0). If you are on an
   older Python version, upgrade before proceeding.

----

Basic Installation
------------------

The simplest way to get everything is the ``openstef`` meta-package, which pulls in
all sub-packages and their default dependencies in one command:

.. code-block:: bash

   pip install openstef

This installs the four constituent packages:

- ``openstef-core`` — data structures, feature engineering, and shared utilities
- ``openstef-models`` — forecasting model implementations (LightGBM, XGBoost, …)
- ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM)
- ``openstef-meta`` — meta-model layer that combines the above

For most users this is the right starting point. If you are working in a constrained
environment or only need a subset of the functionality, read on.

----

Installing Individual Packages
-------------------------------

Each sub-package can be installed independently. This is useful when you want to
keep your environment lean or when you are building a service that only needs one
layer of the stack.

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Add model implementations on top of core
   pip install openstef-models

   # Add backtesting and evaluation tooling
   pip install openstef-beam

   # Add the meta-model layer (requires beam + core + models[lgbm])
   pip install openstef-meta

The dependency graph flows upward: ``openstef-meta`` depends on ``openstef-beam``,
which depends on ``openstef-core``. Installing a higher-level package will
automatically pull in the packages below it.

.. note:: [DIAGRAM: Dependency graph showing openstef-core at the base, openstef-models and openstef-beam building on top of it, and openstef-meta at the apex depending on all three.]

----

Optional Feature Extras
-----------------------

Several packages expose optional extras that gate heavier or platform-specific
dependencies behind an explicit opt-in.

openstef-models extras
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # LightGBM support (recommended for most forecasting tasks)
   pip install "openstef-models[lgbm]"

   # XGBoost on CPU (Linux and Windows use the leaner xgboost-cpu build)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU support
   pip install "openstef-models[xgb-gpu]"

The default ``openstef-models`` install does **not** include LightGBM or XGBoost.
If you call a model class that requires one of these backends without the
corresponding extra installed, OpenSTEF raises a ``MissingExtraError`` with an
actionable message telling you exactly which extra to add.

openstef-beam extras
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Baseline model support (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # S3 filesystem support for reading/writing data from AWS S3
   pip install "openstef-beam[all]"   # includes baselines + s3fs

The ``[all]`` extra is a convenience shorthand that activates every optional
feature for ``openstef-beam`` at once.

----

Virtual Environments
--------------------

It is strongly recommended to install OpenSTEF inside a dedicated virtual
environment to avoid dependency conflicts with other projects.

.. code-block:: bash

   # Create and activate a virtual environment
   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

   # Then install as normal
   pip install openstef

If you use ``conda``, create an environment with Python 3.12 first:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install openstef

----

Verifying the Installation
---------------------------

After installation, confirm that the packages are importable and check their
versions:

.. code-block:: python

   import importlib.metadata

   packages = [
       "openstef",
       "openstef-core",
       "openstef-models",
       "openstef-beam",
       "openstef-meta",
   ]

   for pkg in packages:
       try:
           version = importlib.metadata.version(pkg)
           print(f"{pkg}: {version}")
       except importlib.metadata.PackageNotFoundError:
           print(f"{pkg}: NOT INSTALLED")

A successful full installation prints a version string for each package. If you
installed only individual packages, the ones you skipped will show ``NOT INSTALLED``,
which is expected.

You can also do a quick smoke-test by importing a core class:

.. code-block:: python

   from openstef_core import PredictionJob   # core data structure
   from openstef_beam.backtesting import Pipeline  # backtesting pipeline

   print("OpenSTEF imported successfully.")

If either import raises a ``ModuleNotFoundError``, the corresponding package is
missing — re-run the relevant ``pip install`` command above.

----

Troubleshooting
---------------

``ModuleNotFoundError: No module named 'openstef_beam'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The package is not installed in the active Python environment. Verify which
Python interpreter is active:

.. code-block:: bash

   which python          # Linux / macOS
   where python          # Windows

Then install into that interpreter explicitly:

.. code-block:: bash

   python -m pip install openstef

``MissingExtraError: Optional package lgbm is missing``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You are using a model that requires LightGBM, but the extra was not installed.
Fix it with:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

``pip`` resolves to Python 2 or an unexpected version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``pip3`` or the ``python -m pip`` form to be explicit about which interpreter
you are targeting:

.. code-block:: bash

   python3 -m pip install openstef

Dependency conflicts with existing packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF pins some dependencies (e.g. ``xgboost>=3,<4``) to ensure reproducible
behaviour. If you hit a conflict, the cleanest solution is to install OpenSTEF in
a fresh virtual environment rather than trying to reconcile versions in a shared
environment.

.. note::

   If you encounter a conflict you cannot resolve, open an issue on the
   `OpenSTEF GitHub repository <https://github.com/OpenSTEF>`_ with the full
   output of ``pip install openstef --verbose``.

----

Next Steps
----------

With OpenSTEF installed you are ready to start forecasting. The sibling pages in
this section walk you through progressively more detailed usage:

- :doc:`quickstart` — run a forecast in a few lines of code
- :doc:`first_forecast` — a step-by-step tutorial explaining each stage of the pipeline
- :doc:`backtesting` — evaluate a trained model on historical data
- :doc:`advanced_customization` — plug in custom models, features, and pipelines