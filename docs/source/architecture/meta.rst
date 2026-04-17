openstef_meta: Ensemble Models and Advanced Architectures
==========================================================

The ``openstef_meta`` package extends OpenSTEF's forecasting capabilities beyond single-model pipelines. It provides the infrastructure for **ensemble forecasting**: running multiple base forecasters in parallel, then combining their predictions through a learned combiner stage. This page covers the design of that ensemble architecture, the available combiner strategies, and how to assemble them in your own code.

For the base ``Forecaster`` interface and preprocessing transforms that feed into ensembles, see the :doc:`models` page. For backtesting and evaluating ensemble performance at scale, see the :doc:`beam` page.

.. mermaid:: /diagrams/architecture/meta_diagram_1.mmd


The Ensemble Pipeline
---------------------

The central class in ``openstef_meta`` is ``EnsembleForecastingModel``. It orchestrates a two-phase training process:

1. **Base forecaster phase** — each configured forecaster is trained independently on the same (preprocessed) data. Their in-sample predictions are collected into an ``EnsembleForecastDataset``.
2. **Combiner phase** — a ``ForecastCombiner`` is trained on top of those stacked predictions, learning how to weight or blend the base forecasters into a single output.

At prediction time the same flow applies: all base forecasters run in parallel, their outputs are assembled, and the combiner produces the final quantile forecasts.

``EnsembleForecastingModel`` is a sibling of ``ForecastingModel`` from ``openstef_models`` — it shares the same ``BaseForecastingModel`` base class but is not a subclass of it. This means it supports the same ``fit`` / ``predict`` contract while internally managing a collection of forecasters rather than a single one.

.. code-block:: python

    from openstef_meta.models.ensemble_forecasting_model import EnsembleForecastingModel
    from openstef_meta.models.forecast_combiners import StackingCombiner
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_models.models.forecasting.lgbm_linear_forecaster import LGBMLinearForecaster

    # Define two base forecasters
    forecasters = {
        "xgboost": XGBoostForecaster(quantiles=[0.1, 0.5, 0.9], horizons=[1, 4, 24]),
        "lgbm":    LGBMLinearForecaster(quantiles=[0.1, 0.5, 0.9], horizons=[1, 4, 24]),
    }

    # Use a stacking combiner as the meta-learner
    combiner = StackingCombiner(
        quantiles=[0.1, 0.5, 0.9],
        horizons=[1, 4, 24],
    )

    model = EnsembleForecastingModel(
        forecasters=forecasters,
        combiner=combiner,
        target_column="load",
    )

    fit_result = model.fit(data=train_dataset)
    forecast = model.predict(data=input_dataset)

The ``fit_result`` is an ``EnsembleModelFitResult``, which exposes both the combiner's metrics and the individual ``ModelFitResult`` for every base forecaster via ``component_fit_results``. This makes it straightforward to inspect whether a particular base model is contributing meaningfully to the ensemble.

.. code-block:: python

    # Inspect per-forecaster metrics alongside combiner metrics
    flat_metrics = fit_result.metrics_to_flat_dict()
    # Keys are prefixed: "xgboost_mae", "lgbm_mae", plus combiner-level metrics

    for name, child_result in fit_result.component_fit_results.items():
        print(f"{name}: {child_result.metrics_to_flat_dict()}")


Preprocessing Layers
--------------------

``EnsembleForecastingModel`` supports three distinct preprocessing scopes, giving fine-grained control over the data pipeline:

- **Common preprocessing** (``preprocessing`` field) — transforms applied once, before any forecaster sees the data. Useful for imputation, feature engineering, and other steps that are identical across all base models.
- **Model-specific preprocessing** (``model_specific_preprocessing``) — a dictionary keyed by forecaster name, containing additional transforms applied only to that forecaster's input. Use this when one model requires feature selection or scaling that would harm another.
- **Combiner preprocessing** (``combiner_preprocessing``) — transforms applied to the stacked predictions before the combiner is trained or used for inference.

The same three-layer pattern applies to postprocessing (``postprocessing``, ``model_specific_postprocessing``, ``combiner_postprocessing``).

.. note::

   The ``cutoff_history`` parameter controls how much historical data is retained when constructing lag features. Setting it too small will silently drop lag columns; setting it too large increases memory usage. Consult the feature engineering documentation in the :doc:`models` page for guidance on choosing an appropriate value.


Forecast Combiners
------------------

The combiner is the meta-learner that sits on top of the base forecasters. ``openstef_meta`` ships three combiner implementations, all inheriting from ``ForecastCombiner``.

``StackingCombiner``
^^^^^^^^^^^^^^^^^^^^

The most expressive option. A separate meta-regressor is trained **per quantile**, taking the base forecasters' quantile predictions as input features. Any ``Forecaster`` from ``openstef_models`` can serve as the meta-regressor template — the combiner clones it once per quantile during ``model_post_init``.

.. code-block:: python

    from openstef_meta.models.forecast_combiners import StackingCombiner
    from openstef_models.models.forecasting.lgbm_linear_forecaster import LGBMLinearForecaster

    # LGBMLinear as the per-quantile meta-regressor
    meta_forecaster = LGBMLinearForecaster(
        quantiles=[0.1, 0.5, 0.9],
        horizons=[1, 4, 24],
    )

    combiner = StackingCombiner(
        meta_forecaster=meta_forecaster,
        quantiles=[0.1, 0.5, 0.9],
        horizons=[1, 4, 24],
    )

Because each quantile has its own model, ``StackingCombiner`` can learn asymmetric combination rules — for example, trusting the XGBoost model more at the upper tail while preferring LGBMLinear at the median. It also supports ``predict_contributions`` and exposes ``feature_importances`` per quantile, making it fully compatible with OpenSTEF's explainability tooling.

``WeightsCombiner``
^^^^^^^^^^^^^^^^^^^

A classification-based combiner that learns **which base forecaster is likely to perform best** under prevailing conditions, rather than fitting a regression on their outputs. It operates in two modes:

- **Hard selection** — picks the single best forecaster for each instance.
- **Soft selection** — uses predicted class probabilities as convex weights, blending all forecasters proportionally.

The underlying classifier is configurable: ``LGBMCombinerHyperParams``, ``XGBCombinerHyperParams``, ``RFCombinerHyperParams``, and ``LogisticCombinerHyperParams`` are all available from ``openstef_meta.models.forecast_combiners``.

.. code-block:: python

    from openstef_meta.models.forecast_combiners import WeightsCombiner, LGBMCombinerHyperParams

    combiner = WeightsCombiner(
        hparams=LGBMCombinerHyperParams(),
        selection_mode="soft",   # or "hard"
        quantiles=[0.1, 0.5, 0.9],
        horizons=[1, 4, 24],
    )

``WeightsCombiner`` is a good default when you want interpretable combination logic: the feature importances of the internal classifiers directly indicate which input signals drive the model selection decision.

``ForecastCombiner`` (base class)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If neither built-in combiner fits your use case, subclass ``ForecastCombiner`` directly. The interface requires implementing ``fit``, ``predict``, ``predict_contributions``, and ``feature_importances``. The base class handles horizon management (``max_horizon``, ``with_horizon``) and enforces the ``EnsembleForecastDataset`` → ``ForecastDataset`` contract.


EnsembleForecastDataset and the Combiner Contract
--------------------------------------------------

The glue between base forecasters and the combiner is ``EnsembleForecastDataset`` (from ``openstef_core``). After the base forecaster phase, each forecaster's quantile predictions are assembled into this dataset using a column naming convention that encodes both the forecaster name and the quantile. The combiner receives this dataset — plus any ``additional_features`` you supply — and is responsible for producing a standard ``ForecastDataset``.

This separation means the combiner is entirely decoupled from the base forecasters' internals. You can swap combiners without retraining the base models, and you can inject external signals (e.g., weather uncertainty indices) as ``additional_features`` at combine time without touching the base forecaster preprocessing.

.. code-block:: python

    # Predict with additional features passed only to the combiner stage
    forecast = model.predict(
        data=input_dataset,
        additional_features=weather_uncertainty_dataset,
    )


Explainability in Ensembles
---------------------------

``EnsembleForecastingModel`` exposes explainability through ``get_explainable_components()``, which returns a dictionary of the base forecasters that implement ``ExplainableForecaster``. This lets you inspect feature importances and SHAP-style contributions at the individual model level, not just at the ensemble output.

.. code-block:: python

    explainable = model.get_explainable_components()
    for name, forecaster in explainable.items():
        importances = forecaster.feature_importances
        print(f"--- {name} ---")
        print(importances.head())

The ``StackingCombiner`` also implements ``ExplainableForecaster``, so the combiner's own feature importances (i.e., how much each base forecaster's prediction influenced the final output, per quantile) are accessible through the same interface.


Relationship to Other Packages
-------------------------------

``openstef_meta`` sits between ``openstef_models`` and ``openstef_beam`` in the typical workflow:

- **openstef_models** supplies the ``Forecaster`` implementations and preprocessing transforms that populate the ``forecasters`` dictionary. See the :doc:`models` page for details on available transforms and the ``ForecastingModel`` single-model pipeline.
- **openstef_beam** provides the backtesting and benchmarking infrastructure to evaluate whether an ensemble genuinely outperforms its base models. See the :doc:`beam` page for how to run statistically rigorous comparisons.
- **openstef_core** defines the shared data types (``TimeSeriesDataset``, ``EnsembleForecastDataset``, ``ForecastDataset``) and the ``BaseForecastingModel`` interface that ties everything together. See the :doc:`core` page for the dataset class hierarchy.