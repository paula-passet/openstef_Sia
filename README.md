Based on the knowledge base search results, I now have enough information to generate the README.md for release/v4.0.0. Let me create the complete README following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides machine learning models, feature engineering, and evaluation tools designed specifically for energy forecasting applications. Learn more at the [OpenSTEF project homepage](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages: **openstef-core** provides foundational data structures and utilities, **openstef-models** contains forecasting models and feature engineering, and **openstef-beam** offers backtesting, evaluation, analysis, and metrics capabilities. This architecture allows you to install only the components you need.

## How to Install

**Basic installation:**

```bash
pip install openstef
```

**For complete functionality:**

```bash
pip install "openstef[all]"
```

**System requirements:**
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, or Linux)

For detailed installation instructions, platform-specific notes, and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in our documentation:

- [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) — get up and running in minutes
- [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html) — step-by-step guides for common tasks

Additional examples are available in the repository's `examples/` folder.

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

If OpenSTEF contributes to a project that leads to a scientific publication, please cite us using the DOI or BibTeX entry below.

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

**Need help?** Visit our [Support page](https://openstef.github.io/openstef/v4/project/support.html) for resources and contact options.

**Connect with the community:**
- [GitHub Discussions](https://github.com/OpenSTEF/openstef/discussions) — Q&A and community discussions
- [GitHub Issues](https://github.com/OpenSTEF/openstef/issues) — bug reports and feature requests
- [LF Energy Slack](https://slack.lfenergy.org/) — join the #openstef channel
- Email: [openstef@lfenergy.org](mailto:openstef@lfenergy.org)