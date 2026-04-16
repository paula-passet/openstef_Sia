Installation
============

This page covers everything you need to install OpenSTEF and verify that it is
working correctly on your system. Once you have a working installation, head to
:doc:`quickstart` to run your first forecast in minutes, or :doc:`first_forecast`
for a more detailed walkthrough.

System Requirements
-------------------

OpenSTEF requires:

- **Python 3.12 or later** (Python < 3.12 is not supported)
- A supported operating system: Linux, macOS, or Windows
- ``pip`` 21.0 or later (to handle modern dependency resolution)

No special hardware is required for the core library. GPU support is available
as an optional extra for XGBoost-based models — see `Optional Extras`_ below.

Installing OpenSTEF
-------------------

The simplest way to get started is to install the ``openstef`` meta-package,
which pulls in the complete framework in a single command:

.. code-block:: bash

   pip install openstef

This installs four packages that together make up the OpenSTEF library:

- **openstef-core** — shared data structures, datasets, and utilities
- **openstef-models** — forecasting models (XGBoost, LightGBM, and more)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-models and ensemble combiners

For most users this is the right choice. If you are building a lightweight
service and want to minimise the dependency footprint, see
`Installing Individual Packages`_ below.

.. note::

   We recommend installing OpenSTEF inside a virtual environment::

      python -m venv .venv
      source .venv/bin/activate   # Linux / macOS
      .venv\Scripts\activate      # Windows
      pip install openstef

Installing Individual Packages
-------------------------------

If you only need part of the framework, each sub-package can be installed
independently:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Forecasting models (requires openstef-core)
   pip install openstef-models

   # Backtesting and evaluation tools (requires openstef-core)
   pip install openstef-beam

   # Meta / ensemble models (requires openstef-beam, openstef-core, openstef-models)
   pip install openstef-meta

Each package declares its required dependencies and will install them
automatically. You do not need to install ``openstef-core`` manually before
installing ``openstef-models``; pip resolves the dependency tree for you.

Optional Extras
---------------

Several packages expose optional feature sets that bring in heavier or
platform-specific dependencies. Install them using pip's ``[extra]`` syntax.

**openstef-models extras**

.. code-block:: bash

   # LightGBM support
   pip install "openstef-models[lgbm]"

   # XGBoost (CPU-optimised build for Linux, macOS, and Windows)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU support
   pip install "openstef-models[xgb-gpu]"

**openstef-beam extras**

.. code-block:: bash

   # Baseline models (pulls in openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # All optional features including S3 filesystem support
   pip install "openstef-beam[all]"

**Install everything at once**

If you want the full framework with every optional feature enabled, combine
the meta-package with the relevant extras:

.. code-block:: bash

   pip install openstef "openstef-models[lgbm,xgb-cpu]" "openstef-beam[all]"

.. note::

   ``openstef-models[xgb-gpu]`` and ``openstef-models[xgb-cpu]`` are mutually
   exclusive. Install only the variant that matches your hardware.

Verifying the Installation
---------------------------

After installation, confirm that the packages are importable and check their
versions:

.. code-block:: python

   import importlib.metadata

   packages = [
       "openstef",
       "openstef-core",
       "openstef-models",
       "openstef-beam",
       "openstef-meta",
   ]

   for pkg in packages:
       try:
           version = importlib.metadata.version(pkg)
           print(f"{pkg}: {version}")
       except importlib.metadata.PackageNotFoundError:
           print(f"{pkg}: not installed")

You can also do a quick smoke test to confirm the core library is functional:

.. code-block:: python

   # Verify core data structures are accessible
   from openstef_core.datasets import ForecastInputDataset
   from openstef_core.exceptions import MissingColumnsError

   print("openstef-core imported successfully")

   # Verify model layer is accessible (requires openstef-models)
   from openstef_models.mixins import ModelSerializer

   print("openstef-models imported successfully")

   # Verify BEAM layer is accessible (requires openstef-beam)
   from openstef_beam.backtesting import pipeline

   print("openstef-beam imported successfully")

If any import raises a ``ModuleNotFoundError``, the corresponding package is
not installed. Re-run the appropriate ``pip install`` command from the sections
above.

Troubleshooting
---------------

**Python version mismatch**

If pip reports a resolver error mentioning Python version constraints, check
your active Python version:

.. code-block:: bash

   python --version

OpenSTEF requires Python 3.12 or later. If you are on an older version, either
upgrade Python or use a tool such as ``pyenv`` to manage multiple Python
versions side-by-side.

**Dependency conflicts in an existing environment**

Installing OpenSTEF into an environment that already has many packages can
sometimes produce resolver conflicts. The safest fix is to install into a
fresh virtual environment:

.. code-block:: bash

   python -m venv openstef-env
   source openstef-env/bin/activate
   pip install openstef

**Missing optional dependency at runtime**

If you see a ``MissingExtraError`` at runtime, the code path you are using
requires an optional extra that was not installed. The error message will tell
you exactly which package to add, for example::

   MissingExtraError: Optional package lgbm is missing. Please install it to
   use this module using `pip install lgbm` or install all optional features
   using `pip install openstef-models[all]`.

Follow the instruction in the error message, or install all extras for the
relevant package:

.. code-block:: bash

   pip install "openstef-models[lgbm,xgb-cpu]"
   pip install "openstef-beam[all]"

**Slow or stalled installation**

Large optional dependencies such as XGBoost and LightGBM can take a while to
download. If the installation appears stalled, check your network connection
and consider using a regional PyPI mirror:

.. code-block:: bash

   pip install openstef -i https://pypi.org/simple/

**pip version too old**

OpenSTEF uses modern packaging metadata. If pip reports unexpected errors,
upgrade pip first:

.. code-block:: bash

   pip install --upgrade pip
   pip install openstef

Next Steps
----------

With OpenSTEF installed you are ready to start forecasting:

- :doc:`quickstart` — run a minimal working forecast in under five minutes
- :doc:`first_forecast` — a step-by-step tutorial that explains each stage of
  the forecasting pipeline
- :doc:`backtesting` — learn how to evaluate and compare models on historical
  data
- :doc:`advanced_customization` — extend OpenSTEF with custom models and
  feature engineering