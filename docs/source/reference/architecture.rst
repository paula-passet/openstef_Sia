Architecture
============

OpenSTEF V4 is designed as a modular Python library that transforms energy forecasting from a complex engineering challenge into a composable set of tools. This page explains the architectural principles behind the library and how its components work together to deliver robust short-term energy forecasting.

.. note::
   [DIAGRAM: Repository-level architecture showing the modular mono-repo structure with openstef-core, openstef-models, openstef-beam, and openstef-meta packages and their relationships]

Modular Design Philosophy
-------------------------

OpenSTEF V4 adopts a "modularity first" approach where each component can function independently while integrating seamlessly with others. This design enables users to adopt only the parts they need, whether building a simple research prototype or integrating into complex enterprise systems.

The library is structured as a modular mono-repo containing four self-contained packages:

**openstef-core**: Foundation layer providing data types, interfaces, and base classes that other packages depend on. Contains shared exceptions, testing utilities, and the fundamental abstractions that define how components interact.

**openstef-models**: Machine learning layer containing forecasting models, preprocessing pipelines, and energy-specific transformations. Includes explainability features and presets for quick start scenarios.

**openstef-beam**: Evaluation layer focused on Backtesting, Evaluation, Analysis, and Metrics. Answers the critical question "Are my model changes significant?" through regression testing against benchmarks.

**openstef-meta**: Advanced modeling layer providing modern ensemble models and sophisticated architectures for users requiring cutting-edge forecasting capabilities.

Component Interactions
----------------------

The packages interact through well-defined interfaces that maintain loose coupling while enabling powerful combinations:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_beam.evaluation import evaluate_forecast
   
   # Core provides the data abstraction
   dataset = TimeSeriesDataset.from_dataframe(data)
   
   # Models handles the forecasting logic
   model = ForecastingModel.from_preset("energy_congestion")
   forecast = model.predict(dataset)
   
   # BEAM evaluates the results
   metrics = evaluate_forecast(forecast, actual_values)

.. note::
   [DIAGRAM: Component-level interaction diagram showing data flow between core datasets, model preprocessing, forecasting, and evaluation components]

Data Flow Architecture
^^^^^^^^^^^^^^^^^^^^^^

The library follows a clear data flow pattern that separates concerns while maintaining flexibility:

1. **Data Ingestion**: Raw time series data enters through openstef-core's dataset abstractions
2. **Preprocessing**: openstef-models applies feature engineering and transformations
3. **Forecasting**: Models generate probabilistic forecasts with uncertainty estimates  
4. **Evaluation**: openstef-beam measures performance and provides analysis tools

This separation allows users to customize any stage without affecting others. For example, you can use custom preprocessing while leveraging the built-in models and evaluation tools.

Extensibility Points
--------------------

OpenSTEF V4 provides clear extension points for customization without modifying core code:

**Custom Models**: Implement the `BaseForecastingModel` interface to add new forecasting algorithms while maintaining compatibility with the evaluation and preprocessing infrastructure.

**Custom Transforms**: Extend the preprocessing pipeline with domain-specific feature engineering by implementing transform interfaces.

**Custom Metrics**: Add specialized evaluation metrics through the BEAM package's extensible metric system.

.. code-block:: python

   from openstef_models.models import BaseForecastingModel
   
   class CustomEnergyModel(BaseForecastingModel):
       def fit(self, data):
           # Your custom training logic
           pass
           
       def predict(self, data):
           # Your custom prediction logic
           pass

Integration Patterns
--------------------

The modular architecture supports multiple integration patterns to match different deployment scenarios:

**Research and Experimentation**: Use prebuilt components in notebooks with minimal configuration. The library provides sensible defaults that work out of the box for common energy forecasting tasks.

**Small-Scale Deployments**: Compose components into lightweight applications using the provided interfaces. Docker examples demonstrate how to package forecasting services with minimal infrastructure requirements.

**Enterprise Integration**: Leverage the flexible APIs and callback mechanisms to integrate forecasting capabilities into existing enterprise systems. The modular design allows selective adoption of components that fit your architecture.

.. note::
   [DIAGRAM: Integration patterns showing research notebook usage, small-scale deployment architecture, and enterprise integration scenarios]

Performance and Reliability
----------------------------

The architecture prioritizes performance without sacrificing maintainability:

- **Type Safety**: Full type annotations throughout the codebase catch errors early and improve IDE support
- **Efficient Implementations**: Core algorithms are optimized for production workloads
- **Memory Management**: Streaming data processing capabilities for large datasets
- **Error Handling**: Comprehensive exception hierarchy provides clear error messages and recovery paths

The modular design also enhances reliability by isolating failures and enabling graceful degradation when components encounter issues.

For more details on using these architectural components, see the getting started quickstart guide for immediate hands-on experience, or explore the use cases guide to understand how the architecture supports different forecasting scenarios.