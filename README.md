<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

[![Build Status](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://badge.fury.io/py/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

OpenSTEF is a complete machine learning pipeline for short-term energy forecasting, providing probabilistic forecasts for the electricity grid. It combines robust preprocessing, feature engineering, and state-of-the-art machine learning models to deliver accurate and reliable energy predictions.

Learn more about OpenSTEF at [lfenergy.org/projects/openstef](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF v4.0 is organized as a modular monorepo with specialized packages:

- **openstef**: Meta-package combining core forecasting functionality
- **packages/openstef-core**: Shared data structures, types, and utilities  
- **packages/openstef-models**: Machine learning models and feature engineering
- **packages/openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics
- **packages/openstef-meta**: Ensemble forecasting and meta-models
- **examples**: Comprehensive examples and benchmarks
- **docs**: Complete documentation and API reference

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF package
pip install openstef

# For specific components only
pip install openstef-models  # Core models and transforms
pip install openstef-beam    # Benchmarking and evaluation
pip install openstef-core    # Shared utilities

# Install with all optional dependencies
pip install "openstef[all]"
```

### Using Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions, troubleshooting, and platform-specific notes, see the [installation documentation](https://openstef.github.io/openstef/index.html).

## Examples

Explore comprehensive examples in the [`examples/`](examples/) directory:

- **[Benchmarks](examples/benchmarks/)**: Compare forecasting models on real datasets
- **[Basic Examples](examples/examples/)**: Step-by-step tutorials for common tasks
- **Complete workflows**: From data preprocessing to model evaluation

Each example includes detailed documentation and can be run independently. See the [Examples README](examples/README.md) for a complete overview.

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

If you use OpenSTEF in your research, please cite our work:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short-Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  license = {MPL-2.0}
}
```

For academic publications, you may also reference our project website: [lfenergy.org/projects/openstef](https://lfenergy.org/projects/openstef/).

## Contact

- **Support**: See our [Support Guide](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- **GitHub Discussions**: [Community Q&A and discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issues**: [Bug reports and feature requests](https://github.com/OpenSTEF/openstef/issues)
- **LF Energy**: [Official project page](https://www.lfenergy.org/projects/openstef/)