<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

[![Build Status](https://github.com/OpenSTEF/openstef/workflows/Build/badge.svg)](https://github.com/OpenSTEF/openstef/actions)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

**OpenSTEF** is a complete framework for short-term energy forecasting. OpenSTEF provides backtesting, evaluation, analysis and metrics (BEAM) for systematic forecasting model development, along with a comprehensive suite of machine learning models and feature engineering tools for the energy domain. For more information about OpenSTEF, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Monorepo Structure

OpenSTEF 4.0 is organized as a monorepo with specialized packages:

- **openstef-core**: Core data structures, datasets, and utilities
- **openstef-models**: Machine learning models and feature engineering transforms
- **openstef-beam**: Backtesting, Evaluation, Analysis and Metrics framework
- **openstef-meta**: Meta-learning and ensemble forecasting models
- **openstef** (meta-package): Convenient installation of core components

## Installation

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF suite
pip install openstef[all]

# Install core forecasting components only
pip install openstef

# Install individual packages as needed
pip install openstef-models
pip install openstef-beam
```

### Using uv (recommended for development)

```bash
uv add openstef[all]
```

## Examples

Explore practical examples in the [`examples/`](examples/) directory:

- **Quick Start**: Basic forecasting workflow
- **Feature Engineering**: Custom transforms and pipelines
- **Model Training**: Training XGBoost, LightGBM, and ensemble models
- **Backtesting**: Realistic evaluation with BEAM framework
- **Benchmarking**: Systematic model comparison studies

See the [examples README](examples/README.md) for a complete overview of available examples.

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

If you use OpenSTEF in your research or project, please cite:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short-Term Energy Forecasting},
  author = {{OpenSTEF Contributors}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

## Contact

For support and questions, please visit our [support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md).