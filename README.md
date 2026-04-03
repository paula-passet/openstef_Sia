Now I'll generate the complete README.md following the structure plan exactly:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/release/v4.0.0/docs/source/logos/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a library for creating short-term forecasts in the energy sector. It provides modular tools for machine learning-based forecasting, feature engineering, backtesting, and model evaluation. OpenSTEF is designed to support grid operators, energy traders, and researchers in making data-driven decisions for energy management and grid stability.

Learn more at the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages that can be installed independently or together. The repository contains core utilities (`openstef-core`), machine learning models (`openstef-models`), and backtesting/evaluation tools (`openstef-beam`), along with comprehensive documentation and examples.

## Installation

**Requirements:**
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, or Linux)

**Basic installation:**

```bash
pip install openstef
```

**For all features:**

```bash
pip install "openstef[all]"
```

**Individual packages:**

```bash
# Core utilities and datasets
pip install openstef-core

# Machine learning models and feature engineering
pip install openstef-models

# Backtesting and evaluation tools
pip install openstef-beam
```

For detailed installation instructions, platform-specific notes, and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) folder. The examples demonstrate common forecasting workflows, feature engineering techniques, and model evaluation approaches.

For step-by-step guidance, visit the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

If OpenSTEF contributes to a project that leads to a scientific publication, please cite us using the DOI [10.5281/zenodo.15316405](https://doi.org/10.5281/zenodo.15316405).

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

- **Support:** Visit our [Support page](https://openstef.github.io/openstef/v4/project/support.html) for help and resources
- **Discussions:** Join [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions) for Q&A and community conversations
- **Issues:** Report bugs and request features on our [Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- **Slack:** Connect with the community on the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)
- **Email:** Contact us at [openstef@lfenergy.org](mailto:openstef@lfenergy.org)