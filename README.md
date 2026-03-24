<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/openstef_logo.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a comprehensive framework for short-term energy forecasting, designed specifically for the energy sector. It provides machine learning models, feature engineering tools, and evaluation metrics to create accurate probabilistic forecasts. The framework supports real-world energy forecasting scenarios with robust backtesting, model evaluation, and operational deployment capabilities.

Learn more at the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF v4.0 uses a modular monorepo structure with specialized packages:

- **openstef-core**: Core data structures, datasets, and utilities
- **openstef-models**: Machine learning models, feature engineering, and data processing
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Ensemble forecasting models and meta-learning components
- **openstef**: Meta-package combining core components

Each package can be installed independently based on your needs.

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# For most users
pip install openstef

# Core forecasting only
pip install openstef-models

# With all optional tools
pip install "openstef[all]"
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including troubleshooting, see our [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore our comprehensive examples in the [`examples/`](examples/) folder, which includes:

- **Quick Start Examples**: Basic forecasting workflows and model usage
- **Benchmarking Examples**: Complete evaluation studies using the Liander 2024 dataset
- **Advanced Examples**: Custom model pipelines, ensemble forecasting, and calibration techniques

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

If you use OpenSTEF in your research or projects, please cite it using:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  note = {LF Energy Foundation Project}
}
```

For more citation formats and project information, see our [documentation](https://openstef.github.io/openstef/v4/).

## Contact

For support and questions:

- **[Support Guide](.github/SUPPORT.md)** - how to get help with OpenSTEF
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - community Q&A and discussions  
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** - bug reports and feature requests
- **Email**: Contact us at `openstef@lfenergy.org`