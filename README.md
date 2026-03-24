<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://openstef.github.io/openstef/v4/_static/logo.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a modular library for creating short-term forecasts in the energy sector. Version 4.0 introduces a complete architectural refactor with enhanced modularity, type safety, and modern Python development practices for probabilistic energy forecasting. OpenSTEF provides backtesting, evaluation, analysis and metrics (BEAM) capabilities for comprehensive model assessment across multiple targets and time horizons.

Learn more about OpenSTEF at [openstef.github.io](https://openstef.github.io/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages:

- **openstef-core**: Core data structures, datasets, types, and utilities
- **openstef-models**: ML models, feature engineering, data processing, and workflows
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Ensemble forecasting and meta-learning models
- **openstef**: Meta-package combining core components

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

Explore practical examples in the [`examples/`](examples/) folder:

- **Quick Start**: Basic forecasting workflow
- **Benchmarking**: Compare multiple models using the Liander 2024 benchmark
- **Feature Engineering**: Custom feature transforms and pipelines
- **Advanced Workflows**: Ensemble forecasting and model calibration

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

If you use OpenSTEF in your research, please cite our work:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

For academic citations and DOI information, visit our [project page](https://www.lfenergy.org/projects/openstef/).

## Contact

- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - community Q&A and discussions
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** - bug reports and feature requests
- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** - comprehensive help resources

For more information, visit our [support page](https://openstef.github.io/openstef/v4/project/support.html).