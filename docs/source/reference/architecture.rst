Architecture
============

OpenSTEF is designed as a modular Python library for short-term energy forecasting. This page explains the architecture at multiple levels: how the monorepo components fit together, how individual packages are structured, and how data flows through the system during typical forecasting workflows.

Understanding the architecture helps you choose the right components for your use case, integrate OpenSTEF into existing systems, and extend functionality when needed.

Repository-level architecture
------------------------------

OpenSTEF V4 is structured as a **modular monorepo** containing multiple self-contained packages. This design allows you to use only the components you need while maintaining consistency across the ecosystem.

.. note::
   [DIAGRAM: Sia-style repository architecture showing the five main packages (openstef-core, openstef-models, openstef-meta, openstef-beam, openstef-dbc) with dependency arrows. Core at the foundation, models and beam depending on core, meta depending on models, and dbc as a separate integration layer. Reference FOSDEM 2026 slide layout.]

The monorepo contains five core packages:

**openstef-core**
   Foundation package providing data types, interfaces, base classes, and shared utilities. All other packages depend on core. This is where common data structures like time series datasets and configuration objects live.

**openstef-models**
   The main forecasting package containing model implementations, feature engineering pipelines, preprocessing transformations, and explainability tools. This is model-agnostic—you can use XGBoost, LightGBM, or custom models through a common interface.

**openstef-meta**
   Advanced meta-learning and ensemble capabilities. Provides modern ensemble architectures that combine multiple base models for improved performance.

**openstef-beam**
   Backtesting, Evaluation, Analysis, and Metrics. Answers the critical question: "Are my model changes actually better?" Originally spun out from an internal Alliander project, BEAM provides regression testing against benchmarks and comprehensive model comparison.

**openstef-dbc**
   Database connectivity and data integration layer. Handles retrieval and storage of forecasts, measurements, and weather data from various backends.

This modular structure means you can:

- Use just ``openstef-models`` for basic forecasting without orchestration overhead
- Add ``openstef-beam`` when you need rigorous model evaluation
- Include ``openstef-meta`` for advanced ensemble techniques
- Integrate ``openstef-dbc`` when working with databases, or write your own data layer

Component-level architecture
-----------------------------

Each package follows a layered architecture that separates concerns and makes the codebase maintainable.

openstef-core package
^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Sia-style component diagram for openstef-core showing three layers: (1) Data types layer with Dataset, PredictionJob, ModelSpecification classes, (2) Base interfaces layer with BaseModel, BasePreprocessor, (3) Utilities layer with exceptions, testing helpers, validation functions. Arrows showing dependencies between layers.]

The core package provides the foundation:

- **Data types**: ``Dataset`` for time series data, ``PredictionJob`` for forecast configuration, ``ModelSpecification`` for model metadata
- **Base classes**: ``BaseModel`` interface that all forecasting models implement, ``BasePreprocessor`` for data transformations
- **Utilities**: Exception classes, testing helpers, validation functions, and shared constants

When you create a custom model or integrate OpenSTEF into your system, you'll interact primarily with these core abstractions.

openstef-models package
^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Sia-style component diagram for openstef-models showing: (1) Models layer with XGBModel, LGBModel, LinearModel, (2) Feature engineering layer with weather features, temporal features, lag features, (3) Preprocessing layer with missing data handling, outlier detection, scaling, (4) Explainability layer with SHAP integration. Show data flow from raw input through preprocessing and feature engineering to model training/prediction.]

The models package implements the forecasting pipeline:

**Model implementations**
   Concrete models like XGBoost, LightGBM, and linear regression, all implementing the ``BaseModel`` interface. Models are interchangeable—swap one for another without changing your workflow.

**Feature engineering**
   Transformations that create predictive features from raw data: weather variables, temporal patterns (hour of day, day of week), lag features, rolling statistics. These are energy-specific transformations tuned for grid forecasting.

**Preprocessing**
   Data cleaning and preparation: missing data imputation, outlier detection, scaling, and validation. Handles common data quality issues in operational environments.

**Explainability**
   SHAP-based model interpretation showing which features drive predictions. Critical for understanding model behavior and building trust with stakeholders.

**Presets**
   Pre-configured pipelines for common use cases. Start with a preset, then customize as needed.

Example of using the models package:

.. code-block:: python

   from openstef_models.models import XGBModel
   from openstef_models.transforms import add_missing_feature_columns
   from openstef_core.datasets import Dataset
   
   # Load your data
   dataset = Dataset.from_dataframe(df)
   
   # Add engineered features
   dataset = add_missing_feature_columns(dataset)
   
   # Train model
   model = XGBModel()
   model.fit(dataset.features, dataset.target)
   
   # Generate forecast
   forecast = model.predict(dataset.features)

openstef-beam package
^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Sia-style component diagram for openstef-beam showing workflow: (1) Backtesting engine that runs historical simulations, (2) Metrics calculator computing error statistics, (3) Evaluation module organizing results, (4) Analysis module generating visualizations and reports, (5) Benchmarking orchestrator running multi-model comparisons. Show feedback loop from analysis back to model development.]

BEAM provides the evaluation framework:

**Backtesting**
   Simulates how models would have performed in real operations by replaying historical data. Tests models under realistic conditions including data delays and missing values.

**Metrics**
   Comprehensive error metrics for energy forecasting: MAE, RMSE, skill scores, quantile coverage. Metrics are designed for time series and respect temporal dependencies.

**Evaluation**
   Organizes forecasting results into structured performance reports. Aggregates metrics across multiple forecasts and time periods.

**Analysis**
   Transforms evaluation results into visualizations and reports for decision-making. Helps answer: "Should I deploy this model?"

**Benchmarking**
   Runs complete model comparison studies across multiple forecasting targets. Essential for validating improvements before production deployment.

openstef-meta package
^^^^^^^^^^^^^^^^^^^^^

.. note::
   [DIAGRAM: Sia-style component diagram for openstef-meta showing: (1) Base models layer (multiple trained models), (2) Meta-learner layer that learns to combine base models, (3) Ensemble prediction layer that produces final forecasts. Show how predictions from base models feed into meta-learner, which outputs weighted combination.]

Meta-learning extends basic forecasting with ensemble techniques:

- Trains multiple base models with different configurations
- Learns optimal ways to combine their predictions
- Provides advanced ensemble architectures beyond simple averaging
- Particularly useful when you have diverse data sources or complex patterns

Data flow architecture
----------------------

Understanding how data flows through OpenSTEF helps you integrate it into your systems and debug issues.

Training workflow
^^^^^^^^^^^^^^^^^

The typical training workflow:

1. **Data retrieval**: Historical load measurements and weather data are loaded (from database, files, or API)
2. **Data validation**: Check for missing values, outliers, and data quality issues
3. **Feature engineering**: Create predictive features from raw measurements
4. **Preprocessing**: Clean, scale, and prepare data for modeling
5. **Model training**: Fit the forecasting model on prepared data
6. **Model validation**: Evaluate performance on held-out validation set
7. **Model storage**: Save trained model and metadata for later use

.. code-block:: python

   from openstef_models.models import XGBModel
   from openstef_models.transforms import add_missing_feature_columns
   from openstef_core.datasets import Dataset
   
   # Load historical data (measurements + weather)
   train_data = load_training_data(start_date, end_date)
   dataset = Dataset.from_dataframe(train_data)
   
   # Engineer features
   dataset = add_missing_feature_columns(dataset)
   
   # Split train/validation
   train_set, val_set = dataset.train_test_split(test_size=0.2)
   
   # Train model
   model = XGBModel()
   model.fit(train_set.features, train_set.target)
   
   # Validate
   val_predictions = model.predict(val_set.features)
   mae = mean_absolute_error(val_set.target, val_predictions)
   
   # Save for production use
   model.save("my_forecast_model.pkl")

Prediction workflow
^^^^^^^^^^^^^^^^^^^

The operational forecasting workflow:

1. **Model loading**: Load previously trained model
2. **Data retrieval**: Get recent measurements and weather forecast
3. **Feature engineering**: Apply same transformations used in training
4. **Prediction**: Generate forecast using loaded model
5. **Post-processing**: Add confidence intervals, apply business rules
6. **Forecast storage**: Save predictions for downstream systems

.. code-block:: python

   from openstef_models.models import XGBModel
   from openstef_models.transforms import add_missing_feature_columns
   
   # Load trained model
   model = XGBModel.load("my_forecast_model.pkl")
   
   # Get recent data and weather forecast
   forecast_data = load_forecast_inputs(forecast_horizon_hours=48)
   dataset = Dataset.from_dataframe(forecast_data)
   
   # Apply same feature engineering
   dataset = add_missing_feature_columns(dataset)
   
   # Generate forecast
   forecast = model.predict(dataset.features)
   
   # Add confidence intervals
   forecast_with_uncertainty = model.predict_quantiles(
       dataset.features, 
       quantiles=[0.1, 0.5, 0.9]
   )
   
   # Store for downstream use
   save_forecast(forecast_with_uncertainty)

Backtesting workflow
^^^^^^^^^^^^^^^^^^^^

The evaluation workflow using BEAM:

1. **Historical data loading**: Load extended historical dataset
2. **Backtest configuration**: Define evaluation period and forecast horizons
3. **Simulation**: For each time point, simulate operational forecasting
4. **Metrics computation**: Calculate error statistics across all forecasts
5. **Analysis**: Generate visualizations and performance reports
6. **Comparison**: Compare against baseline or alternative models

.. code-block:: python

   from openstef_beam.backtesting import backtest_model
   from openstef_beam.metrics import calculate_metrics
   from openstef_beam.analysis import generate_report
   
   # Load historical data for backtesting
   historical_data = load_historical_data(
       start_date="2023-01-01",
       end_date="2023-12-31"
   )
   
   # Run backtest simulation
   backtest_results = backtest_model(
       model=model,
       data=historical_data,
       forecast_horizon_hours=48,
       train_window_days=365
   )
   
   # Calculate performance metrics
   metrics = calculate_metrics(backtest_results)
   print(f"MAE: {metrics['mae']:.2f}")
   print(f"Skill score: {metrics['skill_score']:.3f}")
   
   # Generate analysis report
   report = generate_report(backtest_results, metrics)
   report.save("backtest_report.html")

Integration patterns
--------------------

OpenSTEF is a library, not an application. You integrate it into your systems using one of several common patterns.

Scheduled batch forecasting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run forecasts on a schedule (e.g., hourly) using cron or orchestration tools like Dagster:

- Orchestrator triggers forecast job at scheduled time
- Job loads trained model and retrieves input data
- Forecast is generated and stored in database
- Downstream systems consume forecasts via database or API

This is the most common pattern for operational forecasting. See :doc:`../guides/how_to_guides` for deployment examples.

On-demand API forecasting
^^^^^^^^^^^^^^^^^^^^^^^^^^

Serve forecasts via REST API for interactive applications:

- API endpoint receives forecast request
- Request handler loads model and retrieves data
- Forecast is generated and returned in response
- Useful for dashboards and real-time applications

Event-driven forecasting
^^^^^^^^^^^^^^^^^^^^^^^^^

Trigger forecasts based on events (new data arrival, model updates):

- Event system monitors for triggers (new measurements, weather updates)
- Event handler initiates forecast workflow
- Results are published to message queue or database
- Enables reactive forecasting with minimal latency

Embedded forecasting
^^^^^^^^^^^^^^^^^^^^

Embed OpenSTEF directly in larger applications:

- Import OpenSTEF packages as dependencies
- Call forecasting functions from application code
- Manage data and models within application context
- Provides maximum flexibility and control

Design principles
-----------------

OpenSTEF's architecture reflects several key design principles:

**Library-first design**
   OpenSTEF is a library, not an application. It provides building blocks you compose into your own workflows. This makes it flexible and integrable but requires you to handle orchestration, data management, and deployment.

**Modular and unopinionated**
   Use only the components you need. Swap implementations without rewriting code. Not built for a single use case—adapt it to your requirements.

**Model-agnostic**
   The architecture doesn't favor specific ML algorithms. Use XGBoost, LightGBM, linear models, or implement custom models through standard interfaces.

**Energy-domain focused**
   While model-agnostic, the feature engineering and evaluation tools are optimized for energy forecasting. Weather dependencies, temporal patterns, and grid-specific metrics are built in.

**Performance without compromise**
   Architecture choices prioritize model quality and execution speed. Forecasts must be accurate and fast enough for operational use.

**Data availability aware**
   Handles realistic constraints: delayed measurements, missing data, delayed weather forecasts. The architecture assumes imperfect data, not laboratory conditions.

See also
--------

- :doc:`concepts` - Understand key forecasting concepts and terminology
- :doc:`../guides/use_cases` - Common use cases and when to use them
- :doc:`../guides/how_to_guides` - Practical integration and deployment guides
- :doc:`../getting_started/quickstart` - Get started with a simple forecast