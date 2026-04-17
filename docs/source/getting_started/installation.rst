Installation
============

This page covers everything you need to install OpenSTEF on your system: system
requirements, the different installation options, optional dependencies for specific
model backends, and how to verify that your installation is working. If you run into
problems, the :ref:`troubleshooting` section at the bottom addresses the most common
issues.

Once you have OpenSTEF installed, head to :doc:`quickstart` for the fastest path to
your first forecast, or :doc:`first_forecast` for a more detailed walkthrough.

.. contents:: On this page
   :local:
   :depth: 2


System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python 3.12 or later** (Python < 3.12 is not supported)
- **pip** (comes with Python; use a recent version — run ``pip install --upgrade pip`` if in doubt)
- A virtual environment is strongly recommended (``venv``, ``conda``, or similar)

OpenSTEF is a pure-Python library and does not require any compiled system libraries
beyond those pulled in automatically by its dependencies. It runs on Linux, macOS, and
Windows.


Installing OpenSTEF
-------------------

The simplest way to get everything is to install the top-level ``openstef`` meta-package.
This pulls in all four sub-packages in one command:

.. code-block:: bash

   pip install openstef

That single command installs:

- **openstef-core** — shared data structures, datasets, and utilities used across the framework
- **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics (BEAM) pipelines
- **openstef-models** — forecasting model implementations (XGBoost, LightGBM, and more)
- **openstef-meta** — meta-models and ensemble combiners

This is the recommended starting point for new users and for production environments
where you want the full feature set available.


Installing Individual Packages
------------------------------

If you only need part of the framework — for example, you are integrating OpenSTEF
models into an existing pipeline and do not need the backtesting tooling — you can
install sub-packages individually:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # BEAM backtesting and evaluation pipelines
   pip install openstef-beam

   # Model implementations
   pip install openstef-models

   # Meta/ensemble models
   pip install openstef-meta

Each sub-package declares its own dependencies, so pip will resolve everything it
needs automatically.


Optional Dependencies
---------------------

Some features require additional packages that are not installed by default, either
because they are large or because they have platform-specific variants (e.g. GPU
support).

openstef-models extras
^^^^^^^^^^^^^^^^^^^^^^

The ``openstef-models`` package ships three optional extras for different model backends:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - What it installs
   * - ``openstef-models[lgbm]``
     - LightGBM >= 4.6 — enables LightGBM-based forecasters and combiners
   * - ``openstef-models[xgb-cpu]``
     - XGBoost >= 3 (CPU build) — recommended for Linux and Windows desktops
   * - ``openstef-models[xgb-gpu]``
     - XGBoost >= 3 (GPU build) — enables CUDA-accelerated training

Install an extra by appending it in square brackets:

.. code-block:: bash

   # LightGBM support
   pip install "openstef-models[lgbm]"

   # XGBoost CPU support
   pip install "openstef-models[xgb-cpu]"

   # Both at once
   pip install "openstef-models[lgbm,xgb-cpu]"

.. note::

   If you installed the top-level ``openstef`` package, the model extras are **not**
   included automatically. You still need to install the backend you intend to use
   explicitly.

openstef-beam extras
^^^^^^^^^^^^^^^^^^^^

The ``openstef-beam`` package has two optional extras:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - What it installs
   * - ``openstef-beam[baselines]``
     - Pulls in ``openstef-meta`` and ``openstef-models`` to enable baseline comparisons in backtesting
   * - ``openstef-beam[all]``
     - Everything in ``baselines`` plus ``s3fs`` for reading/writing data directly from Amazon S3

.. code-block:: bash

   pip install "openstef-beam[all]"


Verifying Your Installation
---------------------------

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

You can also do a quick smoke test by importing a core data structure:

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset
   import pandas as pd

   # Build a minimal dataset to confirm the import chain works
   index = pd.date_range("2024-01-01", periods=48, freq="15min")
   df = pd.DataFrame({"load": range(48)}, index=index)
   dataset = ForecastInputDataset(df)
   print("OpenSTEF is installed and working:", dataset)

If both blocks run without errors, your installation is complete.


.. _troubleshooting:

Troubleshooting
---------------

Python version error
^^^^^^^^^^^^^^^^^^^^

If you see an error such as::

   ERROR: Package 'openstef' requires a different Python: 3.11.x not in '>=3.12,<4.0'

your active Python interpreter is too old. Check which Python pip is using:

.. code-block:: bash

   pip --version
   python --version

Create a new virtual environment with Python 3.12 or later and install OpenSTEF there.

Missing optional dependency at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you encounter a ``MissingExtraError`` at runtime, for example::

   MissingExtraError: Optional package lgbm is missing. Please install it to use this
   module using `pip install lgbm` or install all optional features using
   `pip install openstef-models[all]`.

install the indicated extra:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

OpenSTEF raises ``MissingExtraError`` (from ``openstef_core.exceptions``) rather than
a bare ``ImportError`` so that the message always tells you exactly which ``pip``
command to run.

Conflicting XGBoost builds
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Installing both ``openstef-models[xgb-cpu]`` and ``openstef-models[xgb-gpu]`` in the
same environment will cause a conflict because they pin different XGBoost wheel
variants. Choose one based on your hardware:

- CPU-only machines (including most CI environments): ``xgb-cpu``
- Machines with a CUDA-capable GPU: ``xgb-gpu``

If you need to switch, uninstall the current variant first:

.. code-block:: bash

   pip uninstall xgboost xgboost-cpu
   pip install "openstef-models[xgb-gpu]"

Stale pip cache
^^^^^^^^^^^^^^^

Occasionally pip serves a cached wheel that is incompatible with your platform.
Clear the cache and retry:

.. code-block:: bash

   pip cache purge
   pip install --no-cache-dir openstef

Editable / development install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are contributing to OpenSTEF or want to run the latest unreleased code, clone
the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

.. note::

   The development install does not automatically install optional model backends.
   Run ``pip install "openstef-models[lgbm,xgb-cpu]"`` separately if you need them
   during development.


Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — run a complete forecast in under five minutes
- :doc:`first_forecast` — a step-by-step tutorial that explains each part of the pipeline
- :doc:`backtesting` — evaluate a trained model on historical data
- :doc:`advanced_customization` — plug in custom models and feature engineering