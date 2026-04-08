Based on the knowledge base search results, I now have enough information to generate a comprehensive README.md for the OpenSTEF release/v4.0.0. Let me create it following the structure plan exactly.

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

**OpenSTEF** (Open Short-Term Energy Forecasting) is a Python library for creating accurate short-term forecasts in the energy sector. It provides machine learning pipelines for data preprocessing, feature engineering, model training, probabilistic forecasting, and evaluation—supporting use cases from congestion management to transport forecasts and grid loss prediction. OpenSTEF is model-agnostic, extensible, and designed for both research and production deployments.

Learn more at the [OpenSTEF project website](https://www.lfenergy.org/projects/openstef/).

## Brief Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages:

- **openstef-models** — Core forecasting models, feature engineering, and data processing
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics
- **openstef-core** — Core utilities, dataset types, and shared base models
- **openstef** — Meta-package for convenient installation

This architecture allows you to install only the components you need while maintaining a unified development workflow.

## How to Install

**System Requirements:**
- Python 3.12 or higher (Python 3.13 supported)
- 64-bit operating system (Windows, macOS, or Linux)

**Basic Installation:**

```bash
# Install the complete package (recommended)
pip install openstef

# Install specific components
pip install openstef-models  # Core forecasting only
pip install openstef-beam    # Evaluation tools only
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

Explore practical examples and tutorials in the [`examples/`](examples/) folder. The examples directory contains:

- **examples/** — Short, focused code examples demonstrating specific features
- **tutorials/** — Multi-step learning-oriented guides for getting started

Each folder includes its own README with an overview of available examples. For more learning resources, visit the [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html) page in the documentation.

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
  doi = {10.5281/zenodo.5841834}
}
```

For more citation formats and the full CITATION.cff file, see the [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html) page.

## Contact

**Need help or want to connect?**

- **Documentation:** [https://openstef.github.io/openstef/v4/](https://openstef.github.io/openstef/v4/)
- **Slack:** Join the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)
- **Email:** openstef@lfenergy.org
- **Issues:** [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- **Community Meetings:** Four-weekly co-coding sessions — details on the [Support page](https://openstef.github.io/openstef/v4/project/support.html)
- **Project Homepage:** [LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)