Now I have enough information to generate the README.md. Let me create it following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term forecasts in the energy sector. It provides a complete machine learning framework with data preprocessing, feature engineering, model training, probabilistic forecasting, and evaluation—designed to help utilities manage grid congestion and navigate the energy transition.

Learn more at the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages that can be installed independently or together. The architecture separates core functionality (`openstef-core`), forecasting models (`openstef-models`), and evaluation tools (`openstef-beam`) to provide flexibility for different use cases.

## Installation

### Requirements
- **Python 3.12+** (Python 3.13 supported)
- **64-bit operating system** (Windows, macOS, Linux)

### Install OpenSTEF

```bash
# For most users - installs core components
pip install openstef

# Core forecasting only
pip install openstef-models

# With evaluation and backtesting tools
pip install openstef openstef-beam
```

### Using modern package managers

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef

# Using pixi
pixi add openstef
```

For detailed installation instructions, troubleshooting, and development setup, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) folder. The examples demonstrate common forecasting workflows, feature engineering, model training, and evaluation.

For step-by-step guidance, start with the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and browse the [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

If OpenSTEF contributes to a project that leads to a scientific publication, please acknowledge it by citing the project.

**Cite using DOI:** [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5720100.svg)](https://doi.org/10.5281/zenodo.5720100)

**BibTeX format:**

```bibtex
@software{openstef,
  author = {{Contributors to the OpenSTEF project}},
  title = {OpenSTEF},
  url = {https://github.com/OpenSTEF/openstef},
  doi = {10.5281/zenodo.5720100}
}
```

For more details, see the [Citation Guide](https://openstef.github.io/openstef/v4/project/citing.html) or download the [CITATION.cff](CITATION.cff) file.

## Contact

**Need help or want to connect?**

- **Documentation:** [openstef.github.io/openstef](https://openstef.github.io/openstef/v4/)
- **Support Guide:** [How to get help](https://openstef.github.io/openstef/v4/project/support.html)
- **Slack:** Join the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)
- **GitHub Issues:** [Report bugs or request features](https://github.com/OpenSTEF/openstef/issues)
- **Email:** openstef@lfenergy.org
- **Community Meetings:** [Four-weekly co-coding sessions](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- **Project Homepage:** [LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)