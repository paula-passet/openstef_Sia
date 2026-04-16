Installation
============

This page covers everything you need to install OpenSTEF and verify that it is
working correctly on your system. Once installation is complete, head to
:doc:`quickstart` to run your first forecast in minutes, or follow the
:doc:`first_forecast` tutorial for a more guided introduction.

.. note::

   OpenSTEF is a Python **library**. It is imported into your own Python
   scripts, notebooks, or applications — it does not run as a standalone
   service or command-line tool.

System Requirements
-------------------

Before installing, confirm your environment meets the following requirements:

- **Python** 3.12 or later (Python < 4.0)
- **pip** 21.0 or later (to support modern dependency resolution)
- A supported operating system: Linux, macOS, or Windows

OpenSTEF is regularly tested on Linux and macOS. Windows is supported but
some optional GPU-accelerated dependencies may require additional setup steps
from the upstream package vendors.

Standard Installation
---------------------

The simplest way to get everything is to install the ``openstef`` meta-package,
which pulls in all sub-packages and their default dependencies in one command:

.. code-block:: bash

   pip install openstef

This single command installs the following four sub-packages:

- **openstef-core** — data structures, feature engineering, and pipeline
  utilities that the rest of the library builds on.
- **openstef-models** — forecasting model implementations (LightGBM, XGBoost,
  and others) together with training and inference logic.
- **openstef-meta** — meta-model support for combining multiple forecasters.
- **openstef-beam** — the Backtesting, Evaluation, Analysis and Metrics (BEAM)
  toolkit, including visualisation via Plotly.

If you only need a subset of this functionality, see
`Installing Individual Sub-packages`_ below.

Virtual Environments
--------------------

It is strongly recommended to install OpenSTEF inside a dedicated virtual
environment so that its dependencies do not conflict with other projects.

Using ``venv`` (standard library):

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate.bat       # Windows

   pip install --upgrade pip
   pip install openstef

Using ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.12
   conda activate openstef-env
   pip install openstef

Optional Dependencies
---------------------

Several sub-packages expose optional extras that activate additional
functionality. Install them by appending the extra name in square brackets.

**Model back-ends for openstef-models**

By default, ``openstef-models`` installs with LightGBM support. You can
explicitly request a specific model back-end:

.. code-block:: bash

   # LightGBM (default, included in the base openstef install)
   pip install "openstef-models[lgbm]"

   # XGBoost — CPU-optimised build (Linux and Windows)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost — GPU build (requires a CUDA-capable GPU and drivers)
   pip install "openstef-models[xgb-gpu]"

.. note::

   The ``xgb-cpu`` extra selects a CPU-only XGBoost wheel on Linux and
   Windows. On macOS the standard ``xgboost`` package is used regardless of
   which extra you choose.

**BEAM extras for openstef-beam**

.. code-block:: bash

   # Baseline model support (requires openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # All BEAM extras, including S3 filesystem support via s3fs
   pip install "openstef-beam[all]"

Installing Individual Sub-packages
-----------------------------------

If your use case only requires part of the library — for example, you want
core data-processing utilities without the full model suite — you can install
sub-packages individually:

.. code-block:: bash

   pip install openstef-core          # Core utilities only
   pip install openstef-models        # Models + core
   pip install openstef-beam          # BEAM evaluation toolkit + core
   pip install openstef-meta          # Meta-models (pulls in all sub-packages)

Installing from Source
----------------------

To work with the latest development code or to contribute to OpenSTEF, clone
the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

Editable installs reflect any local changes you make to the source code
immediately, without needing to reinstall.

Verifying the Installation
--------------------------

After installation, open a Python interpreter or notebook and run the
following snippet to confirm that the library imports correctly and to check
the installed versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam

   # Print versions to confirm the install
   print("openstef-core   :", openstef_core.__version__)
   print("openstef-models :", openstef_models.__version__)
   print("openstef-beam   :", openstef_beam.__version__)

A successful run prints the version strings without any import errors. If you
see a ``ModuleNotFoundError``, revisit the steps above and ensure you are
running Python inside the correct virtual environment.

Troubleshooting
---------------

**pip cannot resolve dependencies**

Upgrade pip before installing, as older versions sometimes fail on complex
dependency trees:

.. code-block:: bash

   pip install --upgrade pip
   pip install openstef

**Wrong Python version**

OpenSTEF requires Python 3.12 or later. Verify your active interpreter:

.. code-block:: bash

   python --version

If the version is below 3.12, either upgrade your system Python or create a
new virtual environment that points to a compatible interpreter (e.g.
``conda create -n openstef-env python=3.12``).

**Conflicting packages in an existing environment**

If you are adding OpenSTEF to an environment that already contains other
packages, dependency conflicts can arise. The safest resolution is to install
OpenSTEF into a fresh virtual environment. If you must share an environment,
try:

.. code-block:: bash

   pip install openstef --upgrade --upgrade-strategy eager

**GPU XGBoost not using the GPU**

Installing ``openstef-models[xgb-gpu]`` provides the GPU-enabled XGBoost
wheel, but the model must also be configured to use a GPU device at runtime.
Confirm that your CUDA drivers are installed and visible to Python:

.. code-block:: python

   import xgboost as xgb
   print(xgb.build_info())   # Should list CUDA under "USE_CUDA"

If CUDA does not appear, reinstall the XGBoost GPU wheel following the
`official XGBoost GPU documentation <https://xgboost.readthedocs.io/en/stable/gpu/index.html>`_.

**ImportError after upgrading**

If you upgrade OpenSTEF and encounter import errors, stale ``.pyc`` cache
files are occasionally the cause. Clear them and retry:

.. code-block:: bash

   find . -type d -name __pycache__ -exec rm -rf {} +
   pip install --upgrade openstef

Next Steps
----------

With OpenSTEF installed you are ready to start forecasting:

- :doc:`quickstart` — the fastest path to a working forecast, with minimal
  boilerplate.
- :doc:`first_forecast` — a step-by-step tutorial that explains each stage of
  the forecasting pipeline.
- :doc:`backtesting` — learn how to evaluate and compare models on historical
  data.
- :doc:`advanced_customization` — customise models, features, and pipelines for
  production use cases.