Based on the knowledge base search results, I now have sufficient information to generate the README.md for the release/v4.0.0 version. I'll create a concise README following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a library for creating short-term forecasts in the energy sector. It provides machine learning models, feature engineering, backtesting, and evaluation tools designed specifically for energy forecasting applications. Learn more at the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages:

- **openstef-core** — Core data structures, datasets, and utilities
- **openstef-models** — Machine learning models and feature engineering
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef** — Meta-package providing convenient installation of core components

This architecture allows you to install only the components you need for your specific use case.

## How to Install

**Requirements:** Python 3.12+ and a 64-bit operating system.

```bash
# For most users - installs core functionality
pip install openstef

# Complete installation with all tools
pip install "openstef[all]"

# Individual packages
pip install openstef-models  # Core forecasting models only
pip install openstef-beam    # Backtesting and evaluation tools
```

For detailed installation instructions, platform-specific notes, and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [examples/](examples/) directory. Each example includes documentation and demonstrates specific OpenSTEF capabilities.

For step-by-step tutorials and guides, visit the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

If OpenSTEF contributes to a project that leads to a scientific publication, please cite the project:

```bibtex
@software{openstefopenstef,
  title = {OpenSTEF/openstef},
  author = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten and Pleiter, Bart and Stoel, Willem Frederik and van den Bogaard, Jonas and Fortin, Maxime and de Smet, Clara and Dmitriev, Egor and Schilders, Lars and Harmsen, A. W.},
  doi = {10.5281/zenodo.15316405},
  url = {https://github.com/OpenSTEF/openstef},
}
```

DOI: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15316405.svg)](https://doi.org/10.5281/zenodo.15316405)

For more citation formats, see [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html).

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** — How to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** — Community Q&A
- **[Issue Tracker](https://github.com/paula-passet/openstef_Sia/issues)** — Bug reports and feature requests
- **[LF Energy Slack](https://slack.lfenergy.org/)** — Join the #openstef channel
- **Email** — openstef@lfenergy.org