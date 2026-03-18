# OpenSTEF

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/openstef_logo.png)

[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://badge.fury.io/py/openstef)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

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

OpenSTEF is a complete, modular Python library for short-term energy forecasting. It provides probabilistic forecasts for energy consumption, renewable generation, and grid load using automated machine learning pipelines. The library handles the entire forecasting workflow from data validation and feature engineering to model training and forecast generation. For more information, visit the [OpenSTEF project website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains multiple specialized packages organized as a monorepo:

- **`openstef`** - Meta-package combining all components
- **`openstef-core`** - Core utilities, dataset types, and shared functionality  
- **`openstef-models`** - ML models, feature engineering, and forecasting workflows
- **`openstef-beam`** - Backtesting, Evaluation, Analysis, and Metrics framework
- **`openstef-meta`** - Meta-models and ensemble forecasting capabilities
- **`examples/`** - Example notebooks and usage demonstrations
- **`docs/`** - Documentation source files

## How to Install

### Basic Installation

```bash
# Install the complete OpenSTEF package
pip install openstef

# Core forecasting models only
pip install openstef-models

# With all optional dependencies
pip install "openstef[all]"
```

### Requirements

- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, Linux)

### Development Installation

```bash
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --dev
```

For detailed installation instructions including GPU support and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/index.html).

## Examples

Explore the [`examples/`](examples/) folder for comprehensive examples including:

- Quick start forecasting tutorials
- Benchmark studies on the Liander 2024 dataset  
- Model configuration and hyperparameter optimization
- Feature engineering and preprocessing examples
- Ensemble forecasting workflows

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

If you use OpenSTEF in your research or commercial projects, please cite it as:

```bibtex
@software{openstef,
  author = {Alliander N.V and Contributors},
  title = {OpenSTEF: Open Short Term Energy Forecasting},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2025}
}
```

## Contact

- **Documentation:** [https://openstef.github.io/openstef/](https://openstef.github.io/openstef/)
- **Support:** See our [Support Guide](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- **Issues:** [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Discussions:** [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)
- **Community:** [Teams Channel](https://teams.microsoft.com/l/team/19%3ac08a513650524fc988afb296cd0358cc%40thread.tacv2/conversations?groupId=bfcb763a-3a97-4938-81d7-b14512aa537d&tenantId=697f104b-d7cb-48c8-ac9f-bd87105bafdc)