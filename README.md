Based on the knowledge base search results, I now have enough information to generate the README.md. Let me create it following the structure plan exactly.

<!--
SPDX-FileCopyrightText: 2017-2025 Contributors to the OpenSTEF project <openstef@lfenergy.org>

SPDX-License-Identifier: MPL-2.0
-->

<img src="https://raw.githubusercontent.com/OpenSTEF/openstef/main/docs/source/logos/openstef-horizontal-color.svg" alt="OpenSTEF" width="400"/>

[![Downloads](https://static.pepy.tech/badge/openstef)](https://pepy.tech/project/openstef)
[![Downloads](https://static.pepy.tech/badge/openstef/month)](https://pepy.tech/project/openstef)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5585/badge)](https://bestpractices.coreinfrastructure.org/projects/5585)

## What is OpenSTEF

**OpenSTEF** (Open Short-Term Energy Forecasting) is an open-source Python library for creating accurate short-term forecasts in the energy sector. It provides a model-agnostic framework with complete pipelines for data preprocessing, feature engineering, model training, forecasting, evaluation, and post-processing. OpenSTEF generates probabilistic forecasts with uncertainty bandwidths and includes built-in domain knowledge for energy-specific use cases such as congestion management, transport forecasts, and grid loss prediction. [Learn more about OpenSTEF](https://www.lfenergy.org/projects/openstef/).

## Monorepo Overview

OpenSTEF 4.0 uses a modular monorepo structure with specialized packages: **openstef-core** (shared utilities and types), **openstef-models** (ML models and feature engineering), **openstef-beam** (backtesting, evaluation, analysis, and metrics), and the **openstef** meta-package that provides convenient installation of core components.

## How to Install

**Requirements:** Python 3.12+ and a 64-bit operating system (Windows, macOS, Linux).

```bash
# Install OpenSTEF with core components
pip install openstef

# Install with all optional tools
pip install "openstef[all]"

# Using uv (recommended for development)
uv add openstef
```

For detailed installation instructions, including troubleshooting for Apple Silicon, GPU support, and development setup, see the [Installation Guide](https://openstef.github.io/openstef/v4/user_guide/installation.html).

## Examples

Explore practical examples and tutorials in the [`examples/`](examples/) folder. The examples directory contains its own README with an overview of available examples, including basic forecasting workflows, advanced feature engineering, and evaluation techniques.

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

If OpenSTEF contributes to a project that leads to a scientific publication, please cite the project. You can use the DOI or reference the GitHub repository.

**BibTeX format:**

```bibtex
@software{openstef,
  title = {OpenSTEF},
  author = {Contributors to the OpenSTEF project},
  url = {https://github.com/OpenSTEF/openstef},
  doi = {10.5281/zenodo.5720605}
}
```

For more citation formats, see [Citing OpenSTEF](https://openstef.github.io/openstef/v4/project/citing.html).

## Contact

- **[Support Guide](https://openstef.github.io/openstef/v4/project/support.html)** - how to get help
- **[Slack](https://slack.lfenergy.org/)** - join the #openstef channel for community discussions
- **[GitHub Issues](https://github.com/OpenSTEF/openstef/issues)** - report bugs and request features
- **[Email](mailto:openstef@lfenergy.org)** - contact the project team
- **[Community Meetings](https://wiki.lfenergy.org/display/OS/Four-weekly+community+meeting)** - join our four-weekly co-coding sessions
- **[LF Energy OpenSTEF](https://www.lfenergy.org/projects/openstef/)** - project homepage