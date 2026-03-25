Changelog
=========


Release History Overview
------------------------


OpenSTEF follows semantic versioning principles with major releases introducing breaking changes and architectural improvements. The changelog is organized chronologically with each version documenting new features, bug fixes, and migration guidance. Version 4.0 represents a significant architectural advancement focusing on modularity, type safety, and broader domain applicability beyond the original Dutch energy market use cases.


.. note::

   This changelog is automatically generated from the project's CHANGELOG.md file and GitHub release notes. Manual edits to this section will be overwritten during documentation builds.


Latest Releases
---------------


OpenSTEF 4.0 represents a major architectural overhaul focused on modularity, type safety, and broader domain applicability. This release decouples external dependencies like MLFlow and openstef-dbc, introduces flexible configuration mechanisms, and generalizes domain-specific logic beyond Netherlands-specific use cases. Breaking changes include centralized data preprocessing, modular component design, and relaxed input data constraints to support diverse forecasting scenarios from research experimentation to enterprise integration.


Migration Guide
---------------


OpenSTEF 4.0 introduces significant architectural changes that require careful migration planning. The release decouples external dependencies like MLFlow and xgboost, adopts modular design patterns, and implements full type safety throughout the codebase. Users should review their existing integrations and prepare for updated APIs and configuration mechanisms.

Before upgrading, assess your current usage patterns and dependency chains. The new modular architecture may require refactoring custom components and updating configuration files. Test thoroughly in development environments, as the enhanced type safety and centralized preprocessing logic may surface previously hidden compatibility issues.


.. code-block:: python

   # OpenSTEF 3.x to 4.0 Migration Example

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline import train_model_pipeline

   # OpenSTEF 3.x approach
   job = PredictionJob(
       id=123,
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       feature_names=["load_entsoe", "weather_temp"]
   )
   model = train_model_pipeline(job, train_data)

   # OpenSTEF 4.0 approach - modular components
   from openstef.forecasting import Forecaster
   from openstef.models import XGBoostModel
   from openstef.preprocessing import StandardPreprocessor

   preprocessor = StandardPreprocessor()
   model = XGBoostModel(quantiles=[0.1, 0.5, 0.9])
   forecaster = Forecaster(
       model=model,
       preprocessor=preprocessor
   )

   forecaster.fit(train_data)
   predictions = forecaster.predict(test_data)


Complete Version History
------------------------


The complete version history below is automatically generated from the project's CHANGELOG.md file and GitHub releases. Each release entry includes version number, release date, and detailed descriptions of new features, bug fixes, breaking changes, and improvements. This comprehensive changelog provides developers and users with full transparency into the OpenSTEF library's evolution, helping track compatibility requirements and understand feature availability across different versions.


