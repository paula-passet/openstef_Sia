Frequently Asked Questions
==========================

This page answers common questions from new users and conference attendees about OpenSTEF, the Python library for short-term energy forecasting.

What is OpenSTEF?
-----------------

OpenSTEF is a Python machine learning library, not a deployable application. It provides complete pipelines for short-term energy forecasting including data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. The library is model-agnostic and generates probabilistic forecasts with uncertainty estimates.

What do you mean by "short-term"?
----------------------------------

Short-term forecasting means predicting energy load hours to days ahead. This is distinct from:

- **Real-time forecasting** (minutes ahead)
- **Long-term planning** (months to years ahead)

The typical forecast horizon ranges from 1 hour to 48 hours ahead, which is optimal for operational decisions like congestion management and grid optimization.

Do I need grid topology information?
------------------------------------

No, OpenSTEF currently works point-based, forecasting each grid point independently without requiring network topology. However, you can combine OpenSTEF with power-grid-model for topology-aware forecasting if needed. Most use cases work effectively with point-based forecasts, especially for congestion management and transport forecasting.

What makes OpenSTEF special compared to other forecasting frameworks?
---------------------------------------------------------------------

OpenSTEF's key differentiators include:

- **Domain knowledge embedded**: Built-in feature engineering specific to energy forecasting (e.g., solar radiation to PV generation estimates)
- **Probabilistic forecasts**: Generates uncertainty bands, not just point predictions
- **Production-tested**: Currently running 10,000+ daily forecasts at Alliander
- **Resilient design**: Multiple fallback strategies ensure forecasts are always available
- **Energy-specific metrics**: Evaluation metrics designed for energy sector applications

What accuracy can I expect?
----------------------------

Accuracy depends heavily on your use case and data quality. The best approach is to test with your own data or the benchmark dataset. Different use cases have different accuracy requirements:

- **Congestion management**: Focus on peak detection accuracy
- **Transport forecasts**: Overall forecast accuracy across all periods
- **Grid losses**: Cost-weighted error minimization

For specific benchmarks, see the Alliander 2021 Energy Forecasting Benchmark dataset on GitHub.

How expensive is it to run?
----------------------------

OpenSTEF is designed for efficiency with classical machine learning models (XGBoost, LightGBM, linear models). Computational requirements are modest:

- Training: Can run on standard hardware
- Inference: Very fast, suitable for real-time applications
- Infrastructure: Minimal requirements for small-scale deployments

The library supports various deployment scales from research notebooks to enterprise integration.

What about deep learning?
--------------------------

OpenSTEF currently focuses on classical machine learning models (XGBoost, LightGBM, linear regression) combined with smart feature engineering. This approach often outperforms deep learning for energy forecasting while being more interpretable and computationally efficient.

A deep learning module is in development for future releases, but classical ML remains the primary focus due to proven effectiveness in production environments.

Can I use OpenSTEF outside the Netherlands?
--------------------------------------------

Yes, OpenSTEF v4.0 is designed for broader applicability beyond the Netherlands. The library supports:

- Customizable holiday calendars
- Flexible data formats
- Configurable weather data sources
- Adaptable feature engineering

However, some domain-specific logic may need customization for your region.

How do I get started?
---------------------

1. Install the library: ``pip install openstef``
2. Follow the quickstart guide for your first forecast
3. Explore the tutorials for comprehensive examples
4. Check the use cases guide to identify your specific application

For questions, join the OpenSTEF community Slack workspace or attend bi-weekly community meetings.