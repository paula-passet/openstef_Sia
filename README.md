Now I'll generate the complete README.md based on the structure plan and the information gathered from the knowledge base:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

# OpenSTEF

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/release/v4.0.0/docs/source/_static/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15316405.svg)](https://doi.org/10.5281/zenodo.15316405)

## What is OpenSTEF

OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides a complete machine learning pipeline with models, feature engineering, and evaluation tools specifically designed for energy forecasting applications. OpenSTEF is developed as an open-source project under the Linux Foundation Energy initiative. Learn more at the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages: **openstef-core** (shared utilities and types), **openstef-models** (forecasting models and preprocessing), **openstef-beam** (backtesting and evaluation), and **openstef** (meta-package). This architecture allows you to install only the components you need while maintaining unified development workflows.

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

For detailed installation instructions, troubleshooting, and platform-specific notes, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore hands-on examples and tutorials in our documentation:

- **[Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html)** - Get up and running with OpenSTEF in minutes
- **[Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)** - Step-by-step examples for common use cases
- **[API Reference](https://openstef.github.io/openstef/v4/api/)** - Detailed function documentation

Additional examples are available in the [OpenSTEF offline examples repository](https://github.com/OpenSTEF/openstef-offline-example).

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

If you use OpenSTEF in your research, please cite our project:

```bibtex
@software{openstefopenstef,
  title = {OpenSTEF/openstef},
  author = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten and Pleiter, Bart and Stoel, Willem Frederik and van den Bogaard, Jonas and Fortin, Maxime and de Smet, Clara and Dmitriev, Egor and Schilders, Lars and Harmsen, A. W.},
  doi = {10.5281/zenodo.15316405},
  url = {https://github.com/OpenSTEF/openstef},
}
```

You can also reference the DOI: [10.5281/zenodo.15316405](https://doi.org/10.5281/zenodo.15316405)

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** - How to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - Community Q&A and discussions  
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** - Bug reports and feature requests
- **[LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)** - Project homepage