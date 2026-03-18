<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

[![Build Status](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml/badge.svg)](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL--2.0-blue.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a modular Python library for creating short-term energy forecasts. It provides machine learning models, backtesting frameworks, and evaluation tools designed specifically for energy sector applications. The library supports probabilistic forecasting with quantile estimates and includes comprehensive benchmarking capabilities for model comparison.

For more information about OpenSTEF, visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains OpenSTEF 4.0's monorepo structure with specialized packages:

- **`openstef-core`**: Core data structures, time series datasets, and shared utilities
- **`openstef-models`**: Machine learning models, feature engineering transforms, and forecasting workflows  
- **`openstef-beam`**: Backtesting, Evaluation, Analysis, and Metrics framework for model comparison
- **`openstef-meta`**: Ensemble forecasting models that combine multiple base forecasters
- **`examples/`**: Tutorial notebooks and benchmarking scripts
- **`docs/`**: Documentation source files

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF suite
pip install openstef

# Core forecasting models only
pip install openstef-models

# Backtesting and evaluation tools only  
pip install openstef-beam

# With all optional components
pip install "openstef[all]"
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia

# Install with uv (recommended)
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) folder, which contains:

- **Tutorials**: Step-by-step guides for common forecasting tasks
- **Benchmarks**: Model comparison studies on real energy datasets
- **Use cases**: Industry-specific forecasting applications

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

If you use OpenSTEF in your research or publications, please cite our work:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

## Contact

For support and questions:

- **GitHub Issues**: [Report bugs or request features](https://github.com/OpenSTEF/openstef/issues)  
- **Email**: Contact the team at `openstef@lfenergy.org`
- **Slack**: Join the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)

For more information, see our [Support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md).