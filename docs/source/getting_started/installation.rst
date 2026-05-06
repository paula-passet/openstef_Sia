Installation
============

This page covers everything you need to get OpenSTEF installed: system requirements,
installation options ranging from the full framework to individual packages, optional
model backends, and how to verify your setup is working correctly.

Once installed, head over to :doc:`quickstart` to run your first forecast.

.. note::

   OpenSTEF requires **Python 3.12 or later** (Python < 4.0). No other system-level
   dependencies are required beyond a working Python environment.

----

Standard Installation
---------------------

The simplest way to install OpenSTEF is via the ``openstef`` meta-package, which pulls
in the entire framework in one step:

.. code-block:: bash

   pip install openstef

This installs four packages together:

- **openstef-core** — shared data structures, dataset abstractions, and base classes
- **openstef-models** — forecasting models (LightGBM, XGBoost, and others)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-models that combine base forecasters

For most users this is the right starting point. If you are working in a constrained
environment or only need part of the stack, see `Individual Packages`_ below.

----

Using a Virtual Environment
----------------------------

It is strongly recommended to install OpenSTEF inside a virtual environment to avoid
dependency conflicts with other projects.

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   # .venv\Scripts\activate.bat     # Windows

   pip install openstef

----

Individual Packages
-------------------

Each component of OpenSTEF can be installed independently. This is useful when you want
to minimise the dependency footprint — for example, installing only ``openstef-core``
in a data-ingestion service that does not need to run models.

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Forecasting models (depends on openstef-core)
   pip install openstef-models

   # Backtesting and evaluation (depends on openstef-core)
   pip install openstef-beam

   # Meta-models / forecast combiners (depends on openstef-beam, openstef-core, openstef-models)
   pip install openstef-meta

The dependency chain is: ``openstef-core`` ← ``openstef-models`` ← ``openstef-beam`` ← ``openstef-meta``.
Installing a higher-level package always brings in the packages it depends on.

----

Optional Dependencies
---------------------

Several packages expose optional extras that activate additional model backends or
integrations. Install them by appending the extra name in square brackets.

openstef-models extras
^^^^^^^^^^^^^^^^^^^^^^

``openstef-models`` ships without a gradient-boosting backend by default. Choose the
one that matches your hardware:

.. code-block:: bash

   # LightGBM backend (recommended for most CPU workloads)
   pip install "openstef-models[lgbm]"

   # XGBoost — CPU-optimised build (Linux, Windows, macOS)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost — GPU build (requires CUDA)
   pip install "openstef-models[xgb-gpu]"

You can combine extras if needed:

.. code-block:: bash

   pip install "openstef-models[lgbm,xgb-cpu]"

openstef-beam extras
^^^^^^^^^^^^^^^^^^^^

``openstef-beam`` has two optional feature groups:

.. code-block:: bash

   # Baseline forecasters (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # S3 filesystem support for reading/writing data from object storage
   # (includes baselines)
   pip install "openstef-beam[all]"

.. note::

   If you try to use a feature that requires a missing extra, OpenSTEF raises a
   ``MissingExtraError`` with an explicit message telling you exactly which
   ``pip install`` command to run.

----

Installing for Development
--------------------------

To contribute to OpenSTEF or run the test suite, clone the repository and install the
package in editable mode with development dependencies:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   pip install -e ".[dev]"

Editable mode (``-e``) means changes to the source files are reflected immediately
without reinstalling.

----

Verifying the Installation
--------------------------

After installation, confirm that the packages are importable and check their versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam
   import openstef_meta

   print(openstef_core.__version__)
   print(openstef_models.__version__)
   print(openstef_beam.__version__)
   print(openstef_meta.__version__)

If any import raises a ``ModuleNotFoundError``, double-check that you are running
Python inside the virtual environment where OpenSTEF was installed:

.. code-block:: bash

   which python          # Linux / macOS — should point inside your .venv
   python -m pip list | grep openstef

----

Common Issues
-------------

**Wrong Python version**
   OpenSTEF requires Python 3.12 or later. Running ``python --version`` before
   installing will save you time.

**Missing model backend**
   Attempting to train an LightGBM or XGBoost model without the corresponding extra
   raises ``MissingExtraError``. Install ``openstef-models[lgbm]`` or
   ``openstef-models[xgb-cpu]`` as appropriate.

**Conflicting dependencies in an existing environment**
   If ``pip`` reports resolver conflicts, try installing into a fresh virtual
   environment. Alternatively, use ``pip install --upgrade openstef`` to ensure all
   sub-packages are on compatible versions.

**GPU XGBoost on macOS**
   The ``xgb-gpu`` extra is not supported on macOS. Use ``xgb-cpu`` or ``lgbm``
   instead.

----

Next Steps
----------

With OpenSTEF installed, continue to :doc:`quickstart` to train your first forecasting
model with a minimal working example.