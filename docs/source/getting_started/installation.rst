Installation
============

This page covers everything you need to get OpenSTEF installed: system requirements, the different ways to install the library, optional feature sets, and how to confirm the installation is working. Once you have OpenSTEF installed, head over to :doc:`quickstart` for a minimal working forecast example.

System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python** 3.12 or later (Python 4.x is also supported)
- **pip** 21.0 or later (for reliable extras resolution)
- A virtual environment is strongly recommended (``venv``, ``conda``, or similar)

OpenSTEF has no mandatory system-level dependencies beyond Python itself. GPU support for XGBoost requires a CUDA-capable device and the appropriate CUDA toolkit, but this is entirely optional.

Installing OpenSTEF
-------------------

The simplest way to get started is to install the ``openstef`` meta-package, which pulls in all sub-packages and their default dependencies in one step:

.. code-block:: bash

   pip install openstef

This installs the following four packages together:

- **openstef-core** — shared data structures, base classes, and dataset utilities
- **openstef-models** — forecasting models (quantile regression, LightGBM, XGBoost, and more)
- **openstef-beam** — backtesting, evaluation, analysis, and metrics (BEAM)
- **openstef-meta** — meta-models that combine the above

For most users this single command is all that is needed.

Installing Individual Packages
------------------------------

If you only need part of the framework — for example, to embed a single model in an existing pipeline — you can install sub-packages individually:

.. code-block:: bash

   # Core data structures and utilities only
   pip install openstef-core

   # Models package (includes openstef-core automatically)
   pip install openstef-models

   # BEAM evaluation toolkit
   pip install openstef-beam

   # Meta-models (requires openstef-beam and openstef-models)
   pip install openstef-meta

Each package declares its own dependencies, so pip will resolve the minimum required set automatically.

Optional Dependencies
---------------------

Several packages expose optional feature sets that are not installed by default. These are activated using pip's ``[extra]`` syntax.

openstef-models extras
^^^^^^^^^^^^^^^^^^^^^^

The models package ships three optional extras for gradient-boosted tree backends:

.. code-block:: bash

   # LightGBM support (recommended for most use cases)
   pip install "openstef-models[lgbm]"

   # XGBoost on CPU (Linux, macOS, Windows)
   pip install "openstef-models[xgb-cpu]"

   # XGBoost with GPU acceleration (requires CUDA)
   pip install "openstef-models[xgb-gpu]"

You can combine extras in a single install:

.. code-block:: bash

   pip install "openstef-models[lgbm,xgb-cpu]"

.. note::
   If you try to use a model that requires an uninstalled extra, OpenSTEF raises a ``MissingExtraError`` with a clear message telling you which extra to install. You will not encounter a bare ``ImportError``.

openstef-beam extras
^^^^^^^^^^^^^^^^^^^^

The BEAM package has two optional extras:

.. code-block:: bash

   # Baseline models (pulls in openstef-meta and openstef-models)
   pip install "openstef-beam[baselines]"

   # S3 filesystem support for reading/writing artifacts from S3
   pip install "openstef-beam[all]"

The ``[all]`` extra includes ``[baselines]`` plus S3 support via ``s3fs``.

MLflow Integration
^^^^^^^^^^^^^^^^^^

MLflow is included as a lightweight dependency (``mlflow-skinny``) in ``openstef-models`` by default. This provides experiment tracking and model registry support without the full MLflow server stack. If you need the complete MLflow UI and artifact server, install the full package separately:

.. code-block:: bash

   pip install mlflow

No additional OpenSTEF configuration is required — the ``MLFlowStorage`` and ``MLFlowStorageCallback`` classes in ``openstef_models.integrations.mlflow`` will pick up a full MLflow installation automatically.

Installing for Development
--------------------------

To contribute to OpenSTEF or run the test suite, clone the repository and install the package in editable mode with development dependencies:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e ".[dev]"

.. note::
   Refer to the contributing guide in the repository root for details on running tests, linting, and submitting pull requests.

Verifying the Installation
--------------------------

After installation, run the following snippet to confirm that the core packages are importable and print their versions:

.. code-block:: python

   import openstef_core
   import openstef_models
   import openstef_beam
   import openstef_meta

   print("openstef-core   :", openstef_core.__version__)
   print("openstef-models :", openstef_models.__version__)
   print("openstef-beam   :", openstef_beam.__version__)
   print("openstef-meta   :", openstef_meta.__version__)

If all four lines print version strings without errors, the installation is complete.

To verify that an optional backend such as LightGBM is available, you can do a quick import check:

.. code-block:: python

   try:
       import lightgbm
       print("LightGBM available:", lightgbm.__version__)
   except ImportError:
       print("LightGBM not installed — run: pip install 'openstef-models[lgbm]'")

Upgrading
---------

To upgrade to the latest release, pass the ``--upgrade`` flag:

.. code-block:: bash

   pip install --upgrade openstef

To upgrade a specific sub-package without touching the others:

.. code-block:: bash

   pip install --upgrade openstef-models

.. warning::
   OpenSTEF follows semantic versioning. Minor and patch releases are backwards-compatible, but major releases may introduce breaking changes. Review the changelog before upgrading across a major version boundary.

Next Steps
----------

With OpenSTEF installed you are ready to run your first forecast. See :doc:`quickstart` for a minimal end-to-end example that trains a model and produces predictions in a few lines of code.