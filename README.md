<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<img src="https://raw.githubusercontent.com/OpenSTEF/.github/main/profile/logo.png" alt="OpenSTEF Logo" width="200"/>

<!-- Badges -->
[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://badge.fury.io/py/openstef)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://github.com/OpenSTEF/openstef/workflows/Build/badge.svg)](https://github.com/OpenSTEF/openstef/actions)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a complete Python library for making probabilistic forecasts in the energy sector. It provides automated machine learning pipelines that combine weather data, load measurements, and market information to generate accurate short-term energy forecasts. OpenSTEF handles everything from data validation and feature engineering to model training and uncertainty quantification.

Visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/) for more information about the project.

## Brief Monorepo Overview

This repository contains multiple specialized packages organized as a monorepo:

- **openstef** - Meta-package providing core functionality and common interfaces
- **openstef-core** - Foundational utilities, types, and dataset abstractions
- **openstef-models** - Machine learning models and feature engineering transforms
- **openstef-meta** - Meta-learning and ensemble modeling capabilities
- **openstef-beam** - Backtesting, Evaluation, Analysis, and Metrics framework
- **examples** - Example notebooks and scripts demonstrating usage

## How to Install

### Requirements
- Python 3.12 or 3.13
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF package
pip install openstef

# Install with all optional dependencies
pip install "openstef[all]"

# Install specific components only
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Benchmarking framework
```

### Using Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including troubleshooting, see the [installation guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore the [`examples/`](examples/) directory for comprehensive tutorials and use cases:

- **Forecasting Workflows** - Complete end-to-end forecasting pipelines
- **Benchmarking** - Model comparison and evaluation on public datasets
- **Feature Engineering** - Custom transforms and preprocessing
- **Model Configuration** - Setting up different forecasting models

Each example includes detailed explanations and can be run independently. See the [examples README](examples/README.md) for a complete overview.

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

If you use OpenSTEF in your research or publications, please cite the project. Citation information and academic references are available at [CITATION.cff](CITATION.cff).

For BibTeX format:
```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short-Term Energy Forecasting},
  author = {Contributors to the OpenSTEF project},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

## Contact

- **Documentation**: https://openstef.github.io/openstef/
- **Support**: See our [Support Guide](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Community**: Join discussions on [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)