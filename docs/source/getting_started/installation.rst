Installation
============

This page covers everything you need to get OpenSTEF installed in your Python environment: system requirements, the available packages, optional extras, and how to confirm the installation is working.

Once installed, head over to :doc:`quickstart` to run your first forecast.

.. note::
   OpenSTEF 4.0 is structured as a **modular mono-repo**. You install only the packages your use case requires — there is no single ``openstef`` mega-package that pulls in every dependency.


System Requirements
-------------------

OpenSTEF requires **Python 3.10 or later**. The library is pure Python and runs on Linux, macOS, and Windows. There are no mandatory system-level dependencies beyond a working Python installation and ``pip``.

For production workloads that process thousands of grid locations (as Alliander does), a multi-core machine with at least 8 GB of RAM is recommended. For experimentation and development, a standard laptop is sufficient.


Package Overview
----------------

OpenSTEF 4.0 is split into focused packages that can be composed together:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Package
     - Purpose
   * - ``openstef-core``
     - Data types, interfaces, base classes, and shared testing utilities. Every other package depends on this.
   * - ``openstef-models``
     - Forecasting models, preprocessing pipelines, energy-specific feature engineering, explainability, and presets for common use cases.
   * - ``openstef-meta``
     - Meta-learning module with modern ensemble models and advanced model architectures.
   * - ``openstef-beam``
     - Backtesting, evaluation, analysis, and metrics (BEAM). Use this to validate forecast accuracy and detect regressions.
   * - ``openstef-foundation``
     - *(Work in progress)* Pre-trained models and transfer learning for energy data.

.. note::
   ``openstef-core`` is a transitive dependency of all other packages. You do not need to install it explicitly unless you are building your own integration against the base interfaces.


Installing the Packages
-----------------------

Most users working on forecasting tasks need ``openstef-models``. Install it with pip:

.. code-block:: bash

   pip install openstef-models

This pulls in ``openstef-core`` automatically. If you also want backtesting and evaluation capabilities, add ``openstef-beam``:

.. code-block:: bash

   pip install openstef-models openstef-beam

To install the meta-learning module alongside the core forecasting stack:

.. code-block:: bash

   pip install openstef-models openstef-meta openstef-beam

If you only need the base data types and interfaces — for example, to build a custom integration or plugin — install the core package alone:

.. code-block:: bash

   pip install openstef-core


Installing from Source
----------------------

To work with the latest development version or to contribute to OpenSTEF, clone the mono-repo and install the packages in editable mode:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install the packages you need in editable mode
   pip install -e packages/openstef-core
   pip install -e packages/openstef-models
   pip install -e packages/openstef-beam

The project uses `uv <https://github.com/astral-sh/uv>`_ and `Ruff <https://github.com/astral-sh/ruff>`_ for fast dependency management and linting. If you are setting up a development environment, install the development extras:

.. code-block:: bash

   pip install -e "packages/openstef-models[dev]"

.. note::
   The ``[dev]`` extra installs testing tools, type-checking dependencies (mypy), and linting utilities used by the project's CI pipeline.


Optional Dependencies
---------------------

Several capabilities in OpenSTEF are gated behind optional extras to keep the default installation lightweight.

Model backends
^^^^^^^^^^^^^^

``openstef-models`` ships with support for XGBoost and LightGBM out of the box. These are installed as direct dependencies. If you want to use additional model backends, install the corresponding extra:

.. code-block:: bash

   # Example: install with deep learning support when available
   pip install "openstef-models[deep-learning]"

MLflow experiment tracking
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF 4.0 decouples MLflow from the core library — it is no longer a hard dependency. To enable MLflow-based experiment tracking:

.. code-block:: bash

   pip install "openstef-models[mlflow]"

.. note::
   In OpenSTEF 3.x, MLflow was a required dependency. If you are migrating from V3, you can now opt out of it entirely or swap it for a different tracking backend.

Notebook and visualisation support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For interactive exploration in Jupyter notebooks:

.. code-block:: bash

   pip install "openstef-models[notebooks]"


Using a Virtual Environment
---------------------------

It is good practice to install OpenSTEF inside a virtual environment to avoid conflicts with other packages. Using the standard library ``venv``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate          # Linux / macOS
   .venv\Scripts\activate             # Windows

   pip install openstef-models

Alternatively, with ``uv`` (recommended for faster installs):

.. code-block:: bash

   uv venv
   source .venv/bin/activate
   uv pip install openstef-models


Verifying the Installation
--------------------------

After installation, confirm that the packages are importable and report the expected version:

.. code-block:: python

   import openstef_core
   import openstef_models

   print(openstef_core.__version__)
   print(openstef_models.__version__)

A quick smoke test — importing the base data types and a preset — confirms the core machinery is intact:

.. code-block:: python

   from openstef_core.data_types import ForecastType
   from openstef_models.presets import get_preset

   preset = get_preset("xgboost")
   print(preset)

If both blocks run without errors, your installation is ready.

.. note::
   If you see an ``ImportError``, check that you are running Python inside the virtual environment where you installed the packages (``which python`` on Linux/macOS, ``where python`` on Windows).


Upgrading
---------

To upgrade to the latest release of any package:

.. code-block:: bash

   pip install --upgrade openstef-models openstef-beam

Because the packages are versioned independently, check the `changelog <https://github.com/OpenSTEF/openstef/releases>`_ for each package before upgrading in a production environment. ``openstef-core`` interface changes are the most likely to require updates in downstream code.

.. warning::
   OpenSTEF 4.0 is a major architectural refactor of V3. The package names, import paths, and API surface have changed significantly. If you are upgrading from V3, review the migration guide before upgrading.


Next Steps
----------

With OpenSTEF installed, the :doc:`quickstart` page walks through the minimal code needed to train a model and produce your first forecast.