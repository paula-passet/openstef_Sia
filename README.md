Now I'll generate the complete README.md following the structure plan exactly:

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a library for creating short-term forecasts in the energy sector. It provides modular tools for machine learning-based forecasting, feature engineering, model evaluation, and backtesting. OpenSTEF is designed for energy system operators, researchers, and developers who need reliable, production-ready forecasting solutions.

Learn more at the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a monorepo structure with specialized packages. The repository contains **openstef-core** (core utilities and datasets), **openstef-models** (ML models and feature engineering), and **openstef-beam** (backtesting, evaluation, analysis, and metrics). All packages are developed together with automatic dependency resolution, allowing you to install only the components you need.

## How to Install

**Requirements:**
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, or Linux)

**Basic Installation:**

```bash
# Install the meta-package with core functionality
pip install openstef

# Install with all components
pip install "openstef[all]"

# Install individual packages
pip install openstef-models
pip install openstef-beam
pip install openstef-core
```

**Using modern package managers:**

```bash
# Using uv (recommended for development)
uv add openstef

# Using conda
conda install -c conda-forge openstef
```

For detailed installation instructions, troubleshooting, and platform-specific notes, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Examples and tutorials are available in the [`examples/`](examples/) folder. The examples folder contains its own README with an overview of available examples and quickstart guides.

For step-by-step tutorials, visit the [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html) page in the documentation.

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

If OpenSTEF contributes to a project that leads to a scientific publication, please cite the project using the DOI [10.5281/zenodo.15316405](https://doi.org/10.5281/zenodo.15316405).

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

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** — How to get help
- **[GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions)** — Community Q&A
- **[Issue Tracker](https://github.com/OpenSTEF/openstef/issues)** — Bug reports and feature requests
- **[LF Energy Slack](https://slack.lfenergy.org/)** — Join the #openstef channel
- **Email:** openstef@lfenergy.org

Join our four-weekly community meetings to connect with contributors and discuss the project roadmap. Details are available on the [Support](https://openstef.github.io/openstef/v4/project/support.html) page.