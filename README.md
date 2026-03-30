<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

![OpenSTEF Logo](_static/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides a complete machine learning pipeline for energy load forecasting, including data preprocessing, feature engineering, model training, and evaluation. OpenSTEF is designed to handle the unique challenges of energy forecasting such as data availability constraints and the need for high-performance predictions. For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 is structured as a modular monorepo with specialized packages: **openstef-core** provides shared data types and utilities, **openstef-models** contains forecasting models and feature engineering, **openstef-beam** offers backtesting and evaluation tools, and the **openstef** meta-package provides convenient access to core functionality.

## How to Install

### Requirements
- Python 3.12 or higher (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, Linux)

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

For detailed installation instructions including troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore the [`examples/`](examples/) folder for hands-on tutorials and use cases. The examples folder contains its own README.md with an overview of available examples and step-by-step guides to get you started with OpenSTEF.

For a quick start, check out our [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

You can cite OpenSTEF using the DOI [10.5281/zenodo.15316405](https://doi.org/10.5281/zenodo.15316405) or reference the GitHub repository.

### BibTeX Format

```bibtex
@software{openstefopenstef,
  title = {OpenSTEF/openstef},
  author = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten and Pleiter, Bart and Stoel, Willem Frederik and van den Bogaard, Jonas and Fortin, Maxime and de Smet, Clara and Dmitriev, Egor and Schilders, Lars and Harmsen, A. W.},
  doi = {10.5281/zenodo.15316405},
  url = {https://github.com/OpenSTEF/openstef},
}
```

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** - how to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - community Q&A and discussions
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** - bug reports and feature requests
- **Email**: [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **[LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)** - project homepage