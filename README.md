# OpenSTEF

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/logo-transparent-color.png)

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://badge.fury.io/py/openstef)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Build Status](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml/badge.svg?branch=release/v4.0.0)](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml)

## What is OpenSTEF

OpenSTEF is a complete, modular Python package for short-term energy forecasting using machine learning. It provides probabilistic forecasts for energy loads on electricity grids, supporting renewable energy integration and grid optimization. For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains the complete OpenSTEF 4.0 ecosystem organized as a monorepo with specialized packages:

- **openstef-models**: Core forecasting models, feature engineering, and data processing
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework  
- **openstef-core**: Shared utilities, dataset types, and base classes
- **openstef-meta**: Meta-models and ensemble forecasting capabilities
- **examples**: Example notebooks and tutorials
- **docs**: Complete documentation

## How to Install

### Requirements
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF package
pip install openstef

# Install with all optional dependencies
pip install "openstef[all]"

# Install individual components as needed
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation
```

### Using Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions including GPU support and development setup, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [examples/](examples/) folder. The examples include:

- Getting started with forecasting workflows
- Benchmarking different models
- Configuring custom pipelines
- Feature engineering examples

Each example includes its own README with setup instructions and explanations.

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

If you use OpenSTEF in your research or applications, please cite our work:

**BibTeX:**
```bibtex
@software{openstef2024,
  title = {OpenSTEF: Open Short-Term Energy Forecasting},
  author = {{Contributors to the OpenSTEF project}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2024},
  publisher = {LF Energy Foundation}
}
```

**DOI:** [10.5281/zenodo.5572090](https://doi.org/10.5281/zenodo.5572090)

## Contact

For support, questions, or collaboration opportunities, please visit our [Support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) or join our community discussions on [GitHub](https://github.com/OpenSTEF/openstef/discussions).