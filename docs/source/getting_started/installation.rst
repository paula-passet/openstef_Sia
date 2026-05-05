Installation
============

This page covers everything you need to install OpenSTEF and verify that it is working correctly. Once installed, head to :doc:`quickstart` to run your first forecast.

System Requirements
-------------------

OpenSTEF requires **Python 3.9 or later**. It runs on Linux, macOS, and Windows. There are no special hardware requirements for basic use, though training on large datasets benefits from additional RAM and CPU cores.

Before installing, confirm your Python version:

.. code-block:: python

   python --version

Basic Installation
------------------

Install OpenSTEF from PyPI using ``pip``:

.. code-block:: bash

   pip install openstef

This installs the core library along with its primary dependencies, including:

- ``scikit-learn`` — base estimator interface and linear models
- ``xgboost`` — XGBoost gradient boosting regressor
- ``lightgbm`` — LightGBM gradient boosting regressor
- ``pandas`` and ``numpy`` — data handling
- ``pydantic`` — prediction job data validation

These cover the most commonly used model types: ``xgb``, ``lgb``, ``linear``, and their quantile variants.

Installing in a Virtual Environment
------------------------------------

It is strongly recommended to install OpenSTEF inside a virtual environment to avoid dependency conflicts with other projects.

Using ``venv``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

   pip install openstef

Using ``conda``:

.. code-block:: bash

   conda create -n openstef-env python=3.11
   conda activate openstef-env
   pip install openstef

Optional Dependencies
---------------------

Some model types and features require additional packages that are not installed by default. Install them individually based on what you need.

ARIMA models
^^^^^^^^^^^^

The ``ARIMAOpenstfRegressor`` depends on ``pmdarima``:

.. code-block:: bash

   pip install pmdarima

Without this package, attempting to use ``model_type="arima"`` in a prediction job will raise an ``ImportError`` at runtime.

Development and testing
^^^^^^^^^^^^^^^^^^^^^^^

To run the test suite or contribute to OpenSTEF, install the development extras:

.. code-block:: bash

   pip install openstef[dev]

This adds ``pytest``, ``pytest-cov``, and related tooling.

.. note::
   If you are integrating OpenSTEF into a larger pipeline (for example with Apache Beam), see the ``openstef-dazls`` or ``openstef-beam`` packages, which are distributed separately and have their own installation instructions.

Installing from Source
----------------------

To install the latest development version directly from GitHub:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e .

The ``-e`` flag installs the package in *editable* mode, so changes to the source files are reflected immediately without reinstalling.

Verifying the Installation
---------------------------

After installation, confirm that the package loads and that its version is accessible:

.. code-block:: python

   import openstef
   print(openstef.__version__)

To do a slightly deeper check, verify that the core model factory and the main model types are importable:

.. code-block:: python

   from openstef.model.model_creator import ModelCreator
   from openstef.enums import ModelType

   # List available built-in model types
   for model_type in ModelType:
       print(model_type.value)

Expected output will include entries such as ``xgb``, ``lgb``, ``xgb_quantile``, ``linear``, ``arima``, and others.

You can also instantiate a model directly to confirm the underlying ML library (e.g. XGBoost) is correctly installed:

.. code-block:: python

   from openstef.model.model_creator import ModelCreator
   from openstef.enums import ModelType

   model = ModelCreator.create_model(ModelType.XGB)
   print(type(model))
   # <class 'openstef.model.regressors.xgb.XGBOpenstfRegressor'>

If this runs without error, your installation is complete and functional.

.. note::
   If you see an ``ImportError`` mentioning ``xgboost`` or ``lightgbm``, those packages may not have been installed correctly. Try ``pip install xgboost lightgbm`` explicitly and re-run the check.

Dependency Overview
-------------------

The table below summarises which packages are needed for each model type:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Model type string
     - Regressor class
     - Required package
   * - ``xgb``, ``xgb_quantile``, ``xgb_multioutput_quantile``
     - ``XGBOpenstfRegressor``
     - ``xgboost`` *(installed by default)*
   * - ``lgb``
     - ``LGBMOpenstfRegressor``
     - ``lightgbm`` *(installed by default)*
   * - ``linear``, ``linear_quantile``, ``gblinear_quantile``
     - ``LinearOpenstfRegressor``
     - ``scikit-learn`` *(installed by default)*
   * - ``arima``
     - ``ARIMAOpenstfRegressor``
     - ``pmdarima`` *(optional)*
   * - ``flatliner``, ``median``
     - ``FlatlinerRegressor``, ``MedianRegressor``
     - ``scikit-learn`` *(installed by default)*

Upgrading
---------

To upgrade an existing installation to the latest release:

.. code-block:: bash

   pip install --upgrade openstef

Check the `changelog <https://github.com/OpenSTEF/openstef/releases>`_ before upgrading in a production environment, as new releases may change default model behaviour or prediction job validation rules.

Next Steps
----------

With OpenSTEF installed, continue to :doc:`quickstart` to train a model and generate your first forecast with a minimal working example.