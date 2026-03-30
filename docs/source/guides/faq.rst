Frequently Asked Questions
==========================

This page answers common questions we hear at conferences and from new users. For detailed tutorials, see :doc:`/getting_started/tutorials`. For specific implementation tasks, check :doc:`how_to_guides`.

What does "short-term" mean?
-----------------------------

Short-term forecasting means predicting load hours to days ahead. OpenSTEF is designed for forecasts ranging from 15 minutes to approximately 48 hours into the future. This time horizon is critical for operational grid management—identifying when equipment will be overloaded, scheduling flexibility services, and optimizing asset utilization.

If you need longer-term forecasts (weeks to months ahead), OpenSTEF is not the right tool. For real-time control (seconds to minutes), you'll want a different approach.

Do I need grid topology information?
-------------------------------------

No. OpenSTEF forecasts each grid point independently using only historical load measurements and weather data. You don't need network models, impedance matrices, or connectivity information.

However, if you want topology-aware forecasting—for example, to model how load flows through the network—you can combine OpenSTEF with `power-grid-model <https://lfenergy.github.io/power-grid-model/>`_. See :doc:`/guides/use_cases` for the MV route congestion management example that demonstrates this integration.

What makes OpenSTEF different from other forecasting tools?
------------------------------------------------------------

Three things set OpenSTEF apart:

**Domain knowledge embedded in the library.** OpenSTEF includes energy-specific feature engineering—transforming solar radiation and temperature into PV generation estimates, handling seasonal patterns, and encoding time-based features relevant to energy systems. You don't need to be a domain expert to get good results.

**Probabilistic forecasts by default.** OpenSTEF generates quantile forecasts (e.g., 10%, 50%, 90% quantiles) that provide uncertainty estimates, not just point predictions. This is essential for risk management and decision-making under uncertainty.

**Complete pipeline, not just a model.** OpenSTEF handles data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. It's a framework for the entire forecasting workflow, not a wrapper around a single algorithm.

What accuracy can I expect?
----------------------------

It depends on your use case and data quality. Typical results:

- **Stable loads** (e.g., residential areas): rMAE of 5-10% for day-ahead forecasts
- **Volatile loads** (e.g., industrial sites with PV): rMAE of 10-20%
- **Peak detection**: Precision and recall typically 70-90% for congestion events

The quality of your input data matters more than the model. Clean historical load measurements and reliable weather forecasts are essential. See :doc:`/reference/concepts` for guidance on interpreting forecast quality metrics.

.. note::
   Use the metrics in ``openstef_beam.metrics`` to evaluate your forecasts. Different use cases require different metrics—rMAE for overall accuracy, precision/recall for peak detection, CRPS for probabilistic forecast quality.

Does OpenSTEF use deep learning?
---------------------------------

OpenSTEF primarily uses classical machine learning models—XGBoost, LightGBM, and linear quantile regression. These models are fast to train, interpretable, and perform well for energy forecasting when combined with good feature engineering.

Deep learning support is in development. For most energy forecasting use cases, gradient boosting models with domain-specific features outperform neural networks while being easier to train and debug.

How expensive is it to run?
----------------------------

Not very. Training a model for a single grid point typically takes seconds to minutes on a standard laptop. You can train hundreds of models per hour on modest hardware.

For production deployments forecasting thousands of grid points:

- **Training**: A few hours per day on a multi-core server (models are retrained periodically, not continuously)
- **Forecasting**: Seconds per prediction—fast enough for operational use
- **Storage**: Minimal—models are small (typically <10 MB each)

OpenSTEF is designed to run on commodity hardware. You don't need GPUs or specialized infrastructure.

What data do I need to get started?
------------------------------------

Minimum requirements:

- **Historical load measurements**: At least a few months of 15-minute resolution data
- **Weather forecasts**: Temperature, wind speed, and solar radiation for your location
- **Location coordinates**: Latitude and longitude for weather feature engineering

Optional but helpful:

- **Holiday calendars**: For modeling holiday effects
- **Additional weather variables**: Humidity, cloud cover, wind direction

See :doc:`/getting_started/quickstart` for a complete example with sample data.

Can I use my own models?
-------------------------

Yes. OpenSTEF is model-agnostic. While it includes XGBoost, LightGBM, and linear models out of the box, you can integrate custom models by implementing the forecaster interface. See :doc:`/getting_started/tutorials` for an example of custom model integration.

Is OpenSTEF an application or a library?
-----------------------------------------

OpenSTEF is a **Python library**, not a standalone application. You integrate it into your own systems and workflows. There's no GUI or web interface included.

If you need a complete application with dashboards and user management, you'll need to build that around OpenSTEF or use it as part of a larger system. See :doc:`/guides/how_to_guides` for deployment examples with orchestration tools like Dagster.

Who uses OpenSTEF in production?
---------------------------------

Alliander (a Dutch DSO) uses OpenSTEF operationally for congestion management across thousands of grid points. RTE and RTE International (transmission operators) are involved in development. Sigholm (a Swedish consultancy) uses OpenSTEF for local DSO clients.

The library is open source and freely available—you can use it for commercial or research purposes under the MPL-2.0 license.

Where can I get help?
----------------------

- **Slack**: Join the OpenSTEF community workspace (link on the `LF Energy project page <https://www.lfenergy.org/projects/openstef/>`_)
- **Community meetings**: Bi-weekly open meetings for users and contributors
- **GitHub Issues**: Report bugs or request features at https://github.com/OpenSTEF/openstef/issues
- **Documentation**: Start with :doc:`/getting_started/quickstart` and :doc:`/getting_started/tutorials`