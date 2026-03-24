FAQ
===

This page answers the most common questions about OpenSTEF from conferences, community meetings, and new users.

About OpenSTEF's Nature
-----------------------

**Is OpenSTEF an application I can just install and run?**

No, OpenSTEF is a Python library, not a deployable application. You need to build your own application that uses OpenSTEF as a dependency. Think of it like pandas or scikit-learn - it provides the building blocks, but you write the code that uses those blocks.

To run OpenSTEF as a complete forecasting system, you'll need additional components like data fetchers, APIs, schedulers, and databases.

**Is OpenSTEF a pre-trained model I can use immediately?**

No, OpenSTEF doesn't come with pre-trained models. You train your own models using your specific data. OpenSTEF provides the machine learning pipeline and algorithms, but the models are trained on your historical energy data.

**What exactly is OpenSTEF then?**

OpenSTEF is a Python library that provides all the components needed to build short-term energy forecasting applications. It includes data validation, feature engineering, multiple machine learning algorithms, probabilistic forecasting, backtesting tools, and evaluation metrics - but you integrate these components into your own application.

Technical Questions
------------------

**Do I need grid topology data to use OpenSTEF?**

Not for basic energy forecasting. OpenSTEF can forecast energy loads using historical consumption data and weather information without knowing the physical grid structure.

However, if you want to do route-level congestion management, you'll need topology data and should combine OpenSTEF with power-grid-model for topology-aware analysis.

**What do you mean by "short term" forecasting?**

OpenSTEF typically forecasts 24-48 hours ahead with 15-minute resolution, though it's configurable. This covers operational planning horizons where weather forecasts are still reliable and energy patterns are predictable.

**What makes OpenSTEF special compared to other forecasting libraries?**

OpenSTEF is specifically designed for energy forecasting with several unique features:

- Probabilistic forecasts with quantile outputs (not just point estimates)
- Energy-specific feature engineering (weather dependency, seasonal patterns, etc.)
- Automatic model selection based on data characteristics
- Built-in backtesting tools for model validation
- Support for different aggregation levels (individual customers to grid-wide)
- Fallback strategies for missing data and model failures

**What kind of accuracy can I expect?**

Accuracy depends heavily on your use case, data quality, and aggregation level. Higher aggregation (many customers combined) typically gives better accuracy than individual customer forecasts.

The best way to assess accuracy for your specific case is to run backtests on your historical data. OpenSTEF includes comprehensive backtesting tools for this purpose.

**How expensive is it to run computationally?**

For typical setups:

- Training: A few minutes to hours depending on data size and model complexity
- Inference: Seconds to minutes for generating forecasts
- Memory: Moderate requirements, scales with data size
- Storage: Primarily for historical data and trained models

OpenSTEF is designed to be efficient enough for production use, but exact requirements depend on your data volume and forecast frequency.

**Does OpenSTEF support deep learning models?**

Currently, OpenSTEF focuses on tree-based models (XGBoost, LightGBM) and linear models, which have proven very effective for energy forecasting. Deep learning support may be added in future releases based on community needs and research developments.

**Can I use OpenSTEF without historical data?**

OpenSTEF requires historical data to train models - this is fundamental to how machine learning works. You need at least several months of historical energy consumption data to train effective models.

For completely new locations without historical data, you'd need to either:

- Wait to collect sufficient historical data
- Use models trained on similar locations (with appropriate domain adaptation)
- Start with simpler forecasting methods until you have enough data

Data and Integration
-------------------

**What data format does OpenSTEF expect?**

OpenSTEF expects time series data in pandas DataFrame format with specific column names. The core requirements are:

- Timestamp column (datetime index)
- Load/demand values
- Weather data (temperature, radiation, wind speed, etc.)
- Optional: holiday indicators, price data

See the API reference for detailed schema requirements.

**How do I integrate OpenSTEF with my existing systems?**

OpenSTEF is designed to integrate into existing data pipelines. Common integration patterns include:

- Batch processing: Run forecasts on schedule (cron jobs, Airflow, etc.)
- API integration: Wrap OpenSTEF in REST APIs for on-demand forecasts
- Database integration: Read from and write to your existing databases
- Cloud platforms: Deploy on AWS, Azure, GCP with appropriate data connectors

**Can OpenSTEF handle missing data?**

Yes, OpenSTEF includes several strategies for handling missing data:

- Automatic data validation and quality checks
- Interpolation methods for short gaps
- Fallback forecasting when primary models can't run
- Graceful degradation with reduced accuracy warnings

However, extensive missing data will impact forecast quality, so data quality is still important.

Getting Help
-----------

**Where can I get support?**

- GitHub Discussions: For questions and community support
- GitHub Issues: For bug reports and feature requests
- Documentation: Comprehensive guides and API reference
- LF Energy Community: Broader energy software community

**How do I contribute to OpenSTEF?**

See the Contributing Guide for details on:

- Code contributions and pull requests
- Bug reporting
- Feature requests
- Documentation improvements
- Community guidelines

**Is OpenSTEF production-ready?**

Yes, OpenSTEF is used in production by multiple organizations. However, as with any machine learning system, you should:

- Thoroughly test with your specific data
- Run comprehensive backtests
- Implement appropriate monitoring and fallbacks
- Follow software engineering best practices for production deployment