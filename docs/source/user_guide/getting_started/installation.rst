Installation
============

This page covers how to install OpenSTEF, verify your installation, choose the right packages for your use case, and resolve common issues.

System Requirements
-------------------

- **Python**: >=3.12, <4.0
- **Operating System**: Linux, macOS, or Windows
- **Package manager**: pip, uv, or conda

Installing OpenSTEF
-------------------

OpenSTEF is distributed as a set of composable packages. The ``openstef`` meta-package installs everything: ``openstef-beam``, ``openstef-core``, ``openstef-meta``, and ``openstef-models``.

.. tabs::

   .. tab:: pip

      Install the full framework:

      .. code-block:: bash

         pip install openstef

      Or install a specific package:

      .. code-block:: bash

         pip install openstef-core

   .. tab:: uv

      Install the full framework:

      .. code-block:: bash

         uv pip install openstef

      Or add to a project:

      .. code-block:: bash

         uv add openstef

   .. tab:: conda

      OpenSTEF is available via pip within a conda environment:

      .. code-block:: bash

         conda create -n openstef python=3.12
         conda activate openstef
         pip install openstef

.. note::

   If you are migrating from OpenSTEF V3, see :doc:`migration_v3_v4` for breaking changes and upgrade instructions.

Choosing the Right Package
--------------------------

You don't always need the full framework. Install only what you need:

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

   * - Package
     - Purpose
     - Install command
   * - ``openstef-core``
     - Data structures, preprocessing, feature engineering
     - ``pip install openstef-core``
   * - ``openstef-models``
     - Forecasting models (XGBoost, LightGBM, etc.)
     - ``pip install openstef-models``
   * - ``openstef-beam``
     - Backtesting, evaluation, analysis, and metrics
     - ``pip install openstef-beam``
   * - ``openstef-meta``
     - Meta models combining multiple forecasters
     - ``pip install openstef-meta``
   * - ``openstef``
     - Everything above (meta-package)
     - ``pip install openstef``

.. mermaid:: /diagrams/user_guide/getting_started/installation_diagram_1.mmd

Optional Extras
---------------

Several packages offer optional extras for specific functionality:

**openstef-models**

.. code-block:: bash

   # LightGBM model support
   pip install "openstef-models[lgbm]"

   # XGBoost CPU-optimized (recommended for Linux/Windows)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU support
   pip install "openstef-models[xgb-gpu]"

   # Hyperparameter tuning with Optuna
   pip install "openstef-models[tuning]"

**openstef-beam**

.. code-block:: bash

   # All optional features (baselines + S3 support)
   pip install "openstef-beam[all]"

   # Baseline models for comparison
   pip install "openstef-beam[baselines]"

**openstef-core**

.. code-block:: bash

   # Benchmark datasets from Hugging Face
   pip install "openstef-core[benchmark]"

You can combine multiple extras:

.. code-block:: bash

   pip install "openstef-models[lgbm,xgb-cpu,tuning]"

Verifying Your Installation
---------------------------

After installation, verify that packages are correctly installed:

.. code-block:: python

   import openstef_core
   print(f"openstef-core: {openstef_core.__version__}")

   import openstef_beam
   print(f"openstef-beam: {openstef_beam.__version__}")

   import openstef_models
   print(f"openstef-models: {openstef_models.__version__}")

A quick functional check that core data structures work:

.. code-block:: python

   import pandas as pd
   from openstef_core.data import TimeSeriesDataset

   # Create a minimal dataset to confirm everything loads
   df = pd.DataFrame({
       "timestamp": pd.date_range("2024-01-01", periods=24, freq="h"),
       "load": range(24),
   })
   print("Installation verified successfully!")

Troubleshooting
---------------

Missing optional dependency
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see a ``MissingExtraError`` like:

.. code-block:: text

   Optional package lightgbm is missing. Please install it to use this module
   using `pip install lightgbm` or install all optional features using
   `pip install openstef-models[lgbm]`.

This means you're using functionality that requires an optional extra. Install the indicated extra to resolve it.

Python version mismatch
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF V4 requires **Python 3.12 or higher**. If you see installation failures, check your Python version:

.. code-block:: bash

   python --version

If you're on an older version, upgrade Python or use a tool like ``pyenv`` to manage multiple versions:

.. code-block:: bash

   pyenv install 3.12
   pyenv local 3.12

Conflicting dependencies
^^^^^^^^^^^^^^^^^^^^^^^^

If you encounter dependency conflicts, try installing in a clean virtual environment:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   pip install openstef

XGBoost platform issues
^^^^^^^^^^^^^^^^^^^^^^^

On Linux and Windows, use the CPU-optimized build for better compatibility:

.. code-block:: bash

   pip install "openstef-models[xgb-cpu]"

On macOS, the standard ``xgboost`` package is used automatically (the ``xgb-cpu`` extra also works on macOS but installs the regular package).

Import errors after installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Note that package names use hyphens (``openstef-core``) but Python imports use underscores (``openstef_core``):

.. code-block:: python

   # Correct
   import openstef_core

   # Wrong - will raise ImportError
   # import openstef-core

Development Installation
------------------------

To contribute to OpenSTEF or work with the source code:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

This installs the package in editable mode with development dependencies (testing, linting, documentation tools).

Next Steps
----------

With OpenSTEF installed, you're ready to start forecasting. Continue with the other pages in this getting started guide to learn about configuring your first forecast and understanding the library's core concepts.