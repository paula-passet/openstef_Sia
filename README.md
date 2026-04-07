Now I have enough information to generate the README. Let me create it following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

![OpenSTEF Logo](https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg)

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term forecasts in the energy sector. It provides a complete machine learning framework with data preprocessing, feature engineering, model training, probabilistic forecasting, and evaluation—designed for grid congestion management, transport forecasts, and other energy applications. Learn more at the [OpenSTEF website](https://www.lfenergy.org/projects/openstef/).

## Monorepo Structure

OpenSTEF 4.0 uses a modular monorepo architecture with specialized packages: **openstef-models** (forecasting models and feature engineering), **openstef-beam** (backtesting, evaluation, analysis, and metrics), **openstef-core** (shared utilities and dataset types), and the **openstef** meta-package for convenient installation. This design allows you to install only the components you need while maintaining a unified development workflow.

## How to Install

**Requirements:** Python 3.12+ on a 64-bit operating system (Windows, macOS, Linux)

```bash
# Install the complete package (recommended)
pip install openstef

# Install specific components
pip install openstef-models  # Core forecasting only
pip install openstef-beam    # Evaluation tools only

# Install with all optional features
pip install "openstef[all]"

# Using uv (recommended for development)
uv add openstef
```

For detailed installation instructions, platform-specific notes, and troubleshooting, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) folder. The examples directory contains its own README with an overview of available examples, including quickstart guides, forecasting workflows, and advanced use cases. For step-by-step learning, visit the [Tutorials](https://openstef.github.io/openstef/v4/user_guide/tutorials.html) page in the documentation.

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

If OpenSTEF contributes to a project that leads to a scientific publication, please cite the project using our DOI or BibTeX entry.

**DOI:** [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5774964.svg)](https://doi.org/10.5281/zenodo.5774964)

For BibTeX format and detailed citation information, see [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html) or download our [CITATION.cff](CITATION.cff) file.

## Contact

- **Support & Questions:** [Support Guide](https://openstef.github.io/openstef/v4/project/support.html)
- **Slack:** Join the [LF Energy Slack workspace](https://slack.lfenergy.org/) (#openstef channel)
- **Email:** openstef@lfenergy.org
- **Issues:** [GitHub Issue Tracker](https://github.com/OpenSTEF/openstef/issues)
- **Community Meetings:** Four-weekly co-coding sessions ([details on our wiki](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting))
- **Project Homepage:** [LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)