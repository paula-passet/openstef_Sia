Changelog
=========

This page summarises the changes introduced in each release of the OpenSTEF library.
Entries are listed in reverse chronological order. For guidance on updating your code
between major versions, see the :doc:`../user_guide/migration` page.

OpenSTEF follows `semantic versioning <https://semver.org/>`_. You can check the
version you have installed at any time:

.. code-block:: bash

   pip show openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ to
receive notifications whenever a new version is published.

----

Version 4.0
-----------

*Major release — breaking changes from 3.x*

OpenSTEF 4.0 is a significant architectural overhaul of the library. The central theme
is **modularity**: the monolithic 3.x codebase has been split into a set of focused,
independently installable packages that can be composed to suit your use case. Along
with the structural changes, 4.0 raises the minimum Python requirement to 3.12 and
introduces full type safety throughout the public API.

.. note::

   Upgrading from OpenSTEF 3.x involves breaking changes. Before upgrading, read the
   :doc:`../user_guide/migration` page for step-by-step instructions.

New features
^^^^^^^^^^^^

**Monorepo package structure**

The library is now distributed as a collection of specialised packages under a single
repository. The top-level ``openstef`` meta-package installs the most commonly needed
components automatically.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Package
     - Purpose
   * - ``openstef``
     - Meta-package; installs ``openstef-core`` and ``openstef-models``
   * - ``openstef-core``
     - Dataset types, base classes, shared exceptions, and testing utilities
   * - ``openstef-models``
     - Forecasting models, feature engineering pipelines, and energy-domain transforms
   * - ``openstef-beam``
     - Backtesting, Evaluation, Analysis, and Metrics (BEAM) tooling
   * - ``openstef-meta``
     - Advanced ensemble and meta-learning model architectures
   * - ``openstef-compatibility``
     - Compatibility shim for OpenSTEF 3.x code *(coming soon)*
   * - ``openstef-foundational-models``
     - Deep learning and foundation model integrations *(coming soon)*

Install only what you need:

.. code-block:: bash

   # Full installation (recommended for most users)
   pip install openstef

   # Evaluation tooling only
   pip install openstef-beam

   # Core types for building integrations
   pip install openstef-core

**Full type safety and Pydantic-based configuration**

All public classes — hyperparameters, transforms, and configuration objects — are now
typed with Pydantic models. Configuration can be serialised to and loaded from YAML
files directly:

.. code-block:: python

   from pathlib import Path
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams

   # Construct and persist hyperparameters
   params = XGBoostHyperParams(max_depth=6, learning_rate=0.05)
   params.write_yaml(Path("params.yaml"))

   # Reload from disk
   reloaded = XGBoostHyperParams.read_yaml(Path("params.yaml"))

**Redesigned transform pipeline**

Data preprocessing logic is now centralised in a composable transform system inside
``openstef-models``. Each transform is a standalone, testable class. The library ships
transforms for the time domain, weather domain, energy domain, and general-purpose
preprocessing:

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.general import Imputer, NaNDropper, Scaler

**Customisable holiday calendars**

``HolidayFeatureAdder`` now accepts any ISO 3166-1 alpha-2 country code, removing the
previous hard-coded dependency on Dutch public holidays. This makes the library
suitable for forecasting applications outside the Netherlands:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder

   # Use German public holidays
   holiday_transform = HolidayFeatureAdder(country="DE")

**Decoupled external dependencies**

Hard-coded dependencies on MLflow, ``openstef-dbc``, and specific XGBoost booster
configurations have been removed from the library core. These integrations can still
be used but are no longer required, making it straightforward to embed OpenSTEF in
existing infrastructure without pulling in unwanted dependencies.

**BEAM evaluation framework**

The ``openstef-beam`` package provides a structured framework for backtesting and
regression testing model changes. It answers the question *"are my model changes
statistically significant?"* and supports benchmark comparisons across model versions.

**Python 3.13 support**

OpenSTEF 4.0 is tested against Python 3.12 and 3.13.

Breaking changes
^^^^^^^^^^^^^^^^

- **Python 3.10 and 3.11 are no longer supported.** Python 3.12 is the minimum
  required version.
- **Package import paths have changed.** The monolithic ``openstef`` namespace has
  been reorganised across ``openstef_core``, ``openstef_models``, and ``openstef_beam``.
  Any ``from openstef.`` imports from 3.x will need to be updated.
- **The ``PredictionJob`` interface has been redesigned.** Configuration is now
  expressed through typed Pydantic models rather than dictionaries.
- **MLflow and ``openstef-dbc`` are no longer installed as transitive dependencies.**
  If your code relies on these, add them explicitly to your project dependencies.
- **Hard-coded Dutch holiday logic has been removed** from the default pipeline.
  Use ``HolidayFeatureAdder(country="NL")`` to restore equivalent behaviour.

See the :doc:`../user_guide/migration` page for a complete mapping of old import paths
to their 4.0 equivalents and worked examples of the most common migration scenarios.

----

Version 3.x
-----------

The 3.x series established OpenSTEF as a general-purpose short-term energy forecasting
library, evolving from an internal Alliander tool into an open-source project under the
LF Energy umbrella.

Notable milestones across the 3.x series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Probabilistic forecasting** — multi-quantile output support was added, enabling
  confidence intervals alongside point forecasts.
- **XGBoost integration** — gradient boosting became the primary model backend, with
  support for custom objective functions and evaluation metrics.
- **Pipeline abstraction** — the ``PredictionJob`` concept was introduced to bundle
  model configuration, feature settings, and forecast horizon into a single object
  passed through training and inference pipelines.
- **Feature engineering** — lag features, rolling aggregates, cyclic datetime
  encodings, and weather-derived features were added incrementally across minor
  releases.
- **MLflow experiment tracking** — optional integration with MLflow for logging
  training runs, metrics, and artefacts.
- **openstef-dbc connector** — a companion package (``openstef-dbc``) provided
  database connectivity for reading measurement data and writing forecasts, tightly
  coupling the library to Alliander's internal infrastructure.
- **LF Energy contribution** — the project was contributed to the Linux Foundation
  Energy ecosystem, broadening governance and community involvement.

.. note::

   Active feature development on the 3.x series has concluded. Critical bug fixes may
   still be backported on a case-by-case basis, but users are encouraged to migrate to
   4.0 for new projects.

----

Staying up to date
------------------

OpenSTEF publishes releases on `PyPI <https://pypi.org/project/openstef/>`_ and tags
each release on `GitHub <https://github.com/OpenSTEF/openstef/releases>`_. The GitHub
releases page includes the full diff and any additional release notes not captured
here.

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade openstef

To pin to a specific major version while allowing patch updates — useful in production
environments — use a compatible-release specifier:

.. code-block:: bash

   # Accept any 4.x release, but not 5.0
   pip install "openstef~=4.0"

If you maintain a ``pyproject.toml`` or ``requirements.txt``, the equivalent
constraint is:

.. code-block:: toml

   # pyproject.toml
   [project]
   dependencies = [
       "openstef>=4.0,<5.0",
   ]