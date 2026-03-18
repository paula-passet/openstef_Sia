<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<p align="center">
  <img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/logo_color.png" alt="OpenSTEF Logo" width="400">
</p>

# OpenSTEF

[![Build Status](https://github.com/OpenSTEF/openstef/workflows/Test/badge.svg)](https://github.com/OpenSTEF/openstef/actions)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Release](https://img.shields.io/github/v/release/OpenSTEF/openstef)](https://github.com/OpenSTEF/openstef/releases/tag/release/v4.0.0)
[![PyPI](https://img.shields.io/pypi/v/openstef)](https://pypi.org/project/openstef/)
[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a complete framework for developing, benchmarking, and deploying probabilistic forecasting models for short-term energy forecasting. It provides state-of-the-art machine learning models, automated feature engineering, and comprehensive evaluation tools to help grid operators and energy companies forecast energy consumption and renewable generation. For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 is structured as a monorepo containing multiple specialized packages. The main `openstef` package is a meta-package that brings together core components (`openstef-core`), forecasting models (`openstef-models`), and benchmarking tools (`openstef-beam`). Additional packages provide specialized functionality for different use cases.

## How to Install

### Requirements
- Python 3.12 or 3.13
- 64-bit operating system (Windows, macOS, Linux)

### Basic Installation

```bash
# Install the main OpenSTEF package
pip install openstef

# Install with all optional components
pip install "openstef[all]"

# Install specific components only
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Benchmarking and evaluation
pip install openstef-core    # Core utilities and types
```

### Modern Package Managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) folder. The examples directory contains its own README with detailed overviews of:

- Quick start forecasting examples
- Model training and evaluation workflows
- Benchmarking different forecasting approaches
- Advanced feature engineering techniques
- Custom model integration

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

To cite OpenSTEF in academic work, please use the following BibTeX entry:

```bibtex
@software{openstef2024,
  title = {OpenSTEF: Open Short-term Energy Forecasting},
  author = {{OpenSTEF Contributors}},
  url = {https://github.com/OpenSTEF/openstef},
  version = {4.0.0},
  year = {2024},
  publisher = {LF Energy Foundation},
  license = {MPL-2.0}
}
```

For DOI-based citations, visit our [Zenodo record](https://doi.org/10.5281/zenodo.5606467).

## Contact

For support, questions, or community discussions, please visit our [support page](https://github.com/OpenSTEF/.github/blob/main/SUPPORT.md) which includes links to:

- GitHub Discussions for Q&A
- Community chat channels
- Issue reporting guidelines
- Professional support options