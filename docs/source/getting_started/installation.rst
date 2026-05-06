Installation
============

This page covers everything you need to install OpenSTEF: system requirements, the
different installation options, optional extras for specific model backends, and how
to verify that your environment is set up correctly. If you are already installed and
want to run your first forecast, head over to :doc:`quickstart`.

.. note::
   OpenSTEF requires **Python 3.12 or later** (Python < 4.0). No other system-level
   dependencies are required beyond a working Python environment.


Standard installation
---------------------

The simplest way to get everything is to install the ``openstef`` meta-package, which
pulls in all four sub-packages at once:

.. code-block:: bash

   pip install openstef

This single command installs:

- **openstef-core** — shared data structures, base classes, and dataset utilities
- **openstef-models** — forecasting models (LightGBM, XGBoost, and more)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-model layer that combines the above

For most users this is the right starting point. If you are working in a constrained
environment or only need a subset of the functionality, read the next section.


Installing individual packages
------------------------------

Each sub-package can be installed on its own. This is useful when, for example, you
only need the core data utilities in a lightweight service, or you want to keep model
dependencies separate from evaluation tooling.

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Forecasting models (depends on openstef-core)
   pip install openstef-models

   # Backtesting and evaluation (depends on openstef-core)
   pip install openstef-beam

   # Meta-models (depends on openstef-beam, openstef-core, and openstef-models)
   pip install openstef-meta

Key dependencies pulled in automatically:

- ``openstef-core``: joblib, numpy, pandas, pyarrow, pydantic
- ``openstef-models``: holidays, mlflow-skinny, pvlib (plus the above)
- ``openstef-beam``: plotly, pyyaml, scoringrules, tqdm (plus openstef-core)
- ``openstef-meta``: openstef-beam, openstef-core, openstef-models[lgbm]


Optional extras
---------------

Several model backends are not installed by default because they carry large or
platform-specific dependencies. Install them with the bracket syntax:

.. code-block:: bash

   # LightGBM backend (recommended for most forecasting tasks)
   pip install "openstef-models[lgbm]"

   # XGBoost — CPU-optimised build (Linux, Windows, macOS)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost — GPU build (requires a CUDA-capable device)
   pip install "openstef-models[xgb-gpu]"

   # openstef-beam with baseline models and S3 support
   pip install "openstef-beam[all]"

   # openstef-beam with baseline models only (no S3)
   pip install "openstef-beam[baselines]"

.. note::
   ``openstef-models[lgbm]`` installs LightGBM ≥ 4.6. The ``[xgb-cpu]`` extra
   selects a CPU-only XGBoost wheel on Linux and Windows, and the standard wheel on
   macOS. Use ``[xgb-gpu]`` only when you have a CUDA environment configured.

If you want everything — all packages and all optional extras — the following command
covers the full installation:

.. code-block:: bash

   pip install openstef "openstef-beam[all]" "openstef-models[lgbm]" "openstef-models[xgb-cpu]"


Using a virtual environment
---------------------------

It is strongly recommended to install OpenSTEF inside an isolated environment to avoid
dependency conflicts with other projects.

.. code-block:: bash

   # Create and activate a virtual environment
   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   # .venv\Scripts\activate         # Windows

   # Then install as normal
   pip install openstef

If you use ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install openstef


Verifying the installation
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

All four lines should print a version string without raising an ``ImportError``. If
any import fails, see the troubleshooting section below.

You can also do a quick smoke-test by loading one of the built-in datasets:

.. code-block:: python

   from openstef_core import datasets

   ds = datasets.load()
   print(ds)


Troubleshooting
---------------

ImportError for an optional backend
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see a message such as::

   Optional package lgbm is missing. Please install it to use this module
   using `pip install lgbm` or install all optional features using
   `pip install openstef-models[all]`.

OpenSTEF raises ``MissingExtraError`` when you call functionality that requires an
optional extra that is not installed. Install the relevant extra:

.. code-block:: bash

   pip install "openstef-models[lgbm]"

Wrong Python version
^^^^^^^^^^^^^^^^^^^^

OpenSTEF requires Python 3.12 or later. If ``pip install openstef`` fails with a
resolver error mentioning Python version constraints, check your active interpreter:

.. code-block:: bash

   python --version

If it reports Python 3.11 or earlier, either upgrade your Python installation or
create a new virtual environment with a compatible version (see above).

Conflicting dependencies
^^^^^^^^^^^^^^^^^^^^^^^^

In environments with many pre-installed packages, pip may report conflicts. The
cleanest fix is to install OpenSTEF in a fresh virtual environment. If you must
install into an existing environment, try:

.. code-block:: bash

   pip install --upgrade openstef

or use ``pip install --dry-run openstef`` first to inspect what would change.

Slow or failed installation behind a proxy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pass proxy settings to pip via the standard environment variables:

.. code-block:: bash

   export HTTPS_PROXY=http://proxy.example.com:8080
   pip install openstef

Or use the ``--proxy`` flag directly:

.. code-block:: bash

   pip install --proxy http://proxy.example.com:8080 openstef


Next steps
----------

Once installation is complete, continue with one of the following pages:

- :doc:`quickstart` — run a forecast in a few lines of code
- :doc:`first_forecast` — a step-by-step walkthrough of your first forecast
- :doc:`backtesting` — evaluate a model on historical data
- :doc:`advanced_customization` — customise models, features, and pipelines