Based on the knowledge base search results, I now have sufficient information to generate the README.md. Let me create it following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/_static/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF is a Python library for creating short-term forecasts in the energy sector. It provides machine learning models, feature engineering, and evaluation tools specifically designed for energy forecasting applications such as congestion management, transport forecasting, and grid operations.

Learn more at the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 is structured as a modular monorepo with specialized packages:

- **openstef-core** — Core data structures, datasets, and shared utilities
- **openstef-models** — Machine learning models, feature engineering, and preprocessing
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics tools
- **openstef** — Meta-package that provides convenient access to core functionality

This modular design allows you to install only the components you need for your specific use case.

## How to Install

**Requirements:**
- Python 3.12 or higher
- 64-bit operating system (Windows, macOS, or Linux)

**Basic installation:**

```bash
pip install openstef
```

**Complete installation with all packages:**

```bash
pip install "openstef[all]"
```

**Individual packages:**

```bash
# Core utilities and datasets only
pip install openstef-core

# Forecasting models only
pip install openstef-models

# Evaluation and backtesting tools only
pip install openstef-beam
```

For detailed installation instructions, platform-specific notes, and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Example Jupyter notebooks demonstrating OpenSTEF's functionality are available at [OpenSTEF/openstef-offline-example](https://github.com/OpenSTEF/openstef-offline-example).

Key examples include:
- [How to train a model](https://github.com/OpenSTEF/openstef-offline-example/blob/master/examples/01.%20Train%20a%20model%20using%20high-level%20pipelines.ipynb)
- [How to create a forecast](https://github.com/OpenSTEF/openstef-offline-example/blob/master/examples/04.%20Test_on_difficult_cases.ipynb)
- [How to evaluate model performance using backtesting](https://github.com/OpenSTEF/openstef-offline-example/blob/master/examples/02.%20Evaluate%20performance%20using%20Backtest%20Pipeline.ipynb)

For comprehensive tutorials and guides, visit the [documentation](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

- **Documentation:** [openstef.github.io/openstef](https://openstef.github.io/openstef/v4/)
- **Support Guide:** [How to get help](https://openstef.github.io/openstef/v4/project/support.html)
- **GitHub Discussions:** [Community Q&A](https://github.com/OpenSTEF/openstef/discussions)
- **Issue Tracker:** [Report bugs and request features](https://github.com/OpenSTEF/openstef/issues)
- **Slack:** [#openstef channel on LF Energy Slack](https://slack.lfenergy.org/)
- **Email:** [openstef@lfenergy.org](mailto:openstef@lfenergy.org)
- **Project Homepage:** [LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)