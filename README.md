Now I have enough information to generate the README.md following the structure plan exactly. Let me create the complete README.

![OpenSTEF](https://raw.githubusercontent.com/OpenSTEF/openstef/release/v4.0.0/docs/source/_static/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a library for creating short-term forecasts in the energy sector. It provides machine learning models and tools for forecasting energy loads on electrical grids, with support for data preprocessing, model training, backtesting, and evaluation. Visit the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/) for more information about the project and its applications in energy forecasting.

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages: `openstef-core` provides shared utilities and data types, `openstef-models` contains forecasting models and feature engineering, `openstef-beam` offers backtesting and evaluation tools, and the `openstef` meta-package combines core components for most users.

## How to Install

**For most users:**
```bash
pip install openstef
```

**System Requirements:**
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, or Linux)

**Alternative package managers:**
```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

**Individual packages:**
```bash
# Core forecasting models only
pip install openstef-models

# Backtesting and evaluation tools
pip install openstef-beam

# Complete installation with all tools
pip install "openstef[all]"
```

For detailed installation instructions, troubleshooting, and development setup, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in our documentation:

- **[Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html)** - Get up and running with OpenSTEF in minutes
- **[Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html)** - Step-by-step examples for common forecasting tasks
- **[API Reference](https://openstef.github.io/openstef/v4/api/)** - Detailed documentation for all functions and classes

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

If you use OpenSTEF in your research, please cite it using the DOI [10.5281/zenodo.15316405](https://doi.org/10.5281/zenodo.15316405):

```bibtex
@software{openstefopenstef,
  title = {OpenSTEF/openstef},
  author = {Kreuwel, Frank and van Es, Daan and van Doorn, Jan Maarten and Pleiter, Bart and Stoel, Willem Frederik and van den Bogaard, Jonas and Fortin, Maxime and de Smet, Clara and Dmitriev, Egor and Schilders, Lars and Harmsen, A. W.},
  doi = {10.5281/zenodo.15316405},
  url = {https://github.com/OpenSTEF/openstef},
}
```

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** - How to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** - Community Q&A
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** - Bug reports and feature requests
- **[LF Energy Slack](https://slack.lfenergy.org/)** - Join the #openstef channel
- **Email:** openstef@lfenergy.org