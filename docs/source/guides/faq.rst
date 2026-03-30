Frequently Asked Questions
==========================

Common questions about OpenSTEF answered concisely for new users and conference attendees.

What is "short-term" forecasting?
----------------------------------

Short-term forecasting in OpenSTEF means predicting energy loads from hours to days ahead. Specifically, OpenSTEF focuses on forecasting horizons from 15 minutes up to approximately 47 hours (2 days) into the future.

This timeframe is crucial for grid operators who need to:

- Identify upcoming congestion before it occurs
- Plan maintenance activities
- Coordinate with customers for demand response
- Optimize existing grid capacity

The "short-term" horizon distinguishes OpenSTEF from long-term planning tools that forecast months or years ahead.

Do you need grid topology?
--------------------------

No, OpenSTEF works without grid topology information. The library forecasts each grid point independently using historical load data and weather information.

However, OpenSTEF can be combined with topology-aware tools like `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for advanced use cases. Research has shown this combination can improve forecasting accuracy for certain applications, particularly in MV route congestion management.

For most users, the point-based approach provides excellent results while keeping implementation simple.

What makes OpenSTEF special?
-----------------------------

OpenSTEF's "magic" lies in its domain-specific feature engineering combined with classical machine learning models:

**Energy-specific intelligence:**

- Automatic conversion of solar radiation and temperature into PV generation estimates
- Built-in understanding of energy consumption patterns
- Weather-dependent feature transformations tailored for grid forecasting

**Probabilistic forecasts:**

- Generates uncertainty bands, not just single-point predictions
- Provides quantile forecasts (P10, P30, P50, P70, P90) for risk assessment
- Enables confidence-based decision making

**Complete pipeline:**

- Handles data preprocessing, feature engineering, model training, forecasting, and evaluation
- Model-agnostic framework supporting XGBoost, LightGBM, linear models, and more
- Production-ready with automated workflows

The combination of smart features with proven ML algorithms delivers high performance without requiring deep learning complexity.

What accuracy can I expect?
----------------------------

Forecast accuracy depends heavily on your specific use case and data quality. OpenSTEF provides multiple metrics to assess performance:

.. code-block:: python

   from openstef_beam.metrics import mae, rmse, bias
   
   # Calculate common accuracy metrics
   mae_score = mae(realized, forecast)
   rmse_score = rmse(realized, forecast) 
   bias_score = bias(realized, forecast)

Factors affecting accuracy:

- **Data quality:** Clean, consistent historical data improves results
- **Forecast horizon:** Shorter horizons (hours) are more accurate than longer ones (days)
- **Location characteristics:** Stable industrial loads are easier to predict than volatile residential areas
- **Weather dependency:** High renewable penetration areas may have more uncertainty

The library includes comprehensive evaluation tools to measure performance for your specific situation.

How expensive is OpenSTEF to run?
----------------------------------

OpenSTEF is designed to be computationally efficient:

**System requirements:**

- Python 3.12+ on standard hardware
- Minimal memory footprint for typical forecasting tasks
- CPU-based models (no GPU required)

**Computational costs:**

- Training: Minutes to hours depending on data size and model complexity
- Forecasting: Seconds to minutes for real-time predictions
- Classical ML models are much faster than deep learning alternatives

**Deployment options:**

- Lightweight: Install only ``openstef-models`` for production forecasting
- Full toolkit: Use ``openstef[all]`` for research and development
- Modular: Choose components based on your needs

Most organizations can run OpenSTEF on existing infrastructure without significant hardware investments.

What about deep learning?
--------------------------

OpenSTEF currently focuses on classical machine learning models (XGBoost, LightGBM, linear regression) because they:

- Train faster and require less computational resources
- Provide excellent performance with proper feature engineering
- Are more interpretable for operational decision-making
- Work well with limited historical data

**Current status:**

- Deep learning module is in development
- Classical models remain the recommended approach
- Domain-specific features often outperform raw neural networks for energy forecasting

**When to consider deep learning:**

- Very large datasets (years of high-frequency data)
- Complex multi-modal inputs (images, text, time series)
- Specific research applications

For most practical energy forecasting applications, OpenSTEF's classical ML approach delivers superior results with lower complexity.

Who uses OpenSTEF operationally?
---------------------------------

**Production users:**

- **Alliander** (Netherlands): Primary operational deployment for congestion management
- **RTE and RTE International**: Transmission system operator applications
- **Sigholm** (Sweden): Consultancy services for local DSOs

**Research and development:**

- Multiple academic institutions
- Energy sector consultancies
- Grid operators evaluating implementation

The library is actively used in production environments, with a growing community of contributors and users across Europe.

Can I use OpenSTEF with my existing systems?
---------------------------------------------

Yes, OpenSTEF is designed for integration flexibility:

**Data sources:**

- Works with any time series data source
- Supports common formats (CSV, databases, APIs)
- Integration examples available for S3, InfluxDB, Databricks

**Deployment options:**

- Simple cron jobs for scheduled forecasting
- Orchestration with Dagster, Airflow, or similar tools
- API integration for real-time forecasting
- Batch processing for large-scale operations

**Output formats:**

- Standard pandas DataFrames
- JSON for API responses
- Database storage options
- Custom export formats

See the :doc:`how_to_guides` for specific integration examples.

How do I get started?
---------------------

1. **Install OpenSTEF:**

   .. code-block:: bash
   
      pip install openstef

2. **Try the quickstart:**

   Follow the :doc:`../getting_started/quickstart` to create your first forecast in minutes.

3. **Explore tutorials:**

   Work through the :doc:`../getting_started/tutorials` for comprehensive examples.

4. **Join the community:**

   - GitHub: https://github.com/OpenSTEF/openstef
   - LF Energy project page: https://www.lfenergy.org/projects/openstef/
   - Community meetings: Bi-weekly (open to all)

5. **Get support:**

   Contact us at openstef@lfenergy.org or join our community discussions.

The fastest path to success is starting with the quickstart guide and gradually exploring more advanced features as your needs grow.