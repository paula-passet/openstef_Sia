Installation
============

This page covers everything you need to install OpenSTEF on your system: the
recommended installation path, individual package options, optional extras for
specific model backends, and how to verify that everything is working. If you
run into problems, the :ref:`troubleshooting` section at the bottom addresses
the most common issues.

Once you have OpenSTEF installed, head over to :doc:`quickstart` to run your
first forecast in minutes, or follow the more detailed :doc:`first_forecast`
tutorial for a step-by-step walkthrough.

.. note::

   OpenSTEF is a Python library distributed via PyPI. It does **not** require
   any special system-level services or daemons — you install it like any
   other Python package and import it directly in your code.


System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python** 3.12 or later (Python < 3.12 is not supported)
- **pip** 21.0 or later (to handle modern dependency metadata correctly)
- A virtual environment is strongly recommended (``venv``, ``conda``, or
  similar)

OpenSTEF is tested on Linux, macOS, and Windows. GPU-accelerated model
backends have additional requirements described in
:ref:`optional-dependencies` below.


Recommended Installation
------------------------

The simplest way to get started is to install the ``openstef`` meta-package,
which pulls in the complete framework in a single command:

.. code-block:: bash

   pip install openstef

This installs four co-ordinated packages:

- **openstef-core** — data structures, feature engineering, and shared
  utilities
- **openstef-models** — forecasting models (LightGBM by default, with optional
  XGBoost support)
- **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics (BEAM)
- **openstef-meta** — meta-model layer that combines the above

All inter-package version constraints are managed for you, so installing the
meta-package is the safest way to get a consistent, working set of
dependencies.


.. _optional-dependencies:

Optional Dependencies
---------------------

Several model backends are not installed by default because they carry
significant extra weight or have platform-specific requirements. Install them
with pip *extras* syntax.

LightGBM backend
^^^^^^^^^^^^^^^^

LightGBM is the default model backend and is included automatically when you
install ``openstef-models``. If you are installing ``openstef-models``
directly and want to be explicit:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

XGBoost backend (CPU)
^^^^^^^^^^^^^^^^^^^^^

XGBoost CPU support is available on Linux, macOS, and Windows:

.. code-block:: bash

   pip install "openstef-models[xgb-cpu]"

.. note::

   On Linux and Windows this installs the ``xgboost-cpu`` wheel. On macOS the
   standard ``xgboost`` wheel is used instead. Both require ``xgboost>=3,<4``.

XGBoost backend (GPU)
^^^^^^^^^^^^^^^^^^^^^

For GPU-accelerated training (requires a CUDA-capable GPU and a compatible
CUDA toolkit):

.. code-block:: bash

   pip install "openstef-models[xgb-gpu]"

BEAM baselines and cloud storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef-beam`` ships two additional extras:

.. code-block:: bash

   # Baseline models (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # All extras, including S3 filesystem support
   pip install "openstef-beam[all]"

Installing everything at once
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install the full framework with all optional extras in one go:

.. code-block:: bash

   pip install "openstef[all]"


Installing Individual Packages
-------------------------------

If you only need a subset of the framework — for example, you want to use the
core data structures without the full model suite — you can install packages
individually:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # BEAM evaluation toolkit only (includes openstef-core as a dependency)
   pip install openstef-beam

   # Models only
   pip install openstef-models

This is useful when building lightweight services or when you want precise
control over your dependency tree.


Virtual Environment Setup
--------------------------

It is good practice to isolate OpenSTEF in its own virtual environment. Here
is a minimal setup using the standard library ``venv`` module:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   # .venv\Scripts\activate         # Windows

   pip install --upgrade pip
   pip install openstef

For Conda users:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install openstef


Verifying the Installation
---------------------------

After installation, confirm that the packages are importable and check their
versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam

   print(openstef_core.__version__)
   print(openstef_models.__version__)
   print(openstef_beam.__version__)

You can also verify from the command line using pip:

.. code-block:: bash

   pip show openstef-core openstef-models openstef-beam openstef-meta

A successful installation will print the version, author, and location for
each package without any errors.


.. _troubleshooting:

Troubleshooting
---------------

Python version mismatch
^^^^^^^^^^^^^^^^^^^^^^^

If pip reports a ``Requires-Python`` conflict, your active Python interpreter
is older than 3.12. Check which Python is active:

.. code-block:: bash

   python --version
   which python   # Linux / macOS
   where python   # Windows

Switch to a Python 3.12+ interpreter or create a new virtual environment with
the correct version before retrying.

Dependency conflicts with existing packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF pins some dependencies (notably ``xgboost>=3,<4``) that may conflict
with other libraries in a shared environment. The recommended fix is to install
OpenSTEF in a dedicated virtual environment rather than into a system or
shared Conda environment.

Missing optional package at runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see a ``MissingExtraError`` at runtime, an optional dependency was not
installed. The error message will tell you exactly which extra to add:

.. code-block:: text

   Optional package <extra> is missing. Please install it to use this module
   using `pip install <extra>` or install all optional features using
   `pip install openstef-beam[all]`.

Follow the instruction in the error message, or install the relevant extras
group as described in :ref:`optional-dependencies`.

SSL / proxy errors behind a corporate firewall
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If pip cannot reach PyPI, configure your proxy settings or use a local mirror:

.. code-block:: bash

   pip install openstef --proxy http://<proxy-host>:<port>
   # or point to an internal index:
   pip install openstef --index-url https://<internal-pypi>/simple/

Slow or failed LightGBM installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

LightGBM requires a C++ compiler on some platforms when a pre-built wheel is
not available. On Linux, install the build tools first:

.. code-block:: bash

   sudo apt-get install build-essential cmake   # Debian / Ubuntu
   pip install openstef

On macOS, make sure the Xcode command-line tools are installed
(``xcode-select --install``).


Next Steps
----------

With OpenSTEF installed you are ready to start forecasting:

- :doc:`quickstart` — run a minimal working forecast in under five minutes
- :doc:`first_forecast` — a guided tutorial that explains each step in detail
- :doc:`backtesting` — learn how to evaluate and compare models on historical
  data
- :doc:`advanced_customization` — extend OpenSTEF with custom models and
  feature engineering