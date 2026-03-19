# OpenSTEF

[![License](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/paula-passet/openstef_Sia?label=release)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)

## What is OpenSTEF

OpenSTEF is a modular Python library for creating short-term forecasts in the energy sector. It provides machine learning models, feature engineering tools, and evaluation frameworks specifically designed for energy load forecasting and grid management. Version 4.0 introduces a complete architectural refactor with enhanced modularity, type safety, and modern Python development practices.

Learn more at the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 is organized as a monorepo with specialized packages:

- **openstef-core**: Core data structures, datasets, and shared utilities
- **openstef-models**: ML models, forecasters, and feature engineering transforms  
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Meta-learning models including ensemble forecasting
- **examples**: Tutorial notebooks and benchmark datasets

## How to Install

### Requirements
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, Linux)

### Installation

```bash
# Install the complete OpenSTEF package
pip install openstef

# Install individual components
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Evaluation and benchmarking
pip install openstef-core    # Core utilities only

# Install all optional dependencies
pip install "openstef[all]"
```

### Development Installation

```bash
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia
uv sync --dev
uv run poe all  # Run tests and quality checks
```

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) folder:

- **Quick Start**: Basic forecasting workflow
- **Benchmarks**: Compare models on standardized datasets
- **Feature Engineering**: Advanced data preprocessing techniques
- **Ensemble Methods**: Combine multiple forecasting models

See the [Examples README](examples/README.md) for a complete overview of available examples and tutorials.

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

If you use OpenSTEF in your research, please cite our project. Citation information and BibTeX entries are available on our [project website](https://lfenergy.org/projects/openstef/).

## Contact

- **Support & Questions**: Visit our [support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- **Issues**: [GitHub Issues](https://github.com/paula-passet/openstef_Sia/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Email**: openstef@lfenergy.org