Architecture
============

OpenSTEF is built as a modular library with three specialized packages that work together to provide a complete forecasting solution. This section explains how these packages are organized, how they depend on each other, and how to choose the right components for your use case.

Understanding OpenSTEF's architecture helps you install only what you need, integrate the library into your systems effectively, and contribute to the right package when extending functionality.

The **core** page explores the foundation of OpenSTEF: the ``openstef_core`` package. This package provides the ``TimeSeriesDataset`` class and related data structures that all other packages build upon. It contains no machine learning logic—just the essential data containers and utilities that ensure consistency across the library.

The **models** page examines ``openstef_models``, which implements the forecasting models and feature engineering pipeline. You'll learn about the ``transforms`` module for creating time-based features, the model implementations themselves, and how explainability tools help interpret predictions. This package depends on core for its data structures.

The **beam** page covers ``openstef_beam``, the evaluation and analysis toolkit. BEAM (Backtesting, Evaluation, Analysis, and Metrics) provides the tools to measure model performance, run historical simulations, and generate reports. It depends on both core and models to evaluate complete forecasting pipelines.

.. note::
   [DIAGRAM: Package dependency diagram showing openstef_core at the base, openstef_models depending on core, and openstef_beam depending on both. Include data flow arrows showing how TimeSeriesDataset flows from core → models → beam, and how predictions flow back through the evaluation pipeline.]

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
