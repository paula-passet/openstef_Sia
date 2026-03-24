# OpenSTEF

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/openstef-logo.png" alt="OpenSTEF Logo" width="200"/>
</p>

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

## What is OpenSTEF

OpenSTEF is a modular Python library for creating short-term forecasts in the energy sector. Version 4.0 features a complete architectural refactor with enhanced modularity, probabilistic forecasting capabilities, and modern development practices. Perfect for grid operators, energy traders, and researchers working with energy demand forecasting.

Visit [openstef.github.io](https://openstef.github.io) for comprehensive documentation.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages:

- **openstef-core**: Core data structures, time series datasets, and base utilities
- **openstef-models**: Machine learning models, feature engineering, and data preprocessing
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Ensemble forecasting and meta-learning capabilities
- **examples**: Benchmarks, tutorials, and real-world use cases

## How to Install

### Requirements
- Python 3.12+ (Python 3.13 supported)
- 64-bit operating system

### Basic Installation

```bash
# For most users - includes core forecasting models
pip install openstef

# Core forecasting only
pip install openstef-models

# With benchmarking and evaluation tools
pip install openstef[beam]

# With ensemble forecasting capabilities
pip install openstef[meta]

# Everything included
pip install openstef[all]
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including GPU support and troubleshooting, see our [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore our [examples/](examples/) directory for:

- **Benchmarks**: Liander 2024 forecasting benchmark comparisons
- **Configuration examples**: Model pipeline and preset configurations  
- **Advanced tutorials**: Isotonic calibration and ensemble forecasting

Each example includes detailed documentation and can be run independently. See [examples/README.md](examples/README.md) for a complete overview.

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

If you use OpenSTEF in your research or projects, please cite:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  year = {2025},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0}
}
```

## Contact

- **GitHub Discussions**: [Community Q&A and discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issue Tracker**: [Bug reports and feature requests](https://github.com/OpenSTEF/openstef/issues)
- **Email**: openstef@lfenergy.org
- **Documentation**: [Complete support guide](https://github.com/OpenSTEF/openstef/blob/main/.github/SUPPORT.md)