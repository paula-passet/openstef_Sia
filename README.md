<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

[![Build Status](https://github.com/paula-passet/openstef_Sia/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/paula-passet/openstef_Sia/actions)
[![PyPI](https://img.shields.io/pypi/v/openstef)](https://pypi.org/project/openstef/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)

## What is OpenSTEF

OpenSTEF is a comprehensive machine learning framework for short-term energy forecasting that provides probabilistic forecasts for the electricity grid. The library combines automated feature engineering, model training, and uncertainty quantification to deliver reliable energy predictions from 15 minutes to several days ahead. For more information about the project, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo architecture with specialized packages:

- **openstef-core**: Core utilities, dataset types, and shared components
- **openstef-models**: ML models, forecasting algorithms, and feature engineering
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework  
- **openstef-meta**: Meta-learning and ensemble forecasting models
- **docs**: Documentation and examples

Each package can be installed independently based on your needs.

## How to Install

### Requirements
- Python 3.12 or 3.13
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the complete OpenSTEF suite
pip install openstef

# Install with all optional dependencies
pip install "openstef[all]"

# Install specific components only
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation
pip install openstef-meta    # Ensemble models
```

### Using Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using poetry
poetry add openstef
```

For detailed installation instructions including GPU support and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/index.html).

## Examples

Explore hands-on examples in the [`examples/`](examples/) directory:

- **Basic Forecasting**: Get started with simple energy forecasting workflows
- **Benchmarking**: Compare model performance using the Liander 2024 benchmark
- **Advanced Models**: Ensemble forecasting and uncertainty quantification
- **Custom Pipelines**: Build your own forecasting workflows

Each example includes a dedicated README with setup instructions and explanations.

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
  author = {{OpenSTEF Contributors}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025},
  publisher = {LF Energy Foundation}
}
```

## Contact

For questions, support, and discussions:

- [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions) - Community Q&A
- [Issue Tracker](https://github.com/OpenSTEF/openstef/issues) - Bug reports and feature requests  
- [Support Documentation](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) - Getting help
- [Teams Channel](https://teams.microsoft.com/l/team/19%3ac08a513650524fc988afb296cd0358cc%40thread.tacv2/conversations) - Join the community discussion