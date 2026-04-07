Architecture
============

OpenSTEF is organized as a **monorepo containing three distinct Python packages**, each with a clear responsibility. This layered design lets you install only what you need and keeps concerns cleanly separated: data structures live apart from models, and evaluation tooling is independent of both.

.. note:: [DIAGRAM: Three-layer package dependency diagram showing ``openstef_core`` at the base, ``openstef_models`` in the middle depending on ``openstef_core``, and ``openstef_beam`` at the top depending on both ``openstef_models`` and ``openstef_core``. Arrows indicate dependency direction (top-down). Data flows upward from core data structures through model training/prediction into backtesting and evaluation.]

Package Overview
----------------

The dependency chain flows in one direction: **core → models → beam**. Each package depends only on the layers below it, never sideways or upward.

``openstef_core`` is the foundation. It defines the shared data structures—most importantly ``TimeSeriesDataset``—along with configuration base classes, utilities, and custom exceptions. Every other package imports from core, making it the common language of the library. If you are building a custom integration or just need OpenSTEF's data containers, this is the only package you need.

``openstef_models`` builds on core to provide the machine learning layer: feature engineering transforms, model implementations, explainability tools, and workflow orchestration for training and prediction. This is where forecasting actually happens. Install this package when you want to train models or generate forecasts.

``openstef_beam`` (Backtesting, Evaluation, Analysis, and Metrics) sits at the top of the stack. It consumes models and core data structures to run backtests, compute forecast accuracy metrics, benchmark models against each other, and produce analysis reports. Reach for this package when you need to evaluate how well your forecasts perform or compare modeling approaches.

Explore the Pages
-----------------

:doc:`core` - Deep dive into the ``openstef_core`` package: the ``TimeSeriesDataset`` class, configuration base models, data versioning, and the shared data structures that underpin the entire library.

:doc:`models` - Deep dive into the ``openstef_models`` package: the transforms module for feature engineering, model implementations and interfaces, explainability utilities, and workflow orchestration for training and prediction.

:doc:`beam` - Deep dive into the ``openstef_beam`` package: backtesting against historical data, forecast accuracy metrics, structured evaluation reports, benchmarking across multiple targets, and analysis visualizations.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
