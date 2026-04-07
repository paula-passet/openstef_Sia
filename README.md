Now I'll generate the README.md based on the structure plan and the information gathered:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a library for creating short-term forecasts in the energy sector. It provides modular tools for machine learning-based forecasting, feature engineering, model evaluation, and backtesting. OpenSTEF is designed to support operational forecasting workflows with production-ready components and comprehensive type safety.

Learn more at the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages:

- **openstef-core** — Core utilities, dataset types, and shared base models
- **openstef-models** — Machine learning models, feature engineering, and data processing
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics framework
- **openstef** — Meta-package providing convenient access to core components

Each package can be installed independently or together based on your needs.

## How to Install

**Requirements:**
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, or Linux)

**Basic installation:**

```bash
# Install the meta-package with core functionality
pip install openstef

# Install with all components
pip install "openstef[all]"

# Install individual packages
pip install openstef-models
pip install openstef-beam
```

**Development installation:**

```bash
# Clone and set up for development
git clone https://github.com/OpenSTEF/openstef.git
cd openstef
uv sync --all-extras --dev

# Run tests
uv run pytest
```

For detailed installation instructions, troubleshooting, and platform-specific notes, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) directory. The examples folder contains its own README with an overview of available examples and step-by-step tutorials.

For a quick introduction, see the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html) in the documentation.

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

If OpenSTEF contributes to a project that leads to a scientific publication, please acknowledge this by citing the project.

**BibTeX:**

```bibtex
@software{openstefopenstef,
  title = {OpenSTEF/openstef},
  author = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten and Pleiter, Bart and Stoel, Willem Frederik and van den Bogaard, Jonas and Fortin, Maxime and de Smet, Clara and Dmitriev, Egor and Schilders, Lars and Harmsen, A. W.},
  doi = {10.5281/zenodo.15316405},
  url = {https://github.com/OpenSTEF/openstef},
}
```

**DOI:** [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15316405.svg)](https://doi.org/10.5281/zenodo.15316405)

For more information, see [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html).

## Contact

**Need help or want to connect?**

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** — How to get help and connect with the community
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** — Community Q&A and discussions
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** — Report bugs and request features
- **[LF Energy Slack](https://slack.lfenergy.org/)** — Join the #openstef channel for real-time discussions
- **Email** — Contact us at openstef@lfenergy.org

Visit the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/) for more information about the project.