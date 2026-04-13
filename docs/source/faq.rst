FAQ
===

This FAQ covers the most common questions from new users of OpenSTEF — the open-source Python library
for short-term energy forecasting. Whether you're evaluating the library, setting it up for the first
time, or trying to understand how it fits into your workflow, you should find answers here.

.. dropdown:: What is OpenSTEF?
   :icon: question

   OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python **library** that provides
   complete machine learning pipelines for short-term load forecasting in the energy sector.
   "Short-term" means predicting energy load hours to a couple of days ahead.

   OpenSTEF is not just a model — it is a model-agnostic framework that handles the full pipeline:
   data preprocessing, feature engineering, model training, probabilistic forecasting, evaluation,
   and post-processing. You bring your data; OpenSTEF brings the machinery.

   It was originally developed at Alliander, a Dutch grid operator, to tackle real-world challenges
   like congestion management, transport forecasting, EV charging capacity estimation, and grid loss
   prediction.

.. dropdown:: What makes OpenSTEF different from just using scikit-learn or XGBoost directly?
   :icon: light-bulb

   Using scikit-learn or XGBoost directly gives you a model. OpenSTEF gives you a **forecasting
   system** built for the energy domain. The key differences are:

   - **Probabilistic forecasts by default** — OpenSTEF produces uncertainty bandwidths (quantile
     forecasts) rather than single-point predictions, which is critical for operational
     decision-making.
   - **Domain-specific feature engineering** — built-in features for energy forecasting such as
     lag transforms, holiday calendars, and solar radiation estimates for PV generation.
   - **Complete pipeline** — preprocessing, training, prediction, and evaluation are all handled
     consistently, reducing the amount of boilerplate you need to write and maintain.
   - **Model-agnostic** — you can swap between XGBoost, LightGBM, GBLinear, and other forecasters
     without rewriting your pipeline.
   - **Multi-horizon forecasting** — a single trained model produces forecasts across multiple
     lead times in one shot.

.. dropdown:: What is short-term energy forecasting, and why does it matter?
   :icon: question

   Short-term energy forecasting means predicting electricity load (or generation) at a specific
   grid point, typically from a few hours up to two days ahead.

   Accurate short-term forecasts are essential for a growing number of grid operations:

   - **Congestion management** — identifying in advance when load will exceed equipment limits,
     so grid operators can act proactively (e.g., calling customers to reduce consumption).
   - **Transport forecasting** — planning how much capacity is needed on the network.
   - **EV charging** — estimating available charging capacity at a given location and time.
   - **Grid loss prediction** — forecasting energy losses in the distribution network.

   As solar panels, wind turbines, EVs, and heat pumps reshape both supply and demand, these
   forecasts become increasingly difficult — and increasingly important.

.. dropdown:: What Python version do I need?
   :icon: checklist

   OpenSTEF 4.0 requires **Python 3.12 or higher**. Python 3.13 is also supported.

   .. code-block:: bash

      python --version  # Should print 3.12.x or higher

   If you are on Python 3.10 or 3.11, consider using OpenSTEF 3.x, or upgrade your Python
   installation using `pyenv <https://github.com/pyenv/pyenv>`_ or
   `conda <https://conda.io/>`_.

   OpenSTEF runs on 64-bit Windows, macOS, and Linux.

.. dropdown:: How do I install OpenSTEF?
   :icon: checklist

   Install OpenSTEF using your preferred package manager:

   .. code-block:: bash

      # pip
      pip install openstef

      # uv (recommended for development)
      uv add openstef

      # conda
      conda install -c conda-forge openstef

   After installation, verify it works:

   .. code-block:: python

      import openstef_models
      print(f"OpenSTEF Models version: {openstef_models.__version__}")

   For a full walkthrough including optional packages and development setup, see
   :doc:`user_guide/installation`.

.. dropdown:: What packages make up OpenSTEF 4.0?
   :icon: info

   OpenSTEF 4.0 uses a **modular monorepo architecture**. Rather than one large package, it is
   split into focused components that you can install independently:

   - **openstef-core** — shared data structures, dataset types, base classes, and utilities used
     across all other packages.
   - **openstef-models** — the forecasting model implementations (XGBoost, LightGBM, GBLinear,
     and more).
   - **openstef-meta** — meta-learning and ensemble/combiner models.
   - **openstef-beam** — Apache Beam-based pipelines for large-scale distributed processing.
   - **openstef** — the top-level convenience package that pulls in the core components.

   If you only need to train and run forecasts locally, ``pip install openstef`` is all you need.
   Install ``openstef-beam`` only if you need distributed pipeline execution.

.. dropdown:: Which forecasting models does OpenSTEF support?
   :icon: question

   OpenSTEF ships with several ready-to-use forecasters in the ``openstef-models`` package:

   - **XGBoostForecaster** — gradient-boosted trees using XGBoost; a strong general-purpose choice.
   - **LGBMForecaster** — gradient-boosted trees using LightGBM; often faster to train on large
     datasets.
   - **GBLinearForecaster** — a linear booster via XGBoost's ``gblinear`` backend; useful when
     you expect a more linear relationship.
   - **FlatlinerForecaster** — a simple baseline that predicts historical quantile values; useful
     for sanity-checking pipelines.

   All forecasters share the same interface and support quantile (probabilistic) predictions.
   You can also implement your own forecaster by subclassing the ``Forecaster`` base class from
   ``openstef-core``.

.. dropdown:: How do I choose which model to use?
   :icon: light-bulb

   For most energy forecasting tasks, start with **LGBMForecaster** or **XGBoostForecaster** —
   both are gradient-boosted tree models that handle non-linear patterns, missing data, and
   mixed feature types well.

   A practical starting point:

   .. code-block:: python

      from openstef_core.types import LeadTime, Quantile
      from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

      forecaster = LGBMForecaster(
          quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
          horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("PT24H")],
      )

   Use **GBLinearForecaster** if your load signal is largely linear (e.g., a simple temperature
   relationship with little interaction). Use **FlatlinerForecaster** only as a baseline to
   confirm that your pipeline is working before switching to a real model.

   If you are unsure, XGBoost and LightGBM tend to perform similarly — try both and compare
   evaluation metrics.

.. dropdown:: What does "probabilistic forecast" mean, and do I need it?
   :icon: question

   A probabilistic forecast produces a **range of possible outcomes** rather than a single
   predicted value. OpenSTEF represents this as quantile forecasts — for example, the 10th,
   50th, and 90th percentiles of the predicted load.

   This means you get answers to questions like: *"What is the worst-case load I should plan
   for?"* or *"How confident is the model in this forecast?"*

   In practice, you almost always want probabilistic forecasts for energy applications:

   - Congestion management requires knowing the upper bound of expected load.
   - Scheduling reserves requires understanding forecast uncertainty.
   - Communicating risk to operators is much easier with confidence intervals.

   The median quantile (``Q(0.5)``) is equivalent to a traditional point forecast if you only
   need a single value.

.. dropdown:: What data do I need to get started?
   :icon: question

   At minimum, you need a **time series of historical load measurements** — a
   ``pandas.DataFrame`` with a ``DatetimeIndex`` and at least one column containing the load
   values you want to forecast.

   OpenSTEF's feature engineering pipeline can then automatically generate additional features
   from the timestamps (hour of day, day of week, public holidays, lag values, etc.). If you
   also have weather data (temperature, solar irradiance, wind speed), providing it will
   typically improve forecast accuracy significantly.

   Data does not need to be perfect — OpenSTEF's preprocessing handles common issues like
   missing values and outliers as part of the pipeline.

.. dropdown:: How do I run a first forecast end-to-end?
   :icon: light-bulb

   The fastest way to see OpenSTEF working is to follow the quickstart example, which walks
   through creating a dataset, configuring a pipeline, training a model, and producing a
   forecast. See :doc:`user_guide/index` for the full guide.

   A minimal pattern looks like this:

   .. code-block:: python

      from openstef_models.workflows import CustomForecastingWorkflow
      from openstef_core.datasets import VersionedTimeSeriesDataset

      # Wrap your pandas DataFrame in OpenSTEF's dataset type
      dataset = VersionedTimeSeriesDataset(data=your_dataframe)

      # Configure and run the workflow
      workflow = CustomForecastingWorkflow(model=your_forecasting_model)
      result = workflow.fit(dataset)

      # Generate a forecast
      forecast = workflow.predict(dataset)
      print(forecast.data.tail())

   See the :doc:`examples` page for complete, runnable examples including synthetic data
   generation so you can try it without needing your own dataset immediately.

.. dropdown:: Can I use OpenSTEF without Apache Beam or MLflow?
   :icon: question

   Yes. Apache Beam (``openstef-beam``) and MLflow are **optional** components.

   - **Without Beam** — you can train models and generate forecasts entirely in-process using
     standard Python. Beam is only needed when you want to run pipelines at scale across
     distributed infrastructure.
   - **Without MLflow** — you can use ``LocalModelStorage`` to save and load models to the local
     filesystem instead of an MLflow tracking server.

   Start simple and add these components only when your use case requires them.

.. dropdown:: Is OpenSTEF only useful for electricity grid operators?
   :icon: info

   No. While OpenSTEF was built by and for grid operators, the library is general enough for
   any short-term energy time series forecasting problem. It has been applied to:

   - Substation and feeder load forecasting
   - Solar PV generation forecasting
   - EV charging demand forecasting
   - Grid loss prediction
   - Any scenario where you need probabilistic, multi-horizon forecasts from tabular time series
     data

   If your problem involves predicting a time series a few hours to days ahead, OpenSTEF's
   pipeline is likely a good fit regardless of whether you work at a utility.

.. dropdown:: Where can I get help or report a bug?
   :icon: info

   - **Documentation** — start with :doc:`user_guide/index` and the :doc:`examples` page.
   - **GitHub Issues** — report bugs or request features on the
     `OpenSTEF GitHub repository <https://github.com/OpenSTEF/openstef>`_.
   - **Community** — see :doc:`project/index` for information on the project community,
     mailing lists, and how to reach the maintainers.
   - **Contributing** — if you want to fix a bug or add a feature yourself, see
     :doc:`contribute/index` for the contribution guide.