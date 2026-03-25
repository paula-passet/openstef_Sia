# OpenSTEF

<img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo_color.png" alt="OpenSTEF logo" width="200">

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL--2.0-brightgreen.svg)](https://github.com/OpenSTEF/openstef/blob/main/LICENSE)

## What is OpenSTEF

OpenSTEF is a modular Python library for creating short-term energy forecasts. Version 4.0 introduces a complete architectural refactor with enhanced modularity, modern Python development practices, and comprehensive backtesting, evaluation, and analysis capabilities. The library provides everything from basic forecasting models to sophisticated ensemble methods and benchmarking frameworks.

For more information, visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages:

- **openstef-core**: Core data structures, datasets, and utilities
- **openstef-models**: ML models, feature engineering, and workflows  
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics
- **openstef-meta**: Ensemble forecasting and meta-learning models
- **openstef**: Meta-package combining core functionality

## How to Install

### Requirements
- Python 3.12+ (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# For most users - includes core models and utilities
pip install openstef

# Core forecasting models only
pip install openstef-models

# With benchmarking and evaluation tools
pip install "openstef[beam]"

# Complete installation with all components
pip install "openstef[all]"
```

### Package-Specific Installation

```bash
# Individual packages
pip install openstef-core          # Core utilities and datasets
pip install openstef-models        # Forecasting models and transforms
pip install openstef-beam          # Backtesting and evaluation
pip install openstef-meta          # Ensemble methods
```

For detailed installation instructions including troubleshooting, see the [installation guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

The [`examples/`](examples/) folder contains comprehensive tutorials and use cases:

- **Basic Forecasting**: Get started with simple forecasting workflows
- **Benchmarking**: Compare models using the Liander 2024 benchmark dataset
- **Feature Engineering**: Advanced feature creation and model configuration
- **Evaluation**: Comprehensive model evaluation and analysis

See the [examples README](examples/README.md) for a complete overview of available examples and tutorials.

## License

**Mozilla Public License Version 2.0** - see [LICENSE.md](LICENSE.md) for details.

This project includes third-party libraries licensed under their respective Open-Source licenses. SPDX-License-Identifier headers show applicable licenses. License files are in the [LICENSES/](LICENSES/) directory.
## Contributing

We welcome contributions to OpenSTEF 4.0! 

**[Read our Contributing Guide](https://openstef.github.io/openstef/v4/contribute/)** - documentation for contributors including:

- How to report bugs and suggest features
- Documentation improvements and examples
- Code contributions and development setup
- Sharing datasets and real-world use cases

### Quick Development Setup

```bash
# Clone and set up for development
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev

# Run tests and quality checks
uv run poe all
```

**Code of Conduct**: We follow the [Contributor Code of Conduct](https://openstef.github.io/openstef/v4/contribute/code_of_conduct.html) to ensure a welcoming environment for all contributors.
## Citations

If you use OpenSTEF in your research or commercial applications, please cite the project:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  publisher = {LF Energy Foundation},
  license = {MPL-2.0}
}
```

## Contact

For support and questions:

- **Documentation**: [OpenSTEF Documentation](https://openstef.github.io/openstef/v4/)
- **GitHub Discussions**: [Community Q&A](https://github.com/OpenSTEF/openstef/discussions)
- **Issues**: [Bug Reports & Feature Requests](https://github.com/OpenSTEF/openstef/issues)
- **Email**: openstef@lfenergy.org
- **Slack**: Join the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)

For detailed support information, see our [Support Guide](https://openstef.github.io/openstef/v4/project/support.html).