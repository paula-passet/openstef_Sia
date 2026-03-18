# OpenSTEF

![OpenSTEF Logo](https://github.com/OpenSTEF/.github/raw/main/profile/logo-color-openstef.png)

[![Build Status](https://github.com/OpenSTEF/openstef/actions/workflows/test.yml/badge.svg)](https://github.com/OpenSTEF/openstef/actions)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/openstef.svg)](https://pypi.org/project/openstef/)

## Table of Contents

- [What is OpenSTEF](#what-is-openstef)
- [Brief Monorepo Overview](#brief-monorepo-overview)
- [How to Install](#how-to-install)
- [Examples](#examples)
- [License](#license)
- [Contributing](#contributing)
- [Citations](#citations)
- [Contact](#contact)

## What is OpenSTEF

OpenSTEF is a modular Python library for creating short-term energy forecasts using machine learning. It provides a complete pipeline from raw data to probabilistic forecasts, designed specifically for grid operators and energy companies. The library handles data validation, feature engineering, model training, and forecast generation with built-in fallback strategies for operational reliability. For more information, visit the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains the complete OpenSTEF ecosystem organized as a monorepo with multiple specialized packages:

- **openstef** - Meta-package providing the core forecasting functionality
- **openstef-core** - Shared types, utilities, and base classes
- **openstef-models** - Machine learning models, feature engineering, and transformations
- **openstef-beam** - Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta** - Ensemble models and advanced meta-learning capabilities
- **examples** - Jupyter notebooks and example scripts

## How to Install

Install OpenSTEF using pip:

```bash
# Basic installation
pip install openstef

# With all optional dependencies
pip install "openstef[all]"

# For development
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev
```

Requirements: Python 3.12+ on a 64-bit system.

For detailed installation instructions including GPU support and troubleshooting, see the [documentation](https://openstef.github.io/openstef/index.html).

## Examples

Explore hands-on examples in the [`examples/`](examples/) directory. The examples include:

- Quick start tutorials
- Feature engineering demonstrations
- Model training and hyperparameter optimization
- Backtesting and evaluation workflows
- Ensemble forecasting examples

Each example includes detailed documentation and can be run independently. See the [examples README](examples/README.md) for a complete overview.

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

To cite OpenSTEF in academic work, please use:

```bibtex
@software{openstef,
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  author = {{OpenSTEF Contributors}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

For more detailed citation information and DOI references, visit our [documentation](https://openstef.github.io/openstef/index.html).

## Contact

For support, questions, and community discussions, please visit our [support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md). You can also join our community channels or report issues through our GitHub repositories.