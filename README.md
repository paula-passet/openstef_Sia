# OpenSTEF

![OpenSTEF Logo](https://www.lfenergy.org/wp-content/uploads/sites/2/2020/06/openstef.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://badge.fury.io/py/openstef)
[![License](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a complete software stack for short-term forecasting of energy consumption, renewable generation, or net load on the electricity grid. It provides automated machine learning pipelines that deliver probabilistic forecasts for the next hours to days, specifically designed for grid operators facing renewable energy integration challenges. Visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/) for more information.

## Brief Monorepo Overview

This repository contains a modular Python package ecosystem organized as a workspace monorepo. The main packages include `openstef-core` (shared utilities), `openstef-models` (forecasting models and feature engineering), `openstef-beam` (backtesting and evaluation), and `openstef-meta` (ensemble forecasting), along with comprehensive documentation and examples.

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

# Install individual components
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation tools
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/OpenSTEF/openstef.git
cd openstef

# Install with uv (recommended)
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

## Examples

Explore practical examples in the [`examples/`](examples/) folder, which contains:

- Basic forecasting workflows
- Benchmarking comparisons
- Feature engineering examples
- Model configuration tutorials

Each example includes detailed documentation to help you get started with OpenSTEF's capabilities.

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

When using OpenSTEF in academic work or publications, please cite the project. For the most up-to-date citation information and BibTeX entries, visit our [project website](https://www.lfenergy.org/projects/openstef/).

## Contact

For support and questions:

- [Support Guidelines](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- [Community Discussions](https://github.com/OpenSTEF/openstef/discussions)
- [Microsoft Teams Channel](https://teams.microsoft.com/l/team/19%3ac08a513650524fc988afb296cd0358cc%40thread.tacv2/conversations?groupId=bfcb763a-3a97-4938-81d7-b14512aa537d&tenantId=697f104b-d7cb-48c8-ac9f-bd87105bafdc)