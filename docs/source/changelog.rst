Changelog
=========

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_ and uses
`Conventional Commits <https://www.conventionalcommits.org/>`_ to drive automated
changelog generation. This page summarises the most significant changes in each
release. For the full list of merged pull requests and individual commits, see the
`GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

If a release introduces breaking changes, a short note is included here. For
step-by-step migration instructions, refer to the
:doc:`../user_guide/migration` page in the User Guide.

.. note::

   OpenSTEF is a **library**. Version numbers apply to the individual packages
   (``openstef-core``, ``openstef-models``, ``openstef-beam``) as well as to the
   ``openstef`` meta-package that installs them together. Check the version of the
   specific package you depend on when evaluating compatibility.

   .. code-block:: python

      import importlib.metadata

      print(importlib.metadata.version("openstef"))         # meta-package
      print(importlib.metadata.version("openstef-core"))
      print(importlib.metadata.version("openstef-models"))
      print(importlib.metadata.version("openstef-beam"))

----

Version 4.x
-----------

4.0 — Modular Monorepo (Current Major Release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Status:** Alpha — in production at Alliander (10 000+ forecasts daily).

Version 4.0 is a ground-up redesign of OpenSTEF. The single-package layout of
the 3.x series has been replaced by a modular monorepo containing several
self-contained, independently versioned packages. The design goals driving this
restructure were:

- **Flexibility** — an unopinionated library that is not tied to a single
  deployment topology.
- **Modularity** — install only the components you need.
- **Enterprise integration** — a clean, composable API that fits into existing
  software landscapes without forcing a particular orchestration pattern.
- **Performance** — no regression in model quality or execution speed.

New packages
""""""""""""

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Package
     - What it provides
   * - ``openstef``
     - Meta-package; installs ``openstef-core`` and ``openstef-models``.
   * - ``openstef-core``
     - Dataset types (``ForecastDataset``, ``ForecastInputDataset``,
       ``TimeSeriesDataset``), base model interfaces (``Predictor``,
       ``Stateful``), shared exceptions, and testing utilities.
   * - ``openstef-models``
     - ML forecasting models, feature-engineering pipelines,
       energy-specific transformations, explainability mixins, and
       ready-to-use presets.
   * - ``openstef-beam``
     - Backtesting, Evaluation, Analysis, and Metrics (BEAM) — answers
       "are my model changes statistically significant?" with regression
       testing against benchmarks.
   * - ``openstef-compatibility``
     - Compatibility shim for 3.x code *(coming soon)*.
   * - ``openstef-foundational-models``
     - Deep-learning and foundational model integrations *(coming soon)*.

New and improved features
"""""""""""""""""""""""""

- **Probabilistic forecasting** — all built-in models produce quantile
  forecasts out of the box. Supported models include ``XGBoostForecaster``,
  ``LGBMForecaster``, ``LGBMLinearForecaster``, and ``GBLinearForecaster``.
- **Composable preprocessing pipelines** — preprocessing and postprocessing
  steps (``HolidayFeatureAdder``, ``DatetimeFeaturesAdder``, ``Imputer``,
  ``QuantileSorter``, ``ConfidenceIntervalApplicator``, …) are plain Python
  objects that can be assembled freely.
- **Presets** — high-level configuration objects let you get a fully
  assembled pipeline in a few lines:

  .. code-block:: python

     from openstef_models.presets import XGBoostPreset

     preset = XGBoostPreset(
         quantiles=[0.1, 0.5, 0.9],
         horizons=[1, 24, 48],
     )
     preset.fit(train_dataset)
     forecast = preset.predict(input_dataset)

- **Typed hyperparameters** — every model exposes a ``HyperParams`` dataclass
  (e.g. ``LGBMLinearHyperParams``) so IDE auto-complete and runtime
  validation work without extra effort.
- **State management and serialisation** — all models implement the
  ``Stateful`` interface with ``get_state`` / ``set_state`` and built-in
  version migration via ``migrate_state``, making safe model persistence
  straightforward.
- **Explainability** — models that mix in ``ContributionsMixin`` /
  ``ExplainableForecaster`` expose feature-contribution methods alongside
  their predictions.
- **``openstef-beam``** — a new first-class package for rigorous backtesting
  and statistical evaluation, spun out from internal Alliander tooling.

Breaking changes in 4.0
""""""""""""""""""""""""

.. warning::

   Version 4.0 contains **significant breaking changes** relative to the 3.x
   series. A dedicated migration guide is available at
   :doc:`../user_guide/migration`.

Key incompatibilities to be aware of:

- The ``openstef`` 3.x single-package import tree (``openstef.pipeline``,
  ``openstef.model``, ``openstef.tasks``, etc.) no longer exists. Imports
  must be updated to use the new package namespaces (``openstef_core``,
  ``openstef_models``, ``openstef_beam``).
- ``PredictionJobDataClass`` and the task-based pipeline API have been
  removed. Replace them with the new ``Preset`` or composable pipeline
  approach.
- The monorepo ships multiple independently versioned packages. Pin each
  package separately in your dependency file rather than pinning only
  ``openstef``.
- Python minimum version has been updated — check the installation guide for
  the current requirement.

----

Version 3.x
-----------

3.x was the production-stable series prior to the 4.0 redesign. It shipped as a
single ``openstef`` package with a task-oriented pipeline API built around
``PredictionJobDataClass``. The 3.x series is no longer receiving new features;
critical bug fixes may still be backported on a best-effort basis.

Notable milestones in the 3.x series are listed below in reverse chronological
order. For the complete commit-level history of any 3.x release, see the
`GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

3.x — Selected Highlights
^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Probabilistic output** — quantile regression support was introduced during
  the 3.x lifecycle, laying the groundwork for the probabilistic-first design
  of 4.0.
- **XGBoost and LightGBM models** — gradient-boosting backends were added and
  refined over successive 3.x releases.
- **Weather feature integration** — dedicated feature engineering for
  meteorological inputs (wind speed, irradiance, temperature) was stabilised.
- **Holiday calendars** — country-aware holiday feature injection was added to
  improve forecast accuracy around public holidays.
- **Confidence intervals** — post-processing steps for deriving confidence
  intervals from quantile predictions were introduced.
- **Performance improvements** — repeated profiling cycles reduced training and
  inference latency across the 3.x series.

----

How Releases Are Made
---------------------

OpenSTEF uses `Conventional Commits <https://www.conventionalcommits.org/>`_ to
drive automated changelog generation and semantic version bumps:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Commit prefix
     - Version bump
     - Example
   * - ``feat:``
     - Minor (``x.Y.0``)
     - ``feat(models): add transformer-based forecasting model``
   * - ``fix:``
     - Patch (``x.y.Z``)
     - ``fix(validation): handle missing weather data gracefully``
   * - ``feat!:`` / ``BREAKING CHANGE``
     - Major (``X.0.0``)
     - ``feat!: remove PredictionJobDataClass``
   * - ``docs:``, ``chore:``, ``style:``
     - No bump
     - ``docs: update installation guide``

Releases are published to `PyPI <https://pypi.org/project/openstef/>`_. To
subscribe to notifications for new releases, watch the
`GitHub repository <https://github.com/OpenSTEF/openstef>`_ and select
*Releases* under the *Watch* menu.

Staying Up to Date
------------------

Check which version you have installed and upgrade with your preferred tool:

.. tab-set::

   .. tab-item:: pip

      .. code-block:: bash

         pip show openstef
         pip install --upgrade openstef

   .. tab-item:: uv

      .. code-block:: bash

         uv list | grep openstef
         uv upgrade openstef

   .. tab-item:: conda

      .. code-block:: bash

         conda list openstef
         conda update openstef

   .. tab-item:: pixi

      .. code-block:: bash

         pixi list | grep openstef
         pixi upgrade openstef

.. note::

   Because OpenSTEF 4.0 ships multiple packages, upgrading the meta-package
   ``openstef`` will pull in the latest compatible versions of
   ``openstef-core`` and ``openstef-models``. If you depend on
   ``openstef-beam`` directly, upgrade it separately.

----

Reporting Issues
----------------

If you believe you have found a regression introduced in a specific release,
please open an issue on
`GitHub <https://github.com/OpenSTEF/openstef/issues>`_ and include:

- The version(s) affected (``pip show openstef`` output).
- A minimal reproducible example.
- The expected and actual behaviour.

For questions about migrating from 3.x to 4.x, see
:doc:`../user_guide/migration`.