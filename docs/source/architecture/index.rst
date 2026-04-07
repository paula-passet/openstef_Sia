Architecture
============

OpenSTEF is built on a modular three-package architecture that separates data handling, modeling, and evaluation concerns. This design allows you to install only what you need—from lightweight forecasting in production to comprehensive research workflows with full backtesting capabilities.

The three packages form a dependency hierarchy: ``openstef_core`` provides foundational data structures, ``openstef_models`` adds machine learning capabilities on top of core, and ``openstef_beam`` extends models with evaluation tools. Understanding this structure helps you choose the right components for your use case and integrate OpenSTEF effectively into your systems.

This section explains how the packages work together, what each one contains, and when to use which combination. Whether you're building a production forecasting service or conducting research experiments, you'll find guidance on architecting your solution with OpenSTEF.

:doc:`core` - The foundation package containing ``TimeSeriesDataset``, data validation, and core utilities that all other packages depend on.

:doc:`models` - Machine learning models, feature engineering transforms, and forecasting workflows built on top of the core data structures.

:doc:`beam` - Backtesting pipelines, performance metrics, evaluation frameworks, and analysis tools for measuring forecast quality.

.. note::
   [DIAGRAM: Package dependency graph showing openstef_core at the base, openstef_models depending on core, and openstef_beam depending on models. Include data flow arrows showing how TimeSeriesDataset flows through transforms to models to evaluation.]

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
