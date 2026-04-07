Changelog
=========

This page documents the version history of OpenSTEF, including new features, bug fixes, and breaking changes for each release. OpenSTEF follows `Semantic Versioning <https://semver.org/>`_ (SemVer), where version numbers take the form ``MAJOR.MINOR.PATCH``:

- **MAJOR** versions introduce breaking API changes
- **MINOR** versions add new functionality in a backward-compatible manner
- **PATCH** versions contain backward-compatible bug fixes

OpenSTEF uses `Conventional Commits <https://www.conventionalcommits.org/>`_ to generate this changelog automatically. For the most up-to-date and detailed release information, see the `GitHub Releases <https://github.com/OpenSTEF/openstef/releases>`_ page.

.. note::

   If you are upgrading across major versions, see the :doc:`user_guide/migration` guide for step-by-step instructions on updating your code.


How to Read This Changelog
--------------------------

Each release entry is organized into the following categories:

- **Features** (``feat``): New capabilities added to the library
- **Bug Fixes** (``fix``): Corrections to existing behavior
- **Breaking Changes**: Changes that require modifications to your code
- **Performance** (``perf``): Improvements to speed or resource usage
- **Deprecations**: Features marked for removal in a future version

Package-specific changes are noted with a scope prefix (e.g., ``models:``, ``beam:``, ``core:``) to indicate which OpenSTEF package is affected.


Version 4.0.0
-------------

*Major release — complete architectural redesign*

OpenSTEF 4.0 is a ground-up rewrite that transforms the library into a modular, composable toolkit for short-term energy forecasting. This release is **not backward-compatible** with 3.x.

.. warning::

   Version 4.0.0 contains significant breaking changes. If you are upgrading from 3.x, consult the :doc:`user_guide/migration` guide before updating.

Highlights
^^^^^^^^^^

- **Modular package architecture**: OpenSTEF is now split into three independent packages that can be installed separately or together:

  - ``openstef-core`` — shared data structures, datasets, and utilities
  - ``openstef-models`` — forecasting model implementations and feature engineering
  - ``openstef-beam`` — backtesting, evaluation, analysis, and metrics

- **Python 3.12+ required**: Leverages modern Python type safety features and performance improvements. Python 3.13 is also supported. Users on Python 3.10 or 3.11 should remain on OpenSTEF 3.x.

- **New model architecture**: Redesigned ``BaseForecastingModel``, ``ForecastingModel``, and ``ComponentSplittingModel`` classes provide a clean pipeline abstraction (preprocessing → forecasting → postprocessing).

- **Pydantic-based configuration**: All model and pipeline configurations use Pydantic models with YAML serialization support via ``BaseConfig``.

- **Built-in datasets**: The ``openstef_core.datasets`` module provides versioned time series datasets for testing and experimentation.

- **BEAM evaluation framework**: A dedicated package for backtesting, evaluation, analysis, and metrics, including benchmarking tools for comparing models across multiple forecasting targets.

- **Modern development tooling**: Monorepo workspace managed with ``uv``, automated quality checks with ``poe``, and ``ruff`` for linting and formatting.

Breaking Changes
^^^^^^^^^^^^^^^^

- **Package imports have changed completely**:

  .. code-block:: python

     # OpenSTEF 3.x (old)
     from openstef.model import forecasting
     from openstef.validation import validation

     # OpenSTEF 4.0 (new)
     from openstef_models.models import ForecastingModel
     from openstef_beam.evaluation import evaluation

- **Python 3.10 and 3.11 are no longer supported.** Python 3.12 or higher is required.

- **Configuration format changed** from dictionaries to Pydantic-based ``BaseConfig`` objects with YAML support:

  .. code-block:: python

     from openstef_core.base_model import BaseConfig

     # Configurations are now typed Pydantic models
     config = BaseConfig.read_yaml("config.yaml")

- **Model state migration**: Models saved with 3.x need to be retrained or migrated. The ``BaseForecastingModel`` includes a ``_migrate_state`` method to assist with version-to-version state migration.

- **Installation commands changed**: The library is now installed as ``openstef`` (meta-package), ``openstef-models``, ``openstef-beam``, or ``openstef-core`` depending on your needs. See :doc:`user_guide/installation` for details.

New Features
^^^^^^^^^^^^

- ``feat(models)``: ``ForecastingModel`` pipeline with composable preprocessing, forecasting, and postprocessing stages
- ``feat(models)``: ``ComponentSplittingModel`` for decomposing forecasts into constituent components
- ``feat(models)``: Explainability utilities in ``openstef_models.explainability``
- ``feat(models)``: Feature engineering transforms in ``openstef_models.transforms``
- ``feat(core)``: Versioned dataset access via ``openstef_core.datasets``
- ``feat(core)``: ``BaseConfig`` with ``read_yaml()`` and ``write_yaml()`` for typed configuration management
- ``feat(beam)``: Backtesting framework for simulating real-world operational performance
- ``feat(beam)``: Metrics module with energy-forecasting-specific evaluation measures
- ``feat(beam)``: Analysis module for generating visualizations and reports
- ``feat(beam)``: Benchmarking tools for multi-model, multi-target comparison studies
- ``feat``: Meta-package with extras for flexible installation (``openstef[all]``, ``openstef[beam]``)


Version 3.x and Earlier
------------------------

OpenSTEF 3.x was a monolithic package providing short-term energy forecasting capabilities as a single ``openstef`` package. It supported Python 3.10 and above.

For the complete release history of the 3.x series, see the `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_ and filter by the ``v3.*`` tags.

.. note::

   OpenSTEF 3.x is in maintenance mode. It will continue to receive critical bug fixes but no new features. Users are encouraged to migrate to 4.0 for the latest capabilities.


Versioning Policy
-----------------

OpenSTEF follows semantic versioning across all packages in the workspace. Here is what you can expect from each type of release:

**Patch releases** (e.g., 4.0.0 → 4.0.1)
   Bug fixes and minor documentation updates. Safe to upgrade without code changes.

**Minor releases** (e.g., 4.0.x → 4.1.0)
   New features and non-breaking enhancements. Existing code continues to work, though new deprecation warnings may appear.

**Major releases** (e.g., 4.x.x → 5.0.0)
   Breaking API changes. Always consult the changelog and migration guide before upgrading.

All packages within the OpenSTEF workspace (``openstef-core``, ``openstef-models``, ``openstef-beam``) are versioned together to ensure compatibility. When you upgrade one package, upgrade all of them to the same version.


Staying Informed
----------------

To receive notifications about new releases:

- **Watch the repository**: Star and watch the `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_ for release notifications.
- **Subscribe to releases**: Use GitHub's "Releases only" watch option to receive emails for each new version.
- **Check installed versions** programmatically:

  .. code-block:: python

     import openstef_models
     print(f"OpenSTEF Models: {openstef_models.__version__}")

     try:
         import openstef_beam
         print(f"OpenSTEF BEAM: {openstef_beam.__version__}")
     except ImportError:
         print("OpenSTEF BEAM not installed")

- **Community channels**: Join the ``#openstef`` channel on the `LF Energy Slack workspace <https://slack.lfenergy.org/>`_ for announcements and discussion.