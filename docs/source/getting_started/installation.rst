Installation
============

This page covers everything you need to get OpenSTEF installed and ready to use: system prerequisites, the standard installation, optional dependencies for additional model backends, and a quick verification step.

Once you have OpenSTEF installed, head over to the :doc:`quickstart` page to run your first forecast.

Prerequisites
-------------

OpenSTEF requires:

- **Python 3.9 or later** (Python 3.10+ recommended)
- **pip 21.3+** or a compatible package manager (e.g. ``conda``, ``poetry``)

No special system libraries are required for the base installation. GPU support for XGBoost or LightGBM follows the standard setup for those libraries and is not managed by OpenSTEF directly.

Standard Installation
---------------------

Install OpenSTEF from PyPI using pip:

.. code-block:: bash

   pip install openstef

This installs the core library along with its required dependencies, including:

- ``xgboost`` — gradient boosting (XGB regressor)
- ``lightgbm`` — gradient boosting (LGB regressor)
- ``scikit-learn`` — linear and quantile regressors, base estimator interface
- ``pandas`` and ``numpy`` — data handling and numerical computation
- ``networkx`` — prediction job dependency resolution

These packages cover the full set of built-in model backends and the standard training and forecasting pipelines.

Installing a Specific Version
-----------------------------

To pin a specific release — useful for reproducible environments — pass the version explicitly:

.. code-block:: bash

   pip install openstef==3.4.0

You can browse available releases on `PyPI <https://pypi.org/project/openstef/#history>`_.

Installing from Source
----------------------

To work with the latest development code or contribute to the project, install directly from the GitHub repository:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e .

The ``-e`` flag installs in *editable* mode, so changes to the source are reflected immediately without reinstalling.

To include development tools (testing, linting, documentation):

.. code-block:: bash

   pip install -e ".[dev]"

Virtual Environments
--------------------

It is strongly recommended to install OpenSTEF inside a virtual environment to avoid dependency conflicts with other projects.

Using ``venv``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate.bat       # Windows

   pip install openstef

Using ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.10
   conda activate openstef-env
   pip install openstef

Optional Dependencies
---------------------

The base installation covers all built-in regressors. Some workflows or integrations require additional packages.

**Plotting and visualisation**

OpenSTEF does not bundle a plotting library. If you want to visualise forecasts or feature importances, install ``matplotlib`` or ``plotly`` separately:

.. code-block:: bash

   pip install matplotlib
   # or
   pip install plotly

**Distributed / large-scale pipelines**

If you are using ``openstef-dbc`` (the database connector) or ``openstef-beam`` (Apache Beam pipelines), install those packages independently:

.. code-block:: bash

   pip install openstef-dbc
   pip install openstef-beam

These are separate libraries with their own release cycles and are not required for the core OpenSTEF functionality.

**Jupyter notebooks**

To run the example notebooks from the repository:

.. code-block:: bash

   pip install jupyter

Verifying the Installation
---------------------------

After installation, confirm that OpenSTEF is available and check the installed version:

.. code-block:: python

   import openstef
   print(openstef.__version__)

You should see a version string such as ``3.4.0`` printed to the console. If you see a ``ModuleNotFoundError``, double-check that you are running Python inside the correct virtual environment.

You can also verify from the command line:

.. code-block:: bash

   python -c "import openstef; print(openstef.__version__)"

To confirm that the key model backends are importable:

.. code-block:: python

   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.model.regressors.lgbm import LGBMOpenstfRegressor
   from openstef.model.regressors.linear_quantile import LinearQuantileOpenstfRegressor

   print("All model backends available.")

If any of these imports fail, the most likely cause is a missing or incompatible version of ``xgboost``, ``lightgbm``, or ``scikit-learn``. Running ``pip install --upgrade openstef`` will typically resolve version mismatches.

.. note::

   If you are installing into an environment that already has ``xgboost`` or ``lightgbm`` pinned to an older version by another package, you may need to resolve the conflict manually. Check ``pip check`` for a summary of dependency issues.

Troubleshooting
---------------

**ImportError on xgboost or lightgbm**
   These are hard dependencies and are installed automatically with ``pip install openstef``. If they are missing, your pip cache may be stale — try ``pip install --no-cache-dir openstef``.

**Python version mismatch**
   OpenSTEF uses type annotation syntax (e.g. ``list[str]``) that requires Python 3.9+. Running under an older interpreter will produce ``SyntaxError`` at import time. Verify with ``python --version``.

**Editable install not reflecting changes**
   Ensure you installed with ``pip install -e .`` and that your IDE or shell is using the Python interpreter from the same virtual environment.

Next Steps
----------

With OpenSTEF installed, you are ready to build your first forecast. See the :doc:`quickstart` page for a minimal working example that trains a model and generates predictions in just a few lines of code.