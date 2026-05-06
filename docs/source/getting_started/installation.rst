Installation
============

This page covers everything you need to get OpenSTEF installed: system requirements, the different packages available, optional extras, and how to confirm your installation is working.

Once you have OpenSTEF installed, head over to the :doc:`quickstart` page to run your first forecast.

System Requirements
-------------------

OpenSTEF requires **Python 3.12 or later** (Python < 4.0). No other system-level dependencies are needed beyond a working Python environment and ``pip``.

.. note::
   Using a virtual environment (``venv``, ``conda``, or similar) is strongly recommended to avoid dependency conflicts with other projects.

Standard Installation
---------------------

The simplest way to get started is to install the ``openstef`` meta-package, which pulls in the full framework:

.. code-block:: bash

   pip install openstef

This single command installs four packages:

- **openstef-core** — shared data structures, base classes, and utilities used across the framework
- **openstef-models** — forecasting model implementations (LightGBM, XGBoost, and others)
- **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics (BEAM) tooling
- **openstef-meta** — meta-model layer that composes the above into end-to-end pipelines

If you only need part of the framework, see `Installing Individual Packages`_ below.

Installing Individual Packages
-------------------------------

Each OpenSTEF package can be installed independently. This is useful when you want to minimise your dependency footprint or when deploying components separately.

**openstef-core** — data structures and shared utilities:

.. code-block:: bash

   pip install openstef-core

Key dependencies: ``joblib``, ``numpy``, ``pandas``, ``pyarrow``, ``pydantic``.

**openstef-beam** — backtesting, evaluation, and metrics:

.. code-block:: bash

   pip install openstef-beam

Key dependencies: ``openstef-core``, ``plotly``, ``pyyaml``, ``scoringrules``, ``tqdm``.

**openstef-models** — forecasting models:

.. code-block:: bash

   pip install openstef-models

Key dependencies: ``openstef-core``, ``openstef-beam``, ``holidays``, ``mlflow-skinny``, ``pvlib``.

**openstef-meta** — meta-model pipelines:

.. code-block:: bash

   pip install openstef-meta

Key dependencies: ``openstef-beam``, ``openstef-core``, ``openstef-models[lgbm]``.

Optional Dependencies
---------------------

Several packages expose optional extras that activate additional functionality. Install them by appending the extra name in square brackets.

openstef-models extras
^^^^^^^^^^^^^^^^^^^^^^

The ``openstef-models`` package ships without a specific gradient-boosting backend by default. Choose the one that fits your hardware:

.. code-block:: bash

   # LightGBM backend (recommended for most use cases)
   pip install "openstef-models[lgbm]"

   # XGBoost — CPU-optimised build (Linux, Windows, macOS)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost — GPU build
   pip install "openstef-models[xgb-gpu]"

You can combine extras:

.. code-block:: bash

   pip install "openstef-models[lgbm,xgb-cpu]"

openstef-beam extras
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Baseline models (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # All optional features, including S3 filesystem support
   pip install "openstef-beam[all]"

The ``[all]`` extra adds ``s3fs`` for reading and writing data directly to Amazon S3, in addition to the baseline models.

.. note::
   If you attempt to use a feature that requires a missing extra, OpenSTEF raises a ``MissingExtraError`` with an explicit message telling you exactly which ``pip install`` command to run.

Installing for Development
--------------------------

To contribute to OpenSTEF or run the test suite, clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

Editable mode means changes to the source files are reflected immediately without reinstalling.

Verifying the Installation
--------------------------

After installation, confirm that the packages are importable and check their versions:

.. code-block:: python

   import openstef_core
   import openstef_beam
   import openstef_models
   import openstef_meta

   print(openstef_core.__version__)
   print(openstef_beam.__version__)
   print(openstef_models.__version__)
   print(openstef_meta.__version__)

All four lines should print a version string without raising an ``ImportError``. If a package is missing, the error message will indicate which ``pip install`` command to run.

You can also verify from the command line:

.. code-block:: bash

   python -c "import openstef_core; print(openstef_core.__version__)"

Troubleshooting
---------------

**ImportError after installation**
   Make sure you are running Python inside the same virtual environment where you ran ``pip install``. Running ``which python`` (macOS/Linux) or ``where python`` (Windows) should point to your environment's interpreter.

**Version conflicts**
   If pip reports dependency conflicts, try installing inside a fresh virtual environment:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate   # Windows: .venv\Scripts\activate
      pip install openstef

**LightGBM or XGBoost not found at runtime**
   These backends are optional. Install the appropriate extra as described in `Optional Dependencies`_ above.

**MissingExtraError at runtime**
   OpenSTEF will tell you exactly what to install. Follow the message — for example:

   .. code-block:: bash

      pip install "openstef-beam[all]"

Next Steps
----------

With OpenSTEF installed, the :doc:`quickstart` page walks you through running your first forecast in a few lines of code.