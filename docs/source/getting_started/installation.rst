Installation
============

This page covers everything you need to install OpenSTEF on your system — from a
simple one-line install to fine-grained control over individual packages and optional
extras. Once installation is complete, see :doc:`quickstart` to run your first
forecast in minutes.

.. contents:: On this page
   :local:
   :depth: 2

System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python** 3.12 or later (Python < 3.12 is not supported)
- **pip** 23.0 or later is recommended
- A virtual environment manager such as ``venv``, ``conda``, or ``uv`` (strongly
  recommended to avoid dependency conflicts)

OpenSTEF runs on Linux, macOS, and Windows.

.. note::
   Using a dedicated virtual environment is strongly recommended. OpenSTEF pulls in
   several scientific computing libraries (NumPy, pandas, PyArrow, etc.) and
   isolating them prevents version conflicts with other projects.


Standard Installation
---------------------

For most users, the simplest approach is to install the ``openstef`` meta-package,
which bundles the complete framework in a single command:

.. code-block:: bash

   pip install openstef

This installs four constituent packages together:

- **openstef-core** — data structures, feature engineering, and shared utilities
- **openstef-models** — forecasting model implementations (LightGBM, XGBoost, and more)
- **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics (BEAM)
- **openstef-meta** — meta-model layer that combines the above

After the command completes, jump straight to :doc:`quickstart` to verify everything
works end-to-end.


Installing Individual Packages
------------------------------

OpenSTEF is designed as a library of composable packages. If you only need a subset
of the functionality — for example, you want to run backtests without pulling in the
full model suite — you can install packages individually:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # BEAM evaluation and backtesting tools
   pip install openstef-beam

   # Forecasting models
   pip install openstef-models

   # Meta-models (requires openstef-beam, openstef-core, and openstef-models[lgbm])
   pip install openstef-meta

Each package declares its own dependencies, so pip will pull in only what is needed
for that package.


Optional Dependencies
---------------------

Several packages expose optional extras that activate additional features. Install
them using the ``[extra]`` syntax.

openstef-models extras
^^^^^^^^^^^^^^^^^^^^^^

The ``openstef-models`` package ships with optional boosting backends:

.. code-block:: bash

   # LightGBM backend (recommended for most use cases)
   pip install "openstef-models[lgbm]"

   # XGBoost backend — CPU-optimised build (Linux, macOS, Windows)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost backend — GPU build
   pip install "openstef-models[xgb-gpu]"

.. note::
   The ``lgbm`` extra requires ``lightgbm >= 4.6``. The ``xgb-cpu`` and ``xgb-gpu``
   extras require ``xgboost >= 3, < 4``. GPU support requires a CUDA-capable device
   and a compatible CUDA toolkit.

openstef-beam extras
^^^^^^^^^^^^^^^^^^^^

The ``openstef-beam`` package has two optional extras:

.. code-block:: bash

   # Baseline model support (pulls in openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # All extras, including S3 filesystem support via s3fs
   pip install "openstef-beam[all]"

Installing everything with all extras
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install the complete framework with every optional feature enabled, combine the
meta-package with the relevant extras:

.. code-block:: bash

   pip install openstef "openstef-beam[all]" "openstef-models[lgbm]"


Development Installation
------------------------

If you intend to contribute to OpenSTEF or want to run the test suite, clone the
repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

Editable mode means changes to the source files are reflected immediately without
reinstalling.


Verifying the Installation
--------------------------

After installation, confirm that the packages are importable and check their versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam
   import openstef_meta

   # Print versions to confirm correct packages are loaded
   print(openstef_core.__version__)
   print(openstef_models.__version__)
   print(openstef_beam.__version__)
   print(openstef_meta.__version__)

If all four lines print version strings without errors, the installation is complete.
You can also run a quick sanity check from the command line:

.. code-block:: bash

   python -c "import openstef_core; print('openstef-core OK')"
   python -c "import openstef_models; print('openstef-models OK')"
   python -c "import openstef_beam; print('openstef-beam OK')"


Troubleshooting
---------------

``ModuleNotFoundError: No module named 'openstef_core'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This usually means the package was installed into a different Python environment than
the one currently active. Check which Python interpreter is in use:

.. code-block:: bash

   which python   # Linux / macOS
   where python   # Windows

Make sure you activated the correct virtual environment before installing, and that
the same environment is active when you run your code.

``MissingExtraError`` when importing a module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF raises ``MissingExtraError`` when you try to use a feature that requires an
optional extra that is not installed. The error message tells you exactly which
package to install, for example:

.. code-block:: text

   Optional package lightgbm is missing. Please install it to use this module
   using `pip install lightgbm` or install all optional features using
   `pip install openstef-models[all]`.

Follow the instruction in the message, or install all extras at once:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

Dependency conflicts on install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If pip reports resolver conflicts, try upgrading pip first:

.. code-block:: bash

   pip install --upgrade pip
   pip install openstef

If conflicts persist, create a fresh virtual environment and install there. Mixing
OpenSTEF with other scientific stacks (e.g., a pre-existing TensorFlow or PyTorch
environment) can cause version clashes.

XGBoost GPU build fails to import
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``xgb-gpu`` extra requires a compatible CUDA installation. If you see a CUDA
library error at import time, verify that:

1. Your GPU driver supports the CUDA version that XGBoost was compiled against.
2. The CUDA toolkit is on your ``LD_LIBRARY_PATH`` (Linux) or ``PATH`` (Windows).
3. You are not accidentally using the CPU build alongside the GPU build — remove one
   before installing the other.

If GPU support is not essential, switch to the CPU build:

.. code-block:: bash

   pip uninstall xgboost
   pip install "openstef-models[xgb-cpu]"


Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — run a minimal working forecast in a few lines of code
- :doc:`first_forecast` — a step-by-step tutorial that explains each stage of the
  forecasting pipeline
- :doc:`backtesting` — learn how to evaluate and compare models on historical data
- :doc:`advanced_customization` — extend OpenSTEF with custom models and pipelines