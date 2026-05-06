Ensemble Forecasting
====================

Energy load is shaped by many overlapping forces — temperature, time-of-day patterns, public holidays, sudden demand spikes — and no single model architecture captures all of them equally well. The ``openstef-meta`` package addresses this by letting you combine several base forecasters into a single ensemble, where a learned *combiner* decides how to blend or select their outputs. This page explains the motivation behind this approach, how the two main combiners work, and how to choose between them.

Why Combine Multiple Forecasters?
----------------------------------

A gradient-boosted tree (such as LightGBM) excels at capturing non-linear interactions between weather variables and load, but can struggle to extrapolate cleanly during unusual demand periods. A linear model, by contrast, generalises more smoothly outside its training distribution but may miss complex seasonal interactions. Rather than picking one and discarding the other, an ensemble keeps both and learns *when* each is trustworthy.

The practical gains are well-documented in forecasting literature: combining diverse models reduces variance without necessarily increasing bias, and the improvement is largest when the base models make different kinds of errors. In energy forecasting this diversity is natural — tree-based models and linear models respond differently to the same weather anomaly, and that disagreement is exactly the signal a combiner can exploit.

.. mermaid:: /diagrams/concepts/meta_ensembles_diagram_1.mmd

The ``openstef-meta`` ensemble sits on top of any set of base forecasters that share the same quantiles and horizons. The base models are trained independently; only the combiner sees their stacked predictions during its own training phase.

Base Forecasters
----------------

The ``EnsembleForecastingWorkflowConfig`` accepts a ``base_models`` list drawn from ``"lgbm"``, ``"gblinear"``, ``"xgboost"``, and ``"lgbm_linear"``. A typical pairing is an LightGBM tree model alongside a gradient-boosted linear model:

.. code-block:: python

    from datetime import timedelta
    from openstef_meta.workflows.config import EnsembleForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_A",
        base_models=["lgbm", "gblinear"],   # diverse architectures
        ensemble_type="learned_weights",
        combiner_model="lgbm",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
    )

The ``"lgbm"`` base model captures non-linear load patterns; ``"gblinear"`` provides a regularised linear baseline. Adding ``"xgboost"`` or ``"lgbm_linear"`` increases diversity further, at the cost of longer training time.

.. note::

   More base models do not always improve accuracy. Two well-chosen, architecturally distinct models often outperform four similar ones. Start with ``["lgbm", "gblinear"]`` and add models only when validation metrics justify the overhead.

The WeightsCombiner
-------------------

``WeightsCombiner`` (selected via ``ensemble_type="learned_weights"``) treats combination as a *classification* problem. For each time step it asks: which base forecaster is most likely to be closest to the true value? A small classifier — logistic regression, random forest, LightGBM, or XGBoost, controlled by ``combiner_model`` — is trained per quantile on historical base-forecaster errors.

At prediction time the combiner produces a probability distribution over the base models. This distribution is used in one of two ways:

- **Soft selection** (default): the final forecast is a weighted average of all base forecaster outputs, where the weights are the predicted probabilities. Every model contributes, but the one judged most reliable for the current conditions dominates.
- **Hard selection**: the combiner picks the single base forecaster with the highest probability and uses its output directly. This is more interpretable but can produce discontinuities when the selected model switches.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.learned_weights_combiner import WeightsCombiner
    from openstef_meta.models.forecast_combiners.hyperparams import XGBoostCombinerHyperParams

    combiner = WeightsCombiner(
        hparams=XGBoostCombinerHyperParams(),
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
    )

    # ensemble_data is an EnsembleForecastDataset containing stacked base predictions
    combiner.fit(ensemble_data, data_val=ensemble_val)
    forecast = combiner.predict(ensemble_data)

    # Inspect which base model dominates for each quantile
    contributions = combiner.predict_contributions(ensemble_data)
    importances = combiner.feature_importances  # per-quantile classifier importances

The classifier receives the same additional features available to the base models (weather, datetime encodings, etc.) via the ``additional_features`` argument to ``fit`` and ``predict``. This lets the combiner learn context-dependent rules such as "prefer the linear model on public holidays" without those rules being hard-coded.

.. mermaid:: /diagrams/concepts/meta_ensembles_diagram_2.mmd

The StackingCombiner
--------------------

``StackingCombiner`` (``ensemble_type="stacking"``) takes a different approach: it trains a separate *meta-regressor* for each quantile directly on the stacked base-forecaster predictions. Where ``WeightsCombiner`` learns which model to trust, ``StackingCombiner`` learns a new regression surface on top of all base outputs simultaneously.

Each meta-regressor is a full ``Forecaster`` instance — typically a gradient-boosted linear model (``"gblinear"``) — cloned once per quantile during initialisation. This means the stacking layer can learn non-linear blending rules and can, in principle, produce forecasts that lie outside the range of any individual base model.

.. code-block:: python

    from openstef_meta.models.forecast_combiners.stacking_combiner import StackingCombiner
    from openstef_models.models.forecasting.lgbm_linear_forecaster import LGBMLinearForecaster
    from openstef_models.hyperparams.lgbm_linear import LGBMLinearHyperParams

    meta_forecaster = LGBMLinearForecaster(
        hyperparams=LGBMLinearHyperParams(),
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
    )

    combiner = StackingCombiner(
        meta_forecaster=meta_forecaster,
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
    )

    combiner.fit(ensemble_data, data_val=ensemble_val)
    forecast = combiner.predict(ensemble_data)

Because each quantile has its own meta-regressor, ``StackingCombiner`` is particularly well-suited to probabilistic forecasting tasks where the spread of the prediction interval matters as much as the median. The meta-regressors for the tail quantiles (e.g. Q(0.05), Q(0.95)) can learn that certain base models are systematically over- or under-confident at the extremes.

Configuring the Ensemble via Workflow Config
--------------------------------------------

In practice you rarely construct combiners directly. The ``EnsembleForecastingWorkflowConfig`` wires everything together:

.. code-block:: python

    from datetime import timedelta
    from openstef_meta.workflows.config import EnsembleForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    # Stacking ensemble with seven probabilistic quantiles
    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_B",
        base_models=["lgbm", "gblinear", "xgboost"],
        ensemble_type="stacking",
        combiner_model="gblinear",          # meta-regressor architecture
        quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
        horizons=[LeadTime.from_string("PT36H")],
        sample_interval=timedelta(minutes=15),
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        energy_price_column="EPEX_NL",
    )

The ``combiner_model`` field controls the architecture of the combiner layer. For ``learned_weights`` the valid choices are ``"lgbm"``, ``"xgboost"``, ``"rf"``, and ``"logistic"``; for ``"stacking"`` use ``"gblinear"`` or ``"lgbm"``.

Choosing Between WeightsCombiner and StackingCombiner
------------------------------------------------------

The two combiners suit different situations:

- **WeightsCombiner** is the better default. It is interpretable — you can inspect ``feature_importances`` to understand which conditions favour each base model — and it degrades gracefully when one base model is consistently dominant (the classifier simply assigns it near-unit probability). Soft selection makes it robust to noisy classifier outputs.

- **StackingCombiner** is preferable when you care deeply about calibrated prediction intervals across many quantiles, or when the base models are individually well-calibrated and you want the meta-layer to learn a refined blending rather than a selection. It requires more training data for the meta-regressors to generalise, and the per-quantile models add memory and inference overhead.

- **Rules-based combination** (``ensemble_type="rules"``) is available as a lightweight fallback that uses fixed, hand-crafted weights. It requires no training data for the combiner and is useful as a baseline or when historical data for fitting the combiner is scarce.

.. note::

   When base models agree closely, the choice of combiner matters less. The ensemble benefit is largest when base models diverge — for example, during weather extremes or unusual demand events. If your base models produce nearly identical forecasts, consider diversifying the architectures before investing in a more complex combiner.

Trade-offs in Production
-------------------------

Ensembles improve accuracy but introduce operational complexity. A few practical considerations:

- **Training cost**: each base model trains independently, so wall-clock training time scales roughly linearly with the number of base models. The combiner training is fast by comparison.
- **Inference latency**: all base models run at prediction time before the combiner. For 15-minute resolution forecasts this is rarely a bottleneck, but it is worth profiling for very short sample intervals.
- **Model versioning**: the combiner and all base models must be stored and loaded together. The workflow handles this automatically when using MLflow storage, but custom deployment pipelines need to account for it.
- **Fallback behaviour**: if a base model fails at inference time, the combiner receives incomplete inputs. See :doc:`reliability_and_fallback` for how OpenSTEF handles degraded-mode operation.

Probabilistic forecasting with ensembles is closely related to the quantile outputs described in :doc:`quantiles_and_confidence`. The features fed to both base models and the combiner are covered in :doc:`feature_engineering`.