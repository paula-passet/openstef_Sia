Now I have enough information to generate the README. Let me create it following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/release/v4.0.0/docs/source/logos/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides machine learning models, feature engineering tools, and evaluation frameworks designed specifically for energy grid operators and researchers. Learn more at the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages: **openstef-core** provides shared utilities and dataset types, **openstef-models** contains ML models and feature engineering, and **openstef-beam** offers backtesting and evaluation tools. All packages are developed together with automatic dependency resolution.

## How to Install

**Requirements:** Python 3.12+ and a 64-bit operating system.

```bash
# Install the meta-package with core functionality
pip install openstef

# Install with all components
pip install "openstef[all]"

# Install individual packages
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation
```

For detailed installation instructions, troubleshooting, and platform-specific notes, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the repository:

- **[examples/](examples/)** - Code examples demonstrating OpenSTEF features
- **[Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html)** - Step-by-step tutorial to get started
- **[Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)** - In-depth guides for common use cases

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

If OpenSTEF contributes to research that leads to a publication, please cite the project:

**DOI:** [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15316405.svg)](https://doi.org/10.5281/zenodo.15316405)

**BibTeX:**

```bibtex
@software{openstefopenstef,
  title = {OpenSTEF/openstef},
  author = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten and Pleiter, Bart and Stoel, Willem Frederik and van den Bogaard, Jonas and Fortin, Maxime and de Smet, Clara and Dmitriev, Egor and Schilders, Lars and Harmsen, A. W.},
  doi = {10.5281/zenodo.15316405},
  url = {https://github.com/OpenSTEF/openstef},
}
```

For more information, see [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html).

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** - How to get help and connect with the community
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - Ask questions and share ideas
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** - Report bugs and request features
- **[LF Energy Slack](https://slack.lfenergy.org/)** - Join the #openstef channel for real-time discussion
- **Email:** openstef@lfenergy.org