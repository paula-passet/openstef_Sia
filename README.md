<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo_color.png)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![Build Status](https://github.com/OpenSTEF/openstef/actions/workflows/ci.yml/badge.svg)](https://github.com/OpenSTEF/openstef/actions)
[![License: MPL-2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

## What is OpenSTEF

OpenSTEF is a complete Python library for creating production-ready short-term forecasts in the energy sector. OpenSTEF provides a modular architecture with specialized packages for machine learning models, backtesting frameworks, and comprehensive evaluation tools, enabling energy professionals to build, validate, and deploy forecasting solutions with confidence. Visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/) for comprehensive information about the project.

## Brief Monorepo Overview

This repository uses a modular monorepo structure with specialized packages: **openstef-core** provides foundational data structures and utilities, **openstef-models** contains machine learning models and feature engineering, **openstef-beam** offers backtesting and evaluation frameworks, and **openstef-meta** handles ensemble forecasting workflows. The main `openstef` package serves as a meta-package that brings together the core components for typical use cases.

## How to Install

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Basic Installation

```bash
# For most users
pip install openstef

# Core forecasting only
pip install openstef-models

# With all optional tools
pip install "openstef[all]"
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore hands-on examples in the [`examples/`](examples/) folder. The examples directory contains its own [README.md](examples/README.md) with comprehensive guides including:

- **Benchmarking Examples**: Compare model performance using the Liander 2024 dataset
- **Forecasting Workflows**: Configure and run complete prediction pipelines
- **Model Calibration**: Improve forecast uncertainty with isotonic calibration techniques

Each example includes detailed documentation and can be run independently to demonstrate specific OpenSTEF capabilities.

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

If you use OpenSTEF in academic work, please cite our project. A BibTeX entry and DOI information will be available soon. For now, you can reference:

```
OpenSTEF Contributors. (2025). OpenSTEF: Open Short Term Energy Forecasting. 
LF Energy Foundation. https://github.com/OpenSTEF/openstef
```

## Contact

For support and questions, please visit our [Support Page](.github/SUPPORT.md) which includes:

- **GitHub Discussions** for community Q&A
- **Issue Tracker** for bug reports and feature requests  
- **Email Contact** for direct communication
- **Community Meetings** for collaboration opportunities