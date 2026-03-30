Now I'll generate the complete README.md following the structure plan exactly:

![OpenSTEF Logo](https://openstef.github.io/openstef/_static/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15316405.svg)](https://doi.org/10.5281/zenodo.15316405)

## What is OpenSTEF

OpenSTEF is a modular library for creating short-term forecasts in the energy sector. It provides machine learning models, feature engineering tools, and evaluation frameworks specifically designed for energy forecasting applications. The library supports various forecasting scenarios including load forecasting, renewable energy prediction, and grid optimization. Learn more at the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

This repository uses a modular monorepo structure with specialized packages: **openstef-core** provides shared utilities and data types, **openstef-models** contains forecasting models and feature engineering, **openstef-beam** offers backtesting and evaluation tools, and the **openstef** meta-package combines core functionality for most users.

## How to Install

```bash
# For most users
pip install openstef

# Core forecasting only
pip install openstef-models

# With all optional tools
pip install "openstef[all]"
```

**Requirements:** Python 3.12+ and 64-bit operating system. See the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html) for detailed instructions including conda, uv, and development setup.

## Examples

Explore hands-on examples and tutorials in our [documentation](https://openstef.github.io/openstef/v4/user_guide/tutorials.html). Start with the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) for step-by-step instructions on creating your first forecasts.

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

If you use OpenSTEF in your research, please cite us using DOI [10.5281/zenodo.15316405](https://doi.org/10.5281/zenodo.15316405). For BibTeX format and detailed citation guidelines, see [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html).

## Contact

For support and questions, visit our [Support page](https://openstef.github.io/openstef/v4/project/support.html). Connect with the community through [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions), the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel), or email us at openstef@lfenergy.org.