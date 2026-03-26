<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/release/v4.0.0/docs/source/_static/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a modular library for creating short-term forecasts in the energy sector. It provides all components for the machine learning pipeline required to make accurate energy forecasts. The library is designed to be unopinionated and flexible, supporting various data availability constraints and use cases from research to enterprise integration.

For more information, visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF release/v4.0.0 uses a modular monorepo structure with specialized packages: `openstef-core` provides shared utilities and data types, `openstef-models` contains forecasting models and feature engineering, and `openstef-beam` offers backtesting, evaluation, analysis, and metrics tools. The meta-package `openstef` combines core functionality for most users.

## How to Install

### System Requirements
- Python 3.12 or higher (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, or Linux)

### Quick Installation

```bash
# For most users
pip install openstef

# Complete installation with all tools
pip install "openstef[all]"

# Individual packages
pip install openstef-models    # Core forecasting models
pip install openstef-beam      # Backtesting and evaluation
pip install openstef-core      # Core utilities only
```

For detailed installation instructions, troubleshooting, and platform-specific notes, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in our documentation:

- [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) - Get up and running fast
- [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html) - Step-by-step examples
- [API Reference](https://openstef.github.io/openstef/v4/api/) - Detailed function documentation

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

If you are using OpenSTEF in your research work, please cite our library:

```bibtex
@software{openstefopenstef,
  title = {OpenSTEF/openstef},
  author = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten and Pleiter, Bart and Stoel, Willem Frederik and van den Bogaard, Jonas and Fortin, Maxime and de Smet, Clara and Dmitriev, Egor and Schilders, Lars and Harmsen, A. W.},
  doi = {10.5281/zenodo.15316405},
  url = {https://github.com/OpenSTEF/openstef},
}
```

You can also reference our DOI: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15316405.svg)](https://doi.org/10.5281/zenodo.15316405)

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** - How to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - Community Q&A
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** - Bug reports and feature requests
- **[LF Energy Slack](https://slack.lfenergy.org/)** - Join the #openstef channel
- **Email**: openstef@lfenergy.org