Frequently Asked Questions
==========================

Common questions from conferences, new users, and production deployments.

What is "short-term" forecasting?
----------------------------------

Short-term forecasting means predicting energy load **hours to days ahead**, typically with a maximum horizon of 7 days. OpenSTEF focuses on this timeframe because:

- Weather forecasts beyond 7 days lack the 15-minute resolution needed for grid operations
- Solar and wind generation becomes unpredictable (cloudy vs sunny conditions)
- Forecast quality degrades significantly beyond this horizon

The library supports forecasting horizons from 15 minutes (0.25 hours) up to approximately 168 hours (7 days), with typical use cases focusing on 2-48 hour forecasts for congestion management.

Do I need grid topology information?
------------------------------------

**No, OpenSTEF works without grid topology.** The library operates on a point-based approach, forecasting each grid location independently. This makes it simple to deploy and scale across thousands of measurement points.

However, OpenSTEF can be combined with topology-aware approaches:

- Integration with `power-grid-model <https://power-grid-model.readthedocs.io/>`_ for topology-aware forecasting
- Published research demonstrates improved accuracy when combining both approaches
- Most production deployments start with point-based forecasting and add topology later if needed

What makes OpenSTEF special compared to other forecasting frameworks?
----------------------------------------------------------------------

OpenSTEF is specifically designed for energy forecasting, not general-purpose time series prediction:

**Energy-specific features:**
- Built-in feature engineering (solar radiation → PV generation estimates)
- Domain knowledge embedded in preprocessing pipelines
- Probabilistic forecasts with uncertainty quantification
- Peak detection capabilities for congestion management

**Production-ready reliability:**
- Multiple fallback strategies ensure forecasts are always available
- Fallback forecasts are clearly labeled for decision traceability
- Model-agnostic framework supports any scikit-learn compatible algorithm

**Complete ML pipeline:**
- Data validation and preprocessing
- Feature engineering with weather and market data
- Model training, evaluation, and deployment
- Not just a model - a complete forecasting system

What accuracy can I expect?
---------------------------

Forecast accuracy depends heavily on your specific use case and data quality. Key factors:

**Use case matters:**
- Congestion management cares about peak detection, not nighttime accuracy
- Transport forecasting needs different metrics than generation forecasting
- Accuracy requirements vary by grid voltage level and customer type

**Data quality is critical:**
- High-quality measurements with minimal gaps
- Reliable weather data aligned with your location
- Sufficient historical data (typically 1+ years for seasonal patterns)

**Best approach:** Test with the `Alliander 2021 Energy Forecasting Benchmark <https://github.com/OpenSTEF/alliander-energy-forecasting-benchmark>`_ to evaluate performance on realistic energy data across 50+ different signals including solar parks, wind farms, transformers, and district heating.

Common metrics include MAE (Mean Absolute Error), MAPE (Mean Absolute Percentage Error), and specialized peak detection rates. See :doc:`../reference/concepts` for detailed metric explanations.

How expensive is OpenSTEF to run?
---------------------------------

OpenSTEF is designed to be computationally efficient:

**Lightweight requirements:**
- Runs on standard Python environments (3.12+)
- Classical ML models (XGBoost, LightGBM) are fast to train and predict
- Minimal memory footprint for most use cases
- Can run on modest hardware or cloud instances

**Production scale:**
- Alliander runs 10,000+ forecasts daily in production
- Suitable for both single-location and large-scale deployments
- Modular architecture allows installing only needed components

**Cost factors:**
- Training: Minutes to hours depending on data size and model complexity
- Prediction: Seconds for most models
- Storage: Minimal - primarily time series data and trained models
- Weather data: External dependency that may have associated costs

For detailed installation options, see :doc:`../getting_started/installation`.

What about deep learning?
-------------------------

OpenSTEF currently focuses on **classical machine learning** approaches (XGBoost, LightGBM, linear models) because:

**Classical ML advantages for energy forecasting:**
- Fast training and prediction
- Interpretable results for operational decisions
- Robust performance with limited data
- Lower computational requirements
- Proven effectiveness in production

**Smart feature engineering + classical ML = high performance**
- Domain-specific features (weather transformations, seasonal patterns)
- Energy-specific preprocessing pipelines
- Probabilistic outputs with uncertainty quantification

**Deep learning development:**
- Foundation models module in progress
- Pre-trained models for energy data planned
- Transfer learning capabilities being developed
- Will complement, not replace, classical approaches

The model-agnostic design means you can already integrate custom deep learning models if needed. Most users find classical ML sufficient for their forecasting needs.

How reliable are OpenSTEF forecasts?
------------------------------------

OpenSTEF is designed for **production reliability** with multiple safeguards:

**Fallback strategies:**
- Extreme day profiles when insufficient data
- Historical averages for missing weather data
- Model degradation detection and automatic fallbacks
- All fallback forecasts clearly labeled for traceability

**Production validation:**
- Currently deployed at Alliander for congestion management
- 10,000+ daily forecasts in operational use
- Continuous monitoring and quality assessment
- Real-world testing during development phase

**Quality indicators:**
- Forecast quality labels (normal, substituted, fallback)
- Uncertainty quantification with confidence intervals
- Model performance metrics and degradation detection
- Data completeness and validation checks

See :doc:`../reference/concepts` for detailed explanations of forecast quality and uncertainty estimation.

Can I use OpenSTEF for my specific energy application?
------------------------------------------------------

OpenSTEF supports multiple energy forecasting use cases:

**Common applications:**
- Congestion management and peak detection
- Renewable generation forecasting (solar, wind)
- Grid loss prediction
- Transport capacity estimation
- District heating demand forecasting
- EV charging load prediction

**Flexibility:**
- Model-agnostic framework works with your preferred algorithms
- Custom feature engineering for domain-specific needs
- Integration with existing data systems and workflows
- Modular architecture allows selective component usage

For detailed use case examples, see :doc:`use_cases`. For implementation guidance, check :doc:`how_to_guides`.

How do I get started?
---------------------

**Quick start path:**
1. Install: ``pip install openstef``
2. Follow :doc:`../getting_started/quickstart` for your first forecast
3. Try the benchmark dataset to evaluate performance
4. Explore :doc:`../getting_started/tutorials` for comprehensive examples

**Production deployment:**
1. Start with point-based forecasting for your use case
2. Integrate with your data systems (see :doc:`how_to_guides`)
3. Set up monitoring and fallback strategies
4. Scale to multiple locations as needed

**Community support:**
- Join our Slack workspace for questions
- Attend bi-weekly community meetings
- Check GitHub issues for known problems
- Contact openstef@lfenergy.org for enterprise support

Where can I learn more?
-----------------------

**Documentation:**
- :doc:`../getting_started/tutorials` - Comprehensive hands-on examples
- :doc:`../reference/concepts` - Understanding forecasting fundamentals
- :doc:`../reference/architecture` - Technical system design
- :doc:`../api/index` - Complete API reference

**Community resources:**
- `GitHub repository <https://github.com/OpenSTEF/openstef>`_
- `LF Energy project page <https://www.lfenergy.org/projects/openstef/>`_
- `Alliander benchmark dataset <https://github.com/OpenSTEF/alliander-energy-forecasting-benchmark>`_
- Bi-weekly community meetings (open to all)

**Research and papers:**
- Academic publications on energy forecasting methodology
- Integration with power-grid-model for topology-aware forecasting
- Benchmark studies and performance comparisons