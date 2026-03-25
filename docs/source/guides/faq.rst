Frequently Asked Questions
==========================


General Questions
-----------------


OpenSTEF is a Python machine learning library for energy forecasting, not a standalone application. To deploy as a full application, you need additional components like data fetchers, APIs, and schedulers. The library requires grid topology data to understand the electrical network structure for accurate load forecasting at different grid levels.


- Q: Is OpenSTEF a complete forecasting application? A: No, OpenSTEF is a Python library. To run as a full application, you need additional components like data fetchers, APIs, and forecasters.

- Q: Can I use OpenSTEF without a database? A: Yes, OpenSTEF is a library that can work with various data sources. Database connectivity requires additional components like OpenSTEF-dbc.

- Q: Does OpenSTEF only work for Dutch energy grids? A: No, while initially developed for Netherlands use cases, OpenSTEF 4.0 aims to generalize beyond Alliander-specific requirements for broader applicability.

- Q: Is OpenSTEF limited to energy forecasting? A: While designed for energy load forecasting, the library's machine learning approach can potentially be adapted to other time series forecasting domains.

- Q: Do I need MLFlow to use OpenSTEF? A: No, OpenSTEF 4.0 is decoupling external dependencies like MLFlow to enhance modularity and allow flexible deployment options.


Technical Capabilities
----------------------


OpenSTEF performs short-term forecasting, predicting energy load hours to days ahead with a typical horizon of up to 2 days. The library generates probabilistic forecasts with uncertainty bands rather than single-point predictions, enabling better decision-making under uncertainty. Forecast accuracy depends on data quality, model selection, and local conditions, with built-in domain knowledge for energy-specific feature engineering improving prediction quality.


.. note::

   OpenSTEF requires significant computational resources for training machine learning models and generating forecasts. Consider cloud deployment for scalability, or local deployment with adequate CPU/memory for your prediction job frequency. The framework supports both CRON-based scheduling and on-demand execution depending on your infrastructure needs.


Competitive Advantages
----------------------


OpenSTEF combines specialized input data preparation with energy-specific features for grid forecasting. The library delivers single-shot, multi-horizon forecasts with confidence estimates through two distinct methods. Its machine learning pipeline is purpose-built for energy sector applications, handling the unique temporal patterns and data requirements of electrical grid load prediction.


- Single-shot multi-horizon forecasting capability eliminates need for multiple model runs

- Built-in confidence estimation with two validated methods for uncertainty quantification

- Energy sector-specific feature engineering and data preparation optimized for grid forecasting

- Modular pipeline architecture allowing flexible deployment as library or full application

- Domain adaptation techniques (DAZLS) for zero-shot learning across different grid locations

- Integrated database schemas designed specifically for energy timeseries and relational data

- Complete ML pipeline from data ingestion to prediction with energy-focused preprocessing


Implementation and Deep Learning
--------------------------------


OpenSTEF primarily uses traditional machine learning algorithms like XGBoost for energy forecasting. While the library's architecture supports various machine learning approaches through its modular pipeline system, deep learning models are not the primary focus. The feature engineering and data validation components are designed to work with established algorithms that provide reliable performance for short-term energy forecasting tasks.


OpenSTEF offers flexible deployment options to suit different integration needs. You can use the complete task-based approach where OpenSTEF handles database operations, or integrate pipelines directly into your existing systems by managing data flow yourself. The library supports both standalone deployment through OpenSTEF-reference for complete stack implementation, and modular integration where individual components can be embedded into existing ML workflows.


