Installation
============

This page covers everything you need to install OpenSTEF: system requirements, the
different installation options, optional extras for specific model backends, and how to
verify that your environment is set up correctly. If you are ready to write your first
forecast after installing, head over to :doc:`quickstart`.

System Requirements
-------------------

OpenSTEF requires **Python 3.12 or later** (Python < 4.0). No special hardware is
needed for most use cases. GPU support is available for XGBoost models through an
optional extra described below.

It is strongly recommended to install OpenSTEF inside a dedicated virtual environment:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

Standard Installation
---------------------

The simplest way to get everything is the ``openstef`` meta-package, which pulls in all
sub-packages in one step:

.. code-block:: bash

   pip install openstef

This single command installs the four packages that make up the framework:

- **openstef-core** — shared data structures, base classes, and dataset utilities
- **openstef-models** — forecasting models (LightGBM, XGBoost, and more)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-models that combine the above

For most users this is the right starting point. The sections below explain when you
might want a narrower install instead.

Installing Individual Packages
------------------------------

If you only need part of the framework — for example, you are integrating OpenSTEF
models into an existing pipeline and do not need the backtesting tooling — you can
install packages individually:

.. code-block:: bash

   pip install openstef-core          # shared utilities only
   pip install openstef-models        # models + core
   pip install openstef-beam          # BEAM evaluation + core
   pip install openstef-meta          # meta-models (pulls in everything)

Each package declares its own dependencies, so pip will fetch exactly what is needed.

Optional Extras
---------------

Several packages expose optional extras that activate additional model backends or
integrations.

Model backends (``openstef-models``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default ``openstef-models`` ships without a heavy gradient-boosting backend so that
you can choose the one that fits your hardware:

.. code-block:: bash

   # LightGBM backend (recommended for most CPU workloads)
   pip install "openstef-models[lgbm]"

   # XGBoost — CPU-optimised build (Linux, Windows, macOS)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost — GPU build (CUDA required)
   pip install "openstef-models[xgb-gpu]"

You can combine extras in a single command:

.. code-block:: bash

   pip install "openstef-models[lgbm,xgb-cpu]"

BEAM extras (``openstef-beam``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Baseline models (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # S3 filesystem support + baselines
   pip install "openstef-beam[all]"

The ``[all]`` extra is convenient when you want the full BEAM feature set including
remote data access via S3.

.. note::

   If you installed the top-level ``openstef`` meta-package, the LightGBM backend is
   already included because ``openstef-meta`` depends on
   ``openstef-models[lgbm]``.

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

All four lines should print a version string without raising an ``ImportError``. If a
package is missing you will see a clear error message — see the troubleshooting section
below.

You can also do a quick functional check by loading one of the built-in datasets:

.. code-block:: python

   from openstef_core.datasets import load_example_dataset

   df = load_example_dataset()
   print(df.head())

A successful run prints the first few rows of a time-series DataFrame and confirms that
the core package is working end-to-end.

Troubleshooting
---------------

``ImportError: No module named 'lightgbm'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

LightGBM is an optional dependency. Install it explicitly:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

``MissingExtraError`` at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF raises ``openstef_core.exceptions.MissingExtraError`` when you call a feature
that requires an optional extra that is not installed. The error message tells you
exactly which package to add, for example::

   Optional package openstef-beam[baselines] is missing. Please install it to use
   this module using `pip install openstef-beam[baselines]` or install all optional
   features using `pip install openstef-beam[all]`.

Follow the instruction in the message and re-run.

``pip`` resolves an incompatible environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF requires Python ≥ 3.12. If pip reports a resolution error, check your Python
version first:

.. code-block:: bash

   python --version

If the version is below 3.12, create a new virtual environment with a supported
interpreter before installing.

XGBoost GPU build fails to import
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``xgb-gpu`` extra requires a CUDA-capable GPU and a compatible CUDA toolkit. If
the import fails with a CUDA-related error, either install the CPU build instead or
consult the `XGBoost GPU documentation <https://xgboost.readthedocs.io/en/stable/gpu/index.html>`_
for environment setup instructions.

Conflicting package versions in an existing environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are adding OpenSTEF to an environment that already has numpy, pandas, or
XGBoost installed, version conflicts can arise. The safest approach is always a fresh
virtual environment. If that is not possible, use ``pip install --upgrade openstef``
and inspect the conflict report that pip prints.

Next Steps
----------

With OpenSTEF installed you are ready to run your first forecast. The
:doc:`quickstart` page shows the minimal working example, and :doc:`first_forecast`
walks through the same process step by step with detailed explanations. If you want to
evaluate model performance on historical data, see :doc:`backtesting`.