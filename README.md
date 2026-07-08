OpenSTEF
========
OpenSTEF
========

**Open Short-Term Energy Forecasting** is a Python machine learning framework for short-term energy load forecasting. It provides complete pipelines for data preprocessing, feature engineering, model training, probabilistic forecasting, and evaluation. OpenSTEF is a project of `LF Energy <https://www.lfenergy.org/projects/openstef/>`_ and is developed primarily by `Alliander <https://www.alliander.com/>`_.

Learn more at `openstef.org <https://openstef.org>`_.

--------------------
Repository Structure
--------------------

OpenSTEF is organized as a modular monorepo. Each package can be installed independently or together via the ``openstef`` meta-package.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Package
     - Description
   * - ``openstef-core``
     - Data types, interfaces, base classes, and shared utilities.
   * - ``openstef-models``
     - Forecasting models, preprocessing pipelines, and energy-specific transformations.
   * - ``openstef-meta``
     - Meta-learning and advanced ensemble model architectures.
   * - ``openstef-beam``
     - Backtesting, Evaluation, Analysis, and Metrics (BEAM).

--------------
How to Install
--------------

Requires Python >= 3.12.

Install the full framework (all packages):

.. code-block:: bash

   pip install openstef

Or install individual packages as needed:

.. code-block:: bash

   pip install openstef-core
   pip install openstef-models
   pip install openstef-beam
   pip install openstef-meta

Optional extras are available for specific model backends:

.. code-block:: bash

   pip install openstef-models[lgbm]
   pip install openstef-models[xgb-cpu]
   pip install openstef-models[tuning]

--------
Examples
--------

Worked examples are available in the `examples/ <https://github.com/OpenSTEF/openstef/tree/main/examples>`_ directory. These notebooks demonstrate common workflows including training, forecasting, and backtesting.

-------
License
-------

OpenSTEF is licensed under the `Mozilla Public License 2.0 <https://github.com/OpenSTEF/openstef/blob/main/LICENSE>`_.

------------
Contributing
------------

Contributions are welcome. Please see the `contributing guidelines <https://github.com/OpenSTEF/openstef/blob/main/.github/CONTRIBUTING.md>`_ for details on how to get started, coding standards, and the pull request process.

---------
Citations
---------

If you use OpenSTEF in academic work, please cite:

.. code-block:: bibtex

   @article{openstef2022,
     title={OpenSTEF: Open Short-Term Energy Forecasting},
     author={Alliander N.V.},
     year={2022},
     url={https://github.com/OpenSTEF/openstef}
   }

-------
Contact
-------

- **Slack:** `LF Energy Slack <https://slack.lfenergy.org/>`_ (join the OpenSTEF channel)
- **Email:** openstef@lfenergy.org
- **Issues:** `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_