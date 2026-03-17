<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo_openstef.png)

[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://badge.fury.io/py/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![Build Status](https://github.com/OpenSTEF/openstef/workflows/CI/badge.svg)](https://github.com/OpenSTEF/openstef/actions)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

# What is OpenSTEF

OpenSTEF is a modular Python library for creating short-term energy forecasts, specifically designed for the energy sector. It provides complete machine learning pipelines that transform time series data into probabilistic forecasts for the next hours to days. OpenSTEF handles everything from data validation and feature engineering to model training and forecast generation, making it suitable for energy consumption, renewable generation, and grid load forecasting.

For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

# Brief Monorepo Overview

This repository contains OpenSTEF 4.0, structured as a monorepo with specialized packages:

- `packages/openstef-core/` - Core utilities, dataset types, and base classes
- `packages/openstef-models/` - ML models, feature engineering, and data processing
- `packages/openstef-beam/` - Backtesting, Evaluation, Analysis, and Metrics
- `packages/openstef-meta/` - Meta-models and ensemble forecasting
- `examples/` - Usage examples and tutorials
- `docs/` - Documentation source files

# How to Install

## Requirements
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, Linux)

## Basic Installation

```bash
# Install the full OpenSTEF package
pip install openstef

# Or install specific components
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Evaluation and benchmarking
```

## Optional Dependencies

```bash
# Install with all optional features
pip install "openstef[all]"

# Install with specific optional features
pip install "openstef[beam]"    # Backtesting and evaluation
pip install "openstef[meta]"    # Ensemble models
```

## Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

# Examples

See the [`examples/`](examples/) folder for comprehensive usage examples and tutorials. The examples cover:

- Basic forecasting workflows
- Feature engineering techniques
- Model training and evaluation
- Ensemble forecasting
- Benchmarking and analysis

Each example includes detailed documentation and can be run independently.

# License

This project is licensed under the Mozilla Public License, version 2.0. See [LICENSE](LICENSE) for details.

# Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://github.com/OpenSTEF/.github/blob/main/CONTRIBUTING.md) for details on how to get started.

For development setup:

```bash
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev
uv run poe all  # Run all tests and checks
```

# Citations

To cite OpenSTEF in academic work, please use:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {OpenSTEF Contributors},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

# Contact

- **Documentation**: [https://openstef.github.io/openstef/](https://openstef.github.io/openstef/)
- **Issues**: [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Support**: See our [Support Guide](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)

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
