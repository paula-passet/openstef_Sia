Installation
============

This page covers everything you need to install OpenSTEF: system requirements,
installation options ranging from a single meta-package to individual components,
optional feature extras, and steps to verify a working setup. If you run into
problems, the :ref:`troubleshooting` section at the bottom addresses the most
common issues.

Once your environment is ready, head to :doc:`quickstart` for the fastest path
to a first forecast, or :doc:`first_forecast` for a step-by-step walkthrough.

.. note::
   OpenSTEF requires **Python 3.12 or later** (``>=3.12,<4.0``). Earlier
   Python versions are not supported.


System Requirements
-------------------

- **Python** ``>=3.12,<4.0``
- **pip** 23+ (ships with Python 3.12; upgrade with ``python -m pip install --upgrade pip``)
- A virtual environment tool such as ``venv``, ``conda``, or ``uv`` (strongly recommended)

No special hardware is required for CPU-based models. GPU acceleration for
XGBoost is available as an optional extra — see `Model Extras`_ below.


Installing OpenSTEF
-------------------

The simplest way to get everything is the ``openstef`` meta-package, which
pulls in all sub-packages in a single command:

.. code-block:: bash

   pip install openstef

This installs the following four packages together:

- **openstef-core** — data structures, feature engineering, and shared utilities
- **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics (BEAM)
- **openstef-models** — forecasting model implementations (LightGBM, XGBoost, …)
- **openstef-meta** — meta-model layer that combines the above

If you prefer a minimal footprint, each package can be installed on its own.


Installing Individual Packages
------------------------------

Install only what your project needs:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # BEAM evaluation framework (depends on openstef-core automatically)
   pip install openstef-beam

   # Model implementations
   pip install openstef-models

   # Meta-models (requires openstef-beam, openstef-core, and openstef-models[lgbm])
   pip install openstef-meta

Key dependencies pulled in automatically by each package:

- **openstef-core**: ``joblib``, ``numpy``, ``pandas``, ``pyarrow``, ``pydantic``
- **openstef-beam**: ``plotly``, ``pyyaml``, ``scoringrules``, ``tqdm``
- **openstef-models**: ``holidays``, ``mlflow-skinny``, ``pvlib``


.. _model-extras:

Model Extras
------------

``openstef-models`` ships several optional extras that gate heavier or
platform-specific dependencies behind an explicit opt-in:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Extra
     - What it installs
   * - ``lgbm``
     - ``lightgbm>=4.6`` — LightGBM gradient boosting
   * - ``xgb-cpu``
     - ``xgboost>=3,<4`` (macOS) / ``xgboost-cpu>=3,<4`` (Linux, Windows)
   * - ``xgb-gpu``
     - ``xgboost>=3,<4`` with GPU support (all platforms)

Install them by appending the extra name in brackets:

.. code-block:: bash

   # LightGBM support
   pip install "openstef-models[lgbm]"

   # XGBoost on CPU (Linux / Windows / macOS)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU acceleration
   pip install "openstef-models[xgb-gpu]"

   # Multiple extras at once
   pip install "openstef-models[lgbm,xgb-cpu]"

.. note::
   The top-level ``openstef`` meta-package installs ``openstef-models`` with
   the ``lgbm`` extra included by default. XGBoost must be added separately if
   you need it.


BEAM Extras
-----------

``openstef-beam`` also exposes optional extras:

.. code-block:: bash

   # Baseline model support (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # All BEAM extras, including S3 filesystem support (s3fs>=2025.5.1)
   pip install "openstef-beam[all]"


Recommended Setup with a Virtual Environment
--------------------------------------------

Using an isolated environment prevents dependency conflicts with other projects.
The example below uses the standard library ``venv`` module:

.. code-block:: bash

   # Create and activate a virtual environment
   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   # .venv\Scripts\activate         # Windows

   # Upgrade pip, then install OpenSTEF
   python -m pip install --upgrade pip
   pip install openstef

``conda`` and ``uv`` work equally well — substitute the environment creation
step as appropriate for your toolchain.


Verifying the Installation
--------------------------

After installation, confirm that the packages import correctly and check their
versions:

.. code-block:: python

   import openstef_core
   import openstef_beam
   import openstef_models
   import openstef_meta

   # Print versions to confirm the expected releases are active
   print(openstef_core.__version__)
   print(openstef_beam.__version__)
   print(openstef_models.__version__)
   print(openstef_meta.__version__)

A successful run prints four version strings without any ``ImportError``. If a
package is missing you will see a clear error message pointing to the missing
dependency — see `Troubleshooting`_ below.


.. _troubleshooting:

Troubleshooting
---------------

**ImportError: No module named 'lightgbm'**

LightGBM is an optional dependency. Install it explicitly:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

----

**ImportError: No module named 'xgboost'**

XGBoost is not installed by default. Choose the variant that matches your
hardware:

.. code-block:: bash

   pip install "openstef-models[xgb-cpu]"   # CPU only
   pip install "openstef-models[xgb-gpu]"   # GPU

----

**MissingExtraError at runtime**

OpenSTEF raises ``openstef_core.exceptions.MissingExtraError`` when code paths
that require an optional extra are reached without that extra being installed.
The error message includes the exact ``pip install`` command needed, for example:

.. code-block:: text

   Optional package baselines is missing. Please install it to use this module
   using `pip install baselines` or install all optional features using
   `pip install openstef-beam[all]`.

Follow the printed instruction, or install all extras at once:

.. code-block:: bash

   pip install "openstef-beam[all]"

----

**Wrong Python version**

OpenSTEF requires Python 3.12 or later. Check your active interpreter:

.. code-block:: bash

   python --version

If the version is below 3.12, switch to a compatible interpreter before
creating your virtual environment. On systems with multiple Python versions
installed you can be explicit:

.. code-block:: bash

   python3.12 -m venv .venv

----

**Conflicting package versions after upgrading**

If you upgrade OpenSTEF inside an existing environment and encounter unexpected
``ImportError`` or ``AttributeError`` exceptions, the safest fix is to recreate
the environment from scratch:

.. code-block:: bash

   deactivate
   rm -rf .venv
   python -m venv .venv
   source .venv/bin/activate
   pip install openstef

----

**pip resolves to an old version**

Ensure pip itself is up to date before installing:

.. code-block:: bash

   python -m pip install --upgrade pip
   pip install openstef


Next Steps
----------

With OpenSTEF installed you are ready to start forecasting:

- :doc:`quickstart` — run a minimal forecast in a few lines of code
- :doc:`first_forecast` — a guided, step-by-step tutorial explaining each stage
- :doc:`backtesting` — evaluate a trained model against historical data
- :doc:`advanced_customization` — extend OpenSTEF with custom models and pipelines