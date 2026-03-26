# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

OpenSTEF is a modular library for creating short-term forecasts in the energy sector. Version 4.0 introduces a complete architectural refactor with enhanced modularity, type safety, and modern Python development practices built for Backtesting, Evaluation, Analysis, and Metrics (BEAM) framework.

Learn more at [lfenergy.org/projects/openstef](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF uses a modular monorepo structure with specialized packages for different forecasting needs:

- **openstef-core**: Core data structures, datasets, and shared utilities
- **openstef-models**: ML models, feature engineering, and data processing
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Ensemble forecasting and model combination utilities

Each package can be installed independently or together through the main `openstef` package.

## How to Install

### Requirements
- Python 3.12+ (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# For most users - includes core and models
pip install openstef

# Core forecasting only
pip install openstef-models

# Individual packages
pip install openstef-beam    # Benchmarking and evaluation
pip install openstef-core    # Core utilities
pip install openstef-meta    # Ensemble models

# All optional tools
pip install "openstef[all]"
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore practical examples in the [`examples/`](examples/) directory:

- **Benchmarks**: [`examples/benchmarks/`](examples/benchmarks/) - Compare different forecasting approaches on standard datasets
- **Basic Usage**: [`examples/examples/`](examples/examples/) - Get started with model configuration and forecasting workflows

Each example includes detailed documentation and can be run independently to demonstrate specific OpenSTEF capabilities.

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

When using OpenSTEF in academic work, please cite:

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

- **GitHub Discussions**: [Community Q&A and discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issue Tracker**: [Bug reports and feature requests](https://github.com/OpenSTEF/openstef/issues)  
- **Support**: See our [Support Guide](.github/SUPPORT.md) for detailed help options
- **Email**: Contact us at `openstef@lfenergy.org`