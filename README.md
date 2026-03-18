# OpenSTEF

![OpenSTEF Logo](https://github.com/OpenSTEF/.github/raw/main/profile/openstef-horizontal-color.svg)

[![PyPI version](https://badge.fury.io/py/openstef.svg)](https://pypi.org/project/openstef/)
[![Build Status](https://github.com/paula-passet/openstef_Sia/actions/workflows/ci.yml/badge.svg)](https://github.com/paula-passet/openstef_Sia/actions)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

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

OpenSTEF is a modular Python library for creating short-term energy forecasts. It provides machine learning models, backtesting tools, and evaluation metrics specifically designed for energy sector applications. Version 4.0 introduces a complete architectural refactor with enhanced modularity, type safety, and modern Python development practices. Learn more at the [OpenSTEF website](https://lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository contains multiple specialized packages:

- **openstef-core**: Core data structures, datasets, and utilities
- **openstef-models**: Machine learning models and feature engineering transforms
- **openstef-beam**: Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef-meta**: Meta-models for ensemble forecasting
- **examples/**: Sample workflows and benchmark implementations
- **docs/**: Complete documentation and API reference

## How to Install

Install OpenSTEF using pip:

```bash
# Basic installation with core functionality
pip install openstef

# With all optional dependencies
pip install "openstef[all]"

# Individual packages
pip install openstef-models
pip install openstef-beam
```

**Requirements**: Python 3.12+ and a 64-bit operating system.

For development setup:

```bash
git clone https://github.com/paula-passet/openstef_Sia.git
cd openstef_Sia
uv sync --dev
```

## Examples

Explore practical examples in the [`examples/`](examples/) folder, including:

- Basic forecasting workflows
- Benchmark implementations (Liander 2024 dataset)
- Model comparison studies
- Feature engineering examples

The examples folder contains its own [README.md](examples/README.md) with detailed descriptions of available examples.

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

If you use OpenSTEF in your research, please cite our work. Citation information and BibTeX entries are available on our [project website](https://lfenergy.org/projects/openstef/).

## Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/OpenSTEF/openstef/issues)
- **Support**: See our [support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md)
- **LF Energy**: [OpenSTEF project homepage](https://lfenergy.org/projects/openstef/)