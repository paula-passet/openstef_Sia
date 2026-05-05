Installation
============

This page covers everything you need to install OpenSTEF and verify that it is working correctly — from a basic ``pip`` install through to optional dependencies and common troubleshooting steps. Once you have a working installation, head over to :doc:`quickstart` to run your first forecast.

System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python**: 3.9 or later (3.10 or 3.11 recommended)
- **Operating system**: Linux, macOS, or Windows
- **pip**: 21.0 or later (run ``pip install --upgrade pip`` if unsure)

A virtual environment is strongly recommended to avoid dependency conflicts with other projects.

Basic Installation
------------------

Install OpenSTEF from PyPI using ``pip``:

.. code-block:: python

   pip install openstef

This installs the core library along with its required dependencies, including:

- ``pandas`` and ``numpy`` — data handling and numerical operations
- ``scikit-learn`` — base estimator interfaces and model utilities
- ``xgboost`` and ``lightgbm`` — the primary gradient-boosting regressors
- ``mlflow`` — model serialisation and experiment tracking
- ``structlog`` — structured logging throughout the pipelines

After installation, confirm the package is available and check the installed version:

.. code-block:: python

   import openstef
   print(openstef.__version__)

If this prints a version string without errors, the core installation is complete.

Installing in a Virtual Environment
------------------------------------

It is good practice to isolate project dependencies. Using the standard library ``venv`` module:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

   pip install --upgrade pip
   pip install openstef

Alternatively, if you use ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.11
   conda activate openstef-env
   pip install openstef

.. note::
   Mixing ``conda``-managed packages with ``pip``-installed packages can occasionally cause solver conflicts. Installing OpenSTEF via ``pip`` inside a ``conda`` environment (as shown above) is the most reliable approach.

Installing from Source
----------------------

If you want the latest development version or plan to contribute to the project, install directly from the GitHub repository:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

The ``-e`` flag installs the package in *editable* mode, so changes to the source files are reflected immediately without reinstalling. The ``[dev]`` extra pulls in testing and linting tools (see `Optional Dependencies`_ below).

Optional Dependencies
---------------------

OpenSTEF exposes several extras that activate additional functionality. Install them by appending the extra name in square brackets:

.. code-block:: bash

   pip install "openstef[<extra>]"

The available extras are described below.

``dev`` — Development tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Includes ``pytest``, ``pytest-cov``, and linting utilities needed to run the test suite and contribute to the codebase:

.. code-block:: bash

   pip install "openstef[dev]"

MLflow tracking server
^^^^^^^^^^^^^^^^^^^^^^

The core install already includes ``mlflow`` as a required dependency because OpenSTEF uses :class:`~openstef.model.serializer.MLflowSerializer` to save and load trained models. No extra is needed for local file-based tracking.

If you want to log experiments to a **remote MLflow tracking server** (e.g. a self-hosted instance or Databricks), point the serialiser at your server URI at runtime:

.. code-block:: python

   from openstef.model.serializer import MLflowSerializer

   serializer = MLflowSerializer(mlflow_tracking_uri="http://my-mlflow-server:5000")

The serialiser automatically detects whether the connected MLflow instance is version 3.0 or later and adjusts its logging calls accordingly.

.. note::
   When running on Databricks, set the ``DATABRICKS_WORKSPACE_PATH`` environment variable. OpenSTEF will use it as a prefix for experiment names, keeping experiments organised across workspaces.

Verifying the Installation
--------------------------

A quick end-to-end check imports the main pipeline entry points and the built-in example data loader:

.. code-block:: python

   # Verify core pipelines are importable
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.model.serializer import MLflowSerializer

   print("OpenSTEF installed successfully.")

You can also run the built-in test suite if you installed with the ``[dev]`` extra:

.. code-block:: bash

   pytest --tb=short tests/

All tests should pass on a clean install. A small number of tests that require a live MLflow server are skipped automatically when no server is reachable.

Upgrading
---------

To upgrade to the latest release:

.. code-block:: bash

   pip install --upgrade openstef

Check the project changelog on GitHub before upgrading in a production environment, as minor releases may introduce changes to pipeline interfaces or model serialisation formats.

Troubleshooting
---------------

**ImportError on** ``xgboost`` **or** ``lightgbm``

These packages include compiled C++ extensions. On some Linux systems you may need to install system-level libraries first:

.. code-block:: bash

   # Debian / Ubuntu
   sudo apt-get install libgomp1

**MLflow version mismatch**

OpenSTEF's serialiser supports both MLflow 2.x and 3.x. If you see unexpected errors when saving or loading models, check that your installed MLflow version is consistent across all environments (training, serving, etc.):

.. code-block:: bash

   pip show mlflow

**pip resolver conflicts**

If ``pip`` reports dependency conflicts during installation, try upgrading pip and using the ``--upgrade-strategy eager`` flag:

.. code-block:: bash

   pip install --upgrade pip
   pip install --upgrade-strategy eager openstef

**Python version not supported**

OpenSTEF requires Python 3.9 or later. Verify your active interpreter:

.. code-block:: bash

   python --version

If the version is too old, create a new virtual environment with a supported Python version before installing.

Next Steps
----------

With OpenSTEF installed, continue to :doc:`quickstart` to build and run your first short-term energy forecast with a minimal working example.