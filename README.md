Based on the knowledge base search results, I now have enough information to generate the README.md. Let me create it following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg" alt="OpenSTEF" width="500"/>

# OpenSTEF

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

OpenSTEF (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term forecasts in the energy sector. It provides a model-agnostic machine learning framework with complete pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. OpenSTEF generates probabilistic forecasts with uncertainty estimates and includes domain-specific knowledge for energy applications.

Learn more at the [LF Energy OpenSTEF project page](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages:

- **openstef-core** — Core utilities, dataset types, and shared base models
- **openstef-models** — ML models, feature engineering, and data processing
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics
- **openstef** — Meta-package that installs core forecasting components

This modular design allows you to install only the components you need for your use case.

## How to Install

**Requirements:** Python 3.12+ and a 64-bit operating system (Windows, macOS, Linux)

**Basic Installation:**

```bash
# For most users - installs models package
pip install openstef

# Core forecasting only
pip install openstef-models

# With all optional tools
pip install "openstef[all]"
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

Explore practical examples and tutorials in the [`examples/`](examples/) folder. The examples folder contains its own README with an overview of available examples covering:

- Basic forecasting workflows
- Custom model integration
- Backtesting and evaluation
- Advanced feature engineering

For step-by-step learning, visit the [Quick Start Guide](https://openstef.github.io/openstef/v4/user_guide/quick_start.html) and [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html).

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

**BibTeX format:**

```bibtex
@software{openstef,
  title = {OpenSTEF},
  author = {Contributors to the OpenSTEF project},
  url = {https://github.com/OpenSTEF/openstef},
  doi = {10.5281/zenodo.5576497}
}
```

**DOI:** [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5576497.svg)](https://doi.org/10.5281/zenodo.5576497)

For the complete citation file, see [CITATION.cff](CITATION.cff) or visit the [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html) page.

## Contact

- **Support and questions:** See our [Support Guide](https://openstef.github.io/openstef/v4/project/support.html)
- **Community chat:** Join the #openstef channel on [LF Energy Slack](https://slack.lfenergy.org/)
- **Bug reports and feature requests:** [GitHub Issues](https://github.com/OpenSTEF/openstef/issues)
- **Community meetings:** Join our four-weekly meetings — details on the [wiki page](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)
- **Email:** openstef@lfenergy.org