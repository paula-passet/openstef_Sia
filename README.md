# OpenSTEF

<div align="center">

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

</div>

## What is OpenSTEF

OpenSTEF is a comprehensive, modular Python library for short-term energy forecasting that combines machine learning models with probabilistic predictions. Built for the energy sector, it provides backtesting, evaluation, analysis and metrics (BEAM) for systematic model comparison and deployment-ready forecasting workflows. Visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/) for more information about the project.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages:

- **openstef-core**: Core data structures, types, and utilities shared across packages
- **openstef-models**: Machine learning models, feature engineering, and forecasting workflows  
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework for model validation
- **openstef-meta**: Ensemble forecasting models and advanced meta-learning techniques
- **examples**: Comprehensive tutorials and benchmarking examples

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# Install complete OpenSTEF framework
pip install openstef

# Core forecasting models only
pip install openstef-models

# Full functionality with optional dependencies
pip install "openstef[all]"
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including GPU support and development setup, see our [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore our comprehensive example collection in the [`examples/`](examples/) folder:

- **Forecasting workflows**: End-to-end model training and prediction pipelines
- **Benchmarking studies**: Systematic comparison of forecasting models using the Liander 2024 dataset
- **Advanced techniques**: Ensemble modeling, quantile calibration, and feature engineering

The examples folder contains its own [README.md](examples/README.md) with detailed descriptions and setup instructions for each tutorial.

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

If you use OpenSTEF in your research or projects, please cite it as:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  publisher = {LF Energy Foundation}
}
```

You can also cite specific releases using DOI links available on our [GitHub releases page](https://github.com/OpenSTEF/openstef/releases).

## Contact

For support and community interaction:

- **Documentation**: [https://openstef.github.io/openstef/v4/](https://openstef.github.io/openstef/v4/)
- **GitHub Discussions**: [Community Q&A and discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Issue Tracker**: [Bug reports and feature requests](https://github.com/OpenSTEF/openstef/issues)
- **Email**: Contact us at `openstef@lfenergy.org`

For detailed support options, see our [Support Guide](https://openstef.github.io/openstef/v4/project/support.html).