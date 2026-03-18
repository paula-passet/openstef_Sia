<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

<!-- Badges -->
[![Build Status](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml/badge.svg)](https://github.com/paula-passet/openstef_Sia/actions)
[![License](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Release](https://img.shields.io/github/v/release/paula-passet/openstef_Sia?label=version)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

**OpenSTEF** is a modular Python library for creating short-term forecasts in the energy sector. It provides a complete framework for backtesting, evaluation, analysis, and metrics (BEAM) for energy forecasting models, with support for probabilistic forecasting and comprehensive model performance assessment.

For more information about the OpenSTEF project, visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Monorepo Structure

This repository contains the complete OpenSTEF v4.0 codebase organized as a monorepo with specialized packages:

- **`openstef-core`**: Core data structures, datasets, and utilities
- **`openstef-models`**: Machine learning models and feature engineering
- **`openstef-beam`**: Backtesting, Evaluation, Analysis, and Metrics framework
- **`openstef-meta`**: Meta-learning and ensemble forecasting models
- **`examples/`**: Example scripts and tutorials
- **`docs/`**: Complete documentation source

## Installation

Install OpenSTEF using pip:

```bash
# Basic installation with core components
pip install openstef

# Full installation with all optional dependencies
pip install "openstef[all]"

# Development installation
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia
uv sync --dev
```

**Requirements**: Python 3.12+ on 64-bit systems (Windows, macOS, Linux).

## Examples

Explore practical examples in the [`examples/`](examples/) folder to get started with OpenSTEF:

- **Forecasting workflows**: Complete end-to-end forecasting examples
- **Benchmarking**: Model comparison and evaluation studies  
- **Feature engineering**: Time series preprocessing and feature creation
- **Ensemble methods**: Multi-model forecasting approaches

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

If you use OpenSTEF in your research, please cite our work. For BibTeX entries and citation guidelines, see our [documentation](https://openstef.github.io/openstef/index.html).

## Contact

For support and questions:

- **Issues**: [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Email**: openstef@lfenergy.org
- **Community**: Join our discussions on [GitHub](https://github.com/OpenSTEF/openstef/discussions)

For detailed support information, visit our [support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md).