Installation
============

This page covers how to install OpenSTEF, including system requirements, package options, optional dependencies, and verification steps. For what to do after installation, see the :doc:`quickstart` guide.

System Requirements
-------------------

- **Python**: >=3.12, <4.0
- **Operating System**: Linux, macOS, or Windows
- **Disk space**: ~500 MB (with all optional dependencies)

Quick Install
-------------

Install the complete OpenSTEF framework with all packages:

.. tabs::

   .. tab:: pip

      .. code-block:: bash

         pip install openstef

   .. tab:: uv

      .. code-block:: bash

         uv add openstef

   .. tab:: conda

      .. code-block:: bash

         # Install from PyPI within a conda environment
         conda create -n openstef python=3.12
         conda activate openstef
         pip install openstef

The ``openstef`` meta-package installs all core packages: ``openstef-beam``, ``openstef-core``, ``openstef-meta``, and ``openstef-models``.

Individual Packages
-------------------

If you only need specific functionality, install packages individually to keep your environment lean:

.. code-block:: bash

   # Backtesting, Evaluation, Analysis and Metrics
   pip install openstef-beam

   # Core data processing and pipeline logic
   pip install openstef-core

   # Model implementations (XGBoost, LightGBM, etc.)
   pip install openstef-models

   # Meta-models (ensemble and stacking)
   pip install openstef-meta

.. mermaid:: /diagrams/user_guide/getting_started/installation_diagram_1.mmd

Optional Extras
---------------

Each package provides optional extras for specific use cases. Install them with bracket syntax:

**openstef-beam**

.. code-block:: bash

   # All optional features (baselines + S3 support)
   pip install openstef-beam[all]

   # Baseline models only
   pip install openstef-beam[baselines]

**openstef-core**

.. code-block:: bash

   # Benchmark datasets from HuggingFace
   pip install openstef-core[benchmark]

**openstef-models**

.. code-block:: bash

   # LightGBM models
   pip install openstef-models[lgbm]

   # Hyperparameter tuning with Optuna
   pip install openstef-models[tuning]

   # XGBoost with CPU acceleration
   pip install openstef-models[xgb-cpu]

   # XGBoost with GPU acceleration
   pip install openstef-models[xgb-gpu]

You can combine multiple extras:

.. code-block:: bash

   pip install openstef-models[lgbm,tuning,xgb-cpu]

.. note::

   On macOS (``darwin``), ``openstef-models[xgb-cpu]`` installs the standard ``xgboost`` package. On Linux and Windows, it installs the optimized ``xgboost-cpu`` variant.

Verifying Your Installation
---------------------------

After installation, verify that packages are correctly installed:

.. code-block:: python

   import openstef_beam
   print(openstef_beam.__version__)

   import openstef_core
   print(openstef_core.__version__)

   import openstef_models
   print(openstef_models.__version__)

If any import fails, see the troubleshooting section below.

Development Installation
------------------------

To install OpenSTEF for development (e.g., contributing or running from source):

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

Troubleshooting
---------------

**ImportError: Optional package X is missing**

OpenSTEF uses lazy imports for optional dependencies. If you see a ``MissingExtraError``, install the required extra:

.. code-block:: text

   Optional package lightgbm is missing. Please install it to use this module
   using `pip install lightgbm` or install all optional features using
   `pip install openstef-models[lgbm]`.

Follow the instructions in the error message to install the missing package.

**Python version mismatch**

OpenSTEF requires Python 3.12 or later. Check your version:

.. code-block:: bash

   python --version

If you're on an older version, use ``pyenv`` or ``conda`` to install Python 3.12+.

**Conflicting dependencies**

If you encounter dependency conflicts, create a fresh virtual environment:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   pip install openstef

**XGBoost installation issues on Linux**

If ``xgboost-cpu`` fails to install, try the standard ``xgboost`` package instead:

.. code-block:: bash

   pip install openstef-models[xgb-gpu]  # installs standard xgboost

**Permission errors**

Use ``--user`` flag or a virtual environment:

.. code-block:: bash

   pip install --user openstef

Next Steps
----------

Once installed, proceed to the :doc:`quickstart` to run your first forecast, or explore the :doc:`concepts` page to understand OpenSTEF's architecture.