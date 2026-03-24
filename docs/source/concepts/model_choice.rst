Model Choice
============

OpenSTEF supports multiple machine learning algorithms for energy forecasting, each with distinct strengths and optimal use cases. The library includes automatic model selection capabilities, but understanding when to use each model type helps optimize forecasting performance for specific scenarios.

Supported Model Types
---------------------

XGBoost (Extreme Gradient Boosting)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

XGBoost is the most commonly used model in OpenSTEF, particularly effective for:

- **Complex non-linear relationships** between weather and energy consumption
- **Feature interactions** where multiple predictors combine in non-obvious ways
- **Robust performance** across diverse data quality conditions
- **Quantile regression** for probabilistic forecasts

XGBoost excels at capturing seasonal patterns, weather dependencies, and behavioral changes in energy consumption data.

LightGBM (Light Gradient Boosting Machine)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LightGBM offers similar capabilities to XGBoost with different performance characteristics:

- **Faster training** on large datasets
- **Lower memory usage** for resource-constrained environments
- **Good performance** on high-dimensional feature spaces
- **Effective handling** of categorical features

Linear Models
~~~~~~~~~~~~~

Linear regression models are suitable for:

- **Simple, interpretable** forecasting scenarios
- **Baseline comparisons** and benchmarking
- **Cases with limited training data** where complex models may overfit
- **Fast inference** requirements in production systems

When to Use Each Model
----------------------

Data Characteristics
~~~~~~~~~~~~~~~~~~~

**High aggregation levels** (e.g., grid losses, transport forecasts):
- Linear models often perform well due to smoother, more predictable patterns
- Weather dependencies are typically reduced at higher aggregation

**Low aggregation levels** (e.g., individual customer forecasts):
- XGBoost or LightGBM recommended for handling high variability
- Complex models better capture individual behavioral patterns

**Medium aggregation levels** (e.g., substation forecasts):
- XGBoost typically provides the best balance of accuracy and robustness
- Strong weather dependencies benefit from gradient boosting approaches

Operational Requirements
~~~~~~~~~~~~~~~~~~~~~~~

**Training speed priority**:
- LightGBM for faster model updates
- Linear models for rapid experimentation

**Inference speed priority**:
- Linear models for real-time applications
- XGBoost/LightGBM acceptable for batch forecasting

**Interpretability requirements**:
- Linear models provide clear coefficient interpretation
- Gradient boosting models offer feature importance rankings

Automatic Model Selection
-------------------------

OpenSTEF includes automatic model selection that:

- **Evaluates multiple model types** during training
- **Selects based on validation performance** using appropriate metrics
- **Considers computational constraints** specified in the prediction job
- **Provides fallback options** if the primary model fails

The automatic selection process uses cross-validation to compare model performance and selects the best-performing option for the specific use case and data characteristics.

.. note::
   Automatic model selection is recommended for most use cases. Manual model specification should be used when you have specific requirements or domain knowledge that suggests a particular approach.

Model Configuration
-------------------

Model selection is controlled through the prediction job configuration:

- **model**: Specify "xgb", "lgb", "linear", or "auto" for automatic selection
- **quantiles**: Define which quantiles to predict for probabilistic forecasts
- **horizon_minutes**: Forecast horizon affects optimal model complexity

Performance Considerations
--------------------------

**Training time**:
- Linear models: seconds to minutes
- XGBoost: minutes to hours depending on data size
- LightGBM: typically 2-3x faster than XGBoost

**Memory usage**:
- Linear models: minimal memory footprint
- LightGBM: lower memory usage than XGBoost
- XGBoost: highest memory requirements but often best accuracy

**Forecast accuracy**:
- Performance varies significantly by use case and data quality
- Gradient boosting models typically achieve best accuracy for complex energy patterns
- Linear models may be sufficient for highly aggregated or simple patterns

Best Practices
--------------

1. **Start with automatic model selection** to establish baseline performance
2. **Use backtesting** to evaluate model performance on historical data
3. **Consider operational constraints** (training time, memory, interpretability)
4. **Monitor model performance** over time and retrain as needed
5. **Experiment with different models** for different forecast horizons or use cases

The choice between models should be driven by your specific accuracy requirements, operational constraints, and data characteristics rather than theoretical preferences.