Now I'll generate the complete README.md based on the structure plan and the information gathered:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg)

# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides modular tools for machine learning-based forecasting, feature engineering, model evaluation, and backtesting. Learn more at the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo architecture with specialized packages: **openstef-core** provides shared utilities and data structures, **openstef-models** contains machine learning models and feature engineering, **openstef-beam** offers backtesting and evaluation tools, and the **openstef** meta-package bundles core components for easy installation.

## How to Install

**Requirements:**
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, or Linux)

**Basic Installation:**

```bash
# Install the meta-package with core functionality
pip install openstef

# Install with all optional components
pip install "openstef[all]"

# Install individual packages
pip install openstef-models  # Core forecasting models
pip install openstef-beam    # Backtesting and evaluation
pip install openstef-core    # Core utilities only
```

**Using modern package managers:**

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions, platform-specific notes, and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [examples](examples/) folder. The examples demonstrate common forecasting workflows, feature engineering techniques, and model evaluation strategies.

For step-by-step guidance, visit the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html) in the documentation.

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

If OpenSTEF contributes to a project that leads to a scientific publication, please cite the project using the DOI or BibTeX entry below.

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

**Need help or want to connect?**

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** – how to get help and report issues
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** – community Q&A and discussions
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** – bug reports and feature requests
- **[LF Energy Slack](https://slack.lfenergy.org/)** – join the #openstef channel for real-time chat
- **Email:** openstef@lfenergy.org