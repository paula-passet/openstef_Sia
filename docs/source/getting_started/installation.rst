Installation
============

This page covers everything you need to install OpenSTEF and verify that it is
working correctly on your system. OpenSTEF is a Python library distributed via
PyPI, so a standard ``pip`` install is all that is needed for most use cases.
Optional integrations — such as MLflow model tracking — require additional
packages described below.

Once you have a working installation, head to :doc:`quickstart` for the fastest
path to your first forecast, or :doc:`first_forecast` for a more detailed
walkthrough.

.. contents:: On this page
   :local:
   :depth: 2

System Requirements
-------------------

Before installing, make sure your environment meets the following requirements:

- **Python 3.10 or later** — OpenSTEF uses modern type-hint syntax and relies
  on features introduced in Python 3.10.
- **pip 22+** — older versions of pip may not resolve the dependency tree
  correctly. Upgrade with ``pip install --upgrade pip`` if needed.
- **Operating system** — Linux, macOS, and Windows are all supported. Linux is
  the recommended platform for production deployments.

A virtual environment is strongly recommended. The examples below use the
built-in ``venv`` module, but ``conda`` or any other environment manager works
equally well.

Installing OpenSTEF
-------------------

OpenSTEF is organised as a set of focused packages that can be installed
individually or together. The two core packages are:

- **openstef-core** — foundational data structures, base classes, and shared
  utilities used across the rest of the library.
- **openstef-models** — forecasting models, feature pipelines, training
  workflows, and model storage backends.

Standard Installation
^^^^^^^^^^^^^^^^^^^^^

Create and activate a virtual environment, then install both packages:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate

   pip install --upgrade pip
   pip install openstef-core openstef-models

This installs the full set of core dependencies required to build, train, and
run forecasting pipelines.

Installing from Source
^^^^^^^^^^^^^^^^^^^^^^

If you want the latest development version, or if you intend to contribute to
OpenSTEF, clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   pip install -e packages/openstef-core
   pip install -e packages/openstef-models

Editable installs mean that any changes you make to the source are immediately
reflected without reinstalling.

Optional Dependencies
---------------------

Several integrations are available as optional extras. Install only what your
use case requires.

MLflow Integration
^^^^^^^^^^^^^^^^^^

MLflow provides experiment tracking, model versioning, and a centralised model
registry. It is particularly useful for production deployments where you need
to compare training runs or roll back to an earlier model version.

.. code-block:: bash

   pip install openstef-models[mlflow]

After installation, ``openstef_models.integrations.mlflow`` exposes
``MLFlowStorage`` and ``MLFlowStorageCallback``, which can be passed directly
to a forecasting workflow in place of the default local storage backend.

.. note::

   MLflow is an *optional* dependency. The core training and forecasting
   functionality works without it. See the API reference for
   ``openstef_models.integrations.mlflow`` for configuration details.

Apache Beam Integration
^^^^^^^^^^^^^^^^^^^^^^^

The ``openstef-beam`` package adds distributed pipeline execution and
built-in visualisation utilities (including ``ForecastTimeSeriesPlotter``).
Install it when you need to scale processing across large datasets or want
ready-made forecast plots:

.. code-block:: bash

   pip install openstef-beam

Development and Testing Extras
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When contributing to OpenSTEF, install the development extras to get the test
runner, linters, and documentation build tools:

.. code-block:: bash

   pip install openstef-core[dev] openstef-models[dev]

Verifying the Installation
--------------------------

After installation, confirm that the library imports correctly and that the
version is as expected:

.. code-block:: python

   import openstef_core
   import openstef_models

   print(openstef_core.__version__)
   print(openstef_models.__version__)

A more meaningful smoke test is to create a small synthetic dataset and confirm
that the core data structures initialise without error:

.. code-block:: python

   from openstef_core.testing import create_synthetic_forecasting_dataset

   dataset = create_synthetic_forecasting_dataset()
   print(dataset)

If both blocks run without raising an exception, your installation is working
correctly. Proceed to :doc:`quickstart` to run your first forecast.

Troubleshooting
---------------

Dependency Conflicts
^^^^^^^^^^^^^^^^^^^^

OpenSTEF pins its direct dependencies to tested version ranges. If you see a
``ResolutionImpossible`` or ``VersionConflict`` error during installation, the
most common cause is an existing package in your environment that conflicts with
one of OpenSTEF's requirements.

**Recommended fix:** install OpenSTEF into a fresh virtual environment:

.. code-block:: bash

   python -m venv .venv-openstef
   source .venv-openstef/bin/activate
   pip install openstef-core openstef-models

If you must share an environment with other packages, try:

.. code-block:: bash

   pip install openstef-core openstef-models --upgrade --upgrade-strategy eager

``ModuleNotFoundError`` After Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If Python cannot find ``openstef_core`` or ``openstef_models`` after a
successful ``pip install``, the most likely cause is that you have more than
one Python interpreter on your system and pip installed the packages into a
different one.

Check which Python and pip you are using:

.. code-block:: bash

   which python   # or: where python  (Windows)
   which pip

Both should point to the same environment. If they do not, use the explicit
form to ensure they match:

.. code-block:: bash

   python -m pip install openstef-core openstef-models

Outdated pip Fails to Resolve Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

pip versions older than 22 sometimes fail to resolve the dependency tree for
packages that use modern metadata formats. If you see unexpected resolver
errors, upgrade pip first:

.. code-block:: bash

   python -m pip install --upgrade pip
   pip install openstef-core openstef-models

MLflow Import Error
^^^^^^^^^^^^^^^^^^^

If you see ``ModuleNotFoundError: No module named 'mlflow'`` when using
``MLFlowStorage`` or ``MLFlowStorageCallback``, the MLflow optional extra was
not installed. Fix this with:

.. code-block:: bash

   pip install openstef-models[mlflow]

.. note::

   If you installed ``openstef-models`` from source in editable mode, run the
   same command from inside the ``packages/openstef-models`` directory:

   .. code-block:: bash

      pip install -e ".[mlflow]"

Next Steps
----------

With OpenSTEF installed, you are ready to start building forecasts:

- :doc:`quickstart` — a minimal working example you can run in under five
  minutes.
- :doc:`first_forecast` — a step-by-step tutorial that explains each part of
  the forecasting workflow.
- :doc:`backtesting` — learn how to evaluate and compare models on historical
  data.
- :doc:`advanced_customization` — customise pipelines, models, and storage
  backends for production use cases.