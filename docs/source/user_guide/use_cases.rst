Common Use Cases
================

OpenSTEF is a flexible forecasting library that supports a wide range of energy system applications. This page describes the most common use cases, explains when to use each approach, and provides practical configuration examples to help you get started.

Understanding Your Use Case
---------------------------

Before building a forecasting model, identify what you're predicting and why. Different use cases have different requirements:

- **Congestion forecasts** prioritize peak detection accuracy to prevent overloads
- **Free space estimation** focuses on remaining capacity for connection requests
- **Grid loss forecasts** require accurate predictions across all load levels
- **Transport forecasts** need to handle aggregated flows across network segments
- **District heating demand** must account for temperature dependencies and thermal inertia

The configuration choices you make—from model selection to hyperparameters to evaluation metrics—should align with your operational needs.

Congestion Forecasting
----------------------

Congestion forecasts predict loading on transformers, cables, or other grid assets to identify when capacity limits may be exceeded. These forecasts are critical for preventing equipment damage and maintaining grid reliability.

**What makes congestion forecasting different:**

Peak detection matters more than average accuracy. A model that slightly overestimates peaks is often preferable to one with lower overall error but missed congestion events. This drives specific configuration choices around metrics, sample weighting, and model selection.

**Key configuration considerations:**

- Use metrics that emphasize peak performance: precision, recall, and F-beta scores with confusion matrices
- Apply exponential sample weighting to give recent data more influence
- Consider gradient boosting models (XGBoost, LightGBM) which excel at capturing peak behavior
- Set quantile predictions (e.g., 0.9, 0.95) to estimate high-load scenarios

**Example configuration:**

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow, ForecastingWorkflowConfig
   from openstef_models.models import ForecastingModel, GBLinearForecaster, GBLinearHyperParams
   from openstef_models.preprocessing import TransformPipeline, Scaler, HolidayFeatureAdder
   from openstef_models.types import LeadTime, Q, FeatureSelection, SampleWeightConfig
   from datetime import timedelta
   
   # Configuration optimized for congestion management
   config = ForecastingWorkflowConfig(
       model_id="transformer_123_congestion",
       target_column="load",  # Transformer loading in kW or MW
       horizons=[LeadTime.from_string("PT36H")],  # 36-hour ahead forecast
       quantiles=[Q(0.5), Q(0.9), Q(0.95)],  # Include high quantiles for peak scenarios
       sample_weight=SampleWeightConfig(
           method="exponential",
           weight_exponent=1.5,  # Emphasize recent patterns
       ),
   )
   
   # Model with preprocessing pipeline
   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(method="standard", selection=FeatureSelection(include={"temp", "wind", "radiation"})),
               HolidayFeatureAdder(country_code="NL"),
           ],
       ),
       forecaster=GBLinearForecaster(
           horizons=config.horizons,
           quantiles=config.quantiles,
           hyperparams=GBLinearHyperParams(
               n_steps=1000,
               learning_rate=0.3,
           ),
       ),
       target_column="load",
   )

When evaluating congestion forecasts, examine confusion matrices at critical thresholds (e.g., 80% of rated capacity) to understand how well the model detects near-overload conditions.

Free Space Estimation
---------------------

Free space forecasts estimate remaining capacity on grid assets, helping grid operators make informed decisions about new connection requests. Unlike congestion forecasting, which focuses on peaks, free space estimation requires accurate predictions across the entire load range.

**What makes free space estimation different:**

You need reliable forecasts of both current loading and future capacity usage. The difference between rated capacity and predicted peak load determines available space for new connections. Underestimating peaks could lead to accepting connections that cause future congestion.

**Key configuration considerations:**

- Use conservative quantile predictions (0.9 or higher) to ensure safety margins
- Validate model performance specifically at high-load periods
- Consider seasonal variations—summer and winter capacity may differ significantly
- Track forecast uncertainty to communicate confidence levels to stakeholders

**Example configuration:**

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow, ForecastingWorkflowConfig
   from openstef_models.types import LeadTime, Q
   from datetime import timedelta
   
   config = ForecastingWorkflowConfig(
       model_id="cable_456_free_space",
       target_column="load",
       horizons=[LeadTime.from_string("PT168H")],  # 1-week ahead for planning
       quantiles=[Q(0.5), Q(0.75), Q(0.9), Q(0.95)],  # Multiple quantiles for risk assessment
       predict_history=timedelta(days=14),
   )

To calculate free space, subtract the predicted high quantile (e.g., 0.95) from the asset's rated capacity. This provides a conservative estimate that accounts for forecast uncertainty.

Grid Loss Forecasting
---------------------

Grid loss forecasts predict energy losses in transmission and distribution networks. These losses depend on load levels, network topology, and physical characteristics of cables and transformers. Accurate loss forecasts are essential for energy procurement and financial settlement.

**What makes grid loss forecasting different:**

Losses typically follow a quadratic relationship with current (I²R losses), making them nonlinear functions of load. Models must capture this relationship accurately across the full operating range, not just at peaks.

**Key configuration considerations:**

- Include squared load features or use models that can learn nonlinear relationships
- Validate predictions across low, medium, and high load periods
- Consider temperature effects on conductor resistance
- Use R² and MAE metrics to assess overall accuracy

**Example configuration:**

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow, ForecastingWorkflowConfig
   from openstef_models.models import ForecastingModel, LGBMForecaster, LGBMHyperParams
   from openstef_models.preprocessing import TransformPipeline, Scaler
   from openstef_models.types import LeadTime, Q, FeatureSelection
   
   config = ForecastingWorkflowConfig(
       model_id="network_losses",
       target_column="losses_mw",
       horizons=[LeadTime.from_string("PT24H")],
       quantiles=[Q(0.5)],  # Deterministic forecast often sufficient
       temperature_column="ambient_temp",  # Temperature affects conductor resistance
   )
   
   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(method="standard", selection=FeatureSelection(include={"ambient_temp"})),
           ],
       ),
       forecaster=LGBMForecaster(
           horizons=config.horizons,
           quantiles=config.quantiles,
           hyperparams=LGBMHyperParams(
               n_steps=500,
               learning_rate=0.1,
               max_depth=6,  # Allow deeper trees to capture nonlinear relationships
           ),
       ),
       target_column="losses_mw",
   )

Transport Forecasting
---------------------

Transport forecasts predict energy flows through specific network segments, such as transmission lines or distribution feeders. These forecasts help operators understand how power moves through the grid and identify potential bottlenecks.

**What makes transport forecasting different:**

Transport flows aggregate multiple underlying loads and generation sources. The forecast must account for the net effect of all connected assets, which may include both consumption and production (e.g., solar generation).

**Key configuration considerations:**

- Ensure training data represents net flow (consumption minus generation)
- Account for bidirectional flow if relevant (e.g., feeders with significant solar)
- Consider correlations between connected loads
- Use appropriate aggregation when multiple segments feed into a common point

**Example configuration:**

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow, ForecastingWorkflowConfig
   from openstef_models.types import LeadTime, Q
   from datetime import timedelta
   
   config = ForecastingWorkflowConfig(
       model_id="feeder_789_transport",
       target_column="net_flow_mw",  # Positive for consumption, negative for export
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],  # Capture both high and low flow scenarios
       predict_history=timedelta(days=21),
       radiation_column="radiation",  # Important if solar generation is present
   )

District Heating Demand
-----------------------

District heating demand forecasts predict thermal energy requirements for heating networks. These forecasts exhibit strong temperature dependence and thermal inertia effects that differ from electrical load patterns.

**What makes district heating forecasting different:**

Heating demand responds to outdoor temperature with a time lag due to building thermal mass. Cold periods drive sustained high demand, while warm weather reduces load significantly. Wind speed and solar radiation also influence heating requirements through building heat loss and solar gains.

**Key configuration considerations:**

- Include temperature, wind speed, and radiation as primary features
- Consider lagged temperature features to capture thermal inertia
- Account for heating degree days or similar temperature-based metrics
- Validate model performance across seasonal transitions

**Example configuration:**

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow, ForecastingWorkflowConfig
   from openstef_models.models import ForecastingModel, XGBForecaster, XGBHyperParams
   from openstef_models.preprocessing import TransformPipeline, Scaler, HolidayFeatureAdder
   from openstef_models.types import LeadTime, Q, FeatureSelection
   
   config = ForecastingWorkflowConfig(
       model_id="district_heating_network_1",
       target_column="heat_demand_mw",
       horizons=[LeadTime.from_string("PT24H")],
       quantiles=[Q(0.5), Q(0.9)],
       temperature_column="outdoor_temp",
       wind_speed_column="windspeed",
       radiation_column="radiation",
   )
   
   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(
                   method="standard",
                   selection=FeatureSelection(include={"outdoor_temp", "windspeed", "radiation"}),
               ),
               HolidayFeatureAdder(country_code="NL"),
           ],
       ),
       forecaster=XGBForecaster(
           horizons=config.horizons,
           quantiles=config.quantiles,
           hyperparams=XGBHyperParams(
               n_steps=800,
               learning_rate=0.05,
               max_depth=7,
           ),
       ),
       target_column="heat_demand_mw",
   )

MV Route Congestion with Power Grid Model
------------------------------------------

Medium voltage (MV) route congestion forecasting combines load predictions with network topology analysis using power-grid-model. This advanced use case accounts for how power flows through the network topology, enabling more accurate congestion detection than simple load forecasting alone.

**What makes topology-aware forecasting different:**

Instead of forecasting individual asset loading directly, you forecast loads at network nodes and use power-grid-model to calculate resulting flows through cables and transformers. This approach captures how network topology affects loading patterns and enables "what-if" analysis of network reconfigurations.

**Key configuration considerations:**

- Forecast loads at individual connection points or aggregated nodes
- Use power-grid-model to perform load flow calculations based on forecasted loads
- Account for network topology changes (switching operations, outages)
- Consider voltage constraints in addition to thermal limits

**Example workflow:**

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow, ForecastingWorkflowConfig
   from openstef_models.types import LeadTime, Q
   from datetime import timedelta
   import pandas as pd
   
   # Step 1: Forecast loads at network nodes
   node_configs = {
       "node_A": ForecastingWorkflowConfig(
           model_id="node_A_load",
           target_column="load",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.5), Q(0.9)],
       ),
       "node_B": ForecastingWorkflowConfig(
           model_id="node_B_load",
           target_column="load",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.5), Q(0.9)],
       ),
   }
   
   # Step 2: After obtaining forecasts, use power-grid-model for load flow
   # (This requires power-grid-model to be installed separately)
   # 
   # from power_grid_model import PowerGridModel
   # 
   # # Define network topology
   # grid_model = PowerGridModel(input_data)
   # 
   # # Run load flow with forecasted loads
   # forecasted_loads = {
   #     "node_A": node_a_forecast["load"].values,
   #     "node_B": node_b_forecast["load"].values,
   # }
   # 
   # output_data = grid_model.calculate_power_flow(
   #     update_data=create_load_update(forecasted_loads)
   # )
   # 
   # # Extract cable/transformer loading from output_data
   # cable_loading = output_data["line"]["loading"]

.. note::

   Integration with power-grid-model requires additional setup and network data. See the power-grid-model documentation for details on defining network topology and running load flow calculations.

This topology-aware approach is particularly valuable for:

- Networks with complex meshed topologies where loading depends on power flow paths
- Scenarios involving network reconfiguration or switching operations
- Detailed voltage analysis in addition to thermal loading
- Coordinated forecasting across multiple network segments

Choosing the Right Approach
----------------------------

The table below summarizes key differences between use cases:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Use Case
     - Primary Focus
     - Key Metrics
     - Typical Quantiles
     - Special Considerations
   * - Congestion
     - Peak detection
     - Precision, recall, F-beta
     - 0.9, 0.95
     - Sample weighting, high quantiles
   * - Free Space
     - Conservative capacity
     - MAE, high quantile accuracy
     - 0.9, 0.95
     - Safety margins, seasonal validation
   * - Grid Loss
     - Overall accuracy
     - R², MAE
     - 0.5 (deterministic)
     - Nonlinear relationships, temperature
   * - Transport
     - Net flow patterns
     - MAE, R²
     - 0.1, 0.5, 0.9
     - Bidirectional flow, aggregation
   * - District Heating
     - Temperature response
     - MAE, R²
     - 0.5, 0.9
     - Thermal inertia, weather features
   * - MV Route (topology)
     - Network-wide loading
     - Precision, recall
     - 0.9, 0.95
     - Topology modeling, load flow

Next Steps
----------

Once you've identified your use case and configured your model:

- See :doc:`data_integration` for guidance on connecting your data sources
- Review :doc:`deployment` for production deployment patterns
- Consult :doc:`logging` for monitoring and debugging your forecasts

For questions about specific use cases or advanced configurations, consult the OpenSTEF community or review the example notebooks in the repository.