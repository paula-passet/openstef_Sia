<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/openstef_logo.png)

[![Build Status](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml/badge.svg)](https://github.com/paula-passet/openstef_Sia/actions)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-blue.svg)](https://opensource.org/licenses/MPL-2.0)
[![Version](https://img.shields.io/github/v/release/paula-passet/openstef_Sia?label=version)](https://github.com/paula-passet/openstef_Sia/releases/tag/release/v4.0.0)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a comprehensive Python framework for short-term energy forecasting that combines machine learning, probabilistic prediction, and energy domain expertise. It provides automated pipelines for training models, generating forecasts, and evaluating performance across energy grid applications. OpenSTEF supports both deterministic and probabilistic forecasting with built-in uncertainty quantification for reliable decision-making in energy operations.

For more information, visit the [OpenSTEF project website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository is organized as a monorepo containing multiple specialized packages:

- **`openstef`** - Meta-package providing the complete OpenSTEF experience
- **`packages/openstef-core`** - Core utilities, dataset types, and shared functionality
- **`packages/openstef-models`** - Machine learning models and feature engineering
- **`packages/openstef-beam`** - Backtesting, Evaluation, Analysis, and Metrics framework
- **`packages/openstef-meta`** - Meta-learning and ensemble forecasting models
- **`examples/`** - Example workflows and tutorials
- **`docs/`** - Comprehensive documentation

## How to Install

### Basic Installation

```bash
# Install the complete OpenSTEF suite
pip install openstef

# Install with all optional components
pip install openstef[all]
```

### Component Installation

```bash
# Install only core forecasting models
pip install openstef-models

# Install backtesting and evaluation tools
pip install openstef-beam

# Install meta-learning capabilities
pip install openstef-meta
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia

# Install with uv (recommended)
uv sync --dev

# Or with pip
pip install -e ".[all]"
```

**Requirements**: Python 3.12+ on 64-bit systems (Windows, macOS, Linux)

## Examples

Explore comprehensive examples and tutorials in the [`examples/`](examples/) folder. The examples directory contains its own README with an overview of available workflows including:

- Basic forecasting workflows
- Backtesting and model comparison
- Ensemble forecasting
- Feature engineering examples
- Real-world case studies

Start with the [Quick Start Guide](examples/README.md) to begin forecasting with your own data.

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

If you use OpenSTEF in your research or applications, please cite the project. Citation information and BibTeX entries are available at our [documentation site](https://openstef.github.io/openstef/index.html).

For academic publications, you can reference the project as:
```
OpenSTEF Contributors. OpenSTEF: Open Short Term Energy Forecasting. 
LF Energy Foundation. https://github.com/OpenSTEF/openstef
```

## Contact

For questions, support, and community discussion:

- [Support and Contact Information](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions) for community Q&A
- [Issue Tracker](https://github.com/OpenSTEF/openstef/issues) for bug reports and feature requests