Installation
============

This page covers everything you need to install OpenSTEF: system requirements,
installation options ranging from a single meta-package to individual components,
optional feature extras, and steps to verify your environment is working correctly.
Once installed, head to :doc:`quickstart` for the fastest path to your first forecast.

.. note::

   OpenSTEF requires **Python 3.12 or later** (Python < 4.0).

----

System Requirements
-------------------

Before installing, confirm your environment meets the following requirements:

- **Python**: ``>=3.12, <4.0``
- **Operating system**: Linux, macOS, or Windows
- **pip**: 21.0 or later (run ``pip install --upgrade pip`` if unsure)

A virtual environment is strongly recommended to avoid dependency conflicts.

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

----

Installing OpenSTEF
-------------------

Full installation
^^^^^^^^^^^^^^^^^

The simplest way to get started is the ``openstef`` meta-package, which pulls in
all sub-packages and their default dependencies in one command:

.. code-block:: bash

   pip install openstef

This installs the following four packages together:

- ``openstef-core`` — data structures, feature engineering, and shared utilities
- ``openstef-models`` — forecasting model implementations (LightGBM by default)
- ``openstef-beam`` — backtesting, evaluation, analysis, and metrics (BEAM)
- ``openstef-meta`` — meta-model layer that combines the above

For most users this is the right starting point.

Individual packages
^^^^^^^^^^^^^^^^^^^

If you only need a subset of the functionality — for example, you are integrating
OpenSTEF into an existing pipeline that already handles evaluation — you can install
packages individually:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Forecasting models (requires openstef-core)
   pip install openstef-models

   # Backtesting and evaluation (requires openstef-core)
   pip install openstef-beam

   # Meta-models (requires openstef-beam, openstef-core, openstef-models)
   pip install openstef-meta

.. note::

   ``openstef-models`` depends on ``openstef-beam`` and ``openstef-core``, so
   installing it will pull those in automatically. You rarely need to install
   ``openstef-core`` or ``openstef-beam`` in isolation unless you are building
   tooling on top of the lower-level APIs.

----

Optional Dependencies
---------------------

Several packages expose *extras* that activate optional features. Install them
by appending the extra name in square brackets.

openstef-models extras
^^^^^^^^^^^^^^^^^^^^^^

By default ``openstef-models`` installs with LightGBM support. XGBoost and GPU
variants are available as extras:

.. code-block:: bash

   # LightGBM (included by default, explicit install also works)
   pip install "openstef-models[lgbm]"

   # XGBoost on CPU (Linux and Windows use the CPU-optimised build automatically)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU support
   pip install "openstef-models[xgb-gpu]"

.. note::

   ``xgb-cpu`` and ``xgb-gpu`` are mutually exclusive. Choose the one that
   matches your hardware. On macOS, ``xgb-cpu`` installs the standard
   ``xgboost`` package; on Linux and Windows it installs ``xgboost-cpu`` for a
   leaner footprint.

openstef-beam extras
^^^^^^^^^^^^^^^^^^^^

``openstef-beam`` ships optional support for baseline models and cloud storage:

.. code-block:: bash

   # Baseline models (pulls in openstef-meta and openstef-models[lgbm])
   pip install "openstef-beam[baselines]"

   # Cloud storage via s3fs, plus baselines
   pip install "openstef-beam[all]"

Installing everything with all extras
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To reproduce a fully-featured development environment:

.. code-block:: bash

   pip install "openstef[all]"

   # Or, more explicitly:
   pip install \
     "openstef-models[lgbm,xgb-cpu]" \
     "openstef-beam[all]"

----

Verifying the Installation
--------------------------

After installation, confirm that the packages import correctly and check their
versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam
   import openstef_meta

   for pkg in (openstef_core, openstef_models, openstef_beam, openstef_meta):
       print(pkg.__name__, pkg.__version__)

A successful run prints four version strings without raising any
``ModuleNotFoundError``. If a package is missing, the error message will tell
you exactly which ``pip install`` command to run.

You can also do a quick smoke-test to confirm that the model layer is reachable:

.. code-block:: python

   from openstef_models.model.lgbm import LGBMForecaster

   model = LGBMForecaster()
   print("LGBMForecaster instantiated successfully:", model)

----

Troubleshooting
---------------

``ModuleNotFoundError: No module named 'lightgbm'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

LightGBM is an optional dependency of ``openstef-models``. Install it explicitly:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

   # Or install the full meta-package which includes it by default:
   pip install openstef

``MissingExtraError`` at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF raises a ``MissingExtraError`` when you call a function that requires
an optional extra that is not installed. The error message includes the exact
``pip install`` command needed, for example::

   MissingExtraError: Optional package baselines is missing. Please install it
   to use this module using `pip install baselines` or install all optional
   features using `pip install openstef-beam[all]`.

Follow the instruction in the message, then re-run your code.

Dependency conflicts with an existing environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If ``pip`` reports resolver conflicts, try installing in a fresh virtual
environment (see `System Requirements`_ above). Alternatively, use
``pip install --upgrade openstef`` to let pip resolve the latest compatible set.

``pip`` version too old
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF packages use modern ``pyproject.toml`` metadata. If you see parsing
errors during installation, upgrade pip first:

.. code-block:: bash

   pip install --upgrade pip
   pip install openstef

XGBoost GPU build fails on CPU-only machines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``xgb-cpu`` instead of ``xgb-gpu``:

.. code-block:: bash

   pip install "openstef-models[xgb-cpu]"

----

Next Steps
----------

With OpenSTEF installed you are ready to start forecasting:

- :doc:`quickstart` — run a minimal forecast in under five minutes
- :doc:`first_forecast` — a step-by-step walkthrough of your first full forecast
- :doc:`backtesting` — evaluate a trained model on historical data
- :doc:`advanced_customization` — plug in custom models and feature engineering