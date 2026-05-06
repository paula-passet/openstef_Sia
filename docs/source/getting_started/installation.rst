Installation
============

This page covers everything you need to install OpenSTEF: system requirements, the
recommended full installation, installing individual packages for leaner environments,
optional extras for specific model backends, and steps to verify that your setup is
working. Common installation problems and their fixes are collected at the bottom.

Once you have OpenSTEF installed, head to :doc:`quickstart` for the fastest path to
your first forecast, or :doc:`first_forecast` for a guided walkthrough.

----

System Requirements
-------------------

- **Python** ≥ 3.12, < 4.0
- A supported operating system: Linux, macOS, or Windows
- ``pip`` ≥ 21 (older versions may struggle with dependency resolution)

No special hardware is required for the default CPU-based model backends. GPU support
is available as an optional extra and is described below.

----

Standard Installation
---------------------

The simplest way to get everything is the ``openstef`` meta-package, which pulls in
all sub-packages and their default dependencies in a single command:

.. code-block:: bash

   pip install openstef

This installs four packages:

- **openstef-core** — shared data structures, base classes, and dataset utilities
- **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics (BEAM) pipelines
- **openstef-models** — forecasting model implementations (LightGBM by default)
- **openstef-meta** — meta-model layer that combines the above

For most users this is the right starting point. If you are working in a constrained
environment — a Docker image, a CI pipeline, or a serverless function — the individual
package installs described in the next section let you keep the footprint small.

.. note::

   It is good practice to install OpenSTEF inside a virtual environment:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate   # Windows: .venv\Scripts\activate
      pip install openstef

----

Installing Individual Packages
-------------------------------

Each sub-package can be installed on its own when you only need part of the framework.

**openstef-core** — data structures and base utilities, no model code:

.. code-block:: bash

   pip install openstef-core

**openstef-beam** — backtesting and evaluation pipelines (depends on ``openstef-core``):

.. code-block:: bash

   pip install openstef-beam

**openstef-models** — model implementations (depends on ``openstef-beam`` and
``openstef-core``):

.. code-block:: bash

   pip install openstef-models

**openstef-meta** — meta-model layer (depends on all of the above):

.. code-block:: bash

   pip install openstef-meta

----

Optional Extras
---------------

Several model backends and integrations are gated behind optional extras so that you
only pay the dependency cost when you actually need them.

Model backends (``openstef-models``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

LightGBM is included by default. XGBoost must be requested explicitly:

.. code-block:: bash

   # XGBoost on CPU (Linux and Windows use the optimised xgboost-cpu build)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU support
   pip install "openstef-models[xgb-gpu]"

   # LightGBM (already included in the default install, but explicit if needed)
   pip install "openstef-models[lgbm]"

BEAM extras (``openstef-beam``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Baseline models (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # Remote storage support via s3fs
   pip install "openstef-beam[all]"

The ``[all]`` extra for ``openstef-beam`` bundles both ``[baselines]`` and S3 support.

.. note::

   If you try to use a feature that requires a missing extra, OpenSTEF raises a
   ``MissingExtraError`` with an exact ``pip install`` command to fix it. You will
   never need to guess which extra to add.

----

Verifying the Installation
--------------------------

After installing, confirm that the packages are importable and check their versions:

.. code-block:: python

   import openstef_core
   import openstef_beam
   import openstef_models
   import openstef_meta

   print(openstef_core.__version__)
   print(openstef_beam.__version__)
   print(openstef_models.__version__)
   print(openstef_meta.__version__)

All four lines should print a version string without raising an ``ImportError``. If
any import fails, see the troubleshooting section below.

You can also do a quick end-to-end smoke test using one of the built-in datasets:

.. code-block:: python

   from openstef_core.datasets import load_example_dataset

   df = load_example_dataset()
   print(df.head())

A successful print confirms that the core data layer is working correctly.

----

Troubleshooting
---------------

``ImportError: No module named 'openstef_...'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The package is not installed in the Python environment that is currently active. Check
which interpreter you are using:

.. code-block:: bash

   which python   # Linux / macOS
   where python   # Windows

Make sure you activated the virtual environment where you ran ``pip install openstef``
before launching Python or your notebook kernel.

``MissingExtraError`` at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF raises this when you call functionality that depends on an optional extra you
have not installed. The error message contains the exact ``pip install`` command to
resolve it. For example:

.. code-block:: text

   MissingExtraError: Optional package xgb-cpu is missing. Please install it to use
   this module using `pip install xgb-cpu` or install all optional features using
   `pip install openstef-models[all]`.

Run the suggested command, then retry.

Dependency conflicts with an existing environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF requires Python ≥ 3.12. If your environment is running an older Python
version, create a fresh environment with the correct version:

.. code-block:: bash

   python3.12 -m venv .venv-openstef
   source .venv-openstef/bin/activate
   pip install openstef

If you are using ``conda``:

.. code-block:: bash

   conda create -n openstef python=3.12
   conda activate openstef
   pip install openstef

Slow or failing dependency resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Older versions of ``pip`` can time out or produce incorrect resolution results with
complex dependency trees. Upgrade ``pip`` first:

.. code-block:: bash

   pip install --upgrade pip
   pip install openstef

XGBoost GPU build fails to import
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``[xgb-gpu]`` extra requires a compatible CUDA toolkit to be installed on the
host. Verify your CUDA version with ``nvidia-smi`` and consult the
`XGBoost installation documentation <https://xgboost.readthedocs.io/en/stable/install.html>`_
for the matching build. If GPU support is not strictly required, use
``openstef-models[xgb-cpu]`` instead.

----

Next Steps
----------

With OpenSTEF installed you are ready to start forecasting:

- :doc:`quickstart` — run a forecast in under five minutes with minimal code
- :doc:`first_forecast` — a step-by-step tutorial that explains each stage of the pipeline
- :doc:`backtesting` — evaluate a trained model against historical data
- :doc:`advanced_customization` — plug in custom models and components