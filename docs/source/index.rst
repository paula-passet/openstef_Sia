OpenSTEF Documentation
======================

.. toctree::
   :maxdepth: 1
   :caption: Contents

   getting_started/quickstart
   getting_started/tutorials
   guides/use_cases
   guides/how_to_guides
   guides/faq
   reference/architecture
   reference/concepts
   reference/changelog
   api/index

What Makes OpenSTEF Different
------------------------------

OpenSTEF is designed specifically for energy sector forecasting challenges. Unlike general-purpose forecasting frameworks, it includes built-in domain knowledge for energy applications:

- Energy-specific feature engineering that automatically derives solar and wind generation estimates from weather data
- Probabilistic forecasts with uncertainty quantification for risk-based decision making  
- Split forecasting that decomposes total load into renewable and conventional components
- Resilient fallback strategies ensuring forecasts are always available for critical operations
- Model-agnostic framework supporting multiple machine learning algorithms

The library handles the complete forecasting workflow from data preprocessing through model training, prediction generation, and performance evaluation.

Common Use Cases
^^^^^^^^^^^^^^^^

OpenSTEF supports diverse energy forecasting applications:

- Grid congestion management and capacity planning
- Transport and distribution load forecasting  
- Renewable energy generation forecasting
- Grid loss prediction and optimization
- District heating demand forecasting
- Electric vehicle charging capacity estimation

Documentation Structure
------------------------

This documentation guides you from initial setup through advanced customization. Start with the quickstart for immediate hands-on experience, then explore tutorials for comprehensive examples and guides for specific implementation scenarios.

Getting Started
^^^^^^^^^^^^^^^

New users should begin with the quickstart to train their first model and generate forecasts in minutes. The tutorials then provide comprehensive examples covering data preparation, model training, backtesting, and advanced customization options.

Implementation Guides  
^^^^^^^^^^^^^^^^^^^^^

Practical guides cover common implementation tasks including deployment setup, data integration with external systems, and migration between OpenSTEF versions. The FAQ addresses frequent questions from conferences and new users.

Technical Reference
^^^^^^^^^^^^^^^^^^^

The reference section provides detailed architecture diagrams, core concept explanations, and comprehensive API documentation. The changelog tracks version history and breaking changes.

Community and Support
----------------------

OpenSTEF is actively developed by Alliander and the open source community. Join our Microsoft Teams channel for discussions, questions, and collaboration opportunities. The project welcomes contributions through GitHub issues and pull requests.

For technical support, consult the FAQ section or post questions in the community Teams channel. The Technical Steering Committee meets monthly to discuss project direction and major decisions.

The project is licensed under the Mozilla Public License 2.0, ensuring it remains open and accessible for energy sector innovation.